# core/management/commands/import_data.py
import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils.text import slugify
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone

# --- Model Imports (with checks) ---
try:
    # Ensure UserProfile is imported correctly from your portfolio app
    from portfolio.models import Project, Certificate, UserProfile, ColophonEntry
    PORTFOLIO_APP_EXISTS = True
except ImportError:
    Project, Certificate, UserProfile, ColophonEntry = None, None, None, None
    PORTFOLIO_APP_EXISTS = False

# ... (rest of your model imports: BlogPost, Skill, SkillCategory, etc.) ...
try:
    from blog.models import BlogPost
    BLOG_APP_EXISTS = True
except ImportError:
    BlogPost = None
    BLOG_APP_EXISTS = False

try:
    from skills.models import Skill, SkillCategory
    SKILLS_APP_EXISTS = True
except ImportError:
    Skill, SkillCategory = None, None
    SKILLS_APP_EXISTS = False

try:
    from topics.models import ProjectTopic
    TOPICS_APP_EXISTS = True
except ImportError:
    ProjectTopic = None
    TOPICS_APP_EXISTS = False

try:
    from recommendations.models import RecommendedProduct # Assuming this exists
    RECOMMENDATIONS_APP_EXISTS = True
except ImportError:
    RecommendedProduct = None
    RECOMMENDATIONS_APP_EXISTS = False


# MODEL_MAP: Defines which model corresponds to which --model_type argument
MODEL_MAP = {}
if PORTFOLIO_APP_EXISTS:
    MODEL_MAP['projects'] = Project
    MODEL_MAP['certificates'] = Certificate
    MODEL_MAP['userprofile'] = UserProfile
    MODEL_MAP['colophonentires'] = ColophonEntry # Corrected typo from previous version if needed
if BLOG_APP_EXISTS:
    MODEL_MAP['blogposts'] = BlogPost
if SKILLS_APP_EXISTS:
    MODEL_MAP['skills'] = Skill
    MODEL_MAP['skillcategories'] = SkillCategory
if TOPICS_APP_EXISTS:
    MODEL_MAP['topics'] = ProjectTopic
if RECOMMENDATIONS_APP_EXISTS:
    MODEL_MAP['recommendedproducts'] = RecommendedProduct


def str_to_bool(s):
    # ... (keep existing str_to_bool function) ...
    if s is None:
        return None
    s_lower = str(s).lower().strip()
    if s_lower in ('true', '1', 'yes', 'y'):
        return True
    if s_lower in ('false', '0', 'no', 'n', ''):
        return False
    return None


