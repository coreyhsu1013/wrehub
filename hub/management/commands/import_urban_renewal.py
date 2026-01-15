import csv
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand
from hub.models import UrbanRenewalCase, UrbanRenewalBonus

PING = 3.305785


class Command(BaseCommand):
    help = "Import urban renewal (危老) cases from CSV"

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="CSV file path")

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            self.stderr.write("File not found")
            return

        created = 0
        with path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                case, is_created = UrbanRenewalCase.objects.get_or_create(
                    district=row.get("行政區", "").strip(),
                    section=row.get("地段", "").strip(),
                    subsection=row.get("小段", "").strip(),
                    parcel_no=row.get("地號", "").strip(),
                    defaults={
                        "address": row.get("地址", "").strip(),
                        "approved_date": self._parse_date(row.get("核准日期")),
                        "site_area_sqm": self._to_float(row.get("基地面積㎡")),
                        "site_area_ping": self._sqm_to_ping(row.get("基地面積㎡")),
                        "raw": row,
                    },
                )

                # 獎勵欄位（有填才寫）
                for code, key in [
                    ("structure", "結構評估"),
                    ("seismic", "耐震設計"),
                    ("green", "綠建築"),
                    ("smart", "智慧建築"),
                    ("barrierfree", "無障礙"),
                    ("donation", "捐贈"),
                    ("schedule", "時程"),
                    ("scale", "規模"),
                ]:
                    pct = self._to_float(row.get(key))
                    if pct:
                        UrbanRenewalBonus.objects.update_or_create(
                            case=case,
                            code=code,
                            defaults={"bonus_pct": pct},
                        )

                if is_created:
                    created += 1

        self.stdout.write(f"Done. created={created}")

    def _to_float(self, v):
        try:
            return float(str(v).replace("%", "").strip())
        except Exception:
            return None

    def _sqm_to_ping(self, v):
        try:
            return float(v) / PING
        except Exception:
            return None

    def _parse_date(self, v):
        if not v:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(v.strip(), fmt).date()
            except Exception:
                pass
        return None






