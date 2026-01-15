"""
Script to fetch William Hill Rewards and Hidden Markets via GraphQL API
This mimics the fetch call to gql-cs.williamhill.com/graphql

SETUP INSTRUCTIONS:
1. Go to https://sports.williamhill.com/betting/en-gb/apps/promotions in your browser
2. Open DevTools (F12) > Network tab
3. Refresh the page
4. Find the graphql request to gql-cs.williamhill.com
5. Right-click > Copy > Copy as cURL
6. Extract all cookies and save them to cookies/william_hill.txt
   OR set them directly in this script below

Alternatively, you can copy all cookies from the request headers.
"""

import requests
import json
from pathlib import Path
import sys

# Add willhill_betbuilder to path
sys.path.insert(0, str(Path(__file__).parent / 'willhill_betbuilder'))
from config import Config

# Optional: Set cookies directly here if not using cookie file
# Paste the full cookie string from browser DevTools here:
COOKIE_STRING = 'cdb=true; _tgpc=9268a492-3545-5a7e-89e4-0316bc633480; s_ecid=MCMID%7C04089004732055721633330442838772380023; cust_lang=en-gb; sitePreference=DESKTOP; trk_curc=GBP; optimizelyEndUserId=oeu1749652225405r0.28641927068893314; __qca=P1-8707307e-ee0d-496e-839c-969d57b985fd; utag_main_device_has_previously_logged_in=Yes; _ga_RJT9VDG4HP=GS2.1.s1753694352$o26$g1$t1753694366$j46$l0$h0; IS_NEW_REG=false; _fbp=fb.1.1749649121848.921270806376011807.Bg; lastSiteVisited=https%3A%2F%2Fsports.williamhill.com; __adal_ca=so%3Dincomeaccess%26me%3Daffiliates%26ca%3D1428%26co%3D1488635%26ke%3D212425%26cg%3DUnknown; _rdt_uuid=1749649106904.8eb44340-7db4-4f10-b4b9-59c2b415dbde; banner_click=NA,NA,NA,NA,admap:d_direct%3Bsource:%3Bzone:%3Bchannel:; _ga_T118T6FPCG=GS2.1.s1765886036$o7$g1$t1765886113$j50$l0$h0; AMCV_279422CE52785BCE0A490D4D%40AdobeOrg=1099438348%7CMCIDTS%7C20440%7CMCMID%7C04089004732055721633330442838772380023%7CMCAID%7CNONE%7CMCOPTOUT-1765970516s%7CNONE%7CMCAAMLH-1766568116%7C6%7CMCAAMB-1766568116%7Cj8Odv6LonN4r3an7LhD3WZrU1bUpAkFkkiY1ncBR96t2PTI%7CvVersion%7C2.1.0%7CMCCIDH%7C-261330133; _tglksd=eyJzIjoiNjk4ZjY2Y2EtODUxNS00NzhiLWI5NDktOTQ2ODIxOTY3OTg5Iiwic3QiOjE3NjYwNDgxODg4MTgsInNvZCI6IihkaXJlY3QpIiwic29kdCI6MTc2NDc5MjIyOTMzNywic29kcyI6Im8iLCJzb2RzdCI6MTc2NTg4NjEwMDkzMH0=; __adal_id=1ddf1a75-225b-4e95-97a6-c5896a965ffc.1759317321.67.1766048189.1765963324.cfe13dc3-7e1a-4878-99da-0f6f45716397; CONSENTMGR=c1:1%7Cc2:1%7Cc3:0%7Cc4:1%7Cc5:1%7Cc6:1%7Cc7:1%7Cc8:1%7Cc9:1%7Cc10:1%7Cc11:1%7Cc12:1%7Cc13:1%7Cc14:1%7Cc15:1%7Cc16:0%7Cts:1766048968982%7Cconsent:true; utag_main_v_id=uk-wh019b30b8b11e0020350820cc7ea80507d003c07501328; _ga=GA1.1.687496970.1766048970; LPVID=Y4NTdhYTViMDk5ODc5OTRk; trk_uid=05180RG; optimizelySession=0; trk_jsoncookie=%7B%22serveGroup%22%3A42.64694653476988%2C%22currUrl%22%3A%22https%3A%2F%2Fsports.williamhill.com%2Fbetting%2Fen-gb%2Fapps%2Fpromotions%22%2C%22prevUrl%22%3A%22https%3A%2F%2Fsports.williamhill.com%2Fbetting%2Fen-gb%2Fapps%2Fpromotions%22%7D; utag_main__sn=13; utag_main_ses_id=1768481430070%3Bexp-session; ddl_landing_document_location=https://sports.williamhill.com/betting/en-gb/apps/promotions; landingURL=https%3A%2F%2Fsports.williamhill.com%2Fbetting%2Fen-gb%2Fapps%2Fpromotions; utag_main__ss=0%3Bexp-session; utag_main_dc_visit=12; LPSID-56599937=tcthDQwvTs2XwW4oO-h5cQ; CASLLD=2026-01-15T08:07:39; CountryCodeCookie=UK; cas_ssl_login=_FezRbFnk3F0lKq9Q_kuE_GN6KgyvhvR0ymaJBPzBcaAzq7E4N~4KEVWEYg0A4uoQb7EJFGzpx4ke1gEAG6g_LVwlfWbzjm1gvnHOjAT8UpMIsoVJvplT19VJpNP09Cl4y_a4tPsqdHob2lnnNPWAPYTzzGLKmrUJ~4ZxMO1_b~EtETkPqV0acdFegr9ej0aM7Sy4zYGCQ--; cas_login=AUPrY7Fo6k9nhTG4xSUeIYfaiM46lvhK/tz8IE07OzGrl9jUwafLD+Mb7OTtIjclan0wb4AgP/hUd/ogGqfX+ck89WyvRvGvbySdk8zTPjtxp1X0WL89wHhybPtk+eJ3RP0vAG8=; cas_ssl_cookie_samesite=AUPrY7Fo6k9nhTG4xSUeIYfaiM46lvhK/tz8IE07OzGrl9jUwafLD+Mb7OTtIjclan0wb4AgP/hUd/ogGqfX+ck89WyvRvGvbySdk8zTPjtxp1X0WL89wHhybPtk+eJ3RP0vAG8=; cust_auth=6d5f542b7a0ba0cb7c6d804dd2c9dcc42a3f85cbc169c71e02d020e0b1b037e3d1eb5ef0b96878906e7b79; utag_main_last_logged_in_user=05180RG; _ga_SXQLDGPPYN=GS2.1.s1768481468$o11$g0$t1768483222$j60$l0$h0; cust_prefs=en|ODDS|form|TYPE|PRICE|||0|SB|0|0||0|en|1|TIME|TYPE|0|1||0||0|0||TYPE||-|0.00; pv_count_session=5; utag_main_dc_event=6%3Bexp-session; _ga_H808RLB5WC=GS2.1.s1768481433$o16$g1$t1768483234$j48$l0$h0; utag_main__pn=3%3Bexp-session; utag_main__se=24%3Bexp-session; utag_main__st=1768485055791%3Bexp-session; TS01448769=01f024109a089067878e97fb30909ed912b00dabbf94468781b1ea372ceec08b5dc8a83d8053d2b6e302cb1fb7cca5c82ce9991a05; sc-session=SC-70142-Zpc6e6uAtqCXu5JebCLkoWIVp4WTsjltorP-vMVUGVY-ip-100-76-146-221.eu-west-1.compute.internal; TS014679d5=01a3ceedc4dfe7b9f7708d43a9b02b0971182257bae44ffe644f2eae6a8579f1090364b384d7964b4d622763a781cdf31e28273124; cust_login=9kb8V8ikjnIMWbMVIheuornToTFJCpEPF7qa6M7iE75NH/zHavrFWnySUbiaKrpFcxES+yPL+vKbFzf3b9WkBvRRP6MDEgpmZx40qjKa8Ka6JG2zaGTSKkwsCiTSdwF5oUuQgS5ZZuFssGD/aYtQdcaStgg9trnRbKNmxz19ktIk+z807O8S6v5rz152leRN8tFzz1o=; cust_ssl_login=6uIiE8ciSknH+PGUgKLvp87uiIvjm/SrPQ8xGPz2eR3nWXwWanLN84UpoGEbwm30d2L0DROUOD9CGZ5IOWkHGAtZTgusTkYfw/qD5Zek80Dq3BhuWtcQSRuo; cust_ssl_login_samesite=9kb8V8ikjnIMWbMVIheuornToTFJCpEPF7qa6M7iE75NH/zHavrFWnySUbiaKrpFcxES+yPL+vKbFzf3b9WkBvRRP6MDEgpmZx40qjKa8Ka6JG2zaGTSKkwsCiTSdwF5oUuQgS5ZZuFssGD/aYtQdcaStgg9trnRbKNmxz19ktIk+z807O8S6v5rz152leRN8tFzz1o=; CSRF_COOKIE=5075936dbe8435b06173; wh_device={"is_native":"false","device_os":"desktop","os_version":"","is_tablet":false}'

