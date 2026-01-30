"""
AccaFreeze - Monitor First Team To Score markets for arbitrage opportunities.

Fetches matches from oddsmatcha accafreeze API and checks Sky Bet odds on OddsChecker
for profitable backing opportunities against exchange lay prices.
"""

import json
import requests
import time
import cloudscraper
import os
from datetime import datetime, timezone, timedelta

# Load configuration
def load_config():
    """Load configuration from accafreeze.json"""
    try:
        with open('accafreeze.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("[ERROR] accafreeze.json not found. Creating default config...")
        default_config = {
            "sites": [
                {
                    "name": "Main Channel",
                    "channel_id": "YOUR_CHANNEL_ID_HERE",
                    "discord_token": "YOUR_BOT_TOKEN_HERE",
                    "enabled": True,
                    "min_lay_odds": 1.5,
                    "hours_to_ko": 24,
                    "min_back_odds": 1.8,
                    "min_rating": 105
                }
            ]
        }
        with open('accafreeze.json', 'w') as f:
            json.dump(default_config, f, indent=2)
        return default_config
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse accafreeze.json: {e}")
        return None

def load_seen_matches():
    """Load seen matches from tracking file"""
    seen_file = 'accafreeze_seen.json'
    if not os.path.exists(seen_file):
        return {}
    
    try:
        with open(seen_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_seen_matches(seen_matches):
    """Save seen matches to tracking file"""
    seen_file = 'accafreeze_seen.json'
    try:
        with open(seen_file, 'w') as f:
            json.dump(seen_matches, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save seen matches: {e}")

def is_match_seen(match_id, outcome_name, channel_id, seen_matches):
    """Check if match + outcome combination has been alerted to specific channel"""
    key = f"{match_id}_{outcome_name}_{channel_id}"
    return key in seen_matches

def mark_match_seen(match_id, outcome_name, channel_id, rating, seen_matches):
    """Mark match + outcome as seen for specific channel with timestamp and rating"""
    key = f"{match_id}_{outcome_name}_{channel_id}"
    seen_matches[key] = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'match_id': match_id,
        'outcome': outcome_name,
        'channel_id': channel_id,
        'rating': rating
    }
    save_seen_matches(seen_matches)

def get_previous_rating(match_id, outcome_name, channel_id, seen_matches):
    """Get previously saved rating for this match + outcome + channel"""
    key = f"{match_id}_{outcome_name}_{channel_id}"
    if key in seen_matches:
        return seen_matches[key].get('rating', 0)
    return 0

def fetch_accafreeze_data():
    """Fetch data from oddsmatcha accafreeze API"""
    api_url = "https://api.oddsmatcha.uk/accafreeze/"
    
    try:
        print(f"[API] Fetching accafreeze data from {api_url}")
        response = requests.get(api_url, timeout=30)
        
        if response.status_code != 200:
            print(f"[ERROR] API returned status {response.status_code}")
            return None
        
        data = response.json()
        print(f"[API] Fetched {data.get('total_matches', 0)} matches")
        return data
    
    except Exception as e:
        print(f"[ERROR] Failed to fetch accafreeze data: {e}")
        return None

def filter_matches(data, max_hours_to_ko):
    """
    Filter matches based on time window and lay odds threshold.
    Returns list of all matches within time window with outcomes meeting ANY site's min_lay_odds.
    """
    if not data:
        return []
    
    now = datetime.now(timezone.utc)
    qualifying = []
    
    for match in data.get('matches', []):
        # Parse kickoff time
        kickoff_str = match.get('kick_off')
        if not kickoff_str:
            continue
        
        try:
            kickoff = datetime.fromisoformat(kickoff_str.replace('Z', '+00:00'))
            if kickoff.tzinfo is None:
                kickoff = kickoff.replace(tzinfo=timezone.utc)
            
            # Check if within time window
            hours_until_ko = (kickoff - now).total_seconds() / 3600
            if hours_until_ko < 0 or hours_until_ko > max_hours_to_ko:
                continue
            
            # Check outcomes
            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')
            
            for outcome in match.get('outcomes', []):
                outcome_name = outcome.get('outcome_name', '')
                
                # Skip "no-goal" outcomes
                if outcome_name.lower() == 'no-goal':
                    continue
                
                lay_odds = outcome.get('lay_odds', 0)
                
                # Include all outcomes - will filter per-site later
                if lay_odds > 0:
                    qualifying.append({
                        'match': match,
                        'outcome': outcome,
                        'hours_until_ko': hours_until_ko,
                        'is_home': outcome_name.lower() in home_team.lower() or home_team.lower() in outcome_name.lower()
                    })
        
        except Exception as e:
            print(f"[WARN] Error processing match {match.get('match_id')}: {e}")
            continue
    
    return qualifying

def get_oddschecker_subevent_id(oddschecker_slug):
    """
    Extract the subevent ID from oddschecker slug by fetching the page.
    We need the numeric subevent ID to use with the mobile API.
    Uses tls_client to avoid 403 errors.
    """
    try:
        import tls_client
        
        # Create session with browser fingerprint
        session = tls_client.Session(
            client_identifier="chrome120",
            random_tls_extension_order=True
        )
        
        url = f'https://www.oddschecker.com/football/{oddschecker_slug}/winner'
        
        # Use same headers as oc.py
        headers = {
            'authority': 'www.oddschecker.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://www.oddschecker.com/football',
            'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
        }
        
        cookies = {
            'odds_type': 'decimal',
            'device': 'desktop',
            'logged_in': 'false',
            'mobile_redirect': 'true',
        }
        
        print(f"[OC] Fetching page to extract subevent ID: {url}")
        response = session.get(url, headers=headers, cookies=cookies)
        
        if response.status_code != 200:
            print(f"[ERROR] HTTP {response.status_code} fetching page")
            return None
        
        # Look for subevent ID in the HTML (it's in various data attributes and meta tags)
        import re
        # Pattern to find subeventId in script tags or data attributes
        patterns = [
            r'"subeventId["\s:]+(\d+)',
            r'subevent[/-](\d+)',
            r'data-subevent-id="(\d+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                subevent_id = match.group(1)
                print(f"[OC] Found subevent ID: {subevent_id}")
                return subevent_id
        
        print(f"[WARN] Could not find subevent ID in page")
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to extract subevent ID: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_skybet_odds_for_match(oddschecker_slug, oddschecker_match_id=None, debug=False):
    """
    Get Sky Bet odds from OddsChecker mobile API.
    Uses the mobile API endpoint for cleaner, faster access.
    
    Args:
        oddschecker_slug: Slug for logging/debugging only
        oddschecker_match_id: Numeric oddschecker ID (if None, will try to extract from page)
    
    Returns dict of {outcome_name: odds} for Sky Bet only.
    """
    try:
        # If we don't have the ID, extract it from the page
        if not oddschecker_match_id:
            oddschecker_match_id = get_oddschecker_subevent_id(oddschecker_slug)
            if not oddschecker_match_id:
                return {}
        
        # Use mobile API to get odds
        scraper = cloudscraper.create_scraper()
        
        # Mobile API headers (from B365 implementation)
        headers = {
            'Content-Type': 'application/json',
            'App-Type': 'mapp',
            'Accept': 'application/json',
            'Userbookmakers': 'SK',  # Only Sky Bet for faster results
            'Device-Id': '32568159-9874-6184-B9E0-A21CADB4EB84',
            'Api-Key': 'a1d4634b-6cd8-4485-a7cd-c9b91f38177f',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'Oddschecker/28716 CFNetwork/3826.500.111.2.2 Darwin/24.4.0',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }
        
        # Add cache buster
        import random
        cache_buster = int(time.time() * 1000) + random.randint(1, 999)
        api_url = f'https://api.oddschecker.com/api/mobile-app/football/v1/subevent/{oddschecker_match_id}?t={cache_buster}'
        
        print(f"[OC] Fetching from mobile API: {api_url}")
        response = scraper.get(api_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"[ERROR] Mobile API returned status {response.status_code}")
            return {}
        
        api_data = response.json()
        
        # Save mobile API response for debugging (only if debug enabled)
        if debug:
            timestamp = datetime.now().strftime("%H%M%S")
            debug_file = f'accafreeze_mobile_api_{oddschecker_match_id}_{timestamp}.json'
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(api_data, f, indent=2)
                print(f"[DEBUG] Saved mobile API response to {debug_file}")
            except Exception as e:
                print(f"[WARN] Failed to save debug file: {e}")
            
            # Also save a latest copy for easy access
            try:
                with open('accafreeze_mobile_api_latest.json', 'w', encoding='utf-8') as f:
                    json.dump(api_data, f, indent=2)
                print(f"[DEBUG] Saved to accafreeze_mobile_api_latest.json")
            except Exception as e:
                print(f"[WARN] Failed to save latest file: {e}")
        
        # Extract Sky Bet odds from mobile API response
        skybet_odds = {}
        
        markets = api_data.get('markets', [])
        for market in markets:
            market_name = market.get('marketName', '').lower()
            market_type = market.get('marketType', 0)
            
            # Look for Winner/Full Time Result market (marketType 1)
            if market_type == 1 and ('winner' in market_name or 'match result' in market_name):
                print(f"[OC] Processing Winner market: {market.get('marketName')}")
                
                bets = market.get('bets', [])
                for bet in bets:
                    bet_name = bet.get('betName', '')
                    odds_list = bet.get('odds', [])
                    
                    for odds_item in odds_list:
                        if odds_item.get('bookieCode') == 'SK':  # Sky Bet
                            odds_decimal = odds_item.get('oddsDecimal', '')
                            
                            if odds_decimal:
                                try:
                                    skybet_odds[bet_name] = float(odds_decimal)
                                    print(f"[OC] Sky Bet: {bet_name} @ {odds_decimal}")
                                except (ValueError, TypeError):
                                    pass
        
        print(f"[OC] Found {len(skybet_odds)} Sky Bet outcomes")
        return skybet_odds
    
    except Exception as e:
        print(f"[ERROR] Failed to get Sky Bet odds: {e}")
        import traceback
        traceback.print_exc()
        return {}

def match_team_names(exchange_name, oddschecker_names, home_team, away_team):
    """
    Match team name from exchange to oddschecker outcome.
    Returns the matching oddschecker outcome name or None.
    """
    exchange_lower = exchange_name.lower()
    home_lower = home_team.lower()
    away_lower = away_team.lower()
    
    # Direct match
    for oc_name in oddschecker_names:
        if oc_name.lower() == exchange_lower:
            return oc_name
    
    # Check if exchange name contains home or away team
    is_home = home_lower in exchange_lower or exchange_lower in home_lower
    is_away = away_lower in exchange_lower or exchange_lower in away_lower
    
    # Try to match with oddschecker names
    for oc_name in oddschecker_names:
        oc_lower = oc_name.lower()
        
        if is_home and (home_lower in oc_lower or oc_lower in home_lower):
            return oc_name
        if is_away and (away_lower in oc_lower or oc_lower in away_lower):
            return oc_name
    
    return None

def calculate_rating(back_odds, lay_odds):
    """Calculate rating as percentage (back/lay * 100)"""
    if lay_odds <= 0:
        return 0
    return (back_odds / lay_odds) * 100

def send_discord_alert(opportunity, sites, is_realert=False):
    """Send alert to all configured Discord channels"""
    if not sites:
        print("[DISCORD] No sites configured")
        return False
    
    # Build embed
    title_prefix = "🔄 " if is_realert else ""
    embed = {
        "title": f"{title_prefix}{opportunity['outcome']} ({opportunity['rating']:.0f}%)",
        "description": f"**{opportunity['home_team']} v {opportunity['away_team']}**\n{opportunity['competition']}\n{opportunity['kickoff_display']}",
        "color": 0xFFFFFF,  # White
        "fields": [
            {
                "name": "Back (Winner)",
                "value": f"**{opportunity['back_odds']}**",
                "inline": True
            },
            {
                "name": f"Lay (First Team to Score)",
                "value": f"**{opportunity['lay_odds']}**",
                "inline": True
            }
        ],
        "footer": {
            "text": "Option for AccaFreeze Leg"
        }
    }
    
    payload = {
        "embeds": [embed]
    }
    
    success_count = 0
    
    for site in sites:
        if not site.get('enabled', True):
            print(f"[DISCORD] Skipping disabled site: {site.get('name', 'Unknown')}")
            continue
        
        channel_id = site.get('channel_id')
        token = site.get('discord_token')
        
        if not channel_id or not token:
            print(f"[DISCORD] Missing channel_id or token for site: {site.get('name', 'Unknown')}")
            continue
        
        if channel_id == "YOUR_CHANNEL_ID_HERE" or token == "YOUR_BOT_TOKEN_HERE":
            print(f"[DISCORD] Skipping unconfigured site: {site.get('name', 'Unknown')}")
            continue
        
        try:
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 204]:
                print(f"[DISCORD] ✅ Sent to {site.get('name', 'Unknown')}")
                success_count += 1
            else:
                print(f"[DISCORD] ❌ Failed to send to {site.get('name', 'Unknown')}: {response.status_code} {response.text}")
        
        except Exception as e:
            print(f"[DISCORD] ❌ Error sending to {site.get('name', 'Unknown')}: {e}")
    
    return success_count > 0

def check_opportunities(qualifying, sites, seen_matches, debug=False):
    """
    Check each qualifying match on OddsChecker and report opportunities.
    Returns opportunities with list of sites they qualify for.
    Skips matches that have already been sent.
    """
    opportunities = []
    
    for item in qualifying:
        match = item['match']
        outcome = item['outcome']
        
        match_id = match.get('match_id')
        home_team = match.get('home_team', '')
        away_team = match.get('away_team', '')
        competition = match.get('competition', '')
        oddschecker_slug = match.get('oddschecker_slug', '')
        oddschecker_match_id = match.get('oddschecker_match_id')  # Get numeric ID if available
        outcome_name = outcome.get('outcome_name', '')
        lay_odds = outcome.get('lay_odds', 0)
        lay_site = outcome.get('lay_site', '')
        lay_liquidity = outcome.get('lay_liquidity', 0)
        hours_until_ko = item.get('hours_until_ko', 0)
        
        if not oddschecker_slug:
            print(f"[SKIP] No oddschecker slug for match {match_id}")
            continue
        
        print(f"\n{'='*80}")
        print(f"[MATCH] {home_team} v {away_team}")
        print(f"[INFO] {competition} | KO in {hours_until_ko:.1f}h")
        print(f"[EXCHANGE] {outcome_name} @ {lay_odds} on {lay_site} (£{lay_liquidity})")
        
        # Get Sky Bet odds (pass numeric ID if available to skip page fetch)
        skybet_odds = get_skybet_odds_for_match(oddschecker_slug, oddschecker_match_id, debug)
        
        if not skybet_odds:
            print(f"[SKIP] No Sky Bet odds available")
            continue
        
        # Match the outcome name
        matched_name = match_team_names(outcome_name, skybet_odds.keys(), home_team, away_team)
        
        if not matched_name:
            print(f"[WARN] Could not match '{outcome_name}' to Sky Bet outcomes: {list(skybet_odds.keys())}")
            continue
        
        back_odds = skybet_odds[matched_name]
        print(f"[SKYBET] {matched_name} @ {back_odds}")
        
        rating = calculate_rating(back_odds, lay_odds)
        print(f"[RATING] {rating:.2f}%")
        
        # Check which sites this qualifies for
        qualifying_sites = []
        realert_sites = []
        
        for site in sites:
            if not site.get('enabled', True):
                continue
            
            channel_id = site.get('channel_id')
            already_seen = is_match_seen(match_id, outcome_name, channel_id, seen_matches)
            
            # Check site-specific thresholds
            site_min_lay = site.get('min_lay_odds', 1.5)
            site_min_back = site.get('min_back_odds', 1.8)
            site_min_rating = site.get('min_rating', 105)
            site_max_hours = site.get('hours_to_ko', 24)
            
            # Check if meets this site's criteria
            meets_criteria = (lay_odds >= site_min_lay and 
                            back_odds >= site_min_back and 
                            rating >= site_min_rating and
                            hours_until_ko <= site_max_hours)
            
            if not meets_criteria:
                if not already_seen:
                    reasons = []
                    if lay_odds < site_min_lay:
                        reasons.append(f"lay {lay_odds} < {site_min_lay}")
                    if back_odds < site_min_back:
                        reasons.append(f"back {back_odds} < {site_min_back}")
                    if rating < site_min_rating:
                        reasons.append(f"rating {rating:.2f}% < {site_min_rating}%")
                    if hours_until_ko > site_max_hours:
                        reasons.append(f"hours {hours_until_ko:.1f} > {site_max_hours}")
                    print(f"[SITE] ❌ Doesn't qualify for: {site.get('name', 'Unknown')} ({', '.join(reasons)})")
                continue
            
            # Meets criteria - check if new alert or re-alert
            if already_seen:
                # Check if re-alerts enabled and rating increased enough
                if site.get('send_realerts', False):
                    previous_rating = get_previous_rating(match_id, outcome_name, channel_id, seen_matches)
                    required_increase = site.get('realert_rating_increase', 5)
                    rating_increase = rating - previous_rating
                    
                    if rating_increase >= required_increase:
                        realert_sites.append(site)
                        print(f"[SITE] 🔄 Re-alert for: {site.get('name', 'Unknown')} (rating increased {rating_increase:.2f}% from {previous_rating:.2f}% to {rating:.2f}%)")
                    else:
                        print(f"[SITE] ⏭️  Already sent to: {site.get('name', 'Unknown')} (rating increase {rating_increase:.2f}% < {required_increase}%)")
                else:
                    print(f"[SITE] ⏭️  Already sent to: {site.get('name', 'Unknown')} (re-alerts disabled)")
            else:
                # New alert
                qualifying_sites.append(site)
                print(f"[SITE] ✅ Qualifies for: {site.get('name', 'Unknown')} (rating {rating:.2f}% >= {site_min_rating}%)")
        
        if not qualifying_sites and not realert_sites:
            print(f"[SKIP] Doesn't meet criteria for any enabled site")
            continue
        
        # Format kickoff time for display
        now = datetime.now(timezone.utc)
        kickoff_time = now + timedelta(hours=hours_until_ko)
        
        # Determine day prefix
        days_diff = (kickoff_time.date() - now.date()).days
        if days_diff == 0:
            day_prefix = "Today"
        elif days_diff == 1:
            day_prefix = "Tomorrow"
        else:
            day_prefix = kickoff_time.strftime("%A")  # Day name (e.g., Sunday)
        
        kickoff_display = f"{day_prefix} {kickoff_time.strftime('%H:%M')}"
        
        # Determine which team to display (use fixture team name, not Sky Bet name)
        is_home = home_team.lower() in outcome_name.lower() or outcome_name.lower() in home_team.lower()
        display_team_name = home_team if is_home else away_team
        
        opportunity = {
            'match_id': match_id,
            'home_team': home_team,
            'away_team': away_team,
            'competition': competition,
            'hours_until_ko': hours_until_ko,
            'kickoff_display': kickoff_display,
            'outcome': display_team_name,
            'back_odds': back_odds,
            'back_site': 'Sky Bet',
            'lay_odds': lay_odds,
            'lay_site': lay_site,
            'lay_liquidity': lay_liquidity,
            'rating': rating,
            'oddschecker_url': f"https://www.oddschecker.com/football/{oddschecker_slug}",
            'qualifying_sites': qualifying_sites + realert_sites
        }
        
        # Send new alerts
        if qualifying_sites:
            print(f"\n[ALERT] ✅ NEW OPPORTUNITY for {len(qualifying_sites)} site(s)!")
            print(f"[DISCORD] Sending alert to {len(qualifying_sites)} channel(s)...")
            for site in qualifying_sites:
                channel_id = site.get('channel_id')
                if send_discord_alert(opportunity, [site], is_realert=False):
                    mark_match_seen(match_id, outcome_name, channel_id, rating, seen_matches)
                    print(f"[TRACKING] Marked as seen for {site.get('name', 'Unknown')}: {match_id}_{outcome_name} @ {rating:.2f}%")
        
        # Send re-alerts
        if realert_sites:
            print(f"\n[ALERT] 🔄 RE-ALERT for {len(realert_sites)} site(s)!")
            print(f"[DISCORD] Sending re-alert to {len(realert_sites)} channel(s)...")
            for site in realert_sites:
                channel_id = site.get('channel_id')
                if send_discord_alert(opportunity, [site], is_realert=True):
                    mark_match_seen(match_id, outcome_name, channel_id, rating, seen_matches)
                    print(f"[TRACKING] Updated rating for {site.get('name', 'Unknown')}: {match_id}_{outcome_name} @ {rating:.2f}%")
        
        opportunities.append(opportunity)
        
        # Rate limit between matches
        time.sleep(2)
    
    return opportunities

def display_summary(opportunities):
    """Display summary of all opportunities found"""
    if not opportunities:
        print("\n" + "="*80)
        print("No opportunities found matching criteria")
        return
    
    print("\n" + "="*80)
    print(f"FOUND {len(opportunities)} OPPORTUNITIES")
    print("="*80)
    
    for i, opp in enumerate(opportunities, 1):
        print(f"\n{i}. {opp['home_team']} v {opp['away_team']}")
        print(f"   Competition: {opp['competition']}")
        print(f"   KO in: {opp['hours_until_ko']:.1f} hours")
        print(f"   Outcome: {opp['outcome']}")
        print(f"   Back: {opp['back_odds']} @ {opp['back_site']}")
        print(f"   Lay: {opp['lay_odds']} @ {opp['lay_site']} (£{opp['lay_liquidity']})")
        print(f"   Rating: {opp['rating']:.2f}%")
        print(f"   Link: {opp['oddschecker_url']}")

def main():
    """Main execution flow"""
    print("="*80)
    print("AccaFreeze - First Team To Score Arbitrage Scanner")
    print("="*80)
    
    # Load config
    config = load_config()
    if not config:
        print("[ERROR] Failed to load config")
        return
    
    sites = config.get('sites', [])
    if not sites:
        print("[ERROR] No sites configured")
        return
    
    enabled_sites = [s for s in sites if s.get('enabled', True)]
    print(f"\n[CONFIG] {len(enabled_sites)} enabled site(s):")
    for site in enabled_sites:
        print(f"  - {site.get('name', 'Unknown')}:")
        print(f"      Lay >= {site.get('min_lay_odds', 'N/A')}, Back >= {site.get('min_back_odds', 'N/A')}")
        print(f"      Rating >= {site.get('min_rating', 'N/A')}%, Hours <= {site.get('hours_to_ko', 'N/A')}")
    
    # Load seen matches
    seen_matches = load_seen_matches()
    print(f"[TRACKING] Loaded {len(seen_matches)} seen matches")
    
    # Fetch data
    data = fetch_accafreeze_data()
    if not data:
        print("[ERROR] Failed to fetch data")
        return
    
    # Filter matches (use maximum hours_to_ko from all sites)
    max_hours = max([s.get('hours_to_ko', 24) for s in enabled_sites], default=24)
    print(f"\n[FILTER] Filtering matches (max {max_hours}h to KO)...")
    qualifying = filter_matches(data, max_hours)
    print(f"[FILTER] Found {len(qualifying)} potential matches to check")
    
    if not qualifying:
        print("[INFO] No qualifying matches found")
        return
    
    # Check opportunities
    debug = config.get('debug', False)
    print(f"\n[CHECK] Checking Sky Bet odds on OddsChecker...")
    opportunities = check_opportunities(qualifying, enabled_sites, seen_matches, debug)
    
    # Display summary
    display_summary(opportunities)
    
    # Save to file
    if opportunities:
        output_file = 'accafreeze_opportunities.json'
        with open(output_file, 'w') as f:
            json.dump(opportunities, f, indent=2)
        print(f"\n[SAVED] Results saved to {output_file}")

if __name__ == "__main__":
    main()
