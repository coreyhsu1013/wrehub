from __future__ import annotations

import csv
from io import StringIO
from typing import Dict

from django.db.models import Avg, Count, F, FloatField, Q
from django.db.models.functions import Cast
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import BuildingPermit, UrbanRenewalCase

PING = 3.305785


def zone_q(zone: str) -> Q:
    z = (zone or "").strip()
    if z == "住二":
        return Q(zoning__contains="住2") | Q(zoning__contains="第二種住宅")
    if z == "住三":
        return Q(zoning__contains="住3") | Q(zoning__contains="第三種住宅")
    if z == "商三":
        return Q(zoning__contains="商3") | Q(zoning__contains="商三") | Q(zoning__contains="第三種商業")
    if z == "商四":
        return Q(zoning__contains="商4") | Q(zoning__contains="商四") | Q(zoning__contains="第四種商業")
    if z == "其他":
        return ~(
            Q(zoning__contains="住2") | Q(zoning__contains="第二種住宅") |
            Q(zoning__contains="住3") | Q(zoning__contains="第三種住宅") |
            Q(zoning__contains="商3") | Q(zoning__contains="商三") | Q(zoning__contains="第三種商業") |
            Q(zoning__contains="商4") | Q(zoning__contains="商四") | Q(zoning__contains="第四種商業")
        )
    return Q()


def build_queryset(q: Dict[str, str]):
    qs = BuildingPermit.objects.all()

    # zone
    zone = (q.get("zone") or "").strip()
    if zone:
        qs = qs.filter(zone_q(zone))

    # permit year
    year = (q.get("year") or "").strip()
    if year:
        qs = qs.filter(permit_year=year)

    # designer keyword
    designer = (q.get("designer") or "").strip()
    if designer:
        qs = qs.filter(designer__contains=designer)

    # site ping range (other_site_area_sqm)
    site_min = (q.get("site_min") or "").strip()
    site_max = (q.get("site_max") or "").strip()
    if site_min:
        qs = qs.filter(other_site_area_sqm__gte=float(site_min) * PING)
    if site_max:
        qs = qs.filter(other_site_area_sqm__lte=float(site_max) * PING)

    # bld ping range (building_area_sqm)
    bld_min = (q.get("bld_min") or "").strip()
    bld_max = (q.get("bld_max") or "").strip()
    if bld_min:
        qs = qs.filter(building_area_sqm__gte=float(bld_min) * PING)
    if bld_max:
        qs = qs.filter(building_area_sqm__lte=float(bld_max) * PING)

    # date range
    date_from = (q.get("date_from") or "").strip()
    date_to = (q.get("date_to") or "").strip()
    if date_from:
        qs = qs.filter(issue_date__gte=date_from)
    if date_to:
        qs = qs.filter(issue_date__lte=date_to)

    # annotate metrics
    qs = qs.annotate(
        site_ping=Cast("other_site_area_sqm", FloatField()) / PING,
        bld_ping=Cast("building_area_sqm", FloatField()) / PING,
        cost=Cast("project_cost", FloatField()),
    ).annotate(
        cost_per_bld_ping=F("cost") / (F("bld_ping") + 1e-9),
        bld_per_site=F("bld_ping") / (F("site_ping") + 1e-9),
    )

    # sort
    sort = (q.get("sort") or "-issue_date").strip()
    allow = {
        "issue_date", "-issue_date",
        "site_ping", "-site_ping",
        "bld_ping", "-bld_ping",
        "project_cost", "-project_cost",
        "cost_per_bld_ping", "-cost_per_bld_ping",
        "bld_per_site", "-bld_per_site",
    }
    if sort not in allow:
        sort = "-issue_date"
    qs = qs.order_by(sort, "-id")

    return qs, sort



def home(request: HttpRequest) -> HttpResponse:
    # 入口頁：給你同事用
    return render(request, "hub/home.html", {})


def permit_list(request: HttpRequest) -> HttpResponse:
    q = request.GET.copy()

    # default
    if not q:
        q["site_min"] = "25"
        q["site_max"] = "40"
        q["zone"] = "住三"
        q["sort"] = "-issue_date"

    qs, sort = build_queryset(q)

    summary = qs.aggregate(
        n=Count("id"),
        avg_site=Avg("site_ping"),
        avg_bld=Avg("bld_ping"),
        avg_cost=Avg("project_cost"),
        avg_cpb=Avg("cost_per_bld_ping"),
        avg_bps=Avg("bld_per_site"),
    )

    top_designers = (
        qs.exclude(designer="")
          .values("designer")
          .annotate(n=Count("id"))
          .order_by("-n")[:20]
    )

    # pagination
    page = int(q.get("page", "1") or 1)
    page_size = 50
    start = (page - 1) * page_size
    end = start + page_size
    items = list(qs[start:end])

    sort_fields = [
        "-issue_date","issue_date",
        "-site_ping","site_ping",
        "-bld_ping","bld_ping",
        "-project_cost","project_cost",
        "-cost_per_bld_ping","cost_per_bld_ping",
        "-bld_per_site","bld_per_site",
    ]

    ctx = {
        "sort_fields": sort_fields,
        "q": q,
        "sort": sort,
        "summary": summary,
        "top_designers": top_designers,
        "items": items,
        "page": page,
        "page_size": page_size,
        "zones": ["住二", "住三", "商三", "商四", "其他"],
    }
    
    # template 不能用 .split()，所以排序選項在 view 產生
    ctx["sort_choices"] = [
        ("-issue_date", "Issue date ↓"),
        ("issue_date", "Issue date ↑"),
        ("-site_ping", "Site ping ↓"),
        ("site_ping", "Site ping ↑"),
        ("-bld_ping", "Bld ping ↓"),
        ("bld_ping", "Bld ping ↑"),
        ("-project_cost", "Project cost ↓"),
        ("project_cost", "Project cost ↑"),
        ("-cost_per_bld_ping", "Cost/bld ping ↓"),
        ("cost_per_bld_ping", "Cost/bld ping ↑"),
        ("-bld_per_site", "Bld/site ↓"),
        ("bld_per_site", "Bld/site ↑"),
    ]
    return render(request, "hub/permit_list.html", ctx)


def permit_detail(request: HttpRequest, pk: int) -> HttpResponse:
    obj = get_object_or_404(BuildingPermit, pk=pk)
    # 也把 ping 算出來方便看
    site_ping = float(obj.other_site_area_sqm or 0) / PING if obj.other_site_area_sqm else None
    bld_ping = float(obj.building_area_sqm or 0) / PING if obj.building_area_sqm else None
    cpb = (float(obj.project_cost or 0) / (bld_ping + 1e-9)) if bld_ping else None
    bps = (bld_ping / (site_ping + 1e-9)) if (bld_ping and site_ping) else None
    return render(request, "hub/permit_detail.html", {
        "obj": obj,
        "site_ping": site_ping,
        "bld_ping": bld_ping,
        "cpb": cpb,
        "bps": bps,
    })


def permit_export_csv(request: HttpRequest) -> HttpResponse:
    q = request.GET.copy()
    qs, _ = build_queryset(q)

    # 限制輸出量避免炸掉（你要全量再加參數）
    limit = int(q.get("limit", "5000") or 5000)
    qs = qs[:limit]

    out = StringIO()
    w = csv.writer(out)
    w.writerow([
        "permit_no", "permit_year", "issue_date", "zoning", "designer",
        "site_ping", "bld_ping", "project_cost", "cost_per_bld_ping", "bld_per_site"
    ])

    for o in qs:
        w.writerow([
            o.permit_no, o.permit_year, o.issue_date, o.zoning, o.designer,
            f"{float(getattr(o,'site_ping',0) or 0):.1f}",
            f"{float(getattr(o,'bld_ping',0) or 0):.1f}",
            o.project_cost or "",
            f"{float(getattr(o,'cost_per_bld_ping',0) or 0):.0f}",
            f"{float(getattr(o,'bld_per_site',0) or 0):.2f}",
        ])

    resp = HttpResponse(out.getvalue(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="permits.csv"'
    return resp


def permit_compare(request: HttpRequest) -> HttpResponse:
    q = request.GET.copy()

    # defaults：你最常用的區間
    if not q:
        q["site_min"] = "25"
        q["site_max"] = "40"
        q["year"] = ""   # 不限年度
        q["sort"] = "-issue_date"

    zones = ["住二", "住三", "商三", "商四"]

    result = []
    for z in zones:
        qq = q.copy()
        qq["zone"] = z
        qs, _ = build_queryset(qq)

        summary = qs.aggregate(
            n=Count("id"),
            avg_site=Avg("site_ping"),
            avg_bld=Avg("bld_ping"),
            avg_cost=Avg("project_cost"),
            avg_cpb=Avg("cost_per_bld_ping"),
            avg_bps=Avg("bld_per_site"),
        )

        top_designers = (
            qs.exclude(designer="")
              .values("designer")
              .annotate(n=Count("id"))
              .order_by("-n")[:10]
        )

        result.append({
            "zone": z,
            "summary": summary,
            "top_designers": list(top_designers),
        })

    return render(request, "hub/permit_compare.html", {
        "q": q,
        "result": result,
        "zones": zones,
    })


def compare_urban_renewal(request: HttpRequest) -> HttpResponse:
    """
    Compare page for Urban Renewal cases (危老).
    Query params:
      - site_min/site_max: ping range (site_area_ping)
      - district: optional exact district
      - date_from/date_to: YYYY-MM-DD
      - q: keyword in address / raw
    """
    from django.db.models import Avg, Q
    from .models import UrbanRenewalCase

    q = (request.GET.get("q") or "").strip()
    district = (request.GET.get("district") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()

    def to_float(x):
        try:
            return float(x)
        except Exception:
            return None

    site_min = to_float(request.GET.get("site_min") or "")
    site_max = to_float(request.GET.get("site_max") or "")

    qs = UrbanRenewalCase.objects.all()

    if q:
        qs = qs.filter(Q(address__icontains=q) | Q(raw__cols__icontains=q))
    if district:
        qs = qs.filter(district=district)
    if date_from:
        qs = qs.filter(approved_date__gte=date_from)
    if date_to:
        qs = qs.filter(approved_date__lte=date_to)
    if site_min is not None:
        qs = qs.filter(site_area_ping__gte=site_min)
    if site_max is not None:
        qs = qs.filter(site_area_ping__lte=site_max)

    qs = qs.order_by("-approved_date", "-case_no")

    stats = {
        "count": qs.count(),
        "avg_site_ping": qs.aggregate(a=Avg("site_area_ping"))["a"],
        "avg_total_bonus": qs.aggregate(a=Avg("total_bonus_pct"))["a"],
    }

    districts = (UrbanRenewalCase.objects.exclude(district="")
                 .values_list("district", flat=True).distinct().order_by("district"))

    ctx = {
        "rows": qs[:200],
        "stats": stats,
        "q": q,
        "district": district,
        "districts": list(districts),
        "date_from": date_from,
        "date_to": date_to,
        "site_min": "" if site_min is None else site_min,
        "site_max": "" if site_max is None else site_max,
    }
    return render(request, "hub/compare_urban_renewal.html", ctx)

def urban_renewal_list(request):
    q = (request.GET.get("q") or "").strip()
    district = (request.GET.get("district") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()

    ping_min = request.GET.get("ping_min") or ""
    ping_max = request.GET.get("ping_max") or ""

    qs = UrbanRenewalCase.objects.all().order_by("-approved_date", "-case_no")

    if q:
        qs = qs.filter(Q(address__icontains=q) | Q(raw__cols__icontains=q))
    if district:
        qs = qs.filter(district=district)

    # 日期篩選（YYYY-MM-DD）
    if date_from:
        qs = qs.filter(approved_date__gte=date_from)
    if date_to:
        qs = qs.filter(approved_date__lte=date_to)

    # 坪數篩選（用 site_area_ping）
    def to_float(x):
        try:
            return float(x)
        except Exception:
            return None

    pmin = to_float(ping_min)
    pmax = to_float(ping_max)
    if pmin is not None:
        qs = qs.filter(site_area_ping__gte=pmin)
    if pmax is not None:
        qs = qs.filter(site_area_ping__lte=pmax)

    # districts for dropdown
    districts = (UrbanRenewalCase.objects.exclude(district="")
                 .values_list("district", flat=True).distinct().order_by("district"))

    ctx = {
        "rows": qs[:500],  # 先限制500筆，後續再做 pagination
        "q": q,
        "district": district,
        "districts": list(districts),
        "date_from": date_from,
        "date_to": date_to,
        "ping_min": ping_min,
        "ping_max": ping_max,
        "count": qs.count(),
    }
    return render(request, "hub/urban_renewal_list.html", ctx)
