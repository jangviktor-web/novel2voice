# Additional Skill Details

## TTS 后端与回退机制

脚本支持两个 TTS 后端，自动检测并按优先级回退：

### 后端对比

| 后端 | 端点 | Key | 音色数 | 优先级 |
|---|---|---|---|---|
| **Edge TTS** | `tts.kalaok.cc.cd/v1/audio/speech` | 公开 `sk-1234567890` | 500+ 种（支持 style/speed/pitch/role/cleaning） | 高（默认） |
| **MiMo TTS** | `api.xiaomimimo.com/v1` | 需要 `MIMO_API_KEY` | 9 种（Dean, Milo, 冰糖 等） | 低（需手动切换） |

> **注意**：MiMo 后端不支持 `speed`/`pitch`/`style_degree`/`role` 参数。这些参数仅在 Edge TTS 后端生效。当使用 MiMo 后端且传入了这些参数时，脚本会打印警告。

### 后端选择流程

1. 默认使用 Edge TTS（无需 key，开箱即用）
2. 用户可通过 `--tts-backend mimo` 手动切换到 MiMo TTS
3. 如果选择 MiMo 但 key 不存在或失效 → 自动回退到 Edge TTS

### Agent 行为要求

**首次使用本 skill 时，Agent 必须先询问用户是否配置 MiMo API Key。** 检查方法：
1. 运行 `python generate_audiobook.py` 时调用 `load_config()` 检查 `.env` 文件
2. 如果 `.env` 不存在或 `MIMO_API_KEY` 为空 → 询问用户
3. 用户提供了 key → 调用 `save_config(mimo_key="用户的key")` 保存到 skill 目录的 `.env`
4. 用户选择不配置 → 跳过，默认使用 Edge TTS

**后续使用：** 自动从 `{baseDir}/.env` 读取已保存的 key，无需重复询问。

如果用户主动要求使用 MiMo TTS：
1. 调用 `get_mimo_api_key()` 检查 key（按优先级：环境变量 → openclaw 配置 → 本地 .env）
2. 如果 key 不存在 → 询问用户提供 key 并保存，或继续使用 Edge TTS
3. 如果 key 有效 → 在命令中添加 `--tts-backend mimo`

### 首次使用：Key 配置（必须询问）

> **Edge TTS 开箱即用，无需配置。** 但 Agent 首次使用时仍需询问用户是否有 MiMo key，以便保存备用。

**Agent 首次配置话术：**

```
首次使用有声书生成。默认使用 Edge TTS（免费，无需配置）。

你是否有 MiMo TTS API Key？如果有，我可以保存到本地，以后需要时直接调用。
  - 有 → 请提供 key，我会保存到 skill 目录的 .env 文件
  - 没有 → 跳过，直接使用 Edge TTS
```

**Key 保存：** Agent 收到用户回复后，调用 `save_config()` 保存到 skill 目录的 `.env`：

文件路径：`{baseDir}/.env`

```
MIMO_API_KEY=用户提供的key
```

用户随时可以说 "更新 mimo key: xxx" 来更新配置，Agent 调用 `save_config(mimo_key="新key")` 即可。

### 命令行参数

```bash
# 强制使用 MiMo
python3 generate_audiobook.py ... --tts-backend mimo

# 强制使用 Edge TTS
python3 generate_audiobook.py ... --tts-backend edge

# 自动检测（默认）
python3 generate_audiobook.py ...
```

### 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `TTS_BACKEND` | 强制后端 (`mimo`/`edge`/`auto`) | `edge` |
| `MIMO_API_KEY` | MiMo API 密钥 | — |
| `MIMO_API_BASE_URL` | MiMo API 端点 | `https://api.xiaomimimo.com/v1` |
| `EDGE_TTS_ENDPOINT` | Edge TTS 端点 | `https://tts.kalaok.cc.cd/v1/audio/speech` |
| `EDGE_TTS_KEY` | Edge TTS 密钥 | `sk-1234567890` |

---

## 字幕转语音工作流（SRT/ASS 字幕文件处理）

当用户上传 `.srt` 或 `.ass` 字幕文件并要求生成语音时，按以下流程执行。

### 字幕模式触发条件

| 用户输入 | 触发字幕模式 |
|---|---|
| 上传 `.srt` 文件 | ✅ |
| 上传 `.ass` / `.ssa` 文件 | ✅ |
| 说"字幕转语音"/"按字幕生成音频" | ✅ |
| 说"subtitle to audio" | ✅ |

### Step S1：解析字幕文件

```bash
python3 {baseDir}/scripts/subtitle_parser.py subtitle.srt
```

自动执行：
1. **多编码检测** — utf-8 → gbk → big5 → shift_jis → euc-kr → latin-1
2. **语言检测** — CJK→中文, 假名→日语, 谚文→韩语, 拉丁→英语
3. **说话人提取** — ASS `{Actor:角色名}` 或 Dialogue 行
4. **时间轴解析** — 提取 start_ms / end_ms

