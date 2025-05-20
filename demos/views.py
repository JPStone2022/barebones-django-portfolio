# demos/views.py

import os
import io # For handling dataframe info in memory
import uuid # For unique filenames
import base64
from django.shortcuts import render, get_object_or_404, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.urls import reverse # Import reverse for generating URLs
from .forms import ImageUploadForm, SentimentAnalysisForm, CSVUploadForm, ExplainableAIDemoForm, AmazonProductURLForm, FlightDealFinderForm
import numpy as np
# Import Demo model
from .models import Demo
import logging # Import logging

#import csv # For processing uploaded CSVs in upload_demo_data_view

import requests
from bs4 import BeautifulSoup
# import smtplib # Not sending actual emails in the demo
from datetime import datetime, timedelta # For Flight Deal Finder (simulated dates)
import random # For Flight Deal Finder (simulated dates)

logger = logging.getLogger(__name__) # Define logger at module level

# --- TensorFlow / Keras Imports (for Image Classification) ---
try:
    import tensorflow as tf
    from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions
    from tensorflow.keras.preprocessing import image as keras_image_utils
    
    TF_AVAILABLE = True
    try:
        # Load model only if needed for the image demo
        # Consider lazy loading if memory is a concern
        image_model = MobileNetV2(weights='imagenet')
        IMAGE_MODEL_LOADED = True
        logger.info("MobileNetV2 model loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading MobileNetV2 model: {e}", exc_info=True)
        IMAGE_MODEL_LOADED = False
        image_model = None # Define as None on error
except ImportError:
    logger.warning("TensorFlow not found. Image Classification demo disabled.")
    TF_AVAILABLE = False
    IMAGE_MODEL_LOADED = False
    image_model = None # Define as None if TF not available
    # Define dummy classes/functions if TF not available to prevent NameErrors later if needed
    class keras_image_utils: # Dummy class
        @staticmethod
        def load_img(*args, **kwargs): raise ImportError("TensorFlow not available")
        @staticmethod
        def img_to_array(*args, **kwargs): raise ImportError("TensorFlow not available")


# --- Hugging Face Transformers Imports (for Sentiment Analysis) ---
sentiment_pipeline = None # Initialize as None at module level
SENTIMENT_MODEL_LOADED = False
TRANSFORMERS_AVAILABLE = False
try:
    # Use pipeline for easy sentiment analysis
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
    try:
        # Load pipeline once on startup (or use caching/lazy loading)
        # Using a distilled version for potentially faster/smaller footprint
        sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
        SENTIMENT_MODEL_LOADED = True
        logger.info("Sentiment analysis pipeline loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading sentiment analysis pipeline: {e}", exc_info=True)
        # sentiment_pipeline remains None
        SENTIMENT_MODEL_LOADED = False
except ImportError:
    logger.warning("Transformers library not found. Sentiment Analysis demo disabled.")
    # sentiment_pipeline remains None
    TRANSFORMERS_AVAILABLE = False
    SENTIMENT_MODEL_LOADED = False

#####

# --- Pandas / Matplotlib / Seaborn Imports ---
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import matplotlib # Use Agg backend for non-interactive plotting
    matplotlib.use('Agg')
    DATA_LIBS_AVAILABLE = True
except ImportError:
    logger.warning("Pandas, Matplotlib, or Seaborn not found. Data Analysis/Wrangling demos disabled.")
    DATA_LIBS_AVAILABLE = False

# --- Scikit-learn Imports (for XAI Demo) ---
try:
    from sklearn.datasets import load_iris
    from sklearn.tree import DecisionTreeClassifier, export_text
    from sklearn import tree # For plotting if needed later
    SKLEARN_AVAILABLE = True
    # Load Iris data and train a simple tree ONCE on startup
    # In production, load a pre-saved model instead.
    try:
        iris = load_iris()
        X_iris, y_iris = iris.data, iris.target
        # Train a simple Decision Tree
        decision_tree_model = DecisionTreeClassifier(max_depth=3, random_state=42) # Limit depth for simplicity
        decision_tree_model.fit(X_iris, y_iris)
        TREE_MODEL_LOADED = True
        logger.info("Decision Tree model trained successfully.")
    except Exception as e:
        logger.error(f"Error loading Iris data or training Decision Tree: {e}", exc_info=True)
        TREE_MODEL_LOADED = False
        decision_tree_model = None
        iris = None

except ImportError:
    logger.warning("Scikit-learn not found. Explainable AI demo disabled.")
    SKLEARN_AVAILABLE = False
    TREE_MODEL_LOADED = False
    decision_tree_model = None
    iris = None

# Statsmodels (for Causal Inference Demo)
try:
    import statsmodels.formula.api as smf
    STATSMODELS_AVAILABLE = True
except ImportError:
    logger.warning("Statsmodels not found. Causal Inference demo disabled.")
    STATSMODELS_AVAILABLE = False

# SciPy (for Optimization Demo)
try:
    from scipy import optimize
    SCIPY_AVAILABLE = True
except ImportError:
    logger.warning("SciPy not found. Optimization demo disabled.")
    SCIPY_AVAILABLE = False


# --- Define paths to your CSV files ---
#DEMOS_SUMMARY_CSV_PATH = os.path.join(settings.BASE_DIR, 'data', 'demos_summary.csv')
#DEMOS_CONTENT_CSV_PATH = os.path.join(settings.BASE_DIR, 'data', 'demos_content.csv') # Assuming this is still used by generic_demo_view

# --- Caches for CSV data ---
_DEMOS_SUMMARY_CACHE = None
_DEMOS_SUMMARY_MOD_TIME = 0
_DEMOS_CONTENT_CACHE = None
_DEMOS_CONTENT_MOD_TIME = 0


# --- FlightData class (from your flight_data.py) ---
class FlightData:
    def __init__(self, price, origin_airport, destination_airport, out_date, return_date, stops, via_city=None):
        self.price = price
        self.origin_airport = origin_airport
        self.destination_airport = destination_airport
        self.out_date = out_date
        self.return_date = return_date
        self.stops = stops
        self.via_city = via_city # Added for more detailed display

# --- Simulated Flight Data for the Demo ---
# Dates are relative to "today" for the demo to feel current
def get_future_date(days_offset, variation=0):
    """ Helper to get a future date string with some variation. """
    base_date = datetime.now() + timedelta(days=days_offset)
    if variation > 0:
        base_date += timedelta(days=random.randint(-variation, variation))
    return base_date.strftime("%Y-%m-%d")

SIMULATED_FLIGHT_OFFERS = [
    FlightData(price=75.00, origin_airport="LHR", destination_airport="CDG", out_date=get_future_date(30, 5), return_date=get_future_date(37, 5), stops=0),
    FlightData(price=65.00, origin_airport="STN", destination_airport="ORY", out_date=get_future_date(40, 3), return_date=get_future_date(45, 3), stops=0),
    FlightData(price=90.00, origin_airport="LGW", destination_airport="CDG", out_date=get_future_date(35, 2), return_date=get_future_date(42, 2), stops=1, via_city="AMS"),
    FlightData(price=120.00, origin_airport="MAN", destination_airport="AMS", out_date=get_future_date(50, 7), return_date=get_future_date(55, 7), stops=0),
    FlightData(price=350.00, origin_airport="LHR", destination_airport="JFK", out_date=get_future_date(60, 10), return_date=get_future_date(70, 10), stops=0),
    FlightData(price=320.00, origin_airport="LGW", destination_airport="EWR", out_date=get_future_date(75, 5), return_date=get_future_date(85, 5), stops=1, via_city="DUB"),
    FlightData(price=45.00, origin_airport="LTN", destination_airport="BCN", out_date=get_future_date(20, 3), return_date=get_future_date(25, 3), stops=0),
    FlightData(price=150.00, origin_airport="EDI", destination_airport="FCO", out_date=get_future_date(90, 10), return_date=get_future_date(97, 10), stops=0),
    FlightData(price=88.00, origin_airport="LHR", destination_airport="BER", out_date=get_future_date(25, 4), return_date=get_future_date(30, 4), stops=0),
    FlightData(price=280.00, origin_airport="MAN", destination_airport="DXB", out_date=get_future_date(100, 15), return_date=get_future_date(110, 15), stops=1, via_city="IST"),
    # Mapping LON (London - all airports) to specific London airports for simulation
    FlightData(price=70.00, origin_airport="LON", destination_airport="PAR", out_date=get_future_date(32, 5), return_date=get_future_date(39, 5), stops=0), # Generic LON to PAR
    FlightData(price=330.00, origin_airport="LON", destination_airport="NYC", out_date=get_future_date(65, 10), return_date=get_future_date(75, 10), stops=0), # Generic LON to NYC
    FlightData(price=50.00, origin_airport="LON", destination_airport="DUB", out_date=get_future_date(15, 2), return_date=get_future_date(19, 2), stops=0),
]
# Add aliases for common city codes to specific airport codes for broader matching
IATA_ALIASES = {
    "LON": ["LHR", "LGW", "STN", "LTN", "LCY"],
    "PAR": ["CDG", "ORY"],
    "NYC": ["JFK", "EWR", "LGA"],
    "BER": ["BER"], # Brandenburg replaced TXL, SXF
    "TYO": ["NRT", "HND"],
}


# Define your hardcoded demo entries here
# The 'url_name' should match the 'name' attribute in your demos/urls.py path() definitions.
# Ensure you have app_name = 'demos' in demos/urls.py for namespacing (e.g., 'demos:image_classifier').
# Replace placeholder image_urls with actual paths to your static images.
HARDCODED_DEMO_ENTRIES = [
    {
        'url_name': 'demos:image_classifier',
        'title': 'Image Classification Demo',
        'description': 'Upload an image and see predictions from a MobileNetV2 model.',
        'image_url': 'https://placehold.co/600x400/6366f1/FFFFFF?text=Image+Classifier', # Replace with your static image path
    },
    {
        'url_name': 'demos:sentiment_analyzer',
        'title': 'Sentiment Analysis Demo',
        'description': 'Analyze the sentiment of a piece of text using a pre-trained model.',
        'image_url': 'https://placehold.co/600x400/10b981/FFFFFF?text=Sentiment+Analysis', # Replace with your static image path
    },
    {
        'url_name': 'demos:data_analyser',
        'title': 'Simple CSV Data Analyzer',
        'description': 'Upload a CSV file to get basic data analysis and visualizations.',
        'image_url': 'https://placehold.co/600x400/f59e0b/FFFFFF?text=Data+Analyser', # Replace with your static image path
    },
    {
        'url_name': 'demos:data_wrangler',
        'title': 'Simple Data Wrangling Demo',
        'description': 'Upload a CSV and apply some basic data wrangling steps.',
        'image_url': 'https://placehold.co/600x400/3b82f6/FFFFFF?text=Data+Wrangler',
    },
    {
        'url_name': 'demos:explainable_ai',
        'title': 'Explainable AI (Decision Tree)',
        'description': 'See how a decision tree makes predictions and understand its feature importance.',
        'image_url': 'https://placehold.co/600x400/8b5cf6/FFFFFF?text=Explainable+AI',
    },
    {
        'url_name': 'demos:causal_inference',
        'title': 'Causal Inference',
        'description': 'This demo illustrates a common challenge in data analysis: estimating the true causal effect of an intervention.',
        'image_url': 'https://placehold.co/600x400/8b5cf6/FFFFFF?text=Causal+Inference',
    },
    {
        'url_name': 'demos:optimization_demo',
        'title': 'Optimisation Demo',
        'description': 'This demo uses scipy.optimize.minimize to find a local minimum of a mathematical function (Himmelblau\'s function)',
        'image_url': 'https://placehold.co/600x400/8b5cf6/FFFFFF?text=Optimisation+Demo',
    },
    {
        'url_name': 'demos:keras_nmt_demo',
        'title': 'Keras NMT Demo',
        'description': 'Keras NMT Demo: A step-by-step guide to building and running a simple English-to-German translator using Keras.',
        'image_url': 'https://placehold.co/600x400/8b5cf6/FFFFFF?text=Keras+NMT+Demo',
    },
    {
        'url_name': 'demos:amazon_price_tracker',
        'title': 'Amazon Price Tracker Demo',
        'description': 'Enter an Amazon product URL to track its price and simulate alerts.',
        'image_url': 'https://placehold.co/600x400/06b6d4/FFFFFF?text=Price+Tracker',
    },
    { # New Flight Deal Finder Demo Entry
        'url_name': 'demos:flight_deal_finder', # This name will be used in urls.py
        'title': 'Flight Deal Finder Demo',
        'description': 'Simulate finding cheap flight deals based on origin, destination, and target price using sample data.',
        'image_url': 'https://placehold.co/600x400/38bdf8/FFFFFF?text=Flight+Deals', # Example placeholder
    },
]

