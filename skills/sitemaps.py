# skills/sitemaps.py

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Skill # Assuming Skill model exists

class SkillsStaticSitemap(Sitemap):
    """ Sitemap for the main skills list page. """
    priority = 0.6
    changefreq = 'monthly'

    def items(self):
        return ['skills:skill_list'] # URL name for the skills list view

    def location(self, item):
        return reverse(item)

class SkillSitemap(Sitemap):
    """ Sitemap for individual skill detail pages. """
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        # Return a queryset of all Skill objects
        return Skill.objects.all()

    # location method is implicitly handled by get_absolute_url on the Skill model
    # If get_absolute_url is not defined, define location(self, obj):
    # def location(self, obj):
    #     return reverse('skills:skill_detail', kwargs={'slug': obj.slug})

    # Optional: Add lastmod if your Skill model has an update timestamp
    # def lastmod(self, obj):
    #     return obj.updated_date

