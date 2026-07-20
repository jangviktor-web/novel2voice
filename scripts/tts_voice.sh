#!/bin/bash
# tts_voice.sh — TTS 客户端（支持 MiMo 和 Edge TTS 双后端）
# Usage: bash tts_voice.sh <text> <output_path> [style] [voice_name] [speed] [pitch] [style_degree] [role]
#
# Arguments:
#   text          Text to synthesize (required)
#   output_path   Destination WAV file (required)
#   style         Natural-language style phrase (optional)
#   voice_name    TTS voice name (optional, default: mimo_default)
#                 Edge TTS voices: zh-CN-XiaoxiaoNeural, en-US-JennyNeural, etc.
#   speed         Speech speed multiplier 0.5~2.0 (optional, default: 1.0)
#   pitch         Pitch multiplier 0.5~1.5 (optional, default: 1.0, Edge TTS only)
#   style_degree  Style intensity 0.01~2.0 (optional, default: 1.0, Edge TTS only)
#   role          Voice role (optional, e.g. Boy, Girl, Narrator, Edge TTS only)
#
# Available MiMo voices: mimo_default, 冰糖, 茉莉, 苏打, 白桦, Mia, Chloe, Milo, Dean
# Edge TTS voices: any {locale}-{Name}Neural (e.g. zh-CN-XiaoxiaoNeural, en-US-JennyNeural)
# Male voices: Milo, Dean
# Female voices: mimo_default, 冰糖, 茉莉, 苏打, 白桦, Mia, Chloe
#
# Env:
#   TTS_BACKEND       — Force backend: mimo / edge / auto (default: auto)
#   MIMO_API_KEY      — MiMo API key
#   MIMO_API_BASE_URL — MiMo API base URL
#   MIMO_TTS_MODEL    — MiMo TTS model name
#   EDGE_TTS_ENDPOINT — Edge TTS endpoint (default: https://tts.kalaok.cc.cd/v1/audio/speech)
#   EDGE_TTS_KEY      — Edge TTS key (required, set via environment variable)

set -euo pipefail

TEXT="${1:-}"
OUTPUT="${2:-}"
STYLE="${3:-}"
VOICE="${4:-mimo_default}"
SPEED="${5:-1.0}"
PITCH="${6:-1.0}"
STYLE_DEGREE="${7:-1.0}"
ROLE="${8:-}"

if [[ -z "$TEXT" ]]; then
  echo "Error: <text> is required" >&2; exit 1
fi
if [[ -z "$OUTPUT" ]]; then
  echo "Error: <output_path> is required" >&2; exit 1
fi

# Edge TTS config
EDGE_TTS_ENDPOINT="${EDGE_TTS_ENDPOINT:-https://tts.kalaok.cc.cd/v1/audio/speech}"
EDGE_TTS_KEY="${EDGE_TTS_KEY:-}"

# ============================================================
# Resolve MiMo API key
# ============================================================

MIMO_KEY="${MIMO_API_KEY:-}"
if [[ -z "$MIMO_KEY" ]]; then
  _OPENCLAW="$HOME/.openclaw/openclaw.json"
  if [[ -f "$_OPENCLAW" ]]; then
    MIMO_KEY=$(python3 - "$_OPENCLAW" <<'PYEOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d['models']['providers']['xiaomi']['apiKey'])
except (KeyError, TypeError):
    sys.exit(1)
PYEOF
) || true
  fi
fi

# ============================================================
# Determine backend
# ============================================================

TTS_BACKEND="${TTS_BACKEND:-auto}"

if [[ "$TTS_BACKEND" == "auto" ]]; then
  if [[ -n "$MIMO_KEY" ]]; then
    TTS_BACKEND="mimo"
  else
    TTS_BACKEND="edge"
    echo "Info: MiMo API key not found, using Edge TTS" >&2
  fi
fi

# ============================================================
# Edge TTS function
# ============================================================