def all_demos_list_view(request):
    """
    Displays a paginated list of demos.
    If demos exist in the database, it shows both database demos and hardcoded interactive demos.
    If the database is empty, no demos (neither DB nor hardcoded) are shown.
    """
    all_display_demos = []
    error_message = None
    placeholder_image = 'https://placehold.co/600x400/cccccc/ffffff?text=Preview+Not+Available'

    try:
        # Fetch all published demos from the database
        db_demos = Demo.objects.filter(is_published=True).order_by('order', 'title')

        if db_demos.exists():
            logger.info(f"Found {db_demos.count()} demos in the database. Processing them and hardcoded demos.")
            # 1. Process demos from the database
            for demo_item in db_demos:
                all_display_demos.append({
                    'id': f"db_{demo_item.slug}", # Unique ID for potential de-duplication if needed later
                    'title': demo_item.title,
                    'description': demo_item.description or "Detailed content available.",
                    'image_url': demo_item.image_url or placeholder_image,
                    'detail_url': demo_item.get_absolute_url()
                })

            # 2. Process hardcoded demo entries (ONLY if DB demos exist)
            for demo_def in HARDCODED_DEMO_ENTRIES:
                try:
                    # Simple check to avoid adding a hardcoded demo if a DB demo links to the same specific view
                    # This assumes DB demos for specific views would have a matching `demo_url_name`
                    # or their slug would be used to generate a URL that matches one of these.
                    # A more robust de-duplication might be needed if slugs and url_names can clash.
                    is_duplicate = False
                    for db_disp_item in all_display_demos:
                        # This de-duplication is basic. If a DB item's get_absolute_url()
                        # resolves to the same as reverse(demo_def['url_name']), it's a conceptual duplicate.
                        # For simplicity, we'll assume for now that if a DB demo exists,
                        # we list all hardcoded ones unless a very direct URL name match is found in a DB demo's specific field.
                        # If your Demo model has a 'url_name_override' field:
                        # if hasattr(db_disp_item, 'db_object') and getattr(db_disp_item['db_object'], 'url_name_override', None) == demo_def['url_name']:
                        #    is_duplicate = True
                        #    break
                        pass # Keeping it simple for now: add all hardcoded if DB is not empty.

                    if not is_duplicate:
                        all_display_demos.append({
                            'id': f"hc_{demo_def['url_name'].replace(':', '_')}", # Unique ID
                            'title': demo_def.get('title', 'Untitled Interactive Demo'),
                            'description': demo_def.get('description', 'No description available.'),
                            'image_url': demo_def.get('image_url', placeholder_image),
                            'detail_url': reverse(demo_def['url_name']) # Ensure url_name exists
                        })
                except Exception as e: # Catch errors like NoReverseMatch
                    logger.error(f"Error processing hardcoded demo '{demo_def.get('title', 'Unknown')}': {e}", exc_info=True)
        else:
            # Database is empty, so hardcoded demos are not processed either.
            logger.info("No demos found in the database. Hardcoded demos will not be processed for display.")
            # all_display_demos will remain empty.

    except Exception as e:
        logger.error(f"Error fetching or processing demos: {e}", exc_info=True)
        error_message = "Could not load demo information. Please try again later."

    # Optional: Sort all combined demos by title for consistent ordering
    # This is useful now that we might have two sources (DB and hardcoded).
    all_display_demos.sort(key=lambda x: x.get('title', '').lower())

    # Pagination
    items_per_page = 9
    paginator = Paginator(all_display_demos, items_per_page)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'page_title': 'Demos & Concepts',
        'meta_description': "Explore a collection of interactive demos and conceptual explanations related to data science, machine learning, and web development.",
        'meta_keywords': "demos, machine learning, data science, AI, Python, Django, interactive examples",
        'demos': page_obj, # This is the page object for pagination
        'error_message': error_message,
    }
    return render(request, 'demos/all_demos.html', context)



# def all_demos_list_view(request):
#     """
#     Displays a paginated list of all demos.
#     It combines demos from HARDCODED_DEMO_ENTRIES (for specific interactive views)
#     and demos from the Demo model in the database (for generic content pages).
#     """
#     all_display_demos = []
#     error_message = None
#     placeholder_image = 'https://placehold.co/600x400/cccccc/ffffff?text=Preview+Not+Available'

#     # 1. Process hardcoded demo entries (for interactive demos with specific views)
#     for demo_def in HARDCODED_DEMO_ENTRIES:
#         try:
#             title = demo_def.get('title', 'Untitled Interactive Demo')
#             description = demo_def.get('description', 'No description available.')
#             image_url = demo_def.get('image_url', placeholder_image)
#             url_name = demo_def.get('url_name')

#             if not url_name:
#                 logger.warning(f"Hardcoded demo '{title}' is missing 'url_name'. Skipping.")
#                 continue

#             all_display_demos.append({
#                 'title': title,
#                 'description': description,
#                 'image_url': image_url,
#                 'detail_url': reverse(url_name)
#             })
#         except Exception as e:
#             logger.error(f"Error reversing URL for hardcoded demo '{demo_def.get('title', 'Unknown')}': {e}", exc_info=True)

#     # 2. Load demos from the database (Demo model instances)
#     # These are typically the content-rich pages managed by Demo and DemoSection.
#     try:
#         # Fetch demos from the database. You can filter (e.g., is_featured=True) or order as needed.
#         # The `description` field in the Demo model should be used for card descriptions.
#         # The `image_url` field in the Demo model should be used for card images.
#         db_demos = Demo.objects.all().order_by('order', 'title')

#         for demo_item in db_demos:
#             # Check if this DB demo might be a duplicate of a hardcoded one
#             # (e.g. if a generic page was created for an interactive demo by mistake)
#             # A more robust de-duplication might involve a specific flag on the Demo model
#             # or ensuring slugs for generic pages don't overlap with URLs for hardcoded ones.
#             is_already_hardcoded = False
#             if demo_item.demo_url_name: # If the DB item itself points to a named URL
#                 if any(hd_entry['url_name'] == demo_item.demo_url_name for hd_entry in HARDCODED_DEMO_ENTRIES):
#                     is_already_hardcoded = True
            
#             if not is_already_hardcoded:
#                 all_display_demos.append({
#                     'title': demo_item.title,
#                     'description': demo_item.description or "Detailed content available.", # Use DB description
#                     'image_url': demo_item.image_url or placeholder_image, # Use DB image_url
#                     'detail_url': demo_item.get_absolute_url() # Uses get_absolute_url from model
#                 })
#     except Exception as e:
#         logger.error(f"Error fetching demos from database: {e}", exc_info=True)
#         error_message = "Could not load some demo information from the database."


#     if not all_display_demos and not error_message:
#         logger.info("No demos (hardcoded or DB) are available to display.")

#     # Optional: Sort all combined demos by title for consistent ordering
#     all_display_demos.sort(key=lambda x: x['title'].lower())

#     items_per_page = 9
#     paginator = Paginator(all_display_demos, items_per_page)
#     page_number = request.GET.get('page')

#     try:
#         page_obj = paginator.get_page(page_number)
#     except PageNotAnInteger:
#         page_obj = paginator.page(1)
#     except EmptyPage:
#         page_obj = paginator.page(paginator.num_pages)

#     context = {
#         'page_title': 'Demos & Concepts',
#         'meta_description': "Explore a collection of interactive demos and conceptual explanations related to data science, machine learning, and web development.",
#         'meta_keywords': "demos, machine learning, data science, AI, Python, Django, interactive examples",
#         'demos': page_obj,
#         'error_message': error_message,
#     }
#     return render(request, 'demos/all_demos.html', context)


def generic_demo_view(request, demo_slug):
    """
    Generic view to display content for an informational demo page.
    Markdown for sections will be processed in the template using 'markdownify'.
    """
    try:
        # Ensure only published demos are accessible via slug
        demo_page = get_object_or_404(Demo, slug=demo_slug, is_published=True)
    except Http404: # Catch Http404 specifically from get_object_or_404
        logger.warning(f"Published demo with slug '{demo_slug}' not found.")
        raise # Re-raise to let Django handle it (render 404 page)
    except Exception as e: # Catch other unexpected errors
        logger.error(f"Unexpected error fetching demo with slug '{demo_slug}': {e}", exc_info=True)
        # You might want to render a generic error page or raise Http404
        raise Http404("An error occurred while trying to retrieve the demo page.")

    # Fetch sections; Markdown will be handled by the template filter
    # The sections queryset is accessed in the template via demo_page.sections.all
    # If you needed to pass them explicitly after some processing (not Markdown conversion):
    # demo_page_sections = demo_page.sections.all().order_by('section_order')
    # For example, if you were to convert code_snippet to HTML here, but we'll assume
    # code snippets are handled by Prism.js in template or similar.

    context = {
        'demo_slug': demo_slug, # Though demo_page.slug is also available
        'demo_page': demo_page, # Pass the whole Demo object
        # 'sections': demo_page_sections, # Only if you pre-process sections for reasons other than Markdown
        'page_title': demo_page.page_meta_title or demo_page.title,
        'meta_description': demo_page.meta_description, # Assuming this is plain text or handled by markdownify in template if needed
        'meta_keywords': demo_page.meta_keywords,
        'error_message': None, # Specific errors for this view's logic if any
    }
    return render(request, 'demos/generic_demo_page.html', context)


