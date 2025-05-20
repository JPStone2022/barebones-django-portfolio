# demos/tests.py

import os
import shutil
import uuid # Required for pagination test
import io
import base64
from unittest.mock import patch, MagicMock

# Import pandas
import pandas as pd
import numpy as np
from io import StringIO # For creating in-memory CSV files

from django.test import TestCase, Client, override_settings
from django.utils import timezone
from django.urls import reverse, resolve, NoReverseMatch
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.conf import settings
from django.core.paginator import Page 
# from django.http import Http404 

# Models
from .models import Demo, DemoSection

# Views
from . import views 
from .views import HARDCODED_DEMO_ENTRIES 

# Sitemaps
from .sitemaps import DemoModelSitemap, CSVDemoPagesSitemap, HardcodedDemoViewsSitemap, MainDemosPageSitemap

# Admin
from .admin import DemoAdmin, DemoSectionAdmin, DemoSectionInline

# Forms
from .forms import ImageUploadForm, SentimentAnalysisForm, CSVUploadForm, ExplainableAIDemoForm

# Import UserProfile from the portfolio app
from portfolio.models import UserProfile

# --- Helper Functions / Test Data ---

def create_test_image_file(name="test_image.png", ext="png", size=(50, 50), color=(255, 0, 0)):
    """Creates a simple image file for upload tests."""
    try:
        from PIL import Image
        pil_available = True
    except ImportError:
        pil_available = False

    if not pil_available:
        file_obj = io.BytesIO(b"fake image content for testing")
        return SimpleUploadedFile(name, file_obj.read(), content_type=f"image/{ext}")

    file_obj = io.BytesIO()
    image = Image.new("RGB", size, color)
    image.save(file_obj, ext)
    file_obj.seek(0)
    return SimpleUploadedFile(name, file_obj.read(), content_type=f"image/{ext}")

# --- Model Tests ---
class DemoModelTests(TestCase):
    def setUp(self):
        self.demo1 = Demo.objects.create(
            title="My First Test Demo",
            slug="my-first-test-demo",
            description="A test demo description.", 
            page_meta_title="Meta Title for First Demo",
            is_published=True,
            is_featured=True,
            order=1
        )
        self.demo2 = Demo.objects.create(
            title="My Second Test Demo For URL Name",
            slug="my-second-test-demo-for-url-name",
            description="Another test demo.", 
            is_published=True,
            is_featured=False,
            order=2,
            demo_url_name='demos:image_classifier' 
        )
        self.demo_draft = Demo.objects.create(
            title="Draft Test Demo",
            slug="draft-test-demo",
            is_published=False
        )

    def test_demo_creation_and_defaults(self):
        self.assertEqual(self.demo1.title, "My First Test Demo")
        self.assertEqual(self.demo1.slug, "my-first-test-demo")
        self.assertTrue(self.demo1.is_published)
        self.assertTrue(self.demo1.is_featured)
        self.assertEqual(self.demo1.order, 1)
        self.assertIsNotNone(self.demo1.date_created)
        self.assertIsNotNone(self.demo1.last_updated)
        self.assertFalse(self.demo_draft.is_published)

    def test_demo_str_representation(self):
        self.assertEqual(str(self.demo1), "My First Test Demo")

    def test_demo_get_absolute_url_generic(self):
        expected_url = reverse('demos:generic_demo_detail', kwargs={'demo_slug': self.demo1.slug})
        self.assertEqual(self.demo1.get_absolute_url(), expected_url)

    def test_demo_get_absolute_url_specific_view(self):
        try:
            expected_url = reverse('demos:image_classifier')
            self.assertEqual(self.demo2.get_absolute_url(), expected_url)
        except NoReverseMatch:
            self.fail("The URL name 'demos:image_classifier' used in Demo model tests could not be reversed. Check your demos/urls.py.")


    def test_demo_automatic_slug_generation_if_blank(self):
        demo_no_slug_provided = Demo.objects.create(title="Demo Needs A Slug Auto Generated")
        self.assertEqual(demo_no_slug_provided.slug, "demo-needs-a-slug-auto-generated")

    def test_demo_slug_persists_on_title_update_if_slug_was_set(self):
        demo = Demo.objects.create(title="Original Title With Slug", slug="original-slug-is-set")
        demo.title = "Updated Title But Slug Should Persist"
        demo.save()
        self.assertEqual(demo.slug, "original-slug-is-set")

    def test_demo_ordering(self):
        Demo.objects.all().delete()
        demo_b = Demo.objects.create(title="Demo B Order", slug="demo-b-ord", order=2)
        demo_a = Demo.objects.create(title="Demo A Order", slug="demo-a-ord", order=1)
        demo_c = Demo.objects.create(title="Demo C Order", slug="demo-c-ord", order=1, is_published=False) 
        demos = list(Demo.objects.all()) 
        self.assertEqual(demos, [demo_a, demo_c, demo_b])

