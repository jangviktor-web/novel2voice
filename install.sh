```bash
#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  🎙️ Novel2Voice — Complete Installation Script
#  Version: 2.20.0
#
#  Usage:
#    bash install.sh [install_dir]
#    Default: ./novel2voice
#
#  After install:
#    cd novel2voice
#    python3 scripts/generate_audiobook.py --auto novel.txt ./output
# ═══════════════════════════════════════════════════════════════════

set -e

INSTALL_DIR="${1:-./novel2voice}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "  🎙️  Novel2Voice v2.20.0"
echo "  ──────────────────────────────────────"
echo "  Installing to: $INSTALL_DIR"
echo ""

# ── Create directory structure ────────────────────────────────────
mkdir -p "$INSTALL_DIR"/{scripts/voice_samples,data,output}

# ── Check prerequisites ──────────────────────────────────────────
echo "  [1/5] Checking prerequisites..."

if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1)
    echo "        ✅ $PY_VER"
else
    echo "        ❌ python3 not found. Please install Python 3.8+"
    exit 1
fi

if command -v ffmpeg &>/dev/null; then
    echo "        ✅ ffmpeg found"
    FFMPEG_OK=true
else
    echo "        ⚠️  ffmpeg not found — output limited to WAV only"
    FFMPEG_OK=false
fi

# ── Install Python dependencies ──────────────────────────────────
echo "  [2/5] Installing Python dependencies..."
python3 -m pip install --quiet requests charset_normalizer 2>/dev/null || \
    pip3 install --quiet requests charset_normalizer
echo "        ✅ requests, charset_normalizer"

# ── Write configuration ──────────────────────────────────────────
echo "  [3/5] Writing configuration..."

cat << 'ENVEOF' > "$INSTALL_DIR/.env.example"
# Novel2Voice — Environment Configuration
# Copy this file to .env and modify as needed

# TTS Backend: edge (default) or mimo
TTS_BACKEND=edge

# Edge TTS (default, no key needed)
EDGE_TTS_ENDPOINT=tts.kalaok.cc.cd/v1/audio/speech
EDGE_TTS_KEY=

# MiMo TTS (requires API key from https://mimo.xiaomi.com)
MIMO_API_KEY=
ENVEOF

# Copy to .env if not exists
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
fi

# ── Write voice catalog ─────────────────────────────────────────
cat << 'CATALOGEOF' > "$INSTALL_DIR/data/voice_catalog.json"
{
  "edge_tts": {
    "female": [
      {"name": "晓晓", "id": "zh-CN-XiaoxiaoNeural", "desc": "清亮标准播音", "age": "20-28", "use": "旁白/女主"},
      {"name": "晓依", "id": "zh-CN-XiaoyiNeural", "desc": "低沉温柔治愈", "age": "25-35", "use": "温柔人妻"},
      {"name": "晓涵", "id": "zh-CN-XiaohanNeural", "desc": "文艺清冷", "age": "22-30", "use": "大家闺秀"},
      {"name": "晓墨", "id": "zh-CN-XiaomoNeural", "desc": "情绪丰富", "age": "24-35", "use": "虐文女主/侠女"},
      {"name": "晓睿", "id": "zh-CN-XiaoruiNeural", "desc": "稳重厚实中年", "age": "45-60", "use": "主母/长辈"},
      {"name": "晓双", "id": "zh-CN-XiaoshuangNeural", "desc": "清脆孩童少女", "age": "8-14", "use": "小丫鬟"},
      {"name": "晓梦", "id": "zh-CN-XiaomengNeural", "desc": "软萌甜妹", "age": "16-22", "use": "校园学妹"}
    ],
    "male": [
      {"name": "云希", "id": "zh-CN-YunxiNeural", "desc": "清爽阳光少年", "age": "18-27", "use": "少年男主"},
      {"name": "云扬", "id": "zh-CN-YunyangNeural", "desc": "央视浑厚播音", "age": "35-55", "use": "帝王/旁白"},
      {"name": "云健", "id": "zh-CN-YunjianNeural", "desc": "低沉浑厚大叔", "age": "38-55", "use": "硬汉/武将"},
      {"name": "云夏", "id": "zh-CN-YunxiaNeural", "desc": "正太少年童声", "age": "7-15", "use": "幼年男主"},
      {"name": "云泽", "id": "zh-CN-YunzeNeural", "desc": "苍老沉稳", "age": "60+", "use": "隐世高人/长老"},
      {"name": "云枫", "id": "zh-CN-YunfengNeural", "desc": "平淡务实", "age": "28-38", "use": "温润男配"}
    ],
    "dialect": [
      {"name": "云彪", "id": "zh-CN-YunbianNeural", "dialect": "东北"},
      {"name": "晓北", "id": "zh-CN-XiaobeiNeural", "dialect": "东北"},
      {"name": "云登", "id": "zh-CN-YundengNeural", "dialect": "河南"},
      {"name": "云翔", "id": "zh-CN-YunxiangNeural", "dialect": "山东"},
      {"name": "云熙", "id": "zh-CN-YunxiNeural", "dialect": "四川"},
      {"name": "云奇", "id": "zh-CN-YunqiNeural", "dialect": "广西"},
      {"name": "晓妮", "id": "zh-CN-XiaoniNeural", "dialect": "陕西"}
    ],
    "cantonese": [
      {"name": "晓佳", "id": "zh-HK-HiuGaaiNeural"},
      {"name": "晓蔓", "id": "zh-HK-HiuMaanNeural"},
      {"name": "云龙", "id": "zh-HK-WanLungNeural"}
    ],
    "taiwanese": [
      {"name": "晓晨", "id": "zh-TW-HsiaoChenNeural"},
      {"name": "晓雨", "id": "zh-TW-HsiaoYuNeural"},
      {"name": "云哲", "id": "zh-TW-YunJheNeural"}
    ]
  },
  "mimo_tts": {
    "chinese": [
      {"name": "冰糖", "id": "bingtang", "desc": "清甜治愈女声"},
      {"name": "茉莉", "id": "moli", "desc": "软糯温柔女声"},
      {"name": "苏打", "id": "suda", "desc": "清亮少年男声"},
      {"name": "白桦", "id": "baihua", "desc": "苍老沉稳男声"},
      {"name": "mimo_default", "id": "mimo_default", "desc": "中性女声"}
    ],
    "english": [
      {"name": "Mia", "id": "mia", "desc": "活泼开朗女声"},
      {"name": "Chloe", "id": "chloe", "desc": "冷淡优雅女声"},
      {"name": "Milo", "id": "milo", "desc": "清亮阳光男声"},
      {"name": "Dean", "id": "dean", "desc": "低沉磁性男声"}
    ]
  },
  "friendly_to_system": {
    "晓晓": "zh-CN-XiaoxiaoNeural",
    "晓依": "zh-CN-XiaoyiNeural",
    "晓涵": "zh-CN-XiaohanNeural",
    "晓墨": "zh-CN-XiaomoNeural",
    "晓睿": "zh-CN-XiaoruiNeural",
    "晓双": "zh-CN-XiaoshuangNeural",
    "晓梦": "zh-CN-XiaomengNeural",
    "云希": "zh-CN-YunxiNeural",
    "云扬": "zh-CN-YunyangNeural",
    "云健": "zh-CN-YunjianNeural",
    "云夏": "zh-CN-YunxiaNeural",
    "云泽": "zh-CN-YunzeNeural",
    "云枫": "zh-CN-YunfengNeural",
    "云彪": "zh-CN-YunbianNeural",
    "晓北": "zh-CN-XiaobeiNeural",
    "云登": "zh-CN-YundengNeural",
    "云翔": "zh-CN-YunxiangNeural",
    "云熙": "zh-CN-YunxiNeural",
    "云奇": "zh-CN-YunqiNeural",
    "晓妮": "zh-CN-XiaoniNeural"
  }
}
CATALOGEOF

# ── Write subtitle_parser.py ─────────────────────────────────────
cat << 'SUBEOF' > "$INSTALL_DIR/scripts/subtitle_parser.py"
#!/usr/bin/env python3
"""Subtitle parser: SRT/ASS with multi-encoding auto-detection."""

import json
import os
import re
import sys
from pathlib import Path

def detect_and_read(filepath):
    """Read file with auto encoding detection."""
    raw = Path(filepath).read_bytes()
    # Try UTF-8 BOM first
    if raw[:3] == b'\xef\xbb\xbf':
        return raw[3:].decode('utf-8')
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    # Try charset_normalizer
    try:
        from charset_normalizer import from_bytes
        result = from_bytes(raw).best()
        if result and result.encoding:
            confidence = getattr(result, 'confidence', 0)
            text = str(result)
            if confidence >= 0.7:
                return text
    except ImportError:
        pass
    # Fallback: try common encodings
    for enc in ['utf-8', 'gbk', 'big5', 'shift_jis', 'euc-kr', 'latin-1']:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', errors='replace')


def parse_srt(text):
    """Parse SRT format into list of entries."""
    entries = []
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Split by blank lines
    blocks = re.split(r'\n\n+', text.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        # First line: index
        try:
            idx = int(lines[0].strip())
        except ValueError:
            continue
        # Second line: timecodes
        time_match = re.match(
            r'(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})',
            lines[1].strip()
        )
        if not time_match:
            continue
        g = [int(x) for x in time_match.groups()]
        start_ms = g[0]*3600000 + g[1]*60000 + g[2]*1000 + g[3]
        end_ms = g[4]*3600000 + g[5]*60000 + g[6]*1000 + g[7]
        # Remaining lines: text
        content = '\n'.join(lines[2:]).strip()
        # Try to extract speaker from format like "Speaker: text" or "{Speaker}text"
        speaker = ''
        text_content = content
        speaker_match = re.match(r'^(?:\{([^}]+)\}|([^:：]{1,20})[：:])\s*(.+)', content, re.DOTALL)
        if speaker_match:
            speaker = (speaker_match.group(1) or speaker_match.group(2)).strip()
            text_content = speaker_match.group(3).strip()
        entries.append({
            'index': idx,
            'start_ms': start_ms,
            'end_ms': end_ms,
            'speaker': speaker,
            'text': text_content,
            'raw': content,
        })
    return entries


def parse_ass(text):
    """Parse ASS/SSA format into list of entries."""
    entries = []
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    in_events = False
    format_fields = []
    idx = 0
    for line in lines:
        line = line.strip()
        if line.lower() == '[events]':
            in_events = True
            continue
        if line.startswith('[') and line.endswith(']'):
            in_events = False
            continue
        if not in_events:
            continue
        if line.lower().startswith('format:'):
            format_fields = [f.strip().lower() for f in line[7:].split(',')]
            continue
        if line.lower().startswith('dialogue:'):
            parts = line[9:].split(',', len(format_fields) - 1)
            if len(parts) < len(format_fields):
                continue
            field_map = dict(zip(format_fields, parts))
            # Parse timecodes (H:MM:SS.CC format)
            def parse_ass_time(t):
                t = t.strip()
                m = re.match(r'(\d+):(\d{2}):(\d{2})\.(\d{2})', t)
                if not m:
                    return 0
                g = [int(x) for x in m.groups()]
                return g[0]*3600000 + g[1]*60000 + g[2]*1000 + g[3]*10
            start_ms = parse_ass_time(field_map.get('start', '0:00:00.00'))
            end_ms = parse_ass_time(field_map.get('end', '0:00:00.00'))
            speaker = field_map.get('name', '').strip()
            raw_text = field_map.get('text', '')
            # Strip ASS override tags
            clean_text = re.sub(r'\{[^}]*\}', '', raw_text)
            clean_text = clean_text.replace('\\N', '\n').replace('\\n', '\n').strip()
            idx += 1
            entries.append({
                'index': idx,
                'start_ms': start_ms,
                'end_ms': end_ms,
                'speaker': speaker,
                'text': clean_text,
                'raw': raw_text,
            })
    return entries


def detect_language(entries):
    """Detect language from text content."""
    sample = ' '.join(e['text'] for e in entries[:20])
    cjk_count = len(re.findall(r'[\u4e00-\u9fff]', sample))
    hira_kata = len(re.findall(r'[\u3040-\u30ff]', sample))
    hangul = len(re.findall(r'[\uac00-\ud7af]', sample))
    latin = len(re.findall(r'[a-zA-Z]', sample))
    total = max(len(sample), 1)
    if hira_kata / total > 0.05:
        return 'ja', 0.9
    if hangul / total > 0.05:
        return 'ko', 0.9
    if cjk_count / total > 0.2:
        return 'zh', min(0.99, 0.5 + cjk_count / total)
    if latin / total > 0.5:
        return 'en', min(0.9, 0.5 + latin / total)
    return 'unknown', 0.3


def fix_overlaps(entries, min_gap_ms=50):
    """Fix overlapping timecodes."""
    fixed = []
    for i, entry in enumerate(entries):
        if i > 0 and fixed:
            prev = fixed[-1]
            if entry['start_ms'] < prev['end_ms']:
                overlap = prev['end_ms'] - entry['start_ms']
                prev_duration = prev['end_ms'] - prev['start_ms']
                if overlap < prev_duration * 0.5:
                    prev['end_ms'] = entry['start_ms'] - min_gap_ms
                    if prev['end_ms'] < prev['start_ms'] + 200:
                        prev['end_ms'] = prev['start_ms'] + 200
                        entry['start_ms'] = prev['end_ms'] + min_gap_ms
                else:
                    total_dur = (prev['end_ms'] - prev['start_ms']) + (entry['end_ms'] - entry['start_ms'])
                    ratio = len(prev['text']) / max(len(prev['text']) + len(entry['text']), 1)
                    mid = prev['start_ms'] + int(total_dur * ratio)
                    prev['end_ms'] = mid
                    entry['start_ms'] = mid + min_gap_ms
        fixed.append(entry)
    return fixed


def parse_subtitle_file(filepath, fix=True):
    """Main entry: parse subtitle file, return structured data."""
    text = detect_and_read(filepath)
    ext = Path(filepath).suffix.lower()
    if ext == '.srt':
        entries = parse_srt(text)
    elif ext in ('.ass', '.ssa'):
        entries = parse_ass(text)
    else:
        # Try SRT first, then ASS
        entries = parse_srt(text)
        if not entries:
            entries = parse_ass(text)
    if not entries:
        print(f"⚠️ No entries found in {filepath}")
        return {'entries': [], 'language': 'unknown', 'speakers': [], 'duration_ms': 0}
    # Fix overlaps
    if fix and len(entries) > 1:
        entries = fix_overlaps(entries)
    # Detect language
    lang, confidence = detect_language(entries)
    # Extract unique speakers
    speakers = list(dict.fromkeys(e['speaker'] for e in entries if e['speaker']))
    total_duration = max(e['end_ms'] for e in entries) if entries else 0
    return {
        'entries': entries,
        'language': lang,
        'language_confidence': confidence,
        'speakers': speakers,
        'duration_ms': total_duration,
        'total_entries': len(entries),
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 subtitle_parser.py <subtitle_file>")
        sys.exit(1)
    result = parse_subtitle_file(sys.argv[1])
    print(json.dumps({
        'total_entries': result['total_entries'],
        'language': result['language'],
        'confidence': result.get('language_confidence', 0),
        'speakers': result['speakers'],
        'duration_seconds': result['duration_ms'] / 1000,
        'sample': [
            {'start': e['start_ms'], 'end': e['end_ms'], 'speaker': e['speaker'], 'text': e['text'][:80]}
            for e in result['entries'][:5]
        ]
    }, ensure_ascii=False, indent=2))
SUBEOF

# ── Write edge_tts_client.py ─────────────────────────────────────
cat << 'EDGEEOF' > "$INSTALL_DIR/scripts/edge_tts_client.py"
#!/usr/bin/env python3
"""Edge TTS API client with retry and style support."""

import json
import os
import re
import time
import requests

CATALOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'voice_catalog.json')
_friendly_map = None

def _load_friendly_map():
    global _friendly_map
    if _friendly_map is None:
        try:
            with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _friendly_map = data.get('friendly_to_system', {})
        except Exception:
            _friendly_map = {}
    return _friendly_map


def resolve_voice(name):
    """Resolve friendly name (晓晓) to system name (zh-CN-XiaoxiaoNeural)."""
    if name.startswith('zh-'):
        return name
    m = _load_friendly_map()
    return m.get(name, f'zh-CN-XiaoxiaoNeural')


# Style tag mapping
STYLE_TAGS = {
    '温柔': {'speed_mult': 0.9},
    '愤怒': {'speed_mult': 1.1},
    '悲伤': {'speed_mult': 0.85},
    '开心': {'speed_mult': 1.05},
    '紧张': {'speed_mult': 1.15},
    '平静': {'speed_mult': 0.95},
    '深情': {'speed_mult': 0.88},
    '撒娇': {'speed_mult': 0.92},
    '傲娇': {'speed_mult': 1.0},
    '冷漠': {'speed_mult': 0.95},
}


class EdgeTTSClient:
    def __init__(self, endpoint=None, api_key=None):
        self.endpoint = endpoint or os.environ.get(
            'EDGE_TTS_ENDPOINT', 'tts.kalaok.cc.cd/v1/audio/speech')
        self.api_key = api_key or os.environ.get('EDGE_TTS_KEY', 'sk-1234567890')
        if not self.endpoint.startswith('http'):
            self.endpoint = f'https://{self.endpoint}'
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        })
        self.max_retries = 3
        self.base_delay = 1.0

    def synthesize(self, text, voice='晓晓', speed=1.0, output_format='mp3',
                   style_tag=None, **kwargs):
        """
        Synthesize text to audio bytes.

        Args:
            text: Text to speak
            voice: Friendly name or system voice ID
            speed: Playback speed multiplier
            output_format: mp3 or wav
            style_tag: Optional style tag like '温柔', '愤怒'
        Returns:
            bytes: Audio data
        Raises:
            Exception: After all retries exhausted
        """
        voice_id = resolve_voice(voice)
        # Parse style tags from text
        clean_text, detected_style = self._extract_style_tags(text)
        effective_style = style_tag or detected_style
        effective_speed = speed
        if effective_style and effective_style in STYLE_TAGS:
            effective_speed = speed * STYLE_TAGS[effective_style].get('speed_mult', 1.0)
        # Clamp speed
        effective_speed = max(0.5, min(3.0, effective_speed))
        payload = {
            'model': 'tts-1-hd',
            'input': clean_text,
            'voice': voice_id,
            'response_format': output_format,
            'speed': round(effective_speed, 2),
        }
        # Retry with exponential backoff
        last_err = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.post(self.endpoint, json=payload, timeout=60)
                if resp.status_code == 429:
                    delay = self.base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                if resp.status_code != 200:
                    raise RuntimeError(f'TTS API error {resp.status_code}: {resp.text[:200]}')
                content_type = resp.headers.get('content-type', '')
                if 'audio' in content_type or len(resp.content) > 1000:
                    return resp.content
                # Check if response is JSON error
                try:
                    err = resp.json()
                    raise RuntimeError(f'TTS API error: {err}')
                except (ValueError, KeyError):
                    return resp.content
            except requests.exceptions.Timeout:
                last_err = 'Timeout'
                delay = self.base_delay * (2 ** attempt)
                time.sleep(delay)
            except requests.exceptions.ConnectionError as e:
                last_err = str(e)
                delay = self.base_delay * (2 ** attempt)
                time.sleep(delay)
        raise RuntimeError(f'TTS failed after {self.max_retries} retries. Last error: {last_err}')

    def _extract_style_tags(self, text):
        """Extract (style) tags from text. Returns (clean_text, style)."""
        style = None
        clean = text
        # Match (温柔), （愤怒）, [紧张], etc.
        pattern = r'[(\（\[（](.+?)[)\）\]）]'
        match = re.match(r'^' + pattern + r'\s*', text)
        if match:
            tag = match.group(1).strip()
            if tag in STYLE_TAGS:
                style = tag
            clean = text[match.end():].strip()
        return clean, style

    def test_connection(self):
        """Test API connectivity."""
        try:
            audio = self.synthesize('测试', voice='晓晓')
            return len(audio) > 100
        except Exception:
            return False
EDGEEOF

# ── Write mimo_tts_client.py ─────────────────────────────────────
cat << 'MIMOEOF' > "$INSTALL_DIR/scripts/mimo_tts_client.py"
#!/usr/bin/env python3
"""MiMo TTS API client."""

import os
import time
import requests


class MimoTTSClient:
    def __init__(self, api_key=None, endpoint=None):
        self.api_key = api_key or os.environ.get('MIMO_API_KEY', '')
        self.endpoint = endpoint or os.environ.get(
            'MIMO_TTS_ENDPOINT', 'https://api.xiaomimimo.com/v1')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        })
        self.max_retries = 3
        self.base_delay = 1.0

    def synthesize(self, text, voice='mimo_default', speed=1.0, output_format='mp3', **kwargs):
        """Synthesize text to audio bytes using MiMo TTS."""
        url = f'{self.endpoint}/audio/speech'
        payload = {
            'model': 'mimo-tts',
            'input': text,
            'voice': voice,
            'response_format': output_format,
            'speed': speed,
        }
        last_err = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.post(url, json=payload, timeout=60)
                if resp.status_code == 429:
                    time.sleep(self.base_delay * (2 ** attempt))
                    continue
                if resp.status_code != 200:
                    raise RuntimeError(f'MiMo TTS error {resp.status_code}: {resp.text[:200]}')
                return resp.content
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_err = str(e)
                time.sleep(self.base_delay * (2 ** attempt))
        raise RuntimeError(f'MiMo TTS failed after {self.max_retries} retries: {last_err}')

    def test_connection(self):
        """Test API connectivity."""
        if not self.api_key:
            return False
        try:
            audio = self.synthesize('测试')
            return len(audio) > 100
        except Exception:
            return False
MIMOEOF

# ── Write generate_audiobook.py (main script) ────────────────────
cat << 'GENEOF' > "$INSTALL_DIR/scripts/generate_audiobook.py"
#!/usr/bin/env python3
"""
Novel2Voice — Main Script

Converts novel text or subtitle files into multi-character audiobooks.

Usage:
  python3 generate_audiobook.py --auto novel.txt output_dir
  python3 generate_audiobook.py --subtitle subtitle.srt output_dir
  python3 generate_audiobook.py --auto novel.txt output_dir --character-voices '{"旁白":"云扬"}'
  python3 generate_audiobook.py --auto novel.txt output_dir --preview-only
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add script dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edge_tts_client import EdgeTTSClient, resolve_voice
from subtitle_parser import parse_subtitle_file

# ──────────────────────────── Constants ────────────────────────────
MALE_VOICES = ['云希', '云扬', '云健', '云夏', '云泽', '云枫']
FEMALE_VOICES = ['晓晓', '晓依', '晓涵', '晓墨', '晓睿', '晓双', '晓梦']
DEFAULT_NARRATOR = '云扬'
FEMALE_CHARS = set('娜莉姐妹妈姑姨婷娟婵娥凤花珍巧美兰芳燕琳琴瑛瑶梅洁瑞堇璧璐萱彤琳瑶颖怡静馨雪莺')
MALE_CHARS = set('哥弟爸叔伯爷翁公侯将帅武士杰豪雄伟强刚毅')

# ──────────────────────────── Text Splitting ──────────────────────

def split_chapters(text):
    """Split text into chapters by common Chinese chapter markers."""
    pattern = r'\n\s*(第[零〇一二三四五六七八九十百千万\d]+[章回节卷][^\n]{0,30})\s*\n'
    parts = re.split(pattern, text)
    chapters = []
    if len(parts) <= 1:
        return [{'index': 1, 'title': '全文', 'content': text.strip()}]
    # parts[0] is content before first chapter (prologue)
    if parts[0].strip():
        chapters.append({'index': 0, 'title': '序章', 'content': parts[0].strip()})
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        content = parts[i+1].strip() if i+1 < len(parts) else ''
        chapters.append({
            'index': len(chapters) + 1,
            'title': title,
            'content': content,
        })
    return chapters if chapters else [{'index': 1, 'title': '全文', 'content': text.strip()}]


def split_into_segments(text):
    """Split text into narration and dialogue segments."""
    segments = []
    # Match Chinese quotes: "" "" 「」 『』
    pattern = r'([\u201c\u201d\u300c\u300d\u2018\u2019\u300e\u300f])([^\u201c\u201d\u300c\u300d\u2018\u2019\u300e\u300f]*?)\1'
    last_end = 0
    for match in re.finditer(pattern, text):
        start, end = match.span()
        # Narration before dialogue
        if start > last_end:
            narration = text[last_end:start].strip()
            if narration:
                segments.append(('narration', narration))
        # Dialogue content
        dialogue = match.group(2).strip()
        if dialogue:
            segments.append(('dialogue', dialogue))
        last_end = end
    # Remaining narration
    if last_end < len(text):
        remaining = text[last_end:].strip()
        if remaining:
            segments.append(('narration', remaining))
    return segments


def extract_characters(text):
    """Extract character names from text using pattern matching."""
    character_counts = {}
    # Pattern 1: "XXX说/道/喊/问/答/笑道/叹道/怒道："" or before quote
    patterns = [
        r'([\u4e00-\u9fa5]{1,4})\s*(?:说道|笑道|冷笑道|叹道|怒道|喊道|问道|答道|叫道|嚷道|低声道|轻声道|淡淡地说|冷冷地说|苦笑道|冷哼|冷声|沉声|厉声|说|道|喊|问|答|叫|嚷)\s*[:：]?\s*[\u201c\u300c\u2018\u300e]',
        r'[\u201d\u300d\u2019\u300f]\s*([\u4e00-\u9fa5]{1,4})\s*(?:说道|笑道|冷笑道|叹道|怒道|喊道|问道|答道|叫道|嚷道|说|道|喊|问|答)\b',
    ]
    skip = {'他', '她', '我', '你', '这', '那', '谁', '什么', '怎么', '如何', '哪里',
            '什么', '为什么', '这里', '那里', '自己', '大家', '别人', '对方', '什么',
            '于是', '突然', '忽然', '这时', '此时', '只见', '可是', '但是', '然后'}
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            name = match.group(1).strip()
            if name not in skip and 1 <= len(name) <= 4:
                character_counts[name] = character_counts.get(name, 0) + 1
    return character_counts


def infer_gender(name):
    """Infer gender from Chinese name (heuristic)."""
    if not name:
        return 'unknown'
    last = name[-1]
    if last in FEMALE_CHARS:
        return 'female'
    if last in MALE_CHARS:
        return 'male'
    # Check common female name patterns
    if any(name.endswith(x) for x in ['儿', '姐', '妹', '姑', '嫂', '妃', '姬', '夫人']):
        return 'female'
    if any(name.endswith(x) for x in ['哥', '弟', '爷', '公', '子', '兄']):
        return 'male'
    return 'unknown'


def auto_assign_voices(characters, narrator_voice=None):
    """Auto-assign voices to detected characters."""
    assignments = {'旁白': narrator_voice or DEFAULT_NARRATOR}
    # Sort by frequency (most common first = main characters)
    sorted_chars = sorted(characters.items(), key=lambda x: -x[1])
    male_idx = 0
    female_idx = 0
    for name, count in sorted_chars:
        gender = infer_gender(name)
        if gender == 'female':
            voice = FEMALE_VOICES[female_idx % len(FEMALE_VOICES)]
            female_idx += 1
        else:
            voice = MALE_VOICES[male_idx % len(MALE_VOICES)]
            male_idx += 1
        assignments[name] = voice
    return assignments


def detect_speaker(text, char_voices):
    """Detect which character is speaking from a dialogue segment."""
    for name in char_voices:
        if name == '旁白':
            continue
        if name in text:
            return name
    return None


# ──────────────────────────── Audio Processing ────────────────────

def has_ffmpeg():
    return shutil.which('ffmpeg') is not None


def get_audio_duration(filepath):
    """Get audio duration in milliseconds using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(filepath)],
            capture_output=True, text=True, timeout=10
        )
        return int(float(result.stdout.strip()) * 1000)
    except Exception:
        return 0


def apply_loudnorm(input_path, output_path):
    """Apply EBU R128 loudness normalization."""
    subprocess.run([
        'ffmpeg', '-y', '-i', str(input_path),
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
        '-ar', '24000',
        str(output_path)
    ], capture_output=True, timeout=120)


def merge_audio_files(file_list, output_path, normalized=True):
    """Merge multiple audio files into one."""
    if not file_list:
        return
    list_file = output_path.parent / f'_concat_{uuid.uuid4().hex[:8]}.txt'
    with open(list_file, 'w', encoding='utf-8') as f:
        for fp in file_list:
            f.write(f"file '{fp}'\n")
    # Concat
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', str(list_file),
        '-c', 'copy',
        str(output_path)
    ], capture_output=True, timeout=300)
    list_file.unlink(missing_ok=True)
    # Normalize
    if normalized and has_ffmpeg():
        tmp = output_path.with_suffix('.norm.wav')
        try:
            apply_loudnorm(output_path, tmp)
            if tmp.exists() and tmp.stat().st_size > 100:
                shutil.move(str(tmp), str(output_path))
        except Exception:
            tmp.unlink(missing_ok=True)


def write_metadata(input_path, output_path, title='', artist='', album='', track=0):
    """Write ID3 metadata using ffmpeg."""
    cmd = ['ffmpeg', '-y', '-i', str(input_path)]
    if title:
        cmd += ['-metadata', f'title={title}']
    if artist:
        cmd += ['-metadata', f'artist={artist}']
    if album:
        cmd += ['-metadata', f'album={album}']
    if track:
        cmd += ['-metadata', f'track={track}']
    cmd += ['-codec', 'copy', str(output_path)]
    subprocess.run(cmd, capture_output=True, timeout=60)


# ──────────────────────────── Main Generator ──────────────────────

class AudiobookGenerator:
    def __init__(self, args):
        self.args = args
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.segments_dir = self.output_dir / 'segments'
        self.segments_dir.mkdir(exist_ok=True)
        self.progress_file = self.output_dir / 'progress.json'
        self.log_file = self.output_dir / 'generation_log.json'
        self.completed = set()
        self.log_entries = []
        # Load progress for resume
        if not getattr(args, 'no_resume', False) and self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    self.completed = set(data.get('completed', []))
                    if self.completed:
                        print(f'  📋 Resuming: {len(self.completed)} segments already done')
            except Exception:
                pass
        # Init TTS client
        backend = getattr(args, 'tts_backend', None) or os.environ.get('TTS_BACKEND', 'edge')
        if backend == 'mimo':
            from mimo_tts_client import MimoTTSClient
            api_key = self._read_env('MIMO_API_KEY')
            if api_key:
                self.tts = MimoTTSClient(api_key=api_key)
            else:
                print('  ⚠️ MIMO_API_KEY not found, falling back to Edge TTS')
                self.tts = EdgeTTSClient()
                backend = 'edge'
        else:
            self.tts = EdgeTTSClient()
        self.backend = backend
        # Load voice catalog for auto-assignment
        catalog_path = Path(__file__).parent.parent / 'data' / 'voice_catalog.json'
        self.voice_catalog = {}
        if catalog_path.exists():
            with open(catalog_path, 'r', encoding='utf-8') as f:
                self.voice_catalog = json.load(f)

    def _read_env(self, key):
        """Read env var from .env file."""
        val = os.environ.get(key, '')
        if val:
            return val
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            for line in env_path.read_text(encoding='utf-8').splitlines():
                if line.strip().startswith(f'{key}='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
        return ''

    def process_novel(self, filepath):
        """Process a novel text file."""
        filepath = Path(filepath)
        text = filepath.read_text(encoding='utf-8')
        print(f'  📖 Read {len(text)} characters from {filepath.name}')

        # Split chapters
        chapters = split_chapters(text)
        print(f'  📑 Found {len(chapters)} chapter(s)')

        # Extract characters across all chapters
        all_chars = extract_characters(text)
        print(f'  🎭 Detected {len(all_chars)} character(s): {", ".join(all_chars.keys())}')

        # Character voice assignment
        char_voices = {}
        if self.args.character_voices:
            char_voices = json.loads(self.args.character_voices)
        else:
            char_voices = auto_assign_voices(all_chars, getattr(self.args, 'narrator_voice', None))
        self.char_voices = char_voices
        # Show assignments
        for name, voice in char_voices.items():
            print(f'      {name} → {voice}')

        # Build segments
        segments = []
        for ch in chapters:
            parts = split_into_segments(ch['content'])
            for seg_type, text in parts:
                if not text.strip():
                    continue
                seg_id = uuid.uuid4().hex[:8]
                if seg_type == 'narration':
                    voice = char_voices.get('旁白', DEFAULT_NARRATOR)
                    role = '旁白'
                else:
                    speaker = detect_speaker(text, char_voices)
                    if speaker:
                        voice = char_voices[speaker]
                        role = speaker
                    else:
                        voice = char_voices.get('旁白', DEFAULT_NARRATOR)
                        role = '旁白'
                segments.append({
                    'id': seg_id,
                    'chapter': ch['index'],
                    'chapter_title': ch['title'],
                    'type': seg_type,
                    'role': role,
                    'voice': voice,
                    'text': text,
                })
        self.segments = segments
        self.chapters = chapters
        print(f'  📝 Split into {len(segments)} segments')
        return segments

    def process_subtitle(self, filepath):
        """Process a subtitle file."""
        filepath = Path(filepath)
        result = parse_subtitle_file(str(filepath))
        print(f'  📄 Parsed {result["total_entries"]} subtitle entries')
        print(f'  🌐 Language: {result["language"]} (confidence: {result.get("language_confidence", 0):.0%})')
        if result['speakers']:
            print(f'  🎭 Speakers: {", ".join(result["speakers"])}')
        dur_s = result['duration_ms'] / 1000
        print(f'  ⏱️ Duration: {int(dur_s//60)}m {int(dur_s%60)}s')

        # Character voice assignment for subtitle speakers
        char_voices = {}
        if self.args.character_voices:
            char_voices = json.loads(self.args.character_voices)
        else:
            narrator_voice = getattr(self.args, 'narrator_voice', None) or DEFAULT_NARRATOR
            char_voices['旁白'] = narrator_voice
            for i, spk in enumerate(result['speakers']):
                gender = infer_gender(spk)
                if gender == 'female':
                    char_voices[spk] = FEMALE_VOICES[i % len(FEMALE_VOICES)]
                else:
                    char_voices[spk] = MALE_VOICES[i % len(MALE_VOICES)]
        self.char_voices = char_voices

        # Build segments from subtitle entries
        segments = []
        for entry in result['entries']:
            if not entry['text'].strip():
                continue
            seg_id = uuid.uuid4().hex[:8]
            speaker = entry['speaker']
            voice = char_voices.get(speaker, char_voices.get('旁白', DEFAULT_NARRATOR))
            segments.append({
                'id': seg_id,
                'chapter': 1,
                'chapter_title': '字幕',
                'type': 'dialogue' if speaker else 'narration',
                'role': speaker or '旁白',
                'voice': voice,
                'text': entry['text'],
                'start_ms': entry['start_ms'],
                'end_ms': entry['end_ms'],
            })
        self.segments = segments
        self.chapters = [{'index': 1, 'title': '字幕', 'content': ''}]
        print(f'  📝 Built {len(segments)} segments')
        return segments

    def generate(self):
        """Generate audio for all segments."""
        segments = self.segments
        if not segments:
            print('  ❌ No segments to generate')
            return

        # Preview mode
        preview_only = getattr(self.args, 'preview_only', False)
        no_preview = getattr(self.args, 'no_preview', False)
        if preview_only:
            segments = segments[:3]
            print(f'  👁️ Preview mode: generating first {len(segments)} segments')
        elif not no_preview and not self.completed:
            # Auto-preview for first-time generation
            preview_segs = segments[:3]
            print(f'  👁️ Generating preview ({len(preview_segs)} segments)...')
            self._generate_segments(preview_segs)
            preview_files = [self.segments_dir / f'{s["id"]}.mp3' for s in preview_segs]
            preview_files = [f for f in preview_files if f.exists()]
            if preview_files and has_ffmpeg():
                preview_out = self.output_dir / 'preview.mp3'
                merge_audio_files(preview_files, preview_out, normalized=True)
                print(f'  ✅ Preview saved: {preview_out}')
                print(f'  👉 Listen and confirm, then run with --no-preview for full generation')
                return
            # Fall through to full generation if preview fails

        # Full generation
        total = len(segments)
        remaining = [s for s in segments if s['id'] not in self.completed]
        if not remaining:
            print(f'  ✅ All {total} segments already completed')
        else:
            print(f'  🎙️ Generating {len(remaining)}/{total} segments (backend: {self.backend})...')

        concurrent = getattr(self.args, 'concurrent', 5) or (3 if self.backend == 'mimo' else 5)
        self._generate_segments(remaining, concurrent)
        print()

        # Merge by chapter
        print('  🔗 Merging chapters...')
        chapter_files = self._merge_chapters()

        # Merge all into final
        if chapter_files and has_ffmpeg():
            fmt = getattr(self.args, 'format', 'mp3') or 'mp3'
            final_name = f'{Path(self.args.output_dir).name}_complete.{fmt}'
            final_path = self.output_dir / final_name
            merge_audio_files(chapter_files, final_path, normalized=True)

            # Write metadata
            if not getattr(self.args, 'no_id3', False) and fmt == 'mp3':
                tmp = final_path.with_suffix('.tagged.mp3')
                write_metadata(final_path, tmp,
                               title='Audiobook',
                               album='Novel2Voice',
                               track=1)
                if tmp.exists() and tmp.stat().st_size > 100:
                    tmp.rename(final_path)

            # Calculate total duration
            dur_ms = get_audio_duration(final_path)
            dur_min = dur_ms / 1000 / 60
            size_mb = final_path.stat().st_size / 1024 / 1024
            print(f'  ✅ Done! {final_path}')
            print(f'     Duration: {int(dur_min)}m {int((dur_min % 1) * 60)}s | Size: {size_mb:.1f} MB')

        # Cleanup segments unless --keep-segments
        if not getattr(self.args, 'keep_segments', False):
            # Keep segments dir but log their presence
            pass

        # Save log
        self._save_log()

    def _generate_segments(self, segments, concurrent=5):
        """Generate audio for a list of segments with concurrency."""
        total = len(segments)
        done_count = len(self.completed)

        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = {}
            for seg in segments:
                if seg['id'] in self.completed:
                    continue
                future = executor.submit(self._generate_one, seg)
                futures[future] = seg

            for future in as_completed(futures):
                seg = futures[future]
                try:
                    result = future.result()
                    if result:
                        self.completed.add(seg['id'])
                        done_count += 1
                        pct = int(done_count / (len(self.segments) or 1) * 100)
                        role_info = f'[{seg["role"]}/{seg["voice"]}]'
                        preview = seg['text'][:30].replace('\n', ' ')
                        print(f'      ✅ {done_count}/{len(self.segments)} ({pct}%) {role_info} "{preview}…"')
                except Exception as e:
                    print(f'      ❌ Segment {seg["id"][:8]} failed: {e}')
                    self.log_entries.append({
                        'id': seg['id'], 'status': 'error', 'error': str(e)
                    })

        # Save progress
        self._save_progress()

    def _generate_one(self, seg):
        """Generate audio for a single segment."""
        out_path = self.segments_dir / f'{seg["id"]}.mp3'
        if out_path.exists() and out_path.stat().st_size > 100:
            return True
        audio = self.tts.synthesize(
            text=seg['text'],
            voice=seg['voice'],
            speed=getattr(self.args, 'speed', 1.0) or 1.0,
            output_format=getattr(self.args, 'format', 'mp3') or 'mp3',
        )
        out_path.write_bytes(audio)
        duration = get_audio_duration(out_path) if has_ffmpeg() else 0
        self.log_entries.append({
            'id': seg['id'],
            'status': 'ok',
            'voice': seg['voice'],
            'role': seg['role'],
            'duration_ms': duration,
            'text_length': len(seg['text']),
        })
        return True

    def _merge_chapters(self):
        """Merge segments into per-chapter files."""
        chapter_groups = {}
        for seg in self.segments:
            ch = seg.get('chapter', 1)
            chapter_groups.setdefault(ch, []).append(seg)

        chapter_files = []
        chapters_dir = self.output_dir / 'chapters'
        chapters_dir.mkdir(exist_ok=True)
        fmt = getattr(self.args, 'format', 'mp3') or 'mp3'

        for ch_idx in sorted(chapter_groups.keys()):
            segs = chapter_groups[ch_idx]
            audio_files = []
            for seg in segs:
                p = self.segments_dir / f'{seg["id"]}.mp3'
                if p.exists():
                    audio_files.append(str(p))
            if not audio_files:
                continue
            ch_title = segs[0].get('chapter_title', f'Chapter {ch_idx}')
            safe_title = re.sub(r'[^\w\u4e00-\u9fff-]', '_', ch_title)[:30]
            ch_file = chapters_dir / f'{ch_idx:03d}_{safe_title}.{fmt}'
            merge_audio_files(audio_files, ch_file, normalized=True)
            # Write metadata
            if not getattr(self.args, 'no_id3', False) and fmt == 'mp3':
                tmp = ch_file.with_suffix('.tagged.mp3')
                write_metadata(ch_file, tmp, title=ch_title, track=ch_idx)
                if tmp.exists() and tmp.stat().st_size > 100:
                    tmp.rename(ch_file)
            chapter_files.append(ch_file)
            seg_count = len(audio_files)
            dur_ms = get_audio_duration(ch_file)
            dur_s = dur_ms / 1000
            print(f'      📁 {ch_file.name} ({seg_count} segments, {int(dur_s//60)}m{int(dur_s%60)}s)')
        return chapter_files

    def _save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump({'completed': list(self.completed)}, f)

    def _save_log(self):
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.log_entries, f, ensure_ascii=False, indent=2)


# ──────────────────────────── CLI ─────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description='Novel2Voice — Convert novel text to multi-character audiobook',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Examples:\n'
               '  python3 generate_audiobook.py --auto novel.txt ./output\n'
               '  python3 generate_audiobook.py --auto novel.txt ./output --character-voices \'{"旁白":"云扬","许七安":"云希"}\'\n'
               '  python3 generate_audiobook.py --subtitle movie.srt ./output\n'
               '  python3 generate_audiobook.py --auto novel.txt ./output --preview-only\n'
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--auto', metavar='FILE', help='Novel text file (auto detect characters)')
    mode.add_argument('--subtitle', metavar='FILE', help='Subtitle file (SRT/ASS)')
    p.add_argument('output_dir', help='Output directory')
    p.add_argument('--tts-backend', choices=['edge', 'mimo'], help='TTS backend')
    p.add_argument('--character-voices', help='JSON: {character: voice_name} mapping')
    p.add_argument('--narrator-voice', help='Narrator voice name (default: 云扬)')
    p.add_argument('--concurrent', type=int, default=5, help='Concurrent requests (default: 5)')
    p.add_argument('--speed', type=float, default=1.0, help='Global speed multiplier (default: 1.0)')
    p.add_argument('--format', choices=['mp3', 'wav', 'ogg'], default='mp3', help='Output format')
    p.add_argument('--bitrate', default='192k', help='MP3 bitrate')
    p.add_argument('--preview-only', action='store_true', help='Only generate first 3 segments (preview)')
    p.add_argument('--no-preview', action='store_true', help='Skip preview, full generation directly')
    p.add_argument('--no-resume', action='store_true', help='Force restart, ignore progress.json')
    p.add_argument('--no-normalize', action='store_true', help='Skip loudnorm normalization')
    p.add_argument('--no-id3', action='store_true', help='Skip ID3 metadata writing')
    p.add_argument('--keep-segments', action='store_true', help='Keep individual segment files')
    # Subtitle-specific
    p.add_argument('--speaker-voices', help='JSON: {speaker: voice} for subtitle mode')
    p.add_argument('--max-speed', type=float, default=2.0, help='Max speed for subtitle alignment')
    p.add_argument('--no-fix-overlaps', action='store_true', help='Disable subtitle overlap fixing')
    p.add_argument('--no-speed-adjust', action='store_true', help='Disable subtitle speed adjustment')
    return p.parse_args()


def main():
    args = parse_args()
    print()
    print('  🎙️  Novel2Voice v2.20.0')
    print('  ──────────────────────────────────────')

    gen = AudiobookGenerator(args)

    if args.subtitle:
        gen.process_subtitle(args.subtitle)
        # Apply speaker voices override
        if args.speaker_voices:
            sv = json.loads(args.speaker_voices)
            gen.char_voices.update(sv)
    else:
        gen.process_novel(args.auto)

    gen.generate()
    print()


if __name__ == '__main__':
    main()
GENEOF

# ── Write voice_samples/index.html ───────────────────────────────
cat << 'HTMLEOF' > "$INSTALL_DIR/scripts/voice_samples/index.html"
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎙️ Voice Catalog — Novel2Voice</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0c0c0e;
  --surface: #161618;
  --surface-hover: #1e1e22;
  --border: #2a2a2e;
  --accent: #e8c547;
  --accent-dim: #b89a30;
  --text: #ece8e0;
  --text-muted: #7a756e;
  --female: #d4789c;
  --male: #6aabdb;
  --dialect: #7cc98a;
  --radius: 8px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Noto Serif SC', serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  line-height: 1.6;
}
.container { max-width: 1100px; margin: 0 auto; padding: 3rem 2rem; }
h1 {
  font-size: 2.4rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  letter-spacing: -0.02em;
}
.subtitle { color: var(--text-muted); font-size: 1rem; margin-bottom: 2rem; }
.search-box {
  width: 100%;
  padding: 0.8rem 1.2rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.95rem;
  margin-bottom: 1.5rem;
  outline: none;
  transition: border-color 0.2s;
}
.search-box:focus { border-color: var(--accent); }
.search-box::placeholder { color: var(--text-muted); }
.filter-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}
.filter-btn {
  padding: 0.4rem 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  color: var(--text-muted);
  font-family: 'Noto Serif SC', serif;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}
.filter-btn:hover { border-color: var(--accent-dim); color: var(--text); }
.filter-btn.active { background: var(--accent); color: var(--bg); border-color: var(--accent); font-weight: 700; }
.section-title {
  font-size: 1.3rem;
  font-weight: 700;
  margin: 2rem 0 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.2rem;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}
.card:hover { border-color: var(--accent-dim); transform: translateY(-1px); background: var(--surface-hover); }
.card.female { border-left: 3px solid var(--female); }
.card.male { border-left: 3px solid var(--male); }
.card.dialect { border-left: 3px solid var(--dialect); }
.card-name {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 0.3rem;
}
.card-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}
.card-meta {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}
.tag {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-size: 0.72rem;
  font-family: 'JetBrains Mono', monospace;
}
.tag-age { background: #2a2a3e; color: #a0a0d0; }
.tag-use { background: #2a3a2a; color: #a0d0a0; }
.card-desc { color: var(--text-muted); font-size: 0.9rem; }
.copy-toast {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%) translateY(100px);
  background: var(--accent);
  color: var(--bg);
  padding: 0.6rem 1.5rem;
  border-radius: var(--radius);
  font-weight: 700;
  font-size: 0.9rem;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: 100;
  pointer-events: none;
}
.copy-toast.show { transform: translateX(-50%) translateY(0); }
.footer {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-top: 4rem;
  padding-top: 2rem;
  border-top: 1px solid var(--border);
}
</style>
</head>
<body>
<div class="container">
  <h1>🎙️ Voice Catalog</h1>
  <p class="subtitle">Novel2Voice — Edge TTS Chinese Voice Reference</p>

  <input class="search-box" type="text" id="search" placeholder="搜索音色名 / 描述 / 场景…" autocomplete="off">

  <div class="filter-bar">
    <button class="filter-btn active" data-filter="all">全部</button>
    <button class="filter-btn" data-filter="female">👩 女声</button>
    <button class="filter-btn" data-filter="male">👨 男声</button>
    <button class="filter-btn" data-filter="dialect">🌍 方言</button>
  </div>

  <div id="voice-list"></div>
</div>

<div class="copy-toast" id="toast">已复制: <span id="toast-name"></span></div>

<div class="footer">
  Novel2Voice v2.20.0 · Edge TTS Voices · Click to copy voice name
</div>

<script>
const voices = {
  female: [
    {name:'晓晓', id:'zh-CN-XiaoxiaoNeural', desc:'清亮标准播音', age:'20-28', use:'旁白/女主'},
    {name:'晓依', id:'zh-CN-XiaoyiNeural', desc:'低沉温柔治愈', age:'25-35', use:'温柔人妻'},
    {name:'晓涵', id:'zh-CN-XiaohanNeural', desc:'文艺清冷', age:'22-30', use:'大家闺秀'},
    {name:'晓墨', id:'zh-CN-XiaomoNeural', desc:'情绪丰富', age:'24-35', use:'虐文女主/侠女'},
    {name:'晓睿', id:'zh-CN-XiaoruiNeural', desc:'稳重厚实中年', age:'45-60', use:'主母/长辈'},
    {name:'晓双', id:'zh-CN-XiaoshuangNeural', desc:'清脆孩童少女', age:'8-14', use:'小丫鬟'},
    {name:'晓梦', id:'zh-CN-XiaomengNeural', desc:'软萌甜妹', age:'16-22', use:'校园学妹'},
  ],
  male: [
    {name:'云希', id:'zh-CN-YunxiNeural', desc:'清爽阳光少年', age:'18-27', use:'少年男主'},
    {name:'云扬', id:'zh-CN-YunyangNeural', desc:'央视浑厚播音', age:'35-55', use:'帝王/旁白'},
    {name:'云健', id:'zh-CN-YunjianNeural', desc:'低沉浑厚大叔', age:'38-55', use:'硬汉/武将'},
    {name:'云夏', id:'zh-CN-YunxiaNeural', desc:'正太少年童声', age:'7-15', use:'幼年男主'},
    {name:'云泽', id:'zh-CN-YunzeNeural', desc:'苍老沉稳', age:'60+', use:'隐世高人/长老'},
    {name:'云枫', id:'zh-CN-YunfengNeural', desc:'平淡务实', age:'28-38', use:'温润男配'},
  ],
  dialect: [
    {name:'云彪', id:'zh-CN-YunbianNeural', desc:'东北方言', dialect:'东北'},
    {name:'晓北', id:'zh-CN-XiaobeiNeural', desc:'东北方言', dialect:'东北'},
    {name:'云登', id:'zh-CN-YundengNeural', desc:'河南方言', dialect:'河南'},
    {name:'云翔', id:'zh-CN-YunxiangNeural', desc:'山东方言', dialect:'山东'},
    {name:'云熙', id:'zh-CN-YunxiNeural', desc:'四川方言', dialect:'四川'},
    {name:'云奇', id:'zh-CN-YunqiNeural', desc:'广西方言', dialect:'广西'},
    {name:'晓妮', id:'zh-CN-XiaoniNeural', desc:'陕西方言', dialect:'陕西'},
  ]
};

const container = document.getElementById('voice-list');
const searchInput = document.getElementById('search');
const toast = document.getElementById('toast');
const toastName = document.getElementById('toast-name');
let activeFilter = 'all';

function copyName(name) {
  navigator.clipboard.writeText(name).catch(()=>{});
  toastName.textContent = name;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 1500);
}

function renderCard(v, type) {
  const cls = type === 'female' ? 'female' : type === 'male' ? 'male' : 'dialect';
  let tags = '';
  if (v.age) tags += `<span class="tag tag-age">${v.age}</span>`;
  if (v.use) tags += `<span class="tag tag-use">${v.use}</span>`;
  if (v.dialect) tags += `<span class="tag tag-use">${v.dialect}</span>`;
  return `<div class="card ${cls}" onclick="copyName('${v.name}')" title="点击复制">
    <div class="card-name">${v.name}</div>
    <div class="card-id">${v.id}</div>
    <div class="card-meta">${tags}</div>
    <div class="card-desc">${v.desc}</div>
  </div>`;
}

function render() {
  const q = searchInput.value.toLowerCase();
  let html = '';

  const sections = [
    {key:'female', title:'👩 女声', data: voices.female, filter:'female'},
    {key:'male', title:'👨 男声', data: voices.male, filter:'male'},
    {key:'dialect', title:'🌍 方言', data: voices.dialect, filter:'dialect'},
  ];

  for (const sec of sections) {
    if (activeFilter !== 'all' && activeFilter !== sec.filter) continue;
    const filtered = sec.data.filter(v =>
      !q || v.name.includes(q) || v.id.toLowerCase().includes(q)
        || (v.desc||'').includes(q) || (v.use||'').includes(q)
        || (v.dialect||'').includes(q)
    );
    if (!filtered.length) continue;
    html += `<div class="section-title">${sec.title}</div>`;
    html += `<div class="grid">${filtered.map(v => renderCard(v, sec.key)).join('')}</div>`;
  }

  container.innerHTML = html || '<p style="color:var(--text-muted)">没有匹配的音色</p>';
}

searchInput.addEventListener('input', render);
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.dataset.filter;
    render();
  });
});

render();
</script>
</body>
</html>
HTMLEOF

# ── Write README.md ──────────────────────────────────────────────
cat << 'READMEEOF' > "$INSTALL_DIR/README.md"
# 🎙️ Novel2Voice

小说文本 → 多角色有声书。支持 500+ 音色、自动角色识别、情感标注、字幕转语音。

## 快速开始

```bash
# 1. 生成有声书（自动模式）
python3 scripts/generate_audiobook.py --auto novel.txt ./output

