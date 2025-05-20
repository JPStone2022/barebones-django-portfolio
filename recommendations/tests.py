# recommendations/tests.py

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse, resolve
from django.utils import timezone
from django.utils.text import slugify
from django.contrib import admin as django_admin_site
from django.contrib.auth.models import User 
from django.db import IntegrityError
from unittest.mock import patch 
from bs4 import BeautifulSoup # Import BeautifulSoup

from .models import RecommendedProduct, RecommendationSection
from . import views 
from .admin import RecommendedProductAdmin, RecommendationSectionAdmin, RecommendationSectionInline 
from .sitemaps import RecommendationStaticViewSitemap, RecommendedProductSitemap 
from .context_processors import recommendation_context 

from portfolio.models import UserProfile 

# --- Model Tests ---
class RecommendedProductModelTests(TestCase):
    """
    Tests for the RecommendedProduct model.
    """
    def test_recommended_product_creation_and_defaults(self):
        """Test basic creation, string representation, and default values."""
        product = RecommendedProduct.objects.create(
            name="Test Recommendation Book",
            short_description="A great book for learning.", # This is Markdown
            product_url="https://example.com/book",
            category="Book",
        )
        self.assertEqual(product.name, "Test Recommendation Book")
        self.assertEqual(str(product), "Test Recommendation Book")
        self.assertEqual(product.order, 0, "Default order should be 0.")
        self.assertTrue(product.slug, "Slug should be auto-generated.")
        self.assertEqual(product.slug, "test-recommendation-book") 
        self.assertIsNotNone(product.date_created)
        self.assertIsNotNone(product.last_updated)
        self.assertIsNone(product.main_description_md, "Default main_description_md should be None.")
        self.assertIsNone(product.page_meta_title, "Default page_meta_title should be None.")
        self.assertIsNone(product.image_url, "Default image_url should be None.")


    def test_slug_generation_and_uniqueness_on_save(self):
        """Test slug generation logic in the save method, including uniqueness."""
        prod1 = RecommendedProduct.objects.create(name="Unique Product Name!", product_url="url1")
        self.assertEqual(prod1.slug, "unique-product-name")

        prod2 = RecommendedProduct.objects.create(name="Unique Product Name!", product_url="url2")
        self.assertEqual(prod2.slug, "unique-product-name-1", "Second product with same name should have a suffixed slug.")

        prod_custom_slug = RecommendedProduct.objects.create(name="Custom Slug Product", slug="custom-slug", product_url="url3")
        self.assertEqual(prod_custom_slug.slug, "custom-slug")

        prod_custom_slug_conflict = RecommendedProduct.objects.create(name="Another Product", slug="custom-slug", product_url="url4")
        self.assertEqual(prod_custom_slug_conflict.slug, "custom-slug-1", "Conflicting provided slug should be made unique.")

        prod_custom_slug.name = "Custom Slug Product Updated"
        prod_custom_slug.save()
        self.assertEqual(prod_custom_slug.slug, "custom-slug", "Existing unique slug should not change on save.")

        prod1_slug = prod1.slug 
        prod_custom_slug.slug = "Unique Product Name!" 
        prod_custom_slug.save()
        self.assertTrue(prod_custom_slug.slug.startswith(slugify("Unique Product Name!")))
        self.assertNotEqual(prod_custom_slug.slug, prod1_slug)
        self.assertNotEqual(prod_custom_slug.slug, prod2.slug)


    def test_get_absolute_url(self):
        """Test the get_absolute_url method."""
        product = RecommendedProduct.objects.create(name="URL Test Product", product_url="url")
        expected_url = reverse('recommendations:recommendation_detail', kwargs={'slug': product.slug})
        self.assertEqual(product.get_absolute_url(), expected_url)

    def test_ordering(self):
        """Test the default ordering of RecommendedProduct objects."""
        RecommendedProduct.objects.all().delete() 
        prod_c = RecommendedProduct.objects.create(name="Product C", order=2, product_url="url_c")
        prod_a = RecommendedProduct.objects.create(name="Product A", order=0, product_url="url_a")
        prod_b_order0 = RecommendedProduct.objects.create(name="Product B", order=0, product_url="url_b") 

        products = list(RecommendedProduct.objects.all()) 
        self.assertEqual(products[0], prod_a, "Product A (order 0, name A) should be first.")
        self.assertEqual(products[1], prod_b_order0, "Product B (order 0, name B) should be second.")
        self.assertEqual(products[2], prod_c, "Product C (order 2) should be third.")


