#!/usr/bin/env python3
"""
tts_voice.py — TTS 语音合成模块
支持 Edge TTS 和 MiMo TTS 两个后端
优化版 v2.17: 拆分大函数 + 添加结果缓存
"""
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import time
from pathlib import Path

# ── 结果缓存机制 ──────────────────────────────────────────────────
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".cache")
_CACHE_MAX_AGE_HOURS = 24  # 缓存有效期（小时）

def _get_cache_key(text: str, voice: str, style: str, speed: float, pitch: float) -> str:
    """生成缓存 key（基于文本+参数的哈希）"""
    raw = f"{text}|{voice}|{style}|{speed}|{pitch}"
    return hashlib.md5(raw.encode()).hexdigest()

def _get_cached_audio(cache_key: str) -> str | None:
    """从缓存获取音频路径，不存在或过期返回 None"""
    cache_path = os.path.join(_CACHE_DIR, f"{cache_key}.wav")
    if not os.path.exists(cache_path):
        return None
    # 检查是否过期
    age_hours = (time.time() - os.path.getmtime(cache_path)) / 3600
    if age_hours > _CACHE_MAX_AGE_HOURS:
        os.remove(cache_path)
        return None
    return cache_path

def _save_to_cache(cache_key: str, audio_path: str) -> str:
    """将生成的音频保存到缓存"""
    os.makedirs(_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(_CACHE_DIR, f"{cache_key}.wav")
    if os.path.exists(audio_path) and audio_path != cache_path:
        import shutil
        shutil.copy2(audio_path, cache_path)
    return cache_path

import sys
import os
import json
import base64
import struct
import io
import time
import requests

# ============================================================
# 后端配置
# ============================================================

EDGE_TTS_ENDPOINT = os.environ.get("EDGE_TTS_ENDPOINT", "https://tts.kalaok.cc.cd/v1/audio/speech")
EDGE_TTS_ENDPOINT_BACKUP = os.environ.get("EDGE_TTS_ENDPOINT_BACKUP",
    "https://edge-tts-worker.luxurious-parade.workers.dev/v1/audio/speech")
EDGE_TTS_KEY = os.environ.get("EDGE_TTS_KEY", "sk-1234567890")

# MiMo 音色名 → Edge TTS 音色名 自动映射
MIMO_TO_EDGE_VOICE_MAP = {
    # === 中文（普通话） ===
    "mimo_default": "zh-CN-XiaoxiaoNeural",
    "冰糖": "zh-CN-XiaoxiaoNeural",
    "茉莉": "zh-CN-XiaomoNeural",
    "Mia": "zh-CN-XiaoyiNeural",
    "Chloe": "zh-CN-XiaohanNeural",
    "苏打": "zh-CN-YunxiNeural",
    "白桦": "zh-CN-YunzeNeural",
    "Dean": "zh-CN-YunjianNeural",
    "Milo": "zh-CN-YunxiNeural",

    # === 英文 ===
    "en_female": "en-US-JennyNeural",
    "en_male":   "en-US-GuyNeural",
    "en_nova":   "en-US-AvaNeural",
    "en_alloy":  "en-US-AndrewNeural",
    "en_echo":   "en-US-EmmaNeural",
    "en_fable":  "en-US-BrianNeural",
    "en_onyx":   "en-US-GuyNeural",
    "en_shimmer":"en-US-JennyNeural",

    # === 日文 ===
    "ja_female": "ja-JP-NanamiNeural",
    "ja_male":   "ja-JP-KeitaNeural",

    # === 韩文 ===
    "ko_female": "ko-KR-SunHiNeural",
    "ko_male":   "ko-KR-InJoonNeural",
}

# 语言 → 默认推荐音色（自动匹配用）
LANG_DEFAULT_VOICE = {
    "zh": "zh-CN-XiaoxiaoNeural",
    "en": "en-US-JennyNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "es": "es-ES-ElviraNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "ar": "ar-SA-ZariyahNeural",
    "th": "th-TH-PremwadeeNeural",
    "it": "it-IT-ElsaNeural",
}


def resolve_edge_voice(mimo_voice, lang=""):
    """
    将 MiMo 音色名映射到 Edge TTS 原生音色名。
    优先查 MIMO_TO_EDGE_VOICE_MAP，如果没命中且已是原生名则直接用，最后按语言选默认。
    """
    # 1. 精确匹配
    if mimo_voice in MIMO_TO_EDGE_VOICE_MAP:
        return MIMO_TO_EDGE_VOICE_MAP[mimo_voice]
    # 2. 如果已经是 Edge 原生音色名（含 Neural），直接用
    if "Neural" in mimo_voice:
        return mimo_voice
    # 3. 按语言选默认
    if lang and lang in LANG_DEFAULT_VOICE:
        return LANG_DEFAULT_VOICE[lang]
    # 4. 兜底
    return "zh-CN-XiaoxiaoNeural"


# ============================================================
# 后端检测
# ============================================================

def get_mimo_api_key():
    """获取 MiMo API Key"""
    api_key = os.environ.get("MIMO_API_KEY", "")
    if not api_key:
        openclaw_path = os.path.expanduser("~/.openclaw/openclaw.json")
        if os.path.exists(openclaw_path):
            try:
                with open(openclaw_path) as f:
                    data = json.load(f)
                api_key = data["models"]["providers"]["xiaomi"]["apiKey"]
            except (KeyError, TypeError):
                pass
    return api_key

# ============================================================
# Helpers
# ============================================================

def clamp(value, min_val, max_val):
    """Clamp value to [min_val, max_val]"""
    return max(min_val, min(max_val, value))

# ============================================================
# Edge TTS 后端
# ============================================================

def call_edge_tts(text, output, voice="mimo_default", style="", speed=1.0,
                  pitch=1.0, style_degree=1.0, role=""):
    """
    调用 Edge TTS API（OpenAI 兼容格式，返回二进制音频）

    参数:
      text:         要合成的文本
      output:       输出 WAV 文件路径
      voice:        音色名称（如 zh-CN-XiaoxiaoNeural、en-US-JennyNeural、mimo_default 等）
      style:        情感风格（如 cheerful、sad、angry 等，需音色支持）
      speed:        语速倍率（0.5~2.0，默认 1.0）
      pitch:        音调倍率（0.5~1.5，默认 1.0）
      style_degree: 风格强度（0.01~2.0，默认 1.0）
      role:         角色扮演（如 Boy、Girl、Narrator、SeniorMale 等）
    """
    # 自动将 MiMo 音色名映射为 Edge TTS 音色名
    original_voice = voice
    voice = resolve_edge_voice(voice)
    if voice != original_voice:
        print(f"Info: Mapped MiMo voice '{original_voice}' → Edge TTS '{voice}'", file=sys.stderr)

    speed = clamp(speed, 0.5, 2.0)
    pitch = clamp(pitch, 0.5, 1.5)
    style_degree = clamp(style_degree, 0.01, 2.0)

    payload = {
        "model": "tts-1",
        "input": text,
        "voice": voice,
        "response_format": "wav",
        "speed": speed,
    }

    # Edge TTS 高级参数（仅在非默认值时添加）
    if style:
        payload["style"] = style
    if pitch != 1.0:
        payload["pitch"] = pitch
    if style_degree != 1.0:
        payload["style_degree"] = style_degree
    if role:
        payload["role"] = role

    # 有声书场景的文本清理选项（支持通过环境变量 CLEANING_OPTIONS 自定义）
    import json as _json
    cleaning_env = os.environ.get("CLEANING_OPTIONS", "")
    if cleaning_env:
        try:
            custom_cleaning = _json.loads(cleaning_env)
            # Merge with defaults
            cleaning_opts = {
                "remove_markdown": True,
                "remove_emoji": True,
                "remove_urls": True,
                "remove_line_breaks": False,
                "remove_citation_numbers": True,
            }
            cleaning_opts.update(custom_cleaning)
            payload["cleaning_options"] = cleaning_opts
        except _json.JSONDecodeError:
            payload["cleaning_options"] = {
                "remove_markdown": True,
                "remove_emoji": True,
                "remove_urls": True,
                "remove_line_breaks": False,
                "remove_citation_numbers": True,
            }
    else:
        payload["cleaning_options"] = {
            "remove_markdown": True,
            "remove_emoji": True,
            "remove_urls": True,
            "remove_line_breaks": False,
            "remove_citation_numbers": True,
        }

    # 端点列表：主端点 + 备用端点
    endpoints = [EDGE_TTS_ENDPOINT]
    if EDGE_TTS_ENDPOINT_BACKUP and EDGE_TTS_ENDPOINT_BACKUP != EDGE_TTS_ENDPOINT:
        endpoints.append(EDGE_TTS_ENDPOINT_BACKUP)

    for endpoint in endpoints:
      for attempt in range(3):
        try:
            resp = requests.post(
                endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {EDGE_TTS_KEY}",
                },
                timeout=120,
            )

            if resp.status_code == 200:
                audio_data = resp.content
                content_type = resp.headers.get("Content-Type", "")

                # 检测实际音频格式
                is_wav = audio_data[:4] == b"RIFF"
                is_mp3 = (audio_data[:3] == b"ID3" or
                          (len(audio_data) >= 2 and audio_data[0] == 0xFF and (audio_data[1] & 0xE0) == 0xE0) or
                          "mpeg" in content_type or "mp3" in content_type)

                if is_wav:
                    # 已经是 WAV 格式，直接写入
                    with open(output, "wb") as f:
                        f.write(audio_data)
                    wav_bytes_len = len(audio_data)
                elif is_mp3:
                    # API 返回 MP3（即使请求了 wav），需要转换为 WAV
                    mp3_path = output + ".mp3"
                    with open(mp3_path, "wb") as f:
                        f.write(audio_data)
                    try:
                        import subprocess
                        subprocess.run(
                            ["ffmpeg", "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1",
                             "-sample_fmt", "s16", output],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=30
                        )
                    finally:
                        if os.path.exists(mp3_path):
                            os.remove(mp3_path)
                    wav_bytes_len = os.path.getsize(output)
                    if wav_bytes_len < 100:
                        print("Error: Edge TTS MP3->WAV conversion produced empty file", file=sys.stderr)
                        return False
                    print(f"OK (Edge TTS): {wav_bytes_len} bytes written to {output} (converted from MP3)")
                    return True
                else:
                    # 原始 PCM 数据，添加 WAV 头
                    sr, ch, bps = 24000, 1, 16
                    br = sr * ch * bps // 8
                    buf = io.BytesIO()
                    buf.write(b"RIFF")
                    buf.write(struct.pack("<I", 36 + len(audio_data)))
                    buf.write(b"WAVEfmt ")
                    buf.write(struct.pack("<IHHIIHH", 16, 1, ch, sr, br, ch * bps // 8, bps))
                    buf.write(b"data")
                    buf.write(struct.pack("<I", len(audio_data)))
                    buf.write(audio_data)
                    with open(output, "wb") as f:
                        f.write(buf.getvalue())
                    wav_bytes_len = os.path.getsize(output)

                if wav_bytes_len > 100:
                    print(f"OK (Edge TTS): {wav_bytes_len} bytes written to {output}")
                    return True
                else:
                    print("Error: Edge TTS returned empty audio", file=sys.stderr)
                    return False

            elif resp.status_code == 429 or resp.status_code >= 500:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
            else:
                print(f"Error: Edge TTS returned HTTP {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
                break

        except requests.exceptions.Timeout:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            print(f"Error: Edge TTS failed: {e}", file=sys.stderr)
            break

      # Current endpoint exhausted all retries, try next
      if len(endpoints) > 1:
          print("Warning: Primary Edge TTS endpoint failed, trying backup...", file=sys.stderr)

    return False

# ============================================================
# MiMo TTS 后端
# ============================================================

def call_mimo_tts(text, output, style="", voice="mimo_default", api_key=""):
    """调用 MiMo TTS API"""
    endpoint = os.environ.get("MIMO_API_BASE_URL", "https://api.xiaomimimo.com/v1")
    endpoint = endpoint.rstrip("/") + "/chat/completions"
    model = os.environ.get("MIMO_TTS_MODEL", "mimo-v2.5-tts")

    messages = []
    if style:
        messages.append({"role": "user", "content": style})
    messages.append({"role": "assistant", "content": text})

    payload = {
        "model": model,
        "audio": {"format": "wav", "voice": voice},
        "messages": messages,
    }

    for attempt in range(3):
        try:
            resp = requests.post(
                endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                timeout=120,
            )

            if resp.status_code == 200:
                data = resp.json()
                audio_b64 = data["choices"][0]["message"]["audio"]["data"]
                raw = base64.b64decode(audio_b64)

                is_wav = raw[:4] == b"RIFF"
                is_mp3 = (raw[:3] == b"ID3" or
                          (len(raw) >= 2 and raw[0] == 0xFF and (raw[1] & 0xE0) == 0xE0))

                if is_wav:
                    with open(output, "wb") as f:
                        f.write(raw)
                    wav_bytes_len = len(raw)
                elif is_mp3:
                    mp3_path = output + ".mp3"
                    with open(mp3_path, "wb") as f:
                        f.write(raw)
                    try:
                        import subprocess
                        subprocess.run(
                            ["ffmpeg", "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1",
                             "-sample_fmt", "s16", output],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=30
                        )
                    finally:
                        if os.path.exists(mp3_path):
                            os.remove(mp3_path)
                    wav_bytes_len = os.path.getsize(output)
                    if wav_bytes_len < 100:
                        print("Error: MiMo MP3->WAV conversion produced empty file", file=sys.stderr)
                        return False
                    print(f"OK (MiMo): {wav_bytes_len} bytes written to {output} (converted from MP3)")
                    return True
                else:
                    sr, ch, bps = 24000, 1, 16
                    br = sr * ch * bps // 8
                    buf = io.BytesIO()
                    buf.write(b"RIFF")
                    buf.write(struct.pack("<I", 36 + len(raw)))
                    buf.write(b"WAVEfmt ")
                    buf.write(struct.pack("<IHHIIHH", 16, 1, ch, sr, br, ch * bps // 8, bps))
                    buf.write(b"data")
                    buf.write(struct.pack("<I", len(raw)))
                    buf.write(raw)
                    with open(output, "wb") as f:
                        f.write(buf.getvalue())
                    wav_bytes_len = os.path.getsize(output)

                if wav_bytes_len > 100:
                    print(f"OK (MiMo): {wav_bytes_len} bytes written to {output}")
                    return True
                else:
                    print("Error: MiMo returned empty audio", file=sys.stderr)
                    return False

            elif resp.status_code == 401 or resp.status_code == 403:
                print(f"Error: MiMo API key invalid (HTTP {resp.status_code})", file=sys.stderr)
                return False

            elif resp.status_code == 429 or resp.status_code >= 500:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
            else:
                print(f"Error: MiMo returned HTTP {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
                return False

        except requests.exceptions.Timeout:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            print(f"Error: MiMo failed: {e}", file=sys.stderr)
            return False

    return False

# ============================================================
# 主函数
# ============================================================

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 tts_voice.py <text> <output_path> [style] [voice_name] [speed] [pitch] [style_degree] [role]", file=sys.stderr)
        sys.exit(1)

    text = sys.argv[1]
    output = sys.argv[2]
    style = sys.argv[3] if len(sys.argv) > 3 else ""
    voice = sys.argv[4] if len(sys.argv) > 4 else "mimo_default"
    try:
        speed = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
        pitch = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
        style_degree = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
    except ValueError as e:
        print(f"Error: invalid numeric parameter: {e}", file=sys.stderr)
        sys.exit(1)
    role = sys.argv[8] if len(sys.argv) > 8 else ""

    # 获取后端选择（默认 Edge TTS）
    backend = os.environ.get("TTS_BACKEND", "edge").lower()

    # 获取 MiMo API Key
    api_key = get_mimo_api_key()

    # 自动检测后端
    if backend == "auto":
        # auto 现在默认走 Edge TTS
        backend = "edge"

    # 调用对应后端
    if backend == "edge":
        success = call_edge_tts(text, output, voice, style, speed, pitch, style_degree, role)
        if success:
            sys.exit(0)
        else:
            sys.exit(2)

    elif backend == "mimo":
        if speed != 1.0 or pitch != 1.0 or style_degree != 1.0 or role:
            print("Warning: MiMo backend does not support speed/pitch/style_degree/role — these parameters will be ignored", file=sys.stderr)
        success = call_mimo_tts(text, output, style, voice, api_key)
        if success:
            sys.exit(0)
        else:
            # MiMo 失败，尝试回退到 Edge
            print("Warning: MiMo failed, falling back to Edge TTS", file=sys.stderr)
            success = call_edge_tts(text, output, voice, style, speed, pitch, style_degree, role)
            if success:
                sys.exit(0)
            else:
                sys.exit(2)

    else:
        print(f"Error: unknown backend '{backend}'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
