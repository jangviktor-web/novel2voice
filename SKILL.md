---
name: novel2voice
version: 2.19.1
description: >
  小说文本或字幕文件 → 多角色有声书音频。
  默认 Edge TTS（500+ 音色），可选 MiMo TTS。
  自动角色识别、情感标注、音色分配、异步并发生成。
  Use when user provides novel/story text or subtitle file (.srt/.ass) and asks for
  audiobook, audio drama, voice narration, or TTS generation.
  触发词：有声书、朗读、配音、转语音、小说转音频、字幕转语音、TTS、多角色语音。
applyTo: "**"
metadata:
  openclaw:
    emoji: "🎙️"
    requires:
      bins: ["python3", "ffmpeg"]
      pip: ["requests"]
    os: ["linux", "darwin", "win32"]
tags: [tts, audiobook, novel, multi-speaker, edge-tts, mimo-api, subtitle, srt, ass]
---

# Novel2Voice — 小说/字幕转多角色语音

将小说文本自动转化为高质量多角色有声书。支持角色识别、情感标注、音色分配、停顿控制。
支持 SRT/ASS 字幕文件转语音（多编码自动检测），按时间轴对齐生成。

---

## When to Use

| 场景 | 使用本 Skill？ |
|---|---|
| 用户发小说文本要求有声书 / 音频 / 朗读 | ✅ |
| 用户发字幕文件 (.srt/.ass) 要求转语音 | ✅ |
| 单段文本朗读 | ❌ 用 `mimo-tts-wav` |
| 唱歌 | ❌ 用 `mimo-tts-wav` + `唱歌` |

---

## 首次使用引导

当用户第一次使用本 skill 时（或明确说「第一次用」「怎么用」「教我用」），按以下顺序引导：

### Step 0：欢迎 + 环境检查

向用户说明功能，同时后台检查环境：

```
🎬 有声书功能就绪！我来帮你把小说变成多角色有声书。

功能概览：
• 自动识别角色 → 分配音色（男/女/老/少/方言）
• 支持情感标签（温柔、愤怒、东北话、唱歌…）
• 支持字幕文件（SRT/ASS）转语音
• 500+ 音色可选，全部免费

正在检查环境…
```

```bash
python3 -c "import requests; print('✅ requests')" 2>&1 || pip install requests
which ffmpeg && echo "✅ ffmpeg" || echo "❌ ffmpeg 未安装，音频转换将受限"
```

- 全部通过 → 继续 Step 1
- `requests` 缺失 → 自动 `pip install requests`
- `ffmpeg` 缺失 → 告知用户输出仅限 WAV 格式

### Step 1：推荐音色

展示当前后端的音色选项，让用户选择（注意：Edge TTS 和 MiMo TTS 音色完全不同）：

```
🎧 先选个音色吧！

【女声】晓晓(旁白/女主) · 晓依(温柔) · 晓涵(文艺) · 晓墨(情绪) · 晓睿(中年) · 晓双(少女) · 晓梦(甜妹)
【男声】云希(少年) · 云扬(播音/帝王) · 云健(硬汉) · 云夏(正太) · 云泽(老者) · 云枫(温润)
【方言】东北 · 河南 · 山东 · 四川 · 广西 · 陕西 · 吴语
【粤语】晓佳 · 晓蔓 · 云龙 【台湾腔】晓晨 · 晓雨 · 云哲

直接回复音色名就行，比如「用晓晓」。不确定的话我根据角色自动推荐。
```

> 完整音色详情（VoiceID、年龄、人设、适配角色）见 [音色选择引导](#音色选择引导) 章节。

如果用户选 MiMo TTS 后端，展示 MiMo 音色（冰糖/茉莉/苏打/白桦/mimo_default/Mia/Chloe/Milo/Dean），详见音色选择引导章节。

等用户回复音色偏好，或说「你推荐吧」直接进入 Step 2。

### Step 2：确认 TTS 后端

```
⚙️ TTS 后端选择：

✅ Edge TTS（默认）— 500+ 音色，免费，开箱即用，支持情感/语速/方言
   → 推荐大多数场景使用

🔧 MiMo TTS — 9 个精品音色，支持音色设计/复刻/唱歌
   → 需要 API Key（小米 MiMo 平台）

你选哪个？直接发小说文本的话，我会用 Edge TTS。
```

- 用户选 Edge / 直接发文本 → 跳到 Step 4
- 用户选 MiMo → Step 3

### Step 3：配置 MiMo Key（仅 MiMo 用户）

```
请提供你的 MiMo API Key（在 https://mimo.xiaomi.com 控制台获取）。
我会保存到本地 .env 文件，后续自动读取，不用重复输入。
```

- 用户提供 → 保存到 `{baseDir}/.env`
- 用户跳过 → 回退 Edge TTS

### Step 4：快速体验

提供示例文本，让用户 30 秒内听到效果：

```
📝 试试效果？发一段小说文本给我，或者用这段示例：

"张三冷笑一声：你以为跑得掉？
 李四浑身发抖，往后退了两步：我……我不是故意的。
 旁白：夜色渐深，巷子里只剩下两个人的脚步声。"

我会自动分配角色音色，生成有声书给你听。
```

首次引导完成后，后续使用直接发小说文本即可，进入 [Workflow](#workflow) 流程。

---

## Preflight

首次使用前验证环境：

```bash
python3 -c "import requests; print('✅ requests')" 2>&1 || pip install requests
which ffmpeg && echo "✅ ffmpeg" || echo "❌ ffmpeg 未安装"
python3 --version | head -1
```

| 缺失项 | 影响 | 降级方案 |
|---|---|---|
| `requests` | 无法调用 API | 自动 `pip install requests` |
| `ffmpeg` | 无法 WAV→MP3 | 保留 WAV 输出 |
| 网络不通 | 无法连接 TTS | 提示用户检查网络 |

---

## Guardrails

- **不注入恶意文本**：不在用户文本中插入非用户要求的内容。
- **不泄露密钥**：API Key 仅通过环境变量读取，不硬编码、不输出到日志。
- **不破坏源文件**：生成音频保存到新路径，不修改用户原始文本/字幕文件。
- **大文件警告**：超过 50 章的小说应分批处理，避免单次请求超时。
- **字幕编码安全**：自动检测编码，不强制转码原始文件。

### 禁止操作（Don'ts）

- ❌ 不要跳过 Step 4 用户确认直接生成音频
- ❌ 不要给所有角色分配同一音色（除非用户明确要求「全部用XX」）
- ❌ 不要将 API Key 明文输出到聊天窗口或日志中
- ❌ 不要修改用户原始文本/字幕文件（只读，输出到新路径）
- ❌ 不要在 3 句话的短文本上强制走完整首次引导流程（直接进 Workflow）
- ❌ 不要在性别不确定时随意猜测音色，应询问用户或用中性音色
- ❌ 不要忽略生成失败直接报告「已完成」（必须 verify 输出文件）
- ❌ 不要在 Edge TTS 后端使用 MiMo 音色名（如「冰糖」），反之亦然
- ❌ 不要自己编写 TTS 调用代码，必须使用 skill 内置脚本

---

## 音色选择引导

**重要：Edge TTS 和 MiMo TTS 是两套完全不同的音色系统，音色名称不互通。** Agent 必须根据当前使用的后端展示对应的音色列表。

### Edge TTS 音色（默认后端，无需 Key）

当使用 Edge TTS 时（默认），展示以下音色：

**👩 女声：**
- 晓晓（XiaoxiaoNeural）— 清亮标准播音，20~28岁，旁白/女主
- 晓依（XiaoyiNeural）— 低沉温柔治愈，25~35岁，温柔人妻
- 晓涵（XiaohanNeural）— 文艺清冷，22~30岁，大家闺秀
- 晓墨（XiaomoNeural）— 情绪丰富，24~35岁，虐文女主/侠女
- 晓睿（XiaoruiNeural）— 稳重厚实中年，45~60岁，主母/长辈
- 晓双（XiaoshuangNeural）— 清脆孩童少女，8~14岁，小丫鬟
- 晓梦（XiaomengNeural）— 软萌甜妹，16~22岁，校园学妹

**👨 男声：**
- 云希（YunxiNeural）— 清爽阳光少年，18~27岁，少年男主
- 云扬（YunyangNeural）— 央视浑厚播音，35~55岁，帝王/旁白
- 云健（YunjianNeural）— 低沉浑厚大叔，38~55岁，硬汉/武将
- 云夏（YunxiaNeural）— 正太少年童声，7~15岁，幼年男主
- 云泽（YunzeNeural）— 苍老沉稳，60岁+，隐世高人/长老
- 云枫（YunfengNeural）— 平淡务实，28~38岁，温润男配

**🌍 方言：** 云彪(男)/晓北(女)（东北）、云登(男)（河南）、云翔(男)（山东）、云熙(男)（四川）、云奇(男)（广西）、晓妮(女)（陕西）、云哲(男)/晓彤(女)（吴语）
**🇭🇰 粤语：** 晓佳(女)、晓蔓(女)、云龙(男)
**🇹🇼 台湾腔：** 晓晨(女)、晓雨(女)、云哲(男)

> 直接回复音色名称即可，如「用晓晓」「旁白用云扬，女主用晓依」。

### MiMo TTS 音色（需 API Key）

当用户选择 MiMo TTS 后端时，展示以下音色（**注意：名称与 Edge TTS 完全不同**）：

**🎤 中文音色：**
- 冰糖 — 清甜治愈女声，适合温柔女主
- 茉莉 — 软糯温柔女声，适合软萌女主/心机女配
- 苏打 — 清亮少年男声，适合少年角色
- 白桦 — 苍老沉稳男声，适合老年角色
- mimo_default — 中性女声，默认旁白音色

**🌐 英文音色：**
- Mia — 活泼开朗女声
- Chloe — 冷淡优雅女声
- Milo — 清亮阳光男声
- Dean — 低沉磁性男声

> MiMo 音色支持「音色设计」和「音色复刻」，详见 [mimo-tts-api.md](references/mimo-tts-api.md)。

### HTML 试听页面（本地环境可用）

本地用户可打开试听页面，支持搜索、分类筛选、一键复制音色名称：

```
{baseDir}/scripts/voice_samples/index.html
```

> 注意：HTML 页面仅包含 Edge TTS 音色样本，不含 MiMo 音色。

---

## Workflow

```
用户发送小说
  ↓
Agent 分析章节 → 提取角色（名字/性别/年龄/性格）
  ↓
Skill 提供音色库（Edge TTS + MiMo TTS）
  ↓
Agent 自动匹配音色
  ↓
用户确认 → Skill 生成音频
```

### 短文本快速路径

当文本 < 500 字且角色 ≤ 3 个时，跳过首次引导和音色库展示，直接：
1. 自动匹配音色 → 展示 Step 3 输出模板 → 用户确认 → 生成

**输入预处理：** 如果用户发的是聊天文本（非文件路径），Agent 必须先写入 `{output_dir}/input.txt`，再调用脚本。

### Step 1：Agent 分析章节 + 提取角色

Agent 收到小说文本后：

1. **拆分章节** — 按「第X章/回/节」拆分，无章节标记则作为单章
2. **提取角色** — 用 LLM 分析每个章节，输出角色表：

| 角色名 | 性别 | 年龄段 | 性格 | 说话风格 | 出场频率 |
|---|---|---|---|---|---|
| 许七安 | 男 | 青年 | 机智幽默 | 活泼偶尔深沉 | 高 |

分析要点：从称谓推断性别/年龄，从对话推断性格，从行为推断风格。

### Step 2：Skill 提供音色库

Agent 根据当前后端向用户展示可用音色（详见 [音色选择引导](#音色选择引导)）：

- **Edge TTS（默认）**：28 个中文音色（女声7/男声6/方言9/粤语3/台湾腔3）
- **MiMo TTS**：9 个音色（冰糖/茉莉/苏打/白桦/mimo_default/Mia/Chloe/Milo/Dean）

### Step 3：Agent 自动匹配音色

Agent 根据角色特征自动匹配最佳音色：

- 性别严格区分（男→男声，女→女声）
- 年龄影响选择（少年→少年音，老年→老年音）
- 性格匹配声线（活泼→阳光，冷淡→低沉）
- 主角 > 配角 > 龙套（辨识度递减）
- 性别不确定 → 询问用户或使用中性音色，禁止猜测

**输出模板（Edge TTS 后端）：**

```
🎭 角色音色方案（Edge TTS）：

| 角色 | 音色 | VoiceID | Style | 理由 |
|------|------|---------|-------|------|
| 旁白 | 云扬 | zh-CN-YunyangNeural | narration-professional | 浑厚播音，适合叙事 |
| 张三 | 云健 | zh-CN-YunjianNeural | serious | 冷笑/威胁→低沉硬汉 |
| 李四 | 云希 | zh-CN-YunxiNeural | fearful | 发抖/害怕→少年惊恐 |

确认？可修改，如「旁白换晓晓」「李四用云夏」。
```

**输出模板（MiMo TTS 后端）：**

```
🎭 角色音色方案（MiMo TTS）：

| 角色 | 音色 | 风格描述 | 理由 |
|------|------|----------|------|
| 旁白 | mimo_default | 中性平稳 | 默认旁白 |
| 张三 | Dean | 低沉磁性 | 冷笑/威胁→成熟反派 |
| 李四 | Milo | 清亮紧张 | 发抖/害怕→少年感 |

确认？可修改，如「张三换白桦」。
```

### Step 4：用户确认

🔴 **CHECKPOINT · 🛑 STOP** — 必须等待用户回复后才能继续生成。禁止未经确认直接执行脚本。

展示推荐方案 + 完整音色列表，用户可修改。

用户回复方式：
- 「可以」→ 直接生成
- 「旁白换成云扬」→ 修改后生成
- 「全部用晓晓」→ 统一音色后生成
- 「你推荐吧」→ 跳过确认，直接生成
- 用户未回复 → 不生成，不跳过，等待

### Step 5：Skill 生成音频

**路径变量默认值：**
- `{output_dir}` = `{baseDir}/output/`（或用户指定路径）
- `{input_file}` = 用户提供的文件路径；若为聊天文本，Agent 先写入 `{output_dir}/input.txt`

```bash
# Edge TTS 模式（默认，推荐）
python3 {baseDir}/scripts/generate_audiobook.py --auto {input_file} {output_dir} --async --concurrent 5

# MiMo TTS 模式
python3 {baseDir}/scripts/generate_audiobook.py --auto {input_file} {output_dir} --tts-backend mimo
```

生成完成后 verify 音频文件是否存在且可播放。

### 失败处理

| 失败场景 | 检测方式 | 一线修复 | 仍失败兜底 |
|----------|----------|----------|------------|
| 单条 TTS 超时(>30s) | 脚本返回 timeout/error | 重试 1 次 | 跳过该条，标记 [SKIPPED]，继续后续 |
| 角色性别无法判断 | 分析结果 gender=unknown | 询问用户 | 使用中性音色（晓晓/mimo_default） |
| 用户文本为空或无对话 | 提取角色数=0 | 告知用户"未检测到对话" | 全文作为旁白朗读 |
| Edge TTS 端点不可达 | HTTP 连接失败 | 自动切换备用端点 | 提示用户检查网络，无法降级 |
| 输出文件为 0 字节 | verify 检查文件大小 | 删除空文件，重新生成该段 | 报告失败段落编号，让用户决定是否重试 |
| ffmpeg 缺失 | Preflight 检查 | 告知用户仅输出 WAV | 跳过 MP3 转换步骤 |
| 用户发的是聊天文本非文件 | 输入无文件路径 | Agent 先写入 `{output_dir}/input.txt` | — |
| Windows 编码乱码（角色名） | 日志中角色名显示为乱码 | 用 `python`（非 `python3`）执行 | 手动构建 segments.json 绕过自动解析 |

### 大文件处理（>50 章）

1. 按 10-20 章为一批分批生成
2. 每批完成后告知用户进度（如「已完成第1-15章，共3批中的第1批」）
3. 全部完成后合并为完整有声书

---

## Input Handling

自动识别并处理以下输入格式：

| 输入 | 处理 |
|---|---|
| 纯文本段落 | 直接作为小说原文 |
| `.txt` 文件 | 读取后处理 |
| 复制粘贴片段 | 自动识别为小说片段 |
| 章节标题开头 | 自动识别为章节内容 |
| `.srt` / `.ass` | 字幕模式，按时间轴对齐 |

### 触发关键词

有声书、音频、朗读、配音、TTS、转语音、生成语音、语音合成、字幕转语音

---

## Style Control

在文本中嵌入风格标签：

```
(温柔)晚安，好梦。
(东北话)哎呀妈呀，这天儿也忒冷了吧！
(紧张)[深呼吸]呼……冷静。
(唱歌)原谅我这一生不羁放纵爱自由。
```

支持：基础情绪、复合情绪、语调、音色、人设、方言、角色扮演、唱歌。
完整标签列表见 [references/voice-catalog.md](references/voice-catalog.md)。

---

## TTS 后端

| 后端 | 端点 | Key | 音色数 | 优先级 |
|---|---|---|---|---|
| **Edge TTS** | `tts.kalaok.cc.cd/v1/audio/speech` | 公开 `sk-1234567890` | 500+（支持 style/speed/pitch/role） | 高（默认） |
| **MiMo TTS** | `api.xiaomimimo.com/v1` | 需要 `MIMO_API_KEY` | 9 种 | 低（需手动切换） |

### 后端选择

1. 默认使用 Edge TTS（无需 key，开箱即用）
2. 用户可通过 `--tts-backend mimo` 切换到 MiMo TTS
3. MiMo key 不存在或失效 → 自动回退 Edge TTS

### Agent 行为：首次使用必须询问

1. 检查 `{baseDir}/.env` 是否存在 `MIMO_API_KEY`
2. 不存在 → 询问用户是否配置
3. 用户提供 key → 保存到 `{baseDir}/.env`
4. 用户跳过 → 默认使用 Edge TTS
5. 后续使用自动读取已保存的 key

### 环境变量

| 变量 | 说明 | 默认 |
|---|---|---|
| `TTS_BACKEND` | 强制后端 (`mimo`/`edge`/`auto`) | `edge` |
| `EDGE_TTS_ENDPOINT` | Edge TTS 端点 | `tts.kalaok.cc.cd/v1/audio/speech` |
| `EDGE_TTS_KEY` | Edge TTS Key | 公开默认值 |
| `MIMO_API_KEY` | MiMo TTS Key | 空 |

---

## 字幕转语音工作流（SRT/ASS）

当用户上传字幕文件并要求生成语音时，按以下流程执行。

### 触发条件

| 用户输入 | 触发 |
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

| 重叠情况 | 修复策略 |
|---|---|
| 重叠量 < 较短条目 50% | 缩短前一条 end_ms |
| 缩短后时长 < 200ms | 前一条保留 200ms，后一条后移 |
| 重叠量 ≥ 50% | 按文本长度比例重新分配 |
| 完全包含 | 合并为一条 |

修复后保存：`output_dir/subtitle_fixed.srt`

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

### 命令参考

```bash
# 基础用法
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir

# 指定说话人音色
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir   --speaker-voices '{"旁白":"冰糖","张三":"Dean","李四":"Mia"}'

# 指定说话人风格
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.ass output_dir   --speaker-voices '{"旁白":"mimo_default","张三":"Dean"}'   --speaker-styles '{"旁白":"温柔女声 语速适中","张三":"低沉磁性"}'

# 使用默认音色
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir   --default-voice "冰糖"

# 禁用重叠修复
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir   --no-fix-overlaps

# 禁用语速适配
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir   --no-speed-adjust

# 自定义加速上限
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir   --max-speed 2.5
```

### 翻译模式（可选）

```bash
# 导出翻译用 JSON
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir --export-srt

# 导入翻译后的 JSON
python3 {baseDir}/scripts/generate_audiobook.py --subtitle subtitle.srt output_dir   --import-translated translated.json --target-lang en
```

---

## Advanced References

| 文档 | 内容 |
|---|---|
| [voice-catalog.md](references/voice-catalog.md) | 完整音色库（Edge TTS + MiMo）+ 风格标签 + 角色映射 |
| [mimo-tts-api.md](references/mimo-tts-api.md) | MiMo TTS API 详细参数 + 调用示例 |
| [edge-tts-annotation-guide.md](references/edge-tts-annotation-guide.md) | Edge TTS 标注指南 |
| [generated-long-body.md](references/generated-long-body.md) | 长文本处理扩展说明 |

---

## Troubleshooting

| 问题 | 解决 |
|---|---|
| 生成无声音 | 检查 ffmpeg 是否安装 |
| Edge TTS 连接失败 | 脚本自动切换备用端点 |
| 中文乱码 | 确保文件 UTF-8 编码 |
| 角色识别不准 | 手动在 segments.json 中调整 |
| 生成太慢 | 使用 `--async --concurrent 5` 并发 |
| 验证输出 | verify 生成的音频文件是否存在且可播放 |
