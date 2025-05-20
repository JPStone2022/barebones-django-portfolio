# portfolio/models.py

from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
import logging # Import logging

logger = logging.getLogger(__name__) # Define logger at module level


# Import Skill model safely
try:
    from skills.models import Skill
except ImportError:
    Skill = None

# Import ProjectTopic model safely
try:
    from topics.models import ProjectTopic # Corrected import path
except ImportError:
    ProjectTopic = None


class Project(models.Model):
    """ Represents a single project in the portfolio. """
    title = models.CharField(max_length=200, help_text="The title of the project.")
    slug = models.SlugField(max_length=250, unique=True, blank=True, help_text="URL-friendly version of the title (auto-generated if blank).")
    description = models.TextField(help_text="A detailed description of the project.")
    image_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL for the project's main image or GIF.")
    results_metrics = models.TextField(blank=True, help_text="Specific results, metrics, or outcomes achieved.")
    challenges = models.TextField(blank=True, help_text="Key challenges faced during the project.")
    lessons_learned = models.TextField(blank=True, help_text="Important takeaways or lessons learned.")
    code_snippet = models.TextField(blank=True, help_text="An interesting code snippet related to the project.")
    code_language = models.CharField(max_length=50, blank=True, default='python', help_text="Language for syntax highlighting of the code snippet.")
    # Add this new field:
    long_description_markdown = models.TextField(
        blank=True, # Allows the field to be empty
        null=True,  # Allows the database to store NULL if empty
        help_text="Detailed project description in Markdown for the project detail page."
    )
    # ManyToManyField for Skills (conditionally added)
    if Skill:
        skills = models.ManyToManyField(Skill, blank=True, related_name='projects')
    
    # ManyToManyField for ProjectTopics (conditionally added)
    if ProjectTopic:
        topics = models.ManyToManyField(ProjectTopic, blank=True, related_name='projects') # related_name='projects' is conventional

    # Deprecated field - to be removed after migration
    technologies = models.CharField(max_length=300, blank=True, help_text="DEPRECATED: Use Skills field instead. Comma-separated list of technologies used.")
    
    # Links
    github_url = models.URLField(max_length=300, blank=True, null=True, help_text="Link to the project's GitHub repository.")
    demo_url = models.URLField(max_length=300, blank=True, null=True, help_text="Link to a live demo of the project.")
    paper_url = models.URLField(max_length=300, blank=True, null=True, help_text="Link to a research paper or article about the project.")
    is_featured = models.BooleanField(default=False, help_text="determine if project is loaded on the home page")

    # Ordering and Timestamps

    order = models.PositiveIntegerField(default=0, help_text="Order for display (lower numbers show first).")
    date_created = models.DateField(default=timezone.now, help_text="The date the project was created or started.")
    # last_updated = models.DateTimeField(auto_now=True) # Optional: if you want to track updates

    class Meta:
        ordering = ['order', '-date_created'] # Default ordering

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('portfolio:project_detail', kwargs={'slug': self.slug})

    def get_technologies_list(self):
        """ Returns a list of technologies. Prioritizes Skills, falls back to deprecated field. """
        if Skill and self.skills.exists():
            return [skill.name for skill in self.skills.all()]
        if self.technologies:
            logger.warning(f"Project '{self.title}' using deprecated 'technologies' field. Please migrate to Skills.")
            return [tech.strip() for tech in self.technologies.split(',') if tech.strip()]
        return []

    def save(self, *args, **kwargs):
        """
        Auto-generate slug if one doesn't exist or if it's empty,
        and ensure its uniqueness. If a slug is provided, it will be used
        as the base (and slugified if not already).
        """
        # Determine the base slug
        if not self.slug:  # If slug is empty or None
            base_slug = slugify(self.title)
        else:
            # FIX: If a slug is provided, use it but ensure it's properly slugified
            base_slug = slugify(self.slug)

        candidate_slug = base_slug
        counter = 1
        
        # Build the queryset for checking conflicts.
        qs_check = Project.objects.all()
        if self.pk: # If updating an existing instance, exclude itself
            qs_check = qs_check.exclude(pk=self.pk)
            
        while qs_check.filter(slug=candidate_slug).exists():
            candidate_slug = f"{base_slug}-{counter}"
            counter += 1
        
        self.slug = candidate_slug
        super().save(*args, **kwargs)

# --- Certificate Model ---
class Certificate(models.Model):
    title = models.CharField(max_length=250)
    issuer = models.CharField(max_length=150)
    date_issued = models.DateField(blank=True, null=True)
    certificate_file = models.FileField(upload_to='certificate_files/', blank=True, null=True)
    logo_image = models.ImageField(
        upload_to='certificate_logos/', 
        blank=True,
        null=True,
        help_text="Upload a logo image for the issuer or certificate (optional)."
    )    
    order = models.PositiveIntegerField(default=0, help_text="Order for display (e.g., 0 for most recent/important).")

    class Meta:
        ordering = ['order', '-date_issued']

    def __str__(self):
        return f"{self.title} - {self.issuer}"