class RecommendationSectionModelTests(TestCase):
    """Tests for the RecommendationSection model."""

    @classmethod
    def setUpTestData(cls):
        cls.product1 = RecommendedProduct.objects.create(name="Main Product for Sections", product_url="url_main")

    def test_recommendation_section_creation(self):
        """Test RecommendationSection creation and its relationship to RecommendedProduct."""
        section = RecommendationSection.objects.create(
            recommendation=self.product1,
            section_order=1.0,
            section_title="Introduction Section",
            section_content_markdown="This is the intro markdown."
        )
        self.assertEqual(section.recommendation, self.product1)
        self.assertEqual(section.section_title, "Introduction Section")
        self.assertEqual(section.section_content_markdown, "This is the intro markdown.")
        self.assertEqual(RecommendationSection.objects.count(), 1)
        self.assertEqual(self.product1.sections.count(), 1)

    def test_recommendation_section_str_representation(self):
        """Test the __str__ method of the RecommendationSection model."""
        section = RecommendationSection.objects.create(
            recommendation=self.product1,
            section_order=1.5,
            section_title="Key Features"
        )
        expected_str = f"{self.product1.name} - Section 1.5 (Key Features)"
        self.assertEqual(str(section), expected_str)

        section_no_title = RecommendationSection.objects.create(recommendation=self.product1, section_order=2.0)
        expected_str_no_title = f"{self.product1.name} - Section 2.0 (Untitled)"
        self.assertEqual(str(section_no_title), expected_str_no_title)


    def test_recommendation_section_ordering(self):
        """Test the ordering of RecommendationSection objects."""
        RecommendationSection.objects.create(recommendation=self.product1, section_order=2.0, section_title="Section Two")
        RecommendationSection.objects.create(recommendation=self.product1, section_order=1.0, section_title="Section One")
        RecommendationSection.objects.create(recommendation=self.product1, section_order=1.5, section_title="Section One Point Five")

        sections = list(self.product1.sections.all()) 
        self.assertEqual(sections[0].section_title, "Section One")
        self.assertEqual(sections[1].section_title, "Section One Point Five")
        self.assertEqual(sections[2].section_title, "Section Two")

    def test_recommendation_section_unique_together_constraint(self):
        """Test unique_together constraint for (recommendation, section_order)."""
        RecommendationSection.objects.create(recommendation=self.product1, section_order=1.0, section_title="First Section")
        with self.assertRaises(IntegrityError):
            RecommendationSection.objects.create(recommendation=self.product1, section_order=1.0, section_title="Duplicate Order Section")

