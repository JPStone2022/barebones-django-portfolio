# portfolio/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
import logging
logger = logging.getLogger(__name__)
from .models import Project, Certificate, ColophonEntry

# Import models from other apps safely
try:
    from blog.models import BlogPost
except ImportError:
    BlogPost = None
try:
    from skills.models import Skill, SkillCategory
except ImportError:
    Skill, SkillCategory = None, None # type: ignore
try: 
    from recommendations.models import RecommendedProduct 
except ImportError: 
    RecommendedProduct = None
try: 
    from demos.models import Demo 
except ImportError: 
    Demo = None
try:
    from topics.models import ProjectTopic # Ensure this is imported
except ImportError:
    ProjectTopic = None

from collections import OrderedDict # To maintain category order if needed

from django.utils import timezone
from .forms import ContactForm
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q 
from django.utils.text import Truncator

FEATURED_ITEMS_COUNT = 6

def index(request):
    """ View function for the home page. """
    featured_projects = Project.objects.order_by('order', '-date_created')[:FEATURED_ITEMS_COUNT]
    featured_certificates = Certificate.objects.order_by('order', '-date_issued')[:FEATURED_ITEMS_COUNT]
    
    latest_blog_post = None
    if BlogPost:
        try:
            latest_blog_post = BlogPost.objects.filter(status='published', published_date__lte=timezone.now()).latest('published_date')
        except BlogPost.DoesNotExist:
            latest_blog_post = None
        except Exception as e:
            logger.error(f"Error fetching latest blog post: {e}", exc_info=True)
            latest_blog_post = None

    featured_recommendations = []
    if RecommendedProduct:
        try:
            featured_recommendations = RecommendedProduct.objects.order_by('order', 'name')[:FEATURED_ITEMS_COUNT]
        except Exception as e:
            logger.error(f"Error fetching featured recommendations: {e}", exc_info=True)

    featured_topics = []
    if ProjectTopic:
        try:
            featured_topics = ProjectTopic.objects.order_by('order', 'name')[:FEATURED_ITEMS_COUNT]
        except Exception as e:
            logger.error(f"Error fetching featured topics: {e}", exc_info=True)

    featured_skills = []
    if Skill:
        try:
            # Example: Fetch top skills by order, perhaps from a specific category or all
            featured_skills = Skill.objects.select_related('category').order_by('category__order', 'category__name', 'order', 'name')[:FEATURED_ITEMS_COUNT]
        except Exception as e:
            logger.error(f"Error fetching featured skills: {e}", exc_info=True)

    featured_demos = []
    if Demo:
        try:
            featured_demos = Demo.objects.filter(is_published=True, is_featured=True).order_by('order', 'title')[:FEATURED_ITEMS_COUNT]
        except Exception as e:
            logger.error(f"Error fetching featured demos: {e}", exc_info=True)

    context = {
        'featured_projects': featured_projects,
        'featured_certificates': featured_certificates,
        'latest_blog_post': latest_blog_post,
        'featured_recommendations': featured_recommendations,
        'featured_topics': featured_topics,
        'featured_skills': featured_skills,
        'featured_demos': featured_demos,
    }
    return render(request, 'portfolio/index.html', context)

def project_detail(request, slug):
    """ View function for a single project detail page. """
    project = get_object_or_404(Project, slug=slug)
    # Prepare meta tags
    meta_description = Truncator(project.description).words(25, truncate='...')
    meta_keywords_list = [project.title.lower(), "project", "portfolio"]
    if Skill and project.skills.exists(): # Check if Skill model is available
        meta_keywords_list.extend([skill.name.lower() for skill in project.skills.all()[:3]]) # Add first 3 skills
    
    context = {
        'project': project,
        'page_title': project.title,
        'meta_description': meta_description,
        'meta_keywords': ", ".join(list(set(meta_keywords_list))), # Unique keywords
    }
    return render(request, 'portfolio/project_detail.html', context)


def certificates_view(request):
    """ View function for the certificates page. """
    certificates = Certificate.objects.order_by('order', '-date_issued')
    context = {
        'certificates': certificates,
        'page_title': 'Certificates & Qualifications',
        'meta_description': "A list of professional certificates and qualifications.",
        'meta_keywords': "certificates, qualifications, professional development, learning",
    }
    return render(request, 'portfolio/certificates.html', context)


