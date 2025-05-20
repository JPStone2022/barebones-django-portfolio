import csv
import io

def convert_demos_to_projects(demos_summary_csv_content, projects_csv_header_list):
    """
    Converts demo summary data to project data format.

    Args:
        demos_summary_csv_content (str): String content of the demos summary CSV.
        projects_csv_header_list (list): A list of header strings for the output projects CSV.

    Returns:
        str: A string containing the new project data in CSV format.
    """
    converted_projects = []
    
    # Use io.StringIO to treat the string content as a file
    demos_file = io.StringIO(demos_summary_csv_content)
    demo_reader = csv.DictReader(demos_file)

    for demo_row in demo_reader:
        project_entry = {}

        # --- Direct Mapping ---
        project_entry['title'] = demo_row.get('title', 'N/A')
        project_entry['slug'] = demo_row.get('demo_slug', '') # Essential for URL
        project_entry['description'] = demo_row.get('demo_description', 'N/A')
        project_entry['image_url'] = demo_row.get('demo_image_url', '')

        # --- Constructed/Default Values ---
        if project_entry['slug']:
            project_entry['demo_url'] = f"/demos/concepts/{project_entry['slug']}/" 
        else:
            project_entry['demo_url'] = '' # Avoid URL if slug is missing

        project_entry['long_description_markdown'] = f"Details for {project_entry['title']}. Content to be migrated from demo sections if applicable."
        
        # Default values for other project fields
        project_entry['results_metrics'] = "To be detailed."
        project_entry['challenges'] = "To be detailed."
        project_entry['lessons_learned'] = "To be detailed."
        project_entry['code_snippet'] = ""
        project_entry['code_language'] = ""
        project_entry['github_url'] = ""
        project_entry['paper_url'] = ""
        project_entry['order'] = "0" # CSVs often store numbers as strings
        project_entry['is_featured'] = "False" # Or "0"
        project_entry['skills'] = "Conceptual Understanding, Content Creation" # Generic placeholder
        project_entry['topics'] = "Technology Overview" # Generic placeholder
        
        # Ensure all target headers are present, even if value is empty
        for header_item in projects_csv_header_list:
            if header_item not in project_entry:
                project_entry[header_item] = "" # Add with empty value if not mapped

        converted_projects.append(project_entry)

    # --- Output to CSV String ---
    output_csv_string = io.StringIO()
    # Use the provided projects_csv_header_list for the writer
    writer = csv.DictWriter(output_csv_string, fieldnames=projects_csv_header_list, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(converted_projects)

    return output_csv_string.getvalue()

if __name__ == '__main__':
    # --- Define file paths ---
    # IMPORTANT: Replace these with the actual paths to your CSV files
    demos_summary_file_path = 'data_import/07a_demos_summary.csv'  # Or full path like '/path/to/your/07a_demos_summary.csv'
    projects_template_file_path = 'data_import/05_projects.csv'    # To get the headers for the output
    output_file_path = 'converted_demos_as_projects_basic.csv' # Changed output filename for clarity

    # --- Read file contents ---
    demos_summary_content_str = ""
    actual_projects_headers = []

    try:
        with open(demos_summary_file_path, 'r', encoding='utf-8-sig') as f_demos: # utf-8-sig handles BOM
            demos_summary_content_str = f_demos.read()
        print(f"Successfully read: {demos_summary_file_path}")

        # Read only the header from the projects CSV to define the output structure
        with open(projects_template_file_path, 'r', encoding='utf-8-sig') as f_projects_template:
            project_reader = csv.reader(f_projects_template)
            actual_projects_headers = next(project_reader) 
        print(f"Successfully read headers from: {projects_template_file_path}")
        print(f"Target Project Headers: {actual_projects_headers}\n")

    except FileNotFoundError as e:
        print(f"Error: File not found. Please check the file paths. Details: {e}")
        exit() # Exit the script if files are not found
    except Exception as e:
        print(f"An error occurred while reading files: {e}")
        exit()

    # Perform the conversion
    if demos_summary_content_str and actual_projects_headers:
        converted_csv_data = convert_demos_to_projects(demos_summary_content_str, actual_projects_headers)
        
        # --- Write to Output File ---
        try:
            with open(output_file_path, 'w', newline='', encoding='utf-8') as outfile:
                outfile.write(converted_csv_data)
            print(f"\nConversion complete. Output written to '{output_file_path}'")
            print("\n--- First few lines of the output file: ---")
            # Print first few lines of the output for quick check
            output_lines = converted_csv_data.splitlines()
            for i, line in enumerate(output_lines):
                if i < 5: # Print header + first 4 data rows
                    print(line)
                else:
                    break
        except Exception as e:
            print(f"An error occurred while writing the output file: {e}")
    else:
        print("Could not perform conversion due to missing file content or headers.")
