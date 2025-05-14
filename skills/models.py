# skills/models.py

from django.db import models
from django.utils.text import slugify
from django.urls import reverse

class SkillCategory(models.Model):
    """ Optional: Category for grouping skills """
    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Skill Categories" # Correct plural in admin

    def __str__(self):
        return self.name

class Skill(models.Model):
    """ Represents a single technical skill. """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="URL-friendly version of the name (auto-generated).")
    description = models.TextField(blank=True, help_text="Detailed description of the skill and your experience.")
    category = models.ForeignKey(
        SkillCategory,
        on_delete=models.SET_NULL, # Keep skill even if category is deleted
        null=True,
        blank=True,
        related_name='skills' # How to access skills from category
    )
    # Optional: Add fields for proficiency level, icon URL/upload, etc.
    # proficiency = models.CharField(max_length=50, blank=True, help_text="e.g., Expert, Intermediate, Basic")
    # icon_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0, help_text="Order within category.")

    class Meta:
        ordering = ['category__order', 'category__name', 'order', 'name'] # Order by category, then skill order

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """ Returns the URL to access a detail record for this skill. """
        return reverse('skills:skill_detail', kwargs={'slug': self.slug})

    # def save(self, *args, **kwargs):
    #     """ Auto-generate slug. """
    #     if not self.slug:
    #         self.slug = slugify(self.name)
    #         # Ensure slug uniqueness
    #         original_slug = self.slug
    #         counter = 1
    #         while Skill.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
    #             self.slug = f'{original_slug}-{counter}'
    #             counter += 1
    #     super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        """
        Auto-generate slug if not provided or ensure provided slug is slugified.
        Ensures slug uniqueness.
        """
        if self.slug: # If a slug is provided, ensure it's in the correct format
            self.slug = slugify(self.slug)
        else: # Otherwise, generate from name
            self.slug = slugify(self.name)

        # Ensure slug uniqueness
        original_slug = self.slug
        counter = 1
        # Check for other instances with the same slug
        # Exclude self.pk to allow updating an instance without triggering uniqueness conflict with itself
        queryset = Skill.objects.filter(slug=self.slug)
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        while queryset.exists():
            self.slug = f'{original_slug}-{counter}'
            counter += 1
            queryset = Skill.objects.filter(slug=self.slug) # Re-check with new slug
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

        super().save(*args, **kwargs)