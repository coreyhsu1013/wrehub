# hub/admin_use_permit.py
from __future__ import annotations

from django.contrib import admin

from hub.models_use_permit import (
    BuildingUsePermit,
    BuildingUsePermitAddress,
    BuildingUsePermitParcel,
    BuildingUsePermitFloor,
    BuildingUsePermitParking,
    BuildingUsePermitNote,
    BuildingUsePermitMiscWork,
    BuildingUsePermitChangeApproval,
)


class AddressInline(admin.TabularInline):
    model = BuildingUsePermitAddress
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in BuildingUsePermitAddress._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ParcelInline(admin.TabularInline):
    model = BuildingUsePermitParcel
    extra = 0
    fields = ("seq", "parcel_text")
    readonly_fields = ("seq", "parcel_text")
    ordering = ("seq",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class FloorInline(admin.TabularInline):
    model = BuildingUsePermitFloor
    extra = 0
    fields = ("seq", "floor_text")
    readonly_fields = ("seq", "floor_text")
    ordering = ("seq",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ParkingInline(admin.TabularInline):
    model = BuildingUsePermitParking
    extra = 0
    fields = ("seq", "parking_text")
    readonly_fields = ("seq", "parking_text")
    ordering = ("seq",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class NoteInline(admin.TabularInline):
    model = BuildingUsePermitNote
    extra = 0
    fields = ("seq", "note_text")
    readonly_fields = ("seq", "note_text")
    ordering = ("seq",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ChangeApprovalInline(admin.TabularInline):
    model = BuildingUsePermitChangeApproval
    extra = 0
    fields = ("seq", "change_approval_text", "change_completion_text")
    readonly_fields = ("seq", "change_approval_text", "change_completion_text")
    ordering = ("seq",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BuildingUsePermit)
class BuildingUsePermitAdmin(admin.ModelAdmin):
    change_form_template = "admin/hub/buildingusepermit/change_form.html"
    
    list_display = (
        "permit_no",
        "permit_year",
        "issue_date_text",
        "zoning",
        "designer",
    )
    search_fields = ("permit_no", "zoning", "designer")
    list_filter = ("permit_year",)

    # === 全部唯讀 ===
    readonly_fields = [f.name for f in BuildingUsePermit._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_fieldsets(self, request, obj=None):
        # 先讓 Django 自動決定「所有欄位」的呈現
        fieldsets = super().get_fieldsets(request, obj)
        if fieldsets is None:
            fieldsets = []
        fieldsets = list(fieldsets)
        # 移除任何包含 raw 的區塊（避免 raw 出現在中間）
        cleaned = []
        for name, opts in fieldsets:
            fields = list(opts.get("fields") or ())
            if "raw" in fields:
                fields = [f for f in fields if f != "raw"]
                if fields:
                    new_opts = dict(opts)
                    new_opts["fields"] = tuple(fields)
                    cleaned.append((name, new_opts))
            else:
                cleaned.append((name, opts))
        # 把 raw 放到最後並收合
        cleaned.append(("原始資料（系統）", {"classes": ("collapse",), "fields": ("raw",)}))
        return tuple(cleaned)


@admin.register(BuildingUsePermitMiscWork)
class BuildingUsePermitMiscWorkAdmin(admin.ModelAdmin):
    list_display = ("permit", "created_at")
    search_fields = ("permit__permit_year", "permit__permit_no", "description")
    readonly_fields = ("permit", "description", "created_at")

    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# 隱藏的 models：只為了覆寫 get_model_perms，不在 index 顯示
@admin.register(BuildingUsePermitAddress)
class BuildingUsePermitAddressAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}


@admin.register(BuildingUsePermitParcel)
class BuildingUsePermitParcelAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}


@admin.register(BuildingUsePermitFloor)
class BuildingUsePermitFloorAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}


@admin.register(BuildingUsePermitParking)
class BuildingUsePermitParkingAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}


@admin.register(BuildingUsePermitNote)
class BuildingUsePermitNoteAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}


@admin.register(BuildingUsePermitChangeApproval)
class BuildingUsePermitChangeApprovalAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}
