from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from hub.models import WreApproval


PING_SQM = Decimal("3.305785")


def to_decimal(val):
    if val in (None, "", "-", "—"):
        return None
    try:
        s = str(val).strip().replace(",", "")
        return Decimal(s)
    except Exception:
        return None


def normalize_parcel_no(v: str) -> str:
    s = (v or "").strip()
    if not s:
        return ""
    # 常見：####-0000 或 ####
    s = s.replace("－", "-")
    return s


class Command(BaseCommand):
    help = "Import WRE approvals from CSV"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="Path to CSV file (utf-8)")
        parser.add_argument("--dry-run", action="store_true", help="Parse only, do not write DB")

    def handle(self, *args, **opts):
        file_path = Path(opts["file"])
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        dry = bool(opts.get("dry_run"))

        created = 0
        updated = 0
        skipped = 0

        with file_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            # 期望欄位（你可以多給，我們只取需要的）
            # approve_date,district,section,subsection,parcel_no,address,site_area_sqm,site_area_ping
            for row in reader:
                approve_date = parse_date((row.get("approve_date") or "").strip())
                district = (row.get("district") or "").strip()
                section = (row.get("section") or "").strip()
                subsection = (row.get("subsection") or "").strip()
                parcel_no = normalize_parcel_no(row.get("parcel_no") or "")
                address = (row.get("address") or "").strip()

                site_area_sqm = to_decimal(row.get("site_area_sqm"))
                site_area_ping = to_decimal(row.get("site_area_ping"))
                if site_area_ping is None and site_area_sqm is not None:
                    site_area_ping = (site_area_sqm / PING_SQM).quantize(Decimal("0.01"))

                # 最低限度：有日期或地址或地號其中之一
                if not (approve_date or address or parcel_no):
                    skipped += 1
                    continue

                # 用比較穩的 key：日期 + 地址(前40字) + 地號
                key_addr = (address or "")[:40]
                key = f"{approve_date or ''}|{district}|{section}|{subsection}|{parcel_no}|{key_addr}"

                defaults = dict(
                    approve_date=approve_date,
                    district=district,
                    section=section,
                    subsection=subsection,
                    parcel_no=parcel_no,
                    address=address,
                    site_area_sqm=site_area_sqm,
                    site_area_ping=site_area_ping,
                    raw=row,
                )

                if dry:
                    created += 1
                    continue

                obj, is_created = WreApproval.objects.update_or_create(
                    # 用 key 放 raw 內避免新增欄位：以 address+date+parcel 做近似唯一
                    # Django 沒有複合 unique，先用這個組合查找
                    approve_date=approve_date,
                    district=district,
                    section=section,
                    subsection=subsection,
                    parcel_no=parcel_no,
                    address=address,
                    defaults=defaults,
                )

                if is_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. created={created} updated={updated} skipped={skipped} dry_run={dry}"
        ))






