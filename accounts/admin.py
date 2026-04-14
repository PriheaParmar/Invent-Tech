from django.contrib import admin
from .models import (
    Jobber, JobberType, UserExtra, Party, Location, Brand, Catalogue,Client,MainCategory, SubCategory,
    BOM, BOMMaterialItem, BOMJobberItem, BOMProcessItem, BOMExpenseItem,DyeingOtherCharge,TermsCondition
)

@admin.register(JobberType)
class JobberTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__username")
    list_filter = ("owner",)

@admin.register(Jobber)
class JobberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "jobber_type", "phone", "email", "is_active", "owner")
    search_fields = ("name", "phone", "email", "jobber_type__name", "owner__username")
    list_filter = ("is_active", "role", "jobber_type", "owner")
    ordering = ("name",)

@admin.register(UserExtra)
class UserExtraAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "designation", "department")
    search_fields = ("user__username", "phone", "designation", "department")

@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ("id", "party_name", "phone_number", "gst_number", "state", "created_at")
    search_fields = ("party_name", "phone_number", "gst_number", "pan_number", "email")
    


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
    

class BOMMaterialInline(admin.TabularInline):
    model = BOMMaterialItem
    extra = 0


class BOMJobberInline(admin.TabularInline):
    model = BOMJobberItem
    extra = 0


class BOMProcessInline(admin.TabularInline):
    model = BOMProcessItem
    extra = 0


class BOMExpenseInline(admin.TabularInline):
    model = BOMExpenseItem
    extra = 0


@admin.register(BOM)
class BOMAdmin(admin.ModelAdmin):
    list_display = (
        "bom_code",
        "sku_code",
        "product_name",
        "brand",
        "category",
        "available_stock",
        "booked_price",
    "selling_price",
        "owner",
    )
    search_fields = ("bom_code", "sku_code", "product_name", "catalogue_name")
    list_filter = ("owner", "is_discontinued", "gender", "size_type")
    inlines = [BOMMaterialInline, BOMJobberInline, BOMProcessInline, BOMExpenseInline]
    
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