#!/usr/bin/env python3
"""生成 Edge TTS 中文音色试听样本"""
import os, sys, requests

sys.stdout.reconfigure(encoding='utf-8')

EDGE_TTS_URL = "https://tts.kalaok.cc.cd/v1/audio/speech"
EDGE_TTS_KEY = os.environ.get("EDGE_TTS_KEY", "sk-1234567890")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "voice_samples")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 统一试听台词（覆盖陈述/疑问/感叹，展示音色特质）
SAMPLE_TEXT = "你好，我是这个故事里的角色。今天的天气真不错，我们一起出去走走吧！"

# 所有中文音色
VOICES = [
    # 女声
    ("zh-CN-XiaoxiaoNeural", "XiaoxiaoNeural", "女"),
    ("zh-CN-XiaoyiNeural", "XiaoyiNeural", "女"),
    ("zh-CN-XiaohanNeural", "XiaohanNeural", "女"),
    ("zh-CN-XiaomoNeural", "XiaomoNeural", "女"),
    ("zh-CN-XiaoruiNeural", "XiaoruiNeural", "女"),
    ("zh-CN-XiaoshuangNeural", "XiaoshuangNeural", "女"),
    ("zh-CN-XiaomengNeural", "XiaomengNeural", "女"),
    # 男声
    ("zh-CN-YunxiNeural", "YunxiNeural", "男"),
    ("zh-CN-YunyangNeural", "YunyangNeural", "男"),
    ("zh-CN-YunjianNeural", "YunjianNeural", "男"),
    ("zh-CN-YunxiaNeural", "YunxiaNeural", "男"),
    ("zh-CN-YunzeNeural", "YunzeNeural", "男"),
    ("zh-CN-YunfengNeural", "YunfengNeural", "男"),
    # 方言
    ("zh-CN-liaoning-YunbiaoNeural", "liaoning-Yunbiao", "男"),
    ("zh-CN-liaoning-XiaobeiNeural", "liaoning-Xiaobei", "女"),
    ("zh-CN-henan-YundengNeural", "henan-Yundeng", "男"),
    ("zh-CN-shandong-YunxiangNeural", "shandong-Yunxiang", "男"),
    ("zh-CN-sichuan-YunxiNeural", "sichuan-Yunxi", "男"),
    ("zh-CN-guangxi-YunqiNeural", "guangxi-Yunqi", "男"),
    ("zh-CN-shaanxi-XiaoniNeural", "shaanxi-Xiaoni", "女"),
    ("wuu-CN-YunzheNeural", "wuu-Yunzhe", "男"),
    ("wuu-CN-XiaotongNeural", "wuu-Xiaotong", "女"),
    # 粤语
    ("zh-HK-HiuGaaiNeural", "HK-HiuGaai", "女"),
    ("zh-HK-HiuMaanNeural", "HK-HiuMaan", "女"),
    ("zh-HK-WanLungNeural", "HK-WanLung", "男"),
    # 台湾腔
    ("zh-TW-HsiaoChenNeural", "TW-HsiaoChen", "女"),
    ("zh-TW-HsiaoYuNeural", "TW-HsiaoYu", "女"),
    ("zh-TW-YunJheNeural", "TW-YunJhe", "男"),
]

print(f"[INFO] Generating {len(VOICES)} voice samples...")
print(f"[INFO] Output: {OUTPUT_DIR}")
print(f"[INFO] Sample text: {SAMPLE_TEXT}")
print()

success = 0
fail = 0
for voice_id, short_name, gender in VOICES:
    out_path = os.path.join(OUTPUT_DIR, f"{short_name}.mp3")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        print(f"  [SKIP] {short_name} (already exists)")
        success += 1
        continue

    try:
        resp = requests.post(EDGE_TTS_URL, json={
            "input": SAMPLE_TEXT,
            "voice": voice_id,
            "speed": 1.0,
            "response_format": "mp3",
        }, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {EDGE_TTS_KEY}",
        }, timeout=30)
        resp.raise_for_status()

        with open(out_path, "wb") as f:
            f.write(resp.content)
        size_kb = len(resp.content) / 1024
        print(f"  [OK] {short_name:25s} ({gender}) {size_kb:.1f} KB")
        success += 1
    except Exception as e:
        print(f"  [FAIL] {short_name:25s} ({gender}) {e}")
        fail += 1

print(f"\n[INFO] Done: {success} success, {fail} fail")
print(f"[INFO] Samples saved to: {OUTPUT_DIR}")