# --- View Tests ---
class RecommendationViewTests(TestCase):
    """
    Tests for the recommendation views (database-driven).
    """
    @classmethod
    def setUpTestData(cls):
        cls.user_profile_for_reco_tests = UserProfile.objects.create(
            full_name="Recommendations Test User",
            tagline="Testing Recommendations",
            email="recotest@example.com",
        )
        cls.client = Client() 
        cls.items_per_page = 9 
        cls.num_products_to_create = 12 

        for i in range(cls.num_products_to_create):
            RecommendedProduct.objects.create(
                name=f"Reco Product {i+1:02d}", 
                slug=f"reco-product-{i+1:02d}",
                product_url=f"http://example.com/product{i+1}",
                short_description=f"Short desc for product {i+1}", # This is Markdown
                order=i 
            )

        cls.product_with_sections = RecommendedProduct.objects.get(name="Reco Product 01")
        cls.section1 = RecommendationSection.objects.create(
            recommendation=cls.product_with_sections,
            section_order=1.0,
            section_title="First Section Title",
            section_content_markdown="**Bold content** for section 1." # Markdown
        )
        cls.section2 = RecommendationSection.objects.create(
            recommendation=cls.product_with_sections,
            section_order=2.0,
            section_title="Second Section Title",
            section_content_markdown="*Italic content* for section 2." # Markdown
        )

        cls.product_no_content = RecommendedProduct.objects.create(
            name="Product With No Content",
            slug="product-no-content",
            product_url="http://example.com/no-content",
            main_description_md=None, 
            short_description=None,   
            order=cls.num_products_to_create 
        )

        # Ensure a blank line for proper paragraph separation in Markdown
        # Ensure no leading whitespace before '#' for header
        cls.product_no_sections = RecommendedProduct.objects.create(
            name="Product Without Sections", # This will be the main H1 page title
            page_meta_title="Meta Title for Product Without Sections", # Explicitly set for clarity in test
            slug="product-without-sections",
            product_url="http://example.com/no-sections",
            main_description_md="# Main Markdown\n\nThis is the main markdown content.", 
            order=cls.num_products_to_create + 1
        )
        cls.total_products_in_db = RecommendedProduct.objects.count()


    def test_recommendation_list_view_status_and_template(self):
        response = self.client.get(reverse('recommendations:recommendation_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommendations/recommendation_list.html')
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_tests)


    def test_recommendation_list_view_context_and_pagination(self):
        response = self.client.get(reverse('recommendations:recommendation_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('recommendations' in response.context)
        self.assertEqual(response.context['page_title'], 'Recommendations')
        self.assertIsNone(response.context.get('error_message'))

        page_obj = response.context['recommendations']
        self.assertEqual(len(page_obj.object_list), min(self.items_per_page, self.total_products_in_db))
        self.assertEqual(page_obj.object_list[0].name, "Reco Product 01")
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_tests)

        if page_obj.has_next():
            response_page2 = self.client.get(reverse('recommendations:recommendation_list') + f'?page={page_obj.next_page_number()}')
            self.assertEqual(response_page2.status_code, 200)
            self.assertTrue(len(response_page2.context['recommendations'].object_list) > 0)
            self.assertIn('user_profile', response_page2.context)
            self.assertEqual(response_page2.context['user_profile'], self.user_profile_for_reco_tests)


    def test_recommendation_list_view_empty_state(self):
        RecommendedProduct.objects.all().delete() 
        response = self.client.get(reverse('recommendations:recommendation_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['recommendations'].object_list), 0)
        self.assertContains(response, "No Recommendations Available") 
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_tests)


    def test_recommendation_detail_view_with_sections_success(self):
        response = self.client.get(reverse('recommendations:recommendation_detail', kwargs={'slug': self.product_with_sections.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommendations/recommendation_detail.html')
        
        product_in_context = response.context.get('product')
        self.assertIsNotNone(product_in_context)
        self.assertEqual(product_in_context, self.product_with_sections)
        
        sections_from_product = list(product_in_context.sections.all().order_by('section_order'))
        self.assertEqual(len(sections_from_product), 2)
        self.assertEqual(sections_from_product[0].section_title, "First Section Title")
        self.assertEqual(sections_from_product[0].section_content_markdown, self.section1.section_content_markdown)
        
        self.assertContains(response, "<strong>Bold content</strong> for section 1.") 
        self.assertContains(response, "<em>Italic content</em> for section 2.") 
        
        soup = BeautifulSoup(response.content.decode(), 'html.parser')
        page_title_h1 = soup.select_one('article > header > h1.bg-clip-text') 
        self.assertIsNotNone(page_title_h1, "Main page title H1 not found.")
        if page_title_h1:
            expected_title = self.product_with_sections.page_meta_title or self.product_with_sections.name
            self.assertEqual(page_title_h1.get_text(strip=True), expected_title)
            
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_tests)


    # def test_recommendation_detail_view_with_main_description_success(self):
    #     response = self.client.get(reverse('recommendations:recommendation_detail', kwargs={'slug': self.product_no_sections.slug}))
    #     self.assertEqual(response.status_code, 200)
    #     product_in_context = response.context.get('product')
    #     self.assertIsNotNone(product_in_context)
    #     self.assertEqual(product_in_context, self.product_no_sections)
        
    #     # Verify the raw Markdown is what we expect
    #     self.assertEqual(product_in_context.main_description_md, "# Main Markdown\n\nThis is the main markdown content.")
        
    #     soup = BeautifulSoup(response.content.decode(), 'html.parser')

    #     # 1. Check the main page title (which is product.page_meta_title or product.name)
    #     page_title_h1 = soup.select_one('article > header > h1.bg-clip-text') 
    #     self.assertIsNotNone(page_title_h1, "Main page title H1 not found.")
    #     if page_title_h1:
    #         expected_page_title = self.product_no_sections.page_meta_title or self.product_no_sections.name
    #         self.assertEqual(page_title_h1.get_text(strip=True), expected_page_title,
    #                          f"Main page H1 content mismatch. Expected '{expected_page_title}', Found: '{page_title_h1.get_text(strip=True)}'")

    #     # 2. Check the H1 generated from main_description_md
    #     #    This content is rendered within a <section class="... prose ...">
    #     markdown_render_area = soup.select_one('article section.prose') 
    #     self.assertIsNotNone(markdown_render_area, 
    #                          "Section for main_description_md (with 'prose' class) not found. "
    #                          "Ensure template renders main_description_md inside a <section> with class 'prose'.")
        
    #     h1_from_markdown = None
    #     if markdown_render_area:
    #         h1_from_markdown = markdown_render_area.find('h1')
        
    #     self.assertIsNotNone(h1_from_markdown, 
    #                          "H1 tag generated from main_description_md not found within its prose section. "
    #                          f"Content of prose section: {markdown_render_area.prettify() if markdown_render_area else 'None'}")
    #     if h1_from_markdown:
    #         self.assertEqual(h1_from_markdown.get_text(strip=True), "Main Markdown", 
    #                          f"H1 from Markdown content mismatch. Found: '{h1_from_markdown.get_text(strip=True)}'")

    #     # 3. Check the paragraph generated from main_description_md
    #     self.assertContains(response, "<p>This is the main markdown content.</p>")

    #     self.assertEqual(product_in_context.sections.count(), 0) 
    #     self.assertIn('user_profile', response.context)
    #     self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_tests)


    def test_recommendation_detail_view_no_main_desc_no_sections(self):
        response = self.client.get(reverse('recommendations:recommendation_detail', kwargs={'slug': self.product_no_content.slug}))
        self.assertEqual(response.status_code, 200)
        product_in_context = response.context.get('product')
        self.assertIsNotNone(product_in_context)
        self.assertEqual(product_in_context, self.product_no_content)
        
        self.assertIsNone(product_in_context.main_description_md)
        self.assertEqual(product_in_context.sections.count(), 0) 
        
        self.assertContains(response, "No detailed content found for this recommendation.")
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_tests)

    # @patch('markdownify.templatetags.markdownify.markdown.markdown') 
    # def test_recommendation_detail_view_main_markdown_error(self, mock_markdown_call):
    #     """Test detail view when markdownify filter encounters an error."""
    #     mock_markdown_call.side_effect = Exception("Markdown processing failed!")
        
    #     with self.assertRaises(Exception) as cm:
    #         self.client.get(reverse('recommendations:recommendation_detail', kwargs={'slug': self.product_no_sections.slug}))
        
    #     self.assertEqual(str(cm.exception), "Markdown processing failed!")

    def test_recommendation_detail_view_404_for_non_existent_slug(self):
        response = self.client.get(reverse('recommendations:recommendation_detail', kwargs={'slug': 'this-slug-does-not-exist'}))
        self.assertEqual(response.status_code, 404)

# --- URL Tests ---
class RecommendationURLTests(TestCase):
    def test_recommendation_list_url_resolves(self):
        url = reverse('recommendations:recommendation_list')
        self.assertEqual(resolve(url).func, views.recommendation_list_view)

    def test_recommendation_detail_url_resolves(self):
        test_slug = "a-sample-slug-for-url-test"
        url = reverse('recommendations:recommendation_detail', kwargs={'slug': test_slug})
        resolver_match = resolve(url)
        self.assertEqual(resolver_match.func, views.recommendation_detail_view)
        self.assertEqual(resolver_match.kwargs['slug'], test_slug)

# --- Admin Tests ---
class RecommendationAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile_for_reco_admin_tests = UserProfile.objects.create(
            full_name="Recommendations Admin Test User",
            site_identifier="main_profile_reco_admin" 
        )
        cls.superuser = User.objects.create_superuser('admin_reco_user', 'admin_reco@example.com', 'password123')
        cls.product = RecommendedProduct.objects.create(name="Admin Test Product Reco", product_url="http://example.com/admin_reco")
        cls.section = RecommendationSection.objects.create(recommendation=cls.product, section_order=1, section_title="Admin Section Reco")

    def setUp(self):
        self.client.login(username='admin_reco_user', password='password123')

    def test_recommendedproduct_is_registered_with_admin(self):
        self.assertIn(RecommendedProduct, django_admin_site.site._registry)
        self.assertIsInstance(django_admin_site.site._registry[RecommendedProduct], RecommendedProductAdmin)

    def test_recommendationsection_is_registered_with_admin(self):
        self.assertIn(RecommendationSection, django_admin_site.site._registry)
        self.assertIsInstance(django_admin_site.site._registry[RecommendationSection], RecommendationSectionAdmin)

    def test_recommendedproductadmin_options(self):
        self.assertEqual(RecommendedProductAdmin.list_display, ('name', 'category', 'order', 'product_url', 'last_updated'))
        self.assertEqual(RecommendedProductAdmin.list_filter, ('category',))
        self.assertEqual(RecommendedProductAdmin.search_fields, ('name', 'short_description', 'main_description_md', 'category'))
        self.assertEqual(RecommendedProductAdmin.list_editable, ('order', 'category'))
        self.assertEqual(RecommendedProductAdmin.prepopulated_fields, {'slug': ('name',)})
        self.assertIn(RecommendationSectionInline, RecommendedProductAdmin.inlines) 
        self.assertTrue(any('name' in fs_options['fields'] for _, fs_options in RecommendedProductAdmin.fieldsets if fs_options.get('fields')))
        self.assertTrue(any('short_description' in fs_options['fields'] for _, fs_options in RecommendedProductAdmin.fieldsets if fs_options.get('fields')))

    def test_recommendationsectionadmin_options(self):
        self.assertEqual(RecommendationSectionAdmin.list_display, ('recommendation', 'section_order', 'section_title'))
        self.assertEqual(RecommendationSectionAdmin.list_filter, ('recommendation__category', 'recommendation__name'))
        self.assertEqual(RecommendationSectionAdmin.search_fields, ('section_title', 'section_content_markdown'))
        self.assertEqual(RecommendationSectionAdmin.autocomplete_fields, ['recommendation'])

    def test_recommendedproduct_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:recommendations_recommendedproduct_changelist'))
        self.assertEqual(response.status_code, 200)
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_admin_tests)

    def test_recommendedproduct_admin_add_view_accessible(self):
        response = self.client.get(reverse('admin:recommendations_recommendedproduct_add'))
        self.assertEqual(response.status_code, 200)
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_admin_tests)

    def test_recommendedproduct_admin_change_view_accessible(self):
        response = self.client.get(reverse('admin:recommendations_recommendedproduct_change', args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_admin_tests)

    def test_recommendationsection_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:recommendations_recommendationsection_changelist'))
        self.assertEqual(response.status_code, 200)
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_admin_tests)

    def test_recommendationsection_admin_add_view_accessible(self):
        response = self.client.get(reverse('admin:recommendations_recommendationsection_add'))
        self.assertEqual(response.status_code, 200)
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_admin_tests)

    def test_recommendationsection_admin_change_view_accessible(self):
        response = self.client.get(reverse('admin:recommendations_recommendationsection_change', args=[self.section.pk]))
        self.assertEqual(response.status_code, 200)
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_reco_admin_tests)