# Parse the cookie string into a dict
MANUAL_COOKIES = {}
if COOKIE_STRING:
    for cookie in COOKIE_STRING.split('; '):
        if '=' in cookie:
            name, value = cookie.split('=', 1)
            MANUAL_COOKIES[name] = value


class WHRewardsClient:
    """Client for William Hill Rewards GraphQL API"""
    
    GRAPHQL_URL = "https://gql-cs.williamhill.com/graphql"
    
    # GraphQL query from the fetch call - exact format with \n escape sequences
    REWARDS_QUERY = "query Rewards($params: PromotionsRewardsParams!) {\n  promotionsRewards(params: $params) {\n    id\n    type\n    title\n    description\n    amountRedeemed\n    minStake\n    maxStake\n    token {\n      id\n      type\n      title\n      value\n      startDate\n      expirationDate\n      awardedDate\n      percentageBoost\n      __typename\n    }\n    bet {\n      id\n      type\n      level\n      sport\n      title\n      singleOnly\n      winOnly\n      channels\n      birType\n      isByoRestricted\n      pdsEntry {\n        name\n        sportName\n        __typename\n      }\n      __typename\n    }\n    action {\n      ... on RewardActionPage {\n        type\n        url\n        __typename\n      }\n      ... on RewardActionAddToBetslip {\n        type\n        selectionId\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  hiddenMarkets(params: {langCode: \"en-gb\"}) {\n    id\n    name\n    status\n    startDateTime\n    expirationDate\n    markets {\n      id\n      name\n      status\n      description\n      selections {\n        id\n        currentPriceNum\n        currentPriceDen\n        regularPriceNum\n        regularPriceDen\n        name\n        status\n        resultType\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"
    
    def __init__(self, session_cookie: str = None):
        """
        Initialize the Rewards client
        
        Args:
            session_cookie: Optional session cookie. If not provided, will use Config.get_session_cookie()
        """
        self.session = requests.Session()
        
        # Get session cookie from config if not provided
        if session_cookie is None:
            session_cookie = Config.get_session_cookie()
        
        # Set up headers to match the fetch call
        self.session.headers.update({
            "accept": "*/*",
            "accept-language": "en-GB,en;q=0.9,en-US;q=0.8",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "vertical": "sportsbook",
            "referer": "https://sports.williamhill.com/betting/en-gb/apps/promotions"
        })
        
        # Set up cookies - include session if available
        # First add any manual cookies
        for name, value in MANUAL_COOKIES.items():
            self.session.cookies.set(name, value, domain='.williamhill.com')
        
        if session_cookie and session_cookie != "REDACTED":
            # Try to read the cookies file if it exists (from browser export)
            cookies_file = Path(__file__).parent / 'cookies' / 'william_hill.txt'
            if cookies_file.exists():
                try:
                    with open(cookies_file, 'r', encoding='utf-8') as f:
                        cookie_str = f.read().strip()
                        # Parse Netscape cookie format or simple key=value pairs
                        for line in cookie_str.split('\n'):
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            if '\t' in line:  # Netscape format
                                parts = line.split('\t')
                                if len(parts) >= 7:
                                    domain, _, path, secure, expiry, name, value = parts[:7]
                                    self.session.cookies.set(name, value, domain=domain, path=path)
                            elif '=' in line:  # Simple key=value format
                                name, value = line.split('=', 1)
                                self.session.cookies.set(name.strip(), value.strip(), domain='.williamhill.com')
                    print(f"[Cookie] Loaded {len(self.session.cookies)} cookies from {cookies_file}")
                except Exception as e:
                    print(f"[Cookie] Failed to load cookie file: {e}")
            
            # Parse session cookie - it might be in format "cookie_name=cookie_value"
            # or just the value
            if '=' in session_cookie:
                name, value = session_cookie.split('=', 1)
                self.session.cookies.set(name, value, domain='.williamhill.com')
            else:
                # Common WH session cookie name
                self.session.cookies.set('WHSESSION', session_cookie, domain='.williamhill.com')
        
        # Set up proxies if configured
        proxies = Config.get_proxies()
        if proxies:
            self.session.proxies.update(proxies)
    
    def save_cookies(self, filepath: Path = None):
        """
        Save current session cookies to file
        
        Args:
            filepath: Path to save cookies. Defaults to cookies/william_hill.txt
        """
        if filepath is None:
            filepath = Path(__file__).parent / 'cookies' / 'william_hill.txt'
        
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Save cookies in simple key=value format
        with open(filepath, 'w', encoding='utf-8') as f:
            for cookie in self.session.cookies:
                f.write(f"{cookie.name}={cookie.value}\n")
        
        print(f"[Cookie] Saved {len(self.session.cookies)} cookies to {filepath}")
    
    def get_rewards(self, lang_code: str = "en-gb") -> dict:
        """
        Fetch rewards and hidden markets
        
        Args:
            lang_code: Language code (default: "en-gb")
            
        Returns:
            Dict containing rewards and hidden markets data
        """
        # Prepare the GraphQL request payload
        payload = {
            "operationName": "Rewards",
            "variables": {
                "params": {
                    "langCode": lang_code
                }
            },
            "query": self.REWARDS_QUERY
        }
        
        print(f"[GraphQL] Making request to: {self.GRAPHQL_URL}")
        print(f"[GraphQL] Variables: {payload['variables']}")
        print(f"[GraphQL] Cookies: {dict(self.session.cookies)}")
        print(f"[GraphQL] Headers: {dict(self.session.headers)}")
        
        try:
            response = self.session.post(
                self.GRAPHQL_URL,
                json=payload,
                timeout=30
            )
            
            print(f"[GraphQL] Response status: {response.status_code}")
            
            # Check if any cookies were updated
            response_cookies = response.cookies
            if response_cookies:
                print(f"[Cookie] Response updated {len(response_cookies)} cookie(s)")
                for cookie in response_cookies:
                    print(f"  - {cookie.name}")
            
            response.raise_for_status()
            
            data = response.json()
            
            # Check for GraphQL errors
            if 'errors' in data:
                print(f"[GraphQL] Errors in response: {json.dumps(data['errors'], indent=2)}")
            
            return data
            
        except requests.RequestException as e:
            print(f"[GraphQL] Request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[GraphQL] Response body: {e.response.text[:1000]}")
            raise
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def parse_cookie_string(cookie_str: str) -> dict:
    """
    Parse a cookie string from browser DevTools
    
    Args:
        cookie_str: Cookie string in format "name1=value1; name2=value2; ..."
        
    Returns:
        Dict of cookie name-value pairs
    """
    cookies = {}
    for cookie in cookie_str.split(';'):
        cookie = cookie.strip()
        if '=' in cookie:
            name, value = cookie.split('=', 1)
            cookies[name.strip()] = value.strip()
    return cookies


