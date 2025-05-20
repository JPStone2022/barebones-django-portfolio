# portfolio/urls.py (App-level URLs)

from django.urls import path, include
from . import views # Import views from the current directory

app_name = 'portfolio' # Namespace for URLs

urlpatterns = [
    # Home page
    path('', views.index, name='index'),
    # Project detail page
    path('project/<slug:slug>/', views.project_detail, name='project_detail'),
    # Add path for topic detail page
    #path('topic/<slug:topic_slug>/', views.topic_detail, name='topic_detail'),
    # Add path for certificates page
    path('certificates/', views.certificates_view, name='certificates'),
    # Add path for the all projects page
    path('projects/', views.all_projects_view, name='all_projects'),
    # Add path for the contact page view
    path('contact/', views.contact_view, name='contact'),
    # Add path for the detailed about me page
    path('about-me/', views.about_me_view, name='about_me'),
    # Add path for the CV page view
    path('cv/', views.cv_view, name='cv'),
    # Add path for the search results view
    path('search/', views.search_results_view, name='search_results'),
    # Add path for the Hire Me page view
    path('hire-me/', views.hire_me_view, name='hire_me'),
    # Add path for the Privacy Policy page view
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    # Add path for the Accessibility Statement page view
    path('accessibility/', views.accessibility_statement_view, name='accessibility'),
    # Add path for the Accessibility Statement page view
    path('terms-and-conditions/', views.terms_and_conditions_view, name='terms'),
    path('colophon/', views.colophon_page, name='colophon'),

]