# --- Sitemap Tests ---
class RecommendationSitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile_for_reco_sitemap_tests = UserProfile.objects.create(
            full_name="Recommendations Sitemap Test User",
            site_identifier="main_profile_reco_sitemap" 
        )
        cls.prod1 = RecommendedProduct.objects.create(name="Sitemap Rec 1", product_url="url1", last_updated=timezone.now())
        cls.prod2 = RecommendedProduct.objects.create(name="Sitemap Rec 2", product_url="url2", last_updated=timezone.now() - timezone.timedelta(days=1))

    def test_recommendation_static_view_sitemap_properties(self):
        sitemap = RecommendationStaticViewSitemap()
        self.assertEqual(list(sitemap.items()), ['recommendations:recommendation_list'])
        self.assertEqual(sitemap.location('recommendations:recommendation_list'), reverse('recommendations:recommendation_list'))
        self.assertEqual(sitemap.priority, 0.7)
        self.assertEqual(sitemap.changefreq, 'weekly')

    def test_recommended_product_sitemap_properties(self):
        sitemap = RecommendedProductSitemap()
        sitemap_items = list(sitemap.items())
        self.assertIn(self.prod1, sitemap_items)
        self.assertIn(self.prod2, sitemap_items)
        self.assertEqual(len(sitemap_items), RecommendedProduct.objects.count())
        if self.prod1 in sitemap_items:
            self.assertEqual(sitemap.location(self.prod1), self.prod1.get_absolute_url())
            self.assertEqual(sitemap.lastmod(self.prod1), self.prod1.last_updated)
            self.assertEqual(sitemap.priority, 0.6)
            self.assertEqual(sitemap.changefreq, "monthly")

