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
    in_table = False
    header_found = False
    project_data = []

    # Find the table header and separator
    for i, line in enumerate(lines):
        if "| Ranking | Project Name |" in line and not header_found:
            # This is the header row
            updated_lines.append(line + " Owner Type | Country |")
            updated_lines.append(lines[i+1] + "---------- | ------- |") # Separator line
            header_found = True
            in_table = True
            continue
        if header_found and in_table and line.strip().startswith('|') and not line.strip().startswith('| ---'):
            # This is a data row
            project_data.append(line)
        elif in_table and not line.strip().startswith('|'):
            # End of the table
            in_table = False
            break
        if not header_found:
            updated_lines.append(line)

    # Process project data
    for row_line in project_data:
        match = re.search(r'\[.*?\]\((https://github.com/(.*?)/(.*?))\)', row_line)
        if match:
            owner_login = match.group(2)
            # print(f"Processing owner: {owner_login}")
            owner_info = get_owner_data(owner_login)
            owner_type = owner_info["type"]
            location = owner_info["location"]
            country = infer_country_from_location(location)

            # Insert new columns before the last column ('Description' or 'Last Commit' in the original structure)
            parts = [p.strip() for p in row_line.split('|')]
            # Original: | Ranking | Project Name | Stars | Forks | Language | Open Issues | Description | Last Commit |
            # New:      | Ranking | Project Name | Stars | Forks | Language | Open Issues | Owner Type | Country | Description | Last Commit |
            if len(parts) >= 9: # Check if all original columns are present
                # Reconstruct the line with new columns inserted
                updated_row_line = (
                    f"| {parts[1]} | {parts[2]} | {parts[3]} | {parts[4]} | {parts[5]} | {parts[6]} "
                    f"| {owner_type} | {country} | {parts[7]} | {parts[8]} |"
                )
                updated_lines.append(updated_row_line)
            else:
                updated_lines.append(row_line) # Fallback if parsing fails

        else:
            updated_lines.append(row_line) # Append original line if no match

    # Add the remaining lines after the table
    if in_table: # This means the loop finished while still in table (e.g., end of file)
        pass # Already processed `project_data`
    else:
        for j in range(i, len(lines)):
            updated_lines.append(lines[j])

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