# def generic_demo_view(request, demo_slug):
#     """
#     Generic view to display content for an informational demo page
#     by fetching a Demo object and its related DemoSection objects from the database.
#     """
#     try:
#         demo_page = get_object_or_404(Demo, slug=demo_slug, is_published=True)
#     except Demo.DoesNotExist:
#         logger.warning(f"Demo with slug '{demo_slug}' not found in the database.")
#         raise Http404(f"Demo page with slug '{demo_slug}' not found.")
#     except Exception as e:
#         logger.error(f"Error fetching demo with slug '{demo_slug}': {e}", exc_info=True)
#         raise Http404(f"Error finding demo page.")

#     sections_queryset = demo_page.sections.all().order_by('section_order')
#     demo_page_sections = []
#     for section_model in sections_queryset:
#         section_dict = {
#             'section_order': section_model.section_order,
#             'section_title': section_model.section_title,
#             'section_content_markdown': section_model.section_content_markdown,
#             'code_language': section_model.code_language,
#             'code_snippet_title': section_model.code_snippet_title,
#             'code_snippet': section_model.code_snippet,
#             'code_snippet_explanation': section_model.code_snippet_explanation,
#             'section_content_html': None
#         }
#         if section_model.section_content_markdown:
#             try:
#                 section_dict['section_content_html'] = markdown.markdown(
#                     section_model.section_content_markdown,
#                     extensions=['fenced_code', 'codehilite', 'tables', 'nl2br', 'toc']
#                 )
#             except Exception as md_e:
#                 logger.error(f"Markdown processing error for demo '{demo_slug}', section order '{section_model.section_order}': {md_e}")
#                 section_dict['section_content_html'] = "<p>Error processing content. Please check the Markdown syntax.</p>"
#         demo_page_sections.append(section_dict)

#     if not demo_page_sections and not demo_page.demo_url_name:
#         logger.info(f"No sections found for generic demo '{demo_slug}', and it's not an interactive demo type.")

#     context = {
#         'demo_slug': demo_slug,
#         'demo_page': demo_page,
#         'sections': demo_page_sections,
#         'page_title': demo_page.page_meta_title or demo_page.title,
#         'meta_description': demo_page.meta_description,
#         'meta_keywords': demo_page.meta_keywords,
#         'error_message': None,
#     }
#     return render(request, 'demos/generic_demo_page.html', context)

# --- Placeholder for your other specific demo views ---
# Ensure these view functions are defined or remove them from HARDCODED_DEMO_ENTRIES if they don't exist.


# --- Flight Deal Finder View (NEW) ---
def flight_deal_finder_view(request):
    form = FlightDealFinderForm()
    cheapest_flight_found = None
    alert_message = None
    error_message = None
    target_price_formval = None
    no_flights_found = False
    submitted_origin = None
    submitted_destination = None


    if request.method == 'POST':
        form = FlightDealFinderForm(request.POST)
        if form.is_valid():
            origin_iata = form.cleaned_data['origin_city_iata']
            destination_iata = form.cleaned_data['destination_city_iata']
            target_price_formval = form.cleaned_data['target_price']
            submitted_origin = origin_iata
            submitted_destination = destination_iata

            logger.info(f"Searching for flights from {origin_iata} to {destination_iata} with target £{target_price_formval}")

            possible_flights = []
            
            # Consider direct IATA match or city code alias match for origin
            origin_airports_to_check = IATA_ALIASES.get(origin_iata, [origin_iata])
             # Consider direct IATA match or city code alias match for destination
            destination_airports_to_check = IATA_ALIASES.get(destination_iata, [destination_iata])

            for flight in SIMULATED_FLIGHT_OFFERS:
                # Check if flight origin matches any of the allowed origin airports
                origin_match = flight.origin_airport == origin_iata or flight.origin_airport in origin_airports_to_check
                if origin_iata in IATA_ALIASES and flight.origin_airport in IATA_ALIASES[origin_iata]: # e.g. form says LON, flight is LHR
                    origin_match = True
                
                # Check if flight destination matches any of the allowed destination airports
                destination_match = flight.destination_airport == destination_iata or flight.destination_airport in destination_airports_to_check
                if destination_iata in IATA_ALIASES and flight.destination_airport in IATA_ALIASES[destination_iata]: # e.g. form says PAR, flight is CDG
                    destination_match = True

                if origin_match and destination_match:
                    possible_flights.append(flight)
            
            if possible_flights:
                # Find the cheapest among the filtered flights
                possible_flights.sort(key=lambda f: f.price)
                cheapest_flight_found = possible_flights[0]

                if cheapest_flight_found.price < target_price_formval:
                    alert_message = f"Great news! Found a flight from {cheapest_flight_found.origin_airport} to {cheapest_flight_found.destination_airport} for £{cheapest_flight_found.price:.2f}, which is below your target of £{target_price_formval:.2f}."
                elif cheapest_flight_found.price == target_price_formval:
                    alert_message = f"Good deal! The cheapest flight found matches your target price: £{cheapest_flight_found.price:.2f} from {cheapest_flight_found.origin_airport} to {cheapest_flight_found.destination_airport}."
                else:
                    alert_message = f"The cheapest flight from {cheapest_flight_found.origin_airport} to {cheapest_flight_found.destination_airport} costs £{cheapest_flight_found.price:.2f}, which is above your target of £{target_price_formval:.2f}."
            else:
                no_flights_found = True
                alert_message = f"Sorry, no flights found in our sample data for the route {origin_iata} to {destination_iata}. Try popular routes like LON-PAR, LON-NYC, LHR-CDG."
                logger.info(f"No simulated flights found for {origin_iata} to {destination_iata}")
        else:
            # Form is not valid, errors will be displayed by the form in the template
            # error_message = "Please correct the errors below." # General message if needed
            pass

    context = {
        'form': form,
        'cheapest_flight': cheapest_flight_found,
        'alert_message': alert_message,
        'error_message': error_message,
        'target_price_formval': target_price_formval,
        'no_flights_found': no_flights_found,
        'submitted_origin': submitted_origin,
        'submitted_destination': submitted_destination,
        'page_title': 'Flight Deal Finder Demo',
        'meta_description': "Find simulated cheap flight deals. Enter your origin, destination (IATA codes), and target price.",
        'meta_keywords': "flight deals, cheap flights, travel, demo, python, django",
    }
    return render(request, 'demos/flight_deal_finder_demo.html', context)


# --- keras_nmt_demo Demo View (NEW) ---
def keras_nmt_demo_demo_view(request):
    """ Renders the page explaining keras_nmt_demo. """
    context = {
        'page_title': 'Neural Machine Translation with Keras',
        'meta_description': "A step-by-step guide to building and running a simple English-to-German Neural Machine Translation model using Keras/TensorFlow.",
        'meta_keywords': "Neural Machine Translation, NMT, Seq2Seq, LSTM, Keras, TensorFlow, Python, Demo, Portfolio",
    }
    return render(request, 'demos/keras_nmt_demo_page.html', context=context)


# --- Image Classification View (MODIFIED) ---
def image_classification_view(request):
    form = ImageUploadForm()
    prediction_results = None
    uploaded_image_base64 = None # Store image as base64 for display
    error_message = None

    if not TF_AVAILABLE:
        error_message = "TensorFlow library is not installed. This demo cannot function."
    elif not IMAGE_MODEL_LOADED:
        error_message = "Image classification model could not be loaded. Please check server logs."

    if request.method == 'POST' and TF_AVAILABLE and IMAGE_MODEL_LOADED:
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_image = form.cleaned_data['image']

            # --- Process Image In-Memory ---
            try:
                # 1. Read image content into memory
                image_bytes = uploaded_image.read()

                # 2. Load image using Keras utils from bytes
                # Use io.BytesIO to treat the bytes as a file
                img = keras_image_utils.load_img(io.BytesIO(image_bytes), target_size=(224, 224))

                # 3. Prepare for display (convert original bytes to base64)
                # Determine image format (optional, but good for data URI)
                image_format = uploaded_image.content_type.split('/')[-1] # e.g., 'jpeg', 'png'
                uploaded_image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                # Prepend the data URI scheme
                uploaded_image_base64 = f"data:{uploaded_image.content_type};base64,{uploaded_image_base64}"

                # 4. Preprocess for prediction
                img_array = keras_image_utils.img_to_array(img)
                img_array_expanded = np.expand_dims(img_array, axis=0)
                img_preprocessed = preprocess_input(img_array_expanded)

                # 5. Predict
                predictions = image_model.predict(img_preprocessed)
                decoded = decode_predictions(predictions, top=3)[0]
                prediction_results = [{'label': label.replace('_', ' '), 'probability': float(prob) * 100} for (_, label, prob) in decoded]

            except ImportError:
                 # This might happen if the dummy keras_image_utils is used
                 error_message = "TensorFlow library is not available for image processing."
                 logger.error("Attempted image processing without TensorFlow.")
            except Exception as e:
                error_message = f"Error processing image or making prediction: {e}"
                logger.error(f"Image Classification Error: {e}", exc_info=True)
                uploaded_image_base64 = None # Clear image on error
            # --- End In-Memory Processing ---

        else:
            error_message = "Invalid form submission. Please upload a valid image file."

    context = {
        'form': form,
        'prediction_results': prediction_results,
        'uploaded_image_url': uploaded_image_base64, # Pass base64 data URI instead of file URL
        'error_message': error_message,
        'page_title': 'Image Classification Demo',
        'meta_description': "Upload an image and see predictions from the MobileNetV2 model.",
        'meta_keywords': "image classification, deep learning, MobileNetV2, TensorFlow, Keras, demo",
    }
    return render(request, 'demos/image_classification_demo.html', context=context)


# --- Sentiment Analysis View (NEW) ---
def sentiment_analysis_view(request):
    form = SentimentAnalysisForm()
    sentiment_result = None
    submitted_text = None
    error_message = None

    if not TRANSFORMERS_AVAILABLE:
        error_message = "Transformers library not installed. This demo cannot function."
    elif not SENTIMENT_MODEL_LOADED:
        error_message = "Sentiment analysis model could not be loaded. Please check server logs."

    if request.method == 'POST' and TRANSFORMERS_AVAILABLE and SENTIMENT_MODEL_LOADED:
        form = SentimentAnalysisForm(request.POST)
        if form.is_valid():
            submitted_text = form.cleaned_data['text_input']
            try:
                # Run text through the pipeline
                # Check if pipeline object actually exists before calling
                if sentiment_pipeline:
                    results = sentiment_pipeline(submitted_text)
                    if results:
                        sentiment_result = results[0] # Get the first result dictionary
                        sentiment_result['score'] = round(sentiment_result['score'] * 100, 1)
                    else:
                        error_message = "Could not analyze sentiment for the provided text."
                else:
                    # This case should ideally not be reached if MODEL_LOADED is True, but added for safety
                    error_message = "Sentiment analysis pipeline is not available."

            except Exception as e:
                error_message = f"Error during sentiment analysis: {e}"
        else:
            error_message = "Please enter some text to analyze."

    context = {
        'form': form,
        'sentiment_result': sentiment_result,
        'submitted_text': submitted_text,
        'error_message': error_message,
        'page_title': 'Sentiment Analysis Demo',
    }
    return render(request, 'demos/sentiment_analysis_demo.html', context=context)

