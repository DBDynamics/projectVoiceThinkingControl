import os
import json
from typing import List, Tuple, Optional, Dict, Any

try:
    from volcenginesdkarkruntime import Ark  # type: ignore
except Exception:
    Ark = None  # 允许在未安装SDK时优雅降级


ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
ARK_MODEL_ID = os.getenv("ARK_MODEL_ID", "doubao-seed-1-6-251015")


def ark_available() -> bool:
    return Ark is not None and bool(os.getenv("ARK_API_KEY"))


def _get_ark_client():
    assert Ark is not None
    return Ark(base_url=ARK_BASE_URL, api_key=os.environ.get("ARK_API_KEY"))


def interpret_text(text: str) -> Dict[str, Any]:
    """使用Ark模型解析文本，返回结构：{"pairs": [(item, degree)], "query_item": Optional[str]}"""
    if not ark_available():
        return {"pairs": [], "query_item": None}

    client = _get_ark_client()
    prompt = (
        "从以下中文输入中，提取两类信息：\n"
        "1) 教知识：格式为‘X在Y度’，可包含中文数字或口语噪声；输出为数组(pairs)，每项是{item, degree整数}；\n"
        "2) 查询：如‘我说西瓜’或‘我说西瓜是’或直接水果名；输出query_item为要查询的对象；\n"
        "注意：度数是整数，‘三百六十’等同0；仅返回JSON，不要其他解释。\n\n"
        f"输入：{text}"
    )
    try:
        completion = client.chat.completions.create(
            model=ARK_MODEL_ID,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
        content = completion.choices[0].message.content
        data = json.loads(content)
        pairs: List[Tuple[str, int]] = []
        for p in data.get("pairs", []):
            item = str(p.get("item", "")).strip()
            try:
                deg = int(p.get("degree", 0))
            except Exception:
                deg = 0
            if item:
                pairs.append((item, deg))
        query_item = data.get("query_item")
        if isinstance(query_item, str):
            query_item = query_item.strip() or None
        else:
            query_item = None
        return {"pairs": pairs, "query_item": query_item}
    except Exception:
        return {"pairs": [], "query_item": None}