# blog/views.py

from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import BlogPost

def blog_post_list(request):
    """
    Displays a paginated list of published blog posts, ordered by publication date.
    Only posts with status 'published' and a published_date in the past or present are shown.
    """
    # Get currently published posts, ordered by date
    all_posts_list = BlogPost.objects.filter(
        status='published',
        published_date__lte=timezone.now()  # Ensure only past or present published posts
    ).order_by('-published_date')

    # Define how many posts per page
    items_per_page = 5 # Adjust as needed

    paginator = Paginator(all_posts_list, items_per_page)
    page_number = request.GET.get('page')

    try:
        # Attempt to get the requested page
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page_obj = paginator.get_page(1)
    except EmptyPage:
        # If page is out of range (e.g., 9999), deliver last page of results.
        page_obj = paginator.get_page(paginator.num_pages)

    context = {
        'page_title': 'Blog',
        # Pass the page_obj to the template, which contains posts for the current page and pagination info
        'page_obj': page_obj,
        # For compatibility with templates that might still use 'posts' directly for the list of items on the page
        'posts': page_obj, 
    }
    return render(request, 'blog/blog_list.html', context)


def blog_post_detail(request, slug):
    """
    Displays a single blog post.
    Ensures that only published posts with a publication date in the past or present are accessible.
    """
    post = get_object_or_404(
        BlogPost,
        slug=slug,
        status='published',
        published_date__lte=timezone.now() # Important: only show published and past-dated posts
    )
    context = {
        'post': post,
        'page_title': post.title, # Use the post's title for the page title
        # Consider adding meta description and keywords from the post model if they exist
        # 'meta_description': post.meta_description if hasattr(post, 'meta_description') else post.content[:160],
        # 'meta_keywords': post.meta_keywords if hasattr(post, 'meta_keywords') else "blog, " + post.title,
    }
    return render(request, 'blog/blog_detail.html', context)
