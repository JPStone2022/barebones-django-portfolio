# topics/sitemaps.py

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import ProjectTopic

class TopicListSitemap(Sitemap):
    """ Sitemap for the main topic list page. """
    priority = 0.6
    changefreq = 'monthly'

    def items(self):
        # Return the URL name for the topic list view
        return ['topics:topic_list']

    def location(self, item):
        return reverse(item)

class TopicSitemap(Sitemap):
    """ Sitemap for individual topic detail pages. """
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        # Return a queryset of all ProjectTopic objects
        return ProjectTopic.objects.all()

    # location is handled by get_absolute_url on the ProjectTopic model

    # Optional: Add lastmod if your Topic model has an update timestamp
    # def lastmod(self, obj):
    #     return obj.updated_date

