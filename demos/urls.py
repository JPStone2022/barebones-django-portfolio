# demos/urls.py

from django.urls import path
from . import views

app_name = 'demos' # Namespace

urlpatterns = [
    # Add path for the list view (at the root of /demos/)
    path('', views.all_demos_list_view, name='all_demos_list'),
    
    path('image-classifier/', views.image_classification_view, name='image_classifier'),
    # Add paths for other demos here later
    # Add path for sentiment analysis demo
    path('sentiment-analyzer/', views.sentiment_analysis_view, name='sentiment_analyzer'),
    # Add path for data analysis demo
    path('data-analysis/', views.data_analyser_view, name='data_analyser'),
    # Add path for data wrangling demo
    path('data-wrangler/', views.data_wrangling_view, name='data_wrangler'),
    # Add path for explainable AI demo
    path('explainable-ai/', views.explainable_ai_view, name='explainable_ai'),
    # Add path for Flask API demo explanation page
    #path('flask-ml-api/', views.flask_api_demo_view, name='flask_api_demo'),
    # Add path for Django concepts demo explanation page
    #path('django-concepts/', views.django_concepts_demo_view, name='django_concepts_demo'),
    # Add path for causal inference demo
    path('causal-inference/', views.causal_inference_demo_view, name='causal_inference'),
    # Add path for optimization demo
    path('scipy-optimize/', views.optimization_demo_view, name='optimization_demo'),
    # Add path for Django security demo explanation page
    #path('django-security/', views.django_security_demo_view, name='django_security_demo'),
    # Add path for Django testing demo explanation page
    #path('django-testing/', views.django_testing_demo_view, name='django_testing_demo'),
    # Add path for AI tools explanation page
    #path('ai-tools-dev/', views.ai_tools_demo_view, name='ai_tools_demo'),
    # Add path for Python concepts demo explanation page
    #path('python-concepts/', views.python_concepts_demo_view, name='python_concepts_demo'),
    # Add path for R concepts demo explanation page
    #path('r-concepts/', views.r_concepts_demo_view, name='r_concepts_demo'),
    # Add path for Go concepts demo explanation page
    #path('go-concepts/', views.go_concepts_demo_view, name='go_concepts_demo'),
    # Add path for Scala concepts demo explanation page
    # path('scala-concepts/', views.scala_concepts_demo_view, name='scala_concepts_demo'),
    # # Add path for Java concepts demo explanation page
    # path('java-concepts/', views.java_concepts_demo_view, name='java_concepts_demo'),
    # # Add path for language comparison demo page
    # path('language-comparison/', views.language_comparison_demo_view, name='language_comparison_demo'),
    # # Add path for Ruby concepts demo explanation page
    # path('ruby-concepts/', views.ruby_concepts_demo_view, name='ruby_concepts_demo'),
    # # Add path for OOP concepts demo explanation page
    # path('oop-concepts/', views.oop_concepts_demo_view, name='oop_concepts_demo'),
    # # Add path for Kotlin concepts demo explanation page
    # path('kotlin-concepts/', views.kotlin_concepts_demo_view, name='kotlin_concepts_demo'),
    # # Add path for Jupyter demo explanation page
    # path('jupyter-notebooks/', views.jupyter_demo_view, name='jupyter_demo'),
    # # Add path for PySpark concepts demo explanation page
    # path('pyspark-concepts/', views.pyspark_concepts_demo_view, name='pyspark_concepts_demo'),
    # # Add path for PyTorch concepts demo explanation page
    # path('pytorch-concepts/', views.pytorch_concepts_demo_view, name='pytorch_concepts_demo'),
    # # Add path for Data Security demo explanation page
    # path('data-security/', views.data_security_demo_view, name='data_security_demo'),
    # # Add path for Ethical Hacking concepts demo explanation page
    # path('ethical-hacking-ml/', views.ethical_hacking_demo_view, name='ethical_hacking_demo'),
    # # Add path for Ethical Hacking concepts demo explanation page
    # path('deploy-to-heroku/', views.deploying_to_heroku_view, name='deploying_django_app_to_heroku'),
    # # Add path for Ethical Hacking concepts demo explanation page
    # path('deploy-to-render/', views.deploying_to_render_view, name='deploying_django_app_to_render'),
    # # Add path for Ethical Hacking concepts demo explanation page
    # path('deploy-to-python-anywhere/', views.deploying_to_python_anywhere_view, name='deploying_django_app_to_pythonanywhere'),
    # # Add path for Ethical Hacking concepts demo explanation page
    # path('deploy-to-google-app-engine/', views.deploying_to_google_app_engine_view, name='deploying_django_app_to_google_app_engine'),
    # # Add path for Ethical Hacking concepts demo explanation page
    # path('deploy-to-aws-elastic-beanstalk/', views.deploying_to_aws_elastic_beanstalk_view, name='deploying_django_app_to_aws_elastic_beanstalk'),
    # # Add path for Ethical Hacking concepts demo explanation page
    # path('django-deployment-options/', views.deploying_options_view, name='deploying_django_options'),
    # # Add path for Ethical Hacking concepts demo explanation page
    # path('django-deployment-comparisons/', views.deploying_comparisons_view, name='deploying_django_comparisons'),
    # # Add path for DRF concepts demo explanation page
    # path('drf-concepts/', views.drf_concepts_demo_view, name='drf_concepts_demo'),
    # # Add path for DRF concepts demo explanation page
    # path('colour-theme-demo/', views.colour_theme_demo_view, name='colour_theme_demo'),
    # # Add path for DevOps demo explanation page
    # path('devops-demo/', views.devops_demo_view, name='devops_mlops_demo'),
    # # Add path for Data Engineering demo explanation page
    # path('data-engineering-demo/', views.data_engineering_demo_view, name='data_engineering_demo'),
    # # Add path for AI Concepts demo explanation page
    # path('ai-concepts-demo/', views.ai_concepts_demo_view, name='ai_concepts_demo'),
    # # Add path for Feature Engineering demo explanation page
    # path('feature-engineering-demo/', views.feature_engineering_demo_view, name='feature_engineering_demo'),
    # # Add path for Generative AI demo explanation page
    # path('generative-ai-demo/', views.generative_ai_demo_view, name='generative_ai_demo'),
    path('concepts/<slug:demo_slug>/', views.generic_demo_view, name='generic_demo_detail'), # New generic view
    path('keras-nmt-demo/', views.keras_nmt_demo_demo_view, name='keras_nmt_demo'),
    #path('ml-charts-interactive/', views.static_ml_visualization, name='ml_charts_interactive'),
]
