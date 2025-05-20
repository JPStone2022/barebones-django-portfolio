# recommendations/admin.py
from django.contrib import admin
from .models import RecommendedProduct, RecommendationSection

class RecommendationSectionInline(admin.TabularInline): # Or admin.StackedInline
    model = RecommendationSection
    extra = 1 # Number of empty forms to display
    fields = ('section_order', 'section_title', 'section_content_markdown')
    ordering = ('section_order',)

@admin.register(RecommendedProduct)
class RecommendedProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'order', 'product_url', 'last_updated')
    list_filter = ('category',)
    search_fields = ('name', 'short_description', 'main_description_md', 'category')
    list_editable = ('order', 'category')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'product_url', 'image_url', 'order')
        }),
        ('Card Display Content', {
            'fields': ('short_description',),
        }),
        ('Detail Page Content (Main/Fallback)', {
            'classes': ('collapse',), # Collapsible section
            'fields': ('main_description_md',),
        }),
        ('SEO & Page Metadata', {
            'classes': ('collapse',),
            'fields': ('page_meta_title', 'page_meta_description', 'page_meta_keywords'),
        }),
    )
    prepopulated_fields = {'slug': ('name',)}
    inlines = [RecommendationSectionInline] # Add sections inline

@admin.register(RecommendationSection)
class RecommendationSectionAdmin(admin.ModelAdmin):
    list_display = ('recommendation', 'section_order', 'section_title')
    list_filter = ('recommendation__category', 'recommendation__name') # Filter by recommendation's category or name
    search_fields = ('section_title', 'section_content_markdown')
    autocomplete_fields = ['recommendation'] # For easier selection of the parent recommendation