### Step S2：询问用户

检测完成后，告知用户结果并询问：

```
📄 字幕文件已解析：
- 格式：SRT
- 条目数：N 条
- 总时长：X 分钟
- 检测语言：中文（置信度 95%）
- 说话人：张三、李四

请问您想：
1. 直接用原语言生成语音
2. 翻译成其他语言再生成（请告诉我目标语言）
```

### Step S3：时间轴重叠检测与修复

```bash
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir
```

自动检测并修复重叠：

| 重叠情况 | 修复策略 |
|---|---|
| 重叠量 < 较短条目 50% | 缩短前一条 end_ms |
| 缩短后时长 < 200ms | 前一条保留 200ms，后一条后移 |
| 重叠量 ≥ 50% | 按文本长度比例重新分配 |
| 完全包含 | 合并为一条 |

修复后自动保存：`output_dir/subtitle_fixed.srt`

### Step S4：TTS 生成 + 语速适配

逐条生成 TTS，每句自动匹配字幕时间槽：

1. TTS 生成每条音频
2. ffprobe 获取实际时长
3. 与字幕时间槽对比
4. TTS 时长 > 字幕时长 → atempo 加速
5. 加速上限默认 2.0x（`--max-speed` 可调）

### Step S5：时间轴对齐合并

使用 adelay 滤镜精确控制播放位置，空隙填充静音。

### Step S6：输出

```
output_dir/
├── subtitle_audio.mp3    # 完整音频
├── subtitle_audio.wav    # WAV 版本
├── subtitle_fixed.srt    # 修复后的字幕
├── timeline.srt          # 时间轴副本
├── segments/             # 单条音频
└── generation_log.json   # 生成日志
```

### 字幕模式命令参考

```bash
# 基础用法
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir

# 指定说话人音色
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir \
  --speaker-voices '{"旁白":"冰糖","张三":"Dean","李四":"Mia"}'

# 指定说话人风格
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.ass output_dir \
  --speaker-voices '{"旁白":"mimo_default","张三":"Dean"}' \
  --speaker-styles '{"旁白":"温柔女声 语速适中","张三":"低沉磁性"}'

# 使用默认音色
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir \
  --default-voice "冰糖"

# 禁用重叠修复
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir \
  --no-fix-overlaps

# 禁用语速适配
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir \
  --no-speed-adjust

# 自定义加速上限
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir \
  --max-speed 2.5
```

### 翻译模式（可选）

```bash
# 导出翻译用 JSON
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir --export-srt

# 导入翻译后的 JSON
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir \
  --import-translated translated.json --target-lang en
```

---

## Edge TTS 配音标注公式

详见 [edge-tts-annotation-guide.md](references/edge-tts-annotation-guide.md)：
- 模块1：固定角色音色库公式（通用模板）
- 模块2：文本切割断句公式（停顿分级 + 三拆分原则）
- 模块3：角色标签标准模板（基础/情绪/完整参数三种格式）
- 模块4：对话分离标准公式（XX道：万能拆解）
- 模块5：群杂人物处理公式
- 模块6：诗词/奏折/祭文专用处理公式
- 避错约束公式（5条强制规则）

## 资源复用规范（禁止内联重写）

### 必须调用的内置资源

| 资源 | 路径 | 用途 |
|---|---|---|
| 主生成脚本 | `{baseDir}/scripts/generate_audiobook.py` | 有声书生成（自动解析模式） |
| TTS 脚本 | `{baseDir}/scripts/tts_voice.py` | 单条 TTS 调用 |
| 文本解析器 | `{baseDir}/scripts/text_parser.py` | 小说文本自动解析 |
| 字幕解析器 | `{baseDir}/scripts/subtitle_parser.py` | SRT/ASS 字幕处理 |
| 参数计算器 | `{baseDir}/scripts/param_calculator.py` | TTS 参数计算 |
| 音色试听页 | `{baseDir}/voice-demo/index.html` | 用户试听音色 |
| 标注公式文档 | `{baseDir}/references/edge-tts-annotation-guide.md` | 标注规范参考 |
| 工作流文档 | `{baseDir}/references/generated-long-body.md` | 完整工作流参考 |

### 禁止行为

1. **禁止**在对话中内联重写 Python 脚本逻辑
2. **禁止**自己拼装 TTS API 调用（必须用内置脚本）
3. **禁止**自己实现文本解析（必须用 text_parser.py）
4. **禁止**绕过 generate_audiobook.py 直接调用 API

### 正确调用方式

```bash
# ✅ 正确：调用内置脚本
python3 {baseDir}/scripts/generate_audiobook.py --auto novel.txt output_dir --tts-backend edge

# ❌ 错误：自己写 Python 代码调用 API
import requests
requests.post("https://tts.kalaok.cc.cd/v1/audio/speech", ...)
```

---

## Additional Details

See [generated-long-body.md](references/generated-long-body.md) for the extended material moved out of the main skill body.
