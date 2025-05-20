# accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm # Add UserCreationForm
from django.contrib.auth.models import User # Needed to customize UserCreationForm fields if necessary

# Common Tailwind CSS classes for form inputs
TAILWIND_INPUT_CLASSES = 'w-full px-4 py-3 mb-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400 dark:focus:ring-blue-400 dark:focus:border-blue-400 transition-colors duration-300 ease-in-out'
TAILWIND_ERROR_CLASSES = 'text-red-500 dark:text-red-400 text-xs mt-1'

class TailwindAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form styled with Tailwind CSS classes
    to match the portfolio's design.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': 'Username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': TAILWIND_INPUT_CLASSES.replace('mb-1', 'mb-3'), # Adjust margin for password field
            'placeholder': 'Password'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove labels if placeholders are sufficient, or style them if needed
        self.fields['username'].label = False
        self.fields['password'].label = False


class TailwindUserCreationForm(UserCreationForm):
    """
    Custom user creation (signup) form styled with Tailwind CSS classes.
    """
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES, 'placeholder': 'Choose a username'})
    )
    # Django's UserCreationForm handles password1 and password2 automatically.
    # We just need to style them.
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT_CLASSES, 'placeholder': 'Enter password'})
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT_CLASSES, 'placeholder': 'Confirm password'})
    )

    class Meta(UserCreationForm.Meta):
        model = User # Use Django's default User model
        fields = ('username',) # Add other fields like 'email' if you want them on the signup form

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove default help texts or style them if you prefer
        self.fields['password2'].help_text = None # Removes the default "Enter the same password as before..."
        # You can add custom help text or styling here if needed

    # You can add clean methods for additional validation if required
    # For example, to ensure username is not 'admin' or similar
    # def clean_username(self):
    #     username = self.cleaned_data.get('username')
    #     if username and username.lower() == 'admin':
    #         raise forms.ValidationError("This username is not allowed.")
    #     return username
