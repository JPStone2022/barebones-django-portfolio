# blog/views.py

from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import BlogPost

# def blog_post_list(request):
#     """Displays a list of published blog posts."""
#     posts = BlogPost.objects.filter(
#         status='published',
#         published_date__lte=timezone.now()
#     ).order_by('-published_date')
#     context = {
#         'posts': posts,
#         'page_title': 'Blog',
#     }
#     return render(request, 'blog/blog_list.html', context)

def blog_post_list(request):
    # Get published posts, ordered by date
    all_posts_list = BlogPost.objects.order_by('-published_date')

    # Define how many posts per page
    items_per_page = 5 # Adjust as needed

    paginator = Paginator(all_posts_list, items_per_page)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    context = {
        'page_title': 'Blog',
        # Pass the page_obj to the template
        'page_obj': page_obj,
        # Keep 'posts' pointing to page_obj for template compatibility
        'posts': page_obj,
    }
    return render(request, 'blog/blog_list.html', context) # Adjust template path if needed


def blog_post_detail(request, slug):
    """Displays a single blog post."""
    post = get_object_or_404(
        BlogPost,
        slug=slug,
        status='published',
        published_date__lte=timezone.now()
    )
    context = {
        'post': post,
        'page_title': post.title,
    }
    return render(request, 'blog/blog_detail.html', context)