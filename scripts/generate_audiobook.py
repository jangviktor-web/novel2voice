#!/usr/bin/env python3
"""
generate_audiobook.py — 小说有声书生成引擎 v2.9
支持：自动文本解析、情感参数计算、异步并发、断点续传、详细日志、字幕转语音

Usage:
  # 从 segments.json 生成（传统模式）
  python3 generate_audiobook.py segments.json output_dir

  # 从原始小说文本生成（自动解析模式）
  python3 generate_audiobook.py --auto novel.txt output_dir

  # 字幕文件转语音（按时间轴对齐）
  python3 generate_audiobook.py --subtitle subtitle.srt output_dir
  python3 generate_audiobook.py --subtitle subtitle.ass output_dir --speaker-voices '{"旁白":"冰糖","张三":"Dean"}'

  # 断点续传
  python3 generate_audiobook.py segments.json output_dir --skip-existing
"""
import subprocess
import os
import sys
import struct
import json
import argparse
import time
import asyncio
from datetime import datetime

# 同目录下的模块
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

try:
    from text_parser import parse_novel, Segment, CharacterProfile
    HAS_PARSER = True
except ImportError:
    HAS_PARSER = False

try:
    from param_calculator import ParamCalculator
    HAS_CALC = True
except ImportError:
    HAS_CALC = False

try:
    from subtitle_parser import (
        parse_subtitle, get_speakers, entries_to_segments,
        detect_language, detect_overlaps, fix_overlaps, entries_to_srt,
        ms_to_srt_time,
    )
    HAS_SUBTITLE = True
except ImportError:
    HAS_SUBTITLE = False


# ============================================================
# 依赖检查
# ============================================================

def _check_dependencies():
    """启动时检查必要依赖"""
    import shutil
    missing = []
    if not shutil.which('ffmpeg'):
        missing.append('ffmpeg')
    if not shutil.which('ffprobe'):
        missing.append('ffprobe')
    if missing:
        print(f"Error: 缺少必要依赖: {', '.join(missing)}", file=sys.stderr)
        print(f"  请安装: apt install {' '.join(missing)}  或  brew install {' '.join(missing)}", file=sys.stderr)
        sys.exit(1)

_check_dependencies()


# ============================================================
# 配置持久化
# ============================================================

SKILL_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(SKILL_CONFIG_DIR, ".env")


def load_config():
    """从 skill 目录的 .env 文件加载配置"""
    config = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, _, value = line.partition('=')
                        config[key.strip()] = value.strip()
        except Exception:
            pass
    return config


def save_config(mimo_key=None, edge_key=None):
    """保存 API key 到 skill 目录的 .env 文件。
    只更新传入的 key，保留已有的其他 key。
    """
    config = load_config()
    if mimo_key is not None:
        config["MIMO_API_KEY"] = mimo_key
    if edge_key is not None:
        config["EDGE_TTS_API_KEY"] = edge_key
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    return config


# ============================================================
# TTS 后端检测
# ============================================================

def get_mimo_api_key():
    """获取 MiMo API Key，按优先级查找：
    1. 环境变量 MIMO_API_KEY
    2. ~/.openclaw/openclaw.json
    3. skill 本地 .env 配置
    """
    api_key = os.environ.get("MIMO_API_KEY", "")
    if api_key:
        return api_key

    # 检查 openclaw 配置
    openclaw_path = os.path.expanduser("~/.openclaw/openclaw.json")
    if os.path.exists(openclaw_path):
        try:
            with open(openclaw_path) as f:
                data = json.load(f)
            api_key = data["models"]["providers"]["xiaomi"]["apiKey"]
            if api_key:
                return api_key
        except (KeyError, TypeError, json.JSONDecodeError):
            pass

    # 检查 skill 本地 .env
    config = load_config()
    api_key = config.get("MIMO_API_KEY", "")
    return api_key


def resolve_tts_backend(cli_backend=None):
    """
    解析 TTS 后端选择。默认使用 Edge TTS。
    返回: ("mimo"|"edge", warning_message|None)
    """
    backend = (cli_backend or os.environ.get("TTS_BACKEND", "edge")).lower()

    if backend == "auto":
        # auto 现在默认走 Edge TTS
        backend = "edge"
    elif backend == "mimo":
        api_key = get_mimo_api_key()
        if not api_key:
            return "edge", "MiMo API key not found, falling back to Edge TTS"
    # edge or explicit mimo — return as-is
    return backend, None


# ============================================================
# TTS 生成
# ============================================================

def normalize_text(text):
    """TTS 文本规范化"""
    text = text.replace("**", "").replace("`", "").replace("#", "").strip()
    if text.startswith("#"):
        text = text.lstrip("#").strip()
    return text


def generate_segment(tts_script, text, style, voice, out_path, max_retries=3, tts_backend=None,
                     speed=1.0, pitch=1.0, style_degree=1.0, role="", cleaning_options=None):
    """生成单个 WAV 段落（同步）"""
    if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
        return True
    norm_text = normalize_text(text)
    if not norm_text:
        return False

    # 优先用 Python TTS（避免 shell 编码问题）
    tts_python = tts_script.replace(".sh", ".py") if tts_script.endswith(".sh") else tts_script
    if not os.path.exists(tts_python):
        tts_python = os.path.join(script_dir, "tts_voice.py")

    env = os.environ.copy()
    if tts_backend:
        env["TTS_BACKEND"] = tts_backend
    if cleaning_options:
        import json as _json
        env["CLEANING_OPTIONS"] = _json.dumps(cleaning_options)

    # 构建 CLI 参数：text, output, style, voice, speed, pitch, style_degree, role
    extra_args = [str(speed), str(pitch), str(style_degree)]
    if role:
        extra_args.append(role)

    for attempt in range(max_retries):
        if os.path.exists(tts_python):
            cmd = [sys.executable, tts_python, norm_text, out_path, style, voice] + extra_args
        else:
            cmd = ["bash", tts_script, norm_text, out_path, style, voice] + extra_args
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                print(f"    FAILED: TTS timeout after 120s", file=sys.stderr)
                continue
        if r.returncode == 0:
            return True
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)
        else:
            print(f"    FAILED: {r.stderr[:100]}", file=sys.stderr)
    return False


