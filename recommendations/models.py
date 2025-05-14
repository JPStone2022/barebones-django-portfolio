# recommendations/models.py
from django.db import models
from django.utils.text import slugify
from django.urls import reverse

class RecommendedProduct(models.Model):
    """ Represents a recommended product (book, tool, course, etc.), populated from CSVs. """
    name = models.CharField(max_length=200, help_text="Name of the product (from summary CSV 'name').")
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=False, # Slug is mandatory
        null=False,
        help_text="URL-friendly identifier (from CSV 'reco_slug'). Must be unique."
    )
    short_description = models.TextField(
        blank=True,
        null=True,
        help_text="Brief description for card views (from summary CSV 'short_description')."
    )
    main_description_md = models.TextField(
        blank=True,
        null=True,
        help_text="Main descriptive content in Markdown (from content CSV 'main_description_md'). Used if no sections."
    )
    product_url = models.URLField(
        max_length=500,
        help_text="Link to the product (from summary CSV 'product_url')."
    )
    image_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL for the product image (from summary CSV 'image_url')."
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional category (e.g., Book, Course, Software, Hardware) (from summary CSV 'category')."
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which to display products (from summary CSV 'order')."
    )

    # SEO and Page Metadata (from content CSV)
    page_meta_title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="SEO Title for the recommendation's detail page (from content CSV 'page_meta_title'). Falls back to name."
    )
    page_meta_description = models.TextField(
        blank=True,
        null=True,
        help_text="SEO Meta Description for the detail page (from content CSV 'page_meta_description'). Falls back to short_description."
    )
    page_meta_keywords = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="SEO Meta Keywords for the detail page (comma-separated) (from content CSV 'page_meta_keywords')."
    )

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name'] # Default ordering

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """ Returns the URL to access a detail page for this recommendation. """
        return reverse('recommendations:recommendation_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        """
        Auto-generate or validate slug if not provided and ensure its uniqueness.
        The population script should ideally provide the slug from 'reco_slug'.
        This save method ensures slugs are always valid and unique if created/edited via admin.
        """
        if not self.slug: # If slug is somehow empty, generate from name
            base_slug = slugify(self.name)
        else: # Ensure provided slug is properly slugified
            base_slug = slugify(self.slug)

        candidate_slug = base_slug
        counter = 1
        # Check for uniqueness, excluding self if this is an update
        qs = RecommendedProduct.objects.filter(slug=candidate_slug)
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        while qs.exists():
            candidate_slug = f"{base_slug}-{counter}"
            counter += 1
            qs = RecommendedProduct.objects.filter(slug=candidate_slug) # Re-check with new candidate
            if self.pk: # Ensure to keep excluding self in loop
                qs = qs.exclude(pk=self.pk)

        self.slug = candidate_slug
        super().save(*args, **kwargs)


class RecommendationSection(models.Model):
    """ Represents a content section for a detailed recommendation page. """
    recommendation = models.ForeignKey(
        RecommendedProduct,
        related_name='sections',
        on_delete=models.CASCADE,
        help_text="The recommended product this section belongs to."
    )
    section_order = models.FloatField(
        default=1.0,
        help_text="Order of this section within the recommendation page (e.g., 1, 1.1, 2)."
    )
    section_title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Title of this section (optional)."
    )
    section_content_markdown = models.TextField(
        blank=True,
        null=True,
        help_text="Main content of the section in Markdown format."
    )
    # Add other fields if sections can have code snippets, images, etc.
    # For simplicity, starting with title and markdown content.

    class Meta:
        ordering = ['recommendation', 'section_order']
        unique_together = ('recommendation', 'section_order') # Ensure section_order is unique per recommendation

    def __str__(self):
        return f"{self.recommendation.name} - Section {self.section_order} ({self.section_title or 'Untitled'})"
