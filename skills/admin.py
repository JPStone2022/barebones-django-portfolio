# skills/admin.py

from django.contrib import admin
from .models import Skill, SkillCategory

@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'order')
    list_filter = ('category',)
    search_fields = ('name', 'description')
    list_editable = ('category', 'order')
    prepopulated_fields = {'slug': ('name',)}
    # Optional: Define fields for edit view if needed
    # fields = ('name', 'slug', 'category', 'description', 'order')