##### 


##### Data Analyser


def data_analyser_view(request):
    form = CSVUploadForm()
    analysis_results = None
    error_message = None
    # plot_image_url will be base64 data URI

    if not DATA_LIBS_AVAILABLE: error_message = "Data science libraries (Pandas, Matplotlib, Seaborn) not installed."

    if request.method == 'POST' and DATA_LIBS_AVAILABLE:
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            if csv_file.size > 5 * 1024 * 1024: error_message = "File size exceeds 5MB."
            elif not csv_file.name.lower().endswith('.csv'): error_message = "Invalid file type. Please upload CSV."
            else:
                try:
                    df = pd.read_csv(csv_file)
                    buffer = io.StringIO()
                    df.info(buf=buffer)
                    df_info = buffer.getvalue()
                    df_describe_html = None
                    numeric_df = df.select_dtypes(include=np.number)
                    if not numeric_df.empty:
                         df_describe_html = numeric_df.describe().to_html(classes='w-full text-sm text-left text-gray-500 dark:text-gray-400 border border-collapse border-gray-200 dark:border-gray-700', border=0)
                    
                    plot_base64 = None
                    if not numeric_df.empty:
                        col_to_plot = numeric_df.columns[0]
                        plt.figure(figsize=(8, 4))
                        sns.histplot(df[col_to_plot], kde=True)
                        plt.title(f'Distribution of {col_to_plot}')
                        plt.xlabel(col_to_plot); plt.ylabel('Frequency'); plt.tight_layout()
                        img_buffer = io.BytesIO()
                        plt.savefig(img_buffer, format='png'); img_buffer.seek(0)
                        plot_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                        plt.close()
                    
                    analysis_results = {
                        'filename': csv_file.name, 'shape': df.shape, 'columns': df.columns.tolist(),
                        'head': df.head().to_html(classes='w-full text-sm text-left text-gray-500 dark:text-gray-400', border=0, index=False),
                        'info': df_info, 'describe_html': df_describe_html,
                        'plot_url': f"data:image/png;base64,{plot_base64}" if plot_base64 else None
                    }
                except pd.errors.EmptyDataError: error_message = "Uploaded CSV is empty."
                except Exception as e: error_message = f"Error processing CSV: {e}"; logger.error(f"Data Analyser Error: {e}", exc_info=True)
        # else: form errors handled by template
    context = {
        'form': form, 'analysis_results': analysis_results, 'error_message': error_message,
        'page_title': 'Simple CSV Data Analyzer',
    }
    return render(request, 'demos/data_analysis_demo.html', context=context)


# # --- Data Analysis View (NEW) ---
# def data_analyser_view(request):
#     form = CSVUploadForm()
#     analysis_results = None
#     error_message = None
#     plot_image_url = None

#     if not DATA_LIBS_AVAILABLE:
#         error_message = "Required libraries (Pandas, Matplotlib, Seaborn) not installed."

#     if request.method == 'POST' and DATA_LIBS_AVAILABLE:
#         form = CSVUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             csv_file = form.cleaned_data['csv_file']

#             # Basic validation (size, type)
#             if csv_file.size > 5 * 1024 * 1024: # Max 5 MB
#                 error_message = "File size exceeds 5MB limit."
#             elif not csv_file.name.lower().endswith('.csv'):
#                 error_message = "Invalid file type. Please upload a CSV file."
#             else:
#                 try:
#                     # Read CSV into Pandas DataFrame
#                     df = pd.read_csv(csv_file)

#                     # --- Perform Basic Analysis ---
#                     # 1. Get DataFrame Info (capture output)
#                     buffer = io.StringIO()
#                     df.info(buf=buffer)
#                     df_info = buffer.getvalue()

#                     # 2. Get Descriptive Statistics (convert to HTML)
#                     df_describe_html = None
#                     try:
#                         # Select only numeric columns for describe()
#                         numeric_df = df.select_dtypes(include=np.number)
#                         if not numeric_df.empty:
#                              df_describe_html = numeric_df.describe().to_html(
#                                  classes='w-full text-sm text-left text-gray-500 dark:text-gray-400 border border-collapse border-gray-200 dark:border-gray-700', # Tailwind classes
#                                  border=0 # Remove default border
#                              )
#                     except Exception as desc_e:
#                         print(f"Error generating describe table: {desc_e}")


#                     # 3. Generate a Plot (Example: Histogram of the first numerical column)
#                     plot_filename = None
#                     numerical_cols = df.select_dtypes(include=np.number).columns
#                     if not numerical_cols.empty:
#                         col_to_plot = numerical_cols[0] # Plot the first numerical column
#                         plt.figure(figsize=(8, 4)) # Create a figure
#                         sns.histplot(df[col_to_plot], kde=True)
#                         plt.title(f'Distribution of {col_to_plot}')
#                         plt.xlabel(col_to_plot)
#                         plt.ylabel('Frequency')
#                         plt.tight_layout()

#                         # Save plot to a temporary file in media
#                         temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_demos')
#                         os.makedirs(temp_dir, exist_ok=True)
#                         plot_filename = f"plot_{uuid.uuid4()}.png"
#                         plot_filepath = os.path.join(temp_dir, plot_filename)
#                         plt.savefig(plot_filepath)
#                         plt.close() # Close the figure to free memory

#                         plot_image_url = os.path.join(settings.MEDIA_URL, 'temp_demos', plot_filename).replace("\\", "/")
#                     else:
#                         print("No numerical columns found for plotting.")


#                     # --- Prepare results for template ---
#                     analysis_results = {
#                         'filename': csv_file.name,
#                         'shape': df.shape,
#                         'columns': df.columns.tolist(),
#                         'head': df.head().to_html(classes='w-full text-sm text-left text-gray-500 dark:text-gray-400', border=0, index=False),
#                         'info': df_info,
#                         'describe_html': df_describe_html,
#                         'plot_url': plot_image_url
#                     }

#                 except pd.errors.EmptyDataError:
#                     error_message = "The uploaded CSV file is empty."
#                 except Exception as e:
#                     error_message = f"Error processing CSV file: {e}"
#         else:
#             error_message = "Invalid form submission. Please upload a valid CSV file."

#     context = {
#         'form': form,
#         'analysis_results': analysis_results,
#         'error_message': error_message,
#         'page_title': 'Simple CSV Data Analyzer',
#     }
#     return render(request, 'demos/data_analysis_demo.html', context=context)


##### --- Data Wrangling View ---


def data_wrangling_view(request):
    form = CSVUploadForm() # Reuse the CSV upload form
    wrangling_results = None
    error_message = None

    if not DATA_LIBS_AVAILABLE:
        error_message = "Required libraries (Pandas, NumPy) not installed."

    if request.method == 'POST' and DATA_LIBS_AVAILABLE:
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']

            # Basic validation
            if csv_file.size > 5 * 1024 * 1024: # Max 5 MB
                error_message = "File size exceeds 5MB limit."
            elif not csv_file.name.lower().endswith('.csv'):
                error_message = "Invalid file type. Please upload a CSV file."
            else:
                try:
                    # Read CSV
                    df = pd.read_csv(csv_file)
                    original_head_html = df.head().to_html(classes='w-full text-sm text-left text-gray-500 dark:text-gray-400', border=0, index=False)
                    original_columns = df.columns.tolist()
                    original_shape = df.shape

                    # --- Apply Wrangling Steps ---
                    steps_applied = []
                    df_wrangled = df.copy() # Work on a copy

                    # 1. Handle Missing Numerical Values (Example: fill with median)
                    numeric_cols = df_wrangled.select_dtypes(include=np.number).columns
                    for col in numeric_cols:
                        if df_wrangled[col].isnull().any():
                            median_val = df_wrangled[col].median()
                            df_wrangled[col].fillna(median_val, inplace=True)
                            steps_applied.append(f"Filled missing values in numerical column '{col}' with median ({median_val:.2f}).")

                    # 2. Handle Missing Categorical Values (Example: fill with 'Unknown')
                    categorical_cols = df_wrangled.select_dtypes(include='object').columns
                    for col in categorical_cols:
                        if df_wrangled[col].isnull().any():
                            df_wrangled[col].fillna('Unknown', inplace=True)
                            steps_applied.append(f"Filled missing values in categorical column '{col}' with 'Unknown'.")

                    # 3. Rename a Column (Example: if 'QuantitySold' exists)
                    if 'QuantitySold' in df_wrangled.columns:
                        df_wrangled.rename(columns={'QuantitySold': 'Units_Sold'}, inplace=True)
                        steps_applied.append("Renamed column 'QuantitySold' to 'Units_Sold'.")
                    elif 'Quantity' in df_wrangled.columns: # Alternative common name
                            df_wrangled.rename(columns={'Quantity': 'Units_Sold'}, inplace=True)
                            steps_applied.append("Renamed column 'Quantity' to 'Units_Sold'.")


                    # 4. Create a Derived Column (Example: Price Category)
                    if 'Price' in df_wrangled.columns:
                        # Ensure Price is numeric first
                        df_wrangled['Price'] = pd.to_numeric(df_wrangled['Price'], errors='coerce')
                        df_wrangled.dropna(subset=['Price'], inplace=True) # Drop rows where conversion failed

                        bins = [0, 50, 200, np.inf] # Define price ranges
                        labels = ['Low', 'Medium', 'High']
                        df_wrangled['Price_Category'] = pd.cut(df_wrangled['Price'], bins=bins, labels=labels, right=False)
                        steps_applied.append("Created 'Price_Category' column based on 'Price' (Low: <50, Medium: 50-199, High: >=200).")

                    # --- Prepare results ---
                    wrangled_head_html = df_wrangled.head().to_html(classes='w-full text-sm text-left text-gray-500 dark:text-gray-400', border=0, index=False)

                    wrangling_results = {
                        'filename': csv_file.name,
                        'original_shape': original_shape,
                        'original_columns': original_columns,
                        'original_head': original_head_html,
                        'wrangled_shape': df_wrangled.shape,
                        'wrangled_columns': df_wrangled.columns.tolist(),
                        'wrangled_head': wrangled_head_html,
                        'steps_applied': steps_applied,
                    }

                except pd.errors.EmptyDataError:
                    error_message = "The uploaded CSV file is empty."
                except Exception as e:
                    error_message = f"Error processing CSV file: {e}"
                    print(f"Wrangling Error: {e}") # Log error for debugging
        else:
            error_message = "Invalid form submission. Please upload a valid CSV file."

    context = {
        'form': form,
        'wrangling_results': wrangling_results,
        'error_message': error_message,
        'page_title': 'Simple Data Wrangling Demo',
    }
    return render(request, 'demos/data_wrangling_demo.html', context=context)



