# portfolio/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
import logging
# Ensure your logger is named consistently, e.g., using __name__
# or 'portfolio' if that's how you've configured it in settings.LOGGING
logger = logging.getLogger(__name__)
from .models import Project, Certificate, ColophonEntry # Assuming UserProfile is handled by context processor

# Import models from other apps safely
try:
    from blog.models import BlogPost
except ImportError:
    BlogPost = None
try:
    from skills.models import Skill, SkillCategory # SkillCategory might not be used directly in views but good to keep if Skill model needs it
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
import random # Import the random module

from django.utils import timezone
from .forms import ContactForm # Your ContactForm from forms.py
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.utils.text import Truncator
from datetime import datetime, timedelta # For timestamp check
import smtplib # For more specific SMTP exceptions

# Constants from your original file
FEATURED_ITEMS_COUNT = 6
RANDOM_DISPLAY_COUNT = 6

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

    featured_skills = []
    if Skill:
        try:
            all_skills = list(Skill.objects.select_related('category').all())
            if len(all_skills) > RANDOM_DISPLAY_COUNT:
                featured_skills = random.sample(all_skills, RANDOM_DISPLAY_COUNT)
            else:
                featured_skills = all_skills
        except Exception as e:
            logger.error(f"Error fetching skills: {e}", exc_info=True)

    featured_topics = []
    if ProjectTopic:
        try:
            all_topics = list(ProjectTopic.objects.all())
            if len(all_topics) > RANDOM_DISPLAY_COUNT:
                featured_topics = random.sample(all_topics, RANDOM_DISPLAY_COUNT)
            else:
                featured_topics = all_topics
        except Exception as e:
            logger.error(f"Error fetching topics: {e}", exc_info=True)

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


# If using django-ratelimit, you would import and use its decorator
# from django_ratelimit.decorators import ratelimit

# Example rate limit (uncomment and configure when ready):
# @ratelimit(key='ip', rate='5/h', block=True, method='POST')
def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Timestamp check
            form_load_time_str = form.cleaned_data.get('form_load_time')
            minimum_submission_time_seconds = 3 # Adjust as needed

            if form_load_time_str:
                try:
                    form_load_dt = datetime.fromisoformat(form_load_time_str)
                    if timezone.is_aware(timezone.now()) and timezone.is_naive(form_load_dt):
                        form_load_dt = timezone.make_aware(form_load_dt, timezone.get_default_timezone())

                    time_diff = timezone.now() - form_load_dt
                    if time_diff < timedelta(seconds=minimum_submission_time_seconds):
                        logger.warning(f"Form submitted too quickly ({time_diff.total_seconds()}s). Possible spam. IP: {request.META.get('REMOTE_ADDR')}")
                        messages.error(request, 'Submission failed. Please wait a moment and try again.')
                        return render(request, 'portfolio/contact_page.html', {'form': form, 'page_title': 'Contact Me'})
                except ValueError:
                    logger.error(f"Invalid form_load_time format: {form_load_time_str}. IP: {request.META.get('REMOTE_ADDR')}")
                    messages.error(request, 'There was an issue with your form submission. Please try again.')
                    return render(request, 'portfolio/contact_page.html', {'form': form, 'page_title': 'Contact Me'})
            else: # form_load_time_str is None or empty
                logger.warning(f"form_load_time missing from submission. IP: {request.META.get('REMOTE_ADDR')}")
                messages.error(request, 'Your form submission was incomplete or timed out. Please try again.')
                return render(request, 'portfolio/contact_page.html', {'form': form, 'page_title': 'Contact Me'})

            # If all checks above passed, proceed to process the valid submission
            name = form.cleaned_data['name']
            email_from = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message_body = form.cleaned_data['message']

            email_subject = f'Contact Form: {subject} (from {name})'
            full_message_content = (
                f"You have a new message from your portfolio contact form:\n\n"
                f"From: {name}\n"
                f"Email: {email_from}\n"
                f"Subject: {subject}\n"
                f"--------------------------------------------------\n"
                f"Message:\n{message_body}\n"
                f"--------------------------------------------------\n"
                f"Submitted at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
                f"Submitter IP: {request.META.get('REMOTE_ADDR')}\n"
            )

            try:
                if not settings.EMAIL_HOST_USER or not settings.DEFAULT_FROM_EMAIL:
                    logger.critical("Contact form submission failed: EMAIL_HOST_USER or DEFAULT_FROM_EMAIL not configured in settings.")
                    messages.error(request, 'Could not send message due to a server configuration error. Please contact the site administrator directly.')
                    return render(request, 'portfolio/contact_page.html', {'form': form, 'page_title': 'Contact Me'})
                else:
                    send_mail(
                        subject=email_subject,
                        message=full_message_content,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[settings.EMAIL_HOST_USER],
                        # reply_to=[email_from], # Optional
                        fail_silently=False,
                    )
                    logger.info(f"Contact form email sent successfully from {email_from} with subject: {subject}")
                    messages.success(request, 'Your message has been sent successfully! Thank you for reaching out.')
                    return redirect('portfolio:contact')
            except smtplib.SMTPException as e:
                logger.error(f"SMTP error sending contact form email: {e}", exc_info=True)
                messages.error(request, 'An SMTP error occurred while sending your message. Please try again later or contact us directly.')
                return render(request, 'portfolio/contact_page.html', {'form': form, 'page_title': 'Contact Me'})
            except Exception as e:
                logger.error(f"General error sending contact form email: {e}", exc_info=True)
                messages.error(request, 'An unexpected error occurred while sending your message. Please try again later.')
                return render(request, 'portfolio/contact_page.html', {'form': form, 'page_title': 'Contact Me'})
        else: # form.is_valid() is False
            logger.warning(f"Contact form validation failed. Errors: {form.errors.as_json()}. IP: {request.META.get('REMOTE_ADDR')}")
            
            is_honeypot_spam = False
            honeypot_field_errors = form.errors.get('honeypot')
            if honeypot_field_errors:
                for error in honeypot_field_errors:
                    # Check if the error object has a 'code' attribute and if it matches 'spam_honeypot'
                    if hasattr(error, 'code') and error.code == 'spam_honeypot':
                        is_honeypot_spam = True
                        break 
            
            if is_honeypot_spam:
                messages.error(request, 'Submission flagged as spam. Please try again.')
            # elif 'captcha' in form.errors: # Placeholder for when you add reCAPTCHA
            #     messages.error(request, 'Invalid reCAPTCHA. Please try again.')
            else:
                # Generic error if not honeypot spam (and not captcha, when added)
                messages.error(request, 'There were errors in your submission. Please check the fields below.')
            # The form with errors will be re-rendered by the return statement at the end of the view function.

    else: # GET request
        form = ContactForm()

    context = {
        'form': form,
        'page_title': 'Contact Me',
        'meta_description': "Get in touch with me. Send a message via the contact form.",
        'meta_keywords': "contact, email, message, get in touch, portfolio",
    }
    return render(request, 'portfolio/contact_page.html', context)


