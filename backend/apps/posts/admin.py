from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "is_published", "is_pinned", "event_at", "published_at")
    list_filter = ("type", "is_published", "is_pinned")
    search_fields = ("title", "body")
