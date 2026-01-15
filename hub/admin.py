from django.contrib import admin
from .models import (
    BuildingPermit,
    BuildingPermitAddress,
    BuildingPermitParcel,
    BuildingPermitFloor,
    BuildingPermitMiscWorkItem,
    BuildingPermitNoteItem,
    WreApproval,
    WrePermitMatch,
    UrbanRenewalCase,
    UrbanRenewalBonus,
)


class BuildingPermitAddressInline(admin.TabularInline):
    model = BuildingPermitAddress
    extra = 0
    fields = ("seq", "address_text")
    readonly_fields = ("seq", "address_text")
    ordering = ("seq",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class BuildingPermitParcelInline(admin.TabularInline):
    model = BuildingPermitParcel
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


class BuildingPermitFloorInline(admin.TabularInline):
    model = BuildingPermitFloor
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


class BuildingPermitMiscWorkItemInline(admin.TabularInline):
    model = BuildingPermitMiscWorkItem
    extra = 0
    fields = ("seq", "misc_text")
    readonly_fields = ("seq", "misc_text")
    ordering = ("seq",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class BuildingPermitNoteItemInline(admin.TabularInline):
    model = BuildingPermitNoteItem
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


@admin.register(BuildingPermit)
class BuildingPermitAdmin(admin.ModelAdmin):
    change_form_template = "admin/hub/buildingpermit/change_form.html"
    
    list_display = (
        "permit_no",
        "permit_year",
        "issue_date",
        "zoning",
        "designer",
        "other_site_area_sqm",
        "building_area_sqm",
        "project_cost",
    )
    search_fields = ("permit_no", "zoning", "designer", "location")
    list_filter = ("permit_year",)

    # === 全部唯讀 ===
    readonly_fields = [f.name for f in BuildingPermit._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if fieldsets is None:
            fieldsets = []
        fieldsets = list(fieldsets)
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
        cleaned.append(("原始資料（系統）", {"classes": ("collapse",), "fields": ("raw",)}))
        return tuple(cleaned)


class UrbanRenewalBonusInline(admin.TabularInline):
    model = UrbanRenewalBonus
    extra = 0
    fields = ("code", "bonus_pct")
    readonly_fields = ("code", "bonus_pct")
    ordering = ("code",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WreApproval)
class WreApprovalAdmin(admin.ModelAdmin):
    change_form_template = "admin/hub/wreapproval/change_form.html"
    
    list_display = ("approve_date","district","section","subsection","parcel_no","site_area_sqm","site_area_ping")
    search_fields = ("district","section","subsection","parcel_no","address")

    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(WrePermitMatch)
class WrePermitMatchAdmin(admin.ModelAdmin):
    list_display = ("match_type","rule_ok","wre","permit","created_at")
    list_filter = ("match_type","rule_ok")
    search_fields = ("wre__district","wre__section","wre__subsection","wre__parcel_no","permit__permit_no")

    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}

@admin.register(UrbanRenewalCase)
class UrbanRenewalCaseAdmin(admin.ModelAdmin):
    change_form_template = "admin/hub/urbanrenewalcase/change_form.html"
    inlines = [UrbanRenewalBonusInline]
    
    list_display = ("case_no","district","approved_date","site_area_sqm","site_area_ping","total_bonus_pct")
    list_filter = ("district",)
    search_fields = ("district","section","subsection","parcel_no","address")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# 隱藏的 models：只為了覆寫 get_model_perms，不在 index 顯示
@admin.register(BuildingPermitAddress)
class BuildingPermitAddressAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}


@admin.register(BuildingPermitParcel)
class BuildingPermitParcelAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}


@admin.register(BuildingPermitFloor)
class BuildingPermitFloorAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}


@admin.register(BuildingPermitMiscWorkItem)
class BuildingPermitMiscWorkItemAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}


@admin.register(BuildingPermitNoteItem)
class BuildingPermitNoteItemAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}


@admin.register(UrbanRenewalBonus)
class UrbanRenewalBonusAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """隱藏此 model，不在 index 顯示"""
        return {}


# 使用執照（Admin 全中文顯示）
from .admin_use_permit import *  # noqa