# --- Amazon Price Tracker View (NEW) ---
def amazon_price_tracker_view(request):
    """
    Handles the Amazon Price Tracker demo.
    Takes a product URL, scrapes it, and compares price with a target.
    """
    form = AmazonProductURLForm()
    product_title = None
    current_price = None
    target_price_formval = None # To store the target price from the form for display
    alert_message = None
    error_message = None

    if request.method == 'POST':
        form = AmazonProductURLForm(request.POST)
        if form.is_valid():
            product_url = form.cleaned_data['product_url']
            target_price_formval = form.cleaned_data.get('target_price') # Get optional target price

            # --- Headers for request (mimic browser) ---
            # Using a more generic User-Agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "DNT": "1", # Do Not Track
            }
            
            try:
                logger.info(f"Attempting to fetch URL: {product_url}")
                response = requests.get(product_url, headers=headers, timeout=10)
                response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
                
                soup = BeautifulSoup(response.content, "html.parser")

                # --- Extract Product Title ---
                # Common selectors for Amazon product titles (these can change!)
                title_selectors = [
                    "#productTitle",
                    "span.a-size-large.product-title-word-break", # Another common one
                    "h1#title span#productTitle" # More specific
                ]
                for selector in title_selectors:
                    title_element = soup.select_one(selector)
                    if title_element:
                        product_title = title_element.get_text().strip()
                        break
                
                if not product_title: # Fallback if specific selectors fail
                    product_title_element = soup.find("span", {"id": "productTitle"})
                    if product_title_element:
                         product_title = product_title_element.get_text().strip()
                    else: # Broader search if still not found
                        h1_title = soup.find('h1')
                        if h1_title: product_title = h1_title.get_text(separator=" ", strip=True).splitlines()[0]


                # --- Extract Product Price ---
                # Common selectors for Amazon prices (these can change!)
                # Order matters: try more specific/reliable ones first.
                price_selectors = [
                    "span.a-price span.a-offscreen", # Often the main price
                    "span.a-price.reinventPricePriceToPayMargin span.a-offscreen", # Variation
                    "span.a-price.aok-align-center span.a-offscreen", 
                    "div#corePrice_feature_div span.a-price span.a-offscreen", # Inside a specific div
                    "div#corePriceDisplay_desktop_feature_div span.a-price span.a-offscreen",
                    "span.priceToPay span.a-offscreen", # For some layouts
                    "span.apexPriceToPay span.a-offscreen",
                    "td.a-span12 span.a-price span.a-offscreen", # Inside tables for some book formats
                    "div#price span.a-offscreen", # Simpler one
                    ".a-price-whole", # Just the whole part, might need to combine with fraction
                ]
                price_text = None
                for selector in price_selectors:
                    price_element = soup.select_one(selector)
                    if price_element:
                        price_text = price_element.get_text().strip()
                        break
                
                # If only whole part was found, try to find fraction
                if not price_text or (price_text and not price_text.startswith("£") and not price_text.startswith("$") and not price_text.startswith("€")):
                    whole_price_el = soup.select_one("span.a-price-whole")
                    fraction_price_el = soup.select_one("span.a-price-fraction")
                    currency_el = soup.select_one("span.a-price-symbol")
                    if whole_price_el and fraction_price_el and currency_el:
                        price_text = f"{currency_el.get_text().strip()}{whole_price_el.get_text().strip()}.{fraction_price_el.get_text().strip()}"


                if price_text:
                    # Clean price (remove currency symbol and commas, handle different decimal separators if needed)
                    # Assuming price is in £ for .co.uk, adapt if international
                    price_cleaned = price_text.replace("£", "").replace("$", "").replace("€", "").replace(",", "").strip()
                    current_price = float(price_cleaned)
                else:
                    logger.warning(f"Could not find price for URL: {product_url}. Soup sample: {soup.title.string if soup.title else 'No title'}")


                if not product_title:
                     logger.warning(f"Could not find product title for URL: {product_url}. Soup sample: {soup.title.string if soup.title else 'No title'}")
                     error_message = "Could not extract product title. Amazon's page structure might have changed or the URL is for a non-standard product page."
                if not current_price and not error_message: # Only set this if title was found but price wasn't
                     error_message = "Could not extract product price. Amazon's page structure might have changed."


                if product_title and current_price:
                    if target_price_formval: # If a target price was given
                        if current_price < target_price_formval:
                            alert_message = f"Success! The current price (£{current_price:.2f}) is below your target of £{target_price_formval:.2f}. (Email alert simulated)"
                        elif current_price == target_price_formval:
                            alert_message = f"The current price (£{current_price:.2f}) matches your target of £{target_price_formval:.2f}. (Email alert simulated)"
                        else:
                            alert_message = f"The current price (£{current_price:.2f}) is above your target of £{target_price_formval:.2f}."
                    else: # No target price given
                        alert_message = "Product details fetched successfully. No target price was set for comparison."
                
                # elif not error_message: # If scraping failed to get title or price but no specific exception
                #     error_message = "Could not retrieve product details. The Amazon page structure might have changed, the URL is invalid, or the product is unavailable."

            except requests.exceptions.HTTPError as e:
                error_message = f"HTTP error accessing URL: {e}. The product page may be unavailable or the URL is incorrect."
                logger.error(f"HTTPError for {product_url}: {e}")
            except requests.exceptions.ConnectionError:
                error_message = "Network error. Could not connect to Amazon. Please check your internet connection."
                logger.error(f"ConnectionError for {product_url}")
            except requests.exceptions.Timeout:
                error_message = "The request to Amazon timed out. The server might be busy or your connection slow."
                logger.error(f"Timeout for {product_url}")
            except requests.exceptions.RequestException as e:
                error_message = f"An error occurred while fetching the product page: {e}"
                logger.error(f"RequestException for {product_url}: {e}")
            except ValueError: # For float conversion error
                error_message = "Could not parse the price value from the page. The format might be unexpected."
                logger.error(f"ValueError parsing price from {product_url}")
            except Exception as e:
                error_message = f"An unexpected error occurred: {e}. Please check the URL and try again."
                logger.error(f"Unexpected error for {product_url}: {e}", exc_info=True)
        else:
            # Form is not valid, errors will be displayed by the form in the template
            pass


    context = {
        'form': form,
        'product_title': product_title,
        'current_price': current_price,
        'target_price_formval': target_price_formval, # Pass submitted target price back to template
        'alert_message': alert_message,
        'error_message': error_message,
        'page_title': 'Amazon Price Tracker Demo',
        'meta_description': "Track Amazon product prices. Enter a product URL and an optional target price to see if you'd get an alert.",
        'meta_keywords': "amazon price tracker, price alert, web scraping, python, django, demo",
    }
    return render(request, 'demos/amazon_price_tracker_demo.html', context)


def explainable_ai_view(request):
    form = ExplainableAIDemoForm()
    prediction = None; explanation_rules = None; feature_importances = None
    input_features_dict = None; probability_list = None; error_message = None

    if not SKLEARN_AVAILABLE: error_message = "Scikit-learn library is not installed."
    elif not TREE_MODEL_LOADED: error_message = "Decision Tree model or Iris data could not be loaded."

    if request.method == 'POST' and SKLEARN_AVAILABLE and TREE_MODEL_LOADED:
        form = ExplainableAIDemoForm(request.POST)
        if form.is_valid():
            input_features_dict = form.cleaned_data
            try:
                input_arr = np.array([[v for k,v in sorted(input_features_dict.items())]])
                pred_idx = decision_tree_model.predict(input_arr)[0]
                prediction = iris.target_names[pred_idx]
                pred_proba_raw = decision_tree_model.predict_proba(input_arr)[0] * 100
                probability_list = [{'name': name, 'probability': prob} for name, prob in zip(iris.target_names, pred_proba_raw)]
                
                # Generate explanation rules as Markdown
                node_indicator = decision_tree_model.decision_path(input_arr)
                leaf_id = decision_tree_model.apply(input_arr)
                node_index = node_indicator.indices[node_indicator.indptr[0]:node_indicator.indptr[1]]
                explanation_rules = []
                tree_ = decision_tree_model.tree_
                feature_names = iris.feature_names
                for i, node_id in enumerate(node_index):
                    if leaf_id[0] == node_id: # Check if it's the leaf node
                        value = tree_.value[node_id][0]; class_dist = [f"{iris.target_names[j]} ({int(v)})" for j, v in enumerate(value)]
                        explanation_rules.append(f"**Leaf Node {node_id}:** Reached Leaf. Prediction based on majority class here (counts: {', '.join(class_dist)}).")
                        break 
                    feature_idx = tree_.feature[node_id]; threshold = round(tree_.threshold[node_id], 2)
                    feature_name = feature_names[feature_idx]; input_val = input_arr[0, feature_idx]
                    
                    # Determine if the current input value for the feature goes left or right
                    if input_val <= threshold:
                        decision_text = f"*{feature_name}* ({input_val:.2f}) **&lt;= {threshold}**" # Using Markdown for bold/italic and HTML entity for <=
                        next_node_id_text = f"Node {tree_.children_left[node_id]}"
                    else:
                        decision_text = f"*{feature_name}* ({input_val:.2f}) **&gt; {threshold}**" # Using Markdown for bold/italic and HTML entity for >
                        next_node_id_text = f"Node {tree_.children_right[node_id]}"
                    
                    explanation_rules.append(f"**Node {node_id}:** {decision_text}? **Yes**. Go to {next_node_id_text}.")

                importances = decision_tree_model.feature_importances_
                feature_importances = sorted(zip(feature_names, importances * 100), key=lambda x: x[1], reverse=True)
            except Exception as e: 
                error_message = f"Error during prediction: {e}"
                logger.error(f"XAI Error: {e}", exc_info=True)
                # Ensure these are None if an error occurs before they are set
                explanation_rules = None
                feature_importances = None
                
    context = {
        'form': form, 'prediction': prediction, 'probability_list': probability_list,
        'explanation_rules': explanation_rules, 
        'feature_importances': feature_importances,
        'input_features': input_features_dict, 
        'error_message': error_message,
        'page_title': 'Explainable AI (Decision Tree)',
    }
    return render(request, 'demos/explainable_ai_demo.html', context=context)


