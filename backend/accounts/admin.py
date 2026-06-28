from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("__str__", "email", "locale", "theme", "created_at")
    search_fields = ("email", "display_name", "supabase_uid")
