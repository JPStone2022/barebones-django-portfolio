# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import views as auth_views, login as auth_login
from .forms import TailwindAuthenticationForm, TailwindUserCreationForm # Make sure these are correctly imported
from django.urls import reverse_lazy
import datetime # Import datetime for formatting last_login

# Login view using the custom form
class TailwindLoginView(auth_views.LoginView):
    authentication_form = TailwindAuthenticationForm
    template_name = 'registration/login.html'

@login_required
def members_page(request):
    """
    Displays a page with enhanced interactive content for logged-in users.
    Correctly handles session-based visit counting with Post/Redirect/Get.
    """
    # Handle the counter interaction first if it's a POST request
    if request.method == 'POST':
        if 'increment_button' in request.POST:
            request.session['member_counter'] = request.session.get('member_counter', 0) + 1
            messages.success(request, f"Counter incremented! Current value: {request.session['member_counter']}")
        elif 'reset_button' in request.POST:
            request.session['member_counter'] = 0
            messages.success(request, "Counter reset!")
        # Redirect to the same page using GET to prevent form re-submission on refresh.
        # The visit_count will be updated on the subsequent GET request.
        return redirect('accounts:members_page')

    # This part now only runs for GET requests (initial load or after the redirect from POST)
    # Increment visit count for the members page in the current session
    visit_count = request.session.get('members_page_visits', 0) + 1
    request.session['members_page_visits'] = visit_count
    
    counter_value = request.session.get('member_counter', 0)
    
    # Get user-specific information
    user_email = request.user.email if request.user.email else "Not provided"
    last_login_time = request.user.last_login 

    context = {
        'username': request.user.username,
        'user_email': user_email,
        'last_login_time': last_login_time,
        'counter_value': counter_value,
        'visit_count': visit_count, # This will now be correctly incremented once per "effective" page load
        'page_title': 'Members Area',
        'meta_description': "A private area for logged-in members with exclusive content.",
    }
    return render(request, 'accounts/members_page.html', context)


def signup_view(request):
    """
    Handles user registration.
    """
    if request.user.is_authenticated:
        # If user is already logged in, redirect them from signup page
        return redirect('accounts:members_page')

    if request.method == 'POST':
        form = TailwindUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save() # Create the new user
            auth_login(request, user) # Log the user in immediately after signup
            messages.success(request, 'Account created successfully! You are now logged in.')
            # Redirect to the members page or another appropriate page
            return redirect('accounts:members_page') 
        else:
            # Form is invalid, errors will be displayed in the template
            messages.error(request, 'Please correct the errors below to sign up.')
    else: # GET request
        form = TailwindUserCreationForm()
    
    context = {
        'form': form,
        'page_title': 'Sign Up',
        'meta_description': "Create a new account to access member features.",
    }
    return render(request, 'registration/signup.html', context)
