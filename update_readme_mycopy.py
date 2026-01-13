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
    in_table_section = False
    header_line_index = -1
    separator_line_index = -1

    for i, line in enumerate(lines):
        if "| Ranking | Project Name |" in line:
            header_line_index = i
            # Check if Owner Type column already exists
            if " Owner Type | Country |" not in line:
                updated_lines.append(line + " Owner Type | Country |")
                separator_line_index = i + 1
                # Assuming the separator line is always directly after the header
                updated_lines.append(lines[separator_line_index] + "---------- | ------- |")
            else:
                updated_lines.append(line)
                updated_lines.append(lines[i+1]) # Append existing separator
            
            in_table_section = True
            continue
        
        if in_table_section and i == separator_line_index: # Skip the original separator as we've handled it
            continue

        if in_table_section and line.strip().startswith('|') and not line.strip().startswith('| ---'):
            # This is a data row
            match = re.search(r'\[.*?\]\((https://github.com/(.*?)/(.*?))\)', line)
            if match:
                owner_login = match.group(2)
                owner_info = get_owner_data(owner_login)
                owner_type = owner_info["type"]
                location = owner_info["location"]
                country = infer_country_from_location(location)

                parts = [p.strip() for p in line.split('|')]
                # Ensure parts list has enough elements for the original columns + new ones if already added
                # If the Owner Type/Country columns were already added, we need to locate them
                # For simplicity, let's always assume we are inserting before 'Description' (index 7 if starting from 1)
                
                # Filter out empty strings from parts from the split
                filtered_parts = [p.strip() for p in line.split('|') if p.strip()]

                # The original structure has 8 data columns (index 0 to 7 after filtering and 0-indexing)
                # If we've already added the columns, there will be more than 8
                # We need to find the correct insertion point
                
                # Reconstruct the line with new columns inserted (assuming original structure)
                # | Ranking | Project Name | Stars | Forks | Language | Open Issues | Description | Last Commit |
                # Filtered parts will be: [Ranking, Project Name, Stars, Forks, Language, Open Issues, Description, Last Commit]
                # Insert Owner Type and Country after Open Issues (index 5) and before Description (index 6)
                
                # Check if the row already contains "Owner Type" to prevent re-insertion
                if "Owner Type" not in parts: # Crude check, assuming "Owner Type" won't be in other fields
                    new_parts = filtered_parts[:6] + [owner_type, country] + filtered_parts[6:]
                else: # Columns already exist, update the values if needed or just keep
                    # This case is tricky if we want to update existing. For now, assume a fresh insert is better.
                    # If columns already exist, we should reconstruct based on existing structure.
                    # This means we need to find the indexes of "Owner Type" and "Country"
                    # For a robust solution, one would parse the header to get column indices.
                    # For now, if the header already has 'Owner Type', assume the data row also has it and it's correct.
                    # We would need to update the existing data in the specific cells if we went this route.
                    # Given the current simple append, if it already exists, the problem is in the header, not here.
                    
                    # For now, if the header already contained "Owner Type", we just append the original line
                    # without re-processing, to prevent duplicate columns in the data rows.
                    updated_lines.append(line)
                    continue

                updated_row_line = "| " + " | ".join(new_parts) + " |"
                updated_lines.append(updated_row_line)
            else:
                updated_lines.append(line) # Append original line if no match or other issues
        elif in_table_section and not line.strip().startswith('|'):
            # End of the table
            in_table_section = False
            updated_lines.append(line)
        elif not in_table_section:
            updated_lines.append(line)

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
