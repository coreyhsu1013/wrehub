from __future__ import annotations
from django.db import models


class BuildingPermit(models.Model):
    permit_year = models.CharField(max_length=10, blank=True, default="")
    permit_no = models.CharField(max_length=64, unique=True)  # 執照號碼
    issue_date = models.DateField(null=True, blank=True)      # 發照日期

    district = models.CharField(max_length=32, blank=True, default="")   # 行政區
    section = models.CharField(max_length=64, blank=True, default="")    # 地段
    subsection = models.CharField(max_length=64, blank=True, default="") # 小段
    parcel_no = models.CharField(max_length=32, blank=True, default="")  # 地號 ####-0000

    build_type = models.CharField(max_length=32, blank=True, default="")
    structure = models.CharField(max_length=128, blank=True, default="")
    zoning = models.CharField(max_length=128, blank=True, default="")

    location = models.CharField(max_length=256, blank=True, default="")
    land_text = models.TextField(blank=True, default="")
    building_info = models.TextField(blank=True, default="")
    summary = models.TextField(blank=True, default="")

    building_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    arcade_site_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    other_site_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    building_count = models.IntegerField("棟數", null=True, blank=True)
    block_count = models.IntegerField("幢數", null=True, blank=True)
    floors_above = models.IntegerField("地上層數", null=True, blank=True)
    floors_below = models.IntegerField("地下層數", null=True, blank=True)
    unit_count = models.IntegerField("戶數", null=True, blank=True)

    build_deadline = models.CharField(max_length=64, blank=True, default="")
    project_cost = models.BigIntegerField(null=True, blank=True)

    owner = models.CharField(max_length=256, blank=True, default="")
    designer = models.CharField(max_length=256, blank=True, default="")
    supervisor = models.CharField(max_length=256, blank=True, default="")

    misc_works = models.TextField(blank=True, default="")
    applicable_law = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "建築執照"
        verbose_name_plural = "建築執照"
        indexes = [
            models.Index(fields=["district", "section", "subsection"]),
            models.Index(fields=["district", "section"]),
            models.Index(fields=["designer"]),
            models.Index(fields=["zoning"]),
        ]

    def __str__(self) -> str:
        return self.permit_no


class BuildingPermitAddress(models.Model):
    permit = models.ForeignKey(BuildingPermit, on_delete=models.CASCADE, related_name="addresses", verbose_name="建築執照")
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


class BuildingPermitParcel(models.Model):
    permit = models.ForeignKey(BuildingPermit, on_delete=models.CASCADE, related_name="parcels", verbose_name="建築執照")
    seq = models.IntegerField("序號")
    parcel_text = models.CharField("地段地號（原文）", max_length=256)

    created_at = models.DateTimeField("建立時間", auto_now_add=True)

    class Meta:
        verbose_name = "地段地號"
        verbose_name_plural = "地段地號"
        ordering = ["seq"]
        indexes = [models.Index(fields=["permit", "seq"])]

    def __str__(self) -> str:
        return self.parcel_text


class BuildingPermitFloor(models.Model):
    permit = models.ForeignKey(BuildingPermit, on_delete=models.CASCADE, related_name="floors", verbose_name="建築執照")
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


class BuildingPermitMiscWorkItem(models.Model):
    permit = models.ForeignKey(BuildingPermit, on_delete=models.CASCADE, related_name="misc_items", verbose_name="建築執照")
    seq = models.IntegerField("序號")
    misc_text = models.TextField("雜項工作物說明（原文）")

    created_at = models.DateTimeField("建立時間", auto_now_add=True)

    class Meta:
        verbose_name = "雜項工作物"
        verbose_name_plural = "雜項工作物"
        ordering = ["seq"]
        indexes = [models.Index(fields=["permit", "seq"])]

    def __str__(self) -> str:
        return f"{self.seq}: {self.misc_text[:30]}"


class BuildingPermitNoteItem(models.Model):
    permit = models.ForeignKey(BuildingPermit, on_delete=models.CASCADE, related_name="note_items", verbose_name="建築執照")
    seq = models.IntegerField("序號")
    note_text = models.TextField("備註說明（原文）")

    created_at = models.DateTimeField("建立時間", auto_now_add=True)

    class Meta:
        verbose_name = "注意事項"
        verbose_name_plural = "注意事項"
        ordering = ["seq"]
        indexes = [models.Index(fields=["permit", "seq"])]

    def __str__(self) -> str:
        return f"{self.seq}: {self.note_text[:30]}"