# --- Context Processor Tests ---
class RecommendationContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_recommendation_count_with_products(self):
        RecommendedProduct.objects.create(name="Prod Context 1", product_url="url_ctx1", order=1)
        RecommendedProduct.objects.create(name="Prod Context 2", product_url="url_ctx2", order=2)
        request = self.factory.get('/')
        context = recommendation_context(request)
        self.assertIn('recommendation_count', context)
        self.assertEqual(context['recommendation_count'], 2)

    def test_recommendation_count_no_products(self):
        RecommendedProduct.objects.all().delete() 
        request = self.factory.get('/')
        context = recommendation_context(request)
        self.assertIn('recommendation_count', context)
        self.assertEqual(context['recommendation_count'], 0)

    @patch('recommendations.context_processors.RecommendedProduct.objects.count')
    def test_recommendation_count_db_exception(self, mock_count):
        mock_count.side_effect = Exception("Database error")
        request = self.factory.get('/')
        with self.assertLogs('recommendations.context_processors', level='WARNING') as log_cm:
            context = recommendation_context(request)
            self.assertTrue(any("Could not query RecommendedProduct count" in message for message in log_cm.output))
        self.assertIn('recommendation_count', context)
        self.assertEqual(context['recommendation_count'], 0)

    @patch('recommendations.context_processors.RECOMMENDATIONS_APP_AVAILABLE', False)
    def test_recommendation_count_app_not_available(self):
        request = self.factory.get('/')
        context = recommendation_context(request)
        self.assertIn('recommendation_count', context)
        self.assertEqual(context['recommendation_count'], 0)

