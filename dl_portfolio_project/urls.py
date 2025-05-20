# dl_portfolio_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# Import sitemaps view and your sitemap classes
from django.contrib.sitemaps.views import sitemap

# from demos.sitemaps import DemoModelSitemap, CSVDemoPagesSitemap
# Import TemplateView for robots.txt
from django.views.generic import TemplateView


# --- Sitemap Imports ---
# It's generally better to let ImportErrors propagate if a sitemap is critical,
# or handle them more explicitly if they are optional.

StaticViewSitemap, ProjectSitemap = None, None
try:
    from portfolio.sitemaps import StaticViewSitemap, ProjectSitemap
except ImportError as e:
    print(f"Warning: Could not import portfolio sitemaps: {e}")

BlogStaticSitemap, BlogPostSitemap = None, None
try:
    from blog.sitemaps import BlogStaticSitemap, BlogPostSitemap
except ImportError as e:
    print(f"Warning: Could not import blog sitemaps: {e}")

SkillsStaticSitemap, SkillSitemap = None, None
try:
    from skills.sitemaps import SkillsStaticSitemap, SkillSitemap
except ImportError as e:
    print(f"Warning: Could not import skills sitemaps: {e}")

DemoModelSitemap, CSVDemoPagesSitemap_class = None, None # Renamed to avoid confusion if it's a class
try:
    from demos.sitemaps import DemoModelSitemap, CSVDemoPagesSitemap as CSVDemoPagesSitemap_class # Import the class
except ImportError as e:
    print(f"Warning: Could not import demos sitemaps: {e}")

TopicListSitemap, TopicSitemap = None, None
try:
    from topics.sitemaps import TopicListSitemap, TopicSitemap
except ImportError as e:
    print(f"Warning: Could not import topics sitemaps: {e}")

RecommendationStaticViewSitemap, RecommendedProductSitemap = None, None
try:
    from recommendations.sitemaps import RecommendationStaticViewSitemap, RecommendedProductSitemap # New imports
except ImportError as e:
    print(f"Warning: Could not import recommendations sitemaps: {e}")

# --- End Sitemap Imports ---

sitemaps = {}
if StaticViewSitemap: sitemaps['static'] = StaticViewSitemap
if ProjectSitemap: sitemaps['projects'] = ProjectSitemap
if BlogStaticSitemap: sitemaps['blogstatic'] = BlogStaticSitemap
if BlogPostSitemap: sitemaps['blogposts'] = BlogPostSitemap
if SkillsStaticSitemap: sitemaps['skillsstatic'] = SkillsStaticSitemap
if SkillSitemap: sitemaps['skills'] = SkillSitemap
if DemoModelSitemap: sitemaps['demos'] = DemoModelSitemap
if CSVDemoPagesSitemap_class: # Check if the class was imported
    sitemaps['demos_csv'] = CSVDemoPagesSitemap_class # Add your CSV sitemap, ensure key is unique
if TopicListSitemap: sitemaps['topiclist'] = TopicListSitemap # Add topic list sitemap
if TopicSitemap: sitemaps['topics'] = TopicSitemap # Add topic detail sitemap
if RecommendationStaticViewSitemap: sitemaps['recommendations-static'] = RecommendationStaticViewSitemap
if RecommendedProductSitemap: sitemaps['recommendations-products'] = RecommendedProductSitemap


urlpatterns = [
    path('admin/', admin.site.urls),
    path('blog/', include('blog.urls', namespace='blog')),
    path('skills/', include('skills.urls', namespace='skills')),
    path('recommendations/', include('recommendations.urls', namespace='recommendations')), # Include recommendations URLs
    path('demos/', include('demos.urls', namespace='demos')), # Include demos URLs
    path('topics/', include('topics.urls', namespace='topics')), # Include topics URLs
    path('accounts/', include('django.contrib.auth.urls')), # Standard auth URLs

    # Include URLs from your new 'accounts' app for custom views like a members page
    path('accounts/', include('accounts.urls')), # Custom account views
    
    # Add the sitemap URL pattern
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
            name='django.contrib.sitemaps.views.sitemap'),

    # Add the robots.txt URL pattern using TemplateView
    path(
        'robots.txt',
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain")
    ),

    # Keep portfolio URLs at the root (should be last for catch-all)
    path('', include('portfolio.urls')),
]

# Media file serving for development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

