# demos/forms.py
from django import forms
from django.core.validators import RegexValidator

# Validator for IATA codes (3 uppercase letters)
iata_code_validator = RegexValidator(
    regex=r'^[A-Z]{3}$',
    message='Enter a valid 3-letter IATA airport code (e.g., LHR, JFK).'
)
class ImageUploadForm(forms.Form):
    image = forms.ImageField(
        label='Upload an Image',
        help_text='(JPEG, PNG, etc.)',
        widget=forms.ClearableFileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 dark:file:bg-blue-900 file:text-blue-700 dark:file:text-blue-300 hover:file:bg-blue-100 dark:hover:file:bg-blue-800 cursor-pointer border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none'
        })
    )

# New form for Sentiment Analysis
class SentimentAnalysisForm(forms.Form):
    text_input = forms.CharField(
        label='Enter Text for Analysis',
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400 transition-colors duration-300 ease-in-out',
            'rows': 5,
            'placeholder': 'Type or paste text here...'
        }),
        max_length=1000, # Limit input length
        required=True
    )

# New form for CSV Upload
class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='Upload CSV File',
        help_text='(Max size: 5MB, must contain headers)',
        widget=forms.ClearableFileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-green-50 dark:file:bg-green-900 file:text-green-700 dark:file:text-green-300 hover:file:bg-green-100 dark:hover:file:bg-green-800 cursor-pointer border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none',
            'accept': '.csv' # Suggest only CSV files
        })
    )
    # Optional: Add fields for user to select columns for analysis later
    # numerical_col = forms.CharField(label='Numerical Column for Histogram', max_length=100, required=False)
    # categorical_col = forms.CharField(label='Categorical Column for Bar Chart', max_length=100, required=False)

# New Form for Explainable AI Demo (Iris Features)
class ExplainableAIDemoForm(forms.Form):
    # Use DecimalField for precise float input
    sepal_length = forms.DecimalField(
        label='Sepal Length (cm)', min_value=0.1, max_value=10.0, decimal_places=1, initial=5.1,
        widget=forms.NumberInput(attrs={'step': '0.1', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-purple-500'})
    )
    sepal_width = forms.DecimalField(
        label='Sepal Width (cm)', min_value=0.1, max_value=10.0, decimal_places=1, initial=3.5,
        widget=forms.NumberInput(attrs={'step': '0.1', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-purple-500'})
    )
    petal_length = forms.DecimalField(
        label='Petal Length (cm)', min_value=0.1, max_value=10.0, decimal_places=1, initial=1.4,
        widget=forms.NumberInput(attrs={'step': '0.1', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-purple-500'})
    )
    petal_width = forms.DecimalField(
        label='Petal Width (cm)', min_value=0.1, max_value=10.0, decimal_places=1, initial=0.2,
        widget=forms.NumberInput(attrs={'step': '0.1', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-purple-500'})
    )


# # New Form for NLTK Demo
# class NltkDemoForm(forms.Form):
#     text_input = forms.CharField(
#         label='Enter a Sentence',
#         widget=forms.Textarea(attrs={
#             'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400 transition-colors duration-300 ease-in-out',
#             'rows': 3,
#             'placeholder': 'e.g., The quick brown fox jumps over the lazy dog.'
#         }),
#         max_length=500, # Limit input length
#         required=True
#     )

# New Form for Amazon Price Tracker Demo
class AmazonProductURLForm(forms.Form):
    """
    Form for users to submit an Amazon product URL and an optional target price.
    """
    product_url = forms.URLField(
        label="Amazon Product URL",
        required=True,
        widget=forms.URLInput(attrs={
            'class': 'w-full p-3 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-gray-100 transition-colors duration-300 ease-in-out',
            'placeholder': 'e.g., https://www.amazon.co.uk/your-product-link/dp/ASIN'
        })
    )
    target_price = forms.DecimalField(
        label="Target Price (£)",
        required=False, # Making it optional; if not provided, we can just display the current price
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'w-full p-3 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-gray-100 transition-colors duration-300 ease-in-out',
            'placeholder': 'e.g., 150.00 (Optional)'
        })
    )

    def clean_product_url(self):
        """
        Validates if the URL is from a recognized Amazon domain.
        """
        url = self.cleaned_data.get('product_url')
        if url:
            # Basic check for amazon domain. More robust parsing might be needed for various Amazon URL formats.
            if not ("amazon.co.uk" in url or "amazon.com" in url or "amazon.de" in url or "amazon.fr" in url or "amazon.es" in url or "amazon.it" in url):
                raise forms.ValidationError("Please enter a valid Amazon product URL.")
        return url

# New Form for Flight Deal Finder Demo
class FlightDealFinderForm(forms.Form):
    """
    Form for users to input origin, destination, and target price for finding flight deals.
    """
    origin_city_iata = forms.CharField(
        label="Origin City (IATA Code)",
        max_length=3,
        required=True,
        validators=[iata_code_validator],
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-gray-100 transition-colors duration-300 ease-in-out',
            'placeholder': 'e.g., LON, LHR, JFK'
        })
    )
    destination_city_iata = forms.CharField(
        label="Destination City (IATA Code)",
        max_length=3,
        required=True,
        validators=[iata_code_validator],
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-gray-100 transition-colors duration-300 ease-in-out',
            'placeholder': 'e.g., PAR, CDG, NYC'
        })
    )
    target_price = forms.DecimalField(
        label="Max Target Price (£)",
        required=True, # Make it required to have a comparison point
        min_value=1.00,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'w-full p-3 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-gray-100 transition-colors duration-300 ease-in-out',
            'placeholder': 'e.g., 100.00'
        })
    )

    def clean_origin_city_iata(self):
        return self.cleaned_data['origin_city_iata'].upper()

    def clean_destination_city_iata(self):
        return self.cleaned_data['destination_city_iata'].upper()

    def clean(self):
        cleaned_data = super().clean()
        origin = cleaned_data.get("origin_city_iata")
        destination = cleaned_data.get("destination_city_iata")

        if origin and destination and origin == destination:
            raise forms.ValidationError("Origin and Destination cities cannot be the same.")
        return cleaned_data
