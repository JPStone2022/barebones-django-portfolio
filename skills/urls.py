# skills/urls.py

from django.urls import path
from . import views

app_name = 'skills' # Namespace

urlpatterns = [
    path('', views.skill_list, name='skill_list'), # List page at /skills/
    path('<slug:slug>/', views.skill_detail, name='skill_detail'), # Detail page
]