async def generate_segment_async(tts_script, text, style, voice, out_path, semaphore, max_retries=3,
                                  tts_backend=None, speed=1.0, pitch=1.0, style_degree=1.0,
                                  role="", cleaning_options=None):
    """生成单个 WAV 段落（异步）"""
    if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
        return True
    norm_text = normalize_text(text)
    if not norm_text:
        return False

    tts_python = tts_script.replace(".sh", ".py") if tts_script.endswith(".sh") else tts_script
    if not os.path.exists(tts_python):
        tts_python = os.path.join(script_dir, "tts_voice.py")

    env = os.environ.copy()
    if tts_backend:
        env["TTS_BACKEND"] = tts_backend
    if cleaning_options:
        import json as _json
        env["CLEANING_OPTIONS"] = _json.dumps(cleaning_options)

    extra_args = [str(speed), str(pitch), str(style_degree)]
    if role:
        extra_args.append(role)

    async with semaphore:
        for attempt in range(max_retries):
            if os.path.exists(tts_python):
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, tts_python, norm_text, out_path, style, voice, *extra_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    "bash", tts_script, norm_text, out_path, style, voice, *extra_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    print(f"    FAILED: TTS timeout after 120s", file=sys.stderr)
                    return False
            if proc.returncode == 0:
                return True
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                print(f"    FAILED: {stderr.decode()[:100]}", file=sys.stderr)
    return False


# ============================================================
# 音频拼接
# ============================================================

def concat_wavs(files, out_path, pause_ms=400, per_file_pauses=None):
    """拼接多个 WAV 文件（使用 wave 模块确保兼容性）"""
    import wave
    
    if not files:
        return 0.0
    
    # 读取第一个文件获取音频参数
    with wave.open(files[0], 'rb') as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
    
    # 使用 wave 模块正确合并所有文件
    with wave.open(out_path, 'wb') as out_wf:
        out_wf.setframerate(sample_rate)
        out_wf.setnchannels(channels)
        out_wf.setsampwidth(sample_width)
        
        for i, fh in enumerate(files):
            with wave.open(fh, 'rb') as in_wf:
                out_wf.writeframes(in_wf.readframes(in_wf.getnframes()))
            
            # 添加停顿（静音）
            if i < len(files) - 1:
                pause = per_file_pauses[i] if per_file_pauses and i < len(per_file_pauses) else pause_ms
                if pause > 0:
                    silence_frames = int(sample_rate * pause / 1000)
                    silence = b'\x00' * (silence_frames * channels * sample_width)
                    out_wf.writeframes(silence)
    
    # 计算总时长
    with wave.open(out_path, 'rb') as wf:
        total_frames = wf.getnframes()
        duration = total_frames / sample_rate
    
    return duration


def to_mp3(wav_path, mp3_path):
    """WAV → MP3"""
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", "192k", mp3_path],
        capture_output=True, text=True, timeout=120
    )
    if r.returncode != 0:
        print(f"Warning: ffmpeg MP3 conversion failed: {r.stderr[:200] if r.stderr else 'unknown error'}", file=sys.stderr)
        return False
    return True


