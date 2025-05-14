# demos/sitemaps.py

from django.contrib.sitemaps import Sitemap
from django.urls import reverse, NoReverseMatch
import pandas as pd
import os
from django.conf import settings
import logging 

logger = logging.getLogger(__name__) 

# --- Path to your demos_summary.csv ---
# Ensure this path is correct for your project structure
DEMOS_SUMMARY_CSV_PATH = os.path.join(settings.BASE_DIR, 'data_import', '07a_demos_summary.csv')

try:
    from .models import Demo
    DEMO_MODEL_EXISTS = True
except ImportError:
    logger.info("Sitemap: .models.Demo not found. DemoModelSitemap will be skipped or return empty.")
    DEMO_MODEL_EXISTS = False
    Demo = None # Define Demo as None to prevent NameErrors later

class DemoModelSitemap(Sitemap):
    """
    Sitemap for individual demo pages managed via a Django 'Demo' model.
    """
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        if DEMO_MODEL_EXISTS and Demo is not None:
            try:
                return Demo.objects.filter(is_published=True)
            except Exception as e:
                logger.error(f"Sitemap: Error querying Demo model items: {e}", exc_info=True)
                return []
        return []

    def lastmod(self, obj):
        """Returns the last modified date for a Demo object."""
        if hasattr(obj, 'last_updated') and obj.last_updated:
            return obj.last_updated
        elif hasattr(obj, 'date_created'): 
            return obj.date_created
        return None


class CSVDemoPagesSitemap(Sitemap):
    """
    Sitemap for demo pages defined in a CSV file, which use the generic_demo_detail view.
    """
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        items_list = []
        if not os.path.exists(DEMOS_SUMMARY_CSV_PATH):
            logger.warning(f"Sitemap: CSV summary file not found at {DEMOS_SUMMARY_CSV_PATH}")
            return items_list
        
        try:
            # Check for empty file before attempting to read
            if os.path.getsize(DEMOS_SUMMARY_CSV_PATH) == 0:
                logger.warning(f"Sitemap: CSV summary file is empty at {DEMOS_SUMMARY_CSV_PATH}")
                return items_list
            
            df = pd.read_csv(DEMOS_SUMMARY_CSV_PATH)

            # Ensure df is a DataFrame before proceeding
            if not isinstance(df, pd.DataFrame):
                logger.error(f"Sitemap: Failed to read {DEMOS_SUMMARY_CSV_PATH} as a DataFrame.")
                return items_list

            # The CSV is expected to have a 'demo_slug' column based on your models/admin
            slug_column_name = 'demo_slug' # Or 'slug' if that's the actual column name in CSV

            if slug_column_name not in df.columns:
                logger.warning(f"Sitemap: '{slug_column_name}' column not found in {DEMOS_SUMMARY_CSV_PATH}. Available columns are: {df.columns.tolist() if isinstance(df, pd.DataFrame) else 'N/A'}")
                return items_list

            slugs = df[slug_column_name].dropna().unique()
            for slug_val in slugs:
                if slug_val and isinstance(slug_val, str) and slug_val.strip():
                    # Only add if a corresponding published Demo object exists
                    if DEMO_MODEL_EXISTS and Demo and Demo.objects.filter(slug=slug_val.strip(), is_published=True).exists():
                        items_list.append({'slug': slug_val.strip()})
                    # If Demo model isn't used/available, this sitemap might not be appropriate
                    # or would need a different logic to determine valid items.
                    # For now, it strictly ties CSV entries to existing, published Demo objects.

        except pd.errors.EmptyDataError:
            logger.warning(f"Sitemap: CSV file {DEMOS_SUMMARY_CSV_PATH} is empty (pandas EmptyDataError).")
        except Exception as e:
            logger.error(f"Sitemap: Error reading or processing CSV {DEMOS_SUMMARY_CSV_PATH}: {e}", exc_info=True)
        return items_list

    def location(self, item_dict):
        slug = item_dict.get('slug')
        if not slug:
            return ''
        
        # This sitemap is for pages backed by Demo model entries.
        # Ensure the Demo object exists and is published before generating a URL.
        if DEMO_MODEL_EXISTS and Demo:
            if Demo.objects.filter(slug=slug, is_published=True).exists():
                try:
                    return reverse('demos:generic_demo_detail', kwargs={'demo_slug': slug})
                except NoReverseMatch:
                    logger.error(f"Sitemap: NoReverseMatch for generic_demo_detail with slug '{slug}'.")
                    return ''
            else:
                # If no published Demo object with this slug, it shouldn't be in the sitemap.
                # The items() method should have already filtered this out.
                return '' 
        else:
            # Fallback if Demo model isn't available (should ideally not happen if items() filters correctly)
            # This path is less likely to be hit if items() is strict.
            try:
                return reverse('demos:generic_demo_detail', kwargs={'demo_slug': slug})
            except NoReverseMatch:
                logger.error(f"Sitemap: NoReverseMatch for generic_demo_detail with slug '{slug}' (Demo model not checked/available).")
                return ''


class HardcodedDemoViewsSitemap(Sitemap):
    """
    Sitemap for demo pages that have dedicated views and URL patterns.
    """
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        # List only URL names that are GUARANTEED to exist in demos/urls.py
        return [
            'demos:image_classifier',
            'demos:sentiment_analyzer',
            'demos:data_analyser', 
            'demos:data_wrangler',
            'demos:explainable_ai',
            'demos:causal_inference',
            'demos:optimization_demo',
            'demos:keras_nmt_demo',
            # Removed 'demos:flask_api_demo' and other potentially non-existent URLs
            # Add other *active* and *defined* hardcoded demo URL names here.
        ]

    def location(self, item_url_name):
        try:
            return reverse(item_url_name)
        except NoReverseMatch: 
            logger.error(f"Sitemap: NoReverseMatch for hardcoded demo URL name '{item_url_name}'. Please check demos/urls.py and sitemap items.", exc_info=True)
            return ''

class MainDemosPageSitemap(Sitemap):
    """
    Sitemap for the main '/demos/' listing page.
    """
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ['demos:all_demos_list']

    def location(self, item):
        return reverse(item)
