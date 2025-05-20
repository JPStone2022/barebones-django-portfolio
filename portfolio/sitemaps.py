# portfolio/sitemaps.py

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Project

class StaticViewSitemap(Sitemap):
    """ Sitemap for static pages in the portfolio app. """
    priority = 0.8  # Priority relative to other pages (0.0 to 1.0)
    changefreq = 'weekly' # How often content might change ('always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never')

    def items(self):
        # Return a list of URL names for your static views
        return [
            'portfolio:index', 'portfolio:all_projects', 'portfolio:certificates',
            'portfolio:contact', 'portfolio:about_me', 'portfolio:cv',
            'portfolio:hire_me', 'portfolio:privacy_policy', 'portfolio:colophon',
            'portfolio:accessibility', 'portfolio:terms'
        ]        
        #return ['portfolio:index', 'portfolio:all_projects', 'portfolio:certificates',
        #        'portfolio:contact', 'portfolio:about_me', 'portfolio:cv']

    def location(self, item):
        # Return the URL for each item (view name)
        return reverse(item)

class ProjectSitemap(Sitemap):
    """ Sitemap for individual project detail pages. """
    changefreq = "monthly"
    priority = 0.9

    def items(self):
        # Return a queryset of all Project objects
        return Project.objects.all()

    def lastmod(self, obj):
        # Optional: Return the last modified date for the object
        # You might need an 'updated_date' field on your Project model
        # return obj.updated_date
        return obj.date_created # Use creation date as fallback

    # location method is implicitly handled by get_absolute_url on the Project model
    # If get_absolute_url is not defined, you need to define location(self, obj):
    # def location(self, obj):
    #     return reverse('portfolio:project_detail', kwargs={'slug': obj.slug})

