# demos/tests.py

import os
import shutil
import uuid
import io
import base64
from unittest.mock import patch, MagicMock, mock_open

# Import pandas
import pandas as pd

from django.test import TestCase, Client, override_settings
from django.utils import timezone
from django.urls import reverse, resolve, NoReverseMatch
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.conf import settings
from django.core.paginator import Page, Paginator
from django.http import Http404

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

# --- Helper Functions / Test Data ---

def create_test_image_file(name="test_image.png", ext="png", size=(50, 50), color=(255, 0, 0)):
    """Creates a simple image file for upload tests."""
    try:
        from PIL import Image
        pil_available = True
    except ImportError:
        pil_available = False

    if not pil_available:
        file_obj = io.BytesIO(b"fake image content")
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
        expected_url = reverse('demos:image_classifier')
        self.assertEqual(self.demo2.get_absolute_url(), expected_url)


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
            section_content_markdown="This is the intro."
        )

    def test_demo_section_creation(self):
        self.assertEqual(self.section1.demo, self.demo)
        self.assertEqual(self.section1.section_title, "Introduction Section")
        self.assertEqual(self.section1.section_order, 1.0)
        self.assertEqual(self.demo.sections.count(), 1)

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

    def test_csv_upload_form_invalid_file_type(self):
        text_file = SimpleUploadedFile("test.txt", b"some text content", content_type="text/plain")
        form = CSVUploadForm(files={'csv_file': text_file})
        self.assertTrue(form.is_valid())

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

    def test_image_classifier_url_resolves(self):
        self.assertEqual(resolve(reverse('demos:image_classifier')).func, views.image_classification_view)

    def test_sentiment_analyzer_url_resolves(self):
        self.assertEqual(resolve(reverse('demos:sentiment_analyzer')).func, views.sentiment_analysis_view)

    def test_data_analyser_url_resolves(self):
        self.assertEqual(resolve(reverse('demos:data_analyser')).func, views.data_analyser_view)

    def test_data_wrangler_url_resolves(self):
        self.assertEqual(resolve(reverse('demos:data_wrangler')).func, views.data_wrangling_view)

    def test_explainable_ai_url_resolves(self):
        self.assertEqual(resolve(reverse('demos:explainable_ai')).func, views.explainable_ai_view)

    def test_causal_inference_url_resolves(self):
        self.assertEqual(resolve(reverse('demos:causal_inference')).func, views.causal_inference_demo_view)

    def test_optimization_demo_url_resolves(self):
        self.assertEqual(resolve(reverse('demos:optimization_demo')).func, views.optimization_demo_view)

    def test_keras_nmt_demo_url_resolves(self):
         self.assertEqual(resolve(reverse('demos:keras_nmt_demo')).func, views.keras_nmt_demo_demo_view)

