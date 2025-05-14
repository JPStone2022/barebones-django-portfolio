# blog/sitemaps.py

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import BlogPost
from django.utils import timezone

class BlogStaticSitemap(Sitemap):
    """ Sitemap for the main blog list page. """
    priority = 0.7
    changefreq = 'daily'

    def items(self):
        return ['blog:blog_post_list'] # URL name for the blog list view

    def location(self, item):
        return reverse(item)

class BlogPostSitemap(Sitemap):
    """ Sitemap for individual blog post detail pages. """
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # Return only published posts
        return BlogPost.objects.filter(status='published', published_date__lte=timezone.now())

    def lastmod(self, obj):
        # Use the published date as the last modification date
        return obj.published_date

    # location method is implicitly handled by get_absolute_url if defined
    # Otherwise define it:
    # def location(self, obj):
    #     return reverse('blog:blog_post_detail', kwargs={'slug': obj.slug})

