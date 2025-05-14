# portfolio/tests.py

from django.test import TestCase, Client, override_settings
from django.urls import reverse, resolve
from django.utils.text import slugify
from django.utils import timezone
from django.core import mail
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Q
from django.contrib import admin as django_admin_site
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.db import IntegrityError


from .models import Project, Certificate
from .forms import ContactForm
from . import views
from .sitemaps import StaticViewSitemap, ProjectSitemap
from .admin import ProjectAdmin, CertificateAdmin
import os
import shutil

# Import models from other apps safely for testing context
try:
    from skills.models import Skill
    SKILL_APP_EXISTS = True
except ImportError:
    Skill = None
    SKILL_APP_EXISTS = False

try:
    from topics.models import ProjectTopic
    TOPICS_APP_EXISTS = True
except ImportError:
    ProjectTopic = None
    TOPICS_APP_EXISTS = False

try:
    from blog.models import BlogPost
    BLOG_APP_EXISTS = True
except ImportError:
    BlogPost = None
    BLOG_APP_EXISTS = False

try:
    from recommendations.models import RecommendedProduct
    RECOMMENDATIONS_APP_EXISTS = True
except ImportError:
    RecommendedProduct = None
    RECOMMENDATIONS_APP_EXISTS = False

try:
    from demos.models import Demo
    DEMOS_APP_EXISTS = True
except ImportError:
    Demo = None
    DEMOS_APP_EXISTS = False


# --- Helper function for creating dummy image/file ---
def create_dummy_file(name="dummy.txt", content=b"dummy content", content_type="text/plain"):
    """Creates a simple dummy file for upload tests."""
    return SimpleUploadedFile(name, content, content_type=content_type)

# --- Model Tests ---

class CertificateModelTests(TestCase):
    """Tests for the Certificate model."""

    def test_certificate_creation_and_defaults(self):
        """Test basic certificate creation, defaults, and string representation."""
        cert = Certificate.objects.create(title="Test Certificate", issuer="Test Issuer Inc.")
        self.assertEqual(str(cert), "Test Certificate - Test Issuer Inc.")
        self.assertEqual(cert.order, 0)
        self.assertIsNone(cert.date_issued)

        # For FileField/ImageField with null=True, if no file is set,
        # the field value is None, and .name on that None value's FieldFile descriptor
        # also results in None.
        self.assertIsNone(cert.certificate_file.name, "Unset FileField's name should be None if null=True")
        self.assertIsNone(cert.logo_image.name, "Unset ImageField's name should be None if null=True")
        # A more general check for an unassigned file:
        self.assertFalse(cert.certificate_file)
        self.assertFalse(cert.logo_image)


    def test_certificate_with_file_and_image(self):
        """Test certificate creation with file and image fields."""
        dummy_pdf = create_dummy_file("test_cert.pdf", b"file_content_pdf", "application/pdf")
        dummy_image = create_dummy_file("test_logo.png", b"file_content_image", "image/png")

        cert = Certificate.objects.create(
            title="Full Certificate",
            issuer="Full Issuer",
            date_issued=timezone.now().date(),
            certificate_file=dummy_pdf,
            logo_image=dummy_image,
            order=1
        )
        self.assertTrue(cert.certificate_file.name.startswith('certificate_files/test_cert'))
        self.assertTrue(cert.logo_image.name.startswith('certificate_logos/test_logo'))
        self.assertEqual(cert.order, 1)


    def test_certificate_ordering(self):
        """Test the default ordering of Certificate objects."""
        Certificate.objects.all().delete() # Clear existing
        cert1 = Certificate.objects.create(title="Cert B", issuer="Issuer", order=1, date_issued=timezone.now().date() - timezone.timedelta(days=1))
        cert2 = Certificate.objects.create(title="Cert A", issuer="Issuer", order=0, date_issued=timezone.now().date())
        cert3 = Certificate.objects.create(title="Cert C", issuer="Issuer", order=1, date_issued=timezone.now().date())

        certs = list(Certificate.objects.all())
        self.assertEqual(certs[0], cert2, "Cert A (order 0) should be first.")
        self.assertEqual(certs[1], cert3, "Cert C (order 1, newest) should be second.")
        self.assertEqual(certs[2], cert1, "Cert B (order 1, older) should be third.")


class ProjectModelTests(TestCase):
    """Tests for the Project model."""

    @classmethod
    def setUpTestData(cls):
        cls.skill_py = None
        if SKILL_APP_EXISTS and Skill:
            cls.skill_py = Skill.objects.create(name="Python Test Skill For Project")

        cls.topic_ml = None
        if TOPICS_APP_EXISTS and ProjectTopic:
            cls.topic_ml = ProjectTopic.objects.create(name="Machine Learning Test Topic For Project")

        cls.project1 = Project.objects.create(
            title="Test Project Alpha",
            description="Description for project alpha.",
            results_metrics="Achieved 95% accuracy.",
            challenges="Limited dataset.",
            lessons_learned="Feature engineering is crucial.",
            code_snippet="print('alpha test')",
            code_language="python",
            order=1,
            date_created=timezone.now().date() - timezone.timedelta(days=1)
        )
        if cls.skill_py:
            cls.project1.skills.add(cls.skill_py)
        if cls.topic_ml:
            cls.project1.topics.add(cls.topic_ml)

        cls.project2 = Project.objects.create(
            title="Test Project Beta",
            description="Description for project beta.",
            order=0
        )

    def test_project_creation_and_defaults(self):
        self.assertEqual(self.project1.title, "Test Project Alpha")
        self.assertEqual(self.project1.order, 1)
        self.assertEqual(self.project1.results_metrics, "Achieved 95% accuracy.")
        self.assertEqual(self.project1.code_language, "python")
        self.assertEqual(self.project2.order, 0)
        self.assertIsNotNone(self.project1.date_created)
        self.assertEqual(self.project1.technologies, "")

    def test_str_representation(self):
        self.assertEqual(str(self.project1), "Test Project Alpha")

    def test_slug_generation_and_uniqueness_on_save(self):
        self.assertEqual(self.project1.slug, "test-project-alpha")

        project_same_title = Project.objects.create(title="Test Project Alpha", description="Another one.")
        self.assertEqual(project_same_title.slug, "test-project-alpha-1", "Slug should be unique for same title.")

        # Test that a provided slug is used (and slugified if necessary by the model's save method)
        project_custom_slug = Project.objects.create(title="Custom Slug Project", slug="my-custom-slug-is-cool")
        self.assertEqual(project_custom_slug.slug, "my-custom-slug-is-cool", "Provided slug should be used and correctly formatted.")

        project_custom_slug_raw = Project.objects.create(title="Custom Slug Project Raw", slug="My Custom Slug RAW with spaces")
        self.assertEqual(project_custom_slug_raw.slug, "my-custom-slug-raw-with-spaces", "Provided raw slug should be slugified.")


        project_custom_slug_conflict = Project.objects.create(title="Another Custom", slug="my-custom-slug-is-cool")
        self.assertEqual(project_custom_slug_conflict.slug, "my-custom-slug-is-cool-1")

        self.project2.title = "Test Project Beta Updated"
        self.project2.slug = "" # Clear slug to force regeneration from new title
        self.project2.save()
        self.assertEqual(self.project2.slug, "test-project-beta-updated", "Slug should update if title changes and slug was auto-generated.")

        project_manual_slug = Project.objects.create(title="Manual Slug", slug="manual-slug-original")
        project_manual_slug.title = "Manual Slug Title Changed"
        project_manual_slug.save() # Slug should not change here because it was manually set
        self.assertEqual(project_manual_slug.slug, "manual-slug-original", "Manually set slug should not change on title update if it was already set.")


    def test_get_absolute_url(self):
        expected_url = reverse('portfolio:project_detail', kwargs={'slug': self.project1.slug})
        self.assertEqual(self.project1.get_absolute_url(), expected_url)

    def test_skills_relationship(self):
        if SKILL_APP_EXISTS and self.skill_py and hasattr(self.project1, 'skills'):
            self.assertEqual(self.project1.skills.count(), 1)
            self.assertIn(self.skill_py, self.project1.skills.all())
        elif SKILL_APP_EXISTS and not self.skill_py:
            self.fail("Skill model exists but skill_py was not created in setUpTestData.")
        else:
            self.skipTest("Skills app/model not found or configured for tests, or Project model has no 'skills' field.")

    def test_topics_relationship(self):
        if TOPICS_APP_EXISTS and self.topic_ml and hasattr(self.project1, 'topics'):
            self.assertEqual(self.project1.topics.count(), 1)
            self.assertIn(self.topic_ml, self.project1.topics.all())
        elif TOPICS_APP_EXISTS and not self.topic_ml:
            self.fail("ProjectTopic model exists but topic_ml was not created in setUpTestData.")
        else:
            self.skipTest("Topics app/model not found or configured for tests, or Project model has no 'topics' field.")

    def test_get_technologies_list_from_skills(self):
        if SKILL_APP_EXISTS and self.skill_py and hasattr(self.project1, 'skills'):
            self.assertListEqual(self.project1.get_technologies_list(), ["Python Test Skill For Project"])
        else:
            self.skipTest("Skills app/model not found or skill_py not available, or Project model has no 'skills' field.")

    def test_get_technologies_list_from_deprecated_field(self):
        project_with_tech_field = Project.objects.create(
            title="Old Tech Project",
            technologies="OldTech1, OldTech2"
        )
        if SKILL_APP_EXISTS and hasattr(project_with_tech_field, 'skills'):
            project_with_tech_field.skills.clear()
        self.assertListEqual(project_with_tech_field.get_technologies_list(), ["OldTech1", "OldTech2"])

    def test_get_technologies_list_empty(self):
        project_no_tech = Project.objects.create(title="No Tech Project")
        if SKILL_APP_EXISTS and hasattr(project_no_tech, 'skills'):
            project_no_tech.skills.clear()
        project_no_tech.technologies = ""
        project_no_tech.save()
        self.assertListEqual(project_no_tech.get_technologies_list(), [])

    def test_project_ordering(self):
        projects = list(Project.objects.all())
        self.assertEqual(projects[0], self.project2, "Project Beta (order 0) should be first.")
        self.assertEqual(projects[1], self.project1, "Project Alpha (order 1) should be second.")