# --- Causal Inference Demo View (NEW) ---
def causal_inference_demo_view(request):
    """
    Demonstrates Causal Inference using Regression Adjustment
    on simulated marketing campaign data.
    """
    results = None
    error_message = None
    plot_url = None

    # Check dependencies
    if not DATA_LIBS_AVAILABLE or not STATSMODELS_AVAILABLE or not SKLEARN_AVAILABLE:
         error_message = "Required libraries (Pandas, Statsmodels, Scikit-learn, Matplotlib) not installed."
         context = {'error_message': error_message, 'page_title': 'Causal Inference Demo'}
         return render(request, 'demos/causal_inference_demo.html', context)

    try:
        # 1. Simulate Data with Confounding
        np.random.seed(42) # for reproducibility
        n_customers = 1000
        # Confounder: 'engagement_score' (influences both treatment and outcome)
        engagement_score = np.random.normal(50, 15, n_customers).clip(1, 100)
        # Treatment Assignment (Promotion): More engaged customers are more likely to get promo
        prob_promo = 1 / (1 + np.exp(-( -2.5 + 0.05 * engagement_score))) # Sigmoid function
        received_promo = (np.random.rand(n_customers) < prob_promo).astype(int) # 1 if promo, 0 otherwise
        # Outcome (Spending): Depends on engagement, promo (true effect=20), and noise
        true_ate = 20
        spending = 50 + 0.8 * engagement_score + true_ate * received_promo + np.random.normal(0, 10, n_customers)
        spending = spending.clip(10) # Min spending of 10

        df = pd.DataFrame({
            'customer_id': range(n_customers),
            'engagement': engagement_score.round(1),
            'received_promo': received_promo, # Treatment (0 or 1)
            'spending': spending.round(2)      # Outcome
        })

        # 2. Naive Comparison (Incorrect due to confounding)
        naive_diff = df[df['received_promo'] == 1]['spending'].mean() - \
                     df[df['received_promo'] == 0]['spending'].mean()

        # 3. Regression Adjustment
        # Model: spending ~ engagement + received_promo
        # Fit OLS model using statsmodels
        # Use C(received_promo) if you want explicit categorical treatment
        ols_formula = 'spending ~ engagement + received_promo'
        ols_model = smf.ols(formula=ols_formula, data=df).fit()

        # Predict potential outcomes
        # Predict spending if EVERYONE received promo
        df_promo_all = df.assign(received_promo=1)
        pred_spending_if_promo = ols_model.predict(df_promo_all)

        # Predict spending if NO ONE received promo
        df_no_promo_all = df.assign(received_promo=0)
        pred_spending_if_no_promo = ols_model.predict(df_no_promo_all)

        # Calculate Average Treatment Effect (ATE)
        ate_estimate = (pred_spending_if_promo - pred_spending_if_no_promo).mean()

        # 4. Prepare results for template
        results = {
            'n_customers': n_customers,
            'naive_difference': round(naive_diff, 2),
            'confounder_info': "Higher engagement scores increase both the chance of receiving a promotion AND baseline spending.",
            'method_used': "Regression Adjustment",
            'regression_formula': ols_formula,
            'ate_estimate': round(ate_estimate, 2),
            'true_ate': true_ate, # For comparison in the demo
            'ols_summary': ols_model.summary().as_html() # Get model summary as HTML table
        }

        # 5. Generate a simple plot (Optional)
        try:
            plt.figure(figsize=(7, 5))
            sns.scatterplot(data=df, x='engagement', y='spending', hue='received_promo', alpha=0.6)
            plt.title('Spending vs Engagement (Colored by Promo)')
            plt.xlabel("Engagement Score")
            plt.ylabel("Customer Spending ($)")
            plt.legend(title='Received Promo', loc='upper left')
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()

            # Save plot to buffer and encode as base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plot_url = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close() # Close the figure
            results['plot_url'] = f"data:image/png;base64,{plot_url}"

        except Exception as plot_e:
            print(f"Error generating plot: {plot_e}")
            results['plot_url'] = None # Handle plot error gracefully

    except Exception as e:
        error_message = f"An error occurred during analysis: {e}"
        print(f"Causal Inference Error: {e}") # Log for debugging

    context = {
        'results': results,
        'error_message': error_message,
        'page_title': 'Causal Inference Demo',
        'meta_description': "Demonstration of causal inference using regression adjustment to estimate treatment effects in the presence of confounding.",
        'meta_keywords': "causal inference, regression adjustment, ATE, confounding, data science, demo",
    }
    return render(request, 'demos/causal_inference_demo.html', context=context)


# --- Optimization Demo View (NEW) ---
def optimization_demo_view(request):
    """
    Demonstrates finding the minimum of a function using SciPy's optimize module.
    """
    results = None
    error_message = None
    plot_url = None

    if not SCIPY_AVAILABLE or not DATA_LIBS_AVAILABLE or not np:
        error_message = "Required libraries (SciPy, NumPy, Matplotlib) not installed."
        context = {'error_message': error_message, 'page_title': 'Optimization with SciPy'}
        return render(request, 'demos/optimization_demo.html', context)

    try:
        # 1. Define the function to minimize (Himmelblau's function)
        # This function has multiple local minima.
        def himmelblau(p):
            x, y = p
            # f(x, y) = (x^2 + y - 11)^2 + (x + y^2 - 7)^2
            term1 = (x**2 + y - 11)**2
            term2 = (x + y**2 - 7)**2
            return term1 + term2

        function_str = "(x**2 + y - 11)**2 + (x + y**2 - 7)**2"
        start_point = np.array([0.0, 0.0]) # Where the optimization starts

        # 2. Perform Optimization
        # Use scipy.optimize.minimize. 'Nelder-Mead' is a common gradient-free method.
        optimization_result = optimize.minimize(
            himmelblau,
            start_point,
            method='Nelder-Mead',
            options={'xatol': 1e-6, 'disp': False} # Tolerance and display options
        )

        # 3. Prepare results
        if optimization_result.success:
            found_minimum_x = optimization_result.x
            found_minimum_value = optimization_result.fun
            results = {
                'function': function_str,
                'start_point': start_point.tolist(),
                'method': 'Nelder-Mead',
                'success': optimization_result.success,
                'message': optimization_result.message,
                'found_minimum_point': [round(coord, 4) for coord in found_minimum_x],
                'found_minimum_value': round(found_minimum_value, 4),
                'iterations': optimization_result.nit,
            }
        else:
            error_message = f"Optimization failed: {optimization_result.message}"
            results = {'success': False, 'message': optimization_result.message}


        # 4. Generate Contour Plot
        try:
            x_range = np.arange(-5.0, 5.0, 0.1)
            y_range = np.arange(-5.0, 5.0, 0.1)
            X_grid, Y_grid = np.meshgrid(x_range, y_range)
            Z_grid = himmelblau([X_grid, Y_grid])

            plt.figure(figsize=(7, 6))
            # Use contourf for filled contours, contour for lines
            contour_plot = plt.contourf(X_grid, Y_grid, Z_grid, levels=np.logspace(0, 3, 15), cmap='viridis', alpha=0.8)
            plt.colorbar(contour_plot, label='Function Value (log scale)')
            plt.contour(X_grid, Y_grid, Z_grid, levels=np.logspace(0, 3, 15), colors='white', linewidths=0.5, alpha=0.5)

            # Mark known minima for Himmelblau's function
            known_minima = [
                (3.0, 2.0),
                (-2.805118, 3.131312),
                (-3.779310, -3.283186),
                (3.584428, -1.848126)
            ]
            for km in known_minima:
                plt.plot(km[0], km[1], 'r*', markersize=10, label='Known Minimum' if km == known_minima[0] else "")

            # Mark start point and found minimum
            plt.plot(start_point[0], start_point[1], 'go', markersize=8, label='Start Point')
            if optimization_result.success:
                plt.plot(found_minimum_x[0], found_minimum_x[1], 'yo', markersize=8, label='Found Minimum')

            plt.xlabel('x')
            plt.ylabel('y')
            plt.title("Optimization of Himmelblau's Function")
            plt.legend(fontsize='small')
            plt.grid(True, linestyle=':', alpha=0.4)
            plt.axis('equal') # Ensure aspect ratio is equal

            # Save plot to buffer and encode as base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plot_url = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close() # Close the figure
            if results: results['plot_url'] = f"data:image/png;base64,{plot_url}"

        except Exception as plot_e:
            print(f"Error generating plot: {plot_e}")
            if results: results['plot_url'] = None # Handle plot error gracefully

    except Exception as e:
        error_message = f"An error occurred during optimization setup: {e}"
        print(f"Optimization Demo Error: {e}") # Log for debugging

    context = {
        'results': results,
        'error_message': error_message,
        'page_title': 'Optimization with SciPy',
        'meta_description': "Demonstration of finding function minima using SciPy's optimization tools.",
        'meta_keywords': "scipy, optimization, minimize, Nelder-Mead, Himmelblau, data science, demo",
    }
    return render(request, 'demos/optimization_demo.html', context=context)

## ml_visualization_static_demo

# from sklearn.metrics import confusion_matrix, roc_curve, auc
# from sklearn.model_selection import learning_curve, train_test_split
# from sklearn.ensemble import RandomForestClassifier # Example model
# from sklearn.datasets import make_classification # For generating sample data

# def _plot_to_base64(fig):
#     """Helper function to save a Matplotlib figure to a base64 encoded string."""
#     buf = io.BytesIO()
#     fig.savefig(buf, format='png', bbox_inches='tight') # Save to buffer
#     buf.seek(0)
#     image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
#     plt.close(fig) # Close the figure to free memory
#     return image_base64

# def static_ml_visualization(request):
#     """
#     View to generate static ML chart images using Matplotlib/Seaborn
#     and render the template.
#     """
#     context = {}
#     error_message = None

#     try:
#         # --- 0. Simulate Data and Train a Model ---
#         n_samples = 1000
#         n_features = 5
#         n_informative = 3
#         random_state = 42

#         X, y = make_classification(
#             n_samples=n_samples,
#             n_features=n_features,
#             n_informative=n_informative,
#             n_redundant=n_features - n_informative,
#             n_clusters_per_class=1,
#             flip_y=0.05,
#             random_state=random_state
#         )
#         feature_names = [f'Feature_{i+1}' for i in range(n_features)]
#         X_train, X_test, y_train, y_test = train_test_split(
#             X, y, test_size=0.3, random_state=random_state
#         )
#         model = RandomForestClassifier(n_estimators=50, random_state=random_state)
#         model.fit(X_train, y_train)
#         y_pred = model.predict(X_test)
#         y_scores = model.predict_proba(X_test)[:, 1]

#         # --- 1. Confusion Matrix Plot ---
#         cm_labels = ['Class 0', 'Class 1']
#         cm = confusion_matrix(y_test, y_pred)

#         fig_cm, ax_cm = plt.subplots(figsize=(5, 4)) # Create figure and axes
#         sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax_cm,
#                     xticklabels=cm_labels, yticklabels=cm_labels,
#                     annot_kws={"size": 12})
#         ax_cm.set_title('Confusion Matrix', fontsize=14)
#         ax_cm.set_ylabel('Actual Labels', fontsize=12)
#         ax_cm.set_xlabel('Predicted Labels', fontsize=12)
#         plt.xticks(rotation=0)
#         plt.yticks(rotation=0)
#         # Convert plot to base64
#         context['confusion_matrix_b64'] = _plot_to_base64(fig_cm)

#         # --- 2. ROC Curve Plot ---
#         fpr, tpr, thresholds = roc_curve(y_test, y_scores)
#         roc_auc_score = auc(fpr, tpr)

#         fig_roc, ax_roc = plt.subplots(figsize=(6, 5))
#         ax_roc.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc_score:.2f})')
#         ax_roc.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Chance (AUC = 0.50)')
#         ax_roc.set_xlim([0.0, 1.0])
#         ax_roc.set_ylim([0.0, 1.05])
#         ax_roc.set_xlabel('False Positive Rate (FPR)', fontsize=12)
#         ax_roc.set_ylabel('True Positive Rate (TPR)', fontsize=12)
#         ax_roc.set_title('Receiver Operating Characteristic (ROC) Curve', fontsize=14)
#         ax_roc.legend(loc="lower right", fontsize=10)
#         ax_roc.grid(alpha=0.3)
#         # Convert plot to base64
#         context['roc_curve_b64'] = _plot_to_base64(fig_roc)

