# recommendations/urls.py

from django.urls import path
from . import views

app_name = 'recommendations' # Namespace

urlpatterns = [
    path('', views.recommendation_list_view, name='recommendation_list'),
    # Add path for the detail view using the slug
    path('<slug:slug>/', views.recommendation_detail_view, name='recommendation_detail'),
]
