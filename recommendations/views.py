# recommendations/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from django.http import Http404 # Not explicitly used if get_object_or_404 is primary
from .models import RecommendedProduct # RecommendationSection is accessed via product.sections
# import markdown # REMOVED: No longer needed for direct conversion in view
import logging

logger = logging.getLogger(__name__) # Ensure logger is defined at module level

def recommendation_list_view(request):
    """ Displays a paginated list of all recommended products from the database. """
    all_recommendations_qs = RecommendedProduct.objects.all().order_by('order', 'name')
    error_message = None

    try:
        # Attempt to get the count to see if the DB query works at a basic level.
        all_recommendations_qs.count() 
    except Exception as e:
        logger.error(f"Error fetching recommendations from database: {e}", exc_info=True)
        all_recommendations_qs = RecommendedProduct.objects.none() # Empty queryset
        error_message = "Could not load recommendations data. Please check server logs."

    paginator = Paginator(all_recommendations_qs, 9) # Show 9 recommendations per page
    page_number = request.GET.get('page')
    recommendations_page_obj = None 

    try:
        recommendations_page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        recommendations_page_obj = paginator.page(1)
    except EmptyPage:
        recommendations_page_obj = paginator.page(paginator.num_pages)
    except Exception as e: 
        logger.error(f"Error during pagination of recommendations: {e}", exc_info=True)
        if paginator.count > 0: 
            recommendations_page_obj = paginator.page(1)
        else: 
            recommendations_page_obj = None 
        if not error_message: 
            error_message = "There was an issue displaying this page of recommendations."

    context = {
        'recommendations': recommendations_page_obj,
        'page_title': 'Recommendations',
        'meta_description': "A curated list of recommended books, tools, courses, and resources related to Machine Learning, AI, Data Science, and Software Development.",
        'meta_keywords': "recommendations, resources, books, tools, courses, machine learning, data science, AI, software development",
        'error_message': error_message
    }
    return render(request, 'recommendations/recommendation_list.html', context)

def recommendation_detail_view(request, slug):
    """
    Displays details for a single recommended product and its sections.
    Markdown will be processed in the template using the 'markdownify' filter.
    """
    product = get_object_or_404(RecommendedProduct, slug=slug)
    view_error_message = None # For errors specific to this view's processing after product is fetched

    # Raw Markdown fields from 'product' (e.g., product.main_description_md, product.short_description)
    # and its related 'sections' (e.g., section.section_content_markdown accessed via product.sections.all in template)
    # will be passed directly to the template via the 'product' object.
    # The |markdownify filter in the template will handle the conversion to HTML.

    context = {
        'product': product, # The product object itself, containing all raw Markdown fields
        'page_title': product.page_meta_title if product.page_meta_title else product.name,
        'meta_description': product.page_meta_description if product.page_meta_description else product.short_description,
        # Note: meta_description in the template (recommendation_detail.html) uses |markdownify|striptags,
        # so it's fine for product.page_meta_description or product.short_description to be Markdown.
        'meta_keywords': product.page_meta_keywords if product.page_meta_keywords else "recommendation, details",
        'error_message': view_error_message, 
    }
    return render(request, 'recommendations/recommendation_detail.html', context)