def filter_football_boosts(rewards_data: dict) -> list:
    """
    Filter rewards for football matches with 25% boost
    
    Args:
        rewards_data: The full GraphQL response data
        
    Returns:
        List of filtered rewards with minimal details (fixture, bet_id)
    """
    football_boosts = []
    
    if 'data' in rewards_data and 'promotionsRewards' in rewards_data['data']:
        for reward in rewards_data['data']['promotionsRewards']:
            # Check if it's a football match with 25% boost
            token = reward.get('token', {})
            bet = reward.get('bet', {})
            
            if (token.get('percentageBoost') == 25 and 
                bet.get('sport') == 'Football'):
                
                football_boosts.append({
                    'fixture': bet.get('title', ''),
                    'bet_id': bet.get('id', ''),
                    'boost_percent': token.get('percentageBoost'),
                    'expiration': token.get('expirationDate'),
                    'max_stake': reward.get('maxStake', '')
                })
    
    return football_boosts


def main():
    """Main function to fetch and filter football boost rewards"""
    try:
        # Create client and fetch rewards
        with WHRewardsClient() as client:
            print("[INFO] Fetching William Hill rewards...")
            data = client.get_rewards()
            
            # Save updated cookies after successful request
            client.save_cookies()
            
            # Filter for football 25% boosts
            football_boosts = filter_football_boosts(data)
            
            # Save to JSON file
            output_file = Path(__file__).parent / 'wh_football_boosts.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(football_boosts, f, indent=2)
            
            print(f"\n[SUCCESS] Found {len(football_boosts)} football boost(s)")
            print(f"[OUTPUT] Saved to: {output_file}")
            
            if football_boosts:
                print("\n[BOOSTS]")
                for boost in football_boosts:
                    print(f"  - {boost['fixture']} (ID: {boost['bet_id']})")
            
            return football_boosts
            
    except Exception as e:
        print(f"[ERROR] Failed to fetch rewards: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()


def main():
    """Main execution"""
    print("=" * 60)
    print("William Hill Rewards & Hidden Markets Fetcher")
    print("=" * 60)
    
    # Check if user wants to paste cookies
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--paste-cookies':
        print("\nPaste the cookie string from browser DevTools (from Request Headers):")
        print("(Press Enter twice when done)\n")
        lines = []
        while True:
            try:
                line = input()
                if not line:
                    break
                lines.append(line)
            except EOFError:
                break
        
        cookie_str = ' '.join(lines)
        cookies = parse_cookie_string(cookie_str)
        
        print(f"\nParsed {len(cookies)} cookies:")
        for name in list(cookies.keys())[:5]:  # Show first 5
            print(f"  - {name}")
        
        # Save to manual cookies in a new file
        output_file = Path(__file__).parent / "wh_cookies_parsed.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2)
        print(f"\nSaved to: {output_file}")
        print("\nYou can now copy these to MANUAL_COOKIES in the script or use them directly.")
        return
    
    # Create client
    with WHRewardsClient() as client:
        # Fetch rewards
        result = client.get_rewards()
        
        # Display results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        
        if 'data' in result:
            data = result['data']
            
            # Show rewards
            if 'promotionsRewards' in data and data['promotionsRewards'] is not None:
                rewards = data['promotionsRewards']
                print(f"\nPromotions/Rewards: {len(rewards)} found")
                for i, reward in enumerate(rewards, 1):
                    print(f"\n  {i}. {reward.get('title', 'Untitled')}")
                    print(f"     Type: {reward.get('type')}")
                    print(f"     Description: {reward.get('description', 'N/A')[:100]}...")
                    if reward.get('token'):
                        token = reward['token']
                        print(f"     Token: {token.get('title')} - Value: {token.get('value')}")
            else:
                print("\nNo promotionsRewards in response")
            
            # Show hidden markets
            if 'hiddenMarkets' in data and data['hiddenMarkets'] is not None:
                markets = data['hiddenMarkets']
                print(f"\n\nHidden Markets: {len(markets)} found")
                for i, market in enumerate(markets, 1):
                    print(f"\n  {i}. {market.get('name', 'Untitled')}")
                    print(f"     ID: {market.get('id')}")
                    print(f"     Status: {market.get('status')}")
                    print(f"     Markets: {len(market.get('markets', []))}")
                    
                    # Show selections from first market
                    if market.get('markets'):
                        first_market = market['markets'][0]
                        print(f"     First Market: {first_market.get('name')}")
                        selections = first_market.get('selections', [])
                        print(f"     Selections: {len(selections)}")
                        for sel in selections[:3]:  # Show first 3
                            price = f"{sel.get('currentPriceNum')}/{sel.get('currentPriceDen')}"
                            print(f"       - {sel.get('name')}: {price}")
            else:
                print("\nNo hiddenMarkets in response")
        
        # Save full response to file
        output_file = Path(__file__).parent / "wh_rewards_response.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n\nFull response saved to: {output_file}")
        print("=" * 60)


if __name__ == "__main__":
    main()
