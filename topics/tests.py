# topics/tests.py

from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.utils.text import slugify
from django.utils import timezone
from django.contrib import admin as django_admin_site
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from django.db import IntegrityError

from .models import ProjectTopic
from . import views
from .admin import ProjectTopicAdmin
from .sitemaps import TopicListSitemap, TopicSitemap

# Import UserProfile from the portfolio app
from portfolio.models import UserProfile # <<< ADD THIS IMPORT

# Conditional import for portfolio.models.Project for view tests
try:
    from portfolio.models import Project as PortfolioProject
    PORTFOLIO_APP_AVAILABLE_FOR_TESTS = True
except ImportError:
    PortfolioProject = None
    PORTFOLIO_APP_AVAILABLE_FOR_TESTS = False


# --- Model Tests ---
class ProjectTopicModelTests(TestCase):
    def test_project_topic_creation_and_defaults(self):
        """Test basic ProjectTopic creation and default values."""
        topic = ProjectTopic.objects.create(name="Natural Language Processing Test Topic")
        self.assertEqual(topic.name, "Natural Language Processing Test Topic")
        self.assertEqual(str(topic), "Natural Language Processing Test Topic")
        self.assertEqual(topic.order, 0, "Default order should be 0.")
        self.assertTrue(topic.slug, "Slug should be auto-generated.")
        self.assertEqual(topic.slug, "natural-language-processing-test-topic")
        self.assertEqual(topic.description, "", "Default description should be empty.")

    def test_slug_generation_and_uniqueness_on_save(self):
        """Test slug generation logic, including uniqueness."""
        topic1 = ProjectTopic.objects.create(name="Web Dev Test Topic For Slug Model")
        self.assertEqual(topic1.slug, "web-dev-test-topic-for-slug-model")

        ProjectTopic.objects.create(name="Topic For Slug Clash A Original", slug="clash-topic-test-manual")
        topic_clash_b = ProjectTopic.objects.create(name="Topic For Slug Clash B New", slug="clash-topic-test-manual")
        self.assertEqual(topic_clash_b.slug, "clash-topic-test-manual-1", "Slug should be made unique for conflicting provided slugs.")

        custom_slug_raw = "My Custom Topic Slug Test with Spaces And Caps"
        expected_custom_slug = slugify(custom_slug_raw)
        topic_custom = ProjectTopic.objects.create(name="Custom Topic Name For Slug Test Model", slug=custom_slug_raw)
        self.assertEqual(topic_custom.slug, expected_custom_slug)

        topic_to_update = ProjectTopic.objects.create(name="Topic To Update Slug Original Name")
        existing_topic_for_clash = ProjectTopic.objects.create(name="Topic With Existing Target Slug Name")

        topic_to_update.slug = existing_topic_for_clash.slug
        topic_to_update.save()
        self.assertNotEqual(topic_to_update.slug, existing_topic_for_clash.slug)
        self.assertTrue(topic_to_update.slug.startswith(existing_topic_for_clash.slug))

        topic_manual_slug = ProjectTopic.objects.create(name="Manual Slug Topic Name Original", slug="manual-slug-topic-original")
        topic_manual_slug.name = "Manual Slug Topic Name Changed"
        topic_manual_slug.save()
        self.assertEqual(topic_manual_slug.slug, "manual-slug-topic-original")


    def test_name_unique_constraint(self):
        """Test that ProjectTopic name field has a unique constraint."""
        ProjectTopic.objects.create(name="A Truly Unique Topic Name For Constraint Test")
        with self.assertRaises(IntegrityError):
            ProjectTopic.objects.create(name="A Truly Unique Topic Name For Constraint Test")

    def test_get_absolute_url(self):
        """Test the get_absolute_url method."""
        topic = ProjectTopic.objects.create(name="Deep Learning Topic For Abs URL Test")
        expected_url = reverse('topics:topic_detail', kwargs={'topic_slug': topic.slug})
        self.assertEqual(topic.get_absolute_url(), expected_url)

    def test_ordering(self):
        """Test the default ordering of ProjectTopic objects."""
        ProjectTopic.objects.all().delete()
        topic_c_order2 = ProjectTopic.objects.create(name="Ordering Topic C Test Model", order=2)
        topic_a_order0 = ProjectTopic.objects.create(name="Ordering Topic A Test Model", order=0)
        topic_b_order0_name_beta = ProjectTopic.objects.create(name="Ordering Topic Beta Test Model", order=0)

        topics = list(ProjectTopic.objects.all())
        self.assertEqual(topics[0], topic_a_order0, "Topic A (order 0, name A) should be first.")
        self.assertEqual(topics[1], topic_b_order0_name_beta, "Topic Beta (order 0, name B) should be second.")
        self.assertEqual(topics[2], topic_c_order2, "Topic C (order 2) should be third.")

