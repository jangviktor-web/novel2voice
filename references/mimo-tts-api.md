# MiMo TTS API Reference

## 模型列表

| 模型 | 功能 | 注意事项 |
|---|---|---|
| `mimo-v2.5-tts` | 预置精品音色 | 支持唱歌，不支持音色设计/复刻 |
| `mimo-v2.5-tts-voicedesign` | 文本描述定制音色 | 不支持唱歌/预置音色/复刻 |
| `mimo-v2.5-tts-voiceclone` | 音频样本复刻音色 | 不支持唱歌/预置音色/设计 |

## 通用规则

- 目标文本必须放在 `role: assistant` 的消息中
- `role: user` 的消息为可选参数，用于控制风格（不会被朗读）
- 流式调用时输出格式请指定为 `pcm16`

## 模型 1：mimo-v2.5-tts（预置音色）

```json
{
  "model": "mimo-v2.5-tts",
  "messages": [
    {"role": "user", "content": "风格/语气描述（不会被朗读）"},
    {"role": "assistant", "content": "待合成的目标文本"}
  ],
  "audio": {"format": "wav", "voice": "冰糖"},
  "stream": false
}
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `model` | ✅ | `mimo-v2.5-tts` |
| `messages[0].role` | ✅ | `user` |
| `messages[0].content` | ⚠️ | 风格描述（可选） |
| `messages[1].role` | ✅ | `assistant` |
| `messages[1].content` | ✅ | 待合成文本 |
| `audio.format` | ✅ | `wav` 或 `pcm16` |
| `audio.voice` | ✅ | 预置音色名称 |
| `stream` | ⚠️ | 是否流式，默认 `false` |

## 模型 2：mimo-v2.5-tts-voicedesign（音色设计）

```json
{
  "model": "mimo-v2.5-tts-voicedesign",
  "messages": [
    {"role": "user", "content": "音色描述文本"},
    {"role": "assistant", "content": "待合成的目标文本"}
  ],
  "audio": {"format": "wav", "optimize_text_preview": true}
}
```

音色描述关键维度：性别与年龄、音色/质感、情绪/语气、语速/节奏。
1-4 句即可，避免矛盾特征和音质效果词。

## 模型 3：mimo-v2.5-tts-voiceclone（音色复刻）

```json
{
  "model": "mimo-v2.5-tts-voiceclone",
  "messages": [
    {"role": "user", "content": ""},
    {"role": "assistant", "content": "待合成的目标文本"}
  ],
  "audio": {"format": "wav", "voice": "data:audio/mpeg;base64,{BASE64_AUDIO}"}
}
```

- Base64 大小不超过 10 MB
- 仅支持 mp3 和 wav 格式
- 前缀：`data:{MIME_TYPE};base64,$BASE64_AUDIO`

## Python 非流式调用示例

```python
import os, base64
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["MIMO_API_KEY"],
    base_url="https://api.xiaomimimo.com/v1"
)

completion = client.chat.completions.create(
    model="mimo-v2.5-tts",
    messages=[
        {"role": "user", "content": "温柔、深情的语气"},
        {"role": "assistant", "content": "(悲伤)[叹气]对不起，我来晚了。"}
    ],
    audio={"format": "wav", "voice": "冰糖"}
)

audio_bytes = base64.b64decode(completion.choices[0].message.audio.data)
with open("output.wav", "wb") as f:
    f.write(audio_bytes)
```

## 计费

当前状态：**限时免费**。查看账单：控制台 → 账单明细。
