import re
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# --- Configuration ---
README_FILE = "README.md"
GITHUB_API_URL = "https://api.github.com"
# Consider setting a GitHub Personal Access Token as an environment variable
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

print(f"Using GITHUB_TOKEN: {'Yes' if GITHUB_TOKEN else 'No'}")
if GITHUB_TOKEN:
    print(f"Headers configured: {{'Authorization': 'token <redacted>'}}")
else:
    print("No GITHUB_TOKEN found, requests will be unauthenticated.")

# Simple city to country mapping (can be expanded)
CITY_TO_COUNTRY = {
    "san francisco": "USA",
    "london": "UK",
    "new york": "USA",
    "seattle": "USA",
    "beijing": "China",
    "shanghai": "China",
    "tokyo": "Japan",
    "berlin": "Germany",
    "paris": "France",
    "amsterdam": "Netherlands",
    "montreal": "Canada",
    "toronto": "Canada",
    "singapore": "Singapore",
    "sydney": "Australia",
    "bangalore": "India",
    "mumbai": "India",
    "delhi": "India",
    "dublin": "Ireland",
    "stockholm": "Sweden",
    "helsinki": "Finland",
    "oslo": "Norway",
    "copenhagen": "Denmark",
    "zurich": "Switzerland",
    "taipei": "Taiwan",
    "hong kong": "Hong Kong",
    "moscow": "Russia",
    "warsaw": "Poland",
    "barcelona": "Spain",
    "madrid": "Spain",
    "tel aviv": "Israel",
    "istanbul": "Turkey",
    "rio de janeiro": "Brazil",
    "sao paulo": "Brazil",
    "mexico city": "Mexico",
    "vancouver": "Canada",
    "chennai": "India",
    "hyderabad": "India",
    "pune": "India",
    "glasgow": "UK",
    "edinburgh": "UK",
    "kyiv": "Ukraine",
    "budapest": "Hungary",
    "prague": "Czech Republic",
    "vienna": "Austria",
    "rome": "Italy",
    "milan": "Italy",
    "seoul": "South Korea",
    "frankfurt": "Germany",
    "munich": "Germany",
    "hamburg": "Germany",
    "dallas": "USA",
    "austin": "USA",
    "chicago": "USA",
    "boston": "USA",
    "los angeles": "USA",
    "portland": "USA",
    "denver": "USA",
    "atlanta": "USA",
    "raleigh": "USA",
    "melbourne": "Australia",
    "auckland": "New Zealand",
    "lisbon": "Portugal",
    "kolkata": "India",
    "noida": "India",
    "gurgaon": "India",
    "hyderabad": "India",
    "bangkok": "Thailand",
    "kuala lumpur": "Malaysia",
    "jakarta": "Indonesia",
    "manila": "Philippines",
    "ho chi minh city": "Vietnam",
    "dubai": "UAE",
    "abu dhabi": "UAE",
    "doha": "Qatar",
    "riyadh": "Saudi Arabia",
    "cairo": "Egypt",
    "johannesburg": "South Africa",
    "capetown": "South Africa",
}

# Add some common countries
COMMON_COUNTRIES = [
    "USA", "United States", "US", "UK", "United Kingdom", "GB",
    "Germany", "France", "Spain", "Italy", "Canada", "Australia",
    "India", "China", "Japan", "Brazil", "Russia", "Mexico",
    "Sweden", "Norway", "Finland", "Denmark", "Netherlands", "Belgium",
    "Switzerland", "Austria", "Poland", "Ireland", "Portugal",
    "Singapore", "South Korea", "Taiwan", "Hong Kong", "UAE", "Qatar",
    "Saudi Arabia", "Egypt", "South Africa", "New Zealand", "Thailand",
    "Malaysia", "Indonesia", "Philippines", "Vietnam", "Ukraine",
    "Hungary", "Czech Republic", "Turkey", "Argentina", "Chile", "Colombia",
    "Pakistan", "Nigeria", "Kenya"
]

