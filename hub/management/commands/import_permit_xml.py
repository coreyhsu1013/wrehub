from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from xml.etree.ElementTree import iterparse, Element

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import CharField

from hub.models import (
    BuildingPermit,
    BuildingPermitAddress,
    BuildingPermitParcel,
    BuildingPermitFloor,
    BuildingPermitMiscWorkItem,
    BuildingPermitNoteItem,
)
from hub.utils import clean_ws, parse_roc_date, parse_land_text


def clip_to_model(model_cls, data: dict, verbose: bool = False) -> dict:
    """
    對所有 CharField(max_length=...) 做安全截斷，避免 DB varchar 爆炸。
    完整原文保留在 raw（不影響）。
    """
    clipped = dict(data)
    for f in model_cls._meta.get_fields():
        if isinstance(f, CharField):
            name = f.name
            if name in clipped and clipped[name] is not None:
                s = str(clipped[name])
                if len(s) > f.max_length:
                    if verbose:
                        print(f"[CLIP] {name} len={len(s)} -> {f.max_length}")
                    clipped[name] = s[: f.max_length]
    return clipped


def _txt(el: Element | None) -> str:
    if el is None:
        return ""
    t = el.text
    return clean_ws(t or "")


def _child(parent: Element, tag: str) -> Element | None:
    for c in list(parent):
        if c.tag == tag:
            return c
    return None


def _children(parent: Element, tag: str) -> list[Element]:
    return [c for c in list(parent) if c.tag == tag]


def _element_to_dict(el: Element) -> dict:
    """將 XML Element 轉成可 JSON 化的 dict（保留 tag/text/attrs/children）"""
    return {
        "tag": el.tag,
        "text": (el.text or "").strip(),
        "attrs": dict(el.attrib),
        "children": [_element_to_dict(c) for c in list(el)],
    }


def to_decimal(v: str):
    v = clean_ws(v)
    if v == "":
        return None
    try:
        return Decimal(v)
    except Exception:
        return None


def to_int(v: str):
    v = clean_ws(v)
    if v == "":
        return None
    try:
        return int(Decimal(v))
    except Exception:
        return None


@dataclass
class Stats:
    processed: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0


