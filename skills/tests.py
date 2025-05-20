# skills/tests.py

from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.utils.text import slugify
from django.utils import timezone
from django.contrib import admin as django_admin_site
from django.contrib.auth.models import User
from django.db import IntegrityError
from unittest.mock import patch, MagicMock

from .models import Skill, SkillCategory # Ensure Skill is imported for Skill.objects
from . import views
from .sitemaps import SkillsStaticSitemap, SkillSitemap
from .admin import SkillCategoryAdmin, SkillAdmin

# Attempt to import UserProfile for test setup
try:
    from portfolio.models import UserProfile
    USER_PROFILE_MODEL_AVAILABLE = True
except ImportError:
    UserProfile = None
    USER_PROFILE_MODEL_AVAILABLE = False

# Mock Project and Demo models for testing skill detail view context
class MockRelatedManager:
    def __init__(self, *items):
        self._items = list(items)
    def all(self):
        return self._items
    def prefetch_related(self, *args): # Add prefetch_related to allow chaining if necessary
        return self
    def count(self):
        return len(self._items)
    def exists(self):
        return bool(self._items)


class MockProject:
    def __init__(self, title, slug, description="Project desc"):
        self.pk = slugify(title)
        self.title = title
        self.slug = slug
        self.description = description
        # This 'topics' attribute is what prefetch_related('projects__topics') would look for on Project instances
        self.topics = MockRelatedManager() # Each MockProject can have its own topics

    def get_absolute_url(self):
        return f"/fake/project/{self.slug}/"
    def __str__(self):
        return self.title

class MockDemo:
    def __init__(self, title, slug, description="Demo desc"):
        self.pk = slugify(title)
        self.title = title
        self.slug = slug
        self.description = description

    def get_absolute_url(self):
        return f"/fake/demo/{self.slug}/"
    def __str__(self):
        return self.title

# --- Model Tests ---
class SkillCategoryModelTests(TestCase):
    def test_skill_category_creation_and_defaults(self):
        category = SkillCategory.objects.create(name="Programming Languages Test Cat")
        self.assertEqual(str(category), "Programming Languages Test Cat")
        self.assertEqual(category.order, 0)

    def test_skill_category_name_unique_constraint(self):
        SkillCategory.objects.create(name="Unique Category Name Constraint Test")
        with self.assertRaises(IntegrityError):
            SkillCategory.objects.create(name="Unique Category Name Constraint Test")

    def test_skill_category_ordering(self):
        SkillCategory.objects.all().delete()
        cat_b_order1 = SkillCategory.objects.create(name="Databases Test Cat", order=1)
        cat_a_order0 = SkillCategory.objects.create(name="Cloud Platforms Test Cat", order=0)
        cat_c_order1_alpha_name = SkillCategory.objects.create(name="Alpha Libs Test Cat", order=1)

        categories = list(SkillCategory.objects.all())
        self.assertEqual(categories[0], cat_a_order0)
        self.assertEqual(categories[1], cat_c_order1_alpha_name)
        self.assertEqual(categories[2], cat_b_order1)


class SkillModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category_frameworks = SkillCategory.objects.create(name="Frameworks Test Cat For Skill Model", order=1)
        Skill.objects.create(
            name="Django For Setup Test Skill Model",
            description="Testing the Django skill from setup.",
            category=cls.category_frameworks,
            order=1
        )

    def test_skill_creation_and_defaults(self):
        skill = Skill.objects.create(name="Python Language For Test Model", category=self.category_frameworks)
        self.assertEqual(str(skill), "Python Language For Test Model")
        self.assertEqual(skill.order, 0)
        self.assertEqual(skill.category, self.category_frameworks)
        self.assertTrue(skill.slug)
        self.assertEqual(skill.slug, "python-language-for-test-model")
        self.assertEqual(skill.description, "")

    def test_slug_generation_and_uniqueness_on_save(self):
        Skill.objects.create(name="Alpha Unique Skill Name For Slug Test")
        custom_slug_raw = "My Custom Skill Slug Test with Spaces And Caps"
        expected_custom_slug = slugify(custom_slug_raw)
        skill_custom = Skill.objects.create(name="Custom Name For Skill Test Slug", slug=custom_slug_raw)
        self.assertEqual(skill_custom.slug, expected_custom_slug)

        Skill.objects.create(name="Skill Original For Slug Clash", slug="shared-skill-slug-test-unique")
        skill_clash_b = Skill.objects.create(name="Skill New For Slug Clash", slug="shared-skill-slug-test-unique")
        self.assertEqual(skill_clash_b.slug, "shared-skill-slug-test-unique-1")

        skill_to_update = Skill.objects.create(name="Skill to Update Slug")
        existing_skill_slug_obj = Skill.objects.create(name="Skill With Existing Target Slug")
        existing_skill_slug = existing_skill_slug_obj.slug

        skill_to_update.slug = existing_skill_slug
        skill_to_update.save()
        self.assertNotEqual(skill_to_update.slug, existing_skill_slug)
        self.assertTrue(skill_to_update.slug.startswith(existing_skill_slug))

        skill_manual_slug = Skill.objects.create(name="Manual Slug Name", slug="manual-slug-original")
        skill_manual_slug.name = "Manual Slug Name Changed"
        skill_manual_slug.save()
        self.assertEqual(skill_manual_slug.slug, "manual-slug-original")

    def test_name_unique_constraint(self):
        Skill.objects.create(name="A Truly Unique Skill Name For Constraint Test Model")
        with self.assertRaises(IntegrityError):
            Skill.objects.create(name="A Truly Unique Skill Name For Constraint Test Model")

    def test_get_absolute_url(self):
        skill = Skill.objects.create(name="URL Test Skill For Abs Test Model")
        expected_url = reverse('skills:skill_detail', kwargs={'slug': skill.slug})
        self.assertEqual(skill.get_absolute_url(), expected_url)

    def test_skill_ordering(self):
        Skill.objects.all().delete()
        SkillCategory.objects.all().delete()
        cat_a0 = SkillCategory.objects.create(name="A Category", order=0)
        cat_b1 = SkillCategory.objects.create(name="B Category", order=1)
        cat_c1_alpha = SkillCategory.objects.create(name="Alpha C Category", order=1)

        s_uncat_a0 = Skill.objects.create(name="Uncat A", order=0)
        s_uncat_b1 = Skill.objects.create(name="Uncat B", order=1)
        s_cat_a0_s0 = Skill.objects.create(name="Skill A0S0", category=cat_a0, order=0)
        s_cat_a0_s1 = Skill.objects.create(name="Skill A0S1", category=cat_a0, order=1)
        s_cat_c1a_s0 = Skill.objects.create(name="Skill C1AS0", category=cat_c1_alpha, order=0)
        s_cat_b1_s0 = Skill.objects.create(name="Skill B1S0", category=cat_b1, order=0)

        skills = list(Skill.objects.all()) # Uses default model ordering
        expected_order = [s_uncat_a0, s_uncat_b1, s_cat_a0_s0, s_cat_a0_s1, s_cat_c1a_s0, s_cat_b1_s0]
        self.assertEqual(skills, expected_order, "Skills are not ordered as expected.")