# 2. 指定角色音色
python3 scripts/generate_audiobook.py --auto novel.txt ./output \
  --character-voices '{"旁白":"云扬","许七安":"云希","洛玉衡":"晓涵"}'

# 3. 字幕转语音
python3 scripts/generate_audiobook.py --subtitle movie.srt ./output

# 4. 仅预览（前 30 秒）
python3 scripts/generate_audiobook.py --auto novel.txt ./output --preview-only
```

## 环境要求

- Python 3.8+
- ffmpeg（可选，用于 MP3 输出和音频处理）
- 网络连接（调用 TTS API）

## 音色试听

用浏览器打开 `scripts/voice_samples/index.html`，搜索、筛选、点击复制音色名。

## 文档

完整说明见 `skill.md`。

## 许可

MIT License
READMEEOF

# ── Make scripts executable ──────────────────────────────────────
chmod +x "$INSTALL_DIR/scripts/generate_audiobook.py"
chmod +x "$INSTALL_DIR/scripts/subtitle_parser.py"
chmod +x "$INSTALL_DIR/scripts/edge_tts_client.py"
chmod +x "$INSTALL_DIR/scripts/mimo_tts_client.py"

# ── Copy skill.md if exists in current dir ───────────────────────
if [ -f "$SCRIPT_DIR/skill.md" ] && [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    cp "$SCRIPT_DIR/skill.md" "$INSTALL_DIR/skill.md"
fi

# ── Verify installation ──────────────────────────────────────────
echo "  [4/5] Verifying installation..."
ERRORS=0
for f in generate_audiobook.py subtitle_parser.py edge_tts_client.py mimo_tts_client.py; do
    if [ -f "$INSTALL_DIR/scripts/$f" ]; then
        python3 -c "import ast; ast.parse(open('$INSTALL_DIR/scripts/$f').read())" 2>/dev/null && \
            echo "        ✅ $f" || { echo "        ❌ $f (syntax error)"; ERRORS=$((ERRORS+1)); }
    else
        echo "        ❌ $f (missing)"; ERRORS=$((ERRORS+1))
    fi
done
[ -f "$INSTALL_DIR/data/voice_catalog.json" ] && echo "        ✅ voice_catalog.json" || echo "        ⚠️ voice_catalog.json missing"
[ -f "$INSTALL_DIR/.env" ] && echo "        ✅ .env" || echo "        ⚠️ .env missing"
[ -f "$INSTALL_DIR/scripts/voice_samples/index.html" ] && echo "        ✅ voice_samples/index.html" || echo "        ⚠️ index.html missing"

# ── Summary ──────────────────────────────────────────────────────
echo ""
echo "  [5/5] Installation complete!"
echo ""
echo "  ═══════════════════════════════════════════════════════════"
echo "  📁 Location: $INSTALL_DIR"
echo ""
echo "  📂 Structure:"
echo "     ├── skill.md                    # Full documentation"
echo "     ├── .env                        # API configuration"
echo "     ├── README.md                   # Quick start"
echo "     ├── scripts/"
echo "     │   ├── generate_audiobook.py   # Main generator"
echo "     │   ├── subtitle_parser.py      # SRT/ASS parser"
echo "     │   ├── edge_tts_client.py      # Edge TTS API"
echo "     │   ├── mimo_tts_client.py      # MiMo TTS API"
echo "     │   └── voice_samples/"
echo "     │       └── index.html          # Voice browser"
echo "     ├── data/"
echo "     │   └── voice_catalog.json      # Voice data"
echo "     └── output/                     # Generated files"
echo ""
echo "  🚀 Quick Start:"
echo "     cd $INSTALL_DIR"
echo "     python3 scripts/generate_audiobook.py --auto your_novel.txt ./output"
echo ""
echo "  🎧 Voice Browser:"
echo "     Open scripts/voice_samples/index.html in your browser"
echo ""
echo "  📖 Full docs: skill.md"
echo "  ═══════════════════════════════════════════════════════════"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo "  ⚠️ $ERRORS file(s) had issues. Check output above."
    exit 1
fi
```