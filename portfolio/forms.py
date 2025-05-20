# portfolio/forms.py

from django import forms
from django.utils import timezone
from django.utils.html import strip_tags # For stripping all HTML tags

# Needed for reCAPTCHA
# from django_recaptcha.fields import ReCaptchaField
# from django_recaptcha.widgets import ReCaptchaV2Checkbox # Or ReCaptchaV3, if preferred

class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400 dark:focus:ring-blue-400 dark:focus:border-blue-400',
            'placeholder': 'Your Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400 dark:focus:ring-blue-400 dark:focus:border-blue-400',
            'placeholder': 'Your Email Address'
        })
    )
    subject = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400 dark:focus:ring-blue-400 dark:focus:border-blue-400',
            'placeholder': 'Subject'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400 dark:focus:ring-blue-400 dark:focus:border-blue-400',
            'rows': 5,
            'placeholder': 'Your Message'
        })
    )

    # Honeypot field for basic spam protection
    honeypot = forms.CharField(required=False, widget=forms.HiddenInput, label="")

    # Timestamp field for another layer of basic spam protection
    form_load_time = forms.CharField(required=False, widget=forms.HiddenInput)

    # reCAPTCHA field
    # captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)
    # If you prefer reCAPTCHA v3, you would use:
    # captcha = ReCaptchaField(widget=ReCaptchaV3(action='contact_form_submission'))
    # And you'd need to handle the score in your view if using v3.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial value for form_load_time when the form is instantiated (typically in the GET request)
        if not self.is_bound: # Only set on initial form load, not on POST
            self.fields['form_load_time'].initial = timezone.now().isoformat()


    def clean_message(self):
        """
        Sanitize the message content to remove ALL HTML.
        """
        message = self.cleaned_data.get('message', '')
        # Strip all HTML tags for maximum security in a typical contact form message.
        cleaned_message = strip_tags(message)
        return cleaned_message

    def clean_honeypot(self):
        """
        Check the honeypot field. If it's filled, raise a validation error.
        This will prevent the form from validating if a bot fills in the hidden field.
        """
        data = self.cleaned_data['honeypot']
        if data:
            # This error won't typically be shown to the user if handled correctly in the view,
            # but it will mark the form as invalid.
            raise forms.ValidationError("Spam detected (honeypot).", code='spam_honeypot')
        return data
