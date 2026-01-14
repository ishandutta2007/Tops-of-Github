import matplotlib.pyplot as plt
import pandas as pd
import re
import os

def extract_country_data(readme_content):
    """
    Extracts country data from the 'Top 100 Starred repositories' table in README.md.
    Assumes the table has a 'Country' column.
    """
    country_counts = {}
    
    # Regex to find the table for 'Top 100 Starred repositories'
    # This might need adjustment based on the exact markdown structure if it changes.
    # We are looking for the section header and then the table rows.
    
    # Find the start of the "Top 100 Starred repositories" section
    start_marker = "## Top 100 Starred repositories"
    end_marker_pattern = r"^(##\s+.*?|\\[.*?\\]\(.*?\\]|```.*?)$" # Next section header or code block or link

    start_idx = readme_content.find(start_marker)
    if start_idx == -1:
        print(f"'{start_marker}' not found in README.md. Cannot extract country data.")
        return {}

    content_after_start = readme_content[start_idx:]
    
    # Find the table header (which contains 'Country')
    header_match = re.search(r"\|.*?(Country).*?\|", content_after_start, re.IGNORECASE)
    if not header_match:
        print("Country column header not found in the identified table.")
        return {}
    
    header_line = header_match.group(0)
    columns = [col.strip() for col in header_line.split('|') if col.strip()]
    
    try:
        country_col_index = columns.index("Country")
    except ValueError:
        print("'Country' column not found in table header.")
        return {}

    # Extract table rows. We need to go from the header line to the end of the table.
    # The table data starts two lines after the header (after the separator line).
    
    lines = content_after_start.splitlines()
    table_started = False
    data_lines = []
    
    for i, line in enumerate(lines):
        if line.strip() == header_line.strip(): # Found the header
            table_started = True
            continue
        
        if table_started and line.strip().startswith('|') and re.match(r"\|[ - :]*\|", line) and i == lines.index(line):
            # This is the separator line, data comes after this
            continue
            
        if table_started and line.strip().startswith('|'):
            data_lines.append(line)
        elif table_started and not line.strip(): # Empty line after table data, usually marks end
            break
        elif table_started and re.match(end_marker_pattern, line): # Next markdown section
            break
        elif table_started and not line.strip().startswith('|'): # Any line not starting with | after table started
            break

    for line in data_lines:
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) > country_col_index:
            country = parts[country_col_index]
            country_counts[country] = country_counts.get(country, 0) + 1
            
    return country_counts

def generate_pie_chart(country_counts, output_path="country_distribution.png"):
    """
    Generates a pie chart from country counts and saves it to a file.
    """
    if not country_counts:
        print("No country data to generate chart.")
        return False

    labels = list(country_counts.keys())
    sizes = list(country_counts.values())

    # Sort by size for better visualization if many slices
    sorted_pairs = sorted(zip(sizes, labels), reverse=True)
    sizes, labels = zip(*sorted_pairs)

    # Combine small slices into 'Other'
    threshold = sum(sizes) * 0.03 # e.g., 3% of total
    main_labels = []
    main_sizes = []
    other_size = 0

    for i in range(len(labels)):
        if sizes[i] > threshold:
            main_labels.append(labels[i])
            main_sizes.append(sizes[i])
        else:
            other_size += sizes[i]
            
    if other_size > 0:
        main_labels.append('Other')
        main_sizes.append(other_size)

    fig1, ax1 = plt.subplots(figsize=(10, 10))
    wedges, texts, autotexts = ax1.pie(main_sizes, labels=main_labels, autopct='%1.1f%%', startangle=90,
                                       pctdistance=0.85, textprops={'fontsize': 10})
    
    # Draw a circle at the center to make it a donut chart
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('Distribution of Repository Owners by Country', fontsize=16)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Pie chart saved to {output_path}")
    return True

def update_readme_with_chart(readme_path="README.md", chart_image_path="country_distribution.png"):
    """
    Adds or updates the pie chart image reference in README.md.
    """
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    chart_markdown = f"\n## Repository Owner Country Distribution\n\n![Country Distribution]({chart_image_path})\n"
    
    # Find the insertion point: after the "Top 100 Starred repositories" table.
    # This might be tricky if there are multiple tables or the structure changes.
    # I'll look for the end of the "Top 100 Starred repositories" data,
    # and insert the chart markdown before the next '##' header or end of file.
    
    # A more robust way: find a specific anchor or section.
    # For now, let's assume it should go after the last data row of the main table.
    
    # Find the main table's start
    table_start_marker = "## Top 100 Starred repositories"
    table_start_idx = content.find(table_start_marker)

    if table_start_idx == -1:
        print(f"Could not find '{table_start_marker}' in README.md. Appending chart to end.")
        if chart_markdown not in content:
            content += chart_markdown
        return content

    # Find the end of the markdown table data
    # This regex looks for the end of the last table row, followed by an optional empty line
    # and then either the end of the string or another markdown header.
    # This is a heuristic and might need tuning.
    table_end_pattern = re.compile(r"(\|.*\|(?:\n\n|\n(?!\||#))|\Z)", re.DOTALL)
    
    # Search from the table_start_idx to ensure we are in the correct table context
    match = table_end_pattern.search(content, table_start_idx)
    
    insert_idx = -1
    if match:
        insert_idx = match.end()
    else:
        # Fallback if pattern doesn't match perfectly, append to end of file
        insert_idx = len(content)

    # Check if the chart markdown is already present and update if necessary
    existing_chart_pattern = re.compile(r"\n## Repository Owner Country Distribution\n\n!\\[Country Distribution\\]\(.*?\.png\)\\n")
    existing_chart_match = existing_chart_pattern.search(content, insert_idx - len(chart_markdown) - 100) # Search slightly before expected insertion
    
    if existing_chart_match:
        # Replace existing chart markdown
        content = existing_chart_pattern.sub(chart_markdown, content)
        print("Updated existing chart in README.md")
    else:
        # Insert new chart markdown
        content = content[:insert_idx] + chart_markdown + content[insert_idx:]
        print("Inserted new chart into README.md")

    return content

def main():
    readme_path = "README.md"
    chart_image_name = "country_distribution.png"

    # Read README.md
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()
    except FileNotFoundError:
        print(f"Error: {readme_path} not found.")
        return

    # Extract country data
    country_counts = extract_country_data(readme_content)
    
    if not country_counts:
        print("No country data extracted. Exiting.")
        return

    # Generate and save pie chart
    if generate_pie_chart(country_counts, chart_image_name):
        # Update README.md with chart image reference
        updated_readme_content = update_readme_with_chart(readme_path, chart_image_name)

        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(updated_readme_content)
        print(f"Successfully updated {readme_path} with the pie chart.")
    else:
        print("Failed to generate pie chart.")

if __name__ == "__main__":
    main()
