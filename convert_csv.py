import csv
import io

def process_demo_content_sections(demos_content_csv_string):
    """
    Reads the demo content CSV string and aggregates sections for each demo_slug
    into a Markdown formatted string.

    Args:
        demos_content_csv_string (str): String content of the 07b_demos_content.csv.

    Returns:
        dict: A dictionary where keys are demo_slugs and values are
              aggregated Markdown strings of their content sections.
    """
    content_by_slug = {}
    
    content_file = io.StringIO(demos_content_csv_string)
    # Headers expected: demo_slug, section_order, section_title, section_content_markdown, 
    #                   code_language, code_snippet_title, code_snippet, code_snippet_explanation
    content_reader = csv.DictReader(content_file)
    
    raw_sections = {}
    for row in content_reader:
        slug = row.get('demo_slug')
        if not slug:
            continue
        if slug not in raw_sections:
            raw_sections[slug] = []
        
        try:
            row['section_order'] = float(row.get('section_order', 999)) 
        except ValueError:
            row['section_order'] = 999 
        raw_sections[slug].append(row)

    for slug, sections in raw_sections.items():
        sections.sort(key=lambda x: x['section_order'])
        
        aggregated_markdown = []
        for section in sections:
            section_md = []
            if section.get('section_title'):
                section_md.append(f"## {section.get('section_title')}\n")
            
            if section.get('section_content_markdown'):
                section_md.append(f"{section.get('section_content_markdown')}\n")
            
            if section.get('code_snippet'):
                code_title = section.get('code_snippet_title') or "Code Example"
                language = section.get('code_language') or "plaintext"
                section_md.append(f"### {code_title}\n")
                section_md.append(f"```{language}\n{section.get('code_snippet')}\n```\n")
            
            if section.get('code_snippet_explanation'):
                section_md.append(f"**Explanation:**\n{section.get('code_snippet_explanation')}\n")
            
            if section_md:
                 aggregated_markdown.append("\n".join(section_md))

        content_by_slug[slug] = "\n---\n\n".join(aggregated_markdown)

    return content_by_slug

def convert_demos_to_projects_with_content(demos_summary_csv_content, 
                                           aggregated_demo_contents, 
                                           projects_csv_header_list):
    """
    Converts demo summary data to project data format, incorporating
    aggregated markdown content for long_description.

    Args:
        demos_summary_csv_content (str): String content of the demos summary CSV.
        aggregated_demo_contents (dict): Dict with demo_slug as key and 
                                         aggregated markdown string as value.
        projects_csv_header_list (list): A list of header strings for the output projects CSV.

    Returns:
        str: A string containing the new project data in CSV format.
    """
    converted_projects = []
    
    demos_file = io.StringIO(demos_summary_csv_content)
    demo_reader = csv.DictReader(demos_file)

    for demo_row in demo_reader:
        project_entry = {}
        current_slug = demo_row.get('demo_slug', '')

        project_entry['title'] = demo_row.get('title', 'N/A')
        project_entry['slug'] = current_slug
        project_entry['description'] = demo_row.get('demo_description', 'N/A')
        project_entry['image_url'] = demo_row.get('demo_image_url', '')

        if current_slug:
            project_entry['demo_url'] = f"/demos/concepts/{current_slug}/" 
        else:
            project_entry['demo_url'] = ''

        project_entry['long_description_markdown'] = aggregated_demo_contents.get(
            current_slug, 
            f"Details for {project_entry['title']}. No detailed section content was found for this demo slug."
        )
        
        project_entry['results_metrics'] = "To be detailed."
        project_entry['challenges'] = "To be detailed."
        project_entry['lessons_learned'] = "To be detailed."
        project_entry['code_snippet'] = ""
        project_entry['code_language'] = ""
        project_entry['github_url'] = ""
        project_entry['paper_url'] = ""
        project_entry['order'] = "0"
        project_entry['is_featured'] = "False"
        project_entry['skills'] = "Conceptual Understanding, Content Creation" 
        project_entry['topics'] = "Technology Overview"
        
        for header_item in projects_csv_header_list:
            if header_item not in project_entry:
                project_entry[header_item] = ""

        converted_projects.append(project_entry)

    output_csv_string = io.StringIO()
    writer = csv.DictWriter(output_csv_string, fieldnames=projects_csv_header_list, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(converted_projects)

    return output_csv_string.getvalue()

if __name__ == '__main__':
    # --- Define file paths ---
    # IMPORTANT: Replace these with the actual paths to your CSV files
    demos_summary_file_path = 'data_import/07a_demos_summary.csv'  # Or full path like '/path/to/your/07a_demos_summary.csv'
    demos_content_file_path = 'data_import/07b_demos_content.csv'  # Or full path
    projects_template_file_path = 'data_import/05_projects.csv' # To get the headers for the output
    output_file_path = 'converted_demos_to_projects.csv'

    # --- Read file contents ---
    try:
        with open(demos_summary_file_path, 'r', encoding='utf-8-sig') as f_summary: # utf-8-sig handles potential BOM
            demos_summary_content_str = f_summary.read()
        print(f"Successfully read: {demos_summary_file_path}")

        with open(demos_content_file_path, 'r', encoding='utf-8-sig') as f_content:
            demos_content_sections_str = f_content.read()
        print(f"Successfully read: {demos_content_file_path}")

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

    # --- Process and Convert ---
    print("--- Processing Demo Content Sections ---")
    aggregated_contents = process_demo_content_sections(demos_content_sections_str)
    
    # For debugging, print a sample of aggregated content (optional)
    # if aggregated_contents:
    #     first_slug = next(iter(aggregated_contents))
    #     print(f"\nSample Aggregated Markdown for '{first_slug}':\n{aggregated_contents[first_slug][:500]}...")
    # print("\n--- End of Sample Aggregated Content ---\n")

    print("--- Converting Demos to Projects ---")
    converted_csv_data = convert_demos_to_projects_with_content(
        demos_summary_content_str,
        aggregated_contents,
        actual_projects_headers
    )
    
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

