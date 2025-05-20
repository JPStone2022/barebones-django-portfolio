# portfolio/tests.py

from django.test import TestCase, Client, override_settings
from django.urls import reverse, resolve
from django.utils.text import slugify
from django.utils import timezone
from django.core import mail
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Q
from django.contrib import admin as django_admin_site # Renamed to avoid conflict
from django.contrib.auth.models import User
from django.contrib.messages import get_messages # Removed DEFAULT_LEVELS as it's not used directly
from django.db import IntegrityError


# Import models from this app
from .models import Project, Certificate, UserProfile, ColophonEntry
from .forms import ContactForm
from . import views # Import views to test view functions directly if needed for URL resolution checks
from .sitemaps import StaticViewSitemap, ProjectSitemap
# Import UserProfileAdmin if you intend to test its specifics
from .admin import ProjectAdmin, CertificateAdmin, UserProfileAdmin, ColophonEntryAdmin # Added ColophonEntryAdmin
import os
import shutil
import datetime # For datetime.fromisoformat
from datetime import timedelta # For form_load_time simulation

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

class UserProfileModelTests(TestCase):
    """Tests for the UserProfile model."""
    def test_user_profile_creation(self):
        """Test UserProfile creation and default site_identifier."""
        profile = UserProfile.objects.create(
            full_name="Test User Profile",
            tagline="Test Tagline",
            email="testprofile@example.com",
        )
        self.assertEqual(str(profile), "Test User Profile's Profile")
        self.assertEqual(profile.site_identifier, "main_profile")

    def test_user_profile_uniqueness_of_site_identifier(self):
        """Test that site_identifier must be unique."""
        UserProfile.objects.create(full_name="Profile 1", site_identifier="main_profile")
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(full_name="Profile 2", site_identifier="main_profile")


class CertificateModelTests(TestCase):
    """Tests for the Certificate model."""
    def test_certificate_creation_and_defaults(self):
        cert = Certificate.objects.create(title="Test Certificate", issuer="Test Issuer Inc.")
        self.assertEqual(str(cert), "Test Certificate - Test Issuer Inc.")
        self.assertEqual(cert.order, 0)
        self.assertIsNone(cert.date_issued)
        self.assertFalse(cert.certificate_file) # Check for falsy value for FileField
        self.assertFalse(cert.logo_image)     # Check for falsy value for ImageField

    def test_certificate_with_file_and_image(self):
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
        Certificate.objects.all().delete()
        cert1 = Certificate.objects.create(title="Cert B", issuer="Issuer", order=1, date_issued=timezone.now().date() - timezone.timedelta(days=1))
        cert2 = Certificate.objects.create(title="Cert A", issuer="Issuer", order=0, date_issued=timezone.now().date())
        cert3 = Certificate.objects.create(title="Cert C", issuer="Issuer", order=1, date_issued=timezone.now().date())
        certs = list(Certificate.objects.all())
        self.assertEqual(certs[0], cert2)
        self.assertEqual(certs[1], cert3)
        self.assertEqual(certs[2], cert1)


class ProjectModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        if SKILL_APP_EXISTS and Skill:
            cls.skill_py = Skill.objects.create(name="Python Test Skill For Project")
        else:
            cls.skill_py = None
        if TOPICS_APP_EXISTS and ProjectTopic:
            cls.topic_ml = ProjectTopic.objects.create(name="Machine Learning Test Topic For Project")
        else:
            cls.topic_ml = None

        cls.project1 = Project.objects.create(
            title="Test Project Alpha", description="Description for project alpha.",
            results_metrics="Achieved 95% accuracy.", challenges="Limited dataset.",
            lessons_learned="Feature engineering is crucial.", code_snippet="print('alpha test')",
            order=1, date_created=timezone.now().date() - timezone.timedelta(days=1)
        )
        if cls.skill_py and hasattr(cls.project1, 'skills'): cls.project1.skills.add(cls.skill_py)
        if cls.topic_ml and hasattr(cls.project1, 'topics'): cls.project1.topics.add(cls.topic_ml)

        cls.project2 = Project.objects.create(title="Test Project Beta", description="Description for project beta.", order=0)

    def test_project_creation_and_defaults(self):
        self.assertEqual(self.project1.title, "Test Project Alpha")
        self.assertEqual(self.project1.order, 1)
        self.assertEqual(self.project1.code_language, "python")

    def test_str_representation(self):
        self.assertEqual(str(self.project1), "Test Project Alpha")

    def test_slug_generation_and_uniqueness_on_save(self):
        self.assertEqual(self.project1.slug, "test-project-alpha")
        project_same_title = Project.objects.create(title="Test Project Alpha", description="Another one.")
        self.assertEqual(project_same_title.slug, "test-project-alpha-1")
        project_custom_slug = Project.objects.create(title="Custom Slug Project", slug="my-custom-slug-is-cool")
        self.assertEqual(project_custom_slug.slug, "my-custom-slug-is-cool")
        project_custom_slug_raw = Project.objects.create(title="Custom Slug Project Raw", slug="My Custom Slug RAW with spaces")
        self.assertEqual(project_custom_slug_raw.slug, "my-custom-slug-raw-with-spaces")
        project_custom_slug_conflict = Project.objects.create(title="Another Custom", slug="my-custom-slug-is-cool")
        self.assertEqual(project_custom_slug_conflict.slug, "my-custom-slug-is-cool-1")
        self.project2.title = "Test Project Beta Updated"; self.project2.slug = ""; self.project2.save()
        self.assertEqual(self.project2.slug, "test-project-beta-updated")

    def test_get_absolute_url(self):
        expected_url = reverse('portfolio:project_detail', kwargs={'slug': self.project1.slug})
        self.assertEqual(self.project1.get_absolute_url(), expected_url)

    def test_skills_relationship(self):
        if not (SKILL_APP_EXISTS and self.skill_py and hasattr(self.project1, 'skills')):
            self.skipTest("Skills app/model not configured or Project model has no 'skills' field.")
        self.assertIn(self.skill_py, self.project1.skills.all())

    def test_topics_relationship(self):
        if not (TOPICS_APP_EXISTS and self.topic_ml and hasattr(self.project1, 'topics')):
            self.skipTest("Topics app/model not configured or Project model has no 'topics' field.")
        self.assertIn(self.topic_ml, self.project1.topics.all())

    # def test_get_technologies_list_from_skills(self):
    #     if not (SKILL_APP_EXISTS and self.skill_py and hasattr(self.project1, 'skills')):
    #         self.skipTest("Skills app/model not configured or skill_py not available, or Project model has no 'skills' field.")
    #     self.assertListEqual(self.project1.get_technologies_list(), ["Python Test Skill For Project"])

    # def test_get_technologies_list_from_deprecated_field(self):
    #     project_with_tech_field = Project.objects.create(title="Old Tech Project", technologies="OldTech1, OldTech2")
    #     if SKILL_APP_EXISTS and hasattr(project_with_tech_field, 'skills'): project_with_tech_field.skills.clear()
    #     self.assertListEqual(project_with_tech_field.get_technologies_list(), ["OldTech1", "OldTech2"])

    # def test_get_technologies_list_empty(self):
    #     project_no_tech = Project.objects.create(title="No Tech Project")
    #     if SKILL_APP_EXISTS and hasattr(project_no_tech, 'skills'): project_no_tech.skills.clear()
    #     project_no_tech.technologies = ""
    #     project_no_tech.save()
    #     self.assertListEqual(project_no_tech.get_technologies_list(), [])

    def test_project_ordering(self):
        projects = list(Project.objects.all())
        self.assertEqual(projects[0], self.project2)
        self.assertEqual(projects[1], self.project1)

class ColophonEntryModelTests(TestCase):
    """Tests for the ColophonEntry model."""
    def test_colophon_entry_creation(self):
        entry = ColophonEntry.objects.create(
            name="Django",
            category="backend",
            description="The web framework used.",
            url="https://www.djangoproject.com/",
            order=1
        )
        self.assertEqual(str(entry), "Django")
        self.assertEqual(entry.category, "backend")
        self.assertEqual(entry.order, 1)

    def test_colophon_entry_ordering(self):
        ColophonEntry.objects.all().delete()
        entry1 = ColophonEntry.objects.create(name="Python", category="backend", order=0)
        entry2 = ColophonEntry.objects.create(name="JavaScript", category="frontend", order=0)
        entry3 = ColophonEntry.objects.create(name="PostgreSQL", category="database", order=0)
        entry4 = ColophonEntry.objects.create(name="Django", category="backend", order=1)

        entries = list(ColophonEntry.objects.all())
        # Expected: Python (backend, 0), Django (backend, 1), PostgreSQL (database, 0), JavaScript (frontend, 0)
        # Based on Meta: ordering = ['category', 'order', 'name']
        self.assertEqual(entries[0], entry1) # Python
        self.assertEqual(entries[1], entry4) # Django
        self.assertEqual(entries[2], entry3) # PostgreSQL
        self.assertEqual(entries[3], entry2) # JavaScript


