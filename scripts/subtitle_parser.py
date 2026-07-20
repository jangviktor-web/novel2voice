#!/usr/bin/env python3
"""
subtitle_parser.py — 字幕文件解析器
支持 SRT / ASS (SSA) 格式，输出标准化 segments 列表

Usage:
    from subtitle_parser import parse_subtitle
    segments = parse_subtitle("subtitle.srt")
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


def _read_file_with_encoding(filepath):
    """Read file with encoding fallback chain"""
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb2312", "big5", "shift_jis", "euc-kr", "latin-1"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                content = f.read()
            return content
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Cannot decode file with any supported encoding: {filepath}")


@dataclass
class SubtitleEntry:
    """单条字幕"""
    index: int
    start_ms: int          # 起始时间（毫秒）
    end_ms: int            # 结束时间（毫秒）
    text: str              # 文本内容（已清理标签）
    raw_text: str          # 原始文本（含标签）
    style: str = ""        # ASS 样式名
    speaker: str = ""      # 说话人（ASS 中 {} 内标注）
    position: str = ""     # 位置信息（ASS \pos 标签）

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    @property
    def start_time(self) -> str:
        return ms_to_srt_time(self.start_ms)

    @property
    def end_time(self) -> str:
        return ms_to_srt_time(self.end_ms)


def ms_to_srt_time(ms: int) -> str:
    """毫秒 → SRT 时间格式 HH:MM:SS,mmm"""
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"


def srt_time_to_ms(time_str: str) -> int:
    """SRT 时间格式 → 毫秒  HH:MM:SS,mmm 或 HH:MM:SS.mmm"""
    time_str = time_str.replace(",", ".")
    parts = time_str.strip().split(":")
    h, m = int(parts[0]), int(parts[1])
    s_parts = parts[2].split(".")
    s = int(s_parts[0])
    ms = int(s_parts[1]) if len(s_parts) > 1 else 0
    return h * 3600000 + m * 60000 + s * 1000 + ms


def ass_time_to_ms(time_str: str) -> int:
    """ASS 时间格式 → 毫秒  H:MM:SS.cc (centiseconds)"""
    time_str = time_str.strip()
    parts = time_str.split(":")
    h = int(parts[0])
    m = int(parts[1])
    s_cs = parts[2].split(".")
    s = int(s_cs[0])
    cs = int(s_cs[1]) if len(s_cs) > 1 else 0
    return h * 3600000 + m * 60000 + s * 1000 + cs * 10


def strip_ass_tags(text: str) -> Tuple[str, str, str]:
    """
    清理 ASS 标签，返回 (clean_text, speaker, position)
    ASS 标签格式: {\\an8}文字 或 {\\pos(x,y)}文字 或 {\\kf0}文字
    说话人标注: {Actor:角色名} 或 {\\N}换行
    """
    speaker = ""
    position = ""

    # 提取说话人: {Actor:xxx} 或前面的 "xxx:" 格式
    actor_match = re.search(r'\{\\actor[:\s]*(.+?)\}', text, re.IGNORECASE)
    if actor_match:
        speaker = actor_match.group(1).strip()
        text = re.sub(r'\{\\actor[:\s]*.+?\}', '', text, flags=re.IGNORECASE)

    # 提取位置标签
    pos_match = re.search(r'\{\\pos\((\d+),(\d+)\)\}', text)
    if pos_match:
        position = f"{pos_match.group(1)},{pos_match.group(2)}"

    # 去掉所有 ASS override 标签 {...}
    clean = re.sub(r'\{[^}]*\}', '', text)

    # 去掉换行标签
    clean = clean.replace("\\N", "\n").replace("\\n", "\n")

    # 去掉首尾空白
    clean = clean.strip()

    return clean, speaker, position


def strip_html_tags(text: str) -> str:
    """去掉 HTML 风格标签（常见于某些字幕）"""
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def clean_subtitle_text(text: str, is_ass: bool = False) -> Tuple[str, str, str]:
    """统一清理字幕文本"""
    if is_ass:
        return strip_ass_tags(text)
    else:
        return strip_html_tags(text), "", ""


# ============================================================
# SRT 解析
# ============================================================

def parse_srt(filepath: str) -> List[SubtitleEntry]:
    """解析 SRT 字幕文件"""
    content = _read_file_with_encoding(filepath)

    entries = []

    # SRT 格式：序号 + 时间行 + 文本块（空行分隔）
    blocks = re.split(r'\n\s*\n', content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue

        # 第一行是序号
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue

        # 第二行是时间
        time_match = re.match(
            r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})',
            lines[1].strip()
        )
        if not time_match:
            continue

        start_ms = srt_time_to_ms(time_match.group(1))
        end_ms = srt_time_to_ms(time_match.group(2))

        # 剩余行是文本
        raw_text = '\n'.join(lines[2:])
        clean_text, speaker, position = clean_subtitle_text(raw_text, is_ass=False)

        if not clean_text:
            continue

        entries.append(SubtitleEntry(
            index=index,
            start_ms=start_ms,
            end_ms=end_ms,
            text=clean_text,
            raw_text=raw_text,
            speaker=speaker,
            position=position,
        ))

    entries.sort(key=lambda e: e.start_ms)
    return entries


# ============================================================
# ASS / SSA 解析
# ============================================================

def parse_ass(filepath: str) -> List[SubtitleEntry]:
    """解析 ASS/SSA 字幕文件"""
    content = _read_file_with_encoding(filepath)

    entries = []
    in_events = False
    format_fields = []

    for line in content.split('\n'):
        line = line.strip()

        # 进入 [Events] 段
        if line.lower() == '[events]':
            in_events = True
            continue

        # 进入其他段落则退出
        if line.startswith('[') and line.endswith(']'):
            in_events = False
            continue

        if not in_events:
            continue

        # 解析 Format 行
        if line.lower().startswith('format:'):
            format_fields = [f.strip().lower() for f in line[7:].split(',')]
            continue

        # 解析 Dialogue 行
        if not line.lower().startswith('dialogue:'):
            continue

        # 去掉 "Dialogue: " 前缀
        _, _, rest = line.partition(':')
        # Dialogue 行的格式：Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
        # 但 Text 可能包含逗号，所以需要按字段数拆分
        parts = rest.split(',')

        # 前面固定字段数 = len(format_fields) - 1（Text 是最后一个字段）
        if len(format_fields) == 0:
            # 默认 ASS 格式
            format_fields = ['layer', 'start', 'end', 'style', 'name',
                             'marginl', 'marginr', 'marginv', 'effect', 'text']

        fixed_count = len(format_fields) - 1
        if len(parts) < fixed_count:
            continue

        fixed_parts = parts[:fixed_count]
        text_part = ','.join(parts[fixed_count:])

        # 从 format_fields 中找到各字段位置
        field_map = {name: i for i, name in enumerate(format_fields)}

        try:
            start_str = fixed_parts[field_map.get('start', 1)]
            end_str = fixed_parts[field_map.get('end', 2)]
            style_name = fixed_parts[field_map.get('style', 3)].strip()
            speaker_name = fixed_parts[field_map.get('name', 4)].strip()
        except (IndexError, KeyError):
            continue

        try:
            start_ms = ass_time_to_ms(start_str)
            end_ms = ass_time_to_ms(end_str)
        except (IndexError, ValueError):
            continue  # Skip malformed Dialogue lines

        raw_text = text_part
        clean_text, extracted_speaker, position = clean_subtitle_text(text_part, is_ass=True)

        # 优先用 Name 字段的说话人
        speaker = speaker_name or extracted_speaker

        if not clean_text:
            continue

        entries.append(SubtitleEntry(
            index=len(entries) + 1,
            start_ms=start_ms,
            end_ms=end_ms,
            text=clean_text,
            raw_text=raw_text,
            style=style_name,
            speaker=speaker,
            position=position,
        ))

    entries.sort(key=lambda e: e.start_ms)
    return entries


# ============================================================
# 统一入口
# ============================================================

def parse_subtitle(filepath: str) -> List[SubtitleEntry]:
    """
    自动检测格式并解析字幕文件
    返回: List[SubtitleEntry]
    """
    # 根据文件扩展名判断
    ext = filepath.rsplit('.', 1)[-1].lower() if '.' in filepath else ''

    if ext in ('ass', 'ssa'):
        return parse_ass(filepath)
    elif ext == 'srt':
        return parse_srt(filepath)
    else:
        # 尝试 SRT 解析，失败则尝试 ASS
        srt_error = None
        try:
            entries = parse_srt(filepath)
            if entries:
                return entries
        except FileNotFoundError:
            raise
        except Exception as e:
            srt_error = e

        try:
            entries = parse_ass(filepath)
            if entries:
                return entries
        except FileNotFoundError:
            raise
        except Exception:
            pass

        if srt_error:
            raise ValueError(f"Failed to parse subtitle file (tried SRT and ASS): {srt_error}")
        raise ValueError(f"Could not parse subtitle file as SRT or ASS: {filepath}")


def get_speakers(entries: List[SubtitleEntry]) -> List[str]:
    """提取所有不重复的说话人"""
    speakers = []
    seen = set()
    for e in entries:
        sp = e.speaker or ""
        if sp and sp not in seen:
            speakers.append(sp)
            seen.add(sp)
    return speakers


def entries_to_segments(entries: List[SubtitleEntry],
                        speaker_voice_map: dict = None,
                        speaker_style_map: dict = None,
                        default_voice: str = "mimo_default",
                        default_style: str = "",
                        strip_punctuation: bool = True) -> dict:
    """
    将字幕条目转换为 generate_audiobook.py 可用的 segments.json 格式

    speaker_voice_map: {"角色名": "voice_id"}
    speaker_style_map: {"角色名": "style_string"}
    strip_punctuation: 是否去掉句末标点（TTS 有时标点会影响语调）
    """
    if speaker_voice_map is None:
        speaker_voice_map = {}
    if speaker_style_map is None:
        speaker_style_map = {}

    voices = {"narrator": default_voice}
    styles = {"narrator": default_style}
    segments = []

    for i, entry in enumerate(entries):
        text = entry.text
        if strip_punctuation:
            # 保留省略号，去掉其他句末标点
            text = re.sub(r'[。！？!?.]+$', '', text).strip()

        if not text:
            continue

        speaker = entry.speaker or "narrator"
        voice = speaker_voice_map.get(speaker, default_voice)
        style = speaker_style_map.get(speaker, default_style)

        voices[speaker] = voice
        styles[speaker] = style

        # 计算与下一条字幕的间隔作为停顿
        pause_after = 0
        if i < len(entries) - 1:
            gap = entries[i + 1].start_ms - entry.end_ms
            # 限制停顿范围：100ms ~ 3000ms
            pause_after = max(100, min(3000, gap))

        segments.append({
            "text": text,
            "char": speaker,
            "pause_after": pause_after,
            # 保留时间轴信息用于精确对齐
            "_start_ms": entry.start_ms,
            "_end_ms": entry.end_ms,
            "_duration_ms": entry.duration_ms,
        })

    return {
        "title": "subtitle_audio",
        "voices": voices,
        "styles": styles,
        "chapters": [{"title": "subtitle", "segments": segments}],
        "_subtitle_mode": True,
        "_total_entries": len(entries),
    }


# ============================================================
# 语言检测
# ============================================================

def detect_language(entries: List[SubtitleEntry], sample_size: int = 50) -> dict:
    """
    检测字幕文本的主要语言。
    返回: {"primary": "zh"|"ja"|"ko"|"en"|..., "confidence": 0.0~1.0, "breakdown": {...}}

    检测逻辑：按 Unicode 字符区间统计字符频率
    - CJK 统一汉字 → zh (中文)
    - 平假名/片假名 → ja (日语)
    - 谚文 → ko (韩语)
    - 拉丁字母 → en (英语，不细分西欧语言)
    - 西里尔字母 → ru (俄语)
    - 阿拉伯字母 → ar (阿拉伯语)
    - 泰文 → th (泰语)
    """
    # 采样（取前 sample_size 条非空字幕）
    sample_texts = []
    for e in entries:
        if e.text.strip():
            sample_texts.append(e.text)
        if len(sample_texts) >= sample_size:
            break

    if not sample_texts:
        return {"primary": "unknown", "confidence": 0.0, "breakdown": {}}

    full_text = "".join(sample_texts)

    # 字符区间计数
    counts = {
        "cjk": 0,       # CJK 统一汉字 (中文)
        "hiragana": 0,   # 平假名
        "katakana": 0,   # 片假名
        "hangul": 0,     # 谚文音节
        "latin": 0,      # 拉丁字母
        "cyrillic": 0,   # 西里尔字母
        "arabic": 0,     # 阿拉伯字母
        "thai": 0,       # 泰文
        "other": 0,      # 其他（标点、数字等）
    }

    for ch in full_text:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            counts["cjk"] += 1
        elif 0x3040 <= cp <= 0x309F:
            counts["hiragana"] += 1
        elif 0x30A0 <= cp <= 0x30FF:
            counts["katakana"] += 1
        elif 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF or 0x3130 <= cp <= 0x318F:
            counts["hangul"] += 1
        elif 0x0041 <= cp <= 0x024F:
            counts["latin"] += 1
        elif 0x0400 <= cp <= 0x04FF:
            counts["cyrillic"] += 1
        elif 0x0600 <= cp <= 0x06FF:
            counts["arabic"] += 1
        elif 0x0E00 <= cp <= 0x0E7F:
            counts["thai"] += 1
        else:
            counts["other"] += 1

    # 日语 = CJK + 假名（假名出现即判定为日语）
    kana_total = counts["hiragana"] + counts["katakana"]
    if kana_total > 0:
        # 有假名 → 日语
        jp_total = counts["cjk"] + kana_total
        total = sum(counts.values()) - counts["other"]
        if total == 0:
            total = 1
        return {
            "primary": "ja",
            "confidence": round(jp_total / max(total, 1), 2),
            "breakdown": counts,
        }

    # 韩语
    if counts["hangul"] > 0:
        total = sum(counts.values()) - counts["other"]
        if total == 0:
            total = 1
        return {
            "primary": "ko",
            "confidence": round(counts["hangul"] / max(total, 1), 2),
            "breakdown": counts,
        }

    # 纯 CJK → 中文
    if counts["cjk"] > 0 and counts["latin"] == 0:
        total = sum(counts.values()) - counts["other"]
        if total == 0:
            total = 1
        return {
            "primary": "zh",
            "confidence": round(counts["cjk"] / max(total, 1), 2),
            "breakdown": counts,
        }

    # CJK + Latin 混合 → 仍判中文（常见中英混排）
    if counts["cjk"] > counts["latin"]:
        total = sum(counts.values()) - counts["other"]
        if total == 0:
            total = 1
        return {
            "primary": "zh",
            "confidence": round(counts["cjk"] / max(total, 1), 2),
            "breakdown": counts,
        }

    # 其他语言按最大计数
    lang_map = {
        "latin": "en",
        "cyrillic": "ru",
        "arabic": "ar",
        "thai": "th",
        "cjk": "zh",
    }
    best_key = max(counts, key=counts.get)
    if best_key in lang_map:
        total = sum(counts.values()) - counts["other"]
        if total == 0:
            total = 1
        return {
            "primary": lang_map[best_key],
            "confidence": round(counts[best_key] / max(total, 1), 2),
            "breakdown": counts,
        }

    return {"primary": "unknown", "confidence": 0.0, "breakdown": counts}


# ============================================================
# 时间轴重叠检测与修复
# ============================================================

def detect_overlaps(entries: List[SubtitleEntry]) -> List[dict]:
    """
    检测时间轴重叠的字幕条目。
    返回: [{"index_a": i, "index_b": j, "overlap_ms": int}, ...]

    两条字幕重叠条件：entry[i].end_ms > entry[i+1].start_ms
    """
    overlaps = []
    for i in range(len(entries) - 1):
        a = entries[i]
        b = entries[i + 1]
        if a.end_ms > b.start_ms:
            overlap_ms = a.end_ms - b.start_ms
            overlaps.append({
                "index_a": i,
                "index_b": i + 1,
                "overlap_ms": overlap_ms,
                "a_end": a.end_ms,
                "b_start": b.start_ms,
            })
    return overlaps


def fix_overlaps(entries: List[SubtitleEntry], min_duration_ms: int = 200) -> Tuple[List[SubtitleEntry], List[dict]]:
    """
    修复时间轴重叠，使每条字幕的时间轴独立不重叠。

    策略：
    1. 如果重叠量较小（< 50% 的较短条目时长）→ 缩短前一条的 end_ms 到后一条的 start_ms
    2. 如果前一条缩短后时长 < min_duration_ms → 将前一条 end_ms 设为 start_ms + min_duration_ms，
       后一条 start_ms 相应后移
    3. 如果两条完全包含（一条的时间完全在另一条内）→ 合并为一条

    返回: (修复后的 entries 列表, 修改记录列表)
    """
    if not entries:
        return entries, []

    # 深拷贝 entries（避免修改原始数据）
    from dataclasses import replace as dc_replace
    fixed = [dc_replace(e) for e in entries]
    changes = []

    i = 0
    while i < len(fixed) - 1:
        a = fixed[i]
        b = fixed[i + 1]

        if a.end_ms <= b.start_ms:
            # 无重叠，继续
            i += 1
            continue

        overlap_ms = a.end_ms - b.start_ms
        a_dur = a.end_ms - a.start_ms
        b_dur = b.end_ms - b.start_ms

        # 情况 1：完全包含 → 合并
        if a.start_ms >= b.start_ms and a.end_ms <= b.end_ms:
            # a 完全在 b 内 → 合并到 b
            merged_text = f"{a.text} {b.text}".strip()
            fixed[i + 1] = dc_replace(b, text=merged_text, start_ms=b.start_ms, end_ms=b.end_ms)
            changes.append({
                "type": "merge",
                "indices": [i, i + 1],
                "reason": f"entry {i} fully contained in entry {i+1}",
            })
            fixed.pop(i)
            continue

        if b.start_ms >= a.start_ms and b.end_ms <= a.end_ms:
            # b 完全在 a 内 → 合并到 a
            merged_text = f"{a.text} {b.text}".strip()
            fixed[i] = dc_replace(a, text=merged_text, start_ms=a.start_ms, end_ms=a.end_ms)
            changes.append({
                "type": "merge",
                "indices": [i, i + 1],
                "reason": f"entry {i+1} fully contained in entry {i}",
            })
            fixed.pop(i + 1)
            continue

        # 情况 2：部分重叠 → 调整边界
        shorter_dur = min(a_dur, b_dur)
        if overlap_ms < shorter_dur * 0.5:
            # 重叠量较小 → 缩短前一条
            new_a_end = b.start_ms
            new_a_dur = new_a_end - a.start_ms

            if new_a_dur >= min_duration_ms:
                # 直接缩短
                fixed[i] = dc_replace(a, end_ms=new_a_end)
                changes.append({
                    "type": "trim_end",
                    "index": i,
                    "old_end": a.end_ms,
                    "new_end": new_a_end,
                    "overlap_ms": overlap_ms,
                })
            else:
                # 缩短后太短 → 给前一条最少 min_duration_ms，后一条后移
                fixed[i] = dc_replace(a, end_ms=a.start_ms + min_duration_ms)
                shift = (a.start_ms + min_duration_ms) - b.start_ms
                fixed[i + 1] = dc_replace(b, start_ms=b.start_ms + shift, end_ms=b.end_ms + shift)
                changes.append({
                    "type": "shift",
                    "index_a": i,
                    "index_b": i + 1,
                    "shift_ms": shift,
                    "overlap_ms": overlap_ms,
                })
        else:
            # 重叠量较大 → 按比例分配时间
            total_span = max(a.end_ms, b.end_ms) - min(a.start_ms, b.start_ms)
            # 按文本长度比例分配
            a_len = len(a.text)
            b_len = len(b.text)
            ratio = a_len / max(a_len + b_len, 1)
            boundary = min(a.start_ms, b.start_ms) + int(total_span * ratio)
            boundary = max(boundary, a.start_ms + min_duration_ms)
            boundary = min(boundary, b.end_ms - min_duration_ms)

            fixed[i] = dc_replace(a, end_ms=boundary)
            fixed[i + 1] = dc_replace(b, start_ms=boundary)
            changes.append({
                "type": "proportional_split",
                "index_a": i,
                "index_b": i + 1,
                "boundary_ms": boundary,
                "overlap_ms": overlap_ms,
            })

        i += 1

    # 重新编号
    for idx, e in enumerate(fixed):
        fixed[idx] = dc_replace(e, index=idx + 1)

    return fixed, changes


def entries_to_srt(entries: List[SubtitleEntry], filepath: str) -> None:
    """将 SubtitleEntry 列表写回 SRT 文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        for i, entry in enumerate(entries):
            f.write(f"{i + 1}\n")
            f.write(f"{entry.start_time} --> {entry.end_time}\n")
            f.write(f"{entry.text}\n")
            f.write("\n")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 subtitle_parser.py <subtitle_file> [--fix-overlaps] [--output <output.srt>]")
        sys.exit(1)

    entries = parse_subtitle(sys.argv[1])
    print(f"Parsed {len(entries)} entries")

    # 语言检测
    lang_info = detect_language(entries)
    print(f"Detected language: {lang_info['primary']} (confidence: {lang_info['confidence']})")

    speakers = get_speakers(entries)
    if speakers:
        print(f"Speakers: {speakers}")

    # 时间轴重叠检测
    overlaps = detect_overlaps(entries)
    if overlaps:
        print(f"\n[WARNING] Found {len(overlaps)} timeline overlap(s):")
        for ov in overlaps[:10]:
            print(f"  entries [{ov['index_a']}]<->[{ov['index_b']}]: overlap {ov['overlap_ms']}ms")
        if len(overlaps) > 10:
            print(f"  ... and {len(overlaps) - 10} more")

        # 如果指定 --fix-overlaps
        if "--fix-overlaps" in sys.argv:
            fixed, changes = fix_overlaps(entries)
            print(f"\nFixed {len(changes)} overlap(s)")
            for ch in changes[:10]:
                print(f"  {ch['type']}: {ch}")

            # 输出修复后的文件
            out_idx = sys.argv.index("--output") if "--output" in sys.argv else -1
            out_path = sys.argv[out_idx + 1] if out_idx >= 0 and out_idx + 1 < len(sys.argv) else None
            if not out_path:
                import os
                base = os.path.splitext(sys.argv[1])[0]
                out_path = f"{base}_fixed.srt"
            entries_to_srt(fixed, out_path)
            print(f"\nFixed subtitle saved to: {out_path}")
    else:
        print("[OK] No timeline overlaps detected")

    # 显示前 5 条
    print()
    for e in entries[:5]:
        print(f"  [{e.start_time} -> {e.end_time}] {e.speaker or 'narrator'}: {e.text[:50]}")
    if len(entries) > 5:
        print(f"  ... and {len(entries) - 5} more")
