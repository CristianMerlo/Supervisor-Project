import requests
import re
from urllib.parse import urljoin

base_url = "https://appmostaza.linkuperp.com/"
print("[*] Fetching index.html")
html = requests.get(base_url).text

# Find all script src
scripts = re.findall(r'src="(js/[^"]+)"', html)
print(f"[*] Found {len(scripts)} scripts. Analyzing...")

api_client = None
api_client_secret = None
distributor_url = None

for script in scripts:
    script_url = urljoin(base_url, script)
    try:
        content = requests.get(script_url).text
        
        if "API_CLIENT_SECRET" in content or "DISTRIBUTOR_URL" in content:
            print(f"\n[+] Found potential variables in {script}")
            
            # Extract variables
            matches = re.findall(r'(var|const|let)\s+(API_CLIENT_SECRET|API_CLIENT|DISTRIBUTOR_URL|SERVER_URL|API_URL)\s*=\s*[\'"]([^\'"]+)[\'"]', content)
            for match in matches:
                var_type, var_name, var_value = match
                print(f"   => {var_name} = {var_value}")
                
            # Sometimes they are not strings but numbers or other objects
            matches_num = re.findall(r'(var|const|let)\s+(API_CLIENT_SECRET|API_CLIENT)\s*=\s*(\d+)', content)
            for match in matches_num:
                var_type, var_name, var_value = match
                print(f"   => {var_name} = {var_value}")
    except Exception as e:
        pass
