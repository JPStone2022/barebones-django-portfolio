# topics/urls.py

from django.urls import path
from . import views

app_name = 'topics' # Namespace

urlpatterns = [
    # URL for the list of all topics
    path('', views.topic_list, name='topic_list'),
    # URL for a specific topic's detail page (uses slug)
    path('<slug:topic_slug>/', views.topic_detail, name='topic_detail'),
]