def project_detail(request, slug):
    """ View function for a single project detail page. """
    project = get_object_or_404(Project, slug=slug)
    # Prepare meta tags
    meta_description = Truncator(project.description).words(25, truncate='...')
    meta_keywords_list = [project.title.lower(), "project", "portfolio"]
    if Skill and hasattr(project, 'skills') and project.skills.exists(): # Check if Skill model and relationship are available
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
            messages.warning(request, f"Skill filter '{selected_skill_slug}' not found. Showing all projects.")
            selected_skill_slug = None # Reset to avoid confusion in template

    # Apply Topic Filter
    if selected_topic_slug and ProjectTopic:
        try:
            selected_topic = ProjectTopic.objects.get(slug=selected_topic_slug)
            projects_qs = projects_qs.filter(topics=selected_topic)
        except ProjectTopic.DoesNotExist:
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
    
    projects_found = Project.objects.none()
    # Ensure skills_found and topics_found are initialized correctly based on app existence
    skills_found = Skill.objects.none() if Skill else None 
    topics_found = ProjectTopic.objects.none() if ProjectTopic else None
    
    if query:
        # Search Projects
        projects_q_filter = Q(title__icontains=query) | Q(description__icontains=query)
        if Skill and hasattr(Project, 'skills'): # Check if skills relationship exists
            projects_q_filter |= Q(skills__name__icontains=query)
        if ProjectTopic and hasattr(Project, 'topics'): # Check if topics relationship exists
            projects_q_filter |= Q(topics__name__icontains=query)
        
        projects_found = Project.objects.filter(projects_q_filter).distinct().order_by('-date_created')


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

# Note: The original uploaded views.py had a 'colophon_view' which seemed to be a duplicate
# of 'colophon_page'. I'm keeping 'colophon_page' as it was more complete.
# If 'colophon_view' was intended to be different, it should be reviewed.

def accessibility_statement_view(request):
    context = {
        'page_title': 'Accessibility Statement',
        'meta_description': "Accessibility Statement for my portfolio website.", # Simplified
        'meta_keywords': "accessibility statement, portfolio, a11y", # Added a11y
    }
    return render(request, 'portfolio/accessibility_statement.html', context=context)


def terms_and_conditions_view(request):
    context = {
        'page_title': 'Terms and Conditions',
        'meta_description': "Terms and Conditions for using my portfolio website.", # Simplified
        'meta_keywords': "terms and conditions, legal, portfolio", # Simplified
    }
    return render(request, 'portfolio/terms_and_conditions.html', context=context)

def colophon_page(request):
    """
    View to display the Colophon page, detailing how the site was built.
    """
    entries = ColophonEntry.objects.all() 
    
    grouped_entries = OrderedDict()
    for category_key, category_display_name in ColophonEntry.CATEGORY_CHOICES:
        category_entries = [entry for entry in entries if entry.category == category_key]
        if category_entries: 
            grouped_entries[category_display_name] = category_entries
            
    context = {
        'page_title': "Colophon: How This Site Was Built",
        'meta_description': "Learn about the technologies, tools, and resources used to build this portfolio website.",
        'grouped_entries': grouped_entries,
    }
    return render(request, 'portfolio/colophon_page.html', context)
