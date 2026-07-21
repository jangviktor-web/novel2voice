<div align="center">

<img src="assets/logo.png" width="200" alt="Novel2Voice Logo"/>

# Novel2Voice

**小说 / 视频字幕 → 多角色有声书，一步到位。**

自动角色识别 · 情感标注 · 智能音色分配 · 异步并发生成 · 500+ 音色

[![Edge TTS](https://img.shields.io/badge/Edge_TTS-500+_Voices-orange?style=flat-square&logo=microsoftedge&logoColor=white)](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)
[![MiMo TTS](https://img.shields.io/badge/MiMo_TTS-9_Voices-green?style=flat-square)](https://mimo.xiaomi.com)
[![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-007808?style=flat-square&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?style=flat-square)](#)

<br/>

<a href="#-Installation">安装</a> <a href="#-quick-start">快速开始</a> · <a href="#-features">Features</a> · <a href="#-voice-library">音色</a> · <a href="#-usage">Usage</a> · <a href="#-workflow">工作流</a> · <a href="#-comparison">Comparison</a> · <a href="references/">Docs</a>

</div>

---

## 📦 Installation

### 方式一：ClawHub 一键安装（推荐）

```bash
openclaw skills install @jangviktor-web/novel2voice
```

### 方式二：直接克隆

```bash
git clone https://github.com/jangviktor-web/novel2voice.git
cd novel2voice
pip install requests charset_normalizer
```

### 方式三：一键安装脚本

```bash
curl -fsSL https://raw.githubusercontent.com/jangviktor-web/novel2voice/main/install.sh | bash
```

### 方式四：手动放入 Skills 目录

```bash
# QoderWork / OpenClaw / Claude Code 等 skills-compatible runtime
cp -r novel2voice ~/.qoderworkcn/skills/novel2voice
```

### 环境要求

| 依赖 | 版本 | 用途 | 必须 |
|---|---|---|---|
| Python | ≥ 3.8 | 主脚本运行 | ✅ |
| FFmpeg | 任意 | MP3 编码 + 响度标准化 | ✅ |
| requests | 最新 | HTTP 请求 TTS API | ✅ |
| charset_normalizer | 最新 | 字幕文件编码检测 | 推荐 |
| 网络连接 | — | 调用 Edge TTS / MiMo API | ✅ |

> [!NOTE]
> Edge TTS 为默认后端，无需 API Key，开箱即用。MiMo TTS 需要额外设置 `MIMO_API_KEY`。

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🎭 | **多角色自动分配** | LLM 分析角色性别/年龄/性格，自动匹配最佳音色 |
| 🎨 | **情感风格控制** | 50+ 情感标签（温柔/愤怒/悲伤/撒娇…）、方言、唱歌模式 |
| 📝 | **字幕转语音** | SRT/ASS 字幕文件，多编码自动检测，按时间轴对齐生成 |
| ⚡ | **异步并发** | 多线程 TTS 生成，速度提升 3-5x，支持断点续传 |
| 🔊 | **500+ 音色** | Edge TTS 覆盖 100+ 语言/地区，中文 28 个精品音色 |
| 🎵 | **MiMo TTS** | 小米 MiMo 音色设计、音色复刻、唱歌（需 API Key） |
| 🎧 | **在线试听** | 内置 HTML 音色试听页面，搜索/筛选/一键复制 |
| 📖 | **章节拆分** | 自动识别「第X章/回/节」，按章合并输出 |
| 🔁 | **断点续传** | 中断后自动跳过已完成片段，继续生成 |
| 🎚️ | **响度标准化** | EBU R128 标准响度归一化，听感一致 |

---

## 🚀 Quick Start

### 1. 环境准备

```bash
# 检查依赖
python3 --version   # ≥ 3.8
ffmpeg -version     # 音频格式转换 + 响度标准化

# 安装 Python 依赖
pip install requests charset_normalizer
```

### 2. 一键生成

```bash
# 小说文本 → 有声书（自动识别角色）
python3 scripts/generate_audiobook.py --auto novel.txt ./output

# 异步并发（推荐，3-5x 加速）
python3 scripts/generate_audiobook.py --auto novel.txt ./output --async --concurrent 5
```

### 3. 完成

输出文件在 `./output/` 目录：

```
output/
├── output_complete.mp3      ← 完整有声书
├── chapters/                ← 按章节拆分
│   ├── 001_第一章.mp3
│   └── 002_第二章.mp3
├── segments/                ← 单片段（可选保留）
└── generation_log.json      ← 生成日志
```

> [!TIP]
> 首次运行会自动生成 3 段预览（`preview.mp3`），确认音色满意后再全量生成。

---

## 📖 Usage

### 基础用法

```bash
# 自动模式：LLM 分析角色 → 分配音色 → 生成
python3 scripts/generate_audiobook.py --auto novel.txt ./output
```

### 指定角色音色

```bash
# 手动指定角色→音色映射
python3 scripts/generate_audiobook.py --auto novel.txt ./output \
  --character-voices '{"旁白":"云扬","许七安":"云希","洛玉衡":"晓涵","李妙真":"晓墨"}'
```

### 字幕转语音

```bash
# SRT 字幕
python3 scripts/generate_audiobook.py --subtitle movie.srt ./output

# ASS 字幕 + 指定说话人音色
python3 scripts/generate_audiobook.py --subtitle anime.ass ./output \
  --speaker-voices '{"旁白":"云扬","张三":"云希","李四":"晓晓"}'
```

### 使用 MiMo TTS

```bash
# 需要设置 MIMO_API_KEY 环境变量
export MIMO_API_KEY="your-key-here"

python3 scripts/generate_audiobook.py --auto novel.txt ./output --tts-backend mimo
```

### 仅预览

```bash
# 只生成前 3 段，快速确认音色效果
python3 scripts/generate_audiobook.py --auto novel.txt ./output --preview-only
```

### 情感风格控制

在文本中嵌入风格标签即可控制语气：

```text
(温柔)晚安，好梦。
(东北话)哎呀妈呀，这天儿也忒冷了吧！
(紧张)[深呼吸]呼……冷静，冷静。
(唱歌)原谅我这一生不羁放纵爱自由。
(极其疲惫，有气无力)师傅……到地方了叫我一声……
```

<details>
<summary>📋 完整风格标签列表</summary>

**基础情绪：** 开心 / 悲伤 / 愤怒 / 恐惧 / 惊讶 / 兴奋 / 委屈 / 平静 / 冷漠

**复合情绪：** 怅然 / 欣慰 / 无奈 / 愧疚 / 释然 / 嫉妒 / 厌倦 / 忐忑 / 动情

**语调：** 温柔 / 高冷 / 活泼 / 严肃 / 慵懒 / 俏皮 / 深沉 / 干练 / 凌厉

**音色：** 磁性 / 醇厚 / 清亮 / 空灵 / 稚嫩 / 苍老 / 甜美 / 沙哑 / 醇雅

**人设：** 夹子音 / 御姐音 / 正太音 / 大叔音 / 台湾腔

**方言：** 东北话 / 四川话 / 河南话 / 粤语

**行内标签：** `[吸气]` `[深呼吸]` `[叹气]` `[喘息]` `[笑]` `[轻笑]` `[大笑]` `[冷笑]` `[抽泣]` `[呜咽]` `[哽咽]` `[颤抖]` `[气声]` `[沙哑]`

</details>

---

## 🎙️ Voice Library

### Edge TTS 中文音色 · 28 个

<table>
<tr>
<td valign="top">

**👩 女声 (7)**

| 音色 | 声线 | 适配角色 |
|---|---|---|
| 晓晓 | 清亮标准播音 | 旁白、女主、解说 |
| 晓依 | 低沉温柔治愈 | 温柔人妻、治愈系 |
| 晓涵 | 文艺清冷 | 大家闺秀、文艺女主 |
| 晓墨 | 情绪丰富 | 虐文女主、江湖侠女 |
| 晓睿 | 稳重厚实中年 | 主母、长辈、老管家 |
| 晓双 | 清脆孩童少女 | 小丫鬟、幼年女主 |
| 晓梦 | 软萌甜妹 | 甜宠文女配、校园学妹 |

</td>
<td valign="top">

**👨 男声 (6)**

| 音色 | 声线 | 适配角色 |
|---|---|---|
| 云希 | 清爽阳光少年 | 少年男主、校园 |
| 云扬 | 央视浑厚播音 | 帝王、官员、旁白 |
| 云健 | 低沉浑厚大叔 | 硬汉、武将、中年男主 |
| 云夏 | 正太少年童声 | 幼年男主、小师弟 |
| 云泽 | 苍老沉稳 | 隐世高人、长老 |
| 云枫 | 平淡务实 | 温润男配、务实配角 |

</td>
</tr>
<tr>
<td valign="top">

**🌍 方言 (9)**

| 音色 | 口音 | 性别 |
|---|---|---|
| 云彪 | 东北 | 男 |
| 晓北 | 东北 | 女 |
| 云登 | 河南 | 男 |
| 云翔 | 山东 | 男 |
| 云熙 | 四川 | 男 |
| 云奇 | 广西 | 男 |
| 晓妮 | 陕西 | 女 |
| 云哲 | 吴语 | 男 |
| 晓彤 | 吴语 | 女 |

</td>
<td valign="top">

**🇭🇰 粤语 (3) · 🇹🇼 台湾腔 (3)**

| 音色 | 地区 | 性别 |
|---|---|---|
| 晓佳 | 粤语 | 女 |
| 晓蔓 | 粤语 | 女 |
| 云龙 | 粤语 | 男 |
| 晓晨 | 台湾 | 女 |
| 晓雨 | 台湾 | 女 |
| 云哲 | 台湾 | 男 |

</td>
</tr>
</table>

### MiMo TTS 音色 · 9 个

| 音色 | 语言 | 声线 | 适配角色 |
|---|---|---|---|
| 冰糖 | 中文 | 清甜治愈 | 温柔女主 |
| 茉莉 | 中文 | 软糯温柔 | 软萌女主、心机女配 |
| 苏打 | 中文 | 清亮少年 | 少年角色 |
| 白桦 | 中文 | 苍老沉稳 | 老年角色 |
| Mia | 英文 | 活泼开朗 | 活泼女主 |
| Chloe | 英文 | 冷淡优雅 | 御姐 |
| Milo | 英文 | 清亮阳光 | 少年男主 |
| Dean | 英文 | 低沉磁性 | 成熟男主 |

> 🎧 **试听全部音色**：用浏览器打开 [`scripts/voice_samples/index.html`](scripts/voice_samples/index.html)，支持搜索、分类筛选、一键复制音色名称。

---

## 🔄 Workflow

```mermaid
graph LR
    A[📄 文本/字幕输入] --> B[📑 章节拆分]
    B --> C[🔍 角色提取]
    C --> D[🎨 音色匹配]
    D --> E[✅ 用户确认]
    E --> F[🔊 并发生成]
    F --> G[🎚️ 响度标准化]
    G --> H[🎵 合并输出]
```

| Step | 说明 | 输出 |
|---|---|---|
| **1. 拆分章节** | 按「第X章/回/节」自动拆分，无标记则单章 | 章节列表 |
| **2. 提取角色** | LLM 分析性别/年龄/性格/说话风格 | 角色档案 |
| **3. 匹配音色** | 根据特征自动匹配 + 情感标注 | 推荐方案表 |
| **4. 用户确认** | 展示方案，可调整任意角色音色 | 确认/修改 |
| **5. 生成音频** | Edge TTS / MiMo TTS 异步并发 | 分段 MP3 |
| **6. 后处理** | 响度标准化 + 按章合并 + ID3 标签 | 最终 MP3 |

---

## 🆚 Comparison

| Feature | Novel2Voice | ebook2audiobook | 传统 TTS 工具 | 在线朗读器 |
|---|---|---|---|---|
| 多角色自动分配 | ✅ LLM 识别 | ✅ | ❌ 手动 | ❌ 单角色 |
| 情感/风格控制 | ✅ 50+ 标签 | ⚠️ SSML | ⚠️ 有限 | ❌ 无 |
| 字幕转语音 | ✅ SRT/ASS | ❌ | ❌ | ❌ |
| 并发生成 | ✅ 异步多线程 | ✅ | ❌ 串行 | ❌ |
| 音色数量 | ✅ 500+ | ✅ | ⚠️ 几十个 | ⚠️ 几个 |
| 中文方言 | ✅ 9 种方言 | ❌ | ❌ | ❌ |
| 断点续传 | ✅ | ✅ | ❌ | ❌ |
| 免费 | ✅ 完全免费 | ✅ | ⚠️ 部分收费 | ❌ 通常收费 |
| 无需 GPU | ✅ | ✅ | ⚠️ 部分需要 | ✅ |

---

## 📁 Structure

```
novel2voice/
├── SKILL.md                           # Agent 指令（核心工作流）
├── README.md                          # ← 你在这里
├── install.sh                         # 一键安装脚本
├── .gitignore
├── references/
│   ├── voice-catalog.md               # 完整音色库 + 风格标签 + 角色映射
│   ├── mimo-tts-api.md                # MiMo TTS API 文档
│   ├── edge-tts-annotation-guide.md   # Edge TTS 标注规范
│   └── generated-long-body.md         # 长文本处理策略
└── scripts/
    ├── generate_audiobook.py          # 主生成引擎
    ├── tts_voice.py                   # 单句 TTS 工具
    ├── tts_voice.sh                   # Shell 版 TTS
    ├── text_parser.py                 # 小说文本解析器
    ├── subtitle_parser.py             # SRT/ASS 字幕解析器
    ├── param_calculator.py            # 情感参数计算器
    ├── generate_voice_samples.py      # 音色样本生成器
    └── voice_samples/
        ├── index.html                 # 🎧 音色试听页面
        └── *.mp3                      # 28 个音色样本
```

---

## 🛠️ Troubleshooting

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 生成无声音 | FFmpeg 未安装 | `apt install ffmpeg` / `brew install ffmpeg` |
| Edge TTS 连接失败 | 网络问题 | 脚本自动切换备用端点，或检查代理 |
| 中文乱码 | 文件编码非 UTF-8 | 转换编码：`iconv -f GBK -t UTF-8 input.txt` |
| 角色识别不准 | 文本格式特殊 | 手动指定 `--character-voices` |
| 生成太慢 | 未启用并发 | 加 `--async --concurrent 5` |
| Windows 中文路径报错 | cmd 编码问题 | 用 `python` 代替 `python3`，路径避免中文 |
| MiMo TTS 401 | API Key 无效 | 检查 `MIMO_API_KEY` 环境变量 |
| 字幕时间轴偏移 | 重叠时间码 | 默认自动修复，或 `--no-fix-overlaps` 禁用 |

---

## 📚 Documentation

| 文档 | 说明 |
|---|---|
| [SKILL.md](SKILL.md) | Agent 完整工作流指令 |
| [Voice Catalog](references/voice-catalog.md) | 完整音色库、风格标签、角色→音色映射表 |
| [MiMo TTS API](references/mimo-tts-api.md) | MiMo TTS 三种模型 API 文档 |
| [Edge TTS Guide](references/edge-tts-annotation-guide.md) | Edge TTS 标注规范（角色/情绪/断句） |
| [Long Body](references/generated-long-body.md) | 长文本处理扩展说明 |

---

## 📄 License

[MIT](LICENSE)

---

<div align="center">

<sub>Built with ❤️ for novel lovers · Powered by <a href="https://learn.microsoft.com/en-us/azure/ai-services/speech-service/">Edge TTS</a> & <a href="https://mimo.xiaomi.com">MiMo TTS</a></sub>

<sub>🎙️ Novel2Voice — 让每一本小说都有声音</sub>

</div>