class UsePermit(models.Model):
    permit_year = models.CharField(max_length=10, blank=True, default="")
    permit_no = models.CharField(max_length=64, unique=True)  # 使用執照號碼
    issue_date = models.DateField(null=True, blank=True)      # 核發/發照日期（以實際 XML 欄位為準）

    district = models.CharField(max_length=32, blank=True, default="")
    section = models.CharField(max_length=64, blank=True, default="")
    subsection = models.CharField(max_length=64, blank=True, default="")
    parcel_no = models.CharField(max_length=64, blank=True, default="")  # 可能是地號/地段地號（很多資料會缺）

    build_type = models.CharField(max_length=64, blank=True, default="")     # 新建/增建/變更使用等（若 XML 有）
    structure = models.CharField(max_length=256, blank=True, default="")
    zoning = models.CharField(max_length=256, blank=True, default="")

    location = models.CharField(max_length=256, blank=True, default="")
    owner = models.CharField(max_length=256, blank=True, default="")
    designer = models.CharField(max_length=256, blank=True, default="")
    supervisor = models.CharField(max_length=256, blank=True, default="")

    building_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    other_site_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    notes = models.TextField(blank=True, default="")
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "使用執照"
        verbose_name_plural = "使用執照"
        indexes = [
            models.Index(fields=["permit_year"]),
            models.Index(fields=["district", "section", "subsection"]),
            models.Index(fields=["designer"]),
        ]

    def __str__(self) -> str:
        return self.permit_no


class WreApproval(models.Model):
    approve_date = models.DateField(null=True, blank=True)
    district = models.CharField(max_length=32, blank=True, default="")
    section = models.CharField(max_length=64, blank=True, default="")
    subsection = models.CharField(max_length=64, blank=True, default="")
    parcel_no = models.CharField(max_length=32, blank=True, default="")  # ####-0000
    address = models.CharField(max_length=256, blank=True, default="")

    site_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    site_area_ping = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "危老核准資料"
        verbose_name_plural = "危老核准資料"
        indexes = [
            models.Index(fields=["district", "section", "subsection", "parcel_no"]),
            models.Index(fields=["approve_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.district} {self.section}{self.subsection} {self.parcel_no}"


class WrePermitMatch(models.Model):
    MATCH_EXACT = "exact"
    MATCH_MULTI = "multi_parcel"
    MATCH_TYPES = [(MATCH_EXACT, "Exact"), (MATCH_MULTI, "Multi-parcel")]

    wre = models.ForeignKey(WreApproval, on_delete=models.CASCADE)
    permit = models.ForeignKey(BuildingPermit, on_delete=models.CASCADE)

    match_type = models.CharField(max_length=32, choices=MATCH_TYPES)
    rule_ok = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "危老對照結果"
        verbose_name_plural = "危老對照結果"
        unique_together = [("wre", "permit", "match_type")]
        indexes = [
            models.Index(fields=["match_type", "rule_ok"]),
        ]


class UrbanRenewalCase(models.Model):
    """
    危老核准案件（一案一列）
    """
    source = models.CharField(max_length=32, default="taipei_ur")
    case_no = models.IntegerField(null=True, blank=True)  # 案件數（序號）
    total_bonus_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    district = models.CharField(max_length=32, blank=True, default="")
    section = models.CharField(max_length=64, blank=True, default="")
    subsection = models.CharField(max_length=64, blank=True, default="")
    parcel_no = models.CharField(max_length=32, blank=True, default="")
    address = models.CharField(max_length=256, blank=True, default="")

    approved_date = models.DateField(null=True, blank=True)

    site_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    site_area_ping = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "危老案件"
        verbose_name_plural = "危老案件"
        indexes = [
            models.Index(fields=["district", "section", "subsection"]),
            models.Index(fields=["approved_date"]),
        ]

    def __str__(self):
        return f"{self.district} {self.section}{self.subsection} {self.parcel_no}"


class UrbanRenewalBonus(models.Model):
    """
    危老獎勵明細（一案多筆）
    """
    BONUS_CODES = [
        ("structure", "結構評估"),
        ("seismic", "耐震設計"),
        ("green", "綠建築"),
        ("smart", "智慧建築"),
        ("barrierfree", "無障礙"),
        ("donation", "捐贈公設"),
        ("schedule", "時程獎勵"),
        ("scale", "規模獎勵"),
        ("other", "其他"),
    ]

    case = models.ForeignKey(
        UrbanRenewalCase,
        on_delete=models.CASCADE,
        related_name="bonuses",
    )

    code = models.CharField(max_length=32, choices=BONUS_CODES)
    bonus_pct = models.DecimalField(max_digits=6, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "危老獎勵明細"
        verbose_name_plural = "危老獎勵明細"
        unique_together = [("case", "code")]
        indexes = [
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.case_id} {self.code} {self.bonus_pct}%"


# 使用執照（獨立資料結構）
from .models_use_permit import *  # noqa
