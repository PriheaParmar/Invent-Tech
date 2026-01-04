from django.contrib import admin
from .models import Jobber, JobberType, UserExtra

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
