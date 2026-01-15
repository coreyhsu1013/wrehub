from django.core.management.base import BaseCommand, CommandError
from hub.models import BuildingPermit
import csv
from pathlib import Path
from decimal import Decimal
from datetime import date


def parse_date(s: str):
    s = (s or "").strip()
    if not s:
        return None
    # expecting YYYY-MM-DD
    try:
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


class Command(BaseCommand):
    help = "Import building permits from CSV file"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="Path to CSV file")

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        created = 0
        updated = 0

        with file_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                permit_no = (row.get("permit_no") or "").strip()
                if not permit_no:
                    continue

                defaults = {
                    "permit_year": (row.get("permit_year") or "").strip(),
                    "issue_date": parse_date(row.get("issue_date") or ""),
                    "district": (row.get("district") or "").strip(),
                    "section": (row.get("section") or "").strip(),
                    "subsection": (row.get("subsection") or "").strip(),
                    "parcel_no": (row.get("parcel_no") or "").strip(),
                    "build_type": (row.get("permit_type") or "").strip(),
                    "zoning": (row.get("zoning") or "").strip(),
                    "location": (row.get("address") or "").strip(),
                    "designer": (row.get("designer") or "").strip(),
                    "building_area_sqm": self._to_decimal(row.get("building_area_sqm")),
                    "other_site_area_sqm": self._to_decimal(row.get("other_site_area_sqm")),
                    "applicable_law": (row.get("applicable_law") or "").strip(),
                    "notes": (row.get("notes") or "").strip(),
                    "raw": row,
                }

                obj, is_created = BuildingPermit.objects.update_or_create(
                    permit_no=permit_no,
                    defaults=defaults,
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Done. created={created}, updated={updated}"))

    @staticmethod
    def _to_decimal(val):
        if val in (None, "", "-"):
            return None
        try:
            return Decimal(str(val).strip())
        except Exception:
            return None






