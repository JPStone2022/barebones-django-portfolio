# demos/management/commands/populate_demos_from_csv.py
import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import IntegrityError
from demos.models import Demo, DemoSection # Ensure DemoSection is also imported
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Populates Demo and DemoSection models from a specified CSV file. The CSV should ideally contain all demo and section data.'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file_path',
            type=str,
            help='The path to the CSV file relative to the project base directory.'
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8-sig', # Default to utf-8-sig to handle BOM
            help='Encoding of the CSV file (e.g., utf-8, latin-1, windows-1252).'
        )

    def handle(self, *args, **options):
        csv_file_path_relative = options['csv_file_path']
        csv_encoding = options['encoding']
        csv_file_path_absolute = os.path.join(settings.BASE_DIR, csv_file_path_relative)

        self.stdout.write(self.style.SUCCESS(f"Processing CSV file: {csv_file_path_absolute} with encoding {csv_encoding}"))

        if not os.path.exists(csv_file_path_absolute):
            raise CommandError(f"CSV file not found at {csv_file_path_absolute}")

        try:
            with open(csv_file_path_absolute, mode='r', encoding=csv_encoding) as file:
                reader = csv.DictReader(file)
                
                if not reader.fieldnames:
                    raise CommandError(f"CSV file {csv_file_path_absolute} appears to be empty or has no header row.")

                # Define expected headers for Demo (from summary) and DemoSection
                # These are columns the script will look for.
                # For Demo model (summary part):
                demo_slug_col = 'demo_slug' # Essential for linking
                demo_title_col = 'demo_title' # Title for the Demo object itself
                demo_description_col = 'demo_description' # For card/listing (Demo.description)
                demo_image_url_col = 'demo_image_url' # For card/listing (Demo.image_url)
                demo_page_meta_title_col = 'page_meta_title_csv' # SEO meta title (Demo.page_meta_title)
                demo_meta_description_col = 'meta_description_csv' # SEO meta description (Demo.meta_description)
                demo_meta_keywords_col = 'meta_keywords_csv' # SEO meta keywords (Demo.meta_keywords)
                demo_order_col = 'demo_order' # Optional ordering
                demo_is_featured_col = 'demo_is_featured' # Optional featured status
                demo_url_name_col = 'demo_url_name_csv' # Optional: if this demo links to a specific interactive view

                # For DemoSection model (content part):
                section_order_col = 'section_order' # Essential for section
                section_title_col = 'section_title'
                section_content_markdown_col = 'section_content_markdown'
                code_language_col = 'code_language'
                code_snippet_title_col = 'code_snippet_title'
                code_snippet_col = 'code_snippet'
                code_snippet_explanation_col = 'code_snippet_explanation'
                
                # Check for essential columns
                if demo_slug_col not in reader.fieldnames:
                    raise CommandError(f"Missing essential column for Demo: '{demo_slug_col}' in CSV header.")
                if section_order_col not in reader.fieldnames: # Assuming sections are always present or it's okay if not.
                    self.stdout.write(self.style.WARNING(f"Column '{section_order_col}' for sections not found. Sections might not be processed if other section columns are also missing."))


                processed_demo_slugs = set() # To update demo only once
                cleared_sections_for_demo_slugs = set() # To clear sections only once per demo

                for row_number, row in enumerate(reader, 1):
                    current_row_slug = row.get(demo_slug_col, '').strip()
                    if not current_row_slug:
                        self.stdout.write(self.style.WARNING(f"Skipping row {row_number} due to missing '{demo_slug_col}'."))
                        continue

                    demo_instance = None
                    try:
                        # --- Create or Update Demo instance ---
                        if current_row_slug not in processed_demo_slugs:
                            demo_defaults = {
                                'title': row.get(demo_title_col, '').strip() or slugify(current_row_slug).replace('-', ' ').title(),
                                'description': row.get(demo_description_col, '').strip() or None,
                                'image_url': row.get(demo_image_url_col, '').strip() or None,
                                'page_meta_title': row.get(demo_page_meta_title_col, '').strip() or (row.get(demo_title_col, '').strip() or slugify(current_row_slug).replace('-', ' ').title()),
                                'meta_description': row.get(demo_meta_description_col, '').strip() or f"Learn more about {slugify(current_row_slug).replace('-', ' ').title()}.",
                                'meta_keywords': row.get(demo_meta_keywords_col, '').strip() or f"{slugify(current_row_slug).replace('-', ' ')}, demo",
                                'demo_url_name': row.get(demo_url_name_col, '').strip() or None,
                            }
                            try:
                                order_val = row.get(demo_order_col, '').strip()
                                if order_val:
                                    demo_defaults['order'] = int(order_val)
                            except ValueError:
                                self.stdout.write(self.style.WARNING(f"Row {row_number}: Invalid value for '{demo_order_col}'. Using default order."))
                            
                            is_featured_val = str(row.get(demo_is_featured_col, '')).strip().lower()
                            if is_featured_val in ['true', '1', 'yes']:
                                demo_defaults['is_featured'] = True
                            elif is_featured_val in ['false', '0', 'no', '']: # Treat empty as False
                                demo_defaults['is_featured'] = False
                            # Else, it will use model's default

                            demo_instance, created = Demo.objects.update_or_create(
                                slug=current_row_slug,
                                defaults=demo_defaults
                            )
                            action = "Created" if created else "Updated"
                            self.stdout.write(self.style.SUCCESS(f"{action} Demo: '{demo_instance.title}' (Slug: {demo_instance.slug})"))
                            processed_demo_slugs.add(current_row_slug)
                        else:
                            # Demo already processed for its summary, just fetch it
                            demo_instance = Demo.objects.get(slug=current_row_slug)

                        # --- Clear old sections for this demo if encountering it for the first time for sections ---
                        if demo_instance and current_row_slug not in cleared_sections_for_demo_slugs:
                            DemoSection.objects.filter(demo=demo_instance).delete()
                            self.stdout.write(self.style.WARNING(f"Cleared old sections for Demo: '{demo_instance.title}'"))
                            cleared_sections_for_demo_slugs.add(current_row_slug)
                        
                        # --- Create DemoSection instance (if section data is present) ---
                        # Check if there's enough data to create a section
                        raw_section_order = row.get(section_order_col, '').strip()
                        raw_section_content = row.get(section_content_markdown_col, '').strip()
                        raw_code_snippet = row.get(code_snippet_col, '').strip()

                        if demo_instance and raw_section_order and (raw_section_content or raw_code_snippet) : # Only process section if order and some content exists
                            try:
                                section_order_val = float(raw_section_order)
                            except ValueError:
                                self.stdout.write(self.style.WARNING(f"Row {row_number}, Demo '{current_row_slug}': Invalid section_order '{raw_section_order}'. Skipping section."))
                                continue

                            section_data = {
                                'demo': demo_instance,
                                'section_order': section_order_val,
                                'section_title': row.get(section_title_col, '').strip() or None,
                                'section_content_markdown': raw_section_content or None,
                                'code_language': row.get(code_language_col, '').strip() or None,
                                'code_snippet_title': row.get(code_snippet_title_col, '').strip() or None,
                                'code_snippet': raw_code_snippet or None,
                                'code_snippet_explanation': row.get(code_snippet_explanation_col, '').strip() or None,
                            }
                            try:
                                DemoSection.objects.create(**section_data)
                            except IntegrityError:
                                self.stdout.write(self.style.ERROR(
                                    f"Row {row_number}, Demo '{current_row_slug}': UNIQUE constraint failed for section_order '{section_order_val}'. "
                                    "This section_order likely already exists for this demo (duplicate in CSV or previous run without clearing). Skipping."
                                ))
                        elif demo_instance and raw_section_order : # If order is there but no content, log it.
                             self.stdout.write(self.style.NOTICE(f"Row {row_number}, Demo '{current_row_slug}', Section Order '{raw_section_order}': Section order present but no markdown or code snippet found. Section not created."))


                    except Demo.DoesNotExist:
                        # This case should not happen if update_or_create was successful or demo_instance was fetched.
                        self.stdout.write(self.style.ERROR(f"Row {row_number}: Demo with slug '{current_row_slug}' could not be found or created. Skipping section processing."))
                    except IntegrityError as ie:
                        self.stdout.write(self.style.ERROR(f"Row {row_number}, Demo '{current_row_slug}': Database integrity error - {ie}. This might be a slug conflict if your DB is case-sensitive and slugs differ only by case."))
                    except Exception as e_row:
                        self.stdout.write(self.style.ERROR(f"Error processing row {row_number} (Demo Slug: '{current_row_slug}'): {e_row}"))
                        continue # Continue to the next row

                self.stdout.write(self.style.SUCCESS('Successfully completed processing CSV for Demo and DemoSection models.'))

        except FileNotFoundError:
            raise CommandError(f"CSV file not found at {csv_file_path_absolute}")
        except UnicodeDecodeError as ude:
            raise CommandError(f"UnicodeDecodeError reading CSV: {ude}. Try a different encoding with --encoding option (e.g., latin-1, windows-1252) or ensure file is {csv_encoding}. Problematic byte: {ude.object[ude.start:ude.end]}")
        except Exception as e:
            raise CommandError(f"An unexpected error occurred: {e}")