class Command(BaseCommand):
    help = "匯入臺北市建築執照 XML（BuildingPermit），支援 --clear/--dry-run/--limit/--upsert"

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="XML 檔案路徑")
        parser.add_argument("--clear", action="store_true", help="清空建築執照主表＋子表")
        parser.add_argument("--dry-run", action="store_true", help="只解析統計，不寫入 DB")
        parser.add_argument("--limit", type=int, default=0, help="只匯入前 N 筆（0=全部）")
        parser.add_argument("--upsert", action="store_true", help="以 permit_no update_or_create")
        parser.add_argument("--show-keys", action="store_true", help="Print top XML tag keys and exit")

    def handle(self, *args, **opts):
        xml_path: str = opts["file"]
        clear: bool = opts["clear"]
        dry_run: bool = opts["dry_run"]
        limit: int = int(opts["limit"] or 0)
        upsert: bool = opts["upsert"]
        show_keys: bool = opts.get("show_keys", False)

        if clear and not dry_run:
            self.stdout.write("清空：BuildingPermit（包含子表 CASCADE）...")
            BuildingPermit.objects.all().delete()

        stats = Stats()

        # iterparse：只在 end 事件處理 <Data>
        context = iterparse(xml_path, events=("end",))
        
        if show_keys:
            from collections import Counter
            c = Counter()
            count = 0
            for event, elem in context:
                if elem.tag == "Data":
                    count += 1
                    for ch in list(elem):
                        if _txt(ch):
                            c[ch.tag] += 1
                    elem.clear()
                    if count >= 2000:
                        break
            for k, v in c.most_common(50):
                print(v, k)
            return

        for event, elem in context:
            if elem.tag != "Data":
                continue

            stats.processed += 1
            if limit and stats.processed > limit:
                elem.clear()
                break

            # ===== 單值欄位 =====
            permit_no = _txt(_child(elem, "執照號碼"))
            if not permit_no:
                stats.skipped += 1
                elem.clear()
                continue

            # 基本欄位
            permit_year = _txt(_child(elem, "執照年度"))
            issue_date = parse_roc_date(_txt(_child(elem, "發照日期")))
            build_type = _txt(_child(elem, "建造類別"))
            structure = _txt(_child(elem, "構造種類"))
            zoning = _txt(_child(elem, "使用分區"))

            # 面積欄位
            building_area_sqm = to_decimal(_txt(_child(elem, "建築面積")))
            arcade_site_area_sqm = to_decimal(_txt(_child(elem, "騎樓基地面積")))
            other_site_area_sqm = to_decimal(_txt(_child(elem, "其他基地面積")))

            # 其他欄位
            build_deadline = _txt(_child(elem, "建築期限"))
            project_cost = to_int(_txt(_child(elem, "工程金額")))
            owner = _txt(_child(elem, "起造人"))
            designer = _txt(_child(elem, "設計人"))
            supervisor = _txt(_child(elem, "監造人"))
            applicable_law = _txt(_child(elem, "適用法令概要"))

            # 保留舊欄位（向後相容）
            building_info = _txt(_child(elem, "建物資訊"))
            location = _txt(_child(elem, "建築地點"))
            land_text = _txt(_child(elem, "地段地號"))
            summary = _txt(_child(elem, "建築概要"))
            misc_works = _txt(_child(elem, "雜項工作物"))
            notes = _txt(_child(elem, "注意事項"))

            # 解析地段地號
            section, subsection, parcel_no = parse_land_text(land_text)

            # ===== 建物資訊（巢狀） =====
            building_count = block_count = floors_above = floors_below = unit_count = None
            info = _child(elem, "建物資訊")
            if info is not None:
                building_count = to_int(_txt(_child(info, "棟數")))
                block_count = to_int(_txt(_child(info, "幢數")))
                floors_above = to_int(_txt(_child(info, "地上層數")))
                floors_below = to_int(_txt(_child(info, "地下層數")))
                unit_count = to_int(_txt(_child(info, "戶數")))

            # ===== 多筆列表收集 =====
            addresses: list[str] = []
            loc = _child(elem, "建築地點")
            if loc is not None:
                for a in _children(loc, "地址"):
                    t = _txt(a)
                    if t:
                        addresses.append(t)

            parcels: list[str] = []
            pr = _child(elem, "地段地號")
            if pr is not None:
                for p in _children(pr, "地段號"):
                    t = _txt(p)
                    if t:
                        parcels.append(t)

            floors: list[str] = []
            summary_elem = _child(elem, "建築概要")
            if summary_elem is not None:
                for f in _children(summary_elem, "樓層"):
                    t = _txt(f)
                    if t:
                        floors.append(t)

            misc_items: list[str] = []
            misc = _child(elem, "雜項工作物")
            if misc is not None:
                for m in _children(misc, "說明"):
                    t = _txt(m)
                    if t:
                        misc_items.append(t)

            note_items: list[str] = []
            nt = _child(elem, "注意事項")
            if nt is not None:
                for n in _children(nt, "備註說明"):
                    t = _txt(n)
                    if t:
                        note_items.append(t)

            # raw（完整 XML 結構）
            raw_obj = _element_to_dict(elem)

            # ===== 寫入 DB =====
            if dry_run:
                stats.created += 1  # dry-run 用 created 計數代表「可寫入」
                elem.clear()
                continue

            with transaction.atomic():
                data = {
                    "permit_year": permit_year,
                    "issue_date": issue_date,
                    "build_type": build_type,
                    "structure": structure,
                    "zoning": zoning,
                    "building_area_sqm": building_area_sqm,
                    "arcade_site_area_sqm": arcade_site_area_sqm,
                    "other_site_area_sqm": other_site_area_sqm,
                    "building_count": building_count,
                    "block_count": block_count,
                    "floors_above": floors_above,
                    "floors_below": floors_below,
                    "unit_count": unit_count,
                    "build_deadline": build_deadline,
                    "project_cost": project_cost,
                    "owner": owner,
                    "designer": designer,
                    "supervisor": supervisor,
                    "applicable_law": applicable_law,
                    # 保留舊欄位
                    "building_info": building_info,
                    "location": location,
                    "land_text": land_text,
                    "section": section,
                    "subsection": subsection,
                    "parcel_no": parcel_no,
                    "summary": summary,
                    "misc_works": misc_works,
                    "notes": notes,
                    "raw": raw_obj,
                }

                # 對主表欄位做 CharField 截斷
                data = clip_to_model(BuildingPermit, data)

                if upsert:
                    obj, created = BuildingPermit.objects.update_or_create(
                        permit_no=permit_no,
                        defaults=data,
                    )
                    if created:
                        stats.created += 1
                    else:
                        stats.updated += 1
                else:
                    obj = BuildingPermit.objects.create(permit_no=permit_no, **data)
                    stats.created += 1

                # 子表：先刪後建（避免重跑累積）
                obj.addresses.all().delete()
                obj.parcels.all().delete()
                obj.floors.all().delete()
                obj.misc_items.all().delete()
                obj.note_items.all().delete()

                if addresses:
                    address_objs = []
                    for i, t in enumerate(addresses):
                        addr_data = clip_to_model(BuildingPermitAddress, {"address_text": t})
                        address_objs.append(BuildingPermitAddress(permit=obj, seq=i + 1, **addr_data))
                    BuildingPermitAddress.objects.bulk_create(address_objs, batch_size=2000)

                if parcels:
                    parcel_objs = []
                    for i, t in enumerate(parcels):
                        parcel_data = clip_to_model(BuildingPermitParcel, {"parcel_text": t})
                        parcel_objs.append(BuildingPermitParcel(permit=obj, seq=i + 1, **parcel_data))
                    BuildingPermitParcel.objects.bulk_create(parcel_objs, batch_size=2000)

                if floors:
                    BuildingPermitFloor.objects.bulk_create([
                        BuildingPermitFloor(permit=obj, seq=i + 1, floor_text=t)
                        for i, t in enumerate(floors)
                    ], batch_size=2000)

                if misc_items:
                    BuildingPermitMiscWorkItem.objects.bulk_create([
                        BuildingPermitMiscWorkItem(permit=obj, seq=i + 1, misc_text=t)
                        for i, t in enumerate(misc_items)
                    ], batch_size=2000)

                if note_items:
                    BuildingPermitNoteItem.objects.bulk_create([
                        BuildingPermitNoteItem(permit=obj, seq=i + 1, note_text=t)
                        for i, t in enumerate(note_items)
                    ], batch_size=2000)

            elem.clear()

        self.stdout.write(
            self.style.SUCCESS(
                f"完成：processed={stats.processed} created={stats.created} updated={stats.updated} skipped={stats.skipped} dry_run={dry_run}"
            )
        )
