# portfolio/context_processors.py
import logging # Import the logging module
from .models import UserProfile

# Get an instance of a logger for this module
# Using __name__ is a common practice as it names the logger after the module (e.g., "portfolio.context_processors")
logger = logging.getLogger(__name__)

def user_profile_context(request):
    """
    Adds the UserProfile instance to the context for all templates.
    Uses logging for errors and warnings.
    """
    profile = None
    try:
        # Attempt to fetch the main profile using a specific identifier
        profile = UserProfile.objects.filter(site_identifier="main_profile").first()
        
        # If the main profile isn't found, try to get any existing profile as a fallback
        if not profile:
            profile = UserProfile.objects.first()
            # If still no profile exists at all, log a warning.
            if not profile:
                logger.warning(
                    "No UserProfile found in the database (neither 'main_profile' nor any other). "
                    "The 'user_profile' context variable will be None."
                )
                
    except UserProfile.DoesNotExist:
        # This specific exception might not be strictly necessary if .first() is used,
        # as .first() returns None if no object is found, rather than raising DoesNotExist.
        # However, keeping it can be useful if the query logic changes.
        logger.warning(
            "UserProfile.DoesNotExist caught (this might be unexpected if using .first()). "
            "No UserProfile available for context."
        )
        profile = None
        
    except Exception as e:
        # Catch any other potential errors during the database query or processing
        # Log the error with level ERROR, including traceback information (exc_info=True)
        logger.error(
            f"An unexpected error occurred while fetching UserProfile for context: {e}",
            exc_info=True  # This includes the full traceback in your logs
        )
        profile = None # Ensure profile is None if an error occurs
        
    return {'user_profile': profile}
