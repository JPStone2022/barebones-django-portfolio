# topics/admin.py

from django.contrib import admin
from .models import ProjectTopic

@admin.register(ProjectTopic)
class ProjectTopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)
    prepopulated_fields = {'slug': ('name',)} # Auto-fill slug from name
    search_fields = ('name', 'description')
    fields = ('name', 'slug', 'description', 'order') # Fields in edit view