def normalize_loudness(wav_path, target_lufs=-16):
    """WAV 响度归一化（两遍 EBU R128），自动调大或调小音量到目标响度。

    使用两遍处理：第一遍测量响度并计算增益，第二遍应用线性增益 + loudnorm 微调。
    适用于极安静的 TTS 音频（如 -60 LUFS 级别）。

    Args:
        wav_path: WAV 文件路径（原地修改）
        target_lufs: 目标响度（LUFS），默认 -16，适合语音内容
    """
    tmp_path = wav_path + ".norm_tmp.wav"
    tmp2_path = wav_path + ".norm_tmp2.wav"

    # 第一遍：测量当前响度
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", wav_path,
             "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=120
        )
        # 从 stderr 提取 JSON 测量结果
        import re
        json_match = re.search(r'\{[^}]+\}', r.stderr, re.DOTALL)
        if not json_match:
            print(f"  [WARN] 响度测量失败，跳过归一化", file=sys.stderr)
            return False
        measured = json.loads(json_match.group())
        input_i = float(measured.get("input_i", -70))
        print(f"  [INFO] 当前响度: {input_i:.1f} LUFS, 目标: {target_lufs} LUFS")
    except Exception as e:
        print(f"  [WARN] 响度测量异常: {e}，跳过归一化", file=sys.stderr)
        return False

    # 计算需要的线性增益（dB）
    gain_db = target_lufs - input_i
    # 限制增益范围，防止过度放大底噪
    gain_db = max(-20, min(gain_db, 60))
    gain_factor = 10 ** (gain_db / 20)

    print(f"  [INFO] 应用增益: {gain_db:.1f} dB (x{gain_factor:.1f})")

    # 第二遍：先应用线性增益，再 loudnorm 微调
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path,
             "-af", f"volume={gain_factor}:precision=float,loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
             "-ar", "24000", "-ac", "1", "-sample_fmt", "s16",
             tmp_path],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 100:
            os.replace(tmp_path, wav_path)
            print(f"  [INFO] 响度归一化完成 (target: {target_lufs} LUFS)")
            return True
        else:
            print(f"  [WARN] 响度归一化失败，保留原始音量", file=sys.stderr)
            return False
    except subprocess.TimeoutExpired:
        print(f"  [WARN] 响度归一化超时，保留原始音量", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  [WARN] 响度归一化异常: {e}", file=sys.stderr)
        return False
    finally:
        for p in [tmp_path, tmp2_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


def get_wav_duration_ms(wav_path: str) -> int:
    """获取 WAV 文件时长（毫秒）"""
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
         '-of', 'csv=p=0', wav_path],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0 and result.stdout.strip():
        return int(float(result.stdout.strip()) * 1000)
    return 0


def speed_up_wav(input_path: str, output_path: str, speed: float):
    """
    加速 WAV 音频文件。speed > 1.0 表示加速，最高支持 4.0x（链式 atempo）。
    使用 ffmpeg atempo 滤镜，atempo 单次支持 0.5~2.0，超出需链式调用。
    """
    if speed <= 1.0:
        if input_path != output_path:
            import shutil
            shutil.copy2(input_path, output_path)
        return

    filters = []
    remaining = min(speed, 4.0)
    while remaining > 2.0:
        filters.append('atempo=2.0')
        remaining /= 2.0
    filters.append(f'atempo={remaining:.4f}')
    filter_str = ','.join(filters)

    r = subprocess.run(
        ['ffmpeg', '-y', '-i', input_path, '-af', filter_str,
         '-ar', str(SAMPLE_RATE), '-ac', str(CHANNELS), output_path],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        print(f"Warning: ffmpeg speed adjustment failed: {r.stderr[:200] if r.stderr else 'unknown error'}", file=sys.stderr)
        return False
    return True


def speed_adjust_segments(wav_files: list, timeline: list, seg_dir: str, max_speed: float = 2.0) -> list:
    """
    语速适配：将 TTS 音频加速到字幕时间槽内。
    如果 TTS 音频时长超过字幕时长，自动加速处理。
    超过 max_speed 仍放不下的，保持 max_speed（略微溢出）。

    返回: 适配后的 WAV 文件路径列表（可能已替换为加速版本）
    """
    if not wav_files or not timeline:
        return wav_files

    adjusted = []
    sped_count = 0
    overflow_count = 0
    sped_dir = os.path.join(os.path.dirname(seg_dir), 'segments_sped')
    os.makedirs(sped_dir, exist_ok=True)

    for i, wav_path in enumerate(wav_files):
        if i >= len(timeline) or not os.path.exists(wav_path):
            adjusted.append(wav_path)
            continue

        sub_duration_ms = timeline[i].get('duration_ms', 0)
        if sub_duration_ms <= 0:
            adjusted.append(wav_path)
            continue

        tts_duration_ms = get_wav_duration_ms(wav_path)
        if tts_duration_ms <= 0:
            adjusted.append(wav_path)
            continue

        if tts_duration_ms <= sub_duration_ms:
            adjusted.append(wav_path)
            continue

        speed = tts_duration_ms / sub_duration_ms
        speed = min(speed, max_speed)

        sped_path = os.path.join(sped_dir, f'sub_{i:04d}.wav')
        speed_up_wav(wav_path, sped_path, speed)

        if os.path.exists(sped_path) and os.path.getsize(sped_path) > 100:
            adjusted.append(sped_path)
            sped_count += 1
            if speed >= max_speed:
                overflow_count += 1
        else:
            adjusted.append(wav_path)

    if sped_count > 0:
        print(f"  [INFO] 语速适配: {sped_count}/{len(wav_files)} 条加速处理")
        if overflow_count > 0:
            print(f"  [WARN] {overflow_count} 条即使 {max_speed}x 加速仍略超时")

    return adjusted


# ============================================================
# 字幕时间轴对齐音频合并
# ============================================================

SAMPLE_RATE = 24000
CHANNELS = 1
BITS_PER_SAMPLE = 16
BYTES_PER_SAMPLE = BITS_PER_SAMPLE // 8
BYTE_RATE = SAMPLE_RATE * CHANNELS * BYTES_PER_SAMPLE


def make_wav_header(data_size: int) -> bytes:
    """构建 WAV 文件头"""
    header = bytearray(44)
    # RIFF header
    header[0:4] = b'RIFF'
    struct.pack_into('<I', header, 4, 36 + data_size)
    header[8:12] = b'WAVE'
    # fmt chunk
    header[12:16] = b'fmt '
    struct.pack_into('<I', header, 16, 16)  # chunk size
    struct.pack_into('<H', header, 20, 1)   # PCM format
    struct.pack_into('<H', header, 22, CHANNELS)
    struct.pack_into('<I', header, 24, SAMPLE_RATE)
    struct.pack_into('<I', header, 28, BYTE_RATE)
    struct.pack_into('<H', header, 32, CHANNELS * BYTES_PER_SAMPLE)
    struct.pack_into('<H', header, 34, BITS_PER_SAMPLE)
    # data chunk
    header[36:40] = b'data'
    struct.pack_into('<I', header, 40, data_size)
    return bytes(header)


def read_wav_data(wav_path: str) -> bytes:
    """读取 WAV 文件的音频数据（跳过44字节头）"""
    with open(wav_path, 'rb') as f:
        f.read(44)  # skip header
        return f.read()


def make_silence(duration_ms: int) -> bytes:
    """生成指定时长的静音数据"""
    num_samples = int(SAMPLE_RATE * duration_ms / 1000)
    return b'\x00' * (num_samples * CHANNELS * BYTES_PER_SAMPLE)


def merge_with_timeline(wav_files: list, output_wav: str, timeline: list) -> float:
    """
    按时间轴合并音频文件

    wav_files: 生成的 WAV 文件路径列表（按顺序）
    timeline: 每条字幕的时间信息 [{"start_ms": ..., "end_ms": ..., "duration_ms": ...}, ...]
    返回: 总时长（秒）
    """
    # 计算总时长
    if not timeline:
        return 0.0
    total_duration_ms = max(t["end_ms"] for t in timeline)

    # 预分配音频缓冲区
    total_samples = int(SAMPLE_RATE * total_duration_ms / 1000)
    total_bytes = total_samples * CHANNELS * BYTES_PER_SAMPLE
    audio_buffer = bytearray(total_bytes)

    # 将每条音频放置到正确的时间位置
    for i, wav_path in enumerate(wav_files):
        if i >= len(timeline):
            break
        if not os.path.exists(wav_path):
            continue

        audio_data = read_wav_data(wav_path)
        if not audio_data:
            continue

        # 计算放置位置（按字幕开始时间）
        start_ms = timeline[i]["start_ms"]
        start_byte = int(start_ms * BYTE_RATE / 1000)
        start_byte = (start_byte // (CHANNELS * BYTES_PER_SAMPLE)) * (CHANNELS * BYTES_PER_SAMPLE)

        # 确保不越界
        available_bytes = total_bytes - start_byte
        copy_bytes = min(len(audio_data), available_bytes)
        if copy_bytes > 0:
            audio_buffer[start_byte:start_byte + copy_bytes] = audio_data[:copy_bytes]

    # 写入文件
    with open(output_wav, 'wb') as f:
        f.write(make_wav_header(len(audio_buffer)))
        f.write(bytes(audio_buffer))

    return total_duration_ms / 1000.0


def merge_with_timeline_fast(wav_files: list, output_wav: str, timeline: list) -> float:
    """
    快速版时间轴合并：使用 ffmpeg 的 adelay 滤镜
    比内存版更省内存，适合长字幕文件
    """
    if not wav_files or not timeline:
        return 0.0

    total_duration_ms = max(t["end_ms"] for t in timeline)
    total_duration_s = total_duration_ms / 1000.0

    # 构建 ffmpeg 命令：为每个输入添加延迟
    cmd = ["ffmpeg", "-y"]

    # 添加所有输入
    for wav_path in wav_files:
        if os.path.exists(wav_path):
            cmd.extend(["-i", wav_path])

    # 构建 filter_complex
    filters = []
    for i, t in enumerate(timeline):
        if i >= len(wav_files) or not os.path.exists(wav_files[i]):
            continue
        delay_ms = t["start_ms"]
        filters.append(f"[{i}:a]adelay={delay_ms}|{delay_ms},apad=whole_dur={total_duration_s}[a{i}]")

    if not filters:
        # 没有有效输入，生成静音
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i",
               f"anullsrc=r={SAMPLE_RATE}:cl=mono",
               "-t", str(total_duration_s),
               "-acodec", "pcm_s16le",
               output_wav]
        subprocess.run(cmd, capture_output=True, timeout=300)
        return total_duration_s

    # 混合所有延迟后的音频
    mix_inputs = "".join(f"[a{i}]" for i in range(len(filters)))
    filters.append(f"{mix_inputs}amix=inputs={len(filters)}:duration=longest:dropout_transition=0[out]")
    filter_str = ";".join(filters)

    cmd.extend(["-filter_complex", filter_str, "-map", "[out]",
                "-acodec", "pcm_s16le", "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
                output_wav])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"ffmpeg merge failed: {result.stderr[:200]}", file=sys.stderr)
        # 回退到内存版
        return merge_with_timeline(wav_files, output_wav, timeline)

    return total_duration_s


# ============================================================
# 自动解析模式
# ============================================================

def auto_parse_to_segments(novel_text, character_voice_map=None, tts_backend="edge"):
    """
    自动解析小说文本为 segments.json 格式
    character_voice_map: {角色名: voice_id} 可选的手动音色覆盖
    tts_backend: "edge" 或 "mimo"，影响默认音色
    """
    if not HAS_PARSER:
        print("Error: text_parser.py not found", file=sys.stderr)
        sys.exit(1)

    segments, characters = parse_novel(novel_text)

    # v2.13: 根据 TTS 后端选择默认音色
    if tts_backend == "mimo":
        narrator_voice = "mimo_default"
        male_voices = ["Dean", "Milo"]
        female_voices = ["冰糖", "茉莉", "Mia", "Chloe", "苏打", "白桦"]
    else:
        # Edge TTS 默认音色
        narrator_voice = "zh-CN-XiaoxiaoNeural"
        male_voices = ["zh-CN-YunxiNeural", "zh-CN-YunjianNeural", "zh-CN-YunyangNeural"]
        female_voices = ["zh-CN-XiaoyiNeural", "zh-CN-XiaohanNeural", "zh-CN-XiaomoNeural"]

    # 默认音色分配
    default_voices = {
        "narrator": narrator_voice,
    }
    male_idx, female_idx = 0, 0

    for name, char in characters.items():
        if name == "narrator":
            continue
        if character_voice_map and name in character_voice_map:
            char.voice_id = character_voice_map[name]
        elif char.gender == "male":
            char.voice_id = male_voices[male_idx % len(male_voices)]
            male_idx += 1
        elif char.gender == "female":
            char.voice_id = female_voices[female_idx % len(female_voices)]
            female_idx += 1
        else:
            # 未知性别，使用童声（较中性，适合不确定年龄/性别的角色）
            char.voice_id = "zh-CN-YunxiaNeural"
        default_voices[name] = char.voice_id

    # 构建 voices 和 styles
    voices = {}
    styles = {}
    for name, char in characters.items():
        voices[name] = char.voice_id
        if char.voice_style:
            styles[name] = char.voice_style
        elif name == "narrator":
            styles[name] = "温柔女声 语速适中 情感丰富 讲故事"
        else:
            styles[name] = ""
    # v2.13: 覆盖 narrator 音色为当前后端的默认音色
    voices["narrator"] = narrator_voice

    # 构建 chapters（按 chapter_title 分割）
    chapters = []
    current_chapter = {"title": "第一章", "segments": []}
    for seg in segments:
        if seg.segment_type == "chapter_title" and current_chapter["segments"]:
            chapters.append(current_chapter)
            current_chapter = {"title": seg.text, "segments": []}

        seg_dict = {
            "text": seg.text,
            "char": "narrator" if seg.character_name in ("__unknown__", "旁白", "narrator") else seg.character_name,
            "pause_after": seg.pause_after,
        }
        if seg.emotion != "neutral":
            seg_dict["emotion"] = seg.emotion
        current_chapter["segments"].append(seg_dict)

    if current_chapter["segments"]:
        chapters.append(current_chapter)

    return {
        "title": "audiobook",
        "voices": voices,
        "styles": styles,
        "chapters": chapters,
        "_characters": {name: {
            "character_id": c.character_id,
            "gender": c.gender,
            "mention_count": c.mention_count,
        } for name, c in characters.items()},
    }


# ============================================================
# 异步批量生成
# ============================================================

async def _async_batch_generate(tasks_info, semaphore):
    """
    异步批量生成 TTS 段落。
    tasks_info: list of (tts_script, text, style, voice, seg_path, kwargs_dict)
    返回: list of bool (success/fail)
    """
    coros = []
    for tts_script, text, style, voice, seg_path, kwargs in tasks_info:
        coros.append(generate_segment_async(
            tts_script, text, style, voice, seg_path, semaphore, **kwargs
        ))
    return await asyncio.gather(*coros, return_exceptions=True)


# ============================================================
# 主生成逻辑
# ============================================================

def run_generation(tts_script, data, output_dir, args, tts_backend=None):
    """执行生成流程"""
    title = data.get("title", "audiobook")
    voices = data.get("voices", {"narrator": "mimo_default"})
    styles = data.get("styles", {"narrator": ""})
    chapters = data.get("chapters", [])

    os.makedirs(output_dir, exist_ok=True)
    seg_dir = os.path.join(output_dir, "segments")
    os.makedirs(seg_dir, exist_ok=True)

    total_segments = sum(len(ch.get("segments", [])) for ch in chapters)
    failed_segments = []
    generation_log = []

    backend_label = tts_backend or "auto"
    print(f"{'='*60}")
    print(f"Title: {title}")
    print(f"TTS Backend: {backend_label}")
    print(f"Chapters: {len(chapters)}")
    print(f"Total segments: {total_segments}")
    print(f"Voice mapping:")
    for char, voice in voices.items():
        print(f"  {char}: {voice}")
    print(f"{'='*60}")

    chapter_files = []
    seg_idx_global = 0

    for ci, chapter in enumerate(chapters):
        ch_title = chapter.get("title", f"Chapter {ci+1}")
        segments = chapter.get("segments", [])
        print(f"\n{'='*60}")
        print(f"Chapter {ci+1}: {ch_title} — {len(segments)} segments")
        print(f"{'='*60}")

        wav_files = []
        pause_afters = []

        # 检查是否启用异步模式
        use_async = getattr(args, 'async_mode', False)

        if use_async:
            # 异步并发模式：批量生成整个 chapter 的所有 segments
            concurrent_count = getattr(args, 'concurrent', 5)
            semaphore = asyncio.Semaphore(concurrent_count)
            tasks_info = []

            for si, seg in enumerate(segments):
                text = seg["text"]
                char = seg.get("char", "narrator")
                style_override = seg.get("style", "")
                emotion = seg.get("emotion", "neutral")
                pause_after = seg.get("pause_after", args.pause_ms)

                seg_speed = seg.get("speed", 1.0)
                seg_pitch = seg.get("pitch", 1.0)
                seg_style_degree = seg.get("style_degree", 1.0)
                seg_role = seg.get("role", "")
                seg_cleaning = seg.get("cleaning_options", None)

                voice = voices.get(char, "mimo_default")
                base_style = style_override if style_override else styles.get(char, "")

                if HAS_CALC and emotion != "neutral":
                    style = ParamCalculator.build_style(base_style, emotion, "medium")
                else:
                    style = base_style

                seg_path = os.path.join(seg_dir, f"ch{ci}_{si:04d}.wav")
                kwargs = {
                    "max_retries": 3,
                    "tts_backend": tts_backend,
                    "speed": seg_speed,
                    "pitch": seg_pitch,
                    "style_degree": seg_style_degree,
                    "role": seg_role,
                    "cleaning_options": seg_cleaning,
                }
                tasks_info.append((tts_script, text, style, voice, seg_path, kwargs))

            print(f"  [INFO] Async mode: {len(tasks_info)} segments, concurrent={concurrent_count}")
            results = asyncio.run(_async_batch_generate(tasks_info, semaphore))

            for si, (result, seg) in enumerate(zip(results, segments)):
                seg_path = tasks_info[si][4]
                pause_after = seg.get("pause_after", args.pause_ms)
                char = seg.get("char", "narrator")
                voice = voices.get(char, "mimo_default")
                text = seg["text"]

                log_entry = {
                    "segment_id": f"ch{ci}_{si:04d}",
                    "character": char,
                    "voice": voice,
                    "emotion": seg.get("emotion", "neutral"),
                    "duration_s": 0,
                    "timestamp": datetime.now().isoformat(),
                }

                if result is True or (isinstance(result, Exception) is False and result):
                    wav_files.append(seg_path)
                    pause_afters.append(pause_after)
                    log_entry["status"] = "success"
                else:
                    failed_segments.append(f"ch{ci}_{si:04d}")
                    log_entry["status"] = "failed"

                generation_log.append(log_entry)
                seg_idx_global += 1

        else:
            # 同步模式（原有逻辑）
            for si, seg in enumerate(segments):
                text = seg["text"]
                char = seg.get("char", "narrator")
                style_override = seg.get("style", "")
                emotion = seg.get("emotion", "neutral")
                pause_after = seg.get("pause_after", args.pause_ms)

                # Edge TTS 扩展参数（per-segment 覆盖）
                seg_speed = seg.get("speed", 1.0)
                seg_pitch = seg.get("pitch", 1.0)
                seg_style_degree = seg.get("style_degree", 1.0)
                seg_role = seg.get("role", "")
                seg_cleaning = seg.get("cleaning_options", None)

                voice = voices.get(char, "mimo_default")
                base_style = style_override if style_override else styles.get(char, "")

                # 使用参数计算器
                if HAS_CALC and emotion != "neutral":
                    style = ParamCalculator.build_style(base_style, emotion, "medium")
                else:
                    style = base_style

                seg_path = os.path.join(seg_dir, f"ch{ci}_{si:04d}.wav")
                # Encode to GBK with replacement for console output
                try:
                    safe_text = text[:35].encode('gbk', errors='replace').decode('gbk')
                    safe_char = char.encode('gbk', errors='replace').decode('gbk')
                except:
                    safe_text = text[:35]
                    safe_char = char
                print(f"[{si+1}/{len(segments)}] {safe_char}({voice}): {safe_text}...")

                start_time = time.time()
                success = generate_segment(tts_script, text, style, voice, seg_path, max_retries=3, tts_backend=tts_backend,
                                           speed=seg_speed, pitch=seg_pitch, style_degree=seg_style_degree, role=seg_role,
                                           cleaning_options=seg_cleaning)
                elapsed = time.time() - start_time

                log_entry = {
                    "segment_id": f"ch{ci}_{si:04d}",
                    "character": char,
                    "voice": voice,
                    "emotion": emotion,
                    "duration_s": round(elapsed, 1),
                    "timestamp": datetime.now().isoformat(),
                }

                if success:
                    wav_files.append(seg_path)
                    pause_afters.append(pause_after)
                    log_entry["status"] = "success"
                    print(f"  OK ({elapsed:.1f}s)")
                else:
                    failed_segments.append(f"ch{ci}_{si:04d}")
                    log_entry["status"] = "failed"
                    print(f"  FAILED")

                generation_log.append(log_entry)
                seg_idx_global += 1

        if wav_files:
            ch_wav = os.path.join(output_dir, f"ch{ci+1}.wav")
            dur = concat_wavs(wav_files, ch_wav, args.pause_ms, pause_afters)
            ch_mp3 = os.path.join(output_dir, f"ch{ci+1}.mp3")
            to_mp3(ch_wav, ch_mp3)
            chapter_files.append(ch_wav)
            print(f"\n  [OK] ch{ci+1}.mp3 — {dur:.1f}s ({dur/60:.1f} min)")

    # 合并所有章节
    if len(chapter_files) > 1:
        print(f"\n{'='*60}")
        print(f"MERGING {len(chapter_files)} CHAPTERS")
        print(f"{'='*60}")
        final_wav = os.path.join(output_dir, "complete.wav")
        # 使用 concat_wavs 合并章节，章节间停顿使用 chapter_pause_ms
        chapter_pauses = [args.chapter_pause_ms] * (len(chapter_files) - 1)
        dur = concat_wavs(chapter_files, final_wav, pause_ms=0, per_file_pauses=chapter_pauses)
        # 响度归一化
        if args.normalize:
            normalize_loudness(final_wav, target_lufs=args.target_lufs)
        final_mp3 = os.path.join(output_dir, "complete.mp3")
        to_mp3(final_wav, final_mp3)
        print(f"\n  [OK] complete.mp3 — {dur:.1f}s ({dur/60:.1f} min)")
    elif len(chapter_files) == 1:
        import shutil
        shutil.copy2(os.path.join(output_dir, "ch1.mp3"),
                     os.path.join(output_dir, "complete.mp3"))

    # 保存日志
    log_path = os.path.join(output_dir, "generation_log.json")
    log_data = {
        "title": title,
        "chapters": len(chapters),
        "total_segments": total_segments,
        "failed_segments": failed_segments,
        "voices": voices,
        "generated_at": datetime.now().isoformat(),
        "segments": generation_log,
    }
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    # 保存 segments.json 副本
    segments_copy = os.path.join(output_dir, "segments.json")
    with open(segments_copy, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"DONE!")
    print(f"  Chapters: {len(chapters)}")
    print(f"  Segments: {total_segments}")
    print(f"  Failed: {len(failed_segments)}")
    if failed_segments:
        print(f"  Failed IDs: {', '.join(failed_segments)}")
    print(f"  Output: {output_dir}")
    print(f"  Log: {log_path}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="有声书/字幕语音生成引擎 v2.9")
    parser.add_argument("input", help="segments.json / 小说文本 / 字幕文件 (.srt/.ass)")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("--auto", action="store_true", help="自动解析模式（输入为原始小说文本）")
    parser.add_argument("--subtitle", action="store_true", help="字幕模式（输入为 .srt/.ass 字幕文件）")
    parser.add_argument("--tts-script", default=None, help="TTS 脚本路径")
    parser.add_argument("--pause-ms", type=int, default=400, help="默认段落间停顿 (ms)")
    parser.add_argument("--chapter-pause-ms", type=int, default=2000, help="章节间停顿 (ms)")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="跳过已生成的段落（默认启用）")
    parser.add_argument("--voices", type=str, default=None, help='角色音色覆盖 JSON: \'{"角色名":"voice"}\'')
    parser.add_argument("--speaker-voices", type=str, default=None, help='说话人音色映射 JSON: \'{"旁白":"冰糖","张三":"Dean"}\'')
    parser.add_argument("--speaker-styles", type=str, default=None, help='说话人风格映射 JSON: \'{"旁白":"温柔女声","张三":"低沉磁性"}\'')
    parser.add_argument("--default-voice", type=str, default="mimo_default", help="默认音色（字幕模式）")
    parser.add_argument("--default-style", type=str, default="", help="默认风格（字幕模式）")
    parser.add_argument("--max-speed", type=float, default=2.0, help="字幕模式最大加速倍率（默认 2.0）")
    parser.add_argument("--tts-backend", type=str, default=None,
                        choices=["mimo", "edge"],
                        help="TTS 后端: mimo (MiMo API) 或 edge (Edge TTS)。默认 edge。")
    parser.add_argument("--fix-overlaps", action="store_true", default=True,
                        help="自动检测并修复字幕时间轴重叠（默认开启）")
    parser.add_argument("--no-fix-overlaps", action="store_false", dest="fix_overlaps",
                        help="禁用字幕时间轴重叠修复")
    parser.add_argument("--normalize", action="store_true", default=True,
                        help="生成后自动响度归一化（默认开启，EBU R128 -16 LUFS）")
    parser.add_argument("--no-normalize", action="store_false", dest="normalize",
                        help="禁用响度归一化")
    parser.add_argument("--target-lufs", type=float, default=-16,
                        help="响度归一化目标 LUFS（默认 -16，适合语音）")
    parser.add_argument("--no-speed-adjust", action="store_true",
                        help="禁用语速自动适配（不加速 TTS 音频以匹配时间轴）")
    parser.add_argument("--async", dest="async_mode", action="store_true",
                        help="启用异步并发 TTS 生成（更快）")
    parser.add_argument("--concurrent", type=int, default=5,
                        help="异步并发数（默认 5，配合 --async 使用）")
    parser.add_argument("--target-lang", type=str, default=None,
                        help="目标语言代码（字幕翻译模式）：zh/en/ja/ko/fr/es/de/pt 等")
    parser.add_argument("--export-srt", action="store_true",
                        help="仅导出处理后的 SRT 文件（不生成语音）")
    parser.add_argument("--import-translated", type=str, default=None,
                        help="导入翻译后的字幕 JSON 文件")
    args = parser.parse_args()

    # 解析 TTS 后端
    tts_backend, backend_warning = resolve_tts_backend(args.tts_backend)
    if backend_warning:
        print(f"[WARN] {backend_warning}", file=sys.stderr)

    # TTS 脚本路径
    tts_script = args.tts_script
    if not tts_script:
        tts_script = os.path.join(script_dir, "tts_voice.sh")
    if not os.path.exists(tts_script):
        print(f"Error: TTS script not found: {tts_script}", file=sys.stderr)
        sys.exit(1)

    # 字幕模式
    if args.subtitle:
        if not HAS_SUBTITLE:
            print("Error: subtitle_parser.py required for --subtitle mode", file=sys.stderr)
            sys.exit(1)
        entries = parse_subtitle(args.input)
        if not entries:
            print("Error: no subtitle entries found", file=sys.stderr)
            sys.exit(1)

        # 语言检测
        lang_info = detect_language(entries)
        lang_names = {
            "zh": "中文", "ja": "日语", "ko": "韩语", "en": "英语",
            "ru": "俄语", "ar": "阿拉伯语", "th": "泰语",
        }
        lang_label = lang_names.get(lang_info["primary"], lang_info["primary"])
        print(f"[INFO] 检测到字幕语言: {lang_label} (置信度: {lang_info['confidence']:.0%})")

        # 时间轴重叠检测与修复
        if args.fix_overlaps:
            overlaps = detect_overlaps(entries)
            if overlaps:
                total_overlap_ms = sum(ov["overlap_ms"] for ov in overlaps)
                print(f"[WARN] 检测到 {len(overlaps)} 处时间轴重叠（总计 {total_overlap_ms}ms），正在修复...")
                entries, changes = fix_overlaps(entries)
                # 统计修复类型
                merge_count = sum(1 for c in changes if c["type"] == "merge")
                trim_count = sum(1 for c in changes if c["type"] == "trim_end")
                shift_count = sum(1 for c in changes if c["type"] == "shift")
                split_count = sum(1 for c in changes if c["type"] == "proportional_split")
                print(f"  [OK] 已修复: {trim_count} 处裁剪, {split_count} 处按比例分配, "
                      f"{shift_count} 处平移, {merge_count} 处合并")
                # 保存修复后的字幕文件
                import os as _os
                base_name = _os.path.splitext(_os.path.basename(args.input))[0]
                fixed_srt = _os.path.join(args.output_dir, f"{base_name}_fixed.srt")
                _os.makedirs(args.output_dir, exist_ok=True)
                entries_to_srt(entries, fixed_srt)
                print(f"  [FILE] 修复后字幕已保存: {fixed_srt}")
            else:
                print("[OK] 时间轴无重叠")

        # === 翻译模式 ===
        if args.target_lang:
            target = args.target_lang.lower()
            lang_names = {
                "zh": "中文", "en": "英语", "ja": "日语", "ko": "韩语",
                "fr": "法语", "es": "西班牙语", "de": "德语", "pt": "葡萄牙语",
                "ru": "俄语", "ar": "阿拉伯语", "th": "泰语",
            }
            target_name = lang_names.get(target, target)
            if target == lang_info["primary"]:
                print(f"[WARN] 目标语言与源语言相同（{target_name}），跳过翻译。")
            else:
                # 导出待翻译的文本
                os.makedirs(args.output_dir, exist_ok=True)
                texts_json = os.path.join(args.output_dir, "_translate_input.json")
                with open(texts_json, 'w', encoding='utf-8') as f:
                    json.dump([{"index": i, "text": e.text, "start": e.start_ms, "end": e.end_ms}
                              for i, e in enumerate(entries)], f, ensure_ascii=False, indent=2)
                print(f"NEED_TRANSLATE:target={target}:source={lang_info['primary']}")
                print(f"TRANSLATE_JSON:{texts_json}")
                print(f"\n请将字幕翻译为 {target_name}({target})，完成后用以下命令导入：")
                print(f"  python3 {sys.argv[0]} --subtitle {args.input} {args.output_dir} --import-translated <translated.json>")
                return

        # === 导入翻译结果 ===
        if args.import_translated:
            with open(args.import_translated, 'r', encoding='utf-8') as f:
                translated = json.load(f)
            translated_texts = [item["text"] for item in translated]
            if len(translated_texts) != len(entries):
                print(f"Error: translated entries ({len(translated_texts)}) != original ({len(entries)})", file=sys.stderr)
                sys.exit(1)
            for i, text in enumerate(translated_texts):
                entries[i].text = text
            # 导出翻译后的 SRT
            base_name = os.path.splitext(os.path.basename(args.input))[0]
            target_lang = args.target_lang or "translated"
            translated_srt = os.path.join(args.output_dir, f"{base_name}_{target_lang}.srt")
            os.makedirs(args.output_dir, exist_ok=True)
            entries_to_srt(entries, translated_srt)
            print(f"[OK] 翻译后字幕已导出: {translated_srt}")

        # === 仅导出 SRT 模式 ===
        if args.export_srt:
            base_name = os.path.splitext(os.path.basename(args.input))[0]
            out_srt = os.path.join(args.output_dir, f"{base_name}_processed.srt")
            os.makedirs(args.output_dir, exist_ok=True)
            entries_to_srt(entries, out_srt)
            print(f"[OK] 已导出: {out_srt}")
            print(f"  条数: {len(entries)}")
            return

        speaker_voice_map = json.loads(args.speaker_voices) if args.speaker_voices else {}
        speaker_style_map = json.loads(args.speaker_styles) if args.speaker_styles else {}

        # 如果没有指定说话人音色，自动检测并展示
        speakers = get_speakers(entries)
        if speakers and not speaker_voice_map:
            print(f"Detected speakers: {speakers}")
            print("Use --speaker-voices to map voices, e.g.:")
            example = {s: "mimo_default" for s in speakers}
            print(f"  --speaker-voices '{json.dumps(example, ensure_ascii=False)}'")
            print()

        data = entries_to_segments(
            entries,
            speaker_voice_map=speaker_voice_map,
            speaker_style_map=speaker_style_map,
            default_voice=args.default_voice,
            default_style=args.default_style,
        )
        data["title"] = os.path.splitext(os.path.basename(args.input))[0]
        data["_source_lang"] = lang_info["primary"]
        run_subtitle_generation(tts_script, data, args.output_dir, args, tts_backend=tts_backend)
        return

    # 解析输入
    if args.auto:
        # 自动解析模式
        if not HAS_PARSER:
            print("Error: text_parser.py required for --auto mode", file=sys.stderr)
            sys.exit(1)
        with open(args.input, 'r', encoding='utf-8') as f:
            novel_text = f.read()
        voice_map = json.loads(args.voices) if args.voices else None
        data = auto_parse_to_segments(novel_text, voice_map, tts_backend=tts_backend)
        data["title"] = os.path.splitext(os.path.basename(args.input))[0]
    else:
        # 传统 segments.json 模式
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)

    run_generation(tts_script, data, args.output_dir, args, tts_backend=tts_backend)


