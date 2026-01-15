from __future__ import annotations

import csv
import re
from decimal import Decimal
from pathlib import Path
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from hub.models import UrbanRenewalCase, UrbanRenewalBonus

PING_SQM = Decimal("3.305785")

# 108/3/19  or 108/03/19
RE_ROC_DATE = re.compile(r"^(?P<y>\d{2,3})/(?P<m>\d{1,2})/(?P<d>\d{1,2})$")

def parse_roc_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    m = RE_ROC_DATE.match(s)
    if not m:
        return None
    y = int(m.group("y")) + 1911
    mo = int(m.group("m"))
    d = int(m.group("d"))
    try:
        return date(y, mo, d)
    except Exception:
        return None

def to_decimal(s: str) -> Decimal | None:
    s = (s or "").strip()
    if not s:
        return None
    s = s.replace(",", "").replace("㎡", "").replace("％", "").replace("%", "")
    try:
        return Decimal(s)
    except Exception:
        return None

def is_int(s: str) -> bool:
    s = (s or "").strip()
    return bool(s) and s.isdigit()

def clean_text(s: str) -> str:
    return (s or "").strip()

def extract_case_row(cols: list[str]) -> dict | None:
    """
    cols 是一列（很多欄，可能位移）
    我們用『規則』抽出欄位，而不是相信 col index。
    """
    cols = [clean_text(c) for c in cols]

    # 1) 案件列判定：第一欄是數字
    if not cols or not is_int(cols[0]):
        return None

    case_no = int(cols[0])

    # 2) 找核准日期：通常在 col4/col5
    approved = None
    date_idx = None
    for idx in range(2, min(len(cols), 12)):
        d = parse_roc_date(cols[idx])
        if d:
            approved = d
            date_idx = idx
            break

    # 3) 行政區 + 基地面積（㎡）通常在 col1 例如： "327 中山區"
    district = ""
    site_area_sqm = None
    if len(cols) >= 2:
        # 例如 "327 中山區" 或 "101 大安區"
        parts = cols[1].split()
        if parts:
            # 找第一個像數字的當面積
            if parts[0].replace(".", "", 1).isdigit():
                site_area_sqm = to_decimal(parts[0])
                # 後面合併當 district
                district = "".join(parts[1:]).strip()
            else:
                # 可能沒有面積，只剩區名
                district = cols[1].strip()

    # 4) 地段地號 / 門牌地址：通常在日期前 1~3 欄，但 PDF 會換行
    #    我們取 date_idx 前面的一段文字合併，粗分成 land + address
    land_text = ""
    addr_text = ""

    if date_idx is not None:
        # date_idx 之前：col2..date_idx-1
        mid = " ".join([c for c in cols[2:date_idx] if c])
        # 很多資料 land/addr 都塞在一起：先整串塞進 address，land 留空（後續再進階解析）
        addr_text = mid.strip()
        land_text = ""
    else:
        # 沒找到日期：保守抓 col2..col5
        mid = " ".join([c for c in cols[2:6] if c])
        addr_text = mid.strip()

    # 5) 總獎勵（%）：固定欄位位置為倒數第 4 欄
    total_bonus = None
    if len(cols) >= 4:
        total_bonus = to_decimal(cols[-4])

    # 6) 備註（例如：失其效力）會出現在日期後面附近：找含中文且不是數字的
    note = ""
    if date_idx is not None:
        tail = cols[date_idx+1:date_idx+4]
        for x in tail:
            if x and (not x.replace(".", "", 1).isdigit()) and (not parse_roc_date(x)):
                # 例如：失其效力
                if len(x) <= 12:
                    note = x
                    break

    # 7) site ping
    site_ping = None
    if site_area_sqm is not None:
        try:
            site_ping = (site_area_sqm / PING_SQM).quantize(Decimal("0.01"))
        except Exception:
            site_ping = None

    return {
        "case_no": case_no,
        "district": district,
        "approved_date": approved,
        "site_area_sqm": site_area_sqm,
        "site_area_ping": site_ping,
        "address": addr_text,
        "land_text": land_text,
        "note": note,
        "total_bonus_pct": total_bonus,
        "raw_cols": cols,
    }

class Command(BaseCommand):
    help = "Import Taipei urban renewal PDF-extracted raw CSV (auto-normalize shifting columns)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to urban_renewal_raw.csv")
        parser.add_argument("--limit", type=int, default=0, help="Only import first N case rows (0=all)")
        parser.add_argument("--dry-run", action="store_true", help="Parse only, no DB writes")

    def handle(self, *args, **opts):
        file_path = Path(opts["file"])
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        limit = int(opts["limit"] or 0)
        dry = bool(opts["dry_run"])

        created = 0
        updated = 0
        skipped = 0
        parsed = 0

        with file_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)

            for row in reader:
                item = extract_case_row(row)
                if not item:
                    continue

                parsed += 1
                if limit and parsed > limit:
                    break

                defaults = dict(
                    source="taipei_ur",
                    case_no=item["case_no"],
                    district=item["district"],
                    address=item["address"],
                    approved_date=item["approved_date"],
                    site_area_sqm=item["site_area_sqm"],
                    site_area_ping=item["site_area_ping"],
                    total_bonus_pct=item["total_bonus_pct"],
                    raw={
                        "cols": item["raw_cols"],
                        "note": item["note"],
                        "land_text": item["land_text"],
                    },
                )

                if dry:
                    continue

                obj, is_created = UrbanRenewalCase.objects.update_or_create(
                    source="taipei_ur",
                    case_no=item["case_no"],
                    defaults=defaults,
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. parsed={parsed} created={created} updated={updated} skipped={skipped} dry_run={dry}"
        ))

