# demos/urls.py

from django.urls import path
from . import views

app_name = 'demos' # Namespace

urlpatterns = [
    # Add path for the list view (at the root of /demos/)
    path('', views.all_demos_list_view, name='all_demos_list'),
    

    path('image-classifier/', views.image_classification_view, name='image_classifier'),
    # Add path for sentiment analysis demo
    path('sentiment-analyzer/', views.sentiment_analysis_view, name='sentiment_analyzer'),

    # Add path for data analysis demo
    path('data-analysis/', views.data_analyser_view, name='data_analyser'),
    # Add path for data wrangling demo
    path('data-wrangler/', views.data_wrangling_view, name='data_wrangler'),
    # Add path for explainable AI demo
    path('explainable-ai/', views.explainable_ai_view, name='explainable_ai'),
    # Add path for causal inference demo
    path('causal-inference/', views.causal_inference_demo_view, name='causal_inference'),
    # Add path for optimization demo
    path('scipy-optimize/', views.optimization_demo_view, name='optimization_demo'),
    # path('generative-ai-demo/', views.generative_ai_demo_view, name='generative_ai_demo'),
    path('amazon-price-tracker/', views.amazon_price_tracker_view, name='amazon_price_tracker'),
    path('flight-deal-finder/', views.flight_deal_finder_view, name='flight_deal_finder'),
    path('concepts/<slug:demo_slug>/', views.generic_demo_view, name='generic_demo_detail'), # New generic view
    path('keras-nmt-demo/', views.keras_nmt_demo_demo_view, name='keras_nmt_demo'),
    #path('ml-charts-interactive/', views.static_ml_visualization, name='ml_charts_interactive'),
]