call_edge_tts() {
  local work_dir
  work_dir=$(mktemp -d)

  # Auto-map MiMo voice names → Edge TTS equivalents
  local original_voice="$VOICE"
  case "$VOICE" in
    mimo_default) VOICE="zh-CN-XiaoxiaoNeural" ;;
    冰糖)         VOICE="zh-CN-XiaoxiaoNeural" ;;
    茉莉)         VOICE="zh-CN-XiaomoNeural" ;;
    Mia)          VOICE="zh-CN-XiaoyiNeural" ;;
    Chloe)        VOICE="zh-CN-XiaohanNeural" ;;
    苏打)         VOICE="zh-CN-YunxiNeural" ;;
    白桦)         VOICE="zh-CN-YunzeNeural" ;;
    Dean)         VOICE="zh-CN-YunjianNeural" ;;
    Milo)         VOICE="zh-CN-YunxiNeural" ;;
  esac
  if [[ "$VOICE" != "$original_voice" ]]; then
    echo "Info: Mapped MiMo voice '$original_voice' → Edge TTS '$VOICE'" >&2
  fi

  # Build payload using Python (cleaner conditional JSON construction)
  local payload
  payload=$(python3 -c "
import json, sys
p = {
    'model': 'tts-1',
    'input': sys.argv[1],
    'voice': sys.argv[2],
    'response_format': 'wav',
    'speed': float(sys.argv[3]),
}
style = sys.argv[4]
pitch = float(sys.argv[5])
style_degree = float(sys.argv[6])
role = sys.argv[7]
if style:
    p['style'] = style
if pitch != 1.0:
    p['pitch'] = pitch
if style_degree != 1.0:
    p['style_degree'] = style_degree
if role:
    p['role'] = role
p['cleaning_options'] = {
    'remove_markdown': True,
    'remove_emoji': True,
    'remove_urls': True,
    'remove_line_breaks': False,
    'remove_citation_numbers': True,
}
print(json.dumps(p))
" "$TEXT" "$VOICE" "$SPEED" "$STYLE" "$PITCH" "$STYLE_DEGREE" "$ROLE")

  local http_code=""
  local max_attempts=3
  for attempt in $(seq 1 "$max_attempts"); do
    http_code=$(curl -s -w "%{http_code}" \
      -o "$work_dir/audio.wav" \
      --max-time 120 \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $EDGE_TTS_KEY" \
      -d "$payload" \
      "$EDGE_TTS_ENDPOINT") || http_code="000"

    [[ "$http_code" == "200" ]] && break

    if [[ "$http_code" =~ ^5 ]] || [[ "$http_code" == "429" ]] || [[ "$http_code" == "000" ]]; then
      if [[ "$attempt" -lt "$max_attempts" ]]; then
        sleep $((2 ** (attempt - 1)))
        continue
      fi
    else
      echo "Error: Edge TTS returned HTTP $http_code" >&2
      cat "$work_dir/audio.wav" >&2 2>/dev/null || true
      rm -rf "$work_dir"
      return 1
    fi
  done

  if [[ "$http_code" != "200" ]]; then
    echo "Error: Edge TTS failed after $max_attempts attempts" >&2
    rm -rf "$work_dir"
    return 1
  fi

  # Check if response is already WAV or raw PCM
  local file_size
  file_size=$(stat -c%s "$work_dir/audio.wav" 2>/dev/null || stat -f%z "$work_dir/audio.wav" 2>/dev/null || echo 0)
  if [[ "$file_size" -lt 100 ]]; then
    echo "Error: Edge TTS returned empty audio" >&2
    rm -rf "$work_dir"
    return 1
  fi

  # Check if it's already a WAV file
  local header
  header=$(head -c 4 "$work_dir/audio.wav" | xxd -p 2>/dev/null || echo "")
  if [[ "$header" != "52494646" ]]; then
    # Not WAV, wrap raw PCM as WAV
    python3 - "$work_dir/audio.wav" "$OUTPUT" <<'PYEOF'
import struct, io, sys
in_path = sys.argv[1]
out_path = sys.argv[2]
with open(in_path, 'rb') as f:
    raw = f.read()
sr, ch, bps = 24000, 1, 16
br = sr * ch * bps // 8
buf = io.BytesIO()
buf.write(b'RIFF')
buf.write(struct.pack('<I', 36 + len(raw)))
buf.write(b'WAVEfmt ')
buf.write(struct.pack('<IHHIIHH', 16, 1, ch, sr, br, ch * bps // 8, bps))
buf.write(b'data')
buf.write(struct.pack('<I', len(raw)))
buf.write(raw)
with open(out_path, 'wb') as f:
    f.write(buf.getvalue())
PYEOF
  else
    cp "$work_dir/audio.wav" "$OUTPUT"
  fi

  rm -rf "$work_dir"

  if [[ ! -s "$OUTPUT" ]]; then
    echo "Error: output file is empty" >&2
    return 1
  fi

  echo "OK (Edge TTS): $(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT" 2>/dev/null) bytes written to $OUTPUT"
  return 0
}

# ============================================================
# MiMo TTS function
# ============================================================

call_mimo_tts() {
  if [[ -z "$MIMO_KEY" ]]; then
    echo "Error: MiMo API key not found" >&2
    return 1
  fi

  local work_dir
  work_dir=$(mktemp -d)

  TTS_ENDPOINT="${MIMO_API_BASE_URL:-https://api.xiaomimimo.com/v1}"
  TTS_ENDPOINT="${TTS_ENDPOINT%/}/chat/completions"
  MODEL="${MIMO_TTS_MODEL:-mimo-v2.5-tts}"

  # Build payload
  local payload
  if [[ -n "$STYLE" ]]; then
    payload=$(jq -n \
      --arg model "$MODEL" \
      --arg content "$TEXT" \
      --arg style "$STYLE" \
      --arg voice "$VOICE" \
      '{model: $model,
        audio: {format: "wav", voice: $voice},
        messages: [
          {role: "user", content: $style},
          {role: "assistant", content: $content}
        ]}')
  else
    payload=$(jq -n \
      --arg model "$MODEL" \
      --arg content "$TEXT" \
      --arg voice "$VOICE" \
      '{model: $model,
        audio: {format: "wav", voice: $voice},
        messages: [{role: "assistant", content: $content}]}')
  fi

  # Call API with retry
  local http_code=""
  local max_attempts=3
  for attempt in $(seq 1 "$max_attempts"); do
    http_code=$(curl -s -w "%{http_code}" \
      -o "$work_dir/resp.json" \
      --max-time 120 \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $MIMO_KEY" \
      -d "$payload" \
      "$TTS_ENDPOINT") || http_code="000"

    [[ "$http_code" == "200" ]] && break

    local retryable=0
    if [[ "$http_code" =~ ^5 ]] || [[ "$http_code" == "429" ]] || [[ "$http_code" == "000" ]]; then
      retryable=1
    elif [[ "$http_code" == "401" ]] || [[ "$http_code" == "403" ]]; then
      echo "Error: MiMo API key invalid (HTTP $http_code)" >&2
      rm -rf "$work_dir"
      return 1
    elif [[ "$http_code" =~ ^4 ]]; then
      grep -qiE 'request failed|returned empty text|timeout|try again' "$work_dir/resp.json" 2>/dev/null && retryable=1
    fi

    if [[ "$retryable" -eq 1 && "$attempt" -lt "$max_attempts" ]]; then
      sleep $((2 ** (attempt - 1)))
      continue
    fi
    break
  done

  if [[ "$http_code" != "200" ]]; then
    echo "Error: MiMo returned HTTP $http_code after ${attempt:-1} attempt(s)" >&2
    cat "$work_dir/resp.json" >&2 2>/dev/null || true
    rm -rf "$work_dir"
    return 1
  fi

  # Decode audio
  python3 - "$work_dir/resp.json" "$OUTPUT" <<'PYEOF'
import json, base64, struct, io, sys

resp_path = sys.argv[1]
out_path = sys.argv[2]

with open(resp_path) as f:
    data = json.load(f)

if data.get('error'):
    print(f'Error: {data["error"]}', file=sys.stderr)
    sys.exit(2)

try:
    audio = data['choices'][0]['message']['audio']
    raw = base64.b64decode(audio['data'])
except (KeyError, IndexError, TypeError) as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(2)

if raw[:4] == b'RIFF':
    wav_bytes = raw
else:
    sr, bps, ch = 24000, 16, 1
    br = sr * ch * bps // 8
    buf = io.BytesIO()
    buf.write(b'RIFF')
    buf.write(struct.pack('<I', 36 + len(raw)))
    buf.write(b'WAVEfmt ')
    buf.write(struct.pack('<IHHIIHH', 16, 1, ch, sr, br, ch * bps // 8, bps))
    buf.write(b'data')
    buf.write(struct.pack('<I', len(raw)))
    buf.write(raw)
    wav_bytes = buf.getvalue()

with open(out_path, 'wb') as f:
    f.write(wav_bytes)

print(f'OK (MiMo): {len(wav_bytes)} bytes written to {out_path}')
PYEOF
  if [[ $? -ne 0 ]]; then
    rm -rf "$work_dir"
    return 1
  fi

  rm -rf "$work_dir"

  if [[ ! -s "$OUTPUT" ]]; then
    echo "Error: output file is empty" >&2
    return 1
  fi

  return 0
}

# ============================================================
# Main: call backend with fallback
# ============================================================

if [[ "$TTS_BACKEND" == "mimo" ]]; then
  if call_mimo_tts; then
    exit 0
  else
    echo "Warning: MiMo failed, falling back to Edge TTS" >&2
    if call_edge_tts; then
      exit 0
    else
      exit 2
    fi
  fi
elif [[ "$TTS_BACKEND" == "edge" ]]; then
  if call_edge_tts; then
    exit 0
  else
    exit 2
  fi
else
  echo "Error: unknown backend '$TTS_BACKEND'" >&2
  exit 1
fi
