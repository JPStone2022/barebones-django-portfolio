# accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts' # Namespace for URLs

urlpatterns = [
    # LoginView is typically handled by django.contrib.auth.urls in main urls.py
    # and will use our TailwindLoginView if configured correctly.
    # If you want an explicit path here for your custom login view:
    # path('login/', views.TailwindLoginView.as_view(), name='login'), 

    path('members/', views.members_page, name='members_page'),
    path('signup/', views.signup_view, name='signup'), # <<< ADD THIS LINE
]