OWNER_CACHE = {}

def get_owner_data(owner_login):
    if owner_login in OWNER_CACHE:
        return OWNER_CACHE[owner_login]

    data = {"type": "Unknown", "location": None, "country": "Unknown"}

    # Try as a user
    user_url = f"{GITHUB_API_URL}/users/{owner_login}"
    try:
        response = requests.get(user_url, headers=HEADERS, timeout=5)
        if response.status_code == 200:
            user_data = response.json()
            data["type"] = "User"
            data["location"] = user_data.get("location")
            OWNER_CACHE[owner_login] = data
            time.sleep(0.1) # Be gentle with the API
            return data
        elif response.status_code == 404:
            # Not a user, try as an organization
            org_url = f"{GITHUB_API_URL}/orgs/{owner_login}"
            response = requests.get(org_url, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                org_data = response.json()
                data["type"] = "Organization"
                data["location"] = org_data.get("location")
                OWNER_CACHE[owner_login] = data
                time.sleep(0.1) # Be gentle with the API
                return data
            elif response.status_code == 403 and 'rate limit exceeded' in response.text:
                print("GitHub API rate limit exceeded. Please try again later or provide a GITHUB_TOKEN.")
                time.sleep(60) # Wait for a minute and retry
                return get_owner_data(owner_login) # Retry after waiting
        else:
            print(f"Error fetching data for {owner_login}: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Network error or timeout for {owner_login}: {e}")

    OWNER_CACHE[owner_login] = data # Cache even if unknown to avoid repeated requests
    return data

def infer_country_from_location(location):
    if not location:
        return "Unknown"

    loc_lower = location.lower().strip()

    # Direct country match
    for country in COMMON_COUNTRIES:
        if loc_lower == country.lower():
            return country

    # City to country mapping
    if loc_lower in CITY_TO_COUNTRY:
        return CITY_TO_COUNTRY[loc_lower]

    # Simple check for country names within the location string
    for country in COMMON_COUNTRIES:
        if country.lower() in loc_lower:
            return country
            
    return "Unknown"

def update_readme_table(readme_content):
    lines = readme_content.splitlines()
    updated_lines = []
    
    header_index = -1
    new_columns_present = False # Initialize here
    
    # Step 1: Find the table header and extract column names
    for i, line in enumerate(lines):
        if "| Ranking | Project Name |" in line:
            header_index = i
            break
            
    if header_index == -1:
        return readme_content # Table not found

    # Extract column names from the header line
    header_line = lines[header_index].strip()
    header_columns = [col.strip() for col in header_line.split('|') if col.strip()]

    # Check if "Owner Type" and "Country" are already present in the header
    new_columns_present = "Owner Type" in header_columns and "Country" in header_columns
    
    # Find insertion point for "Owner Type" and "Country"
    insert_at_idx = -1 # Initialize to a safe default
    
    try:
        open_issues_idx = header_columns.index("Open Issues")
        # description_idx = header_columns.index("Description") # Not directly used for insertion point anymore
        
        # Determine the insertion index based on whether columns are new or existing
        if not new_columns_present:
            insert_at_idx = open_issues_idx + 1 # Insert after Open Issues
        else:
            # If columns are present, find the index of "Owner Type"
            insert_at_idx = header_columns.index("Owner Type")
            
    except ValueError:
        print("Error: 'Open Issues' or 'Description' column not found in header. Cannot insert new columns.")
        return readme_content

    # Check if "Owner Type" and "Country" are already present in the header
    # This check needs to be done *after* potentially getting insert_at_idx for existing columns
    # because header_columns might contain them already.
    # Re-evaluate new_columns_present after all parsing
    new_columns_present = "Owner Type" in header_columns and "Country" in header_columns
    
    # Step 2: Reconstruct lines before the table
    updated_lines.extend(lines[:header_index])

    # Step 3: Construct new header and separator lines
    new_header_columns = list(header_columns) # Create a mutable copy
    if not new_columns_present:
        # Insert "Owner Type" and "Country" after "Open Issues"
        new_header_columns.insert(insert_at_idx, "Owner Type")
        new_header_columns.insert(insert_at_idx + 1, "Country")
    # If new_columns_present is true, new_header_columns already contains them in the right order
    # so no insertion is needed, just use new_header_columns as is.
    
    updated_header_line = "| " + " | ".join(new_header_columns) + " |"
    updated_lines.append(updated_header_line)

    # Construct the new separator line based on the new header
    separator_line = lines[header_index + 1].strip()
    separator_parts = [part.strip() for part in separator_line.split('|') if part.strip()]
    
    new_separator_parts = list(separator_parts)
    if not new_columns_present:
        new_separator_parts.insert(insert_at_idx, "----------")
        new_separator_parts.insert(insert_at_idx + 1, "-------")
    
    updated_separator_line = "| " + " | ".join(new_separator_parts) + " |"
    updated_lines.append(updated_separator_line)

    # Step 4: Process data rows
    data_rows_start_index = header_index + 2
    for i in range(data_rows_start_index, len(lines)):
        line = lines[i]
        if not line.strip().startswith('|'): # End of table data
            updated_lines.extend(lines[i:])
            break

        # Process data row
        match = re.search(r'\[.*?\]\((https://github.com/(.*?)/(.*?))\)', line)
        
        # Split the data line into columns
        current_data_columns = [col.strip() for col in line.split('|') if col.strip()]
        
        if match:
            owner_login = match.group(2)
            owner_info = get_owner_data(owner_login)
            owner_type = owner_info["type"]
            location = owner_info["location"]
            country = infer_country_from_location(location)

            # Insert or update Owner Type and Country values
            new_data_columns = list(current_data_columns)
            
            # Here, we need to ensure insert_at_idx is correct for data columns as well.
            # If new_columns_present was true, it means original header had them,
            # so data rows should also have them, and insert_at_idx is the index of Owner Type.
            # If not new_columns_present, then we insert at insert_at_idx.
            
            # This logic needs to consider the current state of the data row.
            # A clean way is to always build the data row from its current parsed content,
            # then insert/replace at the calculated insert_at_idx.
            
            # If the current data row already has the new columns, update them.
            # Otherwise, insert them. The `len(new_header_columns)` check is good.
            if len(new_data_columns) == len(new_header_columns):
                # Columns already exist, update them
                new_data_columns[insert_at_idx] = owner_type
                new_data_columns[insert_at_idx + 1] = country
            else:
                # Columns don't exist, insert them
                new_data_columns.insert(insert_at_idx, owner_type)
                new_data_columns.insert(insert_at_idx + 1, country)
            

            updated_data_line = "| " + " | ".join(new_data_columns) + " |"
            updated_lines.append(updated_data_line)
        else:
            # If no match or other issues, still reconstruct based on new column structure if applicable
            # Or just append the line as is if it's already in the new format
            # This also needs insert_at_idx to be robust
            
            # If the header changed, and this data row needs to conform to new header's column count
            if len(current_data_columns) < len(new_header_columns):
                # Insert empty placeholders to match the column count of the new header
                empty_fillers = [""] * (len(new_header_columns) - len(current_data_columns))
                new_data_columns = list(current_data_columns)
                new_data_columns.insert(insert_at_idx, empty_fillers[0])
                new_data_columns.insert(insert_at_idx + 1, empty_fillers[1])
                updated_lines.append("| " + " | ".join(new_data_columns) + " |")
            else:
                updated_lines.append(line) # Append original line


    return "\n".join(updated_lines)

def main():
    print(f"Reading {README_FILE}...")
    with open(README_FILE, "r", encoding="utf-8") as f:
        readme_content = f.read()

    print("Updating README table...")
    updated_content = update_readme_table(readme_content)

    print(f"Writing updated content to {README_FILE}...")
    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print("README.md updated successfully.")

if __name__ == "__main__":
    main()
