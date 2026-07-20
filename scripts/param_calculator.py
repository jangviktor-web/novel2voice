import os
#!/usr/bin/env python3
"""
param_calculator.py — TTS 参数计算引擎
根据角色属性 + 情感标注，自动计算 speed/pitch/volume/pause
"""


class ParamCalculator:
    """TTS 参数计算器（支持外部配置覆盖）"""

    @classmethod
    def load_config(cls, config_dir: str):
        """从 config/emotion_params.json 加载外部配置覆盖默认值"""
        import json
        path = os.path.join(config_dir, "emotion_params.json") if config_dir else "emotion_params.json"
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "speed_modifier" in data:
                cls.EMOTION_SPEED.update({k: float(v) for k, v in data["speed_modifier"].items()})
            if "pitch_delta" in data:
                cls.EMOTION_PITCH.update({k: int(v) for k, v in data["pitch_delta"].items()})
            if "volume" in data:
                cls.EMOTION_VOLUME.update({k: float(v) for k, v in data["volume"].items()})
            if "pause_rules_ms" in data:
                pass  # future: update pause rules
            return True
        except (FileNotFoundError, json.JSONDecodeError):
            return False

    # 情感→语速修正
    EMOTION_SPEED = {
        "anger": 1.15, "fear": 1.05, "sadness": 0.85, "calm": 0.95,
        "excitement": 1.20, "joy": 1.10, "contempt": 0.90,
        "neutral": 1.00, "mockery": 0.95, "anxiety": 1.08,
        "tenderness": 0.92, "melancholy": 0.88, "surprise": 1.12,
        "disgust": 0.95,
    }

    # 情感→音调偏移
    EMOTION_PITCH = {
        "anger": 2, "fear": 1, "sadness": -1, "joy": 1,
        "contempt": -1, "neutral": 0, "mockery": -1,
        "anxiety": 1, "calm": 0, "excitement": 2,
        "tenderness": 1, "melancholy": -1, "surprise": 2,
        "disgust": -1,
    }

    # 情感→音量
    EMOTION_VOLUME = {
        "anger": 1.2, "fear": 1.1, "sadness": 0.9, "joy": 1.1,
        "neutral": 1.0, "excitement": 1.15, "calm": 0.95,
        "contempt": 1.0, "mockery": 1.05, "anxiety": 1.1,
        "tenderness": 0.9, "melancholy": 0.9, "surprise": 1.15,
        "disgust": 1.0,
    }

    # 年龄→音调偏移
    AGE_PITCH = {"child": 3, "young": 1, "middle": 0, "elder": -2}

    # 年龄→语速修正
    AGE_SPEED = {"child": 1.08, "young": 1.02, "middle": 1.0, "elder": 0.92}

    # 情感强度→乘数
    INTENSITY = {"low": 0.4, "medium": 0.65, "high": 0.9}

    # 情感→TTS style 关键词
    EMOTION_STYLE = {
        "neutral": "",
        "anger": "生气 语速快 语气重",
        "fear": "紧张 恐惧 语速快",
        "sadness": "悲伤 声音发轻 语速慢",
        "joy": "开心 语速稍快 轻快",
        "tenderness": "深情款款 温柔 语速慢",
        "contempt": "冷淡 嘲讽 语速慢",
        "mockery": "嘲弄 绵里藏针",
        "anxiety": "焦虑 不安 语速快",
        "calm": "平静 语速适中",
        "melancholy": "忧郁 低沉 语速慢",
        "excitement": "兴奋 语速快 声音明亮",
        "surprise": "惊讶 语速快 尾音上扬",
        "disgust": "厌恶 语气重 语速慢",
    }

    @classmethod
    def calc_speed(cls, base_speed: float, age_group: str, emotion: str) -> float:
        """计算最终语速"""
        speed = base_speed
        speed *= cls.AGE_SPEED.get(age_group, 1.0)
        speed *= cls.EMOTION_SPEED.get(emotion.lower(), 1.0)
        return round(speed, 2)

    @classmethod
    def calc_pitch(cls, base_pitch: int, age_group: str, emotion: str) -> int:
        """计算最终音调"""
        pitch = base_pitch
        pitch += cls.AGE_PITCH.get(age_group, 0)
        pitch += cls.EMOTION_PITCH.get(emotion.lower(), 0)
        return pitch

    @classmethod
    def calc_volume(cls, emotion: str) -> float:
        """计算音量"""
        return cls.EMOTION_VOLUME.get(emotion.lower(), 1.0)

    @classmethod
    def calc_intensity(cls, intensity: str) -> float:
        """计算情感强度乘数"""
        return cls.INTENSITY.get(intensity, 0.65)

    @classmethod
    def get_emotion_style(cls, emotion: str) -> str:
        """获取情感对应的 TTS style 关键词"""
        return cls.EMOTION_STYLE.get(emotion.lower(), "")

    @classmethod
    def build_style(cls, base_style: str, emotion: str, intensity: str = "medium") -> str:
        """
        构建最终 TTS style 字符串
        基础风格 + 情感风格 + 强度修饰
        """
        parts = [base_style] if base_style else []

        emotion_style = cls.get_emotion_style(emotion)
        if emotion_style:
            parts.append(emotion_style)

        # 高强度时加强语气
        if intensity == "high" and emotion not in ("neutral", "calm"):
            parts.append("语气加重")

        return " ".join(parts)

    @classmethod
    def calculate_all(
        cls,
        base_speed: float = 1.0,
        base_pitch: int = 0,
        age_group: str = "young",
        emotion: str = "neutral",
        intensity: str = "medium",
        base_style: str = "",
    ) -> dict:
        """
        一次性计算所有参数
        返回: {speed, pitch, volume, style, emotion_intensity}
        """
        return {
            "speed": cls.calc_speed(base_speed, age_group, emotion),
            "pitch": cls.calc_pitch(base_pitch, age_group, emotion),
            "volume": cls.calc_volume(emotion),
            "style": cls.build_style(base_style, emotion, intensity),
            "emotion_intensity": cls.calc_intensity(intensity),
        }


if __name__ == "__main__":
    # 测试
    import json

    test_cases = [
        {"emotion": "tenderness", "intensity": "high", "age": "young", "base_style": "低沉磁性 温润深情"},
        {"emotion": "anger", "intensity": "high", "age": "middle", "base_style": "低沉磁性"},
        {"emotion": "sadness", "intensity": "medium", "age": "young", "base_style": "清甜轻柔"},
        {"emotion": "neutral", "intensity": "low", "age": "middle", "base_style": "温柔女声"},
        {"emotion": "fear", "intensity": "high", "age": "young", "base_style": "软糯温柔"},
    ]

    for tc in test_cases:
        result = ParamCalculator.calculate_all(
            age_group=tc["age"],
            emotion=tc["emotion"],
            intensity=tc["intensity"],
            base_style=tc["base_style"],
        )
        print(f"{tc['emotion']:12s} | speed={result['speed']} pitch={result['pitch']:+d} vol={result['volume']} | {result['style']}")
