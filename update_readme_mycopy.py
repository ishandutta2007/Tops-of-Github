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
    
    header_start_index = -1
    table_rows_start_index = -1
    
    # Pass 1: Find table boundaries and check for existing columns
    for i, line in enumerate(lines):
        if "| Ranking | Project Name |" in line:
            header_start_index = i
            # Check if columns already exist
            if " Owner Type | Country |" in lines[header_start_index]:
                # Columns already present, no need to add, but still need to re-process data
                pass
            break
            
    if header_start_index == -1:
        # Table not found, return original content
        return readme_content

    # Assuming separator is right after header
    separator_line_index = header_start_index + 1
    table_rows_start_index = separator_line_index + 1

    # Reconstruct lines before the table
    updated_lines.extend(lines[:header_start_index])

    # Reconstruct header and separator
    current_header = lines[header_start_index]
    current_separator = lines[separator_line_index]
    
    if " Owner Type | Country |" not in current_header:
        updated_lines.append(current_header.strip() + " Owner Type | Country |")
        updated_lines.append(current_separator.strip() + "---------- | ------- |")
    else:
        # If headers already exist, append them as is.
        # This handles cases where the script might have been partially run or manually edited.
        updated_lines.append(current_header)
        updated_lines.append(current_separator)

    # Process table data rows
    for i in range(table_rows_start_index, len(lines)):
        line = lines[i]
        # Stop processing table data if we hit a line that doesn't look like a table row or separator
        if not line.strip().startswith('|') or line.strip().startswith('| ---'):
            # Append this line and all subsequent lines as they are outside the table
            updated_lines.extend(lines[i:])
            break

        # This is a data row
        match = re.search(r'\[.*?\]\((https://github.com/(.*?)/(.*?))\)', line)
        if match:
            owner_login = match.group(2)
            owner_info = get_owner_data(owner_login)
            owner_type = owner_info["type"]
            location = owner_info["location"]
            country = infer_country_from_location(location)

            # Split the line by '|'. This will give us parts like ['', ' val1 ', ' val2 ', ..., ' val8 ', '']
            original_parts = line.split('|')
            
            # We expect 11 parts for an original 8-column table row (empty + 8 data + empty)
            if len(original_parts) >= 9: # Checking for at least 8 data parts + leading empty
                # Construct the new line with inserted owner_type and country
                # | Ranking | Project Name | Stars | Forks | Language | Open Issues | Owner Type | Country | Description | Last Commit |
                new_row = (
                    f"{original_parts[0]}|{original_parts[1]}|{original_parts[2]}|{original_parts[3]}|"
                    f"{original_parts[4]}|{original_parts[5]}|{original_parts[6]}| {owner_type} | {country} |"
                    f"{original_parts[7]}|{original_parts[8]}|"
                )
                updated_lines.append(new_row)
            else:
                updated_lines.append(line) # Fallback if parsing fails or row is malformed
        else:
            updated_lines.append(line) # Append original line if no match or other issues
            
    # If the loop finished without hitting a break (i.e., table goes to end of file)
    # the remaining lines (which are part of the table) would have been processed
    # This block handles cases where lines after the table might exist and weren't appended by the break.
    if len(updated_lines) < len(lines):
        updated_lines.extend(lines[len(updated_lines):])

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
