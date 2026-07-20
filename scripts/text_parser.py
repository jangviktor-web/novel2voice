#!/usr/bin/env python3
"""
text_parser.py — 小说文本自动解析器
自动识别：章节标题、对话、旁白、心理活动、说话人提取
"""
import os
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass, field


# 段落最大长度，超过后在句末标点处断开
MAX_SEGMENT_LEN = 300


@dataclass
class CharacterProfile:
    """角色档案"""
    character_id: str
    name: str
    gender: str = "unknown"            # male / female / unknown
    age_group: str = "young"           # child / young / middle / elder
    personality: str = ""
    speaking_style: str = ""
    dialogue_frequency: str = "medium" # high / medium / low
    voice_id: str = "mimo_default"
    voice_style: str = ""
    mention_count: int = 0


@dataclass
class Segment:
    """文本段落"""
    segment_id: str
    text: str
    segment_type: str                  # narration / dialogue / inner_thought / chapter_title
    character_id: str = "narrator"
    character_name: str = ""
    emotion: str = "neutral"
    intensity: str = "medium"          # low / medium / high
    pause_after: int = 400


class TextParser:
    """小说文本自动解析器"""

    # v2.19: 描述词到角色名的映射（用于上下文指代解析）
    DESCRIPTION_TO_NAME = {
        '中年男人': None,  # 需要上下文推断
        '中年人': None,
        '中年妇人': None,
        '年轻人': None,
        '老者': None,
        '少女': None,
        '书生': None,
        '男子': None,
        '女子': None,
        '男人': None,
        '女人': None,
    }

    # 章节标题正则：第一章、第1节、第十二回、第三卷、第四幕、第五集、第六部、第七篇
    CHAPTER_RE = re.compile(
        r'^第[一二三四五六七八九十百千零\d]+[章节回卷幕集部篇]'
    )

    # 对话开头检测：中文引号、英文引号、书名号式对话
    DIALOGUE_START = re.compile(r'^[\u201c「"]')

    # 对话标签提取：从行尾提取说话人（支持古典用法）
    # 匹配格式："对话内容"XXX说。 或 "对话内容"XXX轻声说。 或 "对话内容"某某曰。
    # 说话人只允许纯汉字，最长6字（中文名字一般2-4字）
    # 注意：单独的"道"加了 (?<!知) 防止"知道"误匹配
    DIALOGUE_TAG_RE = re.compile(
        r'["\u201d][\s]*(?P<speaker>[\u4e00-\u9fff]{1,4}?)'
        r'(?:说|(?<!知)道|曰|云|喊|叫|问|答|吼|低语|笑道|叹道|怒道|冷笑道|轻声道|大声|嘟囔|呢喃|惊呼|冷笑|叹气|'
        r'微笑道|厉声道|沉声道|柔声道|急声道|淡淡地说|冷冷地说|轻声说|轻声问|笑着说|哭着说|'
        r'答道|喝道|唱道|骂道|问道|叫道|吼道|嚷道|嘟囔道|惊呼道|叹息道|冷笑道|低声道|高声道|'
        r'怒吼|低吼|呢喃道|嘟囔道|惊叫|尖叫|叹息|微笑|冷笑|轻笑|苦笑|'
        r'接口道|接过话|插嘴|补充|反驳|应道|回道|啐道|骂道|喝道|附和|'
        r'低声|高声|喃喃|嚷着|喊着|吼着|自语|低声自语|喃喃自语|自言自语)'
    )
    
    # 句尾对话标签：闭引号后的说话人标记（支持古典用法）
    TRAILING_TAG_RE = re.compile(
        r'[\u201d\u300d\u300f」』"\'][\s]*(?P<speaker>[\u4e00-\u9fff]{1,4}?)'
        r'(?:说|(?<!知)道|曰|云|喊|叫|问|答|吼|低语|笑道|叹道|怒道|冷笑道|轻声道|厉声道|沉声道|柔声道|急声道|'
        r'答道|喝道|唱道|骂道|问道|叫道|吼道|嚷道|应道|回道|接口道|接过话)'
    )
    
    # 行内对话检测（非行首引号）
    INLINE_DIALOGUE_RE = re.compile(r'[\u201c\u300c「『"]')
    
    # 备用：行内说话人提取（如：XXX说，"……" 或 XXX点头："……"）
    # 限制名字为2-3字，避免匹配到"陈府尹摇"这样的错误
    INLINE_SPEAKER_RE = re.compile(
        r'^(?P<speaker>[\u4e00-\u9fff]{2,3})'
        r'(?:说|道|曰|云|喊|叫|问|答|吼|低语|笑道|叹道|怒道|冷笑道|轻声道|点头|摇头|轻声|叹气|微笑|'
        r'答道|喝道|唱道|骂道|问道|叫道|吼道|嚷道)'
    )

    # v2.18: "Speaker + action + colon" 格式（如"许新年皱了皱眉："）
    # 先匹配2-3字名字，如果是4字名字（如黄裙少女）需要额外验证
    SPEAKER_ACTION_COLON_RE = re.compile(
        r'^[\s]*(?P<name>[\u4e00-\u9fff]{2,3})(?P<rest>[^：:\n]*)[：:]', re.MULTILINE
    )
    SPEAKER_ACTION_COLON_4CHAR_RE = re.compile(
        r'^[\s]*(?P<name>[\u4e00-\u9fff]{4})(?P<rest>[^：:\n]*)[：:]', re.MULTILINE
    )

    # 心理活动检测
    INNER_THOUGHT_RE = re.compile(
        r'(心想|暗道|心中暗想|内心|暗想|寻思|琢磨|心道|心想道|暗自|心中|脑海里|脑子里|心里想)'
    )

    # 对话格式3：角色名（情感描述）：台词（无引号）
    EMOTION_DIALOGUE_RE = re.compile(
        r'^(?P<speaker>[^（(]{1,8})[（(][^）)]+[）)][：:](?P<dialogue>.+)$'
    )

    # 角色名预扫描：从言语动词前提取可能的角色名
    CHARACTER_DETECT_RE = re.compile(
        r'(?:(?:^|(?<=[。！？；\n\u201d\u300d\u300f」』"\']))[\s]*)'
        r'(?P<name>[\u4e00-\u9fff]{2,4})'
        r'(?:说|道|曰|云|喊|叫|问|答|吼|笑道|叹道|怒道|冷笑道|轻声道|沉声道|厉声道|'
        r'答道|喝道|唱道|骂道|问道|叫道|吼道|嚷道|应道|回道|嘟囔|呢喃|惊呼|'
        r'接口道|接过话|插嘴|补充|反驳|低声|高声|喃喃|嚷着|喊着|吼着|'
        r'笑着说|哭着说|喊着说|指着说|摇头说|点头说|叹着说|冷笑着说|'
        r'笑着说|笑着问|笑着喊|笑着答|笑着叫|笑着招呼|'
        r'急忙说|连忙说|赶紧说|低声说|高声说|大声说|轻声说|冷冷地说|'
        r'问道|喊道|叫道|答道|骂道|嚷道|吼道|笑道|叹道|怒道|'
        r'关切地问|急切地问|紧张地问|小心地问|轻声问|冷冷地问|'
        r'招呼|问道|答道|喊道|叫道)'
    )

    # ============================================================
    # v2.11 新增：角色别名归一化
    # ============================================================
    # 常见别名映射：将文本中出现的各种称呼统一到标准角色名
    # Agent 可在调用时通过 alias_map 参数传入自定义映射
    DEFAULT_ALIASES = {
        # 称谓 → 标准名（示例，实际使用时由 Agent 根据小说内容配置）
        "中年警察": "警察", "中年警员": "警察", "警员": "警察",
        "年轻的警察": "警察", "稍长的警察": "警察",
        "警队队长": "队长", "队长": "队长",
        "犯罪嫌疑人": "罪犯", "嫌疑人": "罪犯", "那个家伙": "罪犯",
        "店主人": "文具店老板", "文具店老板": "文具店老板",
        "男学生": "路人", "女学生": "路人", "学生": "路人",
        "急救员": "急救人员", "法医": "急救人员",
    }

    # ============================================================
    # v2.11 新增：情绪关键词检测
    # ============================================================
    EMOTION_KEYWORDS = {
        "sad": [
            "哭泣", "流泪", "泪水", "泪", "哭", "悲伤", "悲痛", "痛苦", "绝望",
            "崩溃", "嘶吼", "怒吼", "呻吟", "哽咽", "泣不成声", "撕心裂肺",
            "郁郁寡欢", "愤恨", "仇恨", "蔑视", "挫败", "无力感", "憔悴",
            "心如刀割", "战栗", "颤抖", "瘫倒", "昏睡",
        ],
        "angry": [
            "愤怒", "气愤", "暴怒", "怒斥", "厉声", "凶狠", "瞪", "痛打",
            "撕碎", "揍", "踢打", "抽打", "猛踢", "咬牙切齿",
        ],
        "happy": [
            "微笑", "笑", "开心", "高兴", "欢乐", "幸福", "温馨", "甜蜜",
            "爱笑", "欢呼", "喜悦", "欣慰", "兴高采烈",
        ],
        "fear": [
            "恐惧", "害怕", "惊恐", "颤抖", "尖叫", "惊吓", "战栗",
            "瑟瑟发抖", "浑身发抖", "吓得", "惊起",
        ],
    }

    # ============================================================
    # v2.11 新增：第一人称叙事检测
    # ============================================================
    FIRST_PERSON_MARKERS = re.compile(
        r'(?:我|俺|咱|老子|本人)'
        r'(?:是|在|的|了|想|觉得|认为|决定|希望|害怕|知道|不记得|记得|'
        r'看到|听到|闻到|感到|觉得|心里|脑海|'
        r'的爸爸|的妈妈|的儿子|的女儿|的丈夫|的妻子)'
    )
    # 第一人称叙事段落中的对话引号内"我"不算（只检测叙述部分的"我"）

    # ============================================================
    # v2.11 新增：信件检测
    # ============================================================
    LETTER_MARKERS = re.compile(
        r'(?:来信|回信|写信|家书|信件|信上写着|信中写道|'
        r'写了.{0,4}信|写了一封信|写了封信|提笔写|'
        r'展开信|打开信|读完信|信纸|'
        r'亲爱的|此致|敬礼|祝好|'
        r'绝笔|亲笔信|'
        r'哆啦A梦来信|爸爸的信|妈妈的信|素媛的信)'
    )

    # 段落类型→停顿映射
    PAUSE_RULES = {
        "chapter_title": 2000,
        "narration": 800,
        "dialogue": 300,
        "inner_thought": 600,
    }

    # 标点符号→停顿映射
    PUNCTUATION_PAUSE = {
        "……": 600,
        "。。。": 600,
        "！": 500,
        "？": 500,
        "!": 500,
        "?": 500,
        "。": 400,
        "…": 400,
    }

    @classmethod
    def parse(cls, text: str, alias_map: dict = None) -> Tuple[List[Segment], Dict[str, CharacterProfile]]:
        """
        解析小说文本，返回 (segments, characters)

        处理流程：
        1. 预扫描全文，提取已知角色名
        2. 逐行分类（章节标题/对话/内心独白/旁白/信件）
        3. 上下文感知的说话人追踪（跨段落继承）
        4. 情绪关键词检测
        5. 第一人称叙事检测
        6. 后处理：长段自动切分、同说话人对话合并
        7. 构建角色档案

        Args:
            text: 小说原始文本
            alias_map: 可选的角色别名映射 {别名: 标准名}

        Returns:
            segments: 段落列表
            characters: 角色字典 {name: CharacterProfile}
        """
        # 合并别名映射（用户自定义 > 默认）
        aliases = dict(cls.DEFAULT_ALIASES)
        if alias_map:
            aliases.update(alias_map)

        # === 预扫描：提取已知角色名 ===
        known_names = cls._pres_scan_characters(text)
        # 对已知名字也做别名归一化
        normalized_names = set()
        for name in known_names:
            normalized = aliases.get(name, name)
            normalized_names.add(normalized)
        known_names = normalized_names

        lines = text.strip().split("\n")
        raw_segments = []
        seg_id = 0

        # v2.11: 上下文感知的说话人追踪
        prev_speaker = "narrator"
        prev_speaker_confidence = 0  # 0=继承, 1=弱匹配, 2=强匹配
        first_person_character = None  # 第一人称叙事的主角

        for line in lines:
            line = line.strip()
            if not line:
                continue

            seg_id += 1
            seg_type = "narration"
            speaker = "narrator"
            emotion = "neutral"

            # 1. 章节标题
            if cls.CHAPTER_RE.match(line):
                seg_type = "chapter_title"

            # v2.11: 第一人称叙事检测
            elif first_person_character is None and cls._detect_first_person(line):
                # 检测到第一人称叙事，尝试识别叙述者身份
                fp_char = cls._identify_first_person_narrator(line, known_names, aliases)
                if fp_char:
                    first_person_character = fp_char

            # v2.11: 信件/内心独白检测（优先于对话检测）
            elif cls.LETTER_MARKERS.search(line):
                seg_type = "letter"
                # 尝试从当前行文本中找写信人
                letter_writer = None
                for name in sorted(known_names, key=len, reverse=True):
                    if name in line:
                        letter_writer = name
                        break
                if letter_writer:
                    speaker = letter_writer
                elif first_person_character:
                    speaker = first_person_character
                else:
                    speaker = prev_speaker if prev_speaker != "narrator" else "narrator"
                emotion = cls._detect_emotion(line)

            # 2. 对话行
            elif cls.DIALOGUE_START.match(line):
                seg_type = "dialogue"
                speaker = cls._extract_speaker(line, known_names, aliases)

                # v2.11: 如果提取不到说话人，使用上下文继承
                if speaker == "__unknown__":
                    if prev_speaker != "narrator" and prev_speaker_confidence > 0:
                        speaker = prev_speaker
                    else:
                        speaker = "__unknown__"
                else:
                    prev_speaker = speaker
                    prev_speaker_confidence = 2  # 强匹配

                # v2.11: 情绪检测
                emotion = cls._detect_emotion(line)

            # 3. 行内对话（如：男人点头："记得。"）
            elif re.search(r'[：:][\s]*[\u201c「"]', line) and not cls.DIALOGUE_START.match(line):
                seg_type = "dialogue"
                speaker = "__unknown__"
                # 策略1：INLINE_SPEAKER_RE 匹配行首名字+言语动词
                m = cls.INLINE_SPEAKER_RE.match(line)
                if m:
                    speaker = cls._clean_speaker(m.group("speaker"))
                    speaker = aliases.get(speaker, speaker)
                # 策略2：检查已知角色名是否出现在引号前
                if speaker == "__unknown__" and known_names:
                    quote_pos = -1
                    for qchar in ['\u201c', '\u300c', '"']:
                        pos = line.find(qchar)
                        if pos > 0 and (quote_pos < 0 or pos < quote_pos):
                            quote_pos = pos
                    if quote_pos > 0:
                        before = line[:quote_pos]
                        # v2.18: 优先匹配 "名字+动作+冒号" 模式
                        colon_match = re.match(r'([\u4e00-\u9fff]{2,4})[^：:\u4e00-\u9fff]{0,10}[：:]', before)
                        if colon_match:
                            candidate = colon_match.group(1)
                            if candidate in known_names:
                                speaker = candidate
                        # 回退：检查已知角色名是否出现在引号前
                        if speaker == "__unknown__":
                            for name in sorted(known_names, key=len, reverse=True):
                                if name in before:
                                    speaker = name
                                    break
                # v2.11: 上下文继承
                if speaker == "__unknown__" and prev_speaker != "narrator":
                    speaker = prev_speaker
                elif speaker != "__unknown__":
                    prev_speaker = speaker
                    prev_speaker_confidence = 2

                emotion = cls._detect_emotion(line)

            # 3b. 角色名（情感描述）：台词 格式（无引号）
            elif cls.EMOTION_DIALOGUE_RE.match(line):
                m = cls.EMOTION_DIALOGUE_RE.match(line)
                seg_type = "dialogue"
                speaker = cls._clean_speaker(m.group("speaker"))
                speaker = aliases.get(speaker, speaker)
                prev_speaker = speaker
                prev_speaker_confidence = 2
                emotion = cls._detect_emotion(line)
                raw_segments.append({
                    "segment_id": f"{seg_id:04d}",
                    "text": m.group("dialogue").strip(),
                    "segment_type": seg_type,
                    "speaker": speaker,
                    "emotion": emotion,
                })
                continue

            # 4. 心理活动
            elif cls.INNER_THOUGHT_RE.search(line):
                seg_type = "inner_thought"
                # v2.11: 心理活动的说话人 = 第一人称主角或上文说话人
                if first_person_character:
                    speaker = first_person_character
                elif prev_speaker != "narrator":
                    speaker = prev_speaker

            # v2.11: 对叙述段落也做情绪检测（用于旁白参数调整）
            if seg_type == "narration":
                emotion = cls._detect_emotion(line)
                # 叙述中出现的角色名可能暗示下一段的说话人
                # 更新弱匹配
                found_in_narration = cls._find_speaker_in_narration(line, known_names, aliases)
                if found_in_narration:
                    prev_speaker = found_in_narration
                    prev_speaker_confidence = 1  # 弱匹配

            # v2.11: 如果说话人未确定且有第一人称主角
            if speaker == "narrator" and first_person_character and seg_type != "chapter_title":
                # 检查是否真的是第一人称叙事段
                if cls._detect_first_person(line):
                    speaker = first_person_character

            raw_segments.append({
                "segment_id": f"{seg_id:04d}",
                "text": line,
                "segment_type": seg_type,
                "speaker": speaker,
                "emotion": emotion,
            })

        # === 后处理 1：长段自动切分 ===
        raw_segments = cls._split_long_segments(raw_segments)

        # === 后处理 2：同说话人连续对话合并 ===
        raw_segments = cls._merge_consecutive_dialogues(raw_segments)

        # 重新编号
        for i, raw in enumerate(raw_segments):
            raw["segment_id"] = f"{i+1:04d}"

        # 提取角色（v2.13: 传入 known_names 确保预扫描角色不遗漏）
        characters = cls._extract_characters(raw_segments, text, known_names)

        # 构建 Segment 对象
        segments = []
        for i, raw in enumerate(raw_segments):
            char_name = raw["speaker"]
            if char_name == "__unknown__":
                char_id = "narrator"
            else:
                char_id = characters.get(char_name, characters.get("narrator")).character_id

            prev_raw = raw_segments[i - 1] if i > 0 else None
            pause = cls._calc_pause(raw["text"], raw["segment_type"],
                                     i - 1 if i > 0 else -1,
                                     raw_segments)

            segments.append(Segment(
                segment_id=raw["segment_id"],
                text=raw["text"],
                segment_type=raw["segment_type"],
                character_id=char_id,
                character_name=char_name if char_name != "__unknown__" else "旁白",
                emotion=raw.get("emotion", "neutral"),
                pause_after=pause,
            ))

        return segments, characters

    # 副词后缀清理
    _ADVERB_SUFFIXES = re.compile(
        r'(?:委屈地|冷冷地|淡淡地|狠狠地|轻轻地|急急地|狠狠|冷冷|淡淡|轻轻|急急|微笑地|愤怒地|悲伤地|开心地|紧张地)$'
    )

    # 动作后缀：从提取的说话人名字中裁掉末尾的动作词
    _ACTION_SUFFIXES = re.compile(
        r'(?:招手|苦笑|冷笑|微笑|叹气|叹息|摇头|点头|皱眉|转身|站起|坐下|'
        r'凑到|走到|跑到|来到|趴在|靠在|看着|望着|盯着|'
        r'懒洋洋|慢条斯理|立刻反映|扫了一眼|眯起眼睛|'
        r'开口|笑着|哭了|喊道|叫道|嚷道|答道|问道|喝道|唱道|骂道)'
        r'(?:，|,|$)'
    )

    # 非名字模式：如果提取的"说话人"包含这些模式，说明不是真正的名字
    _NON_NAME_PATTERNS = re.compile(
        r'(?:开口|笑着|哭了|叹了|摇头|点头|皱眉|转身|站起|坐下|看着|望着|盯着|'
        r'走到|跑到|来到|凑到|趴在|靠在|抱|拉|推|举|放|收|取|拿|'
        r'他的|她的|我的|你的|谁的|那个|这个|一个|'
        r'虽然|即使|因为|所以|但是|然而|于是|然后|接着|随后|'
        r'慢慢地|快速地|轻轻地|悄悄地|默默地|静静地|缓缓地|'
        r'心想|暗道|心中|内心|暗想|寻思|琢磨|'
        r'面露|脸色|表情|眼中|嘴角|眉头|'
        r'一声|一下|一番|什么|怎么|为何|'
        r'再好不过|不如|不过是|只是|而已|'
        r'懒洋洋|慢条斯理|凑在他|眯起眼睛|扫了|'
        r'知道|来不及|还没|他只|她每|虽|不对|一笑|'
        r'没有|不是|跟你|在客|关切|大声|低声|冷冷|淡淡|小声|轻声|'
        r'有些|有些|终于|缓缓|默默|悄悄|静静|'
        r'从|到|向|对|被|把|给|让|和|与|跟)'
    )

    @classmethod
    def _clean_speaker(cls, name: str) -> str:
        """清理说话人名字，去除副词后缀和动作后缀，过滤非名字"""
        if not name:
            return "__unknown__"
        name = cls._ADVERB_SUFFIXES.sub('', name).strip()
        name = cls._ACTION_SUFFIXES.sub('', name).strip()
        if not name:
            return "__unknown__"
        # 过滤包含非名字模式的提取结果
        if cls._NON_NAME_PATTERNS.search(name):
            return "__unknown__"
        # 过滤纯代词（单字"他""她""我"等不算有效名字）
        if len(name) == 1 and name in '他她我你它':
            return "__unknown__"
        return name

    # ============================================================
    # v2.11 新增方法
    # ============================================================

    @classmethod
    def _detect_emotion(cls, text: str) -> str:
        """检测文本中的情绪关键词，返回主导情绪。
        返回: "sad" / "angry" / "happy" / "fear" / "neutral"
        """
        scores = {"sad": 0, "angry": 0, "happy": 0, "fear": 0}
        for emotion, keywords in cls.EMOTION_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[emotion] += 1
        # 返回得分最高的情绪（至少需要1个关键词命中）
        best = max(scores, key=scores.get)
        if scores[best] >= 1:
            return best
        return "neutral"

    @classmethod
    def _detect_first_person(cls, text: str) -> bool:
        """检测文本是否包含第一人称叙事特征。
        排除引号内的"我"（对话中的"我"不算叙事）。
        """
        # 去掉引号内的内容
        cleaned = re.sub(r'\u201c[^\u201d]*\u201d', '', text)
        cleaned = re.sub(r'「[^」]*」', '', cleaned)
        return bool(cls.FIRST_PERSON_MARKERS.search(cleaned))

    @classmethod
    def _identify_first_person_narrator(cls, text: str, known_names: set, aliases: dict) -> str:
        """从第一人称叙事段落中识别叙述者身份。
        通过检查段落中出现的角色名来判断"我"是谁。
        """
        # 去掉引号内容
        cleaned = re.sub(r'\u201c[^\u201d]*\u201d', '', text)
        # 在剩余文本中查找已知角色名
        for name in sorted(known_names, key=len, reverse=True):
            if name in cleaned:
                return aliases.get(name, name)
        return ""

    @classmethod
    def _find_speaker_in_narration(cls, text: str, known_names: set, aliases: dict) -> str:
        """从叙述段落中查找可能的下一段说话人。
        策略：找到紧邻引号前的角色名。
        """
        # 查找 "XXX说/问/喊" 模式
        for m in cls.DIALOGUE_TAG_RE.finditer(text):
            name = cls._clean_speaker(m.group("speaker"))
            if name in known_names:
                return aliases.get(name, name)
        # 查找引号前的角色名
        for qchar in ['\u201c', '\u300c']:
            pos = text.find(qchar)
            if pos > 0:
                before = text[:pos]
                for name in sorted(known_names, key=len, reverse=True):
                    if name in before:
                        return aliases.get(name, name)
        return ""

    @classmethod
    def _extract_speaker(cls, line: str, known_names: set = None, aliases: dict = None) -> str:
        """从对话行中提取说话人，多策略融合。
        优先使用已知角色名匹配。支持别名归一化。
        """
        if known_names is None:
            known_names = set()
        if aliases is None:
            aliases = {}

        # 策略1：从引号后提取说话人（"对话"XXX说。）
        m = cls.DIALOGUE_TAG_RE.search(line)
        if m:
            name = cls._clean_speaker(m.group("speaker"))
            name = aliases.get(name, name)
            if name in known_names:
                return name
            if name and name not in ("narrator", "__unknown__"):
                return name

        # 策略2：从行首提取说话人（XXX说，"……"）
        m2 = cls.INLINE_SPEAKER_RE.match(line)
        if m2:
            name = cls._clean_speaker(m2.group("speaker"))
            name = aliases.get(name, name)
            if name in known_names:
                return name
            if name and name not in ("narrator", "__unknown__"):
                return name

        # 策略3：已知角色名出现在引号前
        if known_names:
            quote_pos = -1
            for qchar in ['\u201c', '\u300c', '"', '\u201d']:
                pos = line.find(qchar)
                if pos > 0 and (quote_pos < 0 or pos < quote_pos):
                    quote_pos = pos
            if quote_pos > 0:
                before = line[:quote_pos]
                # v2.18: 优先匹配 "名字+动作+冒号" 模式
                # 先尝试匹配已知角色名+冒号
                for name in sorted(known_names, key=len, reverse=True):
                    # 检查名字是否在冒号前
                    colon_pos = before.find('：')
                    if colon_pos < 0:
                        colon_pos = before.find(':')
                    if colon_pos > 0:
                        before_colon = before[:colon_pos]
                        if name in before_colon:
                            return name
                # 回退：检查已知角色名是否出现在引号前
                for name in sorted(known_names, key=len, reverse=True):
                    if name in before:
                        return name

        # v2.19: 策略4：描述词解析（如"中年男人摇了摇头："→推断为已知角色）
        # 检查是否是描述词开头的行
        for desc in cls.DESCRIPTION_TO_NAME:
            if line.startswith(desc) or (len(line) > len(desc) and line[:len(desc)+1].startswith(desc)):
                # 尝试从已知角色中找到最近提到的角色
                # 这需要上下文信息，暂时返回 __unknown__
                break

        # v2.19: 策略5：上下文指代解析
        # 如果行以描述词开头（如"中年男人"、"黄裙少女"），尝试推断角色
        # 这需要在解析过程中维护角色描述映射
        # 暂时返回 __unknown__，后续通过 segments.json 手动修正

        return "__unknown__"

    # v2.13: 叙述性角色引入检测（如"是XXX"、"XXX从...走出来"、"XXX站在..."）
    # 使用惰性匹配 {2,4}? 防止捕获名字+动词
    # 要求名字前有句子边界，防止匹配任意子串
    NARRATIVE_INTRO_RE = re.compile(
        r'(?:(?:^|(?<=[。！？；\n]))[\s]*)'
        r'(?P<name1>[\u4e00-\u9fff]{2,4}?)'
        r'(?:从|在|站在|坐在|躺在|趴在|靠在|走到|跑到|来到|'
        r'转过身|站起身|蹲下来|走出来|探出来|抬起头|站起来|'
        r'停下|回头|转身)'
    )

    @classmethod
    def _extract_characters(cls, raw_segments: List[dict], text: str = "",
                            known_names: set = None) -> Dict[str, CharacterProfile]:
        """从段落中提取角色信息，包括性别检测。
        v2.13: 也包含预扫描发现但没有对话的角色。
        """
        char_count: Dict[str, int] = {}
        for seg in raw_segments:
            speaker = seg.get("speaker", "narrator")
            if speaker not in ("narrator", "__unknown__"):
                char_count[speaker] = char_count.get(speaker, 0) + 1

        # v2.13: 将预扫描发现的角色也纳入（即使没有对话）
        # 但要过滤误报：必须通过名字验证且在文本中出现至少2次
        if known_names and text:
            for name in known_names:
                if name not in char_count and cls._is_valid_character_name(name):
                    # 检查名字在文本中出现的次数（至少2次才算真实角色）
                    occurrences = len(re.findall(re.escape(name), text))
                    if occurrences >= 2:
                        char_count[name] = 0

        characters: Dict[str, CharacterProfile] = {}

        # 旁白
        characters["narrator"] = CharacterProfile(
            character_id="narrator",
            name="旁白",
            gender="unknown",
            age_group="middle",
            personality="沉稳客观",
            speaking_style="中性沉稳朗读",
            dialogue_frequency="low",
            voice_id="zh-CN-XiaoxiaoNeural",
            voice_style="温柔女声 语速适中 情感丰富 讲故事",
        )

        # v2.13: 性别检测 - 扫描全文中的代词引用
        gender_map = cls._detect_gender(text, list(char_count.keys())) if text else {}
        # v2.20: 年龄组检测
        age_map = cls._detect_age_group(text, list(char_count.keys())) if text else {}

        # 按出场频率降序排列
        for idx, (name, count) in enumerate(
            sorted(char_count.items(), key=lambda x: -x[1]), 1
        ):
            freq = "high" if count > 10 else ("medium" if count > 3 else "low")
            gender = gender_map.get(name, "unknown")
            age_group = age_map.get(name, "young")  # 默认年轻
            voice_id = cls._recommend_voice(gender, age_group)
            characters[name] = CharacterProfile(
                character_id=f"char_{idx:03d}",
                name=name,
                gender=gender,
                age_group=age_group,
                mention_count=count,
                dialogue_frequency=freq,
                voice_id=voice_id,
            )

        return characters

    @classmethod
    def _detect_gender(cls, text: str, character_names: List[str]) -> Dict[str, str]:
        """扫描全文，通过名字特征字和性别特征词推断角色性别。
        v2.13: 不使用代词检测（多角色文本中代词指向不可靠）。
        1. 名字本身含性别特征字（叔/伯/哥/爷=男，姐/妹/姨/姑=女）权重最高
        2. 近距离（±30字）性别特征词为中等信号
        """
        # 性别特征词（仅保留直接描述角色性别的词，不含可能指他人的称谓）
        FEMALE_WORDS = ['女孩', '女人', '女士', '姑娘', '母女', '妻子', '少妇', '女子', '少女', '小姐', '美人', '佳人', '仙女', '公主', '皇后', '妃子', '丫鬟', '婢女', '侍女', '女侠', '女皇', '女神', '大婶', '阿姨', '婆婆', '奶奶', '姥姥']
        MALE_WORDS = ['男孩', '男人', '先生', '小伙', '老头', '父子', '丈夫', '郎', '少年', '公子', '少爷', '王子', '皇帝', '大臣', '将军', '侠客', '书生', '秀才', '举人', '进士', '大叔', '大爷', '伯伯', '叔叔', '爷爷', '姥爷', '汉子', '壮汉']
        # 名字中的性别特征字（极高置信度）
        FEMALE_NAME_CHARS = set('姐姐妹姑姨婆娘嫂婶少女妃娥娟婷婉娇媚娴婉')
        MALE_NAME_CHARS = set('叔伯哥爷爹翁郎汉子雄豪杰伟刚强勇毅')

        gender_map = {}
        for name in character_names:
            male_score = 0
            female_score = 0

            # 策略1：名字本身的性别特征字（最高优先级）
            for ch in name:
                if ch in FEMALE_NAME_CHARS:
                    female_score += 50
                if ch in MALE_NAME_CHARS:
                    male_score += 50

            # 策略2：名字前方的性别特征词（前30字到名字位置）
            # 只看不看后——名字后面的词常描述宾语/他人
            for m in re.finditer(re.escape(name), text):
                pos = m.start()
                ctx_start = max(0, pos - 30)
                context_before = text[ctx_start:pos]
                for word in FEMALE_WORDS:
                    female_score += context_before.count(word) * 5
                for word in MALE_WORDS:
                    male_score += context_before.count(word) * 5

            # 根据得分判断性别
            if male_score > female_score and male_score >= 5:
                gender_map[name] = "male"
            elif female_score > male_score and female_score >= 5:
                gender_map[name] = "female"
        return gender_map

    # Edge TTS 音色映射（按性别+年龄）
    EDGE_TTS_VOICES = {
        "male": {
            "child": "zh-CN-YunxiaNeural",    # 正太少年
            "young": "zh-CN-YunxiNeural",     # 清爽阳光
            "middle": "zh-CN-YunjianNeural",   # 低沉浑厚
            "elder": "zh-CN-YunzeNeural",      # 苍老沉稳
            "default": "zh-CN-YunxiNeural",    # 默认青年
        },
        "female": {
            "child": "zh-CN-XiaoshuangNeural", # 清脆孩童
            "young": "zh-CN-XiaoxiaoNeural",   # 清亮播音
            "middle": "zh-CN-XiaoruiNeural",   # 稳重厚实
            "elder": "zh-CN-XiaoyiNeural",     # 温柔治愈
            "default": "zh-CN-XiaoxiaoNeural", # 默认青年
        },
        "unknown": {
            "default": "zh-CN-XiaoxiaoNeural", # 默认旁白
        }
    }

    # MiMo TTS 音色映射（按性别+年龄）
    MIMO_TTS_VOICES = {
        "male": {
            "child": "苏打",      # 少年音
            "young": "Milo",      # 阳光少年
            "middle": "Dean",     # 低沉磁性
            "elder": "白桦",      # 苍老沉稳
            "default": "Milo",    # 默认青年
        },
        "female": {
            "child": "茉莉",      # 软萌少女
            "young": "冰糖",      # 清甜治愈
            "middle": "茉莉",     # 温柔成熟
            "elder": "冰糖",      # 温柔治愈
            "default": "冰糖",    # 默认青年
        },
        "unknown": {
            "default": "mimo_default", # 默认旁白
        }
    }

    # 年龄特征词
    AGE_KEYWORDS = {
        "elder": ["老", "翁", "爷", "公", "婆婆", "老者", "老翁", "老汉", "老爷子", "老太爷", "长老", "老道"],
        "middle": ["中年", "壮年", "大叔", "大婶", "阿姨", "伯伯", "叔叔", "婶婶", "主母", "管家"],
        "young": ["少年", "青年", "年轻人", "小伙子", "姑娘", "小姐", "公子", "少爷", "书生", "秀才"],
        "child": ["童", "孩子", "小孩", "幼", "丫鬟", "小厮", "书童", "小童", "孩童"],
    }

    @classmethod
    def _detect_age_group(cls, text: str, character_names: List[str]) -> Dict[str, str]:
        """扫描全文，通过年龄特征词推断角色年龄组。
        """
        age_map = {}
        for name in character_names:
            # 在名字附近（±50字）查找年龄特征词
            for m in re.finditer(re.escape(name), text):
                pos = m.start()
                ctx_start = max(0, pos - 50)
                ctx_end = min(len(text), pos + len(name) + 50)
                context = text[ctx_start:ctx_end]
                
                for age_group, keywords in cls.AGE_KEYWORDS.items():
                    for keyword in keywords:
                        if keyword in context:
                            age_map[name] = age_group
                            break
                    if name in age_map:
                        break
                if name in age_map:
                    break
        return age_map

    @classmethod
    def _recommend_voice(cls, gender: str, age_group: str, tts_backend: str = "edge") -> str:
        """根据性别、年龄和TTS后端推荐音色。
        Args:
            gender: 性别 (male/female/unknown)
            age_group: 年龄组 (child/young/middle/elder)
            tts_backend: TTS后端 (edge/mimo)
        Returns:
            音色ID
        """
        voices = cls.EDGE_TTS_VOICES if tts_backend == "edge" else cls.MIMO_TTS_VOICES
        gender_voices = voices.get(gender, voices["unknown"])
        return gender_voices.get(age_group, gender_voices["default"])

    # 常见非名字词汇（高频误识别）
    NON_NAME_WORDS = {
        # 常见动词/形容词/副词
        '一喜', '一惊', '一笑', '一愣', '一呆', '一怔', '一颤',
        '不理', '不错', '不敢', '不能', '不会', '不是', '没有', '还有', '就是', '只是', '真是', '都是',
        '前面', '后面', '上面', '下面', '里面', '外面', '中间', '旁边', '对面',
        '所有', '很多', '不少', '一些', '几个', '无数', '各种', '每个',
        '寻常', '普通', '一般', '特殊', '奇怪', '正常', '异常',
        '好事', '坏事', '大事', '小事',
        '兄弟', '姐妹', '父母', '子女', '夫妻', '朋友', '敌人',
        '代表', '象征', '标志', '信号', '迹象', '痕迹',
        '天地', '日月', '星辰', '风雨', '雷电', '山河',
        '基本', '根本', '基础', '核心', '关键', '重要',
        '早已', '早就', '终于', '居然', '竟然', '果然',
        '太远', '太近', '太大', '太小', '太多', '太少',
        '说明', '表示', '证明', '意味',
        '寻死', '寻活', '找死', '找活',
        '恭敬', '尊敬', '尊重', '敬畏', '畏惧', '害怕',
        '强行', '强制', '强迫', '逼迫', '压迫',
        '近身', '远处', '附近', '周围', '身边',
        '祸人', '祸事', '灾难', '灾害',
        '蛟龙', '真龙', '神龙', '龙王', '龙君',
        '草龟', '老龟', '小龟', '大龟',
        '十分听话', '凝眉怒声', '一脸黑线', '一大片漫',
        '口嗨', '天地宠儿', '天生龙裔', '天骄必吃',
        '还是', '一喜', '一惊',
        '老寿星', '跑不掉', '近身蛮力', '无数泥沙',
        '代表外', '低调些', '好事', '寻常', '还是',
        # 新增：更多误识别词汇
        '乡亲们', '代表着', '低调些', '凝眉怒', '只留下', '只长角',
        '各种网', '基本操', '小说里', '强行用', '恭敬地', '敢光明',
        '死都不', '玉珠凝', '祸人间', '祸那些', '老寿星', '身长大',
        '陈阳知', '龟族传', '不能呆', '个巨物', '个老头', '个蛟龙',
        '个长虫', '乡亲们', '什麽武', '什麽笑', '什麽蛟', '代表着',
        '低调些', '先撤吧', '凝眉怒', '只吞了', '只留下', '只长角',
        '叫龙君', '各种网', '吾真龙', '基本操', '太远了', '小说里',
        '强行用', '恭敬地', '敢光明', '数不多', '早已有了', '死都不',
        '玉珠凝', '真龙又', '祸人间', '祸那些', '老寿星', '说明了一',
        '跑不掉', '身长大', '近身蛮', '这草龟', '那只蛟', '那蛟龙',
        '陈阳知', '骗了俺', '龟族传',
        # 4字短语误识别
        '乡亲们除', '代表着外', '低调些好', '只留下一', '各种网文',
        '基本操作', '小说里那', '强行用意', '恭敬地拱', '敢光明正',
        '死都不敢', '玉珠凝聚', '祸那些修', '老寿星上', '身长大约',
        '龟族传统', '不能呆了', '个巨物了', '个老头染', '个蛟龙了',
        '个长虫精', '什麽武道', '什麽笑', '什麽蛟龙', '先撤吧',
        '凝眉怒', '只吞了不', '只留下一', '只长角的', '叫龙君好',
        '吾真龙', '太远了', '早已有了', '祸人间', '说明了一',
        '跑不掉了', '近身蛮力', '这草龟居', '那只蛟龙', '那蛟龙',
    }

    @classmethod
    def _is_valid_character_name(cls, name: str) -> bool:
        """检查提取的名字是否是有效的角色名。
        过滤掉代词开头、动词结尾、非名字模式等。
        """
        if not name or len(name) < 2 or len(name) > 4:
            return False
        # 直接过滤常见非名字词汇
        if name in cls.NON_NAME_WORDS:
            return False
        # 过滤非名字模式
        if cls._NON_NAME_PATTERNS.search(name):
            return False
        # 过滤代词开头的名字（如"她小声"、"他连忙"）
        if name[0] in '她他我你它':
            return False
        # 过滤助词/虚词/副词开头的名字（如"的小身影"、"能已经不"、"也安静地"）
        if name[0] in '的地点得了过着到在从和与跟被把给让也又都才能已':
            return False
        # 过滤动词/介词结尾的名字
        if name[-1] in '站坐躺趴靠走跑来到从到在把被让给对向':
            return False
        # 过滤以"的"开头的名字（如"压抑的气"）
        if name[0] == '的':
            return False
        # 过滤含"气"结尾的名字（如"压抑的气"）
        if name[-1] == '气':
            return False
        # 过滤含"物"结尾的名字（如"妖物"）
        if name[-1] == '物':
            return False
        # 过滤含"脸"结尾的名字（如"这才脸"）
        if name[-1] == '脸':
            return False
        # 过滤含"人"结尾的名字（如"中年男人"）- 但保留"黄裙少女"这类
        if name[-1] == '人' and '女' not in name and '男' not in name:
            return False
        # 过滤明显不是名字的组合
        NON_NAME_PATTERNS = ['压抑', '妖物', '这才', '中年', '老年', '青年', '少年']
        for pattern in NON_NAME_PATTERNS:
            if pattern in name:
                return False
        # 过滤动词重复（如"摇了摇"、"看了看"）
        if len(name) == 3 and name[0] == name[2] and name[1] == '了':
            return False
        # 过滤以动词结尾的3字名（如"摇了摇"、"点了点头"）
        if len(name) >= 2 and name[-1] in '摇点眨抿撅咂嘶哼嗯啊呀哦呃嘻呵嘿哈呜哇唉哎哟喔噢唔欸':
            return False
        # 过滤明显不是名字的组合（如"爸爸自己"、"清脆声音"）
        if '自己' in name or '声音' in name or '身影' in name or '已经' in name or '安静' in name:
            return False
        # v2.13: 过滤通用称呼/称谓（不是具体角色名）
        COMMON_TITLES = {'叔叔', '阿姨', '伯伯', '爷爷', '奶奶', '哥哥', '姐姐',
                         '弟弟', '妹妹', '爸爸', '妈妈', '父亲', '母亲', '儿子',
                         '女儿', '老婆', '老公', '先生', '太太', '婆婆', '公公',
                         '大叔', '大婶', '大爷', '大妈', '老板', '老师', '医生'}
        if name in COMMON_TITLES:
            return False
        # 过滤含常见非名字字的组合
        NON_NAME_CHARS = set('了的吗呢吧啊哦呀嗯呃嘛啦嘞噻嗨哎哟喔噢唔欸')
        if any(c in NON_NAME_CHARS for c in name):
            return False
        # 过滤以"不"开头的名字
        if name[0] == '不':
            return False
        # 过滤以"一"开头的名字（如"一惊"、"一喜"）
        if name[0] == '一':
            return False
        # 过滤以"这"、"那"开头的名字
        if name[0] in '这那':
            return False
        # 过滤以"什"开头的名字
        if name[0] == '什':
            return False
        # 过滤以"有"、"是"、"在"开头的名字
        if name[0] in '有是在':
            return False
        # 过滤以"个"开头的名字
        if name[0] == '个':
            return False
        # 过滤含"蛟龙"、"真龙"等神话词汇
        MYTH_WORDS = ['蛟龙', '真龙', '神龙', '龙王', '龙君', '龙虾', '龙宫', '龙族']
        for word in MYTH_WORDS:
            if word in name:
                return False
        return True

    @classmethod
    def _pres_scan_characters(cls, text: str) -> set:
        """预扫描全文，提取可能的角色名。
        通过言语动词前的名字模式来识别角色，用于后续对话归属判断。
        v2.12: 也检测叙述性引入的角色（如"是XXX"、"XXX从...走出来"）
        """
        names = set()
        # 策略1：言语动词前的名字
        for m in cls.CHARACTER_DETECT_RE.finditer(text):
            name = m.group("name").strip()
            if cls._is_valid_character_name(name):
                names.add(name)
        # 策略2：引号后的标签
        for m in cls.DIALOGUE_TAG_RE.finditer(text):
            name = cls._clean_speaker(m.group("speaker"))
            if cls._is_valid_character_name(name):
                names.add(name)
        # v2.12 策略3：叙述性引入（"XXX从...走/站/坐"）
        for m in cls.NARRATIVE_INTRO_RE.finditer(text):
            name = m.group("name1") if m.group("name1") else None
            if name and cls._is_valid_character_name(name):
                names.add(name)
        # v2.12 策略4：扫描"是XXX"模式（XXX为2-4字名字）
        for m in re.finditer(r'是([\u4e00-\u9fff]{2,4})(?:[，。、]|的)', text):
            name = m.group(1).strip()
            if cls._is_valid_character_name(name):
                names.add(name)
        # v2.13 策略5：扫描"叫XXX" / "名叫XXX"模式（如"他叫陆沉舟"）
        # 要求"叫"前有代词/标点/句首，防止匹配无关文本
        for m in re.finditer(r'(?:^|(?<=[。！？；\n\s他她我你它]))(?:叫|名叫|唤作|叫做)([\u4e00-\u9fff]{2,4})(?:[，。、；\n]|了|的)', text):
            name = m.group(1).strip()
            if cls._is_valid_character_name(name):
                names.add(name)
        # v2.18 策略6：Speaker + action + colon 格式（如"许新年皱了皱眉："）
        ACTION_CHARS = set('皱沉摇吐淡轻重急慢慢快到在从说笑道怒喝喊叫嚷嘟喃')
        # 匹配2-3字名字
        for m in cls.SPEAKER_ACTION_COLON_RE.finditer(text):
            name = m.group("name").strip()
            rest = m.group("rest").strip()
            if cls._is_valid_character_name(name):
                # 额外验证：rest 部分应该包含动词/动作词
                if re.search(r'[皱沉摇吐淡轻重急慢慢快到在从说笑道怒喝喊叫嚷嘟喃]', rest):
                    names.add(name)
        # 匹配4字名字（如黄裙少女）
        for m in cls.SPEAKER_ACTION_COLON_4CHAR_RE.finditer(text):
            name = m.group("name").strip()
            rest = m.group("rest").strip()
            if cls._is_valid_character_name(name):
                # 验证：第4个字不应是常见动词/动作词
                if name[-1] not in ACTION_CHARS:
                    # 额外验证：rest 部分应该包含动词/动作词
                    if re.search(r'[皱沉摇吐淡轻重急慢慢快到在从说笑道怒喝喊叫嚷嘟喃]', rest):
                        names.add(name)
        # v2.20 策略7：描述词-角色名映射（如"中年男人叫李玉春"、"中年人李玉春"）
        # 匹配格式1：描述词 + 叫/是/为 + 角色名
        DESC_TO_NAME_RE1 = re.compile(
            r'([一-鿿]{2,4})(?:叫|是|为|乃)([一-鿿]{2,4})'
        )
        for m in DESC_TO_NAME_RE1.finditer(text):
            desc = m.group(1).strip()
            name = m.group(2).strip()
            if cls._is_valid_character_name(name):
                names.add(name)
        # 匹配格式2：描述词 + 角色名（如"中年人李玉春"）
        # 描述词：中年/老年/青年/少年 + 人/男人/女人
        # 限制名字为2-3字，避免匹配到"李玉春吐"这样的错误
        DESC_TO_NAME_RE2 = re.compile(
            r'(?:中年|老年|青年|少年)(?:人|男人|女人)([一-鿿]{2,3})'
        )
        for m in DESC_TO_NAME_RE2.finditer(text):
            name = m.group(1).strip()
            if cls._is_valid_character_name(name):
                names.add(name)
        # v2.21: 过滤子串（如果"A"是"B"的子串，且B也在names中，则移除A）
        names_to_remove = set()
        for name1 in names:
            for name2 in names:
                if name1 != name2 and name1 in name2 and len(name1) < len(name2):
                    names_to_remove.add(name1)
        names -= names_to_remove
        
        return names

    @classmethod
    def _split_long_segments(cls, raw_segments: List[dict]) -> List[dict]:
        """将超过 MAX_SEGMENT_LEN 的段落按句末标点切分。
        在 。！？； 处断开，保持每段不超过 MAX_SEGMENT_LEN。
        """
        result = []
        for seg in raw_segments:
            text = seg["text"]
            if len(text) <= MAX_SEGMENT_LEN:
                result.append(seg)
                continue

            # 按句末标点切分
            parts = []
            current = ""
            for char in text:
                current += char
                if char in '。！？；' and len(current) >= 50:
                    parts.append(current)
                    current = ""
            if current:
                if parts:
                    parts[-1] += current
                else:
                    parts.append(current)

            # 如果切分后只有一段，说明没有合适的断点，保留原文
            if len(parts) <= 1:
                result.append(seg)
                continue

            # 合并过短的段（< 30字），避免碎片化
            merged_parts = []
            buf = ""
            for p in parts:
                if len(buf) + len(p) < MAX_SEGMENT_LEN:
                    buf += p
                else:
                    if buf:
                        merged_parts.append(buf)
                    buf = p
            if buf:
                merged_parts.append(buf)

            for part in merged_parts:
                new_seg = dict(seg)
                new_seg["text"] = part.strip()
                result.append(new_seg)

        return result

    @classmethod
    def _merge_consecutive_dialogues(cls, raw_segments: List[dict]) -> List[dict]:
        """合并同一说话人的连续对话段落。
        如果连续多段都是同一人的对话，合并为一段（用换行分隔）。
        合并后不超过 MAX_SEGMENT_LEN。
        """
        if not raw_segments:
            return raw_segments

        result = []
        i = 0
        while i < len(raw_segments):
            seg = raw_segments[i]
            if seg["segment_type"] != "dialogue" or seg["speaker"] == "__unknown__":
                result.append(seg)
                i += 1
                continue

            # 收集连续的同说话人对话
            speaker = seg["speaker"]
            buf = seg["text"]
            j = i + 1
            while j < len(raw_segments):
                next_seg = raw_segments[j]
                if (next_seg["segment_type"] == "dialogue"
                        and next_seg["speaker"] == speaker
                        and len(buf) + len(next_seg["text"]) + 1 <= MAX_SEGMENT_LEN):
                    buf += next_seg["text"]
                    j += 1
                else:
                    break

            if j > i + 1:
                # 合并了多段
                new_seg = dict(seg)
                new_seg["text"] = buf
                result.append(new_seg)
            else:
                result.append(seg)
            i = j

        return result

    @classmethod
    def _calc_pause(cls, text: str, seg_type: str, prev_idx: int, all_segments: List[dict]) -> int:
        """计算段落后的停顿时间"""
        # 章节标题
        if seg_type == "chapter_title":
            return cls.PAUSE_RULES["chapter_title"]

        # 按标点符号确定基础停顿
        base = 400
        for punct, pause in cls.PUNCTUATION_PAUSE.items():
            if text.rstrip().endswith(punct) or punct in text:
                base = max(base, pause)
                break

        # 段落类型间停顿
        if prev_idx >= 0:
            prev_type = all_segments[prev_idx]["segment_type"]
            if seg_type == "narration" and prev_type == "narration":
                base = max(base, cls.PAUSE_RULES["narration"])
            elif seg_type == "narration" and prev_type == "dialogue":
                base = max(base, 600)
            elif seg_type == "dialogue" and prev_type == "dialogue":
                base = min(base, cls.PAUSE_RULES["dialogue"])

        return base


def parse_novel(text: str, alias_map: dict = None) -> Tuple[List[Segment], Dict[str, CharacterProfile]]:
    """便捷函数：解析小说文本。alias_map 可选的角色别名映射。"""
    return TextParser.parse(text, alias_map=alias_map)


def detect_encoding(file_path: str) -> str:
    """自动检测文件编码。支持 UTF-8/UTF-16/GBK/GB2312/GB18030/Big5。"""
    with open(file_path, 'rb') as f:
        raw = f.read(min(10000, os.path.getsize(file_path)))

    # BOM 检测
    if raw[:3] == b'\xef\xbb\xbf':
        return 'utf-8-sig'
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return 'utf-16'

    # 尝试 UTF-8
    try:
        raw.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        pass

    # 尝试 GBK/GB18030
    try:
        raw.decode('gbk')
        return 'gbk'
    except UnicodeDecodeError:
        pass

    # 尝试 Big5
    try:
        raw.decode('big5')
        return 'big5'
    except UnicodeDecodeError:
        pass

    # 兜底
    return 'utf-8'


if __name__ == "__main__":
    import sys
    import json
    import os

    if len(sys.argv) < 2:
        print("Usage: python3 text_parser.py <novel.txt> [--encoding gbk]")
        sys.exit(1)

    file_path = sys.argv[1]
    encoding = 'utf-8'
    if '--encoding' in sys.argv:
        idx = sys.argv.index('--encoding')
        if idx + 1 < len(sys.argv):
            encoding = sys.argv[idx + 1]
    elif '--auto-encoding' in sys.argv:
        encoding = detect_encoding(file_path)
        print(f"[INFO] Auto-detected encoding: {encoding}")

    with open(file_path, "r", encoding=encoding) as f:
        text = f.read()

    segments, characters = parse_novel(text)

    print(f"=== 解析结果 ===")
    print(f"段落数: {len(segments)}")
    print(f"角色数: {len(characters)}")
    print()

    print("=== 角色列表 ===")
    for name, char in characters.items():
        print(f"  {char.character_id}: {name} (出现{char.mention_count}次, {char.dialogue_frequency})")
    print()

    print("=== 前10个段落 ===")
    for seg in segments[:10]:
        print(f"  [{seg.segment_id}] {seg.segment_type:12s} | {seg.character_name:8s} | {seg.text[:40]}... | pause={seg.pause_after}ms")

    # 输出 JSON
    output = {
        "characters": {name: {
            "character_id": c.character_id,
            "name": c.name,
            "gender": c.gender,
            "age_group": c.age_group,
            "mention_count": c.mention_count,
            "dialogue_frequency": c.dialogue_frequency,
        } for name, c in characters.items()},
        "segments": [{
            "segment_id": s.segment_id,
            "text": s.text,
            "segment_type": s.segment_type,
            "character_id": s.character_id,
            "character_name": s.character_name,
            "emotion": s.emotion,
            "pause_after": s.pause_after,
        } for s in segments],
    }

    out_path = sys.argv[1].rsplit(".", 1)[0] + "_parsed.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n解析结果已保存: {out_path}")