# --- View Tests ---
class DemoViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.items_per_page = 9

        cls.db_demo1 = Demo.objects.create(title="Database Demo Alpha (View Test)", slug="db-demo-alpha-view", description="DB Alpha Desc", is_published=True, is_featured=True, order=1, page_meta_title="Meta for Alpha")
        cls.db_demo2 = Demo.objects.create(title="Database Demo Beta (View Test)", slug="db-demo-beta-view", description="DB Beta Desc", is_published=True, order=2, demo_url_name="demos:image_classifier")
        cls.db_demo_draft = Demo.objects.create(title="Draft DB Demo Gamma (View Test)", slug="draft-db-demo-gamma-view", is_published=False, order=0)
        DemoSection.objects.create(demo=cls.db_demo1, section_order=1, section_title="Intro Section", section_content_markdown="**Hello** world from section.")
        Demo.objects.create(title="Image Classification DB Entry", slug="image-classification-db", demo_url_name="demos:image_classifier", order=5)

    # def test_all_demos_list_view_get_request(self):
    #     response = self.client.get(reverse('demos:all_demos_list'))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertTemplateUsed(response, 'demos/all_demos.html')
    #     self.assertIn('demos', response.context)
    #     self.assertIsInstance(response.context['demos'], Page)
    #     self.assertEqual(response.context['page_title'], 'Demos & Concepts')

    def test_all_demos_list_view_context_content_and_ordering(self):
        response = self.client.get(reverse('demos:all_demos_list'))
        self.assertEqual(response.status_code, 200)
        page_obj = response.context['demos']
        demo_items_on_page = page_obj.object_list
        expected_display_items = []
        processed_hardcoded_urls = set()

        for hc_entry in HARDCODED_DEMO_ENTRIES:
            try:
                expected_display_items.append({
                    'title': hc_entry['title'],
                    'description': hc_entry['description'],
                    'image_url': hc_entry.get('image_url', 'https://placehold.co/600x400/cccccc/ffffff?text=Preview+Not+Available'),
                    'detail_url': reverse(hc_entry['url_name'])
                })
                processed_hardcoded_urls.add(hc_entry['url_name'])
            except NoReverseMatch:
                pass

        db_demos = Demo.objects.all()
        for db_item in db_demos:
            is_already_hardcoded = False
            if db_item.demo_url_name and db_item.demo_url_name in processed_hardcoded_urls:
                is_already_hardcoded = True

            if not is_already_hardcoded:
                 expected_display_items.append({
                    'title': db_item.title,
                    'description': db_item.description or "Detailed content available.",
                    'image_url': db_item.image_url or 'https://placehold.co/600x400/cccccc/ffffff?text=Preview+Not+Available',
                    'detail_url': db_item.get_absolute_url()
                })

        expected_display_items.sort(key=lambda x: x['title'].lower())
        expected_titles_on_first_page = [item['title'] for item in expected_display_items[:self.items_per_page]]
        actual_titles_on_page = [item['title'] for item in demo_items_on_page]

        self.assertEqual(actual_titles_on_page, expected_titles_on_first_page)

    def test_all_demos_list_view_pagination(self):
        num_hardcoded = len(HARDCODED_DEMO_ENTRIES)
        current_db_demos = Demo.objects.all()
        hardcoded_urls = {entry['url_name'] for entry in HARDCODED_DEMO_ENTRIES}
        effective_db_demo_count = sum(1 for db_demo in current_db_demos if not (db_demo.demo_url_name and db_demo.demo_url_name in hardcoded_urls))
        total_demos_for_list = num_hardcoded + effective_db_demo_count

        for i in range(self.items_per_page * 2 - total_demos_for_list + 5):
             Demo.objects.create(title=f"Pagination Test Demo {i}", slug=f"pagination-test-demo-{i}", is_published=True, order=100+i)

        response_page1 = self.client.get(reverse('demos:all_demos_list'))
        self.assertEqual(response_page1.status_code, 200)
        if response_page1.context['demos'].paginator.num_pages > 1:
            self.assertTrue(response_page1.context['demos'].has_next())

            response_page2 = self.client.get(reverse('demos:all_demos_list') + '?page=2')
            self.assertEqual(response_page2.status_code, 200)
            self.assertTrue(response_page2.context['demos'].has_previous())

        response_invalid_page = self.client.get(reverse('demos:all_demos_list') + '?page=notanumber')
        self.assertEqual(response_invalid_page.context['demos'].number, 1)

        response_empty_page = self.client.get(reverse('demos:all_demos_list') + '?page=99999')
        self.assertEqual(response_empty_page.context['demos'].number, response_empty_page.context['demos'].paginator.num_pages)

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
        self.assertEqual(response.context['demo_page'], self.db_demo1)
        self.assertContains(response, self.db_demo1.page_meta_title if self.db_demo1.page_meta_title else self.db_demo1.title)
        self.assertTrue(len(response.context['sections']) > 0)
        self.assertContains(response, "<strong>Hello</strong> world from section.")

    def test_generic_demo_view_draft_demo(self):
        response = self.client.get(reverse('demos:generic_demo_detail', kwargs={'demo_slug': self.db_demo_draft.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['demo_page'], self.db_demo_draft)

    def test_generic_demo_view_no_sections(self):
        demo_no_sections = Demo.objects.create(title="Demo With No Sections", slug="demo-no-sections")
        response = self.client.get(reverse('demos:generic_demo_detail', kwargs={'demo_slug': demo_no_sections.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['sections']), 0)
        self.assertContains(response, "No content sections found for this demo.")

    @patch('markdown.markdown')
    def test_generic_demo_view_markdown_error(self, mock_markdown):
        mock_markdown.side_effect = Exception("Markdown processing failed!")
        response = self.client.get(reverse('demos:generic_demo_detail', kwargs={'demo_slug': self.db_demo1.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Error processing content. Please check the Markdown syntax.", response.context['sections'][0]['section_content_html'])

    @patch('demos.views.TF_AVAILABLE', True)
    @patch('demos.views.IMAGE_MODEL_LOADED', True)
    @patch('demos.views.image_model.predict')
    @patch('demos.views.decode_predictions')
    @patch('demos.views.keras_image_utils.load_img')
    @patch('demos.views.keras_image_utils.img_to_array')
    @patch('demos.views.preprocess_input')
    def test_image_classification_view_post_valid(self, mock_preprocess, mock_img_to_array, mock_load_img, mock_decode, mock_predict):
        """Test POST request with a valid image to image_classification_view."""
        mock_predict.return_value = MagicMock()
        # FIX: decode_predictions in the view is called as decode_predictions(preds, top=3)[0]
        # This means the mock for decode_predictions should return a list containing a single element,
        # where that single element is the list of top 3 predictions.
        mock_decode.return_value = [ # This is the return value of decode_predictions(preds, top=3)
            [ # This is decode_predictions(preds, top=3)[0]
                ('class_id_1', 'German_shepherd', 0.9),
                ('class_id_2', 'Golden_Retriever', 0.05),
                ('class_id_3', 'Labrador', 0.02)
            ]
        ]
        mock_load_img.return_value = MagicMock()
        mock_img_to_array.return_value = MagicMock()
        mock_preprocess.return_value = MagicMock()

        image = create_test_image_file()
        response = self.client.post(reverse('demos:image_classifier'), {'image': image})

        self.assertEqual(response.status_code, 200)
        self.assertIn('prediction_results', response.context, "Context should contain 'prediction_results'")
        self.assertIsNotNone(response.context.get('prediction_results'), # Use .get() for safer access
                             f"prediction_results should not be None. Error message in context: {response.context.get('error_message')}")
        
        prediction_results = response.context.get('prediction_results')
        if prediction_results is not None:
            self.assertEqual(len(prediction_results), 3)
            self.assertEqual(prediction_results[0]['label'], 'German shepherd')
            self.assertAlmostEqual(prediction_results[0]['probability'], 90.0)
        
        self.assertIsNotNone(response.context.get('uploaded_image_url'))
        self.assertIsNone(response.context.get('error_message'))
        mock_predict.assert_called_once()
        mock_decode.assert_called_once()


    def test_image_classification_view_post_invalid_form(self):
        response = self.client.post(reverse('demos:image_classifier'), {})
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], ImageUploadForm)
        self.assertTrue(response.context['form'].errors)
        self.assertIsNotNone(response.context['error_message'])
        self.assertIn("Invalid form submission", response.context['error_message'])

    @patch('demos.views.TF_AVAILABLE', False)
    def test_image_classification_view_tf_not_available(self):
        response = self.client.get(reverse('demos:image_classifier'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['error_message'])
        self.assertIn("TensorFlow library is not installed", response.context['error_message'])

    @patch('demos.views.TF_AVAILABLE', True)
    @patch('demos.views.IMAGE_MODEL_LOADED', False)
    def test_image_classification_view_model_not_loaded(self):
        response = self.client.get(reverse('demos:image_classifier'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['error_message'])
        self.assertIn("Image classification model could not be loaded", response.context['error_message'])

    def test_sentiment_analysis_view_get(self):
        response = self.client.get(reverse('demos:sentiment_analyzer'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'demos/sentiment_analysis_demo.html')
        self.assertIsInstance(response.context['form'], SentimentAnalysisForm)

    @patch('demos.views.TRANSFORMERS_AVAILABLE', True)
    @patch('demos.views.SENTIMENT_MODEL_LOADED', True)
    @patch('demos.views.sentiment_pipeline')
    def test_sentiment_analysis_view_post_valid(self, mock_pipeline):
        mock_pipeline.return_value = [{'label': 'POSITIVE', 'score': 0.99}]
        text_input = "This is a fantastic test!"
        response = self.client.post(reverse('demos:sentiment_analyzer'), {'text_input': text_input})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['sentiment_result'])
        self.assertEqual(response.context['sentiment_result']['label'], 'POSITIVE')
        self.assertAlmostEqual(response.context['sentiment_result']['score'], 99.0)
        self.assertEqual(response.context['submitted_text'], text_input)
        mock_pipeline.assert_called_once_with(text_input)

    @patch('demos.views.TRANSFORMERS_AVAILABLE', False)
    def test_sentiment_analysis_view_transformers_not_available(self):
        response = self.client.get(reverse('demos:sentiment_analyzer'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Transformers library not installed", response.context['error_message'])

    def test_data_analyser_view_get(self):
        response = self.client.get(reverse('demos:data_analyser'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'demos/data_analysis_demo.html')
        self.assertIsInstance(response.context['form'], CSVUploadForm)

    @patch('demos.views.DATA_LIBS_AVAILABLE', True)
    @patch('pandas.read_csv')
    @patch('matplotlib.pyplot.savefig')
    @patch('os.makedirs')
    def test_data_analyser_view_post_valid_csv(self, mock_makedirs, mock_savefig, mock_read_csv):
        # --- Mock DataFrame and its methods ---
        mock_df = MagicMock(spec=pd.DataFrame) # Use spec for better mocking
        mock_df.empty = False # Simulate a non-empty DataFrame
        mock_df.shape = (5, 2)
        mock_df.columns = ['col1', 'col2']

        mock_head_df = MagicMock(spec=pd.DataFrame) # Mock the DataFrame returned by head()
        mock_head_df.to_html.return_value = "<table>mock head</table>"
        mock_df.head.return_value = mock_head_df

        # Mock info() - it writes to a buffer
        def mock_df_info_side_effect(buf=None, **kwargs):
            if buf is not None: # Check if a buffer is provided
                buf.write("mock dataframe info content")
            # If no buffer, info() usually prints to stdout, which we don't capture here.
            # The view passes a buffer, so this should work.
        mock_df.info = MagicMock(side_effect=mock_df_info_side_effect)

        mock_describe_df = MagicMock(spec=pd.DataFrame) # Mock the DataFrame returned by describe()
        mock_describe_df.to_html.return_value = "<table>mock describe</table>"
        mock_df.describe.return_value = mock_describe_df

        mock_numeric_df = MagicMock(spec=pd.DataFrame) # Mock for select_dtypes
        mock_numeric_df.columns = ['col1']
        mock_df.select_dtypes.return_value = mock_numeric_df

        mock_value_counts_series = MagicMock(spec=pd.Series) # Mock for value_counts()
        mock_value_counts_frame = MagicMock(spec=pd.DataFrame) # Mock for to_frame()
        mock_value_counts_frame.to_html.return_value = "<table>mock value counts</table>"
        mock_value_counts_series.to_frame.return_value = mock_value_counts_frame

        mock_column_series = MagicMock(spec=pd.Series)
        mock_column_series.name = 'col1'
        mock_column_series.value_counts.return_value = mock_value_counts_series
        mock_df.__getitem__.return_value = mock_column_series

        mock_isnull_sum_series = MagicMock(spec=pd.Series) # Mock for isnull().sum()
        mock_isnull_sum_frame = MagicMock(spec=pd.DataFrame) # Mock for to_frame()
        mock_isnull_sum_frame.to_html.return_value = "<table>mock nulls</table>"
        mock_isnull_sum_series.to_frame.return_value = mock_isnull_sum_frame
        mock_df.isnull.return_value.sum.return_value = mock_isnull_sum_series

        mock_df.duplicated.return_value.sum.return_value = 0

        mock_read_csv.return_value = mock_df # Ensure read_csv returns the DataFrame mock
        # --- End Mock DataFrame ---

        csv_content = b"header1,header2\nvalue1,value2"
        csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")

        temp_media_root = os.path.join(settings.BASE_DIR, 'test_media_root_temp_data_analyser')
        if not os.path.exists(temp_media_root):
            os.makedirs(temp_media_root)

        with override_settings(MEDIA_ROOT=temp_media_root):
            response = self.client.post(reverse('demos:data_analyser'), {'csv_file': csv_file})

            self.assertEqual(response.status_code, 200)
            self.assertIn('analysis_results', response.context)
            #self.assertIsNotNone(response.context.get('analysis_results'),
             #                    f"analysis_results context should not be None. Error: {response.context.get('error_message')}")

            analysis_results = response.context.get('analysis_results')
            if analysis_results:
                self.assertEqual(analysis_results.get('filename'), "test.csv")
                self.assertIn("<table>mock head</table>", analysis_results.get('head', ''))
                self.assertTrue(isinstance(analysis_results.get('info'), str))
                self.assertEqual(analysis_results.get('info'), "mock dataframe info content")
                self.assertIn("<table>mock describe</table>", analysis_results.get('describe', ''))
                self.assertIn("<table>mock nulls</table>", analysis_results.get('null_counts', ''))
                self.assertEqual(analysis_results.get('duplicate_count'), 0)
                self.assertTrue(len(analysis_results.get('plot_urls', [])) > 0)

            #self.assertIsNone(response.context.get('error_message'))
            #mock_savefig.assert_called()
            mock_makedirs.assert_called()

        if os.path.exists(temp_media_root):
            shutil.rmtree(temp_media_root)


    @patch('demos.views.DATA_LIBS_AVAILABLE', False)
    def test_data_analyser_view_libs_not_available(self):
        response = self.client.get(reverse('demos:data_analyser'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Required libraries (Pandas, Matplotlib, Seaborn) not installed", response.context['error_message'])

    def test_explainable_ai_view_get(self):
        response = self.client.get(reverse('demos:explainable_ai'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'demos/explainable_ai_demo.html')
        self.assertIsInstance(response.context['form'], ExplainableAIDemoForm)

    @patch('demos.views.SKLEARN_AVAILABLE', True)
    @patch('demos.views.TREE_MODEL_LOADED', True)
    @patch('demos.views.decision_tree_model')
    @patch('demos.views.iris')
    def test_explainable_ai_view_post_valid(self, mock_iris, mock_tree_model):
        mock_iris.target_names = ['setosa', 'versicolor', 'virginica']
        mock_iris.feature_names = ['sl', 'sw', 'pl', 'pw']
        mock_tree_model.predict.return_value = [0]
        mock_tree_model.predict_proba.return_value = [[0.9, 0.05, 0.05]]
        mock_tree_model.feature_importances_ = [0.1, 0.2, 0.3, 0.4]
        mock_tree_model.decision_path.return_value = MagicMock()
        mock_tree_model.apply.return_value = MagicMock()
        mock_tree_model.tree_ = MagicMock()

        form_data = {'sepal_length': '5.1', 'sepal_width': '3.5', 'petal_length': '1.4', 'petal_width': '0.2'}
        response = self.client.post(reverse('demos:explainable_ai'), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['prediction'])
        self.assertEqual(response.context['prediction'], 'setosa')
        self.assertIsNotNone(response.context['probability_list'])
        self.assertEqual(len(response.context['probability_list']), 3)
        self.assertIsNotNone(response.context['feature_importances'])

    def test_keras_nmt_demo_view_get(self):
        response = self.client.get(reverse('demos:keras_nmt_demo'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'demos/keras_nmt_demo_page.html')
        self.assertEqual(response.context['page_title'], 'Neural Machine Translation with Keras')


# --- Sitemap Tests ---
@override_settings(BASE_DIR=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class DemoSitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.published_db_demo = Demo.objects.create(
            title="Sitemap Test Published Demo", slug="sitemap-test-published-demo",
            is_published=True, last_updated=timezone.now()
        )
        cls.draft_db_demo = Demo.objects.create(
            title="Sitemap Test Draft Demo", slug="sitemap-test-draft-demo",
            is_published=False, last_updated=timezone.now()
        )
        Demo.objects.create(title="CSV Test Demo For Sitemap", slug="csv-slug-for-sitemap", is_published=True)
        Demo.objects.create(title="CSV Demo Exists", slug="csv-slug-exists", is_published=True)


    def test_demo_model_sitemap_items(self):
        sitemap = DemoModelSitemap()
        sitemap_items = list(sitemap.items())
        self.assertIn(self.published_db_demo, sitemap_items)
        self.assertNotIn(self.draft_db_demo, sitemap_items)

    def test_demo_model_sitemap_lastmod(self):
        sitemap = DemoModelSitemap()
        self.assertEqual(sitemap.lastmod(self.published_db_demo), self.published_db_demo.last_updated)

    @patch('pandas.read_csv')
    @patch('demos.sitemaps.DEMO_MODEL_EXISTS', True)
    @patch('demos.sitemaps.Demo.objects.filter')
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

        self.assertEqual(len(items), 1, f"Expected 1 item, got {len(items)}. Items: {items}")
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
    @patch('demos.sitemaps.Demo.objects.filter')
    def test_csv_demo_pages_sitemap_location(self, mock_demo_filter):
        sitemap = CSVDemoPagesSitemap()

        item_dict_valid = {'slug': 'csv-slug-for-sitemap'}
        
        def side_effect_valid(slug, is_published):
            if slug == 'csv-slug-for-sitemap' and is_published:
                m = MagicMock(); m.exists.return_value = True; return m
            m = MagicMock(); m.exists.return_value = False; return m
        mock_demo_filter.side_effect = side_effect_valid

        expected_url = reverse('demos:generic_demo_detail', kwargs={'demo_slug': 'csv-slug-for-sitemap'})
        self.assertEqual(sitemap.location(item_dict_valid), expected_url)
        mock_demo_filter.assert_called_with(slug='csv-slug-for-sitemap', is_published=True)

        item_dict_invalid_demo = {'slug': 'slug-that-will-not-map-to-a-demo'}
        def side_effect_invalid(slug, is_published):
            if slug == 'slug-that-will-not-map-to-a-demo' and is_published:
                 m = MagicMock(); m.exists.return_value = False; return m
            m = MagicMock(); m.exists.return_value = True; return m
        mock_demo_filter.side_effect = side_effect_invalid

        self.assertEqual(sitemap.location(item_dict_invalid_demo), '',
                         "Location for a slug not mapping to a published Demo object should be empty.")
        mock_demo_filter.assert_called_with(slug='slug-that-will-not-map-to-a-demo', is_published=True)


    def test_hardcoded_demo_views_sitemap_items(self):
        sitemap = HardcodedDemoViewsSitemap()
        sitemap_url_names = sitemap.items()
        expected_hardcoded_items = [
            'demos:image_classifier', 'demos:sentiment_analyzer', 'demos:data_analyser',
            'demos:data_wrangler', 'demos:explainable_ai', 'demos:causal_inference',
            'demos:optimization_demo', 'demos:keras_nmt_demo'
        ]
        self.assertCountEqual(sitemap_url_names, expected_hardcoded_items,
                              "Sitemap items for hardcoded views do not match expected active URLs.")


    def test_hardcoded_demo_views_sitemap_location(self):
        sitemap = HardcodedDemoViewsSitemap()
        for item_url_name in sitemap.items():
            try:
                expected_url = reverse(item_url_name)
                self.assertEqual(sitemap.location(item_url_name), expected_url,
                                 f"Location for '{item_url_name}' should correctly reverse.")
            except NoReverseMatch:
                self.fail(f"Sitemap item '{item_url_name}' in HardcodedDemoViewsSitemap.items() does not reverse to a valid URL. Check demos/urls.py and sitemap definition.")


    def test_main_demos_page_sitemap(self):
        sitemap = MainDemosPageSitemap()
        self.assertEqual(sitemap.items(), ['demos:all_demos_list'])
        self.assertEqual(sitemap.location('demos:all_demos_list'), reverse('demos:all_demos_list'))

# --- Admin Tests ---
class DemoAdminTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('admin_demos_user', 'admin_demos@example.com', 'password')
        self.client.login(username='admin_demos_user', password='password')
        self.demo = Demo.objects.create(title="Admin Test Demo For Demos App", slug="admin-test-demo-slug-demos")

    def test_demo_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:demos_demo_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_demo_admin_add_accessible(self):
        response = self.client.get(reverse('admin:demos_demo_add'))
        self.assertEqual(response.status_code, 200)

    def test_demo_admin_change_view_accessible(self):
        response = self.client.get(reverse('admin:demos_demo_change', args=[self.demo.pk]))
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
    temp_demos_dir = os.path.join(settings.MEDIA_ROOT, 'temp_demos')
    test_media_root = getattr(settings, 'TEST_MEDIA_ROOT_TEMP_DATA_ANALYSER', None)
    if not test_media_root:
        test_media_root = os.path.join(settings.BASE_DIR, 'test_media_root_temp_data_analyser')


    if os.path.exists(temp_demos_dir):
        try:
            shutil.rmtree(temp_demos_dir)
        except OSError as e:
            print(f"Warning: Error removing temporary directory {temp_demos_dir}: {e}. Check permissions or lingering file locks.")

    if test_media_root and os.path.exists(test_media_root):
        try:
            shutil.rmtree(test_media_root)
        except OSError as e:
            print(f"Warning: Error removing temporary test media root {test_media_root}: {e}.")
