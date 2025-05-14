# demos/models.py
from django.db import models
from django.urls import reverse, NoReverseMatch
from django.utils.text import slugify
from django.utils import timezone # Ensure timezone is imported
import logging

logger = logging.getLogger(__name__)

class Demo(models.Model):
    """ 
    Represents an informational demo page, primarily populated from a CSV,
    but can also be managed via Admin.
    """
    title = models.CharField(max_length=200, help_text="The main display title of the demo page.")
    slug = models.SlugField(
        max_length=220, 
        unique=True, 
        blank=False, 
        null=False, 
        help_text="URL-friendly identifier. Must be unique. Auto-generated if left blank in admin."
    )
    
    # Page-level metadata
    page_meta_title = models.CharField(max_length=255, blank=True, null=True, help_text="SEO Title for the page.")
    meta_description = models.TextField(blank=True, null=True, help_text="SEO Meta Description for the page.")
    meta_keywords = models.CharField(max_length=255, blank=True, null=True, help_text="SEO Meta Keywords for the page (comma-separated).")

    # Card/Listing specific fields
    description = models.TextField(blank=True, null=True, help_text="Short description for display on cards or listings.")
    image_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL for a preview image for the demo card.")
    
    # Control fields
    is_published = models.BooleanField(default=True, help_text="Whether this demo is publicly visible.")
    is_featured = models.BooleanField(default=False, help_text="Whether this demo should be highlighted as featured.")
    order = models.PositiveIntegerField(default=0, help_text="Display order for listings (lower numbers show first).")

    # Specific URL for interactive demos (if not using generic page)
    demo_url_name = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Optional: Django URL name for a specific interactive demo view (e.g., 'demos:image_classifier')."
    )

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title'] # Default ordering

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """
        Returns the URL to access this demo.
        Prioritizes specific demo_url_name if provided and valid,
        otherwise falls back to the generic detail page.
        """
        if self.demo_url_name:
            try:
                return reverse(self.demo_url_name)
            except NoReverseMatch:
                logger.warning(
                    f"Demo '{self.title}' (slug: {self.slug}) has an invalid demo_url_name "
                    f"'{self.demo_url_name}'. Falling back to generic detail page."
                )
        # Fallback to generic detail page using its slug
        return reverse('demos:generic_demo_detail', kwargs={'demo_slug': self.slug})

    def save(self, *args, **kwargs):
        """
        Auto-generate slug if one doesn't exist or if it's empty, 
        and ensure its uniqueness.
        """
        if not self.slug: # Only generate if slug is empty
            base_slug = slugify(self.title)
            candidate_slug = base_slug
            counter = 1
            # Check for uniqueness, excluding self if updating
            qs_check = Demo.objects.all()
            if self.pk:
                qs_check = qs_check.exclude(pk=self.pk)
            
            while qs_check.filter(slug=candidate_slug).exists():
                candidate_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = candidate_slug
        super().save(*args, **kwargs)


class DemoSection(models.Model):
    """ Represents a content section within a Demo page, populated from CSV or Admin. """
    demo = models.ForeignKey(Demo, related_name='sections', on_delete=models.CASCADE, help_text="The demo this section belongs to.")
    section_order = models.FloatField(default=1.0, help_text="Order of this section within the demo page (e.g., 1, 1.1, 2).")
    section_title = models.CharField(max_length=255, blank=True, null=True, help_text="Title of this section (optional).")
    section_content_markdown = models.TextField(blank=True, null=True, help_text="Main content of the section in Markdown format.")
    
    code_language = models.CharField(max_length=50, blank=True, null=True, help_text="Programming language of the code snippet (e.g., python, html).")
    code_snippet_title = models.CharField(max_length=255, blank=True, null=True, help_text="Title for the code snippet block (optional).")
    code_snippet = models.TextField(blank=True, null=True, help_text="The code snippet itself.")
    code_snippet_explanation = models.TextField(blank=True, null=True, help_text="Explanation for the code snippet or its output.")

    class Meta:
        ordering = ['demo', 'section_order'] 
        unique_together = ('demo', 'section_order') 

    def __str__(self):
        title_part = f" ({self.section_title})" if self.section_title else " (Untitled)"
        return f"{self.demo.title} - Section {self.section_order}{title_part}"

