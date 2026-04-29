from django.contrib import admin
from .models import (
    Jobber, JobberType, UserExtra, Party, Location, Brand, Catalogue,Client,MainCategory, SubCategory,
    DyeingOtherCharge,TermsCondition, Accessory, ERPNotification
)

@admin.register(JobberType)
class JobberTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__username")
    list_filter = ("owner",)

@admin.register(Jobber)
class JobberAdmin(admin.ModelAdmin):
    list_display = ("name", "jobber_type", "phone", "email", "is_active", "owner")
    search_fields = ("name", "phone", "email", "jobber_type__name", "owner__username")
    list_filter = ("is_active", "jobber_type", "owner")
    ordering = ("name",)

@admin.register(UserExtra)
class UserExtraAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "designation", "department")
    search_fields = ("user__username", "phone", "designation", "department")

@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = (
        "party_code",
        "party_name",
        "party_category",
        "contact_person",
        "phone_number",
        "gst_number",
        "city",
        "is_active",
        "owner",
    )
    search_fields = (
        "party_code",
        "party_name",
        "contact_person",
        "phone_number",
        "alt_phone",
        "email",
        "gst_number",
        "pan_number",
        "city",
        "owner__username",
    )
    list_filter = ("party_category", "is_active", "state", "owner")
    ordering = ("party_name",)
    


admin.site.register(Location)

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_active", "created_at")
    search_fields = ("name", "description", "owner__username")
    list_filter = ("is_active", "owner")
    ordering = ("name",)
    
@admin.register(Catalogue)
class CatalogueAdmin(admin.ModelAdmin):
    list_display = ("name", "wear_type", "owner", "is_active", "created_at")
    search_fields = ("name", "wear_type", "description", "owner__username")
    list_filter = ("is_active", "owner", "wear_type")
    ordering = ("name",)
    

    
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_person", "phone", "email", "city", "is_active", "owner")
    search_fields = ("name", "contact_person", "phone", "email", "gst_number", "pan_number")
    list_filter = ("is_active", "state", "owner")
    ordering = ("name",)

@admin.register(DyeingOtherCharge)
class DyeingOtherChargeAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__username")
    list_filter = ("owner",)

@admin.register(TermsCondition)
class TermsConditionAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "is_active", "created_at")
    search_fields = ("title", "content", "owner__username")
    list_filter = ("is_active", "owner")
    ordering = ("title",)
    
@admin.register(MainCategory)
class MainCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "description", "owner__username")
    list_filter = ("owner",)
    ordering = ("name",)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "main_category", "owner", "created_at")
    search_fields = ("name", "description", "main_category__name", "owner__username")
    list_filter = ("main_category", "owner")
    ordering = ("main_category__name", "name")
    
@admin.register(Accessory)
class AccessoryAdmin(admin.ModelAdmin):
    list_display = ("name", "default_unit", "owner", "created_at")
    search_fields = ("name", "description", "owner__username")
    list_filter = ("owner", "default_unit")
    ordering = ("name",)

@admin.register(ERPNotification)
class ERPNotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "priority", "is_read", "owner", "updated_at")
    search_fields = ("title", "message", "object_key", "owner__username")
    list_filter = ("kind", "priority", "is_read", "owner")
    ordering = ("is_read", "-updated_at")
