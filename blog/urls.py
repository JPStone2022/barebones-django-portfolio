# blog/urls.py

from django.urls import path
from . import views

app_name = 'blog' # Namespace for blog URLs

urlpatterns = [
    path('', views.blog_post_list, name='blog_post_list'),
    path('<slug:slug>/', views.blog_post_detail, name='blog_post_detail'),
]