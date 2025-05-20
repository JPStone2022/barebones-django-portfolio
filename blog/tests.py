# blog/tests.py

from django.test import TestCase, Client
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse, resolve
from django.contrib import admin as django_admin_site # Corrected import
from django.contrib.auth.models import User
from django.db import IntegrityError

from .models import BlogPost
from . import views # Import views from the current app
from .sitemaps import BlogStaticSitemap, BlogPostSitemap
from .admin import BlogPostAdmin

# Import UserProfile from the portfolio app
from portfolio.models import UserProfile # <<< ADD THIS IMPORT

# --- Model Tests ---
class BlogPostModelTests(TestCase):
    """
    Tests for the BlogPost model.
    """

    def test_blog_post_creation(self):
        """
        Test that a BlogPost instance can be created with all required fields
        and that default/auto fields are set correctly.
        """
        now = timezone.now()
        post = BlogPost.objects.create(title="My Test Post Model Create", content="Test content for model creation.")
        self.assertEqual(post.title, "My Test Post Model Create")
        self.assertEqual(post.content, "Test content for model creation.")
        self.assertEqual(post.status, "published", "Default status should be 'published'.")
        self.assertTrue(post.slug, "Slug should be auto-generated.")
        self.assertEqual(post.slug, "my-test-post-model-create")
        self.assertIsNotNone(post.published_date)
        # Allow for a small delta in time comparisons due to execution time
        self.assertTrue(now - timezone.timedelta(seconds=5) <= post.published_date <= now + timezone.timedelta(seconds=5))
        self.assertIsNotNone(post.created_date)
        self.assertIsNotNone(post.updated_date)

    def test_str_representation(self):
        """
        Test the __str__ method returns the post's title.
        """
        post = BlogPost.objects.create(title="A Readable Title For Str Test", content="Some text.")
        self.assertEqual(str(post), "A Readable Title For Str Test")

    def test_slug_auto_generation_if_not_provided(self):
        """
        Test that a slug is automatically generated from the title if not provided.
        """
        post = BlogPost.objects.create(title="A New Post Title For Slug Test!", content="Content here.")
        self.assertEqual(post.slug, "a-new-post-title-for-slug-test")

    def test_slug_uniqueness_auto_generated(self):
        """
        Test that automatically generated slugs are unique for posts with the same title.
        """
        post1 = BlogPost.objects.create(title="Unique Title For Auto Slug Test", content="Content 1")
        self.assertEqual(post1.slug, "unique-title-for-auto-slug-test")

        post2 = BlogPost.objects.create(title="Unique Title For Auto Slug Test", content="Content 2")
        self.assertEqual(post2.slug, "unique-title-for-auto-slug-test-1")

        post3 = BlogPost.objects.create(title="Unique Title For Auto Slug Test", content="Content 3")
        self.assertEqual(post3.slug, "unique-title-for-auto-slug-test-2")

    def test_slug_provided_is_used_and_slugified(self):
        """
        Test that if a slug is provided, it is used and correctly slugified by the model's save method.
        """
        # Test with an already good slug
        expected_slug_good = "my-custom-slug-is-already-good"
        post_good_slug = BlogPost.objects.create(title="Another Post For Custom Slug Test", slug=expected_slug_good, content="...")
        self.assertEqual(post_good_slug.slug, expected_slug_good)

        # Test with a raw string that needs slugification
        post_raw_slug = BlogPost.objects.create(title="Post With Raw Provided Slug", slug="raw provided slug with SPACES", content="...")
        self.assertEqual(post_raw_slug.slug, "raw-provided-slug-with-spaces") # Model's save() calls slugify(self.slug)

    def test_slug_uniqueness_with_provided_slug_conflict(self):
        """
        Test that if a provided slug (after slugification) conflicts, it's made unique.
        """
        BlogPost.objects.create(title="Post A Original Slug Test", slug="shared-slug-test-conflict", content="Content A")
        # The slug "shared-slug-test-conflict" will be used as is by the save method.

        post_b = BlogPost.objects.create(title="Post B New Slug Test", slug="shared-slug-test-conflict", content="Content B")
        self.assertNotEqual(post_b.slug, "shared-slug-test-conflict", "Slug should have been modified to ensure uniqueness.")
        self.assertTrue(post_b.slug.startswith("shared-slug-test-conflict-"), "Conflicting slug should be appended with a counter.")
        self.assertEqual(post_b.slug, "shared-slug-test-conflict-1")


    def test_get_absolute_url(self):
        """
        Test the get_absolute_url method.
        """
        post = BlogPost.objects.create(title="URL Test Post For Abs URL", content="Content.")
        # Slug will be 'url-test-post-for-abs-url'
        expected_url = reverse('blog:blog_post_detail', kwargs={'slug': post.slug})
        self.assertEqual(post.get_absolute_url(), expected_url)

    def test_ordering(self):
        """
        Test that posts are ordered by '-published_date' by default.
        """
        now = timezone.now()
        post1 = BlogPost.objects.create(title="Older Post Ordering Test", content="Content.", published_date=now - timezone.timedelta(days=1))
        post2 = BlogPost.objects.create(title="Newer Post Ordering Test", content="Content.", published_date=now)
        post3 = BlogPost.objects.create(title="Middle Post Ordering Test", content="Content.", published_date=now - timezone.timedelta(hours=12))

        posts = list(BlogPost.objects.all()) # Default ordering is applied here
        self.assertEqual(posts[0], post2, "Newest post should be first.")
        self.assertEqual(posts[1], post3, "Middle post should be second.")
        self.assertEqual(posts[2], post1, "Oldest post should be third.")

