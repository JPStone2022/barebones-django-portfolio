# skills/views.py

from django.shortcuts import render, get_object_or_404
from .models import Skill, SkillCategory

# Import Demo model safely
try:
    from demos.models import Demo
    DEMOS_APP_ENABLED = True
except ImportError:
    Demo = None
    DEMOS_APP_ENABLED = False


def skill_list(request):
    """ Displays skills grouped by category. """
    # Fetch categories with their related skills prefetched for efficiency
    categories = SkillCategory.objects.prefetch_related('skills').order_by('order', 'name')
    # Fetch skills without a category
    uncategorized_skills = Skill.objects.filter(category__isnull=True).order_by('order', 'name')

    context = {
        'categories': categories,
        'uncategorized_skills': uncategorized_skills,
        'page_title': 'Technical Skills',
    }
    return render(request, 'skills/skill_list.html', context)


def skill_detail(request, slug):
    """ Displays details for a single skill, related projects, and related demos. """
    # Prefetch related projects and their topics for efficiency
    skill = get_object_or_404(Skill.objects.prefetch_related('projects__topics'), slug=slug)
    related_projects = skill.projects.all() # Use related_name 'projects' from Project model

    # Fetch related demos using the related_name 'demos' from Demo model
    related_demos = None
    if DEMOS_APP_ENABLED and Demo and hasattr(skill, 'demos'): # Check if relationship exists
        related_demos = skill.demos.all()

    context = {
        'skill': skill,
        'projects': related_projects,
        'demos': related_demos, # Add demos to context
        'page_title': f"{skill.name} - Skill Details",
        # Add meta tags if desired
        'meta_description': f"Details about the skill {skill.name} and related projects/demos.",
        'meta_keywords': f"{skill.name}, skill, portfolio, project, demo",
    }   
    return render(request, 'skills/skill_detail.html', context=context)
