from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q

from hub.models import BuildingPermit, WreApproval, WrePermitMatch


def normalize(s: str) -> str:
    return (s or "").strip()


class Command(BaseCommand):
    help = "Match WRE approvals to building permits"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Only process N approvals (0=all)")
        parser.add_argument("--dry-run", action="store_true", help="Do not write DB")
        parser.add_argument("--use-address", action="store_true", help="Also match by address contains (fallback)")

    def handle(self, *args, **opts):
        limit = int(opts["limit"] or 0)
        dry = bool(opts.get("dry_run"))
        use_addr = bool(opts.get("use_address"))

        qs = WreApproval.objects.all().order_by("id")
        if limit:
            qs = qs[:limit]

        created = 0
        skipped = 0

        for w in qs:
            d = normalize(w.district)
            sec = normalize(w.section)
            sub = normalize(w.subsection)
            parcel = normalize(w.parcel_no)
            addr = normalize(w.address)

            matched = False

            # 1) exact: section/subsection/parcel 必須齊
            if d and sec and sub and parcel:
                pqs = BuildingPermit.objects.filter(
                    district=d, section=sec, subsection=sub, parcel_no=parcel
                )
                if pqs.exists():
                    for p in pqs[:20]:
                        if not dry:
                            obj, is_created = WrePermitMatch.objects.get_or_create(
                                wre=w, permit=p, match_type=WrePermitMatch.MATCH_EXACT,
                                defaults={"rule_ok": True, "notes": "exact match"},
                            )
                            if is_created:
                                created += 1
                        else:
                            created += 1
                    matched = True

            # 2) fallback by address contains
            if (not matched) and use_addr and addr:
                # 避免太短造成大量誤判
                key = addr
                if len(key) >= 6:
                    pqs = BuildingPermit.objects.filter(location__contains=key)
                    for p in pqs[:10]:
                        if not dry:
                            obj, is_created = WrePermitMatch.objects.get_or_create(
                                wre=w, permit=p, match_type=WrePermitMatch.MATCH_MULTI,
                                defaults={"rule_ok": False, "notes": "address fallback (needs review)"},
                            )
                            if is_created:
                                created += 1
                        else:
                            created += 1
                    matched = matched or pqs.exists()

            if not matched:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. created_matches={created} skipped_wre={skipped} dry_run={dry} use_address={use_addr}"
        ))






