# recommendations/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404 # Import Http404 for explicit raising if needed, though get_object_or_404 handles it.
from .models import RecommendedProduct, RecommendationSection
import markdown # For rendering Markdown to HTML
import logging

logger = logging.getLogger(__name__)

def recommendation_list_view(request):
    """ Displays a paginated list of all recommended products from the database. """
    all_recommendations_qs = RecommendedProduct.objects.all().order_by('order', 'name')
    error_message = None # Initialize error_message

    # It's generally better to let database errors propagate if they are unexpected
    # or handle them more specifically if they are anticipated (e.g., connection issues).
    # For this view, if .all() fails, it's likely a server/DB setup issue.
    # However, if we want to ensure the page always tries to render:
    try:
        # This query is already above, but if we were to wrap it:
        # all_recommendations_qs = RecommendedProduct.objects.all().order_by('order', 'name')
        pass # Assuming the query above succeeded or is handled by Django's default error pages for major DB issues.
    except Exception as e:
        logger.error(f"Error fetching recommendations from database: {e}")
        all_recommendations_qs = RecommendedProduct.objects.none() # Empty queryset
        error_message = "Could not load recommendations data. Please check server logs."
        # If error_message is set, we'll use it in the context below.

    paginator = Paginator(all_recommendations_qs, 9) # Show 9 recommendations per page
    page_number = request.GET.get('page')
    try:
        recommendations_page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        recommendations_page_obj = paginator.page(1)
    except EmptyPage:
        recommendations_page_obj = paginator.page(paginator.num_pages)
    except Exception as e: # Catch other unexpected paginator errors
        logger.error(f"Error during pagination of recommendations: {e}")
        recommendations_page_obj = paginator.page(1) # Default to page 1
        if not error_message: # Avoid overwriting a DB error message
            error_message = "There was an issue displaying this page of recommendations."


    context = {
        'recommendations': recommendations_page_obj, # Pass the page object
        'page_title': 'Recommendations',
        'meta_description': "A curated list of recommended books, tools, courses, and resources related to Machine Learning, AI, Data Science, and Software Development.",
        'meta_keywords': "recommendations, resources, books, tools, courses, machine learning, data science, AI, software development",
        'error_message': error_message # Pass error message to template
    }
    return render(request, 'recommendations/recommendation_list.html', context)

def recommendation_detail_view(request, slug):
    """
    Displays details for a single recommended product and its sections.
    If the product is not found, get_object_or_404 will raise Http404.
    """
    product = get_object_or_404(RecommendedProduct, slug=slug)
    
    # Initialize variables for content processing
    main_description_html = ""
    processed_sections = []
    view_error_message = None # Specific error message for this view's processing

    try:
        sections = product.sections.all().order_by('section_order')

        if product.main_description_md:
            try:
                main_description_html = markdown.markdown(
                    product.main_description_md, 
                    extensions=['fenced_code', 'codehilite', 'tables']
                )
            except Exception as md_e:
                logger.error(f"Markdown processing error for product '{product.slug}' main_description_md: {md_e}")
                # FIX: Align error message with test expectation
                main_description_html = "<p><em>Error rendering content.</em></p>"
                if not view_error_message: view_error_message = "Could not fully load recommendation details."


        for section in sections:
            content_html = ""
            if section.section_content_markdown:
                try:
                    content_html = markdown.markdown(
                        section.section_content_markdown, 
                        extensions=['fenced_code', 'codehilite', 'tables']
                    )
                except Exception as md_e:
                    logger.error(f"Markdown processing error for section '{section.id}' of product '{product.slug}': {md_e}")
                    # FIX: Align error message with test expectation
                    content_html = "<p><em>Error rendering section content.</em></p>"
                    if not view_error_message: view_error_message = "Could not fully load recommendation details."
            
            processed_sections.append({
                'section_title': section.section_title,
                'section_content_html': content_html,
            })

    except Exception as e:
        # This catches errors during section fetching or other unexpected issues *after* product is found.
        logger.error(f"Error processing details (e.g., sections) for product '{product.slug}': {e}")
        # Product is available, but sections or other parts might have failed.
        # Reset parts that might be in an inconsistent state.
        processed_sections = [] 
        if not main_description_html and not product.main_description_md: # If main_description_html wasn't processed due to this error
             main_description_html = "<p><em>Could not load detailed content.</em></p>"
        if not view_error_message:
            view_error_message = "There was an issue loading all details for this recommendation."

    context = {
        'product': product, # Product is guaranteed to be valid here due to get_object_or_404
        'main_description_html': main_description_html,
        'sections': processed_sections,
        'page_title': product.page_meta_title if product.page_meta_title else product.name,
        'meta_description': product.page_meta_description if product.page_meta_description else product.short_description,
        'meta_keywords': product.page_meta_keywords if product.page_meta_keywords else "recommendation, details",
        'error_message': view_error_message, # Pass any processing error message
    }
    return render(request, 'recommendations/recommendation_detail.html', context)
