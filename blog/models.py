# blog/models.py
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse

class BlogPost(models.Model):
    """
    Represents a single blog post.
    """
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True, help_text="URL-friendly version of the title (auto-generated).")
    # Optional: Link to author (if you have user accounts)
    # author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blog_posts')
    content = models.TextField(help_text="The main content of the blog post (can use Markdown or HTML).")
    published_date = models.DateTimeField(default=timezone.now, help_text="The date and time the post was published.")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='published')

    class Meta:
        ordering = ['-published_date'] # Order by most recent first

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """
        Returns the URL to access a detail page for this blog post.
        """
        return reverse('blog:blog_post_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        """
        Auto-generate slug if one doesn't exist, and ensure its uniqueness.
        """
        # Determine the base slug: if a slug is provided, use it; otherwise, generate from title.
        # This ensures that even if a slug is provided, it's checked for uniqueness.
        if not self.slug:
            base_slug = slugify(self.title)
        else:
            # If a slug is provided, ensure it's properly slugified (e.g. no spaces, correct case)
            # and use that as the base. However, for the test case, we assume the provided slug is already "correct".
            # If the provided slug might not be in a valid slug format, you might want to slugify it here:
            # base_slug = slugify(self.slug) 
            # But typically, if a user provides a slug, they expect it to be used as-is if possible.
            # For this fix, we'll use the self.slug as the base if it's provided.
            base_slug = slugify(self.slug)


        # Ensure the slug is unique
        candidate_slug = base_slug
        counter = 1
        
        # Build the queryset for checking conflicts.
        # For new objects (self.pk is None), exclude(pk=self.pk) does nothing.
        # For existing objects being updated, it excludes itself from the uniqueness check.
        while BlogPost.objects.filter(slug=candidate_slug).exclude(pk=self.pk).exists():
            # If the candidate_slug conflicts, generate a new one by appending the counter
            # to the original base_slug.
            candidate_slug = f"{base_slug}-{counter}"
            counter += 1
        
        self.slug = candidate_slug # Set the final, unique slug
        super().save(*args, **kwargs)