# --- View Tests ---
class SkillViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        if USER_PROFILE_MODEL_AVAILABLE and UserProfile:
            try:
                cls.user_profile = UserProfile.objects.create(site_identifier="main_profile", full_name="Test User")
            except Exception:
                try:
                    cls.user_profile = UserProfile.objects.create(full_name="Test User")
                except Exception:
                    cls.user_profile = None
        else:
            cls.user_profile = None

        cls.cat_web = SkillCategory.objects.create(name="Web Dev Test Cat View List", order=0)
        cls.cat_data = SkillCategory.objects.create(name="Data Science Test Cat View List", order=1)
        cls.cat_empty = SkillCategory.objects.create(name="Empty Test Category View List", order=2)

        cls.skill_django = Skill.objects.create(name="Django Test View Detail", category=cls.cat_web, description="Desc Django.", order=0)
        cls.skill_python = Skill.objects.create(name="Python Test View List", category=cls.cat_web, order=1)
        cls.skill_pandas = Skill.objects.create(name="Pandas Test View List", category=cls.cat_data, order=0)
        cls.skill_uncategorized = Skill.objects.create(name="Uncategorized Test Skill View List", order=0)

    def test_skill_list_view_success(self):
        response = self.client.get(reverse('skills:skill_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'skills/skill_list.html')
        
        list_view_context = response.context[-1] if isinstance(response.context, list) else response.context

        self.assertIn('categories', list_view_context)
        self.assertIn('uncategorized_skills', list_view_context)
        self.assertEqual(list_view_context['page_title'], 'Technical Skills')

        categories_in_context = list_view_context['categories']
        self.assertEqual(categories_in_context.count(), 3)
        self.assertEqual(categories_in_context[0], self.cat_web)
        self.assertIn(self.skill_django, categories_in_context[0].skills.all())
        self.assertIn(self.skill_python, categories_in_context[0].skills.all())
        self.assertEqual(categories_in_context[1], self.cat_data)
        self.assertIn(self.skill_pandas, categories_in_context[1].skills.all())
        self.assertEqual(categories_in_context[2], self.cat_empty)
        self.assertFalse(categories_in_context[2].skills.exists())

        self.assertIn(self.skill_uncategorized, list_view_context['uncategorized_skills'])

    def test_skill_list_view_empty_states(self):
        Skill.objects.all().delete()
        SkillCategory.objects.all().delete()
        response_no_data = self.client.get(reverse('skills:skill_list'))
        self.assertEqual(response_no_data.status_code, 200)
        
        empty_list_context = response_no_data.context[-1] if isinstance(response_no_data.context, list) else response_no_data.context
        self.assertFalse(empty_list_context['categories'])
        self.assertFalse(empty_list_context['uncategorized_skills'])
        self.assertContains(response_no_data, "No Skills Added Yet")

        empty_cat = SkillCategory.objects.create(name="Empty Category For Test")
        response_cat_no_skills = self.client.get(reverse('skills:skill_list'))
        self.assertEqual(response_cat_no_skills.status_code, 200)
        cat_no_skills_context = response_cat_no_skills.context[-1] if isinstance(response_cat_no_skills.context, list) else response_cat_no_skills.context
        self.assertTrue(cat_no_skills_context['categories'])
        self.assertEqual(cat_no_skills_context['categories'][0], empty_cat)
        self.assertFalse(cat_no_skills_context['categories'][0].skills.exists())
        self.assertFalse(cat_no_skills_context['uncategorized_skills'])
        self.assertContains(response_cat_no_skills, "No specific skills listed in this category yet.")

    
    def test_skill_detail_view_404_non_existent_slug(self):
        url = reverse('skills:skill_detail', kwargs={'slug': 'non-existent-skill-slug'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

# --- URL Tests ---
# ... (rest of the file remains the same)
class SkillURLTests(TestCase):
    def test_skill_list_url_resolves_to_correct_view(self):
        url = reverse('skills:skill_list')
        self.assertEqual(resolve(url).func, views.skill_list)

    def test_skill_detail_url_resolves_to_correct_view(self):
        slug = "any-valid-skill-slug"
        url = reverse('skills:skill_detail', kwargs={'slug': slug})
        resolver_match = resolve(url)
        self.assertEqual(resolver_match.func, views.skill_detail)
        self.assertEqual(resolver_match.kwargs['slug'], slug)

# --- Sitemap Tests ---
class SkillSitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.skill1 = Skill.objects.create(name="Sitemap Skill For Test Sitemap 1 Model", description="Desc 1")
        cls.skill2 = Skill.objects.create(name="Sitemap Skill For Test Sitemap 2 Model", description="Desc 2")

    def test_skills_static_sitemap_properties(self):
        sitemap = SkillsStaticSitemap()
        self.assertEqual(list(sitemap.items()), ['skills:skill_list'])
        self.assertEqual(sitemap.location('skills:skill_list'), reverse('skills:skill_list'))
        self.assertEqual(sitemap.priority, 0.6)
        self.assertEqual(sitemap.changefreq, 'monthly')

    def test_skill_sitemap_properties(self):
        sitemap = SkillSitemap()
        sitemap_items = list(sitemap.items())
        self.assertIn(self.skill1, sitemap_items)
        self.assertIn(self.skill2, sitemap_items)
        self.assertEqual(len(sitemap_items), Skill.objects.count())
        self.assertFalse(hasattr(sitemap, 'lastmod') and callable(getattr(sitemap, 'lastmod', None)))
        self.assertEqual(sitemap.location(self.skill1), self.skill1.get_absolute_url())
        self.assertEqual(sitemap.priority, 0.7)
        self.assertEqual(sitemap.changefreq, "monthly")

# --- Admin Tests ---
class SkillAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser('admin_skill_user', 'admin_skill@example.com', 'password123')
        if USER_PROFILE_MODEL_AVAILABLE and UserProfile:
            try:
                UserProfile.objects.create(site_identifier="main_profile", full_name="Admin Test User")
            except Exception:
                pass
        cls.category = SkillCategory.objects.create(name="Admin Test Category For Skill Admin")
        cls.skill = Skill.objects.create(name="Admin Test Skill For Admin Test", category=cls.category)

    def setUp(self):
        self.client.login(username='admin_skill_user', password='password123')

    def test_skillcategory_is_registered_with_correct_admin_class(self):
        self.assertIn(SkillCategory, django_admin_site.site._registry)
        self.assertIsInstance(django_admin_site.site._registry[SkillCategory], SkillCategoryAdmin)

    def test_skill_is_registered_with_correct_admin_class(self):
        self.assertIn(Skill, django_admin_site.site._registry)
        self.assertIsInstance(django_admin_site.site._registry[Skill], SkillAdmin)

    def test_skillcategoryadmin_options(self):
        self.assertEqual(SkillCategoryAdmin.list_display, ('name', 'order'))
        self.assertEqual(SkillCategoryAdmin.list_editable, ('order',))

    def test_skilladmin_options(self):
        self.assertEqual(SkillAdmin.list_display, ('name', 'category', 'order'))
        self.assertEqual(SkillAdmin.list_filter, ('category',))
        self.assertEqual(SkillAdmin.search_fields, ('name', 'description'))
        self.assertEqual(SkillAdmin.list_editable, ('category', 'order'))
        self.assertEqual(SkillAdmin.prepopulated_fields, {'slug': ('name',)})

    def test_skillcategory_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:skills_skillcategory_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_skillcategory_admin_add_view_accessible(self):
        response = self.client.get(reverse('admin:skills_skillcategory_add'))
        self.assertEqual(response.status_code, 200)

    def test_skillcategory_admin_change_view_accessible(self):
        response = self.client.get(reverse('admin:skills_skillcategory_change', args=[self.category.pk]))
        self.assertEqual(response.status_code, 200)

    def test_skill_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:skills_skill_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_skill_admin_add_view_accessible(self):
        response = self.client.get(reverse('admin:skills_skill_add'))
        self.assertEqual(response.status_code, 200)

    def test_skill_admin_change_view_accessible(self):
        response = self.client.get(reverse('admin:skills_skill_change', args=[self.skill.pk]))
        self.assertEqual(response.status_code, 200)