class DemoSectionModelTests(TestCase):
    def setUp(self):
        self.demo = Demo.objects.create(title="Parent Demo for Sections", slug="parent-demo-sections")
        self.section1 = DemoSection.objects.create(
            demo=self.demo,
            section_order=1.0,
            section_title="Introduction Section",
            section_content_markdown="This is the **intro**." 
        )

    def test_demo_section_creation(self):
        self.assertEqual(self.section1.demo, self.demo)
        self.assertEqual(self.section1.section_title, "Introduction Section")
        self.assertEqual(self.section1.section_order, 1.0)
        self.assertEqual(self.demo.sections.count(), 1)
        self.assertEqual(self.section1.section_content_markdown, "This is the **intro**.")

    def test_demo_section_str_representation(self):
        self.assertEqual(str(self.section1), f"{self.demo.title} - Section 1.0 (Introduction Section)")
        section_no_title = DemoSection.objects.create(demo=self.demo, section_order=2.0)
        self.assertEqual(str(section_no_title), f"{self.demo.title} - Section 2.0 (Untitled)")

    def test_demo_section_ordering(self):
        section2 = DemoSection.objects.create(demo=self.demo, section_order=2.0, section_title="Section Two")
        section0_5 = DemoSection.objects.create(demo=self.demo, section_order=0.5, section_title="Section Half")
        sections = list(self.demo.sections.all()) 
        self.assertEqual(sections, [section0_5, self.section1, section2])

    def test_demo_section_unique_together_constraint(self):
        with self.assertRaises(IntegrityError):
            DemoSection.objects.create(demo=self.demo, section_order=1.0, section_title="Duplicate Order Section")

