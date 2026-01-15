from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Q
from collections import Counter

from hub.models import BuildingPermit

PING = 3.305785


def ping(v_sqm):
    return float(v_sqm) / PING if v_sqm is not None else None


def norm_zone(z: str) -> str:
    z = (z or "").strip()
    if not z:
        return "UNKNOWN"
    # housing
    if "住2" in z or "第二種住宅" in z or "第二種住宅區" in z:
        return "住二"
    if "住3" in z or "第三種住宅" in z or "第三種住宅區" in z:
        return "住三"
    # commercial
    if "商3" in z or "商三" in z or "第三種商業" in z:
        return "商三"
    if "商4" in z or "商四" in z or "第四種商業" in z:
        return "商四"
    return "其他"


class Command(BaseCommand):
    help = "Report small base stats by zoning and designer (using other_site_area_sqm as site area)"

    def add_arguments(self, parser):
        parser.add_argument("--min", type=float, default=25.0, help="min site ping")
        parser.add_argument("--max", type=float, default=30.0, help="max site ping")
        parser.add_argument("--top", type=int, default=10, help="top N designers per zoning")

    def handle(self, *args, **opts):
        pmin = float(opts["min"])
        pmax = float(opts["max"])
        topn = int(opts["top"])

        # site area uses other_site_area_sqm (based on dataset reality)
        qs = (BuildingPermit.objects
              .exclude(other_site_area_sqm__isnull=True)
              .filter(other_site_area_sqm__gte=pmin*PING, other_site_area_sqm__lte=pmax*PING)
        )

        print(f"=== 基地 {pmin}-{pmax} 坪（以其他基地面積換算） ===")
        print("total=", qs.count())

        # zoning breakdown
        zone_counter = Counter(norm_zone(z) for z in qs.values_list("zoning", flat=True))
        for k,v in zone_counter.most_common():
            print(f"- {k}: {v}")

        # per zoning top designers
        for zone in ["住二","住三","商三","商四","其他","UNKNOWN"]:
            sub = qs.filter(zoning__isnull=False)
            # apply rough filter by keywords in raw zoning string
            if zone == "住二":
                sub = sub.filter(Q(zoning__contains="住2") | Q(zoning__contains="第二種住宅"))
            elif zone == "住三":
                sub = sub.filter(Q(zoning__contains="住3") | Q(zoning__contains="第三種住宅"))
            elif zone == "商三":
                sub = sub.filter(Q(zoning__contains="商3") | Q(zoning__contains="商三") | Q(zoning__contains="第三種商業"))
            elif zone == "商四":
                sub = sub.filter(Q(zoning__contains="商4") | Q(zoning__contains="商四") | Q(zoning__contains="第四種商業"))
            elif zone == "UNKNOWN":
                sub = sub.filter(Q(zoning="") | Q(zoning__isnull=True))
            else:
                sub = sub.exclude(Q(zoning__contains="住2") | Q(zoning__contains="第二種住宅") |
                                  Q(zoning__contains="住3") | Q(zoning__contains="第三種住宅") |
                                  Q(zoning__contains="商3") | Q(zoning__contains="商三") | Q(zoning__contains="第三種商業") |
                                  Q(zoning__contains="商4") | Q(zoning__contains="商四") | Q(zoning__contains="第四種商業"))

            if sub.count() == 0:
                continue

            print(f"\n[{zone}] count={sub.count()}")
            rows = (sub.exclude(designer="")
                       .values("designer")
                       .annotate(n=Count("id"),
                                 avg_site=Avg("other_site_area_sqm"),
                                 avg_bld=Avg("building_area_sqm"),
                                 avg_cost=Avg("project_cost"))
                       .order_by("-n")[:topn])

            for r in rows:
                avg_site_ping = ping(r["avg_site"])
                avg_bld_ping = ping(r["avg_bld"])
                print(f"- {r['designer']} | n={r['n']} | avg_site={avg_site_ping:.1f}坪 | avg_bld={avg_bld_ping:.1f}坪 | avg_cost={int(r['avg_cost'] or 0)}")