#         # --- 3. Feature Importance Plot ---
#         importances_fi = model.feature_importances_
#         indices = np.argsort(importances_fi)[::-1]
#         sorted_names = [feature_names[i] for i in indices]
#         sorted_importances = importances_fi[indices]

#         fig_fi, ax_fi = plt.subplots(figsize=(7, 4)) # Adjusted size
#         ax_fi.barh(range(len(sorted_importances)), sorted_importances, align='center', color='skyblue')
#         ax_fi.set_yticks(range(len(sorted_importances)), sorted_names)
#         ax_fi.set_xlabel('Feature Importance Score', fontsize=12)
#         ax_fi.set_ylabel('Feature', fontsize=12)
#         ax_fi.set_title('Feature Importances', fontsize=14)
#         ax_fi.invert_yaxis()
#         # Convert plot to base64
#         context['feature_importance_b64'] = _plot_to_base64(fig_fi)

#         # --- 4. Learning Curve Plot ---
#         train_sizes_abs, train_scores, test_scores = learning_curve(
#             estimator=model, X=X, y=y, cv=5, n_jobs=-1,
#             train_sizes=np.linspace(0.1, 1.0, 5), scoring='accuracy', random_state=random_state
#         )
#         train_scores_mean_lc = np.mean(train_scores, axis=1)
#         train_scores_std_lc = np.std(train_scores, axis=1)
#         test_scores_mean_lc = np.mean(test_scores, axis=1)
#         test_scores_std_lc = np.std(test_scores, axis=1)

#         fig_lc, ax_lc = plt.subplots(figsize=(7, 5)) # Adjusted size
#         ax_lc.grid(alpha=0.3)
#         ax_lc.fill_between(train_sizes_abs, train_scores_mean_lc - train_scores_std_lc,
#                          train_scores_mean_lc + train_scores_std_lc, alpha=0.1, color="r")
#         ax_lc.plot(train_sizes_abs, train_scores_mean_lc, 'o-', color="r", label="Training score")
#         ax_lc.fill_between(train_sizes_abs, test_scores_mean_lc - test_scores_std_lc,
#                          test_scores_mean_lc + test_scores_std_lc, alpha=0.1, color="g")
#         ax_lc.plot(train_sizes_abs, test_scores_mean_lc, 'o-', color="g", label="Cross-validation score")
#         ax_lc.set_title("Learning Curve", fontsize=14)
#         ax_lc.set_xlabel("Training Examples", fontsize=12)
#         ax_lc.set_ylabel("Score (e.g., Accuracy)", fontsize=12)
#         ax_lc.legend(loc="best", fontsize=10)
#         ax_lc.set_ylim(max(0, min(test_scores_mean_lc.min(), train_scores_mean_lc.min()) - 0.05), 1.01)
#         # Convert plot to base64
#         context['learning_curve_b64'] = _plot_to_base64(fig_lc)

#     except ImportError as e:
#         error_message = f"Required libraries missing: {e}. Please install scikit-learn, matplotlib, and seaborn."
#         print(f"Error: {error_message}")
#     except Exception as e:
#         error_message = f"An error occurred during data/plot generation: {e}"
#         print(f"Error: {error_message}")

#     if error_message:
#         context['error_message'] = error_message

#     # Render the *static* template version
#     return render(request, 'demos/ml_visualization_static_demo.html', context)


# --- Flask API Demo View (NEW) ---
def flask_api_demo_view(request):
    """ Renders the page explaining Flask for simple ML APIs. """
    context = {
        'page_title': 'Flask for Machine Learning APIs',
        'meta_description': "Learn how the Flask microframework is often used to create simple APIs for serving machine learning models.",
        'meta_keywords': "Flask, API, machine learning, deployment, Python, microframework",
    }
    return render(request, 'demos/flask_api_demo.html', context=context)

# # --- Django Concepts Demo View (NEW) ---
# def django_concepts_demo_view(request):
#     """ Renders the page explaining key Django concepts. """
#     context = {
#         'page_title': 'Key Django Concepts',
#         'meta_description': "Explore key features of the Django web framework, including its ORM, Admin, Forms, and Template system.",
#         'meta_keywords': "Django, web framework, ORM, admin, forms, templates, Python",
#     }
#     return render(request, 'demos/django_concepts_demo.html', context=context)


# # --- Django Security Demo View (NEW) ---
# def django_security_demo_view(request):
#     """ Renders the page explaining key Django security features. """
#     context = {
#         'page_title': 'Django Security Features',
#         'meta_description': "Learn about built-in security features in the Django framework like CSRF protection, XSS prevention, and SQL injection prevention.",
#         'meta_keywords': "Django, security, web framework, CSRF, XSS, SQL injection, protection",
#     }
#     return render(request, 'demos/django_security_demo.html', context=context)



# # --- Django Testing Demo View (NEW) ---
# def django_testing_demo_view(request):
#     """ Renders the page explaining Django's testing framework. """
#     context = {
#         'page_title': 'Django Testing Framework',
#         'meta_description': "Learn how Django's built-in testing framework helps ensure application reliability by testing models, views, and forms.",
#         'meta_keywords': "Django, testing, unit testing, TestCase, web framework, Python",
#     }
#     return render(request, 'demos/django_testing_demo.html', context=context)

# # --- AI Tools Demo View (NEW) ---
# def ai_tools_demo_view(request):
#     """ Renders the page explaining the use and risks of AI tools in development. """
#     context = {
#         'page_title': 'AI Tools in Machine Learning and Data Science Development',
#         'meta_description': "Exploring the benefits and potential dangers of using AI code assistants and large language models in machine learning and data science workflows.",
#         'meta_keywords': "AI tools, LLM, code assistant, Copilot, ChatGPT, machine learning, data science, productivity, risks, ethics",
#     }
#     return render(request, 'demos/ai_tools_demo.html', context=context)

# # --- Python Concepts Demo View (NEW) ---
# def python_concepts_demo_view(request):
#     """ Renders the page explaining/demonstrating core Python concepts. """
#     context = {
#         'page_title': 'Core Python Concepts for ML/DS',
#         'meta_description': "Interactive examples showcasing Python lists, dictionaries, loops, and functions and their relevance to data science and machine learning.",
#         'meta_keywords': "Python, core concepts, data structures, list, dictionary, function, loop, machine learning, data science, demo",
#     }
#     return render(request, 'demos/python_concepts_demo.html', context=context)


# # --- R Concepts Demo View (NEW) ---
# def r_concepts_demo_view(request):
#     """ Renders the page explaining core R concepts for Data Science. """
#     context = {
#         'page_title': 'R Language for Data Science',
#         'meta_description': "Explore key concepts and packages in the R programming language commonly used for statistical analysis, data visualization, and machine learning.",
#         'meta_keywords': "R language, data science, statistics, dplyr, ggplot2, data visualization, machine learning, demo",
#     }
#     return render(request, 'demos/r_concepts_demo.html', context=context)


# # --- Go Concepts Demo View (NEW) ---
# def go_concepts_demo_view(request):
#     """ Renders the page explaining Go's role in ML/DS infrastructure. """
#     context = {
#         'page_title': 'Go (Golang) in ML/DS Infrastructure',
#         'meta_description': "Learn how the Go programming language is used for building performant backend systems, APIs, and infrastructure components supporting machine learning workflows.",
#         'meta_keywords': "Go, Golang, machine learning, data science, infrastructure, performance, concurrency, API",
#     }
#     return render(request, 'demos/go_concepts_demo.html', context=context)


# # --- Scala Concepts Demo View (NEW) ---
# def scala_concepts_demo_view(request):
#     """ Renders the page explaining Scala's role, especially with Spark. """
#     context = {
#         'page_title': 'Scala in Big Data & ML Ecosystem',
#         'meta_description': "Learn how Scala, running on the JVM, is used with Apache Spark for large-scale data processing and machine learning tasks.",
#         'meta_keywords': "Scala, Spark, big data, machine learning, data engineering, JVM, functional programming",
#     }
#     return render(request, 'demos/scala_concepts_demo.html', context=context)


# # --- Java Concepts Demo View (NEW) ---
# def java_concepts_demo_view(request):
#     """ Renders the page explaining Java's role in the ML/DS ecosystem. """
#     context = {
#         'page_title': 'Java in Big Data & Enterprise AI',
#         'meta_description': "Learn how the Java programming language and its ecosystem are used in large-scale data processing (Hadoop, Spark), enterprise systems, and for deploying ML models.",
#         'meta_keywords': "Java, machine learning, data science, big data, Hadoop, Spark, enterprise, JVM",
#     }
#     return render(request, 'demos/java_concepts_demo.html', context=context)


# # --- Language Comparison Demo View (NEW) ---
# def language_comparison_demo_view(request):
#     """ Renders the page comparing languages used in ML/DS/AI. """
#     context = {
#         'page_title': 'Languages in ML, AI & Data Science',
#         'meta_description': "Comparing the roles and use cases of Python, R, Scala, Java, C++, and other languages in the machine learning, AI, and data science ecosystem.",
#         'meta_keywords': "programming languages, Python, R, Scala, Java, C++, machine learning, data science, AI, comparison",
#     }
#     return render(request, 'demos/language_comparison_demo.html', context=context)


# # --- Ruby Concepts Demo View (NEW) ---
# def ruby_concepts_demo_view(request):
#     """ Renders the page explaining Ruby's role relative to ML/DS. """
#     context = {
#         'page_title': 'Ruby & the ML/AI/DS Ecosystem',
#         'meta_description': "Understanding the role of the Ruby programming language, primarily known for web development (Ruby on Rails), in relation to data science and AI.",
#         'meta_keywords': "Ruby, Ruby on Rails, machine learning, data science, AI, web development",
#     }
#     return render(request, 'demos/ruby_concepts_demo.html', context=context)


# # --- OOP Concepts Demo View (NEW) ---
# def oop_concepts_demo_view(request):
#     """ Renders the page explaining OOP concepts and their relevance to ML/DS. """
#     context = {
#         'page_title': 'Demo: OOP Concepts in ML/DS',
#         'meta_description': "Understanding Object-Oriented Programming (OOP) principles like classes, objects, inheritance, and encapsulation and their application in Python for data science and machine learning.",
#         'meta_keywords': "OOP, Object-Oriented Programming, Python, machine learning, data science, classes, objects, inheritance, encapsulation, polymorphism",
#     }
#     return render(request, 'demos/oop_concepts_demo.html', context=context)


# # --- Kotlin Concepts Demo View (NEW) ---
# def kotlin_concepts_demo_view(request):
#     """ Renders the page explaining Kotlin's role, mainly in Android ML integration. """
#     context = {
#         'page_title': 'Demo: Kotlin & On-Device AI (Android)',
#         'meta_description': "Understanding Kotlin's primary role in Android development and how machine learning models (like TensorFlow Lite) are integrated for on-device AI features.",
#         'meta_keywords': "Kotlin, Android, machine learning, AI, TensorFlow Lite, on-device ML, mobile AI",
#     }
#     return render(request, 'demos/kotlin_concepts_demo.html', context=context)


