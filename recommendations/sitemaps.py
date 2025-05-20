# recommendations/sitemaps.py

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import RecommendedProduct # Import your RecommendedProduct model

class RecommendationStaticViewSitemap(Sitemap):
    """ Sitemap for static list views in the recommendations app. """
    priority = 0.7  # Adjust priority as needed
    changefreq = 'weekly' # How often the list page might change

    def items(self):
        # Return a list of URL names for your recommendations app's static views
        return ['recommendations:recommendation_list']

    def location(self, item):
        # Return the URL for each item (view name)
        return reverse(item)

class RecommendedProductSitemap(Sitemap):
    """ Sitemap for individual Recommended Product detail pages. """
    changefreq = "monthly"  # Or 'weekly' if you update them often
    priority = 0.6          # Adjust priority as needed

    def items(self):
        # Return a queryset of all RecommendedProduct objects
        # You might want to add a filter here if you have a way to mark
        # recommendations as "published" or "active"
        return RecommendedProduct.objects.all()

    def lastmod(self, obj):
        # RecommendedProduct model has 'last_updated'
        return obj.last_updated

    # The location method will be implicitly handled because your
    # RecommendedProduct model has a get_absolute_url() method.
    # If it didn't, you would define it like this:
    # def location(self, obj):
    #     return reverse('recommendations:recommendation_detail', kwargs={'slug': obj.slug})