# --- View Tests ---
class ProjectTopicViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create UserProfile instance for tests in this class
        cls.user_profile_for_topics_tests = UserProfile.objects.create(
            full_name="Topics Test User",
            tagline="Testing the Topics App",
            email="topicstest@example.com",
            # site_identifier will default to "main_profile"
        )

        cls.client = Client()
        cls.items_per_page = 9
        cls.num_topics_to_create = 12

        for i in range(cls.num_topics_to_create):
            ProjectTopic.objects.create(name=f"View Test Topic {i+1:02d} Name For List", order=i)

        cls.topic_with_projects = ProjectTopic.objects.get(name="View Test Topic 01 Name For List")
        cls.topic_no_projects = ProjectTopic.objects.create(name="Empty Test Topic For Detail View", order=cls.num_topics_to_create + 1, description="Topic with no projects.")
        cls.total_topics_in_db = cls.num_topics_to_create + 1

        if PORTFOLIO_APP_AVAILABLE_FOR_TESTS and PortfolioProject is not None:
            cls.project1 = PortfolioProject.objects.create(title="Project Alpha for Topic Test View Detail", description="Desc Alpha")
            cls.project2 = PortfolioProject.objects.create(title="Project Beta for Topic Test View Detail", description="Desc Beta")
            if hasattr(cls.project1, 'topics') and hasattr(cls.topic_with_projects, 'projects'):
                # Assuming 'projects' is the related_name on ProjectTopic from Project's M2M field.
                # Or, if Project has a 'topics' M2M to ProjectTopic:
                cls.topic_with_projects.projects.add(cls.project1) # Use the correct related manager
                cls.topic_with_projects.projects.add(cls.project2)
        else:
            cls.project1 = None
            cls.project2 = None

    def test_topic_list_view_status_and_template(self):
        response = self.client.get(reverse('topics:topic_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'topics/topic_list.html')
        # Assert UserProfile is in context
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_topics_tests)

    def test_topic_list_view_context_and_pagination(self):
        response = self.client.get(reverse('topics:topic_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context, "Context should contain 'page_obj'.")
        self.assertIn('topics', response.context, "Context should contain 'topics' (aliased to page_obj).")
        self.assertEqual(response.context['page_title'], 'Project Topics')

        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj.object_list), min(self.items_per_page, self.total_topics_in_db))

        expected_first_topic_name = "View Test Topic 01 Name For List"
        self.assertEqual(page_obj.object_list[0].name, expected_first_topic_name, f"The first topic should be '{expected_first_topic_name}' based on 'order' field.")
        # Assert UserProfile is in context
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_topics_tests)


        response_invalid_page = self.client.get(reverse('topics:topic_list') + '?page=notanumber')
        self.assertEqual(response_invalid_page.context['page_obj'].number, 1)
        # Assert UserProfile is in context
        self.assertIn('user_profile', response_invalid_page.context)
        self.assertEqual(response_invalid_page.context['user_profile'], self.user_profile_for_topics_tests)


        response_out_of_range = self.client.get(reverse('topics:topic_list') + '?page=99999')
        self.assertEqual(response_out_of_range.context['page_obj'].number, page_obj.paginator.num_pages)
        # Assert UserProfile is in context
        self.assertIn('user_profile', response_out_of_range.context)
        self.assertEqual(response_out_of_range.context['user_profile'], self.user_profile_for_topics_tests)


    def test_topic_list_view_empty_state(self):
        ProjectTopic.objects.all().delete()
        response = self.client.get(reverse('topics:topic_list'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['page_obj'].object_list)
        self.assertContains(response, "No Topics Available")
        # Assert UserProfile is in context
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_topics_tests)


    def test_topic_detail_view_no_projects(self):
        response = self.client.get(reverse('topics:topic_detail', kwargs={'topic_slug': self.topic_no_projects.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'topics/topic_detail.html')
        self.assertEqual(response.context['topic'], self.topic_no_projects)
        self.assertIn('projects', response.context)
        if PORTFOLIO_APP_AVAILABLE_FOR_TESTS and ProjectTopic:
            self.assertFalse(response.context['projects'])
        else:
            self.assertIsNone(response.context['projects'])
        self.assertContains(response, self.topic_no_projects.name)
        self.assertContains(response, "No Projects Found")
        self.assertContains(response, self.topic_no_projects.description)
        # Assert UserProfile is in context
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_topics_tests)


    @patch('topics.views.PORTFOLIO_APP_EXISTS', False)
    def test_topic_detail_view_portfolio_app_disabled(self):
        response = self.client.get(reverse('topics:topic_detail', kwargs={'topic_slug': self.topic_with_projects.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'topics/topic_detail.html')
        self.assertEqual(response.context['topic'], self.topic_with_projects)
        self.assertIsNone(response.context['projects'], "Projects should be None when portfolio app is disabled.")
        # Assert UserProfile is in context
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_topics_tests)

    def test_topic_detail_view_404_non_existent_slug(self):
        url = reverse('topics:topic_detail', kwargs={'topic_slug': 'non-existent-topic-slug'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        # If 404.html uses user_profile, this test will pass because UserProfile is set up for the class.

# --- URL Tests ---
class ProjectTopicURLTests(TestCase):
    # No UserProfile setup needed here as these tests don't render templates.
    def test_topic_list_url_resolves_to_correct_view_func(self):
        url = reverse('topics:topic_list')
        self.assertEqual(resolve(url).func, views.topic_list)

    def test_topic_detail_url_resolves_to_correct_view_func(self):
        test_slug = "a-sample-topic-slug-for-url-test"
        url = reverse('topics:topic_detail', kwargs={'topic_slug': test_slug})
        resolver_match = resolve(url)
        self.assertEqual(resolver_match.func, views.topic_detail)
        self.assertEqual(resolver_match.kwargs['topic_slug'], test_slug)

# --- Admin Tests ---
class ProjectTopicAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create UserProfile for admin tests
        cls.user_profile_for_topics_admin_tests = UserProfile.objects.create(
            full_name="Topics Admin Test User",
            site_identifier="main_profile_topics_admin" # Unique identifier
        )
        cls.superuser = User.objects.create_superuser('admin_topic_user', 'admin_topic@example.com', 'password123')
        cls.topic = ProjectTopic.objects.create(name="Admin Test Topic For Admin Test")

    def setUp(self):
        self.client.login(username='admin_topic_user', password='password123')

    def test_projecttopic_is_registered_with_correct_admin_class(self):
        self.assertIn(ProjectTopic, django_admin_site.site._registry, "ProjectTopic should be registered.")
        self.assertIsInstance(django_admin_site.site._registry[ProjectTopic], ProjectTopicAdmin,
                              "ProjectTopic should be registered with ProjectTopicAdmin class.")

    def test_projecttopicadmin_modeladmin_options(self):
        self.assertEqual(ProjectTopicAdmin.list_display, ('name', 'order'))
        self.assertEqual(ProjectTopicAdmin.list_editable, ('order',))
        self.assertEqual(ProjectTopicAdmin.prepopulated_fields, {'slug': ('name',)})
        self.assertEqual(ProjectTopicAdmin.search_fields, ('name', 'description'))
        self.assertEqual(ProjectTopicAdmin.fields, ('name', 'slug', 'description', 'order'))

    def test_projecttopic_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:topics_projecttopic_changelist'))
        self.assertEqual(response.status_code, 200)
        # Assert UserProfile is in context if your admin base template uses it
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_topics_admin_tests)

    def test_projecttopic_admin_add_view_accessible(self):
        response = self.client.get(reverse('admin:topics_projecttopic_add'))
        self.assertEqual(response.status_code, 200)
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_topics_admin_tests)

    def test_projecttopic_admin_change_view_accessible(self):
        response = self.client.get(reverse('admin:topics_projecttopic_change', args=[self.topic.pk]))
        self.assertEqual(response.status_code, 200)
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_topics_admin_tests)


# --- Sitemap Tests ---
class TopicSitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create UserProfile for sitemap tests
        cls.user_profile_for_topics_sitemap_tests = UserProfile.objects.create(
            full_name="Topics Sitemap Test User",
            site_identifier="main_profile_topics_sitemap" # Unique identifier
        )
        cls.topic1 = ProjectTopic.objects.create(name="Sitemap Topic Alpha Test Model", order=0)
        cls.topic2 = ProjectTopic.objects.create(name="Sitemap Topic Beta Test Model", order=1)

    def test_topic_list_sitemap_properties(self):
        """Test properties of TopicListSitemap."""
        sitemap = TopicListSitemap()
        self.assertEqual(list(sitemap.items()), ['topics:topic_list'])
        self.assertEqual(sitemap.location('topics:topic_list'), reverse('topics:topic_list'))
        self.assertEqual(sitemap.priority, 0.6)
        self.assertEqual(sitemap.changefreq, 'monthly')

    def test_topic_sitemap_properties(self):
        """Test properties of TopicSitemap."""
        sitemap = TopicSitemap()
        sitemap_items = list(sitemap.items())
        self.assertIn(self.topic1, sitemap_items)
        self.assertIn(self.topic2, sitemap_items)
        self.assertEqual(len(sitemap_items), ProjectTopic.objects.count())

        # FIX: TopicSitemap does not define lastmod, and ProjectTopic model doesn't have a default last_updated field.
        # Verify that the sitemap class itself doesn't have a callable lastmod method.
        self.assertFalse(hasattr(sitemap, 'lastmod') and callable(getattr(sitemap, 'lastmod')),
                         "TopicSitemap should not have a callable lastmod method unless ProjectTopic model has a relevant date field and sitemap implements lastmod.")

        self.assertEqual(sitemap.location(self.topic1), self.topic1.get_absolute_url())
        self.assertEqual(sitemap.priority, 0.7)
        self.assertEqual(sitemap.changefreq, "monthly")