def all_projects_view(request):
    """ View function for the page listing all projects with filtering and sorting. """
    projects_qs = Project.objects.all() # Start with all projects
    
    selected_skill_slug = request.GET.get('skill', None)
    selected_topic_slug = request.GET.get('topic', None)
    current_sort = request.GET.get('sort', '-date_created') # Default sort

    skills_list = []
    if Skill:
        skills_list = Skill.objects.all().order_by('name')
    
    topics_list = []
    if ProjectTopic:
        topics_list = ProjectTopic.objects.all().order_by('name')

    # Apply Skill Filter
    if selected_skill_slug and Skill:
        try:
            selected_skill = Skill.objects.get(slug=selected_skill_slug)
            projects_qs = projects_qs.filter(skills=selected_skill)
        except Skill.DoesNotExist:
            # FIX: Add message if skill filter is invalid
            messages.warning(request, f"Skill filter '{selected_skill_slug}' not found. Showing all projects.")
            selected_skill_slug = None # Reset to avoid confusion in template

    # Apply Topic Filter
    if selected_topic_slug and ProjectTopic:
        try:
            selected_topic = ProjectTopic.objects.get(slug=selected_topic_slug)
            projects_qs = projects_qs.filter(topics=selected_topic)
        except ProjectTopic.DoesNotExist:
            # FIX: Add message if topic filter is invalid
            messages.warning(request, f"Topic filter '{selected_topic_slug}' not found. Showing all projects.")
            selected_topic_slug = None # Reset

    # Apply Sorting
    valid_sort_options = ['date_created', '-date_created', 'title', '-title', 'order', '-order']
    if current_sort in valid_sort_options:
        projects_qs = projects_qs.order_by(current_sort)
    else:
        projects_qs = projects_qs.order_by('-date_created') # Fallback to default sort

    context = {
        'projects': projects_qs, # Pass the filtered and sorted queryset
        'skills_list': skills_list,
        'topics_list': topics_list,
        'selected_skill_slug': selected_skill_slug,
        'selected_topic_slug': selected_topic_slug,
        'current_sort': current_sort,
        'page_title': 'All Projects',
        'meta_description': "Browse all projects, filter by skill or topic, and sort by preference.",
        'meta_keywords': "all projects, portfolio, filter projects, sort projects, skills, topics",
    }
    return render(request, 'portfolio/all_projects.html', context)


def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Anti-spam: Check honeypot field
            if form.cleaned_data.get('honeypot'):
                messages.error(request, 'Spam detected.') # Or just ignore
                return redirect('portfolio:contact') # Or render with error

            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message_body = form.cleaned_data['message']
            
            full_message = f"Message from: {name} ({email})\n\nSubject: {subject}\n\n{message_body}"
            
            try:
                if not settings.EMAIL_HOST_USER: # Check if recipient email is configured
                    logger.error("Contact form submission failed: EMAIL_HOST_USER not configured.")
                    messages.error(request, 'Could not send message. Server configuration error.')
                else:
                    send_mail(
                        f'Contact Form: {subject}',
                        full_message,
                        settings.DEFAULT_FROM_EMAIL, # Sender's email (from settings)
                        [settings.EMAIL_HOST_USER], # Your recipient email address
                        fail_silently=False,
                    )
                    messages.success(request, 'Message sent successfully! Thank you.')
                    return redirect('portfolio:contact') # Redirect to clear form
            except Exception as e:
                logger.error(f"Email sending failed: {e}", exc_info=True)
                messages.error(request, 'An error occurred while sending your message. Please try again later.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm()

    context = {
        'form': form,
        'page_title': 'Contact Me',
        'meta_description': "Get in touch with me. Send a message via the contact form.",
        'meta_keywords': "contact, email, message, get in touch, portfolio",
    }
    return render(request, 'portfolio/contact_page.html', context)

def about_me_view(request):
    context = {
        'page_title': 'About Me',
        'meta_description': "Learn more about me, my background, skills, and experience in machine learning and AI.",
        'meta_keywords': "about me, portfolio, machine learning, AI, data science, biography",
    }
    return render(request, 'portfolio/about_me_page.html', context=context)

def cv_view(request):
    context = {
        'page_title': 'Curriculum Vitae (CV)',
        'meta_description': "View my Curriculum Vitae (CV) detailing his professional experience, education, and skills.",
        'meta_keywords': "CV, curriculum vitae, resume, experience, education, skills",
    }
    return render(request, 'portfolio/cv_page.html', context=context)

def search_results_view(request):
    query = request.GET.get('q', '')
    
    # FIX: Initialize to empty querysets if no query
    projects_found = Project.objects.none()
    skills_found = Skill.objects.none() if Skill else Skill # type: ignore
    topics_found = ProjectTopic.objects.none() if ProjectTopic else ProjectTopic # type: ignore
    
    if query:
        # Search Projects
        projects_found = Project.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(skills__name__icontains=query) | # Search by related skill names
            Q(topics__name__icontains=query)   # Search by related topic names
        ).distinct().order_by('-date_created')

        # Search Skills (if Skill model is available)
        if Skill:
            skills_found = Skill.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query) # Search by category name
            ).distinct().select_related('category').order_by('name')

        # Search Topics (if ProjectTopic model is available)
        if ProjectTopic:
            topics_found = ProjectTopic.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            ).distinct().order_by('name')
            
    context = {
        'query': query,
        'projects': projects_found,
        'skills': skills_found,
        'topics': topics_found,
        'page_title': f'Search Results for "{query}"' if query else 'Search',
        'meta_description': f"Search results for '{query}' in projects, skills, and topics." if query else "Search the portfolio content.",
        'meta_keywords': f"search, results, {query.lower() if query else ''}, portfolio",
    }
    return render(request, 'portfolio/search_results.html', context)


