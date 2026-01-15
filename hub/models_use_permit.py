# hub/models_use_permit.py
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re

from django.db import models


_DEC_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def parse_decimal_maybe(s: str | None) -> Decimal | None:
    """
    安全解析 Decimal：
    - 允許字串帶雜字（例如 '199.45㎡' / '3.15M'），只取第一段數字
    - 解析失敗回 None（不猜、不硬塞 0）
    """
    if not s:
        return None
    m = _DEC_RE.search(str(s).strip())
    if not m:
        return None
    try:
        return Decimal(m.group(0))
    except InvalidOperation:
        return None


class BuildingUsePermit(models.Model):
    """
    使用執照（主表）
    來源：臺北市使用執照 XML，每筆 <Data> 對應一筆
    """

    permit_year = models.CharField("執照年度", max_length=16)
    permit_no = models.CharField("執照號碼", max_length=64)

    issue_date_text = models.CharField("發照日期", max_length=32, blank=True, default="")
    original_permit_no = models.CharField("原核發執照", max_length=256, blank=True, default="")

    designer = models.CharField("設計人", max_length=256, blank=True, default="")
    supervisor = models.CharField("監造人", max_length=256, blank=True, default="")
    contractor = models.CharField("承造人", max_length=256, blank=True, default="")

    build_type = models.CharField("建造類別", max_length=128, blank=True, default="")
    structure_type = models.CharField("構造種類", max_length=128, blank=True, default="")
    zoning = models.CharField("使用分區", max_length=256, blank=True, default="")

    building_count = models.IntegerField("棟數", null=True, blank=True)
    block_count = models.IntegerField("幢數", null=True, blank=True)  # XML 內確實存在「幢數」
    floors_above = models.IntegerField("地上層數", null=True, blank=True)
    floors_below = models.IntegerField("地下層數", null=True, blank=True)
    unit_count = models.IntegerField("戶數", null=True, blank=True)

    arcade_site_area_sqm = models.DecimalField("騎樓基地面積（㎡）", max_digits=18, decimal_places=4, null=True, blank=True)
    other_site_area_sqm = models.DecimalField("其他基地面積（㎡）", max_digits=18, decimal_places=4, null=True, blank=True)
    footprint_area_sqm = models.DecimalField("建築面積（㎡）", max_digits=18, decimal_places=4, null=True, blank=True)
    legal_open_space_sqm = models.DecimalField("法定空地面積（㎡）", max_digits=18, decimal_places=4, null=True, blank=True)
    refuge_area_above_sqm = models.DecimalField("地上避難面積（㎡）", max_digits=18, decimal_places=4, null=True, blank=True)
    refuge_area_below_sqm = models.DecimalField("地下避難面積（㎡）", max_digits=18, decimal_places=4, null=True, blank=True)

    building_height_m = models.DecimalField("建物高度（m）", max_digits=18, decimal_places=4, null=True, blank=True)

    project_cost_text = models.CharField("工程金額", max_length=64, blank=True, default="")
    completion_date_text = models.CharField("竣工日期", max_length=32, blank=True, default="")
    start_date_text = models.CharField("開工日期", max_length=32, blank=True, default="")

    law_summary = models.TextField("適用法令概要", blank=True, default="")
    change_summary_text = models.TextField("變更概要", blank=True, default="")

    raw = models.JSONField("原始資料（僅備查）", default=dict, blank=True)

    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True)

    class Meta:
        verbose_name = "使用執照"
        verbose_name_plural = "使用執照"
        constraints = [
            models.UniqueConstraint(fields=["permit_year", "permit_no"], name="uq_use_permit_year_no"),
        ]
        indexes = [
            models.Index(fields=["permit_year", "permit_no"]),
        ]

    def __str__(self) -> str:
        return f"{self.permit_year}-{self.permit_no}"


class BuildingUsePermitAddress(models.Model):
    permit = models.ForeignKey(BuildingUsePermit, on_delete=models.CASCADE, related_name="addresses", verbose_name="使用執照")
    seq = models.IntegerField("序號")
    address_text = models.CharField("地址", max_length=512)

    created_at = models.DateTimeField("建立時間", auto_now_add=True)

    class Meta:
        verbose_name = "建築地點"
        verbose_name_plural = "建築地點"
        ordering = ["seq"]
        indexes = [models.Index(fields=["permit", "seq"])]

    def __str__(self) -> str:
        return self.address_text


