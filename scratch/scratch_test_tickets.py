import requests
import json

# 1. Login
url_login = "https://opgroup.linkuperp.com/apiv2/Oauth/token"
payload = {
    "grant_type": "password",
    "client_id": "4",
    "client_secret": "lXsUsNd9NXldzNENiUTNC2uLSQMhc3kI4CjhimJn",
    "username": "cmerlo@mostazaweb.com.ar",
    "password": "cmer654321",
    "device_os": "android",
    "app_version": "7.0.5"
}

res_login = requests.post(url_login, json=payload)
if res_login.status_code == 200:
    token = res_login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Get tickets for channel 2 (Franquicias)
    res_tickets = requests.get("https://opgroup.linkuperp.com/apiv2/tickets/channel/2", headers=headers)
    
    if res_tickets.status_code == 200:
        with open("/home/cristian/PROYECTOS/Supervisor-Project/scratch/tickets_channel2.json", "w") as f:
            json.dump(res_tickets.json(), f, indent=2)
        print("[+] Saved tickets_channel2.json")
    else:
        print("[-] Failed to get tickets:", res_tickets.status_code, res_tickets.text)