class UserProfile(models.Model):
    # Basic Info
    full_name = models.CharField(max_length=100, default="Julian Stone")
    tagline = models.CharField(max_length=255, blank=True, help_text="e.g., Web Developer & Data Science Enthusiast")
    location = models.CharField(max_length=100, blank=True, help_text="e.g., Stoke-on-Trent, England")
    email = models.EmailField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True) # E.164 format recommended if used programmatically
    
    # Bio & About
    short_bio_html = models.TextField(blank=True, help_text="Short introduction for homepage (can include HTML).")
    about_me_markdown = models.TextField(blank=True, help_text="Longer 'About Me' content in Markdown for the about page.")
    profile_picture_url = models.URLField(max_length=255, blank=True, null=True, help_text="URL to your profile picture.")

    # Social & Professional Links
    linkedin_url = models.URLField(max_length=255, blank=True)
    github_url = models.URLField(max_length=255, blank=True)
    personal_website_url = models.URLField(max_length=255, blank=True, help_text="If different from this portfolio.")
    cv_url = models.URLField(max_length=255, blank=True, null=True, help_text="Direct link to your CV PDF if hosted online.")
    # Alternatively, for CV file upload:
    # cv_file = models.FileField(upload_to='cv/', blank=True, null=True, help_text="Upload your CV PDF.")

    # Meta for SEO (can be overridden by page-specific meta)
    default_meta_description = models.CharField(max_length=160, blank=True)
    default_meta_keywords = models.CharField(max_length=255, blank=True, help_text="Comma-separated keywords.")

    # Singleton pattern: Ensure only one instance exists
    # This is a simple way to enforce it.
    # More robust solutions might involve django-solo or custom save methods.
    site_identifier = models.CharField(max_length=50, default="main_profile", unique=True, editable=False)

    # --- NEW Fields for Page Content ---
    # About Me Page Content
    about_me_intro_markdown = models.TextField(
        blank=True, null=True,
        help_text="Introduction paragraph for the About Me page (Markdown format)."
    )
    about_me_journey_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the 'My Journey & Experience' section (Markdown format)."
    )
    about_me_expertise_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the 'Areas of Expertise' section (Markdown format)."
    )
    about_me_philosophy_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the 'Philosophy & Approach' section (Markdown format)."
    )
    about_me_beyond_work_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the 'Beyond Work' section (Markdown format)."
    )

    # Hire Me Page Content
    hire_me_intro_markdown = models.TextField(
        blank=True, null=True,
        help_text="Introduction paragraph for the Hire Me page (Markdown format)."
    )
    hire_me_seeking_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the 'What I'm Seeking' section (Markdown format)."
    )
    hire_me_strengths_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the 'My Key Strengths' section (Markdown format)."
    )
    hire_me_availability_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the 'Current Availability' section (Markdown format)."
    )

    # *** NEW: Index Page - Skills Overview Content ***
    skills_overview_ml_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the 'Deep Learning & ML Libraries' card on the index page (Markdown list format)."
    )
    skills_overview_datasci_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the 'Python & Data Science' card on the index page (Markdown list format)."
    )
    skills_overview_general_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the 'General IT & Other Skills' card on the index page (Markdown list format)."
    )

    # --- NEW: Index Page - Skills Overview Titles (Plain Text) ---
    skills_overview_ml_title = models.CharField(
        max_length=100, blank=True, null=True,
        default="Deep Learning & ML Libraries",
        help_text="Title for the 'Deep Learning & ML Libraries' card on the index page."
    )
    skills_overview_datasci_title = models.CharField(
        max_length=100, blank=True, null=True,
        default="Python & Data Science",
        help_text="Title for the 'Python & Data Science' card on the index page."
    )
    skills_overview_general_title = models.CharField(
        max_length=100, blank=True, null=True,
        default="General IT & Other Skills",
        help_text="Title for the 'General IT & Other Skills' card on the index page."
    )
    about_me_introduction = models.CharField(
        max_length=100, blank=True, null=True,
        default="I am a machine learning engineer.",
        help_text="Short introduction about me"
    )
    about_me_details = models.CharField(
        max_length=100, blank=True, null=True,
        default="I am passionate about leveraging my background in Python and a suite of Data Science tools.",
        help_text="Going into more detail about me."
    )    
    # --- END NEW Skill Titles ---

    # --- NEW Legal/Policy Page Content ---
    privacy_policy_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the Privacy Policy page (Markdown format)."
    )
    terms_conditions_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the Terms & Conditions page (Markdown format)."
    )
    accessibility_statement_markdown = models.TextField(
        blank=True, null=True,
        help_text="Content for the Accessibility Statement page (Markdown format)."
    )

# --- End NEW Fields ---

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name}'s Profile"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

class ColophonEntry(models.Model):
    """
    Model to store entries for the "How This Site Was Built" (Colophon) page.
    Each entry represents a technology, tool, service, or resource used.
    """
    CATEGORY_CHOICES = [
        ('backend', 'Backend Technologies'),
        ('frontend', 'Frontend Technologies'),
        ('database', 'Database'),
        ('deployment', 'Deployment & Hosting'),
        ('devops', 'DevOps & Tools'),
        ('design', 'Design & Assets'),
        ('learning', 'Key Learning Resources'),
        ('inspiration', 'Inspiration & APIs'),
    ]
    name = models.CharField(max_length=100, help_text="Name of the technology, tool, or resource.")
    category = models.CharField(
        max_length=20,  # Max length of the longest key in CATEGORY_CHOICES
        choices=CATEGORY_CHOICES,
        help_text="Category for grouping."
    )
    description = models.TextField(blank=True, help_text="Briefly why/how it's used or what you learned.")
    url = models.URLField(blank=True, null=True, help_text="Link to the official website or resource.")
    # MODIFIED: Added null=True to allow this field to be empty in the database
    icon_class = models.CharField(
        max_length=50,
        blank=True,
        null=True, # Allow NULL values in the database
        help_text="Optional: Font Awesome class or similar for an icon (e.g., 'fab fa-python')."
    )
    order = models.PositiveIntegerField(default=0, help_text="Order within its category for display.")

    class Meta:
        ordering = ['category', 'order', 'name'] # Default ordering
        verbose_name = "Colophon Entry"
        verbose_name_plural = "Colophon Entries"

    def __str__(self):
        return self.name