class BuildingUsePermitParcel(models.Model):
    permit = models.ForeignKey(BuildingUsePermit, on_delete=models.CASCADE, related_name="parcels", verbose_name="使用執照")
    seq = models.IntegerField("序號")
    parcel_text = models.CharField("地段號（原文）", max_length=256)

    created_at = models.DateTimeField("建立時間", auto_now_add=True)

    class Meta:
        verbose_name = "地段地號"
        verbose_name_plural = "地段地號"
        ordering = ["seq"]
        indexes = [models.Index(fields=["permit", "seq"])]

    def __str__(self) -> str:
        return self.parcel_text


class BuildingUsePermitFloor(models.Model):
    permit = models.ForeignKey(BuildingUsePermit, on_delete=models.CASCADE, related_name="floors", verbose_name="使用執照")
    seq = models.IntegerField("序號")
    floor_text = models.TextField("樓層（原文）")

    created_at = models.DateTimeField("建立時間", auto_now_add=True)

    class Meta:
        verbose_name = "建築概要"
        verbose_name_plural = "建築概要"
        ordering = ["seq"]
        indexes = [models.Index(fields=["permit", "seq"])]

    def __str__(self) -> str:
        return f"{self.seq}: {self.floor_text[:30]}"


class BuildingUsePermitParking(models.Model):
    permit = models.ForeignKey(BuildingUsePermit, on_delete=models.CASCADE, related_name="parkings", verbose_name="使用執照")
    seq = models.IntegerField("序號")
    parking_text = models.TextField("停車空間說明（原文）")

    created_at = models.DateTimeField("建立時間", auto_now_add=True)

    class Meta:
        verbose_name = "停車空間"
        verbose_name_plural = "停車空間"
        ordering = ["seq"]
        indexes = [models.Index(fields=["permit", "seq"])]

    def __str__(self) -> str:
        return f"{self.seq}: {self.parking_text[:30]}"


class BuildingUsePermitNote(models.Model):
    permit = models.ForeignKey(BuildingUsePermit, on_delete=models.CASCADE, related_name="notes", verbose_name="使用執照")
    seq = models.IntegerField("序號")
    note_text = models.TextField("備註說明")

    created_at = models.DateTimeField("建立時間", auto_now_add=True)

    class Meta:
        verbose_name = "注意事項"
        verbose_name_plural = "注意事項"
        ordering = ["seq"]
        indexes = [models.Index(fields=["permit", "seq"])]

    def __str__(self) -> str:
        return f"{self.seq}: {self.note_text[:30]}"


class BuildingUsePermitMiscWork(models.Model):
    permit = models.OneToOneField(BuildingUsePermit, on_delete=models.CASCADE, related_name="misc_work", verbose_name="使用執照")
    description = models.TextField("雜項工作物說明", blank=True, default="")

    created_at = models.DateTimeField("建立時間", auto_now_add=True)

    class Meta:
        verbose_name = "雜項工作物"
        verbose_name_plural = "雜項工作物"

    def __str__(self) -> str:
        return f"{self.permit}"


class BuildingUsePermitChangeApproval(models.Model):
    """
    變更概要 / 核准文號（XML：<核准文號 變使准="..." 變使竣工="..." />）
    """
    permit = models.ForeignKey(BuildingUsePermit, on_delete=models.CASCADE, related_name="change_approvals", verbose_name="使用執照")
    seq = models.IntegerField("序號")

    change_approval_text = models.CharField("變使准（原文）", max_length=128, blank=True, default="")
    change_completion_text = models.CharField("變使竣工（原文）", max_length=128, blank=True, default="")

    created_at = models.DateTimeField("建立時間", auto_now_add=True)

    class Meta:
        verbose_name = "變更核准文號"
        verbose_name_plural = "變更核准文號"
        ordering = ["seq"]
        indexes = [models.Index(fields=["permit", "seq"])]

    def __str__(self) -> str:
        return f"{self.permit} #{self.seq}"