# ============================================================
# 字幕模式生成
# ============================================================

def run_subtitle_generation(tts_script, data, output_dir, args, tts_backend=None):
    """
    字幕模式生成：按时间轴对齐生成语音
    data 中的 segments 包含 _start_ms/_end_ms/_duration_ms 时间轴信息
    """
    title = data.get("title", "subtitle_audio")
    voices = data.get("voices", {"narrator": "mimo_default"})
    styles = data.get("styles", {"narrator": ""})
    chapters = data.get("chapters", [])

    os.makedirs(output_dir, exist_ok=True)
    seg_dir = os.path.join(output_dir, "segments")
    os.makedirs(seg_dir, exist_ok=True)

    # 收集所有 segments 和时间轴
    all_segments = []
    all_timeline = []
    for chapter in chapters:
        for seg in chapter.get("segments", []):
            all_segments.append(seg)
            all_timeline.append({
                "start_ms": seg.get("_start_ms", 0),
                "end_ms": seg.get("_end_ms", 0),
                "duration_ms": seg.get("_duration_ms", 2000),
            })

    total_segments = len(all_segments)
    backend_label = tts_backend or "auto"
    print(f"{'='*60}")
    print(f"SUBTITLE MODE")
    print(f"Title: {title}")
    print(f"TTS Backend: {backend_label}")
    print(f"Total entries: {total_segments}")
    if all_timeline:
        total_ms = max(t["end_ms"] for t in all_timeline)
        print(f"Total duration: {total_ms/1000:.1f}s ({total_ms/60000:.1f} min)")
    print(f"Voice mapping:")
    for char, voice in voices.items():
        print(f"  {char}: {voice}")
    print(f"{'='*60}")

    wav_files = []
    failed_segments = []
    generation_log = []
    success_indices = []  # Track which segment indices succeeded

    for si, seg in enumerate(all_segments):
        text = seg["text"]
        char = seg.get("char", "narrator")
        style_override = seg.get("style", "")
        emotion = seg.get("emotion", "neutral")
        timeline = all_timeline[si] if si < len(all_timeline) else {}

        # Edge TTS 扩展参数（per-segment 覆盖）
        seg_speed = seg.get("speed", 1.0)
        seg_pitch = seg.get("pitch", 1.0)
        seg_style_degree = seg.get("style_degree", 1.0)
        seg_role = seg.get("role", "")
        seg_cleaning = seg.get("cleaning_options", None)

        voice = voices.get(char, "mimo_default")
        base_style = style_override if style_override else styles.get(char, "")

        if HAS_CALC and emotion != "neutral":
            style = ParamCalculator.build_style(base_style, emotion, "medium")
        else:
            style = base_style

        seg_path = os.path.join(seg_dir, f"sub_{si:04d}.wav")
        start_s = timeline.get("start_ms", 0) / 1000
        print(f"[{si+1}/{total_segments}] {char}({voice}) @{start_s:.2f}s: {text[:40]}...")

        start_time = time.time()
        success = generate_segment(tts_script, text, style, voice, seg_path, max_retries=3, tts_backend=tts_backend,
                                   speed=seg_speed, pitch=seg_pitch, style_degree=seg_style_degree, role=seg_role,
                                   cleaning_options=seg_cleaning)
        elapsed = time.time() - start_time

        log_entry = {
            "segment_id": f"sub_{si:04d}",
            "character": char,
            "voice": voice,
            "start_ms": timeline.get("start_ms", 0),
            "end_ms": timeline.get("end_ms", 0),
            "duration_s": round(elapsed, 1),
            "timestamp": datetime.now().isoformat(),
        }

        if success:
            wav_files.append(seg_path)
            success_indices.append(si)
            log_entry["status"] = "success"
            print(f"  OK ({elapsed:.1f}s)")
        else:
            failed_segments.append(f"sub_{si:04d}")
            log_entry["status"] = "failed"
            print(f"  FAILED")

        generation_log.append(log_entry)

    # 按时间轴合并
    if wav_files:
        print(f"\n{'='*60}")
        print(f"MERGING WITH TIMELINE ({len(wav_files)} segments)")
        print(f"{'='*60}")

        final_wav = os.path.join(output_dir, "subtitle_audio.wav")
        # 只传入已成功生成的 segments 对应的时间轴
        valid_timeline = [all_timeline[i] for i in success_indices if i < len(all_timeline)]
        valid_wavs = [w for w in wav_files if os.path.exists(w)]

        # 语速适配：自动加速 TTS 音频以适配字幕时间槽
        no_speed_adjust = getattr(args, 'no_speed_adjust', False)
        if valid_wavs and valid_timeline and not no_speed_adjust:
            print(f"\n  [INFO] 检测语速适配...")
            max_speed = getattr(args, 'max_speed', 2.0)
            valid_wavs = speed_adjust_segments(valid_wavs, valid_timeline, seg_dir, max_speed=max_speed)
        elif no_speed_adjust:
            print(f"\n  [INFO] 语速适配已禁用（--no-speed-adjust）")

        if valid_wavs:
            dur = merge_with_timeline_fast(valid_wavs, final_wav, valid_timeline)
            # 响度归一化
            if args.normalize:
                normalize_loudness(final_wav, target_lufs=args.target_lufs)
            final_mp3 = os.path.join(output_dir, "subtitle_audio.mp3")
            to_mp3(final_wav, final_mp3)
            print(f"\n  [OK] subtitle_audio.mp3 — {dur:.1f}s ({dur/60:.1f} min)")

            # 同时生成时间轴对齐的 SRT 副本（标注每条语音的实际位置）
            srt_out = os.path.join(output_dir, "timeline.srt")
            with open(srt_out, 'w', encoding='utf-8') as f:
                for idx, si in enumerate(success_indices):
                    if si >= len(all_timeline):
                        break
                    seg = all_segments[si]
                    tl = all_timeline[si]
                    f.write(f"{idx+1}\n")
                    f.write(f"{ms_to_srt_time(tl['start_ms'])} --> {ms_to_srt_time(tl['end_ms'])}\n")
                    f.write(f"{seg['text']}\n\n")
            print(f"  [FILE] timeline.srt — 时间轴副本已保存")

    # 保存日志
    log_path = os.path.join(output_dir, "generation_log.json")
    log_data = {
        "title": title,
        "mode": "subtitle",
        "total_segments": total_segments,
        "failed_segments": failed_segments,
        "voices": voices,
        "generated_at": datetime.now().isoformat(),
        "segments": generation_log,
    }
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    # 保存 segments.json 副本
    segments_copy = os.path.join(output_dir, "segments.json")
    with open(segments_copy, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"DONE!")
    print(f"  Mode: subtitle")
    print(f"  Segments: {total_segments}")
    print(f"  Failed: {len(failed_segments)}")
    if failed_segments:
        print(f"  Failed IDs: {', '.join(failed_segments)}")
    print(f"  Output: {output_dir}")
    print(f"{'='*60}")



