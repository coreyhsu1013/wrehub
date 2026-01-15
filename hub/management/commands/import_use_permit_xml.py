# hub/management/commands/import_use_permit_xml.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from xml.etree.ElementTree import iterparse, Element

from django.core.management.base import BaseCommand
from django.db import transaction

from hub.models_use_permit import (
    BuildingUsePermit,
    BuildingUsePermitAddress,
    BuildingUsePermitParcel,
    BuildingUsePermitFloor,
    BuildingUsePermitParking,
    BuildingUsePermitNote,
    BuildingUsePermitMiscWork,
    BuildingUsePermitChangeApproval,
    parse_decimal_maybe,
)


def _txt(el: Element | None) -> str:
    if el is None:
        return ""
    t = el.text
    return (t or "").strip()


def _child(parent: Element, tag: str) -> Element | None:
    for c in list(parent):
        if c.tag == tag:
            return c
    return None


def _children(parent: Element, tag: str) -> list[Element]:
    return [c for c in list(parent) if c.tag == tag]


def _element_to_primitive(el: Element) -> Any:
    """
    將 XML Element 轉成可 JSON 化的 dict（保留 tag/text/attrs/children）
    用於 raw（僅備查）
    """
    return {
        "tag": el.tag,
        "text": (el.text or "").strip(),
        "attrs": dict(el.attrib),
        "children": [_element_to_primitive(c) for c in list(el)],
    }


@dataclass
class Stats:
    processed: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0