# --- View Tests ---
class BlogPostViewTests(TestCase):
    """
    Tests for the blog views.
    """
    @classmethod
    def setUpTestData(cls):
        # Create the UserProfile instance needed by the context processor
        cls.user_profile_for_blog_tests = UserProfile.objects.create(
            full_name="Blog Test User",
            tagline="Testing the blog",
            email="blogtest@example.com",
            # site_identifier will default to "main_profile"
        )

        # Original setUpTestData for blog posts
        cls.client = Client() # client can be initialized here or in setUp, here is fine for class-level.
        cls.items_per_page = 5 # Matches view
        cls.num_published_past_posts = 7 # Number of posts that should be visible

        # Create posts that should be visible in the list
        for i in range(cls.num_published_past_posts):
            BlogPost.objects.create(
                title=f'Visible Test Post {i+1}',
                content=f'Content for visible test post {i+1}.',
                status='published',
                published_date=timezone.now() - timezone.timedelta(days=i)
            )

        # Store one of the visible posts for detail view testing
        cls.published_post_for_detail = BlogPost.objects.get(title='Visible Test Post 1')

        # Create a draft post (should not be visible in list or detail)
        cls.draft_post_for_view = BlogPost.objects.create(
            title='Draft Post For View Test',
            content='This is a draft for view test.',
            status='draft',
            published_date=timezone.now() - timezone.timedelta(days=10) # Past date, but draft
        )
        # Create a future-published post (should not be visible in list or detail yet)
        cls.future_post_for_view = BlogPost.objects.create(
            title='Future Post For View Test',
            content='This will be published later for view test.',
            status='published',
            published_date=timezone.now() + timezone.timedelta(days=1)
        )
        # Total posts in DB = num_published_past_posts + 2 (draft + future)
        cls.total_db_posts = cls.num_published_past_posts + 2


    def test_blog_post_list_view_status_code_and_template(self):
        """Test the list view returns 200 OK and uses the correct template."""
        response = self.client.get(reverse('blog:blog_post_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/blog_list.html')
        # Assert UserProfile is in context
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_blog_tests)


    def test_blog_post_list_view_context_content_and_ordering(self):
        """
        Test context data, content, and ordering for the list view.
        The view now filters for status='published' and published_date__lte=timezone.now().
        """
        response = self.client.get(reverse('blog:blog_post_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('page_obj' in response.context)
        self.assertTrue('posts' in response.context) # 'posts' is an alias for page_obj
        self.assertEqual(response.context['page_title'], 'Blog')

        page_obj = response.context['page_obj']
        # Check number of items on the first page
        self.assertEqual(len(page_obj.object_list), min(self.items_per_page, self.num_published_past_posts))

        # Verify the posts displayed are the correct ones and in the correct order
        visible_posts_sorted = list(BlogPost.objects.filter(
            status='published',
            published_date__lte=timezone.now()
        ).order_by('-published_date'))

        expected_titles_on_page1 = [post.title for post in visible_posts_sorted[:self.items_per_page]]
        actual_titles_on_page1 = [post.title for post in page_obj.object_list]
        self.assertEqual(actual_titles_on_page1, expected_titles_on_page1)

        # Ensure draft and future posts are not in the list
        for post_on_page in page_obj.object_list:
            self.assertNotEqual(post_on_page.title, self.draft_post_for_view.title)
            self.assertNotEqual(post_on_page.title, self.future_post_for_view.title)
        
        # Assert UserProfile is in context
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_blog_tests)


    def test_blog_post_list_view_empty_state(self):
        """Test the list view when no PUBLISHED blog posts exist."""
        # Delete all posts, then create only a draft and a future post
        BlogPost.objects.all().delete()
        BlogPost.objects.create(title='Only Draft Here', status='draft', published_date=timezone.now()-timezone.timedelta(days=1))
        BlogPost.objects.create(title='Only Future Here', status='published', published_date=timezone.now()+timezone.timedelta(days=1))

        response = self.client.get(reverse('blog:blog_post_list'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['page_obj'].object_list, "Page object list should be empty as no posts meet criteria.")
        self.assertContains(response, "No Blog Posts Yet") # Or similar message from your template
        # Assert UserProfile is in context
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_blog_tests)


    def test_blog_post_list_pagination_functionality(self):
        """Test pagination for the list view with multiple pages based on visible posts."""
        # Pagination should be based on the number of visible posts
        num_expected_pages = (self.num_published_past_posts + self.items_per_page - 1) // self.items_per_page
        self.assertEqual(num_expected_pages, 2, f"Should be 2 pages with {self.num_published_past_posts} visible posts and {self.items_per_page} items/page.")

        response_page1 = self.client.get(reverse('blog:blog_post_list'))
        page_obj1 = response_page1.context['page_obj']
        self.assertEqual(len(page_obj1.object_list), self.items_per_page)
        self.assertTrue(page_obj1.has_next())
        # Assert UserProfile is in context for page 1
        self.assertIn('user_profile', response_page1.context)
        self.assertEqual(response_page1.context['user_profile'], self.user_profile_for_blog_tests)


        response_page2 = self.client.get(reverse('blog:blog_post_list') + '?page=2')
        page_obj2 = response_page2.context['page_obj']
        self.assertEqual(len(page_obj2.object_list), self.num_published_past_posts - self.items_per_page)
        self.assertFalse(page_obj2.has_next())
        self.assertTrue(page_obj2.has_previous())
        # Assert UserProfile is in context for page 2
        self.assertIn('user_profile', response_page2.context)
        self.assertEqual(response_page2.context['user_profile'], self.user_profile_for_blog_tests)


    def test_blog_post_list_pagination_invalid_page_numbers(self):
        """Test pagination with invalid and out-of-range page numbers based on visible posts."""
        num_expected_pages = (self.num_published_past_posts + self.items_per_page - 1) // self.items_per_page

        response_nan = self.client.get(reverse('blog:blog_post_list') + '?page=abc')
        self.assertEqual(response_nan.context['page_obj'].number, 1, "Invalid page string should default to page 1.")
        self.assertIn('user_profile', response_nan.context) # Check UserProfile

        response_high = self.client.get(reverse('blog:blog_post_list') + '?page=999')
        self.assertEqual(response_high.context['page_obj'].number, num_expected_pages, "Page number too high should default to last page.")
        self.assertIn('user_profile', response_high.context) # Check UserProfile

        response_zero = self.client.get(reverse('blog:blog_post_list') + '?page=0')
        # Paginator.get_page treats 0 or negative as the last page if invalid, or first if valid but 0
        # Django's Paginator.get_page behavior for 0 is to go to page 1.
        self.assertEqual(response_zero.context['page_obj'].number, num_expected_pages, "Page 0 should default to page 1.")
        self.assertIn('user_profile', response_zero.context) # Check UserProfile


    def test_blog_post_detail_view_published_post_success(self):
        """Test detail view for a published, past-dated post returns 200 OK and correct context."""
        response = self.client.get(reverse('blog:blog_post_detail', kwargs={'slug': self.published_post_for_detail.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/blog_detail.html')
        self.assertEqual(response.context['post'], self.published_post_for_detail)
        self.assertEqual(response.context['page_title'], self.published_post_for_detail.title)
        self.assertContains(response, self.published_post_for_detail.title)
        self.assertContains(response, self.published_post_for_detail.content)
        # Assert UserProfile is in context
        self.assertIn('user_profile', response.context)
        self.assertEqual(response.context['user_profile'], self.user_profile_for_blog_tests)

    def test_blog_post_detail_view_404_non_existent_slug(self):
        """Test detail view returns 404 for a non-existent slug."""
        response = self.client.get(reverse('blog:blog_post_detail', kwargs={'slug': 'non-existent-slug-for-404'}))
        self.assertEqual(response.status_code, 404)
        # Note: If the 404 page itself uses the context processor, this test might still show the warning
        # if UserProfile isn't set up for the test class. It is here, so it should be fine.

    def test_blog_post_detail_view_404_for_draft_post(self):
        """Test detail view returns 404 for a draft post (as per view logic)."""
        response = self.client.get(reverse('blog:blog_post_detail', kwargs={'slug': self.draft_post_for_view.slug}))
        self.assertEqual(response.status_code, 404)

    def test_blog_post_detail_view_404_for_future_published_post(self):
        """Test detail view returns 404 for a future-dated post (as per view logic)."""
        response = self.client.get(reverse('blog:blog_post_detail', kwargs={'slug': self.future_post_for_view.slug}))
        self.assertEqual(response.status_code, 404)

# --- URL Tests ---
class BlogURLTests(TestCase):
    """
    Tests for the blog URL configurations.
    No UserProfile setup needed here as these tests don't render templates.
    """
    def test_blog_post_list_url_resolves_to_correct_view(self):
        """Test that the URL for the blog post list resolves to the correct view function."""
        url = reverse('blog:blog_post_list')
        self.assertEqual(resolve(url).func, views.blog_post_list)

    def test_blog_post_detail_url_resolves_to_correct_view(self):
        """Test that the URL for a blog post detail resolves to the correct view function and captures slug."""
        test_slug = "test-slug-for-url-resolution-detail"
        # We don't need to create a post for this, just testing URL resolution
        url = reverse('blog:blog_post_detail', kwargs={'slug': test_slug})
        resolver_match = resolve(url)
        self.assertEqual(resolver_match.func, views.blog_post_detail)
        self.assertEqual(resolver_match.kwargs['slug'], test_slug)

# --- Sitemap Tests ---
class BlogSitemapTests(TestCase):
    """
    Tests for the blog sitemaps.
    """
    @classmethod
    def setUpTestData(cls):
        # Create UserProfile in case sitemap generation or related views need it
        cls.user_profile_for_sitemap_tests = UserProfile.objects.create(
            full_name="Sitemap Test User",
            site_identifier="main_profile_sitemap_blog" # Ensure unique if needed across test classes
        )

        cls.now = timezone.now()
        cls.published_post1_sitemap = BlogPost.objects.create(
            title="Sitemap Published Post 1 For Test",
            content="Content.",
            status="published",
            published_date=cls.now - timezone.timedelta(days=1)
        )
        cls.published_post2_sitemap = BlogPost.objects.create(
            title="Sitemap Published Post 2 For Test",
            content="Content.",
            status="published",
            published_date=cls.now - timezone.timedelta(hours=5)
        )
        cls.draft_post_sitemap_test = BlogPost.objects.create(
            title="Sitemap Draft Post For Test",
            content="Content.",
            status="draft",
            published_date=cls.now - timezone.timedelta(days=2)
        )
        cls.future_post_sitemap_test = BlogPost.objects.create(
            title="Sitemap Future Post For Test",
            content="Content.",
            status="published",
            published_date=cls.now + timezone.timedelta(days=1)
        )

    def test_blog_static_sitemap_properties(self):
        """Test items, location, priority, and changefreq for BlogStaticSitemap."""
        sitemap = BlogStaticSitemap()
        self.assertEqual(list(sitemap.items()), ['blog:blog_post_list'])
        expected_url = reverse('blog:blog_post_list')
        self.assertEqual(sitemap.location('blog:blog_post_list'), expected_url)
        self.assertEqual(sitemap.priority, 0.7)
        self.assertEqual(sitemap.changefreq, 'daily')

    def test_blog_post_sitemap_items_filter_correctly(self):
        """Test BlogPostSitemap items only include published, past-dated posts."""
        sitemap = BlogPostSitemap()
        items = list(sitemap.items())
        self.assertIn(self.published_post1_sitemap, items)
        self.assertIn(self.published_post2_sitemap, items)
        self.assertNotIn(self.draft_post_sitemap_test, items, "Draft posts should not be in sitemap items.")
        self.assertNotIn(self.future_post_sitemap_test, items, "Future-dated posts should not be in sitemap items.")
        self.assertEqual(len(items), 2, "Only two currently published and visible posts should be in sitemap.")

    def test_blog_post_sitemap_lastmod_and_location(self):
        """Test lastmod and location methods of BlogPostSitemap."""
        sitemap = BlogPostSitemap()
        self.assertEqual(sitemap.lastmod(self.published_post1_sitemap), self.published_post1_sitemap.published_date)
        expected_location = self.published_post1_sitemap.get_absolute_url()
        self.assertEqual(sitemap.location(self.published_post1_sitemap), expected_location)


    def test_blog_post_sitemap_priority_and_changefreq(self):
        """Test priority and changefreq of BlogPostSitemap."""
        sitemap = BlogPostSitemap()
        self.assertEqual(sitemap.priority, 0.8)
        self.assertEqual(sitemap.changefreq, 'weekly')

# --- Admin Tests ---
class BlogAdminTests(TestCase):
    """
    Tests for the blog admin configurations and accessibility.
    """
    @classmethod
    def setUpTestData(cls):
        # Create UserProfile in case admin views or templates need it
        cls.user_profile_for_admin_tests = UserProfile.objects.create(
            full_name="Admin Test User for Blog",
            site_identifier="main_profile_admin_blog" # Ensure unique if needed
        )
        cls.superuser = User.objects.create_superuser('admin_blog_user', 'admin_blog@example.com', 'password123')
        cls.post_for_admin = BlogPost.objects.create(title="Admin Test Post For Blog Admin", content="Admin content.")

    def setUp(self):
        self.client.login(username='admin_blog_user', password='password123')

    def test_blogpost_is_registered_with_correct_admin_class(self):
        """Test that BlogPost model is registered with BlogPostAdmin."""
        self.assertIn(BlogPost, django_admin_site.site._registry, "BlogPost should be registered in the admin site.")
        self.assertIsInstance(django_admin_site.site._registry[BlogPost], BlogPostAdmin)

    def test_blogpostadmin_modeladmin_options(self):
        """Test ModelAdmin options for BlogPostAdmin."""
        self.assertEqual(BlogPostAdmin.list_display, ('title', 'slug', 'status', 'published_date', 'created_date'))
        self.assertEqual(BlogPostAdmin.list_filter, ('status', 'created_date', 'published_date'))
        self.assertEqual(BlogPostAdmin.search_fields, ('title', 'content'))
        self.assertEqual(BlogPostAdmin.prepopulated_fields, {'slug': ('title',)})

    def test_blogpost_admin_changelist_accessible(self):
        response = self.client.get(reverse('admin:blog_blogpost_changelist'))
        self.assertEqual(response.status_code, 200)
        # Check if user_profile is in context if your admin base template uses it
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_admin_tests)


    def test_blogpost_admin_add_view_accessible(self):
        response = self.client.get(reverse('admin:blog_blogpost_add'))
        self.assertEqual(response.status_code, 200)
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_admin_tests)


    def test_blogpost_admin_change_view_accessible(self):
        response = self.client.get(reverse('admin:blog_blogpost_change', args=[self.post_for_admin.pk]))
        self.assertEqual(response.status_code, 200)
        if 'user_profile' in response.context:
            self.assertEqual(response.context['user_profile'], self.user_profile_for_admin_tests)

