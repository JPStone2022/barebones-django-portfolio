# blog/admin.py

from django.contrib import admin
from .models import BlogPost

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'status', 'published_date', 'created_date')
    list_filter = ('status', 'created_date', 'published_date')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    # Optional: Define fields shown in edit view if needed
    # fields = ('title', 'slug', 'content', 'published_date', 'status')