# --- Form Tests ---
class ContactFormTests(TestCase):
    def test_valid_contact_form(self):
        form_load_time = timezone.now() - timedelta(seconds=10)
        form_data = {
            'name': 'Test User', 'email': 'test@example.com',
            'subject': 'Valid Subject', 'message': 'Valid message.',
            'form_load_time': form_load_time.isoformat()
        }
        form = ContactForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_json()}")

    def test_invalid_contact_form_missing_required_fields(self):
        form_data = {'name': 'Test User'} # Missing email, subject, message
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('subject', form.errors)
        self.assertIn('message', form.errors)

    def test_invalid_contact_form_invalid_email(self):
        form_load_time = timezone.now() - timedelta(seconds=10)
        form_data = {
            'name': 'Test User', 'email': 'not-an-email',
            'subject': 'Bad Email', 'message': 'Message',
            'form_load_time': form_load_time.isoformat()
            }
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertEqual(form.errors['email'][0], 'Enter a valid email address.')

    def test_contact_form_honeypot_field_not_required_and_empty(self):
        form_load_time = timezone.now() - timedelta(seconds=10)
        form_data = {
            'name': 'Real User', 'email': 'real@example.com',
            'subject': 'Real Subject', 'message': 'Real message.',
            'form_load_time': form_load_time.isoformat()
        }
        form = ContactForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_json()}")
        self.assertEqual(form.cleaned_data.get('honeypot'), "")


    def test_contact_form_with_honeypot_filled_is_invalid(self):
            form_load_time = timezone.now() - timedelta(seconds=10)
            form_data = {'name': 'Bot', 'email': 'bot@example.com', 'subject': 'Spam', 'message': 'Am a bot', 'honeypot': 'Gotcha', 'form_load_time': form_load_time.isoformat()}
            form = ContactForm(data=form_data)
            self.assertFalse(form.is_valid())
            self.assertIn('honeypot', form.errors)
            # Iterate through ValidationError instances to check the code
            found_spam_code = False
            # form.errors['honeypot'] is an ErrorList. Use .as_data() to get ValidationError instances
            for error_instance in form.errors['honeypot'].as_data(): 
                if hasattr(error_instance, 'code') and error_instance.code == 'spam_honeypot':
                    found_spam_code = True
                    break
            self.assertTrue(found_spam_code, "Error code 'spam_honeypot' not found for honeypot field.")
            # Check the message of the first error in the list for the honeypot field
            # The first item in form.errors['honeypot'] (which is an ErrorList) is the message string.
            # To check the message from the ValidationError object:
            self.assertEqual(form.errors['honeypot'].as_data()[0].message, "Spam detected (honeypot).")



    def test_form_load_time_initial_value(self):
        form = ContactForm()
        self.assertIsNotNone(form.fields['form_load_time'].initial)
        try:
            datetime.datetime.fromisoformat(form.fields['form_load_time'].initial)
        except ValueError:
            self.fail("Initial form_load_time is not a valid ISO format datetime string.")


# --- View Tests ---
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PortfolioViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfile.objects.create(full_name="Test Site Owner", email="owner@example.com")
        cls.project1 = Project.objects.create(title="Homepage Project", description="Featured on homepage.", order=0, is_featured=True)
        cls.project2 = Project.objects.create(title="Another Project", description="Not featured.", order=1)
        cls.project3 = Project.objects.create(title="Third Project ZZZ", description="For sorting test", order=2)
        cls.cert1 = Certificate.objects.create(title="Homepage Cert", issuer="Issuer A", order=0)
        cls.colophon_entry1 = ColophonEntry.objects.create(name="Test Backend Tool", category="backend", order=1)


        if BLOG_APP_EXISTS and BlogPost:
            cls.blog_post1 = BlogPost.objects.create(title="Latest Blog", content="Blog content", status='published', published_date=timezone.now())
        if RECOMMENDATIONS_APP_EXISTS and RecommendedProduct:
            cls.rec1 = RecommendedProduct.objects.create(name="Featured Rec", product_url="http://example.com/rec", order=0)
        if DEMOS_APP_EXISTS and Demo:
            cls.demo1 = Demo.objects.create(title="Featured Demo", slug="featured-demo-portfolio", is_published=True, is_featured=True, order=0)

        if TOPICS_APP_EXISTS and ProjectTopic:
            cls.topic1 = ProjectTopic.objects.create(name="Featured Topic Portfolio", slug="featured-topic-portfolio", order=0)
            cls.topic2 = ProjectTopic.objects.create(name="Another Topic Portfolio", slug="another-topic-portfolio", order=1)
            if hasattr(cls.project1, 'topics'): cls.project1.topics.add(cls.topic1)
            if hasattr(cls.project2, 'topics'): cls.project2.topics.add(cls.topic2)
            if hasattr(cls.project3, 'topics'): cls.project3.topics.add(cls.topic2)


        if SKILL_APP_EXISTS and Skill:
            cls.skill1 = Skill.objects.create(name="Featured Skill Portfolio", slug="featured-skill-portfolio", order=0)
            cls.skill2 = Skill.objects.create(name="Another Skill Portfolio", slug="another-skill-portfolio", order=1)
            if hasattr(cls.project1, 'skills'): cls.project1.skills.add(cls.skill1)
            if hasattr(cls.project3, 'skills'): cls.project3.skills.add(cls.skill1)
            if hasattr(cls.project2, 'skills'): cls.project2.skills.add(cls.skill2)


    def setUp(self):
        self.client = Client()
        mail.outbox = []
        if not hasattr(settings, 'EMAIL_HOST_USER') or not settings.EMAIL_HOST_USER:
            settings.EMAIL_HOST_USER = 'test_recipient@example.com'
        if not hasattr(settings, 'DEFAULT_FROM_EMAIL') or not settings.DEFAULT_FROM_EMAIL:
            settings.DEFAULT_FROM_EMAIL = 'test_sender@example.com'
        self.contact_url = reverse('portfolio:contact')
        self.all_projects_url = reverse('portfolio:all_projects')


    def test_index_view_status_template_and_context(self):
        response = self.client.get(reverse('portfolio:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/index.html')
        self.assertEqual(response.context.get('user_profile'), self.user_profile)
        self.assertIn('featured_projects', response.context)
        self.assertIn(self.project1, response.context['featured_projects'])
        self.assertIn('featured_certificates', response.context)
        self.assertIn(self.cert1, response.context['featured_certificates'])
        if BLOG_APP_EXISTS and hasattr(self, 'blog_post1'):
            self.assertEqual(response.context.get('latest_blog_post'), self.blog_post1)
        if RECOMMENDATIONS_APP_EXISTS and hasattr(self, 'rec1'):
            self.assertIn(self.rec1, response.context['featured_recommendations'])
        if DEMOS_APP_EXISTS and hasattr(self, 'demo1'):
            self.assertIn(self.demo1, response.context['featured_demos'])
        if TOPICS_APP_EXISTS and hasattr(self, 'topic1'):
            self.assertIn(self.topic1, response.context['featured_topics'])
        if SKILL_APP_EXISTS and hasattr(self, 'skill1'):
            self.assertIn(self.skill1, response.context['featured_skills'])

    def test_index_view_context_empty_related_data(self):
        # Temporarily delete data to test empty states
        Project.objects.all().delete()
        Certificate.objects.all().delete()
        if BlogPost: BlogPost.objects.all().delete()
        if RecommendedProduct: RecommendedProduct.objects.all().delete()
        if Demo: Demo.objects.all().delete()
        if ProjectTopic: ProjectTopic.objects.all().delete()
        if Skill: Skill.objects.all().delete()

        response = self.client.get(reverse('portfolio:index'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['featured_projects'])
        self.assertFalse(response.context['featured_certificates'])
        self.assertIsNone(response.context['latest_blog_post'])
        if RecommendedProduct: self.assertFalse(response.context['featured_recommendations'])
        if Demo: self.assertFalse(response.context['featured_demos'])
        if ProjectTopic: self.assertFalse(response.context['featured_topics'])
        if Skill: self.assertFalse(response.context['featured_skills'])

    def test_contact_view_get_request(self):
        response = self.client.get(self.contact_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertIsInstance(response.context['form'], ContactForm)
        self.assertIsNotNone(response.context['form'].fields['form_load_time'].initial)

    def test_contact_view_post_success(self):
        form_load_time = timezone.now() - timedelta(seconds=10)
        form_data = {'name': 'Test User', 'email': 'test@example.com', 'subject': 'Test Subject', 'message': 'Hello', 'form_load_time': form_load_time.isoformat()}
        response = self.client.post(self.contact_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200) 
        self.assertRedirects(response, self.contact_url, status_code=302, target_status_code=200, fetch_redirect_response=False)
        
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1, f"Expected 1 message, got {len(messages)}: {[str(m) for m in messages]}")
        self.assertEqual(str(messages[0]), 'Your message has been sent successfully! Thank you for reaching out.')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [settings.EMAIL_HOST_USER])

    @override_settings(EMAIL_HOST_USER=None, DEFAULT_FROM_EMAIL=None)
    def test_contact_view_post_email_config_error(self):
        form_load_time = timezone.now() - timedelta(seconds=10)
        form_data = {
            'name': 'Test User', 'email': 'test@example.com',
            'subject': 'Config Error', 'message': 'Test',
            'form_load_time': form_load_time.isoformat()
        }
        logger_name = views.logger.name
        with self.assertLogs(logger=logger_name, level='CRITICAL') as cm:
             response = self.client.post(self.contact_url, form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertContains(response, 'Could not send message due to a server configuration error.')
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(any("Contact form submission failed: EMAIL_HOST_USER or DEFAULT_FROM_EMAIL not configured" in log_message for log_message in cm.output))

    def test_contact_view_post_invalid_data_missing_fields(self):
        form_load_time = timezone.now() - timedelta(seconds=10)
        form_data = {
            'name': '', 'email': 'test@example.com',
            'subject': 'Incomplete', 'message': 'Some message',
            'form_load_time': form_load_time.isoformat()
        }
        response = self.client.post(self.contact_url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertFormError(response.context['form'], 'name', 'This field is required.')
        self.assertContains(response, "There were errors in your submission. Please check the fields below.")
        self.assertEqual(len(mail.outbox), 0)

    def test_contact_view_post_invalid_email_format(self):
        form_load_time = timezone.now() - timedelta(seconds=10)
        form_data = {
            'name': 'Test User', 'email': 'not-a-valid-email',
            'subject': 'Invalid Email Test', 'message': 'Message content',
            'form_load_time': form_load_time.isoformat()
        }
        response = self.client.post(self.contact_url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertFormError(response.context['form'], 'email', 'Enter a valid email address.')
        self.assertContains(response, "There were errors in your submission. Please check the fields below.")
        self.assertEqual(len(mail.outbox), 0)


    def test_contact_view_post_honeypot_filled(self):
        form_load_time = timezone.now() - timedelta(seconds=10)
        form_data = {
            'name': 'Spambot', 'email': 'spam@example.com',
            'subject': 'Buy Now', 'message': 'Click here!',
            'honeypot': 'iamabot',
            'form_load_time': form_load_time.isoformat()
        }
        response = self.client.post(self.contact_url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertContains(response, "There were errors in your submission. Please check the fields below.")
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('honeypot', response.context['form'].errors)
        self.assertEqual(len(mail.outbox), 0)

    def test_contact_view_post_missing_form_load_time(self):
        form_data = {
            'name': 'Test User', 'email': 'test@example.com',
            'subject': 'Missing Time', 'message': 'No timestamp here.'
        }
        response = self.client.post(self.contact_url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertContains(response, "Your form submission was incomplete or timed out. Please try again.")
        self.assertEqual(len(mail.outbox), 0)

    def test_contact_view_post_submission_too_quick(self):
        form_load_time = timezone.now() - timedelta(seconds=1)
        form_data = {
            'name': 'Fast User', 'email': 'fast@example.com',
            'subject': 'Too Quick', 'message': 'Very fast submission.',
            'form_load_time': form_load_time.isoformat()
        }
        response = self.client.post(self.contact_url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/contact_page.html')
        self.assertContains(response, "Submission failed. Please wait a moment and try again.")
        self.assertEqual(len(mail.outbox), 0)

    def test_all_projects_view_status_template_and_initial_context(self):
        response = self.client.get(self.all_projects_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/all_projects.html')
        self.assertIn(self.project1, response.context['projects'])
        self.assertIn(self.project2, response.context['projects'])
        if hasattr(self, 'project3'): self.assertIn(self.project3, response.context['projects'])
        if SKILL_APP_EXISTS and Skill: self.assertIn('skills_list', response.context)
        if TOPICS_APP_EXISTS and ProjectTopic: self.assertIn('topics_list', response.context)
        self.assertEqual(response.context['current_sort'], '-date_created')
        self.assertEqual(response.context['user_profile'], self.user_profile)


    def test_all_projects_view_filter_by_skill(self):
        if not (SKILL_APP_EXISTS and Skill and hasattr(self, 'skill1')):
            self.skipTest("Skills app not configured or no test skill available.")
        url = self.all_projects_url + f'?skill={self.skill1.slug}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        projects_in_context = response.context['projects']
        self.assertIn(self.project1, projects_in_context)
        if hasattr(self, 'project3'): self.assertIn(self.project3, projects_in_context)
        self.assertNotIn(self.project2, projects_in_context)
        expected_count = Project.objects.filter(skills=self.skill1).count()
        self.assertEqual(projects_in_context.count(), expected_count)
        self.assertEqual(response.context['selected_skill_slug'], self.skill1.slug)

    def test_all_projects_view_filter_by_topic(self):
        if not (TOPICS_APP_EXISTS and ProjectTopic and hasattr(self, 'topic1')):
            self.skipTest("Topics app not configured or no test topic available.")
        url = self.all_projects_url + f'?topic={self.topic1.slug}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        projects_in_context = response.context['projects']
        self.assertIn(self.project1, projects_in_context)
        self.assertNotIn(self.project2, projects_in_context)
        expected_count = Project.objects.filter(topics=self.topic1).count()
        self.assertEqual(projects_in_context.count(), expected_count)
        self.assertEqual(response.context['selected_topic_slug'], self.topic1.slug)

    def test_all_projects_view_filter_by_non_existent_skill_shows_message(self):
        if not (SKILL_APP_EXISTS and Skill):
            self.skipTest("Skills app not configured.")
        url = self.all_projects_url + '?skill=non-existent-skill-slug'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Skill filter 'non-existent-skill-slug' not found." in str(m) for m in messages_list))
        self.assertIsNone(response.context['selected_skill_slug'])

    def test_all_projects_view_combined_filters(self):
        if not (SKILL_APP_EXISTS and Skill and TOPICS_APP_EXISTS and ProjectTopic and hasattr(self, 'skill1') and hasattr(self, 'topic1')):
            self.skipTest("Skills or Topics app not configured, or test data missing.")
        
        # Ensure project1 has both skill1 and topic1 for this test
        if hasattr(self.project1, 'skills') and self.skill1: self.project1.skills.add(self.skill1)
        if hasattr(self.project1, 'topics') and self.topic1: self.project1.topics.add(self.topic1)
        self.project1.save()

        url = self.all_projects_url + f'?skill={self.skill1.slug}&topic={self.topic1.slug}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        projects_in_context = response.context['projects']
        self.assertIn(self.project1, projects_in_context)
        self.assertNotIn(self.project2, projects_in_context)
        if hasattr(self, 'project3'): self.assertNotIn(self.project3, projects_in_context) # project3 has skill1 but not topic1
        self.assertEqual(projects_in_context.count(), Project.objects.filter(skills=self.skill1, topics=self.topic1).count())


    def test_all_projects_view_sorting(self):
        response_title_asc = self.client.get(self.all_projects_url + '?sort=title')
        projects_title_asc = list(response_title_asc.context['projects'])
        self.assertEqual(projects_title_asc[0].title, self.project2.title) # Another Project
        self.assertEqual(projects_title_asc[1].title, self.project1.title) # Homepage Project
        self.assertEqual(projects_title_asc[2].title, self.project3.title) # Third Project ZZZ

        response_order_asc = self.client.get(self.all_projects_url + '?sort=order')
        projects_order_asc = list(response_order_asc.context['projects'])
        self.assertEqual(projects_order_asc[0], self.project1) # order 0
        self.assertEqual(projects_order_asc[1], self.project2) # order 1
        self.assertEqual(projects_order_asc[2], self.project3) # order 2

    def test_all_projects_view_empty_state_with_filters(self):
        if not (SKILL_APP_EXISTS and Skill):
            self.skipTest("Skills app not configured.")
        empty_skill_slug = "skill-for-empty-filter-test"
        Skill.objects.create(name="Empty Filter Skill", slug=empty_skill_slug)
        url = self.all_projects_url + f'?skill={empty_skill_slug}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['projects'].exists())
        # Assuming your template shows a message for no projects.
        # self.assertContains(response, "No projects found matching your criteria.")


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
        self.assertEqual(response.context['user_profile'], self.user_profile)


    def test_project_detail_view_404_for_non_existent_slug(self):
        response = self.client.get(reverse('portfolio:project_detail', kwargs={'slug': 'slug-does-not-exist'}))
        self.assertEqual(response.status_code, 404)

    def test_certificates_view_status_template_and_context(self):
        response = self.client.get(reverse('portfolio:certificates'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/certificates.html')
        self.assertIn('certificates', response.context)
        self.assertIn(self.cert1, response.context['certificates'])
        self.assertEqual(response.context['user_profile'], self.user_profile)

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
                self.assertTemplateUsed(response, template_name)
                self.assertEqual(response.context.get('user_profile'), self.user_profile)
                # Specific content checks for some pages
                if url_name == 'portfolio:colophon':
                     self.assertIn(self.colophon_entry1, response.context['grouped_entries']['Backend Technologies'])


    def test_search_results_view_get_no_query(self):
        response = self.client.get(reverse('portfolio:search_results'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['query'], '')
        self.assertFalse(response.context['projects'].exists())
        if SKILL_APP_EXISTS and Skill:
            self.assertQuerySetEqual(response.context.get('skills'), Skill.objects.none(), ordered=False)
        else:
            self.assertIsNone(response.context.get('skills')) # This path is taken if SKILL_APP_EXISTS is False
        if TOPICS_APP_EXISTS and ProjectTopic:
            self.assertQuerySetEqual(response.context.get('topics'), ProjectTopic.objects.none(), ordered=False)
        else:
            self.assertIsNone(response.context.get('topics')) # This path is taken if TOPICS_APP_EXISTS is False


    def test_search_results_view_with_query_matching_project(self):
        query_term = "Homepage" # Should match self.project1's title
        response = self.client.get(reverse('portfolio:search_results') + f'?q={query_term}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['query'], query_term)
        self.assertIn(self.project1, response.context['projects'])
        if SKILL_APP_EXISTS and Skill: self.assertFalse(response.context['skills'].exists())
        if TOPICS_APP_EXISTS and ProjectTopic: self.assertFalse(response.context['topics'].exists())
        self.assertEqual(response.context['user_profile'], self.user_profile)

    def test_search_results_view_with_query_matching_skill(self):
        if not (SKILL_APP_EXISTS and Skill and hasattr(self, 'skill1')):
            self.skipTest("Skill app/model not configured or skill1 not available.")
        query_term = self.skill1.name # "Featured Skill Portfolio"
        response = self.client.get(reverse('portfolio:search_results') + f'?q={query_term}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['query'], query_term)
        # This query might also match projects that have this skill
        # self.assertFalse(response.context['projects'].exists()) # This might be true or false depending on project descriptions
        self.assertIn(self.skill1, response.context['skills'])
        if TOPICS_APP_EXISTS and ProjectTopic: self.assertFalse(response.context['topics'].exists())


    def test_search_results_view_no_results_found(self):
        query_term = "NonExistentTermXYZ123"
        response = self.client.get(reverse('portfolio:search_results') + f'?q={query_term}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['query'], query_term)
        self.assertFalse(response.context['projects'].exists())
        if SKILL_APP_EXISTS and Skill: self.assertFalse(response.context['skills'].exists())
        if TOPICS_APP_EXISTS and ProjectTopic: self.assertFalse(response.context['topics'].exists())
        # Assuming your template has a message for no results
        # self.assertContains(response, "No results found matching your query")
        self.assertEqual(response.context['user_profile'], self.user_profile)


# --- URL Resolution Tests ---
class PortfolioURLTests(TestCase):
    def test_index_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:index')).func, views.index)
    def test_all_projects_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:all_projects')).func, views.all_projects_view)
    def test_project_detail_url_resolves(self):
        resolver = resolve(reverse('portfolio:project_detail', kwargs={'slug': 'any-slug'}))
        self.assertEqual(resolver.func, views.project_detail)
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
    def test_colophon_url_resolves(self): # Assuming colophon_page is the correct view
        self.assertEqual(resolve(reverse('portfolio:colophon')).func, views.colophon_page)
    def test_accessibility_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:accessibility')).func, views.accessibility_statement_view)
    def test_terms_url_resolves(self):
        self.assertEqual(resolve(reverse('portfolio:terms')).func, views.terms_and_conditions_view)


# --- Sitemap Tests ---
class PortfolioSitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        UserProfile.objects.create(full_name="Sitemap Test User")
        cls.project1 = Project.objects.create(title="Sitemap Project", description="Desc", date_created=timezone.now().date())

    def test_static_view_sitemap_properties(self):
        sitemap = StaticViewSitemap()
        expected_items = [
            'portfolio:index', 'portfolio:all_projects', 'portfolio:certificates',
            'portfolio:contact', 'portfolio:about_me', 'portfolio:cv',
            'portfolio:hire_me', 'portfolio:privacy_policy', 'portfolio:colophon',
            'portfolio:accessibility', 'portfolio:terms'
        ]
        self.assertCountEqual(list(sitemap.items()), expected_items)
        for item_name in expected_items:
            self.assertEqual(sitemap.location(item_name), reverse(item_name))

    def test_project_sitemap_properties(self):
        sitemap = ProjectSitemap()
        sitemap_items = list(sitemap.items())
        self.assertIn(self.project1, sitemap_items)
        self.assertEqual(len(sitemap_items), Project.objects.count())
        if self.project1 in sitemap_items:
            self.assertEqual(sitemap.location(self.project1), self.project1.get_absolute_url())
            self.assertEqual(sitemap.lastmod(self.project1), self.project1.date_created)


# --- Admin Tests ---
class PortfolioAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser('admin_portfolio_user', 'admin_portfolio@example.com', 'password123')
        UserProfile.objects.create(full_name="Admin Test User Profile", site_identifier="main_profile")
        cls.project = Project.objects.create(title="Admin Test Project Portfolio", slug="admin-test-project-portfolio")
        cls.certificate = Certificate.objects.create(title="Admin Test Cert Portfolio", issuer="Admin Issuer Portfolio")
        cls.colophon_entry = ColophonEntry.objects.create(name="Admin Colophon Test", category="backend")


    def setUp(self):
        self.client.login(username='admin_portfolio_user', password='password123')

    def test_user_profile_admin_is_registered(self):
        self.assertIn(UserProfile, django_admin_site.site._registry)
        self.assertIsInstance(django_admin_site.site._registry[UserProfile], UserProfileAdmin)

    def test_user_profile_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:portfolio_userprofile_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_user_profile_admin_add_permission_when_main_exists(self):
        user_profile_admin_instance = UserProfileAdmin(UserProfile, django_admin_site.site)
        class MockRequest: pass
        request = MockRequest()
        self.assertFalse(user_profile_admin_instance.has_add_permission(request))

    def test_project_is_registered_with_correct_admin_class(self):
        self.assertIn(Project, django_admin_site.site._registry)
        self.assertIsInstance(django_admin_site.site._registry[Project], ProjectAdmin)

    def test_certificate_is_registered_with_correct_admin_class(self):
        self.assertIn(Certificate, django_admin_site.site._registry)
        self.assertIsInstance(django_admin_site.site._registry[Certificate], CertificateAdmin)

    def test_colophon_entry_is_registered_with_correct_admin_class(self):
        self.assertIn(ColophonEntry, django_admin_site.site._registry)
        self.assertIsInstance(django_admin_site.site._registry[ColophonEntry], ColophonEntryAdmin)


    def test_project_admin_options(self):
        self.assertEqual(ProjectAdmin.list_display, ('title', 'slug', 'order', 'is_featured'))
        if SKILL_APP_EXISTS:
            self.assertIn('skills', ProjectAdmin.filter_horizontal)
            if TOPICS_APP_EXISTS: self.assertIn('topics', ProjectAdmin.filter_horizontal)
        elif TOPICS_APP_EXISTS:
            self.assertEqual(ProjectAdmin.filter_horizontal, ('topics',))
        else:
            self.assertEqual(ProjectAdmin.filter_horizontal, tuple())
        self.assertEqual(ProjectAdmin.prepopulated_fields, {'slug': ('title',)})

    def test_project_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:portfolio_project_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_certificate_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:portfolio_certificate_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_colophon_entry_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:portfolio_colophonentry_changelist'))
        self.assertEqual(response.status_code, 200)


def tearDownModule():
    if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
        test_media_dirs = [
            os.path.join(settings.MEDIA_ROOT, 'certificate_files'),
            os.path.join(settings.MEDIA_ROOT, 'certificate_logos'),
        ]
        for dir_path in test_media_dirs:
            if os.path.exists(dir_path):
                try:
                    shutil.rmtree(dir_path)
                except OSError as e:
                    print(f"Warning: Error removing test media directory {dir_path}: {e}")
    else:
        print("Warning: settings.MEDIA_ROOT not defined. Skipping media cleanup in tearDownModule.")

