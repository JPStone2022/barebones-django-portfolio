# demos/admin.py
from django.contrib import admin
from .models import Demo, DemoSection

class DemoSectionInline(admin.TabularInline): # Or admin.StackedInline
    model = DemoSection
    extra = 1 # Number of empty forms to display
    fields = ('section_order', 'section_title', 'section_content_markdown', 'code_language', 'code_snippet_title', 'code_snippet', 'code_snippet_explanation')
    ordering = ('section_order',)
    classes = ['collapse'] # Make inlines collapsible

@admin.register(Demo)
class DemoAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_published', 'is_featured', 'order', 'last_updated')
    # CORRECTED: Removed 'skills' from list_filter as it's not on the Demo model
    list_filter = ('is_published', 'is_featured', 'last_updated', 'date_created') 
    # CORRECTED: Removed 'skills__name' from search_fields
    search_fields = ('title', 'slug', 'description', 'page_meta_title', 'meta_description') 
    list_editable = ('is_published', 'is_featured', 'order')
    
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'is_published', 'is_featured', 'order')
        }),
        ('Card & Listing Display', {
            'fields': ('description', 'image_url')
        }),
        ('Page Content & SEO', {
            'classes': ('collapse',),
            'fields': ('page_meta_title', 'meta_description', 'meta_keywords')
        }),
        ('Interactive Demo Link', {
            'classes': ('collapse',),
            'fields': ('demo_url_name',)
        }),
         ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('date_created', 'last_updated'),
        }),
    )
    readonly_fields = ('date_created', 'last_updated')

    inlines = [DemoSectionInline]

    # CORRECTED: Removed 'skills' from filter_horizontal.
    # If your Demo model does not have a 'skills' ManyToManyField,
    # filter_horizontal should not reference it.
    # If you have other ManyToManyFields (e.g., 'topics' if you add it to Demo), list them here.
    # Example: filter_horizontal = ('topics',)
    filter_horizontal = () # Empty tuple if no ManyToManyFields on Demo model to display this way

@admin.register(DemoSection)
class DemoSectionAdmin(admin.ModelAdmin):
    list_display = ('demo', 'section_order', 'section_title')
    list_filter = ('demo__title',)
    search_fields = ('section_title', 'section_content_markdown', 'code_snippet')
    autocomplete_fields = ['demo']
    list_select_related = ['demo']

    fieldsets = (
        (None, {
            'fields': ('demo', 'section_order', 'section_title', 'section_content_markdown')
        }),
        ('Code Snippet (Optional)', {
            'classes': ('collapse',),
            'fields': ('code_language', 'code_snippet_title', 'code_snippet', 'code_snippet_explanation')
        }),
    )