# ── 优化辅助函数（v2.17 新增）──────────────────────────────────────
# 以下函数从大函数中拆分，提升可读性和可维护性
# 原始函数保持不变，新函数作为可选的调用入口

def prepare_generation_env(input_path, output_dir, voices=None, styles=None):
    """准备生成环境：创建目录、检测输入类型"""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "segments"), exist_ok=True)

    if input_path.endswith((".srt", ".ass")):
        input_type = "subtitle"
    elif input_path.endswith(".json"):
        input_type = "segments_json"
    else:
        input_type = "novel_text"

    return {
        "input_path": input_path,
        "output_dir": output_dir,
        "voices": voices or {},
        "styles": styles or {},
        "input_type": input_type,
    }


def get_voice_for_character(char_name, voices_map, default_voice="mimo_default"):
    """根据角色名获取音色"""
    return voices_map.get(char_name, default_voice)


def merge_audio_files(wav_files, output_path, silence_ms=400):
    """合并多个 WAV 文件（带静音间隔）"""
    import subprocess

    if not wav_files:
        return False

    try:
        silence_path = output_path + ".silence.wav"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            "anullsrc=r=24000:cl=mono:d=" + str(silence_ms / 1000),
            silence_path
        ], capture_output=True, timeout=10)

        list_path = output_path + ".concat.txt"
        with open(list_path, "w") as f:
            for i, wav in enumerate(wav_files):
                line = "file '" + wav + "'\n"
                f.write(line)
                if i < len(wav_files) - 1:
                    sil_line = "file '" + silence_path + "'\n"
                    f.write(sil_line)

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
            output_path
        ], capture_output=True, timeout=300)

        for tmp in [silence_path, list_path]:
            if os.path.exists(tmp):
                os.remove(tmp)

        return os.path.exists(output_path)
    except Exception as e:
        print("  [ERROR] Merge failed: " + str(e))
        return False


def speed_adjust_audio(audio_path, target_ms, max_speed=2.0):
    """调整音频速度以匹配目标时长"""
    import subprocess

    if not os.path.exists(audio_path):
        return False

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", audio_path],
            capture_output=True, text=True, timeout=10
        )
        actual_ms = float(result.stdout.strip()) * 1000
    except Exception:
        return False

    if actual_ms <= target_ms:
        return True

    speed_ratio = min(actual_ms / target_ms, max_speed)

    try:
        tmp_path = audio_path + ".sped.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", audio_path,
            "-filter:a", "atempo=" + str(speed_ratio),
            tmp_path
        ], capture_output=True, timeout=30)

        if os.path.exists(tmp_path):
            os.replace(tmp_path, audio_path)
            return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    main()