# --- Form Tests ---
class ContactFormTests(TestCase):
    def test_valid_contact_form(self):
        form_data = {'name': 'Test User', 'email': 'test@example.com', 'subject': 'Valid Subject', 'message': 'Valid message.'}
        form = ContactForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_contact_form_missing_required_fields(self):
        form_data = {'name': 'Test User'}
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('subject', form.errors)
        self.assertIn('message', form.errors)

    def test_invalid_contact_form_invalid_email(self):
        form_data = {'name': 'Test User', 'email': 'not-an-email', 'subject': 'Bad Email', 'message': 'Message'}
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertEqual(form.errors['email'][0], 'Enter a valid email address.')

    def test_contact_form_honeypot_field_not_required(self):
        form_data = {'name': 'Real User', 'email': 'real@example.com', 'subject': 'Real Subject', 'message': 'Real message.'}
        form = ContactForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data.get('honeypot'))

    def test_contact_form_with_honeypot_filled(self):
        form_data = {'name': 'Bot', 'email': 'bot@example.com', 'subject': 'Spam', 'message': 'Am a bot', 'honeypot': 'Gotcha'}
        form = ContactForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['honeypot'], 'Gotcha')


# --- View Tests ---
class PortfolioViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project1 = Project.objects.create(title="Homepage Project", description="Featured on homepage.", order=0)
        cls.project2 = Project.objects.create(title="Another Project", description="Not featured.", order=1, date_created=timezone.now().date() - timezone.timedelta(days=5))
        cls.project3 = Project.objects.create(title="Third Project ZZZ", description="For sorting test.", order=2, date_created=timezone.now().date() - timezone.timedelta(days=10))
        cls.cert1 = Certificate.objects.create(title="Homepage Cert", issuer="Issuer A", order=0)

        if BLOG_APP_EXISTS and BlogPost:
            cls.blog_post1 = BlogPost.objects.create(title="Latest Blog", content="Blog content", status='published', published_date=timezone.now())
        if RECOMMENDATIONS_APP_EXISTS and RecommendedProduct:
            cls.rec1 = RecommendedProduct.objects.create(name="Featured Rec", product_url="http://example.com/rec", order=0)
        if DEMOS_APP_EXISTS and Demo:
            cls.demo1 = Demo.objects.create(title="Featured Demo", slug="featured-demo-portfolio", is_published=True, is_featured=True, order=0)
        if TOPICS_APP_EXISTS and ProjectTopic:
            cls.topic1 = ProjectTopic.objects.create(name="Featured Topic Portfolio", slug="featured-topic-portfolio", order=0)
            cls.topic2 = ProjectTopic.objects.create(name="Other Topic Portfolio", slug="other-topic-portfolio", order=1)
            if hasattr(cls.project1, 'topics'): cls.project1.topics.add(cls.topic1)
            if hasattr(cls.project2, 'topics'): cls.project2.topics.add(cls.topic2)
        if SKILL_APP_EXISTS and Skill:
            cls.skill1 = Skill.objects.create(name="Featured Skill Portfolio", slug="featured-skill-portfolio", order=0)
            cls.skill2 = Skill.objects.create(name="Other Skill Portfolio", slug="other-skill-portfolio", order=1)
            if hasattr(cls.project1, 'skills'): cls.project1.skills.add(cls.skill1)
            if hasattr(cls.project3, 'skills'): cls.project3.skills.add(cls.skill1)
            if hasattr(cls.project2, 'skills'): cls.project2.skills.add(cls.skill2)


    def setUp(self):
        self.client = Client()
        # Ensure settings used by contact_view are present for tests
        settings.DEFAULT_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'test_sender@example.com')
        settings.EMAIL_HOST_USER = getattr(settings, 'EMAIL_HOST_USER', 'test_recipient@example.com')


    def test_index_view_status_and_template(self):
        response = self.client.get(reverse('portfolio:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/index.html')

    def test_index_view_context(self):
        response = self.client.get(reverse('portfolio:index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('featured_projects', response.context)
        self.assertIn('featured_certificates', response.context)
        self.assertIn('latest_blog_post', response.context)
        self.assertIn('featured_recommendations', response.context)
        self.assertIn('featured_topics', response.context)
        self.assertIn('featured_skills', response.context)
        self.assertIn('featured_demos', response.context)

        self.assertIn(self.project1, response.context['featured_projects'])
        self.assertIn(self.cert1, response.context['featured_certificates'])
        if BLOG_APP_EXISTS and BlogPost and hasattr(self, 'blog_post1'): self.assertEqual(response.context['latest_blog_post'], self.blog_post1)
        if RECOMMENDATIONS_APP_EXISTS and RecommendedProduct and hasattr(self, 'rec1'): self.assertIn(self.rec1, response.context['featured_recommendations'])
        if DEMOS_APP_EXISTS and Demo and hasattr(self, 'demo1'): self.assertIn(self.demo1, response.context['featured_demos'])
        if TOPICS_APP_EXISTS and ProjectTopic and hasattr(self, 'topic1'): self.assertIn(self.topic1, response.context['featured_topics'])
        if SKILL_APP_EXISTS and Skill and hasattr(self, 'skill1'): self.assertIn(self.skill1, response.context['featured_skills'])

    def test_index_view_context_empty_related_data(self):
        """Test index view context when related apps have no featured data."""
        # Delete all specific items created in setUpTestData
        Project.objects.all().delete()
        Certificate.objects.all().delete()
        if BlogPost: BlogPost.objects.all().delete()
        if RecommendedProduct: RecommendedProduct.objects.all().delete()
        if Demo: Demo.objects.all().delete() # Specifically delete Demos
        if ProjectTopic: ProjectTopic.objects.all().delete()
        if Skill: Skill.objects.all().delete()


        response = self.client.get(reverse('portfolio:index'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['featured_projects'])
        self.assertFalse(response.context['featured_certificates'])
        self.assertIsNone(response.context['latest_blog_post'])
        if RecommendedProduct: self.assertFalse(response.context['featured_recommendations'])
        if Demo: self.assertFalse(response.context['featured_demos'], "Featured demos should be empty after deletion.")
        if ProjectTopic: self.assertFalse(response.context['featured_topics'])
        if Skill: self.assertFalse(response.context['featured_skills'])


    def test_all_projects_view_status_template_and_initial_context(self):
        response = self.client.get(reverse('portfolio:all_projects'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/all_projects.html')
        self.assertIn('projects', response.context)
        self.assertEqual(response.context['projects'].count(), Project.objects.count())
        self.assertIn(self.project1, response.context['projects'])
        self.assertIn(self.project2, response.context['projects'])
        if SKILL_APP_EXISTS and Skill: self.assertIn('skills_list', response.context)
        if TOPICS_APP_EXISTS and ProjectTopic: self.assertIn('topics_list', response.context)
        self.assertEqual(response.context['current_sort'], '-date_created')

    def test_all_projects_view_filter_by_skill(self):
        if not (SKILL_APP_EXISTS and Skill and hasattr(self, 'skill1')):
            self.skipTest("Skills app not configured or no test skill available.")
        url = reverse('portfolio:all_projects') + f'?skill={self.skill1.slug}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        projects_in_context = response.context['projects']
        self.assertIn(self.project1, projects_in_context)
        self.assertIn(self.project3, projects_in_context)
        self.assertNotIn(self.project2, projects_in_context)
        self.assertEqual(projects_in_context.count(), 2)
        self.assertEqual(response.context['selected_skill_slug'], self.skill1.slug)

    def test_all_projects_view_filter_by_topic(self):
        if not (TOPICS_APP_EXISTS and ProjectTopic and hasattr(self, 'topic1')):
            self.skipTest("Topics app not configured or no test topic available.")
        url = reverse('portfolio:all_projects') + f'?topic={self.topic1.slug}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        projects_in_context = response.context['projects']
        self.assertIn(self.project1, projects_in_context)
        self.assertNotIn(self.project2, projects_in_context)
        self.assertEqual(projects_in_context.count(), 1)
        self.assertEqual(response.context['selected_topic_slug'], self.topic1.slug)

    def test_all_projects_view_filter_by_non_existent_skill_shows_message(self):
        if not (SKILL_APP_EXISTS and Skill):
            self.skipTest("Skills app not configured.")
        url = reverse('portfolio:all_projects') + '?skill=non-existent-skill-slug'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Skill filter 'non-existent-skill-slug' not found." in str(m) for m in messages_list),
                        "Expected warning message for non-existent skill filter not found.")
        self.assertIsNone(response.context['selected_skill_slug']) # Should be reset or None


    def test_all_projects_view_combined_filters(self):
        if not (SKILL_APP_EXISTS and Skill and TOPICS_APP_EXISTS and ProjectTopic and hasattr(self, 'skill1') and hasattr(self, 'topic1')):
            self.skipTest("Skills or Topics app not configured, or test data missing.")

        # project1 has skill1 and topic1
        # Create another project that also has skill1 and topic1
        combo_project = Project.objects.create(title="Combo Project Filter Test", description="Has skill1 and topic1", order=5)
        if hasattr(combo_project, 'skills'): combo_project.skills.add(self.skill1)
        if hasattr(combo_project, 'topics'): combo_project.topics.add(self.topic1)


        url = reverse('portfolio:all_projects') + f'?skill={self.skill1.slug}&topic={self.topic1.slug}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        projects_in_context = response.context['projects']

        self.assertIn(self.project1, projects_in_context)
        self.assertIn(combo_project, projects_in_context)
        self.assertNotIn(self.project2, projects_in_context)
        self.assertNotIn(self.project3, projects_in_context)
        self.assertEqual(projects_in_context.count(), 2)


    def test_all_projects_view_sorting(self):
        response_title_asc = self.client.get(reverse('portfolio:all_projects') + '?sort=title')
        projects_title_asc = list(response_title_asc.context['projects'])
        self.assertEqual(projects_title_asc[0].title, self.project2.title) # Another Project
        self.assertEqual(projects_title_asc[1].title, self.project1.title) # Homepage Project
        self.assertEqual(projects_title_asc[2].title, self.project3.title) # Third Project ZZZ

        response_order_asc = self.client.get(reverse('portfolio:all_projects') + '?sort=order')
        projects_order_asc = list(response_order_asc.context['projects'])
        self.assertEqual(projects_order_asc[0], self.project1)
        self.assertEqual(projects_order_asc[1], self.project2)
        self.assertEqual(projects_order_asc[2], self.project3)

    def test_all_projects_view_empty_state_with_filters(self):
        if not (SKILL_APP_EXISTS and Skill):
            self.skipTest("Skills app not configured.")

        # Create a skill that exists but isn't linked to any projects by default.
        # This ensures that the view's filter logic is tested for a valid skill
        # that happens to have no associated projects.
        empty_skill_slug = "skill-for-empty-filter-test"
        Skill.objects.create(name="Empty Filter Skill", slug=empty_skill_slug)

        url = reverse('portfolio:all_projects') + f'?skill={empty_skill_slug}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Because 'empty_skill_slug' corresponds to an existing Skill,
        # Skill.DoesNotExist should NOT be raised in the view.
        # The filter projects_qs = projects_qs.filter(skills=selected_skill) will execute.
        # Since no projects are linked to this "Empty Filter Skill",
        # response.context['projects'].exists() should be False.
        self.assertFalse(response.context['projects'].exists(),
                         "Projects queryset should be empty when a valid skill filter matches no projects.")
        self.assertContains(response, "No projects found matching your criteria.")

        # Verify that the warning message for a "not found" skill filter is NOT present,
        # as the skill does exist.
        messages_list = list(get_messages(response.wsgi_request))
        self.assertFalse(any(f"Skill filter '{empty_skill_slug}' not found." in str(m) for m in messages_list),
                         "Warning message for non-existent skill should not appear when skill exists.")


    def test_project_detail_view_success(self):
        response = self.client.get(reverse('portfolio:project_detail', kwargs={'slug': self.project1.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/project_detail.html')
        self.assertEqual(response.context['project'], self.project1)
        self.assertContains(response, self.project1.title)
        self.assertContains(response, self.project1.description)
        if TOPICS_APP_EXISTS and ProjectTopic and hasattr(self, 'topic1') and hasattr(self.project1, 'topics') and self.topic1 in self.project1.topics.all():
            self.assertContains(response, self.topic1.name)
        if SKILL_APP_EXISTS and Skill and hasattr(self, 'skill1') and hasattr(self.project1, 'skills') and self.skill1 in self.project1.skills.all():
            self.assertContains(response, self.skill1.name)
        self.assertIn('meta_description', response.context)
        self.assertIn('meta_keywords', response.context)
        self.assertTrue(self.project1.title.lower() in response.context['meta_keywords'])


    def test_project_detail_view_404_for_non_existent_slug(self):
        response = self.client.get(reverse('portfolio:project_detail', kwargs={'slug': 'slug-does-not-exist'}))
        self.assertEqual(response.status_code, 404)

    def test_certificates_view_status_template_and_context(self):
        response = self.client.get(reverse('portfolio:certificates'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/certificates.html')
        self.assertIn('certificates', response.context)
        self.assertIn(self.cert1, response.context['certificates'])

    def test_contact_view_get_request(self):
        response = self.client.get(reverse('portfolio:contact'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertIsInstance(response.context['form'], ContactForm)

    def test_contact_view_post_success(self):
        form_data = {'name': 'Test User', 'email': 'test@example.com', 'subject': 'Test Subject', 'message': 'Hello World'}
        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(reverse('portfolio:contact'), form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertContains(response, 'Message sent successfully! Thank you.')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Contact Form: Test Subject')
        self.assertEqual(mail.outbox[0].to, [settings.EMAIL_HOST_USER])
        self.assertEqual(mail.outbox[0].from_email, settings.DEFAULT_FROM_EMAIL)


    @override_settings(EMAIL_HOST_USER=None)
    def test_contact_view_post_email_config_error(self):
        form_data = {'name': 'Test User', 'email': 'test@example.com', 'subject': 'Config Error', 'message': 'Test'}
        with self.assertLogs('portfolio.views', level='ERROR') as cm:
            response = self.client.post(reverse('portfolio:contact'), form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertNotContains(response, 'Message sent successfully! Thank you.')
        self.assertEqual(len(mail.outbox), 0)
        # FIX: Check for the correct log message
        self.assertTrue(any("Contact form submission failed: EMAIL_HOST_USER not configured" in log_message for log_message in cm.output),
                        f"Expected log message not found. Logs: {cm.output}")


    def test_contact_view_post_invalid_data(self):
        form_data = {'name': '', 'email': 'not-an-email', 'subject': '', 'message': ''}
        response = self.client.post(reverse('portfolio:contact'), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertFormError(response.context['form'], 'name', 'This field is required.')
        self.assertFormError(response.context['form'], 'email', 'Enter a valid email address.')
        self.assertFormError(response.context['form'], 'subject', 'This field is required.')
        self.assertFormError(response.context['form'], 'message', 'This field is required.')
        self.assertEqual(len(mail.outbox), 0)

    def test_contact_view_post_honeypot_filled(self):
        form_data = {'name': 'Spambot', 'email': 'spam@example.com', 'subject': 'Buy Now', 'message': 'Click here!', 'honeypot': 'iamabot'}
        response = self.client.post(reverse('portfolio:contact'), form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertContains(response, 'Spam detected.')
        self.assertEqual(len(mail.outbox), 0)

    def test_static_content_views(self):
        static_views_to_test = {
            'portfolio:about_me': 'portfolio/about_me_page.html',
            'portfolio:cv': 'portfolio/cv_page.html',
            'portfolio:hire_me': 'portfolio/hire_me_page.html',
            'portfolio:privacy_policy': 'portfolio/privacy_policy.html',
            'portfolio:colophon': 'portfolio/colophon_page.html',
            'portfolio:accessibility': 'portfolio/accessibility_statement.html',
            'portfolio:terms': 'portfolio/terms_and_conditions.html',
        }
        for url_name, template_name in static_views_to_test.items():
            with self.subTest(view_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200, f"{url_name} did not return 200 OK.")
                self.assertTemplateUsed(response, template_name, f"{url_name} did not use template {template_name}.")
                if url_name == 'portfolio:privacy_policy': self.assertContains(response, "Privacy Policy")
                if url_name == 'portfolio:colophon': self.assertContains(response, "How This Site Was Built")


    def test_search_results_view_get_no_query(self):
        response = self.client.get(reverse('portfolio:search_results'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/search_results.html')
        self.assertEqual(response.context['query'], '')
        self.assertFalse(response.context['projects'].exists())
        if SKILL_APP_EXISTS and Skill:
            self.assertFalse(response.context['skills'].exists())
        else:
            self.assertIsNone(response.context['skills'])
        if TOPICS_APP_EXISTS and ProjectTopic:
            self.assertFalse(response.context['topics'].exists())
        else:
            self.assertIsNone(response.context['topics'])


    def test_search_results_view_with_query(self):
        query_term = "Homepage"
        response = self.client.get(reverse('portfolio:search_results') + f'?q={query_term}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['query'], query_term)

        self.assertIn(self.project1, response.context['projects'])
        if SKILL_APP_EXISTS and Skill: self.assertFalse(response.context['skills'].exists())
        if TOPICS_APP_EXISTS and ProjectTopic: self.assertFalse(response.context['topics'].exists())


    def test_search_results_view_no_results_found(self):
        query_term = "NonExistentTermXYZ123"
        response = self.client.get(reverse('portfolio:search_results') + f'?q={query_term}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['query'], query_term)
        self.assertFalse(response.context['projects'].exists())
        if SKILL_APP_EXISTS and Skill: self.assertFalse(response.context['skills'].exists())
        if TOPICS_APP_EXISTS and ProjectTopic: self.assertFalse(response.context['topics'].exists())
        self.assertContains(response, "No results found matching your query")


# --- URL Resolution Tests ---
class PortfolioURLTests(TestCase):
    def test_index_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:index')).func, views.index)

    def test_all_projects_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:all_projects')).func, views.all_projects_view)

    def test_project_detail_url_resolves(self):
        resolver = resolve(reverse('portfolio:project_detail', kwargs={'slug': 'any-project-slug'}))
        self.assertEqual(resolver.func, views.project_detail)
        self.assertEqual(resolver.kwargs['slug'], 'any-project-slug')

    def test_certificates_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:certificates')).func, views.certificates_view)

    def test_contact_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:contact')).func, views.contact_view)

    def test_about_me_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:about_me')).func, views.about_me_view)

    def test_cv_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:cv')).func, views.cv_view)

    def test_search_results_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:search_results')).func, views.search_results_view)

    def test_hire_me_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:hire_me')).func, views.hire_me_view)

    def test_privacy_policy_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:privacy_policy')).func, views.privacy_policy_view)

    def test_colophon_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:colophon')).func, views.colophon_page)

    def test_accessibility_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:accessibility')).func, views.accessibility_statement_view)

    def test_terms_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:terms')).func, views.terms_and_conditions_view)


# --- Sitemap Tests ---
class PortfolioSitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project1 = Project.objects.create(title="Sitemap Project", description="Desc", date_created=timezone.now().date())

    def test_static_view_sitemap_properties(self):
        sitemap = StaticViewSitemap()
        expected_items = [
            'portfolio:index', 'portfolio:all_projects', 'portfolio:certificates',
            'portfolio:contact', 'portfolio:about_me', 'portfolio:cv'
        ]
        self.assertListEqual(list(sitemap.items()), expected_items)
        for item_name in expected_items:
            self.assertEqual(sitemap.location(item_name), reverse(item_name))
        self.assertEqual(sitemap.priority, 0.8)
        self.assertEqual(sitemap.changefreq, 'weekly')

    def test_project_sitemap_properties(self):
        sitemap = ProjectSitemap()
        sitemap_items = list(sitemap.items())

        self.assertIn(self.project1, sitemap_items)
        self.assertEqual(len(sitemap_items), Project.objects.count())

        if self.project1 in sitemap_items:
            self.assertEqual(sitemap.location(self.project1), self.project1.get_absolute_url())
            self.assertEqual(sitemap.priority, 0.9)
            self.assertEqual(sitemap.changefreq, 'monthly')
            self.assertEqual(sitemap.lastmod(self.project1), self.project1.date_created)


# --- Admin Tests ---
class PortfolioAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser('admin_portfolio_user', 'admin_portfolio@example.com', 'password123')
        cls.project = Project.objects.create(title="Admin Test Project Portfolio", slug="admin-test-project-portfolio")
        cls.certificate = Certificate.objects.create(title="Admin Test Cert Portfolio", issuer="Admin Issuer Portfolio")

    def setUp(self):
        self.client.login(username='admin_portfolio_user', password='password123')

    def test_project_is_registered_with_correct_admin_class(self):
        self.assertIn(Project, django_admin_site.site._registry)
        self.assertIsInstance(django_admin_site.site._registry[Project], ProjectAdmin)

    def test_certificate_is_registered_with_correct_admin_class(self):
        self.assertIn(Certificate, django_admin_site.site._registry)
        self.assertIsInstance(django_admin_site.site._registry[Certificate], CertificateAdmin)

    def test_project_admin_options(self):
        self.assertEqual(ProjectAdmin.list_display, ('title', 'slug', 'order', 'is_featured'))

        expected_filter_horizontal = []
        # Correctly build expected_filter_horizontal based on app existence
        if SKILL_APP_EXISTS and Skill: expected_filter_horizontal.append('skills')
        if TOPICS_APP_EXISTS and ProjectTopic: expected_filter_horizontal.append('topics')
        # If only one app exists, filter_horizontal in admin.py might be ('skills',) or ('topics',)
        # If both exist, it's ('skills', 'topics'). If neither, it might be an empty tuple.
        # The original admin.py has: filter_horizontal = ('skills', 'topics',) if Skill else ('topics',)
        # This logic is a bit complex for a direct tuple comparison if Skill is None but ProjectTopic exists.
        # For simplicity, we'll check based on the actual ProjectAdmin.filter_horizontal
        self.assertEqual(ProjectAdmin.filter_horizontal, tuple(expected_filter_horizontal) if Skill else ('topics',) if ProjectTopic else tuple())


        self.assertEqual(ProjectAdmin.prepopulated_fields, {'slug': ('title',)})
        self.assertIn('title', ProjectAdmin.fieldsets[0][1]['fields'])
        if SKILL_APP_EXISTS and Skill and TOPICS_APP_EXISTS and ProjectTopic:
             self.assertIn('skills', ProjectAdmin.fieldsets[1][1]['fields'])
             self.assertIn('topics', ProjectAdmin.fieldsets[1][1]['fields'])
        elif TOPICS_APP_EXISTS and ProjectTopic: # If only topics app exists
             self.assertIn('topics', ProjectAdmin.fieldsets[1][1]['fields'])


    def test_certificate_admin_options(self):
        self.assertEqual(CertificateAdmin.list_display, ('title', 'issuer', 'date_issued', 'order', 'certificate_file'))
        self.assertEqual(CertificateAdmin.list_filter, ('issuer', 'date_issued'))
        self.assertEqual(CertificateAdmin.search_fields, ('title', 'issuer'))
        self.assertEqual(CertificateAdmin.list_editable, ('order',))
        self.assertEqual(CertificateAdmin.fields, ('title', 'issuer', 'date_issued', 'credential_url', 'certificate_file', 'order'))

    def test_project_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:portfolio_project_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_certificate_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:portfolio_certificate_changelist'))
        self.assertEqual(response.status_code, 200)

def tearDownModule():
    # Construct paths relative to settings.MEDIA_ROOT if defined, otherwise skip cleanup
    if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
        test_media_root_cert = os.path.join(settings.MEDIA_ROOT, 'certificate_files')
        test_media_root_logo = os.path.join(settings.MEDIA_ROOT, 'certificate_logos')

        # Clean up specific test directories if they exist
        if os.path.exists(test_media_root_cert):
            try:
                shutil.rmtree(test_media_root_cert)
            except OSError as e:
                print(f"Warning: Error removing {test_media_root_cert}: {e}")
        if os.path.exists(test_media_root_logo):
            try:
                shutil.rmtree(test_media_root_logo)
            except OSError as e:
                print(f"Warning: Error removing {test_media_root_logo}: {e}")
    else:
        print("Warning: settings.MEDIA_ROOT not defined. Skipping media cleanup in tearDownModule.")

