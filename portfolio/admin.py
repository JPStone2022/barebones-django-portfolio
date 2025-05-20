# portfolio/admin.py

from django.contrib import admin
# Import models from this app
from .models import Project, Certificate, UserProfile, ColophonEntry
# Import models from other apps that might be related or managed here
from topics.models import ProjectTopic # Assuming Project model has a ForeignKey or ManyToMany to ProjectTopic

# Import Skill model safely for ProjectAdmin filter_horizontal
try:
    from skills.models import Skill
    SKILL_MODEL_EXISTS = True
except ImportError:
    Skill = None # Define Skill as None if it cannot be imported
    SKILL_MODEL_EXISTS = False

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface options for the UserProfile model.
    """
    list_display = ('full_name', 'site_identifier', 'email', 'tagline')
    search_fields = ('full_name', 'email', 'tagline')

    # Since UserProfile is intended as a singleton (only one instance),
    # customize the admin to prevent adding new ones if 'main_profile' exists.
    def has_add_permission(self, request):
        # Allow adding if no UserProfile instance with site_identifier="main_profile" exists yet.
        if UserProfile.objects.filter(site_identifier="main_profile").exists():
            return False # Prevent adding new ones if 'main_profile' exists
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the 'main_profile' instance.
        if obj is not None and obj.site_identifier == "main_profile":
            return False
        return super().has_delete_permission(request, obj)

    fieldsets = (
        ("Basic Information", {
            'fields': ('full_name', 'tagline', 'location', 'email', 'phone_number')
        }),
        ("Biography & Appearance", {
            'fields': ('short_bio_html', 'about_me_markdown', 'profile_picture_url')
        }),
        ("Links & CV", {
            # If you added cv_file to your UserProfile model, include 'cv_file' here
            'fields': ('linkedin_url', 'github_url', 'personal_website_url', 'cv_url') 
        }),
        ("SEO Defaults", {
            'fields': ('default_meta_description', 'default_meta_keywords'),
            'classes': ('collapse',), 
        }),
        # 'site_identifier' is editable=False in the model, so it won't show by default
        # unless added to readonly_fields or a fieldset. It's usually managed internally.
    )
    # If you want to see site_identifier in the admin form (but not edit it because model has editable=False):
    # readonly_fields = ('site_identifier',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'order', 'is_featured') # Added for better overview
    list_filter = ('is_featured', 'topics', 'skills')
    search_fields = ('title', 'description', 'slug', 'skills__name', 'topics__name') # Added slug and topics__name
    list_editable = ('order', 'is_featured') # Added is_featured
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'image_url', 'is_featured') # Added is_featured
        }),
        ('Topics & Skills', {
            'fields': ('topics', 'skills')
        }),
        ('Project Content & Outcomes', { # Renamed for clarity
            'classes': ('collapse',),
            'fields': ('long_description_markdown', 'results_metrics', 'challenges', 'lessons_learned') # Added long_description_markdown
        }),
        ('Code Snippet', {
            'classes': ('collapse',),
            'fields': ('code_snippet', 'code_language')
        }),
        ('Links', {
            'fields': ('github_url', 'demo_url', 'paper_url')
        }),
        ('Ordering & Timestamps', { # Renamed for clarity
            'fields': ('order',),
            'classes': ('collapse',) 
        }),
    )
    #readonly_fields = ('created_at', 'updated_at') # Make timestamps read-only

    # Adjust filter_horizontal based on whether Skill model was successfully imported
    if SKILL_MODEL_EXISTS:
        filter_horizontal = ('skills', 'topics',)
    else:
        filter_horizontal = ('topics',)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('title', 'issuer', 'date_issued', 'order', 'certificate_file')
    list_filter = ('issuer', 'date_issued')
    search_fields = ('title', 'issuer')
    list_editable = ('order',)
    # Updated fields to include is_featured and potentially logo_image if you add it to the model
    fields = ('title', 'issuer', 'date_issued', 'certificate_file', 'logo_image') 
    # If you add a logo_image field to Certificate model:
    # fields = ('title', 'issuer', 'date_issued', 'credential_url', 'certificate_file', 'logo_image', 'is_featured', 'order')


@admin.register(ColophonEntry)
class ColophonEntryAdmin(admin.ModelAdmin):
    """
    Admin interface options for the ColophonEntry model.
    """
    list_display = ('name', 'category', 'order', 'url')
    list_filter = ('category',)
    search_fields = ('name', 'description')
    list_editable = ('order',) # Allows editing 'order' directly in the list view
    ordering = ('category', 'order', 'name') # Default sorting in the admin view
    fields = ('name', 'category', 'description', 'url', 'icon_class', 'order') # Explicit field order in edit form

