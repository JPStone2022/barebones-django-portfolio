# demos/management/commands/populate_demos_from_csv.py
import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import IntegrityError, transaction
from demos.models import Demo, DemoSection # Ensure DemoSection is also imported
from django.utils.text import slugify

class Command(BaseCommand):
    help = (
        'Populates Demo and DemoSection models from two specified CSV files. '
        'One CSV for demo summaries, and one for demo content and sections.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'summary_csv_path',
            type=str,
            help='The path to the demo summaries CSV file relative to the project base directory.'
        )
        parser.add_argument(
            'content_csv_path',
            type=str,
            help='The path to the demo content and sections CSV file relative to the project base directory.'
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8-sig', # Default to utf-8-sig to handle BOM
            help='Encoding of the CSV files (e.g., utf-8, latin-1, windows-1252).'
        )

    def _read_csv(self, file_path_relative, encoding, required_headers):
        """Helper function to read a CSV file and check for required headers."""
        file_path_absolute = os.path.join(settings.BASE_DIR, file_path_relative)
        self.stdout.write(self.style.SUCCESS(f"Processing CSV file: {file_path_absolute} with encoding {encoding}"))

        if not os.path.exists(file_path_absolute):
            raise CommandError(f"CSV file not found at {file_path_absolute}")

        try:
            with open(file_path_absolute, mode='r', encoding=encoding) as file:
                reader = csv.DictReader(file)
                if not reader.fieldnames:
                    raise CommandError(f"CSV file {file_path_absolute} appears to be empty or has no header row.")

                # Check for essential columns
                missing_headers = [header for header in required_headers if header not in reader.fieldnames]
                if missing_headers:
                    raise CommandError(f"Missing essential column(s) in {file_path_absolute}: {', '.join(missing_headers)}. "
                                       f"Expected headers: {', '.join(required_headers)}. Found: {', '.join(reader.fieldnames)}")
                return list(reader) # Return list of rows (dictionaries)
        except FileNotFoundError:
            raise CommandError(f"CSV file not found at {file_path_absolute}")
        except UnicodeDecodeError as ude:
            raise CommandError(
                f"UnicodeDecodeError reading {file_path_absolute}: {ude}. "
                f"Try a different encoding with --encoding option (e.g., latin-1, windows-1252) "
                f"or ensure file is {encoding}. Problematic byte: {ude.object[ude.start:ude.end]}"
            )
        except Exception as e:
            raise CommandError(f"An unexpected error occurred while reading {file_path_absolute}: {e}")


    @transaction.atomic # Ensure all database operations are atomic
    def handle(self, *args, **options):
        summary_csv_path_relative = options['summary_csv_path']
        content_csv_path_relative = options['content_csv_path']
        csv_encoding = options['encoding']

        # --- Define expected headers ---
        # For Summary CSV (Demo model - primary info for cards/listings)
        summary_demo_slug_col = 'demo_slug'
        summary_title_col = 'title' # This will be Demo.title
        summary_demo_description_col = 'demo_description' # This will be Demo.description
        summary_demo_image_url_col = 'demo_image_url' # This will be Demo.image_url
        summary_required_headers = [
            summary_demo_slug_col, summary_title_col,
            summary_demo_description_col, summary_demo_image_url_col
        ]

        # For Content CSV (Demo model - metadata for detail page, and DemoSection model)
        content_demo_slug_col = 'demo_slug' # Essential for linking
        content_page_meta_title_col = 'page_title_csv' # This will be Demo.page_meta_title
        content_meta_description_col = 'meta_description_csv' # This will be Demo.meta_description
        content_meta_keywords_col = 'meta_keywords_csv' # This will be Demo.meta_keywords
        # For DemoSection model (content part):
        section_order_col = 'section_order'
        section_title_col = 'section_title'
        section_content_markdown_col = 'section_content_markdown'
        code_language_col = 'code_language'
        code_snippet_title_col = 'code_snippet_title'
        code_snippet_col = 'code_snippet'
        code_snippet_explanation_col = 'code_snippet_explanation'
        
        # Required headers for the content CSV (can be adjusted based on minimum requirements)
        content_required_headers = [
            content_demo_slug_col, # Must be present to link
            # Add other metadata columns if they are strictly required for every demo
            # section_order_col # Only required if sections are always expected
        ]


        # --- 1. Process Summary CSV ---
        self.stdout.write(self.style.MIGRATE_HEADING("--- Processing Summary CSV ---"))
        summary_rows = self._read_csv(summary_csv_path_relative, csv_encoding, summary_required_headers)
        demos_map = {} # To store demo instances by slug for quick lookup

        for row_number, row in enumerate(summary_rows, 1):
            current_row_slug = row.get(summary_demo_slug_col, '').strip()
            if not current_row_slug:
                self.stdout.write(self.style.WARNING(f"Summary CSV Row {row_number}: Skipping due to missing '{summary_demo_slug_col}'."))
                continue

            try:
                # These fields are primarily for the card display on all_demos page
                demo_defaults = {
                    'title': row.get(summary_title_col, '').strip() or slugify(current_row_slug).replace('-', ' ').title(),
                    'description': row.get(summary_demo_description_col, '').strip() or None, # For card display
                    'image_url': row.get(summary_demo_image_url_col, '').strip() or None, # For card display
                    # Fields not in summary CSV will use model defaults or be populated from content CSV / admin:
                    # 'page_meta_title', 'meta_description', 'meta_keywords' (from content CSV)
                    # 'order', 'is_featured', 'demo_url_name' (from admin or if added to a CSV)
                }

                demo_instance, created = Demo.objects.update_or_create(
                    slug=current_row_slug,
                    defaults=demo_defaults
                )
                demos_map[current_row_slug] = demo_instance
                action = "Created" if created else "Updated summary for"
                self.stdout.write(self.style.SUCCESS(f"Summary CSV Row {row_number}: {action} Demo: '{demo_instance.title}' (Slug: {demo_instance.slug})"))

            except IntegrityError as ie:
                self.stdout.write(self.style.ERROR(
                    f"Summary CSV Row {row_number}, Demo '{current_row_slug}': Database integrity error - {ie}. "
                    "This might be a slug conflict if your DB is case-sensitive and slugs differ only by case, or another unique constraint violation."
                ))
            except Exception as e_row:
                self.stdout.write(self.style.ERROR(f"Summary CSV Row {row_number}: Error processing (Demo Slug: '{current_row_slug}'): {e_row}"))
                continue

        if not demos_map:
            self.stdout.write(self.style.WARNING("No demos were processed from the summary CSV. Halting content processing if no demos exist."))
            # Depending on desired behavior, you might want to return or allow content processing if demos could exist from other means.
            # For now, we'll let it proceed to content CSV processing, which will skip rows if slugs don't match.

        # --- 2. Process Content CSV ---
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Processing Content CSV ---"))
        # Check if content_required_headers are present before reading
        # For flexibility, we'll make content_required_headers minimal (just demo_slug)
        # and check for other headers row by row.
        content_rows = self._read_csv(content_csv_path_relative, csv_encoding, [content_demo_slug_col])


        processed_metadata_for_slugs = set()
        cleared_sections_for_demo_slugs = set()

        for row_number, row in enumerate(content_rows, 1):
            current_row_slug = row.get(content_demo_slug_col, '').strip()
            if not current_row_slug:
                self.stdout.write(self.style.WARNING(f"Content CSV Row {row_number}: Skipping due to missing '{content_demo_slug_col}'."))
                continue

            demo_instance = demos_map.get(current_row_slug)
            if not demo_instance:
                # Attempt to fetch from DB if not in summary CSV (e.g. demo created manually)
                try:
                    demo_instance = Demo.objects.get(slug=current_row_slug)
                    self.stdout.write(self.style.NOTICE(
                        f"Content CSV Row {row_number}: Demo with slug '{current_row_slug}' found in DB but not in summary CSV. Proceeding with content."
                    ))
                except Demo.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"Content CSV Row {row_number}: Demo with slug '{current_row_slug}' not found from summary CSV or DB. Skipping this content row."
                    ))
                    continue

            try:
                # --- Update Demo Metadata (once per demo from content CSV) ---
                # These fields are primarily for the detailed demo page's SEO
                if current_row_slug not in processed_metadata_for_slugs:
                    needs_save = False
                    # Only update if the column exists in the CSV row and has a value
                    if content_page_meta_title_col in row and row.get(content_page_meta_title_col, '').strip():
                        demo_instance.page_meta_title = row.get(content_page_meta_title_col, '').strip()
                        needs_save = True
                    elif not demo_instance.page_meta_title: # Fallback if not set and not in CSV
                        demo_instance.page_meta_title = demo_instance.title # Use main title
                        needs_save = True

                    if content_meta_description_col in row and row.get(content_meta_description_col, '').strip():
                        demo_instance.meta_description = row.get(content_meta_description_col, '').strip()
                        needs_save = True
                    elif not demo_instance.meta_description: # Fallback
                        demo_instance.meta_description = f"Learn more about {demo_instance.title}."
                        needs_save = True
                        
                    if content_meta_keywords_col in row and row.get(content_meta_keywords_col, '').strip():
                        demo_instance.meta_keywords = row.get(content_meta_keywords_col, '').strip()
                        needs_save = True
                    elif not demo_instance.meta_keywords: # Fallback
                        demo_instance.meta_keywords = f"{slugify(current_row_slug).replace('-', ' ')}, demo"
                        needs_save = True

                    if needs_save:
                        demo_instance.save() 
                    processed_metadata_for_slugs.add(current_row_slug)
                    self.stdout.write(self.style.SUCCESS(
                        f"Content CSV Row {row_number}: Updated/Ensured metadata for Demo '{demo_instance.title}' (Slug: {current_row_slug})"
                    ))

                # --- Clear old sections for this demo (once per demo) ---
                if current_row_slug not in cleared_sections_for_demo_slugs:
                    DemoSection.objects.filter(demo=demo_instance).delete()
                    self.stdout.write(self.style.WARNING(f"Cleared old sections for Demo: '{demo_instance.title}' (Slug: {current_row_slug})"))
                    cleared_sections_for_demo_slugs.add(current_row_slug)

                # --- Create DemoSection instance (if section data is present) ---
                raw_section_order = row.get(section_order_col, '').strip()
                raw_section_content = row.get(section_content_markdown_col, '').strip()
                raw_code_snippet = row.get(code_snippet_col, '').strip()

                # Only process section if order and some content exists
                if raw_section_order and (raw_section_content or raw_code_snippet):
                    try:
                        section_order_val = float(raw_section_order)
                    except ValueError:
                        self.stdout.write(self.style.WARNING(
                            f"Content CSV Row {row_number}, Demo '{current_row_slug}': Invalid section_order '{raw_section_order}'. Skipping section."
                        ))
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
                        self.stdout.write(self.style.SUCCESS(
                             f"Content CSV Row {row_number}: Created Section (Order: {section_order_val}) for Demo '{current_row_slug}'"
                        ))
                    except IntegrityError:
                        self.stdout.write(self.style.ERROR(
                            f"Content CSV Row {row_number}, Demo '{current_row_slug}': UNIQUE constraint failed for section_order '{section_order_val}'. "
                            "This section_order likely already exists for this demo (duplicate in CSV). Skipping this section."
                        ))
                elif raw_section_order: # If order is there but no content, log it.
                     self.stdout.write(self.style.NOTICE(
                         f"Content CSV Row {row_number}, Demo '{current_row_slug}', Section Order '{raw_section_order}': "
                         "Section order present but no markdown or code snippet found. Section not created."
                     ))

            except IntegrityError as ie_demo_update: 
                 self.stdout.write(self.style.ERROR(
                    f"Content CSV Row {row_number}, Demo '{current_row_slug}': Database integrity error during demo metadata update - {ie_demo_update}."
                ))
            except Exception as e_row_content:
                self.stdout.write(self.style.ERROR(f"Content CSV Row {row_number}: Error processing (Demo Slug: '{current_row_slug}'): {e_row_content}"))
                continue # Continue to the next row

        self.stdout.write(self.style.SUCCESS('\nSuccessfully completed processing both CSV files for Demo and DemoSection models.'))
