# core/management/commands/initial_populate_all.py
# (Place this in a 'core' app or your main 'portfolio' app's management/commands directory)

from django.core.management.base import BaseCommand, CommandError
from django.core import management
from django.conf import settings
import os

# Define the sequence of data to import and their respective CSV files and parameters.
# Assumes CSV_FILES is defined in settings.py as suggested.
# Example settings.py entry:
# CSV_FILES = {
#     'SKILLCATEGORIES_CSV': os.path.join(BASE_DIR, 'data_import/01_skill_categories.csv'),
#     'SKILLS_CSV': os.path.join(BASE_DIR, 'data_import/02_skills.csv'),
#     # ... other file paths ...
# }

INITIAL_IMPORT_CONFIG = [
    {
        'label': 'User Profile',
        'command_name': 'import_data',
        'csv_filepath_setting': 'USER_PROFILE_CSV', # New key for settings.CSV_FILES
        'model_type': 'userprofile',
        'unique_field': 'site_identifier', # UserProfile uses 'site_identifier'
        'update': True # Ensures it updates the existing one or creates if not present
    },
    {
        'label': 'Skill Categories',
        'command_name': 'import_data',
        'csv_filepath_setting': 'SKILLCATEGORIES_CSV', # Key in settings.CSV_FILES
        'model_type': 'skillcategories',
        'unique_field': 'name',
        'update': True
    },
    {
        'label': 'Skills',
        'command_name': 'import_data',
        'csv_filepath_setting': 'SKILLS_CSV',
        'model_type': 'skills',
        'unique_field': 'name',
        'update': True
    },
    {
        'label': 'Project Topics',
        'command_name': 'import_data',
        'csv_filepath_setting': 'TOPICS_CSV',
        'model_type': 'topics',
        'unique_field': 'name',
        'update': True
    },
    {
        'label': 'Certificates',
        'command_name': 'import_data',
        'csv_filepath_setting': 'CERTIFICATES_CSV',
        'model_type': 'certificates',
        'unique_field': 'title',
        'update': True
    },
    {
        'label': 'Projects',
        'command_name': 'import_data',
        'csv_filepath_setting': 'PROJECTS_CSV',
        'model_type': 'projects',
        'unique_field': 'title',
        'update': True
    },
    {
        'label': 'Blog Posts',
        'command_name': 'import_data',
        'csv_filepath_setting': 'BLOGPOSTS_CSV',
        'model_type': 'blogposts',
        'unique_field': 'title',
        'update': True
    },
    { # NEW ENTRY for Colophon
        'label': 'Colophon Entries',
        'command_name': 'import_data',
        'csv_filepath_setting': 'COLOPHON_ENTRIES_CSV', # Needs to be added to settings.CSV_FILES
        'model_type': 'colophonentires', # Matches MODEL_MAP key in import_data.py
        'unique_field': 'name', # Assuming 'name' is unique enough for colophon entries
        'update': True
    },
    {
        'label': 'Demos (Summary & Content)',
        'command_name': 'populate_demos_from_csv',
        'args_settings_keys': [
            'DEMOS_SUMMARY_CSV',
            'DEMOS_CONTENT_CSV'
        ],
    },
    {
        'label': 'Recommendations (Summary & Content)',
        'command_name': 'populate_recommendations_from_csv',
        'args_settings_keys': [
            'RECOMMENDATIONS_SUMMARY_CSV',
            'RECOMMENDATIONS_CONTENT_CSV'
        ],
    },
]

class Command(BaseCommand):
    help = 'Performs the initial comprehensive population of the database from predefined CSV files configured in settings.CSV_FILES.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting initial database population sequence..."))
        self.stdout.write(self.style.WARNING("This will attempt to import data for all configured models. Ensure your database is clean or backups exist if running on existing data."))

        if not hasattr(settings, 'CSV_FILES') or not isinstance(settings.CSV_FILES, dict):
            raise CommandError("The 'CSV_FILES' dictionary is not defined in your Django settings.py.")

        for config_item in INITIAL_IMPORT_CONFIG:
            label = config_item['label']
            command_name = config_item['command_name']
            
            # These will store arguments for management.call_command
            positional_args_for_call = []
            keyword_options_for_call = {}

            self.stdout.write(self.style.MIGRATE_HEADING(f"\n--- Importing: {label} ---"))

            try:
                # Prepare arguments and options based on command type
                if 'args_settings_keys' in config_item: # For commands like populate_demos_from_csv
                    for key in config_item['args_settings_keys']:
                        if key not in settings.CSV_FILES:
                            raise CommandError(f"CSV file key '{key}' for '{label}' not found in settings.CSV_FILES.")
                        positional_args_for_call.append(settings.CSV_FILES[key])
                
                if command_name == 'import_data':
                    csv_key = config_item.get('csv_filepath_setting')
                    if not csv_key or csv_key not in settings.CSV_FILES:
                        raise CommandError(f"CSV file key '{csv_key}' for '{label}' not found or not specified in settings.CSV_FILES.")
                    
                    # 'csv_filepath' is a positional argument for import_data
                    positional_args_for_call.append(settings.CSV_FILES[csv_key]) 
                    
                    # Other arguments for import_data are optional/keyword arguments
                    keyword_options_for_call['model_type'] = config_item['model_type']
                    keyword_options_for_call['unique_field'] = config_item.get('unique_field', 'slug')
                    if config_item.get('update', False):
                        keyword_options_for_call['update'] = True
                    if 'encoding' in config_item: # Allow overriding encoding per config item
                         keyword_options_for_call['encoding'] = config_item['encoding']


                # Call the command
                management.call_command(command_name, *positional_args_for_call, **keyword_options_for_call)

                self.stdout.write(self.style.SUCCESS(f"Successfully imported {label}."))

            except KeyError as ke:
                self.stderr.write(self.style.ERROR(f"Configuration error for '{label}': Missing key {ke} in settings.CSV_FILES or config_item."))
                self.stdout.write(self.style.WARNING(f"Skipping {label} due to configuration error. Continuing with next item..."))
            except CommandError as ce:
                self.stderr.write(self.style.ERROR(f"CommandError during import of {label}: {ce}"))
                self.stdout.write(self.style.WARNING(f"Skipping {label} due to error. Continuing with next item..."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"An unexpected error occurred importing {label}: {e}"))
                self.stdout.write(self.style.WARNING(f"Skipping {label} due to unexpected error. Continuing with next item..."))

        self.stdout.write(self.style.SUCCESS("\nInitial database population sequence complete!"))
        
        # self.stdout.write(self.style.NOTICE("Remember to create a superuser if you haven't already (if the migration didn't run or env vars weren't set): python manage.py createsuperuser"))
