from __future__ import annotations
import re
from datetime import date
from typing import Optional, Tuple


def clean_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def parse_roc_date(s: str) -> Optional[date]:
    s = clean_ws(s).replace("-", "/")
    if not s:
        return None

    m = re.match(r"^(\d{2,3})/(\d{1,2})/(\d{1,2})$", s)
    if m:
        y = int(m.group(1)) + 1911
        return date(y, int(m.group(2)), int(m.group(3)))

    m = re.match(r"^(\d{2,3})(\d{2})(\d{2})$", s)
    if m:
        y = int(m.group(1)) + 1911
        return date(y, int(m.group(2)), int(m.group(3)))

    return None


def norm_parcel_no(s: str) -> str:
    s = clean_ws(s).replace("－", "-").replace("—", "-").replace("–", "-")
    if not s:
        return ""
    m = re.match(r"^(\d+)(?:-(\d+))?$", s)
    if not m:
        return s
    a = int(m.group(1))
    b = int(m.group(2) or 0)
    return f"{a}-{b:04d}"


def parse_land_text(land_text: str) -> Tuple[str, str, str]:
    """
    強化版：
    - 支援多筆地號，用第一筆做 parcel_no（其餘留在 raw）
    - 支援 '地段：xxx'、'小段：yyy' 格式
    - 清掉括號與多餘說明
    """
    t = clean_ws(land_text)
    if not t:
        return "", "", ""

    # normalize punctuation
    t = t.replace("，", ",").replace("、", ",").replace("．", ".")
    # remove bracket notes
    t = re.sub(r"[（(].*?[）)]", " ", t)
    t = clean_ws(t)

    sec = ""
    sub = ""
    parcel = ""

    # format A: 'xxx段' 'yyy小段'
    m = re.search(r"([^\s,]+?段)", t)
    if m:
        sec = m.group(1)

    m = re.search(r"([^\s,]+?小段)", t)
    if m:
        sub = m.group(1)

    # format B: '地段: XXX' '小段: YYY'
    if not sec:
        m = re.search(r"地段[:：]\s*([^\s,]+)", t)
        if m:
            sec = m.group(1)
    if not sub:
        m = re.search(r"小段[:：]\s*([^\s,]+)", t)
        if m:
            sub = m.group(1)

    # parcel candidates: 123 or 123-4, possibly multiple separated by comma
    nums = re.findall(r"\d+(?:-\d+)?", t)
    if nums:
        parcel = norm_parcel_no(nums[0])

    return sec, sub, parcel
