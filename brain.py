import re
from typing import List, Tuple, Optional
from llm import interpret_text


class Memory:
    """用于存储和查询“物体在X度”的知识。"""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    def teach(self, text: str) -> List[Tuple[str, int]]:
        """从输入中提取并记录知识，返回提取到的 (item, degree) 列表。"""
        # 先用规则匹配
        pairs = self.extract_pairs(text)
        # 规则失败时，优先用Ark大模型解析
        if not pairs:
            result = interpret_text(text)
            pairs = result.get("pairs", [])

        for item, deg in pairs:
            norm = self.normalize_degree(deg)
            self.store[item] = norm
        return pairs

    def query(self, item: str) -> Optional[int]:
        """查询物体角度，未记录返回 None。"""
        if item in self.store:
            return self.normalize_degree(self.store[item])
        return None

    @staticmethod
    def normalize_degree(deg: int) -> int:
        """将角度规范化到 [0, 360)；其中360视为0度。"""
        d = deg % 360
        return 0 if d == 0 else d

    @staticmethod
    def extract_pairs(text: str) -> List[Tuple[str, int]]:
        """规则提取：匹配“X在Y度”。允许Y中夹杂口语噪声（如“是、的”等）。支持一行多条。"""
        # 更宽松地抓取到“度”前的所有内容，然后在解析阶段进行过滤
        pattern = re.compile(r"(?P<item>\S+)\s*在\s*(?P<deg>[^度]+)\s*度")
        pairs: List[Tuple[str, int]] = []
        for m in pattern.finditer(text):
            item = m.group("item")
            deg_txt = m.group("deg")
            deg = Memory.parse_degree_text(deg_txt)
            pairs.append((item, deg))
        return pairs

    @staticmethod
    def maybe_extract_item_from_phrase(text: str) -> Optional[str]:
        """支持“我说 西瓜”、“我说西瓜”、“我说西瓜是”这类查询语句。"""
        # 先匹配“我说”后面的词，允许没有空格，并可选“是”结尾
        m = re.search(r"我说\s*(\S+?)(?:是)?$", text)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def parse_degree_text(deg_txt: str) -> int:
        """解析角度文本到整数，支持阿拉伯数字与中文数词。"""
        s = deg_txt.strip().replace(" ", "")
        # 先尝试原样解析阿拉伯数字
        try:
            return int(s)
        except Exception:
            pass

        # 中文数词解析
        digits_map = {
            "零": 0, "〇": 0, "O": 0,
            "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9,
        }
        units = {"千": 1000, "百": 100, "十": 10}

        # 预清理：仅保留阿拉伯数字与中文数词字符
        allowed = set("0123456789") | set(digits_map.keys()) | set(units.keys())
        cleaned = "".join(ch for ch in s if ch in allowed)

        # 若清理后包含阿拉伯数字，直接按阿拉伯数字解析
        if any(ch.isdigit() for ch in cleaned):
            try:
                return int("".join(ch for ch in cleaned if ch.isdigit()))
            except Exception:
                pass

        # 若包含单位字符，按单位规则解析
        if any(u in cleaned for u in units):
            total = 0
            num = 0
            for ch in cleaned:
                if ch in digits_map:
                    num = digits_map[ch]
                elif ch in units:
                    if num == 0:
                        num = 1  # 如“十”表示10
                    total += num * units[ch]
                    num = 0
                else:
                    # 其他字符忽略
                    pass
            total += num
            return total

        # 否则当作逐位数字（如“一二零”-> 120）
        buf = []
        for ch in cleaned:
            if ch in digits_map:
                buf.append(str(digits_map[ch]))
        if buf:
            try:
                return int("".join(buf))
            except Exception:
                pass
        # 解析失败默认返回0
        return 0

    @staticmethod
    def extract_item_llm(text: str) -> Optional[str]:
        """使用Ark模型尝试解析查询对象（当‘我说X’等规则不匹配时）。"""
        result = interpret_text(text)
        qi = result.get("query_item")
        if isinstance(qi, str) and qi.strip():
            return qi.strip()
        return None