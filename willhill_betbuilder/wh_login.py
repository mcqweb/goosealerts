"""
William Hill Login and Session Management

This script handles:
1. Full login flow (when you have username/password)
2. Session refresh flow (when you have CASTGC cookie)

Usage:
  python wh_login.py login <username> <password>     # Full login
  python wh_login.py refresh                          # Refresh existing session

The script will save cookies to cookies/william_hill.txt (Netscape format)
and print the SESSION cookie to update in your .env file.
"""
import sys
from http.cookiejar import MozillaCookieJar
import os
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()
import cloudscraper


import requests

# ========= ENV / PATHS =========
NORD_USER = os.getenv("NORD_USER", "")
NORD_PWD = os.getenv("NORD_PWD", "")
NORD_LOCATION = os.getenv("NORD_LOCATION", "")

if NORD_USER and NORD_PWD and NORD_LOCATION:
    PROXIES = {
        'http': f'http://{NORD_USER}:{NORD_PWD}@{NORD_LOCATION}.nordvpn.com:89',
        'https': f'https://{NORD_USER}:{NORD_PWD}@{NORD_LOCATION}.nordvpn.com:89',
    }
else:
    PROXIES = {}


def full_login(username, password, proxies=None):
    print("=" * 60)
        
    # Step 1: Get login form with executionKey
    print("\n[1/3] Getting login form...")
    url1 = "https://auth.williamhill.com/cas/v3/login"
    
    headers1 = {
        "Accept": "application/json",
        "Accept-Language": "en-GB,en;q=0.9"
    }

    # Prefer curl_cffi if available, then tls_client, then cloudscraper
    session = None
    client_used = None
    try:
        from curl_cffi.requests import Session as CurlSession
        session = CurlSession(impersonate="chrome120")
        client_used = 'curl_cffi'
    except Exception:
        try:
            from tls_client import Session as TlsSession
            session = TlsSession(client_identifier="chrome_120")
            client_used = 'tls_client'
        except Exception:
            session = cloudscraper.create_scraper()
            client_used = 'cloudscraper'


    print(f"Using HTTP client: {client_used}")
    r1 = session.get(url1, headers=headers1, proxies=PROXIES)
    
    used_proxies = proxies if proxies is not None else PROXIES
    if not r1:
        r1 = session.get(url1, headers=headers1, proxies=used_proxies)
        return None
        
    try:
        print(f"Response status: {r1.status_code}")
        print(f"Content-Type: {r1.headers.get('Content-Type')}")
        
        print(f"\n=== Step 1 Full Response ===")
        form_data = r1.json()
        print(json.dumps(form_data, indent=2))
        
        execution_key = form_data['form_defaults']['executionKey']
        print(f"\n✓ Got execution key: {execution_key[:50]}...")
        
        # Extract any other flags that might be needed for step 2
        form_defaults = form_data.get('form_defaults', {})
        print(f"\n=== Form defaults for step 2 ===")
        for key, value in form_defaults.items():
            print(f"{key}: {value}")
        
    except json.JSONDecodeError as e:
        print(f"✗ Failed to parse JSON response: {e}")
        print(f"Response content: {r1.text[:500]}")
        return None
    except Exception as e:
        print(f"✗ Failed to get login form: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Step 2: Submit login credentials
    print("\n[2/3] Submitting credentials...")
    url2 = "https://auth.williamhill.com/cas/v3/login"
    
    headers2 = {
        "accept": "application/json",
        "accept-language": "ql",
        "content-type": "application/x-www-form-urlencoded",
        "priority": "u=1, i",
        "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "referer": "https://www.williamhill.com",
        "origin": "https://www.williamhill.com"
    }
    
    # Build payload using exact values from step 1 form_defaults
    payload = {
        "username": username,
        "password": password,
        "execution": execution_key,
        "rememberMe": False,
        "_rememberMe":"off",
        "_rememberUsername":"off"

    }
    
    # Add any other form defaults from step 1
    for key, value in form_defaults.items():
        if key not in ['executionKey', 'username', 'password']:
            payload[key] = value
    
    print(f"\n=== Payload ===")
    # Print payload without showing password
    payload_display = payload.copy()
    payload_display['password'] = '***'
    print(json.dumps(payload_display, indent=2))
    
   
    try:
        print(f"\n--- Sending as form data (data=) ---")
        # Manually encode payload to match browser (for booleans and on/off)
        from urllib.parse import urlencode
        encoded_payload = urlencode(payload)
        r2 = session.post(url2, data=encoded_payload, headers=headers2, proxies=used_proxies)
        print(f"\nResponse status: {r2.status_code}")
        print(f"Content-Type: {r2.headers.get('Content-Type')}")
        print(f"\n=== Response Headers ===")
        for header, value in r2.headers.items():
            print(f"{header}: {value}")
        
        print(f"\n=== Response Body ===")
        try:
            response_json = r2.json()
            print(json.dumps(response_json, indent=2))

            # Treat JSON {"success": true} as a successful login even if no ticket present
            service_ticket = None
            success_flag = bool(response_json.get('success') is True)
            if 'ticket' in response_json:
                service_ticket = response_json['ticket']
                print(f"\n✓ Got service ticket: {service_ticket}")
            else:
                if success_flag:
                    print("\n✓ Login returned success:true. Proceeding to step 3 to obtain ticket via redirect.")
                else:
                    print("\n⚠ Login Failed")
        except:
            print(f"Non-JSON response: {r2.text[:1000]}")
            service_ticket = None
 
        
        # Step 3: Call /cas/login?service=... to get redirected with service ticket
        print("\n[3/3] Calling /cas/login?service=... to get service ticket...")
        url3 = (
            "https://auth.williamhill.com/cas/login?service="
            "https%3A%2F%2Ftransact.williamhill.com%2Fbetslip%2Flogin%2Fcas%3Ftarget%3D%252Fbetslip%252Fapi%252Fbets%252Fslip%253Flang%253Den"
            "&gateway=true"
        )
        headers3 = {
            "Host": "auth.williamhill.com",
            "Accept": "*/*",
            "Accept-Language": "en-GB,en;q=0.9",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Ch-Ua": '"Not_A Brand";v="99", "Chromium";v="142"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Sec-Ch-Ua-Mobile": "?0",
            "Origin": "https://sports.williamhill.com",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://sports.williamhill.com/betting/en-gb/football/OB_EV38027661/reading-v-luton",
            "Accept-Encoding": "gzip, deflate, br",
            "Priority": "u=1, i"
        }
        try:
            # This call should follow redirects=False to capture the Location header
            r3 = session.get(url3, headers=headers3, proxies=PROXIES, allow_redirects=False)
            print(f"Response status: {r3.status_code}")
            print(f"Content-Type: {r3.headers.get('Content-Type')}")
            print(f"\n=== Response Headers ===")
            for header, value in r3.headers.items():
                print(f"{header}: {value}")
            # The service ticket is in the Location header as ...ticket=...
            location = r3.headers.get('Location')
            service_ticket = None
            if location and 'ticket=' in location:
                from urllib.parse import parse_qs, urlparse
                parsed = urlparse(location)
                qs = parse_qs(parsed.query)
                service_ticket = qs.get('ticket', [None])[0]
                print(f"\n✓ Got service ticket from redirect: {service_ticket}")
            else:
                print(f"✗ No service ticket found in redirect Location header")
            # Now, if we have a service ticket, call the transact endpoint to get SESSION
            if service_ticket:
                url4 = f"https://transact.williamhill.com/betslip/login/cas?target=%2Fbetslip%2Fapi%2Fbets%2Fslip%3Flang%3Den&ticket={service_ticket}"
                headers4 = {
                    "accept": "*/*",
                    "accept-language": "en-GB,en;q=0.9",
                    "referer": "https://sports.williamhill.com/betting/en-gb/football/OB_EV38027661/reading-v-luton",
                    "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-site"
                }
                r4 = session.get(url4, headers=headers4, proxies=PROXIES)
                print(f"\n=== Final SESSION exchange ===")
                print(f"Response status: {r4.status_code}")
                print(f"Content-Type: {r4.headers.get('Content-Type')}")
                print(f"\n=== Response Headers ===")
                for header, value in r4.headers.items():
                    print(f"{header}: {value}")
                print(f"\n=== Response Body (first 1000 chars) ===")
                print(r4.text[:1000])
                session_cookie = session.cookies.get('SESSION')
                if session_cookie:
                    print(f"\n{'=' * 60}")
                    print("✓ SUCCESS! Got SESSION cookie:")
                    print(f"{'=' * 60}")
                    print(f"{session_cookie}")
                    # Write SESSION to williamhill_session.txt for other scripts
                    try:
                        session_file = Path(__file__).resolve().parents[0] / 'williamhill_session.txt'
                        with open(session_file, 'w', encoding='utf-8') as sf:
                            sf.write(session_cookie)
                        print(f"✓ Wrote SESSION to {session_file}")
                    except Exception as e:
                        print(f"⚠ Failed to write session file: {e}")
                    print(f"\nUpdate your .env file with:")
                    print(f"WILLIAMHILL_SESSION={session_cookie}")
                    print(f"{'=' * 60}")
                else:
                    print(f"✗ No SESSION cookie returned after ticket exchange")
        except Exception as e:
            print(f"✗ Step 3 request failed: {e}")
            import traceback
            traceback.print_exc()
        # Return session for saving cookies, etc.
        return session
    except Exception as e:
        print(f"✗ Login request failed: {e}")
        import traceback
        traceback.print_exc()
        return session
        
def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python wh_login.py login <username> <password>")
        print("  python wh_login.py refresh")
        return
    
    command = sys.argv[1]
    
    
    if command == "login":
        if len(sys.argv) < 4:
            print("Usage: python wh_login.py login <username> <password>")
            return
        
        username = sys.argv[2]
        password = sys.argv[3]
        session = full_login(username, password)
    
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: login")

if __name__ == "__main__":
    main()