class Command(BaseCommand):
    help = "匯入臺北市使用執照 XML（BuildingUsePermit），支援 --clear/--dry-run/--limit/--upsert"

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="XML 檔案路徑")
        parser.add_argument("--clear", action="store_true", help="清空使用執照主表＋子表")
        parser.add_argument("--dry-run", action="store_true", help="只解析統計，不寫入 DB")
        parser.add_argument("--limit", type=int, default=0, help="只匯入前 N 筆（0=全部）")
        parser.add_argument("--upsert", action="store_true", help="以 (permit_year, permit_no) 更新/新增")

    def handle(self, *args, **opts):
        xml_path: str = opts["file"]
        clear: bool = opts["clear"]
        dry_run: bool = opts["dry_run"]
        limit: int = int(opts["limit"] or 0)
        upsert: bool = opts["upsert"]

        if clear and not dry_run:
            self.stdout.write("清空：BuildingUsePermit（包含子表 CASCADE）...")
            BuildingUsePermit.objects.all().delete()

        stats = Stats()

        # iterparse：只在 end 事件處理 <Data>
        context = iterparse(xml_path, events=("end",))
        for event, elem in context:
            if elem.tag != "Data":
                continue

            stats.processed += 1
            if limit and stats.processed > limit:
                # 清理 elem 以釋放 memory
                elem.clear()
                break

            # ===== 單值欄位 =====
            permit_year = _txt(_child(elem, "執照年度"))
            permit_no = _txt(_child(elem, "執照號碼"))

            # 沒有唯一鍵就跳過（不猜）
            if not permit_year or not permit_no:
                stats.skipped += 1
                elem.clear()
                continue

            data = {
                "permit_year": permit_year,
                "permit_no": permit_no,
                "issue_date_text": _txt(_child(elem, "發照日期")),
                "original_permit_no": _txt(_child(elem, "原核發執照")),
                "designer": _txt(_child(elem, "設計人")),
                "supervisor": _txt(_child(elem, "監造人")),
                "contractor": _txt(_child(elem, "承造人")),
                "build_type": _txt(_child(elem, "建造類別")),
                "structure_type": _txt(_child(elem, "構造種類")),
                "zoning": _txt(_child(elem, "使用分區")),
                "building_height_m": parse_decimal_maybe(_txt(_child(elem, "建物高度"))),
                "project_cost_text": _txt(_child(elem, "工程金額")),
                "completion_date_text": _txt(_child(elem, "竣工日期")),
                "start_date_text": _txt(_child(elem, "開工日期")),
                "law_summary": _txt(_child(elem, "適用法令概要")),
                "change_summary_text": _txt(_child(elem, "變更概要")),  # 若是空元素則為空字串
            }

            # 建物資訊
            info = _child(elem, "建物資訊")
            if info is not None:
                def to_int(s: str) -> int | None:
                    s = (s or "").strip()
                    if not s:
                        return None
                    try:
                        return int(s)
                    except ValueError:
                        return None

                data["building_count"] = to_int(_txt(_child(info, "棟數")))
                data["block_count"] = to_int(_txt(_child(info, "幢數")))
                data["floors_above"] = to_int(_txt(_child(info, "地上層數")))
                data["floors_below"] = to_int(_txt(_child(info, "地下層數")))
                data["unit_count"] = to_int(_txt(_child(info, "戶數")))

            # 建物面積
            area = _child(elem, "建物面積")
            if area is not None:
                data["arcade_site_area_sqm"] = parse_decimal_maybe(_txt(_child(area, "騎樓基地面積")))
                data["other_site_area_sqm"] = parse_decimal_maybe(_txt(_child(area, "其他基地面積")))
                data["footprint_area_sqm"] = parse_decimal_maybe(_txt(_child(area, "建築面積")))
                data["legal_open_space_sqm"] = parse_decimal_maybe(_txt(_child(area, "法定空地面積")))
                data["refuge_area_above_sqm"] = parse_decimal_maybe(_txt(_child(area, "地上避難面積")))
                data["refuge_area_below_sqm"] = parse_decimal_maybe(_txt(_child(area, "地下避難面積")))

            # raw（僅備查）
            raw_obj = _element_to_primitive(elem)
            data["raw"] = raw_obj

            # ===== 多值節點收集 =====
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
            summary = _child(elem, "建築概要")
            if summary is not None:
                for f in _children(summary, "樓層"):
                    t = _txt(f)
                    if t:
                        floors.append(t)

            parkings: list[str] = []
            pk = _child(elem, "停車空間")
            if pk is not None:
                for p in _children(pk, "停車空間說明"):
                    t = _txt(p)
                    if t:
                        parkings.append(t)

            notes: list[str] = []
            nt = _child(elem, "注意事項")
            if nt is not None:
                for n in _children(nt, "備註說明"):
                    t = _txt(n)
                    if t:
                        notes.append(t)

            # 雜項工作物（0~1）
            misc_desc = ""
            misc = _child(elem, "雜項工作物")
            if misc is not None:
                misc_desc = _txt(_child(misc, "說明"))

            # 變更概要/核准文號（多筆，取屬性）
            change_approvals: list[tuple[str, str]] = []
            ch = _child(elem, "變更概要")
            if ch is not None:
                for ap in _children(ch, "核准文號"):
                    # 只取實際存在的兩個屬性
                    a1 = (ap.attrib.get("變使准") or "").strip()
                    a2 = (ap.attrib.get("變使竣工") or "").strip()
                    if a1 or a2:
                        change_approvals.append((a1, a2))

            # ===== 寫入 DB =====
            if dry_run:
                stats.created += 1  # dry-run 用 created 計數代表「可寫入」
                elem.clear()
                continue

            with transaction.atomic():
                if upsert:
                    obj, created = BuildingUsePermit.objects.get_or_create(
                        permit_year=permit_year,
                        permit_no=permit_no,
                        defaults=data,
                    )
                    if created:
                        stats.created += 1
                    else:
                        for k, v in data.items():
                            setattr(obj, k, v)
                        obj.save(update_fields=list(data.keys()) + ["updated_at"])
                        stats.updated += 1
                else:
                    obj = BuildingUsePermit.objects.create(**data)
                    stats.created += 1

                # 子表：先刪後建（避免重跑累積）
                obj.addresses.all().delete()
                obj.parcels.all().delete()
                obj.floors.all().delete()
                obj.parkings.all().delete()
                obj.notes.all().delete()
                obj.change_approvals.all().delete()
                # misc_work：OneToOne
                try:
                    obj.misc_work.delete()
                except Exception:
                    pass

                if addresses:
                    BuildingUsePermitAddress.objects.bulk_create([
                        BuildingUsePermitAddress(permit=obj, seq=i + 1, address_text=t)
                        for i, t in enumerate(addresses)
                    ], batch_size=2000)

                if parcels:
                    BuildingUsePermitParcel.objects.bulk_create([
                        BuildingUsePermitParcel(permit=obj, seq=i + 1, parcel_text=t)
                        for i, t in enumerate(parcels)
                    ], batch_size=2000)

                if floors:
                    BuildingUsePermitFloor.objects.bulk_create([
                        BuildingUsePermitFloor(permit=obj, seq=i + 1, floor_text=t)
                        for i, t in enumerate(floors)
                    ], batch_size=2000)

                if parkings:
                    BuildingUsePermitParking.objects.bulk_create([
                        BuildingUsePermitParking(permit=obj, seq=i + 1, parking_text=t)
                        for i, t in enumerate(parkings)
                    ], batch_size=2000)

                if notes:
                    BuildingUsePermitNote.objects.bulk_create([
                        BuildingUsePermitNote(permit=obj, seq=i + 1, note_text=t)
                        for i, t in enumerate(notes)
                    ], batch_size=2000)

                if change_approvals:
                    BuildingUsePermitChangeApproval.objects.bulk_create([
                        BuildingUsePermitChangeApproval(
                            permit=obj, seq=i + 1,
                            change_approval_text=a1,
                            change_completion_text=a2,
                        )
                        for i, (a1, a2) in enumerate(change_approvals)
                    ], batch_size=2000)

                if misc_desc:
                    BuildingUsePermitMiscWork.objects.create(permit=obj, description=misc_desc)

            # 清理 elem 釋放記憶體
            elem.clear()

        self.stdout.write(
            f"完成：processed={stats.processed} created={stats.created} updated={stats.updated} skipped={stats.skipped} dry_run={dry_run}"
        )
