# recommendations/management/commands/populate_recommendations_from_csv.py
import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import IntegrityError, transaction
from recommendations.models import RecommendedProduct, RecommendationSection
from django.utils.text import slugify

class Command(BaseCommand):
    help = (
        'Populates RecommendedProduct and RecommendationSection models from two CSV files. '
        'One for recommendation summaries, one for detailed content and sections.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'summary_csv_path',
            type=str,
            help='Path to the recommendation summaries CSV file (relative to project base directory).'
        )
        parser.add_argument(
            'content_csv_path',
            type=str,
            help='Path to the recommendation content and sections CSV file (relative to project base directory).'
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8-sig',
            help='Encoding of the CSV files (e.g., utf-8, latin-1).'
        )

    def _read_csv(self, file_path_relative, encoding, required_headers):
        file_path_absolute = os.path.join(settings.BASE_DIR, file_path_relative)
        self.stdout.write(self.style.SUCCESS(f"Processing CSV: {file_path_absolute} (Encoding: {encoding})"))
        if not os.path.exists(file_path_absolute):
            raise CommandError(f"CSV file not found: {file_path_absolute}")
        try:
            with open(file_path_absolute, mode='r', encoding=encoding) as file:
                reader = csv.DictReader(file)
                if not reader.fieldnames:
                    raise CommandError(f"CSV {file_path_absolute} is empty or has no header.")
                missing_headers = [h for h in required_headers if h not in reader.fieldnames]
                if missing_headers:
                    raise CommandError(
                        f"Missing headers in {file_path_absolute}: {', '.join(missing_headers)}. "
                        f"Expected: {', '.join(required_headers)}. Found: {', '.join(reader.fieldnames)}"
                    )
                # Return list of rows (dictionaries), ensure None values from empty cells are handled if necessary
                # csv.DictReader typically yields empty strings for empty cells, not None,
                # unless the CSV explicitly contains 'None' or 'NULL' as strings.
                return list(reader)
        except Exception as e:
            raise CommandError(f"Error reading {file_path_absolute}: {e}")

    @transaction.atomic
    def handle(self, *args, **options):
        summary_csv_path = options['summary_csv_path']
        content_csv_path = options['content_csv_path']
        csv_encoding = options['encoding']

        # --- Define expected CSV column names ---
        s_slug_col = 'reco_slug'
        s_name_col = 'name'
        s_short_desc_col = 'short_description'
        s_category_col = 'category'
        s_product_url_col = 'product_url'
        s_image_url_col = 'image_url'
        s_order_col = 'order'
        summary_required_headers = [s_slug_col, s_name_col, s_product_url_col]

        c_slug_col = 'reco_slug'
        c_meta_title_col = 'page_meta_title'
        c_meta_desc_col = 'page_meta_description'
        c_meta_keywords_col = 'page_meta_keywords'
        c_main_desc_md_col = 'main_description_md'
        c_section_order_col = 'section_order'
        c_section_title_col = 'section_title'
        c_section_content_md_col = 'section_content_markdown'
        content_required_headers = [c_slug_col]

        # --- 1. Process Summary CSV ---
        self.stdout.write(self.style.MIGRATE_HEADING("--- Processing Summary Recommendations CSV ---"))
        summary_rows = self._read_csv(summary_csv_path, csv_encoding, summary_required_headers)
        recommendations_map = {}

        for r_num, row in enumerate(summary_rows, 1):
            # Robustly get and strip values, defaulting to empty string if None
            current_slug = (row.get(s_slug_col) or '').strip()

            if not current_slug:
                self.stdout.write(self.style.WARNING(f"Summary Row {r_num}: Missing '{s_slug_col}'. Skipping."))
                continue

            try:
                name_val = (row.get(s_name_col) or '').strip()
                short_desc_val = (row.get(s_short_desc_col) or '').strip()
                category_val = (row.get(s_category_col) or '').strip()
                product_url_val = (row.get(s_product_url_col) or '').strip() # This is a required header
                image_url_val = (row.get(s_image_url_col) or '').strip()
                order_str_val = (row.get(s_order_col) or '0').strip() # Default order to '0' string if missing

                product_defaults = {
                    'name': name_val or slugify(current_slug).replace('-', ' ').title(),
                    'short_description': short_desc_val or None,
                    'category': category_val or None,
                    'product_url': product_url_val,
                    'image_url': image_url_val or None,
                    'order': int(order_str_val) if order_str_val else 0,
                }

                if not product_defaults['product_url']: # Check after stripping
                    self.stdout.write(self.style.WARNING(f"Summary Row {r_num}, Slug '{current_slug}': Missing or empty '{s_product_url_col}'. Skipping."))
                    continue

                instance, created = RecommendedProduct.objects.update_or_create(
                    slug=current_slug,
                    defaults=product_defaults
                )
                recommendations_map[current_slug] = instance
                action = "Created" if created else "Updated summary for"
                self.stdout.write(self.style.SUCCESS(f"Summary Row {r_num}: {action} RecommendedProduct '{instance.name}' (Slug: {instance.slug})"))
            except ValueError as ve:
                self.stdout.write(self.style.ERROR(f"Summary Row {r_num}, Slug '{current_slug}': Invalid data (e.g., for order: '{order_str_val}') - {ve}. Skipping."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Summary Row {r_num}, Slug '{current_slug}': Error - {e}. Skipping."))

        if not recommendations_map:
            self.stdout.write(self.style.WARNING("No recommendations processed from summary CSV. Halting."))
            return

        # --- 2. Process Content CSV ---
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Processing Content Recommendations CSV ---"))
        content_rows = self._read_csv(content_csv_path, csv_encoding, content_required_headers)
        processed_metadata_slugs = set()
        cleared_sections_slugs = set()

        for r_num, row in enumerate(content_rows, 1):
            current_slug = (row.get(c_slug_col) or '').strip()
            if not current_slug:
                self.stdout.write(self.style.WARNING(f"Content Row {r_num}: Missing '{c_slug_col}'. Skipping."))
                continue

            instance = recommendations_map.get(current_slug)
            if not instance:
                self.stdout.write(self.style.WARNING(f"Content Row {r_num}: Slug '{current_slug}' not found from summary. Skipping content/sections."))
                continue

            try:
                if current_slug not in processed_metadata_slugs:
                    instance.page_meta_title = (row.get(c_meta_title_col) or '').strip() or instance.name
                    instance.page_meta_description = (row.get(c_meta_desc_col) or '').strip() or instance.short_description
                    instance.page_meta_keywords = (row.get(c_meta_keywords_col) or '').strip() or None
                    instance.main_description_md = (row.get(c_main_desc_md_col) or '').strip() or None
                    instance.save()
                    processed_metadata_slugs.add(current_slug)
                    self.stdout.write(self.style.SUCCESS(f"Content Row {r_num}: Updated metadata for '{instance.name}'"))

                if current_slug not in cleared_sections_slugs:
                    RecommendationSection.objects.filter(recommendation=instance).delete()
                    cleared_sections_slugs.add(current_slug)
                    self.stdout.write(self.style.WARNING(f"Cleared old sections for '{instance.name}'"))

                raw_section_order = (row.get(c_section_order_col) or '').strip()
                raw_section_title = (row.get(c_section_title_col) or '').strip()
                raw_section_content_md = (row.get(c_section_content_md_col) or '').strip()

                if raw_section_order and (raw_section_title or raw_section_content_md):
                    try:
                        section_order_val = float(raw_section_order)
                        section_data = {
                            'recommendation': instance,
                            'section_order': section_order_val,
                            'section_title': raw_section_title or None,
                            'section_content_markdown': raw_section_content_md or None,
                        }
                        RecommendationSection.objects.create(**section_data)
                        self.stdout.write(self.style.SUCCESS(f"Content Row {r_num}: Created Section (Order: {section_order_val}) for '{current_slug}'"))
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f"Content Row {r_num}: Invalid '{c_section_order_col}' value ('{raw_section_order}'). Skipping section."))
                    except IntegrityError:
                        self.stdout.write(self.style.ERROR(f"Content Row {r_num}: UNIQUE constraint failed for section_order '{raw_section_order}'. Skipping section."))
                elif raw_section_order:
                    self.stdout.write(self.style.NOTICE(f"Content Row {r_num}: Section order '{raw_section_order}' present but no title or content. Section not created."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Content Row {r_num}, Slug '{current_slug}': Error processing - {e}."))
                continue
        self.stdout.write(self.style.SUCCESS('\nSuccessfully completed processing recommendations CSV files.'))
