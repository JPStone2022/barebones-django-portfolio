# recommendations/context_processors.py

import logging # Import the logging module

# Import the model safely in case the app isn't always installed
try:
    from .models import RecommendedProduct
    RECOMMENDATIONS_APP_AVAILABLE = True
except ImportError:
    RECOMMENDATIONS_APP_AVAILABLE = False

# Get an instance of a logger
logger = logging.getLogger(__name__)

def recommendation_context(request):
    """
    Adds the count of recommended products to the template context.
    """
    count = 0
    if RECOMMENDATIONS_APP_AVAILABLE:
        try:
            # Get the count of products
            count = RecommendedProduct.objects.count()
        except Exception as e:
            # Handle potential database errors gracefully if needed
            logger.warning(f"Could not query RecommendedProduct count: {e}") # Changed print to logger.warning
            count = 0 # Default to 0 on error

    # Return a dictionary to add to the context
    return {'recommendation_count': count}