def hire_me_view(request):
    context = {
        'page_title': 'Hire Me - Services & Availability',
        'meta_description': "Information about my availability for freelance projects, consulting, or full-time roles in Machine Learning, AI, and Data Science.",
        'meta_keywords': "hire me, freelance, consulting, services, machine learning, AI, data science, availability",
    }
    return render(request, 'portfolio/hire_me_page.html', context=context)


def privacy_policy_view(request):
    context = {
        'page_title': 'Privacy Policy',
        'meta_description': "Privacy Policy for my portfolio website, detailing how user data is handled.",
        'meta_keywords': "privacy policy, data protection, user data, portfolio",
    }
    return render(request, 'portfolio/privacy_policy.html', context=context)

def colophon_view(request):
    context = {
        'page_title': 'Colophon: How This Site Was Built',
        'meta_description': "Learn about the technologies and process used to build this Django portfolio website.",
        'meta_keywords': "colophon, portfolio, django, python, tailwind css, web development, site build",
    }
    return render(request, 'portfolio/colophon.html', context=context)


def accessibility_statement_view(request):
    context = {
        'page_title': 'Accessibility Statement',
        'meta_description': "Accessibility Statement for my portfolio website, detailing how user data is handled.",
        'meta_keywords': "accessibility statement, data protection, user data, portfolio",

    }
    return render(request, 'portfolio/accessibility_statement.html', context=context)


def terms_and_conditions_view(request):
    context = {
        'page_title': 'Terms and Conditions',
        'meta_description': "Terms and Conditions for my portfolio website, detailing how user data is handled.",
        'meta_keywords': "terms and conditions, data protection, user data, portfolio",

    }
    return render(request, 'portfolio/terms_and_conditions.html', context=context)

def colophon_page(request):
    """
    View to display the Colophon page, detailing how the site was built.
    """
    # Fetch all colophon entries, ordered by category and then by custom order
    entries = ColophonEntry.objects.all() 
    
    # Group entries by category for display in the template
    # Uses the display name from CATEGORY_CHOICES
    grouped_entries = OrderedDict()
    # Get the display names for categories to ensure consistent ordering if possible
    # This relies on the order in CATEGORY_CHOICES in the model
    category_display_order = [choice[1] for choice in ColophonEntry.CATEGORY_CHOICES]
    
    for category_key, category_display_name in ColophonEntry.CATEGORY_CHOICES:
        category_entries = [entry for entry in entries if entry.category == category_key]
        if category_entries: # Only add category if there are entries for it
            grouped_entries[category_display_name] = category_entries
            
    # Add any entries whose category might not be in CATEGORY_CHOICES (should not happen if data is clean)
    # This part is more for robustness if categories in DB don't match choices.
    # current_categories_in_grouped = {entry.category for entries_list in grouped_entries.values() for entry in entries_list}
    # for entry in entries:
    #     if entry.category not in current_categories_in_grouped:
    #         category_display_name = entry.get_category_display() # Get display name
    #         if category_display_name not in grouped_entries:
    #             grouped_entries[category_display_name] = []
    #         grouped_entries[category_display_name].append(entry)


    context = {
        'page_title': "Colophon: How This Site Was Built",
        'meta_description': "Learn about the technologies, tools, and resources used to build this portfolio website.",
        # user_profile is likely already added by your context processor
        'grouped_entries': grouped_entries,
    }
    return render(request, 'portfolio/colophon_page.html', context) # Ensure template path is correct