# # --- Jupyter Demo View (NEW) ---
# def jupyter_demo_view(request):
#     """ Renders the page explaining Jupyter Notebooks for ML/DS. """
#     context = {
#         'page_title': 'Demo: Jupyter Notebooks in ML/DS',
#         'meta_description': "Understanding the use of Jupyter Notebooks for interactive data exploration, analysis, model prototyping, and sharing results in data science and machine learning.",
#         'meta_keywords': "Jupyter Notebook, data science, machine learning, interactive computing, Python, R, Julia, EDA",
#     }
#     return render(request, 'demos/jupyter_demo.html', context=context)


# # --- PySpark Concepts Demo View (NEW) ---
# def pyspark_concepts_demo_view(request):
#     """ Renders the page explaining PySpark for Big Data ML/DS. """
#     context = {
#         'page_title': 'Demo: PySpark for Big Data & ML',
#         'meta_description': "Understanding PySpark (Python API for Apache Spark) and its use for distributed data processing, analysis, and machine learning on large datasets.",
#         'meta_keywords': "PySpark, Spark, big data, distributed computing, data engineering, machine learning, data science, Python",
#     }
#     return render(request, 'demos/pyspark_concepts_demo.html', context=context)


# # --- PyTorch Concepts Demo View (NEW) ---
# def pytorch_concepts_demo_view(request):
#     """ Renders the page explaining PyTorch for Deep Learning. """
#     context = {
#         'page_title': 'Demo: PyTorch for Deep Learning',
#         'meta_description': "Understanding the PyTorch framework, its core concepts like Tensors and Autograd, and its use in building and training neural networks for AI and machine learning.",
#         'meta_keywords': "PyTorch, deep learning, machine learning, AI, tensors, autograd, neural networks, Python",
#     }
#     return render(request, 'demos/pytorch_concepts_demo.html', context=context)


# # --- Data Security Demo View (NEW) ---
# def data_security_demo_view(request):
#     """ Renders the page explaining security considerations in ML/DS/AI. """
#     context = {
#         'page_title': 'Security in ML, AI & Data Science',
#         'meta_description': "Understanding key security risks and considerations in machine learning, AI, and data science, including data privacy, model security, and infrastructure protection.",
#         'meta_keywords': "security, machine learning, data science, AI, data privacy, model security, adversarial attacks, infrastructure security",
#     }
#     return render(request, 'demos/data_security_demo.html', context=context)


# # --- Ethical Hacking Concepts Demo View (NEW) ---
# def ethical_hacking_demo_view(request):
#     """ Renders the page explaining ethical hacking concepts relevant to ML/DS/AI. """
#     context = {
#         'page_title': 'Demo: Ethical Hacking Mindset for AI/ML Security',
#         'meta_description': "Understanding how ethical hacking principles apply to securing data pipelines, machine learning models, and AI infrastructure against potential threats.",
#         'meta_keywords': "ethical hacking, security, machine learning, AI, data science, adversarial attacks, penetration testing, vulnerability",
#     }
#     return render(request, 'demos/ethical_hacking_demo.html', context=context)

# # --- Django to Heroku Deployment Guide View (NEW) ---
# def deploying_to_heroku_view(request):
#     """ Renders the page Django to Heroku Deployment Guide relevant to ML/DS/AI. """
#     context = {
#         'page_title': 'Demo: Django to Heroku Deployment Guide for AI/ML Security',
#         'meta_description': "Understanding how Django to Heroku Deployment Guide.",
#         'meta_keywords': "Django, Heroku, Deployment, Guide",
#     }
#     return render(request, 'demos/deploying_django_app_to_heroku.html', context=context)

# # --- Django to Render Deployment Guide View (NEW) ---
# def deploying_to_render_view(request):
#     """ Renders the page Django to Render Deployment Guide relevant to ML/DS/AI. """
#     context = {
#         'page_title': 'Demo: Django to Render Deployment Guide for AI/ML Security',
#         'meta_description': "Understanding how Django to Render Deployment Guide.",
#         'meta_keywords': "Django, Render, Deployment, Guide",
#     }
#     return render(request, 'demos/deploying_django_app_to_render.html', context=context)

# # --- Django to Python Anywhere Deployment Guide View (NEW) ---
# def deploying_to_python_anywhere_view(request):
#     """ Renders the page Django to Python Anywhere Deployment Guide relevant to ML/DS/AI. """
#     context = {
#         'page_title': 'Demo: Django to Python Anywhere Deployment Guide for AI/ML Security',
#         'meta_description': "Understanding how Django to Python Anywhere Deployment Guide.",
#         'meta_keywords': "Django, Python Anywhere, Deployment, Guide",
#     }
#     return render(request, 'demos/deploying_django_app_to_pythonanywhere.html', context=context)

# # --- Django to Google App Engine Deployment Guide View (NEW) ---
# def deploying_to_google_app_engine_view(request):
#     """ Renders the page Django to Google App Engine Deployment Guide relevant to ML/DS/AI. """
#     context = {
#         'page_title': 'Demo: Django to Google App Engine Deployment Guide for AI/ML Security',
#         'meta_description': "Understanding how Django to Google App Engine Deployment Guide.",
#         'meta_keywords': "Django, Google App Engine, Deployment, Guide",
#     }
#     return render(request, 'demos/deploying_django_app_to_google_app_engine.html', context=context)

# # --- Django to AWS Elastic Beanstalk Deployment Guide View (NEW) ---
# def deploying_to_aws_elastic_beanstalk_view(request):
#     """ Renders the page Django to AWS Elastic Beanstalk Deployment Guide relevant to ML/DS/AI. """
#     context = {
#         'page_title': 'Demo: Django to AWS Elastic Beanstalk Deployment Guide for AI/ML Security',
#         'meta_description': "Understanding how Django to AWS Elastic Beanstalk Deployment Guide.",
#         'meta_keywords': "Django, AWS Elastic Beanstalk, Deployment, Guide",
#     }
#     return render(request, 'demos/deploying_django_app_to_aws_elastic_beanstalk.html', context=context)

# # --- Django Deployment Options View (NEW) ---
# def deploying_options_view(request):
#     """ Renders the page Django Deployment Guide relevant to ML/DS/AI. """
#     context = {
#         'page_title': 'Demo: Django Deployment Guide for AI/ML Security',
#         'meta_description': "Understanding how Django Deployment Guide.",
#         'meta_keywords': "Django, Deployment, Options, Guide",
#     }
#     return render(request, 'demos/deploying_django_options.html', context=context)

# # --- Django Deployment Comparisons View (NEW) ---
# def deploying_comparisons_view(request):
#     """ Renders the page Django Deployment Comparisons Guide relevant to ML/DS/AI. """
#     context = {
#         'page_title': 'Demo: Django Deployment Comparisons Guide for AI/ML Security',
#         'meta_description': "Understanding Django Deployment Comparisons Guide.",
#         'meta_keywords': "Django, Deployment, Comparisons, Guide",
#     }
#     return render(request, 'demos/deploying_django_comparisons.html', context=context)


# # --- DRF Concepts Demo View (NEW) ---
# def drf_concepts_demo_view(request):
#     """ Renders the page explaining Django REST Framework for APIs. """
#     context = {
#         'page_title': 'Demo: Django REST Framework (DRF) for APIs',
#         'meta_description': "Understanding how Django REST Framework (DRF) builds powerful Web APIs, often used to serve machine learning model predictions or data science results.",
#         'meta_keywords': "Django REST Framework, DRF, API, REST API, machine learning, deployment, Python, Django",
#     }
#     return render(request, 'demos/drf_concepts_demo.html', context=context)


# # --- Colour Theme Demo View (NEW) ---
# def colour_theme_demo_view(request):
#     """ Renders the page explaining Colour Theme Demo . """
#     context = {
#         'page_title': 'Demo: Colour Theme Switcher Demo',
#         'meta_description': "Demonstration of dynamic theme switching using CSS and JavaScript.",
#         'meta_keywords': "theme switcher, css themes, javascript, dark mode, light mode, web design demo",
#     }
#     return render(request, 'demos/colour_theme_demo.html', context=context)


# # --- DevOps Demo View (NEW) ---
# def devops_demo_view(request):
#     """ Renders the page explaining DevOps. """
#     context = {
#         'page_title': 'DevOps & MLOps Concepts Demo',
#         'meta_description': "Learn about DevOps principles and how they apply to Machine Learning (MLOps) for efficient AI development and deployment.",
#         'meta_keywords': "DevOps, MLOps, CI/CD, Infrastructure as Code, IaC, Monitoring, Machine Learning Operations, AI Deployment",
#     }
#     return render(request, 'demos/devops_mlops_demo.html', context=context)


# # --- Data Engineering Demo View (NEW) ---
# def data_engineering_demo_view(request):
#     """ Renders the page explaining Data Engineering. """
#     context = {
#         'page_title': 'Data Engineering Concepts Demo',
#         'meta_description': "Learn about Data Engineering principles, practices, tools, and its crucial role in supporting Data Science and Machine Learning.",
#         'meta_keywords': "Data Engineering, ETL, ELT, Data Warehouse, Data Lake, Data Pipeline, Big Data, Spark, Airflow, SQL, Python",
#     }
#     return render(request, 'demos/data_engineering_demo.html', context=context)


# # --- Data Engineering Demo View (NEW) ---
# def ai_concepts_demo_view(request):
#     """ Renders the page explaining Data Engineering. """
#     context = {
#         'page_title': 'Artificial Intelligence Concepts Demo',
#         'meta_description': "An overview of Artificial Intelligence (AI), its relationship with Machine Learning and Deep Learning, key subfields, and core concepts.",
#         'meta_keywords': "Artificial Intelligence, AI, Machine Learning, ML, Deep Learning, DL, NLP, Computer Vision, Robotics, AI Concepts",
#     }
#     return render(request, 'demos/ai_concepts_demo.html', context=context)

# # --- Feature Engineering Demo View (NEW) ---
# def feature_engineering_demo_view(request):
#     """ Renders the page explaining Feature Engineering. """
#     context = {
#         'page_title': 'Feature Engineering Concepts Demo',
#         'meta_description': "Learn about Feature Engineering techniques used to improve Machine Learning model performance by transforming raw data into informative features.",
#         'meta_keywords': "Feature Engineering, Machine Learning, Data Science, Data Preprocessing, Feature Scaling, Encoding, Imputation, Feature Creation",
#     }
#     return render(request, 'demos/feature_engineering_demo.html', context=context)

# # --- Generative AI Demo View (NEW) ---
# def generative_ai_demo_view(request):
#     """ Renders the page explaining Generative AI. """
#     context = {
#         'page_title': 'Generative AI Concepts',
#         'meta_description': "Learn about Generative AI, including how it works, its applications in text, image, and code generation, and its role in modern AI.",
#         'meta_keywords': "Generative AI, GenAI, Large Language Models, LLM, Diffusion Models, GANs, VAEs, AI Content Generation, Machine Learning",
#     }
#     return render(request, 'demos/generative_ai_demo.html', context=context)