# --- Form Tests ---
class DemoFormTests(TestCase):
    def test_image_upload_form_valid(self):
        image = create_test_image_file()
        form = ImageUploadForm(files={'image': image})
        self.assertTrue(form.is_valid())

    def test_image_upload_form_invalid_no_image(self):
        form = ImageUploadForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_image_upload_form_invalid_file_type(self):
        text_file = SimpleUploadedFile("test.txt", b"some text content", content_type="text/plain")
        form = ImageUploadForm(files={'image': text_file})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_sentiment_analysis_form_valid(self):
        form = SentimentAnalysisForm(data={'text_input': 'This is a great test!'})
        self.assertTrue(form.is_valid())

    def test_sentiment_analysis_form_empty(self):
        form = SentimentAnalysisForm(data={'text_input': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('text_input', form.errors)

    def test_sentiment_analysis_form_too_long(self):
        long_text = 'a' * 1001 
        form = SentimentAnalysisForm(data={'text_input': long_text})
        self.assertFalse(form.is_valid())
        self.assertIn('text_input', form.errors)

    def test_csv_upload_form_valid(self):
        csv_content = b"header1,header2\nvalue1,value2"
        csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        form = CSVUploadForm(files={'csv_file': csv_file})
        self.assertTrue(form.is_valid())

    def test_csv_upload_form_no_file(self):
        form = CSVUploadForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('csv_file', form.errors)

    def test_explainable_ai_demo_form_valid_data(self):
        form_data = {'sepal_length': '5.1', 'sepal_width': '3.5', 'petal_length': '1.4', 'petal_width': '0.2'}
        form = ExplainableAIDemoForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_explainable_ai_demo_form_missing_data(self):
        form_data = {'sepal_length': '5.1', 'sepal_width': '3.5'} 
        form = ExplainableAIDemoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('petal_length', form.errors)
        self.assertIn('petal_width', form.errors)

    def test_explainable_ai_demo_form_invalid_data_type(self):
        form_data = {'sepal_length': 'abc', 'sepal_width': '3.5', 'petal_length': '1.4', 'petal_width': '0.2'}
        form = ExplainableAIDemoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('sepal_length', form.errors)

    def test_explainable_ai_demo_form_out_of_range(self):
        form_data = {'sepal_length': '100.0', 'sepal_width': '3.5', 'petal_length': '1.4', 'petal_width': '0.2'}
        form = ExplainableAIDemoForm(data=form_data)
        self.assertFalse(form.is_valid()) 
        self.assertIn('sepal_length', form.errors)


# --- URL Tests ---
class DemoURLTests(TestCase):
    def test_all_demos_list_url_resolves(self):
        self.assertEqual(resolve(reverse('demos:all_demos_list')).func, views.all_demos_list_view)

    def test_generic_demo_detail_url_resolves(self):
        resolver = resolve(reverse('demos:generic_demo_detail', kwargs={'demo_slug': 'any-slug'}))
        self.assertEqual(resolver.func, views.generic_demo_view)
        self.assertEqual(resolver.kwargs['demo_slug'], 'any-slug')

    def test_hardcoded_demo_urls_resolve(self):
        import demos.views as demo_views_module
        defined_view_functions = {name: func for name, func in demo_views_module.__dict__.items() if callable(func)}

        for demo_entry in HARDCODED_DEMO_ENTRIES:
            url_name = demo_entry['url_name']
            inferred_view_name_from_url = url_name.split(':')[-1].replace('-', '_') + "_view"
            
            if url_name == 'demos:keras_nmt_demo':
                 inferred_view_name_from_url = 'keras_nmt_demo_demo_view'

            if inferred_view_name_from_url not in defined_view_functions:
                print(f"Warning: View function '{inferred_view_name_from_url}' for URL name '{url_name}' not found in demos/views.py. Skipping URL resolution test for this entry.")
                continue

            expected_view_func = defined_view_functions[inferred_view_name_from_url]
            try:
                url = reverse(url_name)
                resolved_func = resolve(url).func
                self.assertEqual(resolved_func, expected_view_func, 
                                 f"URL {url_name} did not resolve to {expected_view_func.__name__}. Resolved to {resolved_func.__name__ if hasattr(resolved_func, '__name__') else resolved_func}.")
            except NoReverseMatch:
                self.fail(f"URL name {url_name} could not be reversed. Check urls.py and HARDCODED_DEMO_ENTRIES.")
            except AttributeError as e:
                 self.fail(f"Error resolving {url_name}: {e}. Check if view function exists and is correctly named.")


# --- View Tests ---
class DemoViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile_for_demos_tests = UserProfile.objects.create(
            full_name="Demos Test User",
            tagline="Testing the Demos App",
            email="demotest@example.com",
        )
        cls.client = Client()
        cls.items_per_page = 9 

        # CHANGED: Use "**BoldTest**" for db_demo1's description for focused testing
        cls.db_demo1 = Demo.objects.create(
            title="Database Demo Alpha (View Test)", 
            slug="db-demo-alpha-view", 
            description="**BoldTest**", # Main Markdown content for testing
            is_published=True, 
            is_featured=True, 
            order=1, 
            page_meta_title="Meta for Alpha"
        )
        cls.db_demo1_section1 = DemoSection.objects.create(
            demo=cls.db_demo1, 
            section_order=1, 
            section_title="Intro Section", 
            section_content_markdown="**Hello** world from section." 
        )
        cls.db_demo2 = Demo.objects.create(
            title="Database Demo Beta (View Test)", 
            slug="db-demo-beta-view", 
            description="DB Beta Desc", 
            is_published=True, 
            order=2, 
            demo_url_name="demos:image_classifier"
        )
        cls.db_demo_marked_unpublished = Demo.objects.create(
            title="Draft DB Demo Gamma", 
            slug="draft-db-demo-gamma-view",        
            is_published=False, 
            order=0
        )        
        try:
            image_classifier_url_name = 'demos:image_classifier'
            if any(entry['url_name'] == image_classifier_url_name for entry in HARDCODED_DEMO_ENTRIES):
                 Demo.objects.create(title="Image Classification DB Entry", slug="image-classification-db", demo_url_name=image_classifier_url_name, order=5, is_published=True)
        except NoReverseMatch:
            pass

    def test_all_demos_list_view_get_request_and_template(self):
        response = self.client.get(reverse('demos:all_demos_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'demos/all_demos.html')
        self.assertIn('demos', response.context)
        self.assertIsInstance(response.context['demos'], Page)
        self.assertEqual(response.context['page_title'], 'Demos & Concepts')
        self.assertIn('user_profile', response.context) 
        self.assertEqual(response.context['user_profile'], self.user_profile_for_demos_tests)

    def test_all_demos_list_view_context_content_and_ordering(self):
        response = self.client.get(reverse('demos:all_demos_list'))
        self.assertEqual(response.status_code, 200)
        page_obj = response.context['demos']
        demo_items_on_page = page_obj.object_list

        for hc_entry in HARDCODED_DEMO_ENTRIES:
            try:
                rendered_item = next((item for item in demo_items_on_page if item['title'] == hc_entry['title']), None)
                if rendered_item:
                    self.assertEqual(rendered_item['description'], hc_entry.get('description', 'No description available.'))
            except NoReverseMatch:
                pass

        db_demo1_rendered = next((item for item in demo_items_on_page if item['title'] == self.db_demo1.title), None)
        if db_demo1_rendered:
            self.assertEqual(db_demo1_rendered['description'], self.db_demo1.description) 

        # Check for plain text of db_demo1.description after striptags in all_demos.html
        # self.db_demo1.description is "**BoldTest**"
        # After markdownify | striptags, it should be "BoldTest"
        self.assertContains(response, "BoldTest")
        self.assertNotContains(response, "<strong>") 


    def test_all_demos_list_view_pagination(self):
        num_hardcoded_reversible = 0
        hardcoded_urls_for_dedup = set()
        for entry in HARDCODED_DEMO_ENTRIES:
            try:
                reverse(entry['url_name'])
                num_hardcoded_reversible += 1
                hardcoded_urls_for_dedup.add(entry['url_name'])
            except NoReverseMatch:
                pass

        effective_db_demo_count = Demo.objects.filter(is_published=True).exclude(demo_url_name__in=hardcoded_urls_for_dedup).count()
        total_demos_for_list = num_hardcoded_reversible + effective_db_demo_count
        
        demos_to_add_for_pagination = (self.items_per_page * 2) - total_demos_for_list + 1
        if demos_to_add_for_pagination > 0:
            for i in range(demos_to_add_for_pagination):
                 Demo.objects.create(title=f"Pagination Test Demo {i}", slug=f"pagination-test-demo-{uuid.uuid4()}", is_published=True, order=100+i)

        effective_db_demo_count_after_add = Demo.objects.filter(is_published=True).exclude(demo_url_name__in=hardcoded_urls_for_dedup).count()
        total_demos_for_list_after_add = num_hardcoded_reversible + effective_db_demo_count_after_add
        num_expected_pages = (total_demos_for_list_after_add + self.items_per_page - 1) // self.items_per_page

        response_page1 = self.client.get(reverse('demos:all_demos_list'))
        self.assertEqual(response_page1.status_code, 200)

        if num_expected_pages > 1:
            self.assertTrue(response_page1.context['demos'].has_next(), f"Expected next page. Total pages: {num_expected_pages}, Total items: {total_demos_for_list_after_add}")
            response_page2 = self.client.get(reverse('demos:all_demos_list') + '?page=2')
            self.assertEqual(response_page2.status_code, 200)
            self.assertTrue(response_page2.context['demos'].has_previous())
        else:
            self.assertFalse(response_page1.context['demos'].has_next(), "Should not have a next page if only one page expected.")

        response_invalid_page = self.client.get(reverse('demos:all_demos_list') + '?page=notanumber')
        self.assertEqual(response_invalid_page.context['demos'].number, 1) 
        response_empty_page = self.client.get(reverse('demos:all_demos_list') + '?page=99999') 
        self.assertEqual(response_empty_page.context['demos'].number, max(1, num_expected_pages)) 

    def test_all_demos_list_view_empty_state(self):
        Demo.objects.all().delete() 
        with patch('demos.views.HARDCODED_DEMO_ENTRIES', []): 
            response = self.client.get(reverse('demos:all_demos_list'))
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context['demos'].object_list) 
            self.assertContains(response, "No Demos Available")

    def test_generic_demo_view_success(self):
        response = self.client.get(reverse('demos:generic_demo_detail', kwargs={'demo_slug': self.db_demo1.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'demos/generic_demo_page.html')
        
        demo_page_in_context = response.context.get('demo_page')
        self.assertIsNotNone(demo_page_in_context)
        self.assertEqual(demo_page_in_context, self.db_demo1)

        # Check raw Markdown for the main description 
        self.assertEqual(demo_page_in_context.description, "**BoldTest**") 

        sections_in_context = list(demo_page_in_context.sections.all().order_by('section_order'))
        self.assertTrue(len(sections_in_context) > 0)
        self.assertEqual(sections_in_context[0].section_content_markdown, self.db_demo1_section1.section_content_markdown)
        
        # Check rendered HTML for section (markdownify usually doesn't add <p> for single lines)
        self.assertContains(response, "<strong>Hello</strong> world from section.")
        self.assertNotContains(response, "<p><strong>Hello</strong> world from section.</p>") 
        
        # Check rendered HTML for main description (now "**BoldTest**")
        self.assertContains(response, "<strong>BoldTest</strong>")
        self.assertNotContains(response, "<p><strong>BoldTest</strong></p>")

        expected_meta_title = self.db_demo1.page_meta_title if self.db_demo1.page_meta_title else self.db_demo1.title
        self.assertContains(response, expected_meta_title) 
        self.assertIn('user_profile', response.context)

    def test_generic_demo_view_404_non_existent_slug(self):
        response = self.client.get(reverse('demos:generic_demo_detail', kwargs={'demo_slug': 'non-existent-demo-slug'}))
        self.assertEqual(response.status_code, 404)

    def test_generic_demo_view_unpublished_demo(self):
        response = self.client.get(reverse('demos:generic_demo_detail', kwargs={'demo_slug': self.db_demo_marked_unpublished.slug}))
        self.assertEqual(response.status_code, 404) 

    def test_generic_demo_view_no_sections(self):
        demo_no_sections = Demo.objects.create(title="Demo With No Sections", slug="demo-no-sections", is_published=True, description=None)
        response = self.client.get(reverse('demos:generic_demo_detail', kwargs={'demo_slug': demo_no_sections.slug}))
        self.assertEqual(response.status_code, 200)
        
        demo_page_in_context = response.context.get('demo_page')
        self.assertIsNotNone(demo_page_in_context)
        self.assertEqual(demo_page_in_context.sections.count(), 0)
        self.assertIsNone(demo_page_in_context.description)
        
        # Assuming generic_demo_page.html is updated to check for `not demo_page.description`
        self.assertContains(response, "No content sections found for this demo.")
        self.assertIn('user_profile', response.context)

    @patch('demos.views.TF_AVAILABLE', True)
    @patch('demos.views.IMAGE_MODEL_LOADED', True)
    @patch('demos.views.image_model.predict') 
    @patch('demos.views.decode_predictions')
    @patch('demos.views.keras_image_utils.load_img')
    @patch('demos.views.keras_image_utils.img_to_array')
    @patch('demos.views.preprocess_input')
    def test_image_classification_view_post_valid(self, mock_preprocess, mock_img_to_array, mock_load_img, mock_decode, mock_predict):
        mock_predict.return_value = MagicMock() 
        mock_decode.return_value = [[('class_id_1', 'German_shepherd', 0.9), ('class_id_2', 'Golden_Retriever', 0.05)]]
        mock_load_img.return_value = MagicMock() 
        mock_img_to_array.return_value = MagicMock() 
        mock_preprocess.return_value = MagicMock() 

        image = create_test_image_file()
        response = self.client.post(reverse('demos:image_classifier'), {'image': image})

        self.assertEqual(response.status_code, 200)
        self.assertIn('prediction_results', response.context)
        prediction_results = response.context.get('prediction_results')
        self.assertIsNotNone(prediction_results)
        if prediction_results: 
            self.assertEqual(len(prediction_results), 2)
            self.assertEqual(prediction_results[0]['label'], 'German shepherd') 
            self.assertAlmostEqual(prediction_results[0]['probability'], 90.0)
        self.assertIsNotNone(response.context.get('uploaded_image_url')) 
        self.assertIsNone(response.context.get('error_message')) 
        mock_predict.assert_called_once()
        mock_decode.assert_called_once()
        self.assertIn('user_profile', response.context)

    def test_image_classification_view_post_invalid_form(self):
        response = self.client.post(reverse('demos:image_classifier'), {}) 
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], ImageUploadForm)
        self.assertTrue(response.context['form'].errors) 
        self.assertIn('user_profile', response.context)

    @patch('demos.views.TF_AVAILABLE', False)
    def test_image_classification_view_tf_not_available(self):
        response = self.client.get(reverse('demos:image_classifier'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context.get('error_message'))
        self.assertIn("TensorFlow library is not installed", response.context['error_message'])
        self.assertIn('user_profile', response.context)

    @patch('demos.views.TF_AVAILABLE', True)
    @patch('demos.views.IMAGE_MODEL_LOADED', False)
    def test_image_classification_view_model_not_loaded(self):
        response = self.client.get(reverse('demos:image_classifier'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context.get('error_message'))
        self.assertIn("Image classification model could not be loaded", response.context['error_message'])
        self.assertIn('user_profile', response.context)

    def test_sentiment_analysis_view_get(self):
        response = self.client.get(reverse('demos:sentiment_analyzer'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'demos/sentiment_analysis_demo.html')
        self.assertIsInstance(response.context['form'], SentimentAnalysisForm)
        self.assertIn('user_profile', response.context)

    @patch('demos.views.TRANSFORMERS_AVAILABLE', True)
    @patch('demos.views.SENTIMENT_MODEL_LOADED', True)
    @patch('demos.views.sentiment_pipeline') 
    def test_sentiment_analysis_view_post_valid(self, mock_pipeline_func):
        mock_pipeline_func.return_value = [{'label': 'POSITIVE', 'score': 0.99}]
        
        text_input = "This is a fantastic test!"
        response = self.client.post(reverse('demos:sentiment_analyzer'), {'text_input': text_input})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context.get('sentiment_result'))
        if response.context.get('sentiment_result'):
            self.assertEqual(response.context['sentiment_result']['label'], 'POSITIVE')
            self.assertAlmostEqual(response.context['sentiment_result']['score'], 99.0) 
        self.assertEqual(response.context.get('submitted_text'), text_input)
        mock_pipeline_func.assert_called_once_with(text_input)
        self.assertIn('user_profile', response.context)

    @patch('demos.views.TRANSFORMERS_AVAILABLE', False)
    def test_sentiment_analysis_view_transformers_not_available(self):
        response = self.client.get(reverse('demos:sentiment_analyzer'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Transformers library not installed", response.context.get('error_message', ''))
        self.assertIn('user_profile', response.context)

    def test_data_analyser_view_get(self):
        response = self.client.get(reverse('demos:data_analyser'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'demos/data_analysis_demo.html')
        self.assertIsInstance(response.context['form'], CSVUploadForm)
        self.assertIn('user_profile', response.context)

    @patch('demos.views.DATA_LIBS_AVAILABLE', False)
    def test_data_analyser_view_libs_not_available(self):
        response = self.client.get(reverse('demos:data_analyser'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Data science libraries (Pandas, Matplotlib, Seaborn) not installed", response.context.get('error_message', ''))
        self.assertIn('user_profile', response.context)

    def test_explainable_ai_view_get(self):
        response = self.client.get(reverse('demos:explainable_ai'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'demos/explainable_ai_demo.html')
        self.assertIsInstance(response.context['form'], ExplainableAIDemoForm)
        self.assertIn('user_profile', response.context)

    @patch('demos.views.SKLEARN_AVAILABLE', True)
    @patch('demos.views.TREE_MODEL_LOADED', True)
    @patch('demos.views.decision_tree_model') 
    @patch('demos.views.iris') 
    def test_explainable_ai_view_post_valid(self, mock_iris, mock_tree_model):
        mock_iris.target_names = np.array(['setosa', 'versicolor', 'virginica'])
        mock_iris.feature_names = ['sepal length (cm)', 'sepal width (cm)', 'petal length (cm)', 'petal width (cm)']
        
        mock_tree_model.predict.return_value = np.array([0])
        mock_tree_model.predict_proba.return_value = np.array([[0.95, 0.03, 0.02]])
        mock_tree_model.feature_importances_ = np.array([0.1, 0.05, 0.45, 0.4])

        mock_tree_object = MagicMock(spec_set=['value', 'feature', 'threshold', 'children_left', 'children_right']) 
        mock_tree_object.value = np.array([[[30.,  0.,  0.]], [[0., 0., 0.]], [[ 0., 30.,  0.]], [[0.,0.,0.]], [[ 0.,  0., 30.]]])
        mock_tree_object.feature = np.array([2, -2, 0, -2, 1, -2, -2]) 
        mock_tree_object.threshold = np.array([2.45, -2., 0.8, -2., 1.75, -2., -2.])
        mock_tree_object.children_left = np.array([1, -1, 3, -1, 5, -1, -1]) 
        mock_tree_object.children_right = np.array([2, -1, 4, -1, 6, -1, -1])
        mock_tree_model.tree_ = mock_tree_object

        mock_decision_path_result = MagicMock()
        mock_decision_path_result.indices = np.array([0, 2, 4]) 
        mock_decision_path_result.indptr = np.array([0, 3])     
        mock_tree_model.decision_path.return_value = mock_decision_path_result
        mock_tree_model.apply.return_value = np.array([4]) 

        form_data = {'sepal_length': '5.1', 'sepal_width': '3.5', 'petal_length': '1.4', 'petal_width': '0.2'}
        response = self.client.post(reverse('demos:explainable_ai'), form_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context.get('error_message'), f"View returned error: {response.context.get('error_message')}")

        self.assertIsNotNone(response.context.get('prediction'))
        self.assertEqual(response.context['prediction'], 'setosa')
        
        probability_list = response.context.get('probability_list')
        self.assertIsNotNone(probability_list)
        if probability_list:
            self.assertEqual(len(probability_list), 3)
            self.assertEqual(probability_list[0]['name'], 'setosa')
            self.assertAlmostEqual(probability_list[0]['probability'], 95.0)

        explanation_rules = response.context.get('explanation_rules')
        self.assertIsNotNone(explanation_rules, "explanation_rules should not be None")
        if explanation_rules: 
            self.assertTrue(len(explanation_rules) > 0)
            self.assertTrue(any("**Node" in rule for rule in explanation_rules))
            self.assertTrue(any("*" in rule for rule in explanation_rules))

        feature_importances_ctx = response.context.get('feature_importances')
        self.assertIsNotNone(feature_importances_ctx, "feature_importances should not be None in context")
        if feature_importances_ctx:
            self.assertEqual(len(feature_importances_ctx), 4)
        
        self.assertIn('user_profile', response.context)

    def test_keras_nmt_demo_view_get(self):
        response = self.client.get(reverse('demos:keras_nmt_demo'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'demos/keras_nmt_demo_page.html')
        self.assertEqual(response.context['page_title'], 'Neural Machine Translation with Keras')
        self.assertIn('user_profile', response.context)

# --- Sitemap Tests ---
@override_settings(BASE_DIR=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class DemoSitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile_for_sitemap_tests = UserProfile.objects.create(
            full_name="Sitemap Demo User",
            site_identifier="main_profile_sitemap_demos"
        )
        cls.published_db_demo = Demo.objects.create(
            title="Sitemap Test Published Demo", slug="sitemap-test-published-demo",
            is_published=True, last_updated=timezone.now()
        )
        cls.draft_db_demo = Demo.objects.create(
            title="Sitemap Test Draft Demo", slug="sitemap-test-draft-demo",
            is_published=False, last_updated=timezone.now()
        )
        Demo.objects.create(title="CSV Slug Exists Demo", slug="csv-slug-exists", is_published=True)

    def test_demo_model_sitemap_items(self):
        sitemap = DemoModelSitemap()
        sitemap_items = list(sitemap.items())
        self.assertIn(self.published_db_demo, sitemap_items)
        self.assertNotIn(self.draft_db_demo, sitemap_items, "Draft demos should not be in the sitemap.")

    def test_demo_model_sitemap_lastmod(self):
        sitemap = DemoModelSitemap()
        self.assertEqual(sitemap.lastmod(self.published_db_demo), self.published_db_demo.last_updated)

    @patch('pandas.read_csv')
    @patch('demos.sitemaps.DEMO_MODEL_EXISTS', True)
    @patch('demos.models.Demo.objects.filter')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_csv_demo_pages_sitemap_items_valid_csv_and_demo_exists(self, mock_getsize, mock_exists, mock_demo_objects_filter, mock_read_csv):
        mock_exists.return_value = True
        mock_getsize.return_value = 100
        mock_df = pd.DataFrame({'demo_slug': ['csv-slug-exists', 'csv-slug-does-not-exist', None, '']})
        mock_read_csv.return_value = mock_df
        def filter_side_effect(slug, is_published): 
            mock_qs = MagicMock()
            if slug == 'csv-slug-exists' and is_published: 
                mock_qs.exists.return_value = True
            else:
                mock_qs.exists.return_value = False
            return mock_qs
        mock_demo_objects_filter.side_effect = filter_side_effect
        sitemap = CSVDemoPagesSitemap()
        items = sitemap.items()
        self.assertEqual(len(items), 1, f"Expected 1 item from CSV, got {len(items)}. Items: {items}")
        self.assertIn({'slug': 'csv-slug-exists'}, items)
        self.assertNotIn({'slug': 'csv-slug-does-not-exist'}, items)

    @patch('pandas.read_csv')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_csv_demo_pages_sitemap_items_empty_csv(self, mock_getsize, mock_exists, mock_read_csv):
        mock_exists.return_value = True
        mock_getsize.return_value = 0
        sitemap = CSVDemoPagesSitemap()
        self.assertEqual(sitemap.items(), [])

    @patch('os.path.exists')
    def test_csv_demo_pages_sitemap_items_csv_not_found(self, mock_exists):
        mock_exists.return_value = False
        sitemap = CSVDemoPagesSitemap()
        self.assertEqual(sitemap.items(), [])

    @patch('demos.sitemaps.DEMO_MODEL_EXISTS', True)
    @patch('demos.models.Demo.objects.filter')
    def test_csv_demo_pages_sitemap_location(self, mock_demo_filter):
        sitemap = CSVDemoPagesSitemap()
        item_dict_valid = {'slug': 'csv-slug-exists'}
        mock_valid_qs = MagicMock()
        mock_valid_qs.exists.return_value = True
        mock_demo_filter.return_value = mock_valid_qs
        expected_url = reverse('demos:generic_demo_detail', kwargs={'demo_slug': 'csv-slug-exists'})
        self.assertEqual(sitemap.location(item_dict_valid), expected_url)
        mock_demo_filter.assert_called_with(slug='csv-slug-exists', is_published=True)

        item_dict_invalid_demo = {'slug': 'slug-that-will-not-map-to-a-demo'}
        mock_invalid_qs = MagicMock()
        mock_invalid_qs.exists.return_value = False
        mock_demo_filter.return_value = mock_invalid_qs
        self.assertEqual(sitemap.location(item_dict_invalid_demo), '',
                         "Location for a slug not mapping to a published Demo object should be empty.")
        mock_demo_filter.assert_called_with(slug='slug-that-will-not-map-to-a-demo', is_published=True)

    def test_hardcoded_demo_views_sitemap_location(self):
        sitemap = HardcodedDemoViewsSitemap()
        for item_url_name in sitemap.items():
            try:
                expected_url = reverse(item_url_name)
                self.assertEqual(sitemap.location(item_url_name), expected_url,
                                 f"Location for '{item_url_name}' should correctly reverse.")
            except NoReverseMatch:
                self.fail(f"Sitemap item '{item_url_name}' from HardcodedDemoViewsSitemap.items() does not reverse. This indicates an issue in items() filtering or urls.py.")

    def test_main_demos_page_sitemap(self):
        sitemap = MainDemosPageSitemap()
        self.assertEqual(sitemap.items(), ['demos:all_demos_list'])
        self.assertEqual(sitemap.location('demos:all_demos_list'), reverse('demos:all_demos_list'))

# --- Admin Tests ---
class DemoAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile_for_demos_admin_tests = UserProfile.objects.create(
            full_name="Demos Admin Test User",
            site_identifier="main_profile_demos_admin"
        )
        cls.superuser = User.objects.create_superuser('admin_demos_user', 'admin_demos@example.com', 'password123')
        cls.demo_for_admin_test = Demo.objects.create(title="Admin Test Demo For Demos App", slug="admin-test-demo-slug-demos")
        cls.demo_section_for_admin_test = DemoSection.objects.create(demo=cls.demo_for_admin_test, section_order=1, section_title="Admin Section")

    def setUp(self):
        self.client.login(username='admin_demos_user', password='password123')

    def test_demo_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:demos_demo_changelist'))
        self.assertEqual(response.status_code, 200)
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_demos_admin_tests)

    def test_demo_admin_add_accessible(self):
        response = self.client.get(reverse('admin:demos_demo_add'))
        self.assertEqual(response.status_code, 200)

    def test_demo_admin_change_view_accessible(self):
        response = self.client.get(reverse('admin:demos_demo_change', args=[self.demo_for_admin_test.pk]))
        self.assertEqual(response.status_code, 200)

    def test_demo_section_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:demos_demosection_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_demo_admin_configuration(self):
        self.assertIn(DemoSectionInline, DemoAdmin.inlines)
        self.assertIn('title', DemoAdmin.list_display)
        self.assertIn('is_published', DemoAdmin.list_filter)
        self.assertIn('title', DemoAdmin.search_fields)
        self.assertEqual(DemoAdmin.prepopulated_fields, {'slug': ('title',)})
        self.assertTrue(any('title' in fs_options.get('fields', []) for _, fs_options in DemoAdmin.fieldsets))

    def test_demo_section_admin_configuration(self):
        self.assertIn('demo', DemoSectionAdmin.list_display)
        self.assertIn('demo__title', DemoSectionAdmin.list_filter)
        self.assertIn('section_title', DemoSectionAdmin.search_fields)
        self.assertIn('demo', DemoSectionAdmin.autocomplete_fields)

# --- tearDownModule ---
def tearDownModule():
    temp_dirs_to_clean = []
    if hasattr(settings, 'MEDIA_ROOT'):
        temp_demos_plots_dir = os.path.join(settings.MEDIA_ROOT, 'temp_demos', 'plots')
        if os.path.exists(temp_demos_plots_dir):
            temp_dirs_to_clean.append(temp_demos_plots_dir)
        temp_uploads_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
        if os.path.exists(temp_uploads_dir):
            temp_dirs_to_clean.append(temp_uploads_dir)
            
    test_media_root_da = getattr(settings, 'TEST_MEDIA_ROOT_TEMP_DATA_ANALYSER', None)
    if test_media_root_da and os.path.exists(test_media_root_da):
        temp_dirs_to_clean.append(test_media_root_da)

    for temp_dir_path in temp_dirs_to_clean:
        if os.path.exists(temp_dir_path):
            try:
                shutil.rmtree(temp_dir_path)
                print(f"Successfully removed temporary test directory: {temp_dir_path}")
            except OSError as e:
                print(f"Warning: Error removing temporary test directory {temp_dir_path}: {e}.")
