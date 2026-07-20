<div align="center">

<img src="https://img.shields.io/badge/🎙️-Novel2Voice-v2.19.1-blue?style=for-the-badge&labelColor=0f1117&color=6c8cff" alt="title"/>

# Novel2Voice — 小说/字幕转多角色语音

**小说 / 视频字幕 → 多角色有声书，一步到位。**

自动角色识别 · 情感标注 · 智能音色分配 · 异步并发生成

[![Edge TTS](https://img.shields.io/badge/Edge_TTS-500+_Voices-orange?style=flat-square&logo=microsoftedge&logoColor=white)](https://edge.microsoft.com)
[![MiMo TTS](https://img.shields.io/badge/MiMo_TTS-9_Voices-green?style=flat-square)](https://mimo.xiaomi.com)
[![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Stable-brightgreen?style=flat-square)](#)

<br/>

<a href="#-features">Features</a> · <a href="#-quick-start">Quick Start</a> · <a href="#-voice-library">Voices</a> · <a href="#-comparison">Comparison</a> · <a href="references/">Docs</a>

</div>

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🎭 | **多角色自动分配** | 自动识别角色性别/年龄/性格，匹配最佳音色 |
| 🎨 | **情感风格控制** | 50+ 情感标签、方言、角色扮演、唱歌模式 |
| 📝 | **字幕转语音** | SRT/ASS 字幕文件，按时间轴对齐生成 |
| ⚡ | **异步并发** | 多线程 TTS 生成，速度提升 3-5x |
| 🔊 | **500+ 音色** | Edge TTS 覆盖 100+ 语言/地区 |
| 🎵 | **MiMo TTS** | 音色设计、音色复刻、唱歌 |
| 🎧 | **在线试听** | 内置 HTML 音色试听页面，一键复制 |

## 🆚 Comparison

| Feature | Novel2Voice | 传统 TTS 工具 | 在线朗读器 |
|---|---|---|---|
| 多角色自动分配 | ✅ 自动识别 | ❌ 手动 | ❌ 单角色 |
| 情感/风格控制 | ✅ 50+ 标签 | ⚠️ 有限 | ❌ 无 |
| 字幕转语音 | ✅ SRT/ASS | ❌ 不支持 | ❌ 不支持 |
| 并发生成 | ✅ 异步多线程 | ❌ 串行 | ❌ 无 |
| 音色数量 | ✅ 500+ | ⚠️ 几十个 | ⚠️ 几个 |
| 离线可用 | ✅ 本地运行 | ⚠️ 部分 | ❌ 需联网 |
| 免费 | ✅ 完全免费 | ⚠️ 部分收费 | ❌ 通常收费 |

## 🚀 Quick Start

### Prerequisites

```bash
python3 --version   # ≥ 3.8
which ffmpeg         # 音频格式转换
pip install requests # HTTP 请求
```

### Usage

```bash
# 小说文本 → 有声书
python3 scripts/generate_audiobook.py --auto novel.txt output_dir

# 字幕 → 语音
python3 scripts/generate_audiobook.py subtitle.srt output_dir --tts-backend edge

# 异步并发（推荐，3-5x 加速）
python3 scripts/generate_audiobook.py --auto novel.txt output_dir --async --concurrent 5
```

### Style Control

在文本中嵌入风格标签即可控制情感：

```text
(温柔)晚安，好梦。
(东北话)哎呀妈呀，这天儿也忒冷了吧！
(紧张)[深呼吸]呼……冷静，冷静。
(唱歌)原谅我这一生不羁放纵爱自由。
```

## 🎙️ Voice Library

### Edge TTS 中文音色 · 28 个

<table>
<tr>
<td valign="top">

**👩 女声 (7)**

| 音色 | 特点 |
|---|---|
| 晓晓 | 清亮标准播音 |
| 晓依 | 低沉温柔治愈 |
| 晓涵 | 文艺清冷 |
| 晓墨 | 情绪丰富 |
| 晓睿 | 稳重厚实中年 |
| 晓双 | 清脆孩童少女 |
| 晓梦 | 软萌甜妹 |

</td>
<td valign="top">

**👨 男声 (6)**

| 音色 | 特点 |
|---|---|
| 云希 | 清爽阳光少年 |
| 云扬 | 央视浑厚播音 |
| 云健 | 低沉浑厚大叔 |
| 云夏 | 正太少年童声 |
| 云泽 | 苍老沉稳 |
| 云枫 | 平淡务实 |

</td>
<td valign="top">

**🌍 方言 (9)**

| 音色 | 口音 |
|---|---|
| 云彪 / 晓北 | 东北 |
| 云登 | 河南 |
| 云翔 | 山东 |
| 云熙 | 四川 |
| 云奇 | 广西 |
| 晓妮 | 陕西 |
| 云哲 / 晓彤 | 吴语 |

</td>
</tr>
<tr>
<td valign="top">

**🇭🇰 粤语 (3)**

| 音色 | 特点 |
|---|---|
| 晓佳 | 干练港风 |
| 晓蔓 | 温柔成熟 |
| 云龙 | 粤语男性 |

</td>
<td valign="top">

**🇹🇼 台湾腔 (3)**

| 音色 | 特点 |
|---|---|
| 晓晨 | 清甜台妹 |
| 晓雨 | 温柔成熟 |
| 云哲 | 台湾男性 |

</td>
<td valign="top">

**🎵 MiMo TTS (9)**

| 音色 | 特点 |
|---|---|
| 冰糖 | 清甜治愈 |
| 茉莉 | 软糯温柔 |
| 苏打 | 清亮少年 |
| 白桦 | 苍老沉稳 |
| Mia | 活泼英文 |
| Chloe | 冷淡英文 |
| Milo | 阳光英文 |
| Dean | 磁性英文 |

</td>
</tr>
</table>

> 🎧 **试听全部音色**：打开 [`scripts/voice_samples/index.html`](scripts/voice_samples/index.html) 在线试听，支持搜索和分类筛选，一键复制音色名称。

## 📖 Workflow

```mermaid
graph LR
    A[📄 文本输入] --> B[📑 章节拆分]
    B --> C[🔍 角色提取]
    C --> D[🎨 音色匹配]
    D --> E[✅ 用户确认]
    E --> F[🔊 生成音频]
```

| Step | Description |
|---|---|
| **1. 拆分章节** | 按「第X章/回/节」自动拆分，无章节标记则作为单章 |
| **2. 提取角色** | LLM 分析角色性别/年龄/性格/说话风格 |
| **3. 匹配音色** | 根据特征自动匹配最佳音色 |
| **4. 用户确认** | 展示推荐方案，用户可调整 |
| **5. 生成音频** | Edge TTS / MiMo TTS 生成 WAV/MP3 |

## 📁 Structure

```
novel2voice/
├── SKILL.md                           # Agent 指令
├── README.md                          # ← 你在这里
├── .gitignore
├── references/
│   ├── voice-catalog.md               # 完整音色库 + 风格标签
│   ├── mimo-tts-api.md                # MiMo TTS API 文档
│   ├── edge-tts-annotation-guide.md   # Edge TTS 标注指南
│   └── generated-long-body.md         # 长文本处理
└── scripts/
    ├── generate_audiobook.py          # 主生成脚本
    ├── tts_voice.py                   # 单句 TTS
    ├── text_parser.py                 # 文本解析
    ├── subtitle_parser.py             # 字幕解析
    └── voice_samples/
        ├── index.html                 # 🎧 音色试听页面
        └── *.mp3                      # 28 个音色样本
```

## 📚 Documentation

| Document | Description |
|---|---|
| [Voice Catalog](references/voice-catalog.md) | 完整音色库、风格标签、角色映射表 |
| [MiMo TTS API](references/mimo-tts-api.md) | MiMo TTS 三种模型 API 文档 |
| [Edge TTS Guide](references/edge-tts-annotation-guide.md) | Edge TTS 标注规范 |
| [Long Body](references/generated-long-body.md) | 长文本处理扩展说明 |

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| 生成无声音 | 确认 `ffmpeg` 已安装 |
| Edge TTS 连接失败 | 脚本自动切换备用端点 |
| 中文乱码 | 确保文件 UTF-8 编码 |
| 角色识别不准 | 手动调整 `segments.json` |
| 生成太慢 | 使用 `--async --concurrent 5` |

## 📄 License

[MIT](LICENSE)

---

<div align="center">
<sub>Built with ❤️ for novel lovers · Powered by <a href="https://edge.microsoft.com">Edge TTS</a> & <a href="https://mimo.xiaomi.com">MiMo TTS</a></sub>
</div>
