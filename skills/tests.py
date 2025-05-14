# skills/tests.py

from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.utils.text import slugify
from django.utils import timezone 
from django.contrib import admin as django_admin_site
from django.contrib.auth.models import User 
from django.db import IntegrityError
from unittest.mock import patch, MagicMock

from .models import Skill, SkillCategory
from . import views 
from .sitemaps import SkillsStaticSitemap, SkillSitemap 
from .admin import SkillCategoryAdmin, SkillAdmin 

# Mock Project and Demo models for testing skill detail view context
class MockRelatedManager:
    def __init__(self, *items):
        self._items = list(items)
    def all(self):
        return self._items
    def prefetch_related(self, *args): 
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
        self.topics = MockRelatedManager() 

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
        """Test that SkillCategory name is unique."""
        SkillCategory.objects.create(name="Unique Category Name Constraint Test")
        with self.assertRaises(IntegrityError):
            SkillCategory.objects.create(name="Unique Category Name Constraint Test")

    def test_skill_category_ordering(self):
        SkillCategory.objects.all().delete() 
        cat_b_order1 = SkillCategory.objects.create(name="Databases Test Cat", order=1)
        cat_a_order0 = SkillCategory.objects.create(name="Cloud Platforms Test Cat", order=0)
        cat_c_order1_alpha_name = SkillCategory.objects.create(name="Alpha Libs Test Cat", order=1) 

        categories = list(SkillCategory.objects.all()) 
        self.assertEqual(categories[0], cat_a_order0, "Category with order 0 should be first.")
        self.assertEqual(categories[1], cat_c_order1_alpha_name, "Alpha Libs (order 1) should be second due to name.")
        self.assertEqual(categories[2], cat_b_order1, "Databases (order 1) should be third.")


class SkillModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category_frameworks = SkillCategory.objects.create(name="Frameworks Test Cat For Skill Model", order=1)
        cls.skill_django_setup = Skill.objects.create(
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
        self.assertTrue(skill.slug, "Slug should be auto-generated.")
        self.assertEqual(skill.slug, "python-language-for-test-model")
        self.assertEqual(skill.description, "", "Default description should be empty.")

    def test_slug_generation_and_uniqueness_on_save(self):
        skill_a = Skill.objects.create(name="Alpha Unique Skill Name For Slug Test")
        self.assertEqual(skill_a.slug, "alpha-unique-skill-name-for-slug-test")
        
        custom_slug_raw = "My Custom Skill Slug Test with Spaces And Caps"
        expected_custom_slug = slugify(custom_slug_raw) 
        skill_custom = Skill.objects.create(name="Custom Name For Skill Test Slug", slug=custom_slug_raw)
        # The model's save method will slugify the provided slug if it's not already.
        self.assertEqual(skill_custom.slug, expected_custom_slug)

        Skill.objects.create(name="Skill Original For Slug Clash", slug="shared-skill-slug-test-unique")
        skill_clash_b = Skill.objects.create(name="Skill New For Slug Clash", slug="shared-skill-slug-test-unique")
        self.assertEqual(skill_clash_b.slug, "shared-skill-slug-test-unique-1", "Slug should be made unique for conflicting provided slugs.")

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

        cat_a_order0 = SkillCategory.objects.create(name="A Category Ord Test Model", order=0)
        cat_b_order1 = SkillCategory.objects.create(name="B Category Ord Test Model", order=1)
        cat_c_order1_named_alpha = SkillCategory.objects.create(name="Alpha C Category Ord Test Model", order=1) 

        skill_uncat_a = Skill.objects.create(name="Uncategorized Skill A Model", order=0) 
        skill_uncat_b = Skill.objects.create(name="Uncategorized Skill B Model", order=1) 

        skill_cat_a_ord0 = Skill.objects.create(name="Skill A0 In Cat A Model", category=cat_a_order0, order=0)
        skill_cat_a_ord1 = Skill.objects.create(name="Skill A1 In Cat A Model", category=cat_a_order0, order=1)

        skill_cat_b_ord0 = Skill.objects.create(name="Skill B0 In Cat B Model", category=cat_b_order1, order=0)
        skill_cat_alpha_c_ord0 = Skill.objects.create(name="Skill C0 In Cat AlphaC Model", category=cat_c_order1_named_alpha, order=0)


        skills = list(Skill.objects.all()) 
        self.assertEqual(skills[0], skill_uncat_a)
        self.assertEqual(skills[1], skill_uncat_b)
        self.assertEqual(skills[2], skill_cat_a_ord0)
        self.assertEqual(skills[3], skill_cat_a_ord1)
        self.assertEqual(skills[4], skill_cat_alpha_c_ord0) 
        self.assertEqual(skills[5], skill_cat_b_ord0)


# --- View Tests ---
class SkillViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client() 
        cls.cat_web = SkillCategory.objects.create(name="Web Dev Test Cat View List", order=0)
        cls.cat_data = SkillCategory.objects.create(name="Data Science Test Cat View List", order=1)

        cls.skill_django = Skill.objects.create(name="Django Test View Detail", category=cls.cat_web, description="Desc Django.", order=0)
        cls.skill_python = Skill.objects.create(name="Python Test View List", category=cls.cat_web, order=1)
        cls.skill_pandas = Skill.objects.create(name="Pandas Test View List", category=cls.cat_data, order=0)
        cls.skill_uncategorized = Skill.objects.create(name="Uncategorized Test Skill View List", order=0) 

        cls.mock_project1 = MockProject(title="Web App Project For Skill View Detail", slug="web-app-project-skill-view-detail")
        cls.mock_project2 = MockProject(title="Another Project For Skill View Detail", slug="another-project-skill-view-detail")
        cls.mock_demo1 = MockDemo(title="Interactive Web Demo For Skill View Detail", slug="interactive-web-demo-skill-view-detail")

    def test_skill_list_view_success(self):
        """Test skill_list view returns 200 OK and correct context."""
        response = self.client.get(reverse('skills:skill_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'skills/skill_list.html')
        self.assertIn('categories', response.context)
        self.assertIn('uncategorized_skills', response.context)
        self.assertEqual(response.context['page_title'], 'Technical Skills')

        categories_in_context = response.context['categories']
        self.assertEqual(categories_in_context.count(), 2)
        self.assertEqual(categories_in_context[0], self.cat_web)
        self.assertIn(self.skill_django, categories_in_context[0].skills.all())
        self.assertIn(self.skill_python, categories_in_context[0].skills.all())
        self.assertEqual(categories_in_context[1], self.cat_data)
        self.assertIn(self.skill_pandas, categories_in_context[1].skills.all())

        uncategorized_in_context = response.context['uncategorized_skills']
        self.assertIn(self.skill_uncategorized, uncategorized_in_context)

    def test_skill_list_view_empty_states(self):
        """Test skill_list view with no categories or no skills."""
        Skill.objects.all().delete()
        SkillCategory.objects.all().delete()

        response = self.client.get(reverse('skills:skill_list'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['categories'])
        self.assertFalse(response.context['uncategorized_skills'])
        self.assertContains(response, "No Skills Added Yet") 

        SkillCategory.objects.create(name="Empty Category Test")
        response = self.client.get(reverse('skills:skill_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['categories'])
        self.assertFalse(response.context['uncategorized_skills'])
        self.assertContains(response, "No specific skills listed in this category yet.")

    def test_skill_detail_view_404_non_existent_slug(self):
        """Test skill_detail view returns 404 for a non-existent slug."""
        url = reverse('skills:skill_detail', kwargs={'slug': 'non-existent-skill-slug'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


# --- URL Tests ---
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
    def setUp(self):
        self.skill1 = Skill.objects.create(name="Sitemap Skill For Test Sitemap 1 Model", description="Desc 1")

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
        self.assertEqual(len(sitemap_items), Skill.objects.count())
        # FIX: SkillSitemap does not define lastmod, so calling it would be an error.
        # If lastmod is not defined on the sitemap class, we shouldn't test it.
        # self.assertIsNone(sitemap.lastmod(self.skill1)) # This line caused AttributeError
        # Instead, verify that the sitemap object itself doesn't have lastmod if not expected
        self.assertFalse(hasattr(sitemap, 'lastmod'), "SkillSitemap should not have a lastmod method by default if Skill model has no update timestamp field.")
        
        self.assertEqual(sitemap.location(self.skill1), self.skill1.get_absolute_url())
        self.assertEqual(sitemap.priority, 0.7)
        self.assertEqual(sitemap.changefreq, "monthly")


# --- Admin Tests ---
class SkillAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser('admin_skill_user', 'admin_skill@example.com', 'password123')
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
