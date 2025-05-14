# demos/forms.py
from django import forms

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