class Command(BaseCommand):
    help = 'Imports data from a specified CSV file into the database for a given model type.'

    def add_arguments(self, parser):
        # ... (keep existing add_arguments method) ...
        parser.add_argument('csv_filepath', type=str, help='The path to the CSV file to import (relative to project base or absolute).')
        parser.add_argument(
            '--model_type',
            type=str,
            help=f"The type of model to import (e.g., {', '.join(MODEL_MAP.keys())}).",
            required=True
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing records based on a unique field instead of just creating new ones.',
        )
        parser.add_argument(
            '--unique_field',
            type=str,
            default='slug',
            help='The unique model field name to use for matching when updating (default: slug). For userprofile, this defaults to site_identifier.',
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8-sig',
            help='Encoding of the CSV file (e.g., utf-8, latin-1).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_filepath_arg = options['csv_filepath']
        model_type = options['model_type'].lower()
        update_existing = options['update']
        unique_field_arg = options['unique_field']
        encoding = options['encoding']

        # Default unique field for userprofile is 'site_identifier'
        if model_type == 'userprofile' and unique_field_arg == 'slug': # Only override if default 'slug' was kept
             unique_field = 'site_identifier'
        else:
             unique_field = unique_field_arg


        if not os.path.isabs(csv_filepath_arg):
            csv_filepath = os.path.join(settings.BASE_DIR, csv_filepath_arg)
        else:
            csv_filepath = csv_filepath_arg

        if model_type not in MODEL_MAP:
            raise CommandError(f"Invalid model_type '{model_type}'. Valid types are: {', '.join(MODEL_MAP.keys())}")

        TargetModel = MODEL_MAP[model_type]
        if TargetModel is None:
             raise CommandError(f"Model for type '{model_type}' could not be imported. Ensure the app is in INSTALLED_APPS and models are defined.")

        if not os.path.exists(csv_filepath):
            raise CommandError(f"File not found at path: {csv_filepath}")

        self.stdout.write(self.style.SUCCESS(f"Starting import for '{model_type}' from '{csv_filepath}' using encoding '{encoding}'..."))
        if update_existing:
            self.stdout.write(self.style.WARNING(f"Update mode enabled. Matching on model field '{unique_field}'."))

        created_count = 0
        updated_count = 0
        skipped_count = 0

        try:
            with open(csv_filepath, mode='r', encoding=encoding) as csvfile:
                reader = csv.DictReader(csvfile)
                if not reader.fieldnames:
                    raise CommandError(f"CSV file '{csv_filepath}' appears to be empty or has no header row.")

                # --- Get expected model fields for validation ---
                try:
                    # Get all fields, including direct fields and foreign keys
                    model_fields_info = TargetModel._meta.get_fields()
                    model_fields = set()
                    for f in model_fields_info:
                        # Include non-relation fields, and relations that are FK or O2O
                        if not f.is_relation or f.one_to_one or f.many_to_one:
                            model_fields.add(f.name)
                        # Special case for ManyToMany: add the field name itself,
                        # but we'll handle the actual data linking separately later.
                        elif f.many_to_many:
                            model_fields.add(f.name)

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Could not reliably determine model fields for {TargetModel.__name__}: {e}"))
                    model_fields = set() # Fallback if introspection fails

                for row_num, row in enumerate(reader, start=1):
                    data_for_model = {}
                    m2m_data = {}
                    csv_unique_value = None # Initialize

                    try:
                        # --- Get the unique value first ---
                        # Strip whitespace from all values in the row for cleaner processing
                        # Handle potential None keys from CSV reader
                        cleaned_row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items() if k}
                        csv_unique_value = cleaned_row.get(unique_field, '')

                        # --- Model-Specific Processing ---
                        if model_type == 'userprofile':
                            if not PORTFOLIO_APP_EXISTS or UserProfile is None: continue

                            # --- Map CSV columns to model fields ---
                            # Basic Info
                            data_for_model['full_name'] = cleaned_row.get('full_name', 'Your Name')
                            data_for_model['tagline'] = cleaned_row.get('tagline') or None
                            data_for_model['location'] = cleaned_row.get('location') or None
                            data_for_model['email'] = cleaned_row.get('email') or None
                            data_for_model['phone_number'] = cleaned_row.get('phone_number') or None

                            # Bio & About
                            data_for_model['short_bio_html'] = cleaned_row.get('short_bio_html') or None
                            #data_for_model['about_me_markdown'] = cleaned_row.get('about_me_markdown') or None
                            data_for_model['profile_picture_url'] = cleaned_row.get('profile_picture_url') or None

                            # Social & Professional Links
                            data_for_model['linkedin_url'] = cleaned_row.get('linkedin_url') or None
                            data_for_model['github_url'] = cleaned_row.get('github_url') or None
                            data_for_model['personal_website_url'] = cleaned_row.get('personal_website_url') or None
                            data_for_model['cv_url'] = cleaned_row.get('cv_url') or None

                            # Meta for SEO
                            data_for_model['default_meta_description'] = cleaned_row.get('default_meta_description') or None
                            data_for_model['default_meta_keywords'] = cleaned_row.get('default_meta_keywords') or None

                            # Site Identifier (Unique Key)
                            data_for_model['site_identifier'] = cleaned_row.get('site_identifier', 'main_profile')
                            if not data_for_model['site_identifier']: raise ValueError("UserProfile 'site_identifier' is required.")

                            # Page Content Fields
                            # About Me Page
                            data_for_model['about_me_intro_markdown'] = cleaned_row.get('about_me_intro_markdown') or None
                            data_for_model['about_me_journey_markdown'] = cleaned_row.get('about_me_journey_markdown') or None
                            data_for_model['about_me_expertise_markdown'] = cleaned_row.get('about_me_expertise_markdown') or None
                            data_for_model['about_me_philosophy_markdown'] = cleaned_row.get('about_me_philosophy_markdown') or None
                            data_for_model['about_me_beyond_work_markdown'] = cleaned_row.get('about_me_beyond_work_markdown') or None
                            # Hire Me Page
                            data_for_model['hire_me_intro_markdown'] = cleaned_row.get('hire_me_intro_markdown') or None
                            data_for_model['hire_me_seeking_markdown'] = cleaned_row.get('hire_me_seeking_markdown') or None
                            data_for_model['hire_me_strengths_markdown'] = cleaned_row.get('hire_me_strengths_markdown') or None
                            data_for_model['hire_me_availability_markdown'] = cleaned_row.get('hire_me_availability_markdown') or None
                            # Skills Overview (Homepage)
                            data_for_model['skills_overview_ml_markdown'] = cleaned_row.get('skills_overview_ml_markdown') or None
                            data_for_model['skills_overview_datasci_markdown'] = cleaned_row.get('skills_overview_datasci_markdown') or None
                            data_for_model['skills_overview_general_markdown'] = cleaned_row.get('skills_overview_general_markdown') or None

                                                        # --- NEW: Skills Overview Titles from CSV ---
                            data_for_model['skills_overview_ml_title'] = cleaned_row.get('skills_overview_ml_title') or None
                            data_for_model['skills_overview_datasci_title'] = cleaned_row.get('skills_overview_datasci_title') or None
                            data_for_model['skills_overview_general_title'] = cleaned_row.get('skills_overview_general_title') or None
                            # --- END NEW Titles ---
                            data_for_model['about_me_introduction'] = cleaned_row.get('about_me_introduction') or None
                            data_for_model['about_me_details'] = cleaned_row.get('about_me_details') or None
                            # *** NEW Legal/Policy Fields ***
                            data_for_model['privacy_policy_markdown'] = cleaned_row.get('privacy_policy_markdown') or None
                            data_for_model['terms_conditions_markdown'] = cleaned_row.get('terms_conditions_markdown') or None
                            data_for_model['accessibility_statement_markdown'] = cleaned_row.get('accessibility_statement_markdown') or None
                            # *** END NEW FIELDS ***

                            # Ensure the unique value used for lookup is correct
                            csv_unique_value = data_for_model['site_identifier']


                        elif model_type == 'skills':
                            # ... (keep existing skills logic) ...
                             if not SKILLS_APP_EXISTS: continue
                             data_for_model['name'] = cleaned_row.get('name', '')
                             if not data_for_model['name']: raise ValueError("Skill 'name' is required.")
                             data_for_model['description'] = cleaned_row.get('description') or None
                             data_for_model['order'] = int(cleaned_row.get('order', 0)) if cleaned_row.get('order') else 0
                             if unique_field == 'slug' and not csv_unique_value: csv_unique_value = slugify(data_for_model['name'])
                             elif unique_field == 'name': csv_unique_value = data_for_model['name']
                             category_name = cleaned_row.get('category_name', '')
                             if category_name:
                                 category, created_cat = SkillCategory.objects.get_or_create(name=category_name)
                                 if created_cat: self.stdout.write(self.style.NOTICE(f"  Created SkillCategory: {category_name}"))
                                 data_for_model['category'] = category

                        elif model_type == 'skillcategories':
                            # ... (keep existing skillcategories logic) ...
                             if not SKILLS_APP_EXISTS: continue
                             data_for_model['name'] = cleaned_row.get('name', '')
                             if not data_for_model['name']: raise ValueError("SkillCategory 'name' is required.")
                             data_for_model['description'] = cleaned_row.get('description') or None
                             if unique_field == 'name': csv_unique_value = data_for_model['name']

                        elif model_type == 'topics':
                            # ... (keep existing topics logic) ...
                             if not TOPICS_APP_EXISTS: continue
                             data_for_model['name'] = cleaned_row.get('name', '')
                             if not data_for_model['name']: raise ValueError("ProjectTopic 'name' is required.")
                             data_for_model['description'] = cleaned_row.get('description') or None
                             data_for_model['order'] = int(cleaned_row.get('order', 0)) if cleaned_row.get('order') else 0
                             if unique_field == 'slug' and not csv_unique_value: csv_unique_value = slugify(data_for_model['name'])
                             elif unique_field == 'name': csv_unique_value = data_for_model['name']

                        elif model_type == 'certificates':
                            # ... (keep existing certificates logic) ...
                             if not PORTFOLIO_APP_EXISTS: continue
                             data_for_model['title'] = cleaned_row.get('title', '')
                             if not data_for_model['title']: raise ValueError("Certificate 'title' is required.")
                             data_for_model['issuer'] = cleaned_row.get('issuer') or None
                             date_str = cleaned_row.get('date_issued', '')
                             data_for_model['date_issued'] = timezone.datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
                             data_for_model['credential_url'] = cleaned_row.get('credential_url') or None
                             data_for_model['order'] = int(cleaned_row.get('order', 0)) if cleaned_row.get('order') else 0
                             data_for_model['is_featured'] = str_to_bool(cleaned_row.get('is_featured', 'False'))
                             if unique_field == 'title': csv_unique_value = data_for_model['title']

                        elif model_type == 'projects':
                             # ... (keep existing projects logic) ...
                             if not PORTFOLIO_APP_EXISTS: continue
                             data_for_model['title'] = cleaned_row.get('title', '')
                             if not data_for_model['title']: raise ValueError("Project 'title' is required.")
                             project_slug_from_csv = cleaned_row.get('slug', '')
                             if project_slug_from_csv:
                                 data_for_model['slug'] = project_slug_from_csv
                                 if unique_field == 'slug': csv_unique_value = project_slug_from_csv
                             elif 'title' in data_for_model:
                                 generated_slug = slugify(data_for_model['title'])
                                 data_for_model['slug'] = generated_slug
                                 if unique_field == 'slug': csv_unique_value = generated_slug
                             if unique_field == 'title': csv_unique_value = data_for_model['title']
                             data_for_model['description'] = cleaned_row.get('description') or None
                             data_for_model['image_url'] = cleaned_row.get('image_url') or None
                             data_for_model['github_url'] = cleaned_row.get('github_url') or None
                             data_for_model['demo_url'] = cleaned_row.get('demo_url') or None
                             data_for_model['paper_url'] = cleaned_row.get('paper_url') or None
                             data_for_model['order'] = int(cleaned_row.get('order', 0)) if cleaned_row.get('order') else 0
                             data_for_model['is_featured'] = str_to_bool(cleaned_row.get('is_featured', 'False'))
                             data_for_model['results_metrics'] = cleaned_row.get('results_metrics') or None
                             data_for_model['challenges'] = cleaned_row.get('challenges') or None
                             data_for_model['lessons_learned'] = cleaned_row.get('lessons_learned') or None
                             data_for_model['code_snippet'] = cleaned_row.get('code_snippet') or None
                             data_for_model['code_language'] = cleaned_row.get('code_language') or None
                             data_for_model['long_description_markdown'] = cleaned_row.get('long_description_markdown') or None
                             m2m_data['skills'] = [s.strip() for s in cleaned_row.get('skills', '').split(',') if s.strip()]
                             m2m_data['topics'] = [t.strip() for t in cleaned_row.get('topics', '').split(',') if t.strip()]

                        elif model_type == 'blogposts':
                            # ... (keep existing blogposts logic) ...
                             if not BLOG_APP_EXISTS: continue
                             data_for_model['title'] = cleaned_row.get('title', '')
                             if not data_for_model['title']: raise ValueError("BlogPost 'title' is required.")
                             data_for_model['content_markdown'] = cleaned_row.get('content_markdown') or None
                             data_for_model['meta_description'] = cleaned_row.get('meta_description') or None
                             data_for_model['meta_keywords'] = cleaned_row.get('meta_keywords') or None
                             pub_date_str = cleaned_row.get('published_date', '')
                             if pub_date_str:
                                 try: data_for_model['published_date'] = timezone.datetime.strptime(pub_date_str, '%Y-%m-%d %H:%M:%S')
                                 except ValueError:
                                     try:
                                         dt_naive = timezone.datetime.strptime(pub_date_str, '%Y-%m-%d')
                                         data_for_model['published_date'] = timezone.make_aware(dt_naive) if timezone.is_naive(dt_naive) else dt_naive
                                     except ValueError:
                                         self.stdout.write(self.style.WARNING(f"    BlogPost '{data_for_model['title']}': Invalid date format '{pub_date_str}'. Setting to now."))
                                         data_for_model['published_date'] = timezone.now()
                             else: data_for_model['published_date'] = timezone.now()
                             data_for_model['is_published'] = str_to_bool(cleaned_row.get('is_published', 'True'))
                             data_for_model['is_featured'] = str_to_bool(cleaned_row.get('is_featured', 'False'))
                             if unique_field == 'slug' and not csv_unique_value: csv_unique_value = slugify(data_for_model['title'])
                             elif unique_field == 'title': csv_unique_value = data_for_model['title']

                        elif model_type == 'colophonentires': # Note: Check spelling if model is ColophonEntry
                            # ... (keep existing colophon logic) ...
                             if not PORTFOLIO_APP_EXISTS or ColophonEntry is None: continue
                             data_for_model['name'] = cleaned_row.get('name', '')
                             if not data_for_model['name']: raise ValueError("ColophonEntry 'name' is required.")
                             category_value = cleaned_row.get('category', '').lower()
                             valid_categories = [choice[0] for choice in ColophonEntry.CATEGORY_CHOICES]
                             if category_value not in valid_categories:
                                 raise ValueError(f"Invalid category '{category_value}' for ColophonEntry '{data_for_model['name']}'. Valid are: {valid_categories}")
                             data_for_model['category'] = category_value
                             data_for_model['description'] = cleaned_row.get('description') or None
                             data_for_model['url'] = cleaned_row.get('url') or None
                             data_for_model['icon_class'] = cleaned_row.get('icon_class') or None
                             data_for_model['order'] = int(cleaned_row.get('order', 0)) if cleaned_row.get('order') else 0
                             if unique_field == 'name': csv_unique_value = data_for_model['name']

                        # --- Filter out keys not present in the model ---
                        # This prevents errors if the CSV has extra columns
                        if model_fields:
                            # Filter data_for_model based on actual model fields
                            # Exclude M2M fields from direct assignment
                            direct_fields = {f.name for f in TargetModel._meta.get_fields() if not f.many_to_many}
                            data_for_model = {k: v for k, v in data_for_model.items() if k in model_fields and k in direct_fields}
                        else:
                             self.stdout.write(self.style.WARNING(f"Could not filter columns for row {row_num} as model fields were not determined."))


                        # --- Create or Update Logic ---
                        instance = None
                        if not csv_unique_value and update_existing:
                            self.stdout.write(self.style.WARNING(f"Row {row_num}: Skipping update for {model_type} because unique field '{unique_field}' value is empty or missing in CSV."))
                            skipped_count += 1
                            continue

                        lookup_params = {unique_field: csv_unique_value}

                        if update_existing:
                            try:
                                instance, created = TargetModel.objects.update_or_create(
                                    defaults=data_for_model,
                                    **lookup_params
                                )
                                if created:
                                    created_count += 1
                                    self.stdout.write(f"  Created {model_type} (as update target not found using {unique_field}='{csv_unique_value}'): {str(instance)}")
                                else:
                                    updated_count += 1
                                    self.stdout.write(f"  Updated {model_type}: {str(instance)} (Lookup: {unique_field}='{csv_unique_value}')")
                            except IntegrityError as ie_update:
                                # Handle cases where update_or_create might fail due to other constraints
                                self.stdout.write(self.style.ERROR(f"Skipping row {row_num} for {model_type}: Integrity error during update_or_create (lookup: {lookup_params}) - {ie_update}. Row: {row}"))
                                skipped_count += 1
                                continue # Skip to next row
                        else: # Create only mode
                            # Ensure slug is generated if needed and not provided
                            if unique_field == 'slug' and 'slug' not in data_for_model:
                                if csv_unique_value:
                                    data_for_model['slug'] = csv_unique_value
                                elif 'name' in data_for_model and data_for_model['name']:
                                    data_for_model['slug'] = slugify(data_for_model['name'])
                                elif 'title' in data_for_model and data_for_model['title']:
                                    data_for_model['slug'] = slugify(data_for_model['title'])

                            try:
                                instance = TargetModel.objects.create(**data_for_model)
                                created_count += 1
                                self.stdout.write(f"  Created {model_type}: {str(instance)}")
                            except IntegrityError as ie_create:
                                self.stdout.write(self.style.ERROR(f"Skipping row {row_num} for {model_type}: Integrity error during create (maybe duplicate unique field '{csv_unique_value}'?) - {ie_create}. Row: {row}"))
                                skipped_count += 1
                                continue # Skip to next row


                        # --- Handle ManyToMany Post-Save ---
                        if instance and m2m_data:
                            if model_type == 'projects':
                                # ... (keep existing M2M logic for projects) ...
                                if update_existing:
                                    if 'skills' in m2m_data: instance.skills.clear()
                                    if 'topics' in m2m_data: instance.topics.clear()
                                if SKILLS_APP_EXISTS and Skill and 'skills' in m2m_data:
                                    for skill_id in m2m_data['skills']:
                                        try:
                                            skill_obj = Skill.objects.get(Q(slug=skill_id) | Q(name=skill_id))
                                            instance.skills.add(skill_obj)
                                        except Skill.DoesNotExist: self.stdout.write(self.style.WARNING(f"    Project '{instance}': Skill '{skill_id}' not found. Skipping."))
                                        except Skill.MultipleObjectsReturned: self.stdout.write(self.style.WARNING(f"    Project '{instance}': Multiple skills found for '{skill_id}'. Skipping."))
                                if TOPICS_APP_EXISTS and ProjectTopic and 'topics' in m2m_data:
                                    for topic_id in m2m_data['topics']:
                                        try:
                                            topic_obj = ProjectTopic.objects.get(Q(slug=topic_id) | Q(name=topic_id))
                                            instance.topics.add(topic_obj)
                                        except ProjectTopic.DoesNotExist: self.stdout.write(self.style.WARNING(f"    Project '{instance}': Topic '{topic_id}' not found. Skipping."))
                                        except ProjectTopic.MultipleObjectsReturned: self.stdout.write(self.style.WARNING(f"    Project '{instance}': Multiple topics found for '{topic_id}'. Skipping."))

                    # --- Error Handling per Row ---
                    except ValueError as ve:
                        self.stdout.write(self.style.ERROR(f"Skipping row {row_num} for {model_type}: Invalid data - {ve}. Row: {row}"))
                        skipped_count += 1
                    except IntegrityError as ie:
                        # This might catch issues if unique_field wasn't handled correctly above
                        self.stdout.write(self.style.ERROR(f"Skipping row {row_num} for {model_type}: Database integrity error (e.g., duplicate unique field '{csv_unique_value}') - {ie}. Row: {row}"))
                        skipped_count += 1
                    except Exception as e:
                        # Catch-all for other unexpected errors in row processing
                        self.stdout.write(self.style.ERROR(f"Error processing row {row_num} for {model_type}: {type(e).__name__} - {e}. Row: {row}"))
                        import traceback
                        self.stdout.write(traceback.format_exc()) # Print traceback for debugging
                        skipped_count += 1

        # --- Overall Error Handling ---
        except FileNotFoundError:
            raise CommandError(f"CSV file not found: '{csv_filepath}'")
        except UnicodeDecodeError as ude:
            raise CommandError(f"UnicodeDecodeError reading '{csv_filepath}' with encoding '{encoding}': {ude}. Try a different --encoding or check file.")
        except Exception as e:
            # Catch-all for errors outside the row loop (e.g., file opening)
            import traceback
            self.stderr.write(traceback.format_exc()) # Print traceback for debugging
            raise CommandError(f"An unexpected error occurred during import: {type(e).__name__} - {e}")

        self.stdout.write(self.style.SUCCESS(f"\nImport for '{model_type}' finished. Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}"))

