import os, sys, time, json, requests, shutil
from dotenv import load_dotenv
import pytz
import traceback
from datetime import datetime, timedelta, timezone
import cloudscraper
from collections import defaultdict
from unidecode import unidecode
import unicodedata
import re 
import unicodedata
import urllib.request
import urllib.error
import urllib.parse
from types import SimpleNamespace
from betfair import Betfair
from oc import get_oddschecker_match_slug, get_oddschecker_odds
from willhill_betbuilder import get_odds, configure, BET_TYPES

try:
    from ladbrokes_alerts.client import LadbrokesAlerts
except Exception:
    LadbrokesAlerts = None


# ========= INITIALIZATION =========

load_dotenv()
london = pytz.timezone("Europe/London")
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEBUG_DIR = os.path.join(BASE_DIR, 'debug')
os.makedirs(DEBUG_DIR, exist_ok=True)

# ========= WH ODDS TRACKING =========
WH_ODDS_TRACKING_DIR = os.path.join(BASE_DIR, 'wh_odds_tracking')
os.makedirs(WH_ODDS_TRACKING_DIR, exist_ok=True)
RUN_COUNTER_FILE = os.path.join(WH_ODDS_TRACKING_DIR, 'run_counter.json')

def load_run_counter():
    """Load the persistent run counter from disk."""
    try:
        if os.path.exists(RUN_COUNTER_FILE):
            with open(RUN_COUNTER_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('run_number', 0)
    except Exception as e:
        print(f"[WARN] Failed to load run counter: {e}")
    return 0

def save_run_counter(run_number):
    """Save the run counter to disk."""
    try:
        data = {'run_number': run_number, 'last_updated': datetime.now(timezone.utc).isoformat()}
        tmp_file = RUN_COUNTER_FILE + '.tmp'
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_file, RUN_COUNTER_FILE)
    except Exception as e:
        print(f"[WARN] Failed to save run counter: {e}")

def track_wh_odds(match_id, match_name, player_name, market_type, wh_odds, boosted_odds, lay_odds, combo_data=None, run_number=None):
    """
    Track William Hill odds over time for analysis.
    Appends timestamped records to a JSON file per match.
    
    Args:
        match_id: William Hill match ID
        match_name: Match name for reference
        player_name: Player name
        market_type: 'FGS' or 'AGS'
        wh_odds: Original WH odds before boost
        boosted_odds: Boosted odds (if applicable, same as wh_odds if not boosted)
        lay_odds: Best lay odds from exchanges
        combo_data: Optional dict with combo selection details
        run_number: Optional run/loop number for correlation
    """
    try:
        # Create a file per match (by match_id)
        tracking_file = os.path.join(WH_ODDS_TRACKING_DIR, f"{match_id}.json")
        
        # Load existing data if file exists
        if os.path.exists(tracking_file):
            with open(tracking_file, 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)
        else:
            tracking_data = {
                'match_id': match_id,
                'match_name': match_name,
                'records': []
            }
        
        # Create new record
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'player_name': player_name,
            'market_type': market_type,
            'wh_odds': float(wh_odds),
            'boosted_odds': float(boosted_odds),
            'lay_odds': float(lay_odds),
            'rating': round((float(boosted_odds) / float(lay_odds) * 100), 2) if lay_odds > 0 else 0
        }
        
        # Add run number if provided
        if run_number is not None:
            record['run_number'] = run_number
        
        # Add combo data if provided
        if combo_data:
            record['combo'] = combo_data
        
        # Append record
        tracking_data['records'].append(record)
        
        # Save atomically
        tmp_file = tracking_file + '.tmp'
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, indent=2)
        os.replace(tmp_file, tracking_file)
        
    except Exception as e:
        print(f"[WARN] Failed to track WH odds: {e}")

def track_wh_base_odds(match_id, match_name, base_odds_data, run_number=None):
    """
    Track William Hill base (single-leg) goalscorer odds over time.
    This helps determine if combo price changes are driven by base odds changes.
    Returns a set of (player_name, market_type) tuples for odds that changed.
    
    Args:
        match_id: William Hill match ID
        match_name: Match name for reference
        base_odds_data: Dict of {(player_name, market_type): odds_value}
        run_number: Optional run/loop number for correlation
    
    Returns:
        set of (player_name, market_type) tuples that changed, or empty set
    """
    try:
        # Create a separate file for base odds tracking
        tracking_file = os.path.join(WH_ODDS_TRACKING_DIR, f"{match_id}_base.json")
        
        # Load existing data if file exists
        if os.path.exists(tracking_file):
            with open(tracking_file, 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)
        else:
            tracking_data = {
                'match_id': match_id,
                'match_name': match_name,
                'records': []
            }
        
        # Create new record with timestamp
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'odds': {}
        }
        
        # Add run number if provided
        if run_number is not None:
            record['run_number'] = run_number
        
        # Store all odds in a structured format
        for (player_name, market_type), odds in base_odds_data.items():
            key = f"{player_name}|{market_type}"
            record['odds'][key] = float(odds)
        
        # Detect changes by comparing with previous record
        changed_markets = set()
        if len(tracking_data['records']) > 0:
            prev_record = tracking_data['records'][-1]
            for key, new_odds in record['odds'].items():
                prev_odds = prev_record['odds'].get(key)
                if prev_odds and prev_odds != new_odds:
                    player_name, market_type = key.split('|')
                    changed_markets.add((player_name, market_type))
                    print(f"[WH BASE CHANGE] {player_name} ({market_type}): {prev_odds} → {new_odds}")
        
        # Append record
        tracking_data['records'].append(record)
        
        # Save atomically
        tmp_file = tracking_file + '.tmp'
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, indent=2)
        os.replace(tmp_file, tracking_file)
        
        return changed_markets
        
    except Exception as e:
        print(f"[WARN] Failed to track WH base odds: {e}")
        return set()

def get_wh_base_goalscorer_odds(wh_client, wh_match_id):
    """
    Extract base William Hill odds for all markets used in bet builder combos.
    Fetches from both /0 and /4 endpoints to get all available markets.
    
    Args:
        wh_client: BetBuilderClient instance with loaded event
        wh_match_id: William Hill match ID
    
    Returns:
        Dict of {(player_name, market_type): odds} or {} on failure
    """
    try:
        from bs4 import BeautifulSoup
        import requests
        
        def fractional_to_decimal(odds_str):
            try:
                if odds_str == "EVS":
                    return 2.0
                num, denom = odds_str.split("/")
                return round(float(num) / float(denom) + 1, 2)
            except Exception:
                return None
        
        base_odds = {}
        
        headers = {
            "referer": f"https://sports.williamhill.com/betting/en-gb/football/{wh_match_id}",
            "authority": "w.sports.williamhill.com",
            "accept": "text/html, */*; q=0.01",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-GB,en;q=0.9,en-US;q=0.8",
            "cache-control": "no-cache",
            "origin": "https://sports.williamhill.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0"
        }
        
        # Markets we need to track (matching combo legs):
        # From /0: Total Goals - Over 0.5, FGS, AGS
        # From /4: Player to Score or Assist
        
        # Fetch from /0 for Total Goals and Scorer Markets
        url_0 = f"https://w.sports.williamhill.com/fragments/eventEntity/en-gb/football/{wh_match_id}/0"
        try:
            scraper = cloudscraper.create_scraper()
            response = scraper.get(url_0, headers=headers, timeout=15)
            html = response.content.decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            
            for section in soup.find_all('section'):
                h2 = section.find('h2')
                if not h2:
                    continue
                
                section_name = h2.text.strip()
                
                # Handle Scorer Markets (FGS, AGS, etc.)
                if section_name == 'Scorer Markets':
                    class_to_market = {
                        'odds-market-1': 'FGS',  # First Goalscorer
                        'odds-market-2': 'AGS',  # Anytime Goalscorer
                    }
                    
                    buttons = section.find_all('button', {'data-player': True, 'data-odds': True})
                    
                    for button in buttons:
                        player_name = button.get('data-player', '').strip()
                        odds_frac = button.get('data-odds', '')
                        
                        if not player_name or not odds_frac:
                            continue
                        
                        parent_li = button.parent
                        if not parent_li or parent_li.name != 'li':
                            continue
                        
                        parent_classes = parent_li.get('class', [])
                        odds_market_class = None
                        for cls in parent_classes:
                            if cls.startswith('odds-market-'):
                                odds_market_class = cls
                                break
                        
                        if odds_market_class not in class_to_market:
                            continue
                        
                        market_type = class_to_market[odds_market_class]
                        odds_dec = fractional_to_decimal(odds_frac)
                        
                        if odds_dec:
                            base_odds[(player_name, market_type)] = odds_dec
                
                # Handle Total Goals section for Over 0.5
                elif section_name in ['Total Goals', 'Match Over/Under Total Goals']:
                    buttons = section.find_all('button', {'data-odds': True})
                    
                    for button in buttons:
                        selection_text = button.get_text(strip=True)
                        odds_frac = button.get('data-odds', '')
                        
                        # Look for "Over 0.5" or similar
                        if 'over' in selection_text.lower() and '0.5' in selection_text:
                            odds_dec = fractional_to_decimal(odds_frac)
                            if odds_dec:
                                base_odds[('Match Total Goals', 'Over 0.5')] = odds_dec
                            break
        except Exception as e:
            print(f"[WARN] Failed to fetch WH base odds from /0: {e}")
        
        # Fetch from /4 for Player to Score or Assist
        url_4 = f"https://w.sports.williamhill.com/fragments/eventEntity/en-gb/football/{wh_match_id}/4"
        try:
            scraper = cloudscraper.create_scraper()
            response = scraper.get(url_4, headers=headers, timeout=15)
            html = response.content.decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            
            for section in soup.find_all('section'):
                h2 = section.find('h2')
                if not h2:
                    continue
                
                section_name = h2.text.strip()
                
                # Handle Player to Score or Assist
                if section_name == 'Player to Score or Assist':
                    buttons = section.find_all('button', {'data-player': True, 'data-odds': True})
                    
                    for button in buttons:
                        player_name = button.get('data-player', '').strip()
                        odds_frac = button.get('data-odds', '')
                        
                        if not player_name or not odds_frac:
                            continue
                        
                        odds_dec = fractional_to_decimal(odds_frac)
                        
                        if odds_dec:
                            base_odds[(player_name, 'Goal or Assist')] = odds_dec
        except Exception as e:
            print(f"[WARN] Failed to fetch WH base odds from /4: {e}")
        
        return base_odds
        
    except Exception as e:
        print(f"[WARN] Failed to get WH base odds: {e}")
        traceback.print_exc()
        return {}

# ========= CACHE CLEARING =========
_last_cache_clear = None

def _clear_cache_at_midnight():
    """Clear cache directory at midnight each day (or first run after)."""
    global _last_cache_clear
    now = datetime.now(london)
    
    # Check if we need to clear (first run or after midnight)
    if _last_cache_clear is None or now.date() > _last_cache_clear.date():
        try:
            cache_dir = 'cache'
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir)
                print(f"[INFO] Cache cleared at {now.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
            _last_cache_clear = now
        except Exception as e:
            print(f"[WARN] Failed to clear cache: {e}", flush=True)


def clear_cache():
    """Remove any existing cache files/dirs on startup.

    This deletes both `cache/` and `cached/` directories under the project
    root (best-effort) and recreates an empty `cache/` directory so the
    process has a place to write new cache files.
    """
    dirs = [
        os.path.join(BASE_DIR, 'cache'),
        os.path.join(BASE_DIR, 'cached')
    ]
    for d in dirs:
        try:
            if os.path.exists(d):
                shutil.rmtree(d)
                print(f"[INFO] Cleared cache directory: {d}")
        except Exception as e:
            print(f"[WARN] Failed to remove cache directory {d}: {e}")

    # Ensure `cache/` exists for later writes
    try:
        os.makedirs(os.path.join(BASE_DIR, 'cache'), exist_ok=True)
    except Exception:
        pass

# ========= ENV / PATHS =========
NORD_USER = os.getenv("NORD_USER", "")
NORD_PWD = os.getenv("NORD_PWD", "")
NORD_LOCATION = os.getenv("NORD_LOCATION", "")

DISCORD_BOT_TOKEN   = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_GOOSE_CHANNEL_ID = os.getenv("DISCORD_GOOSE_CHANNEL_ID", "").strip()  # separate channel for goose alerts
DISCORD_ARB_CHANNEL_ID   = os.getenv("DISCORD_ARB_CHANNEL_ID", "").strip()      # separate channel for arbitrage alerts
DISCORD_WH_CHANNEL_ID   = os.getenv("DISCORD_WH_CHANNEL_ID", "").strip()      # separate channel for William Hill BB alerts
DISCORD_LADBROKES_CHANNEL_ID   = os.getenv("DISCORD_LADBROKES_CHANNEL_ID", "").strip()      # separate channel for William Hill BB alerts

# Second Discord bot/channel for Smarkets-only WH alerts
DISCORD_BOT_TOKEN_SMARKETS = os.getenv("DISCORD_BOT_TOKEN_SMARKETS", "")  # Can be same or different bot
DISCORD_WH_SMARKETS_CHANNEL_ID = os.getenv("DISCORD_WH_SMARKETS_CHANNEL_ID", "").strip()  # Smarkets-only WH alerts

DISCORD_ENABLED     = os.getenv("DISCORD_ENABLED", "1") == "1"      # enable/disable posting

if NORD_USER and NORD_PWD and NORD_LOCATION:
    PROXIES = {
        'http': f'http://{NORD_USER}:{NORD_PWD}@{NORD_LOCATION}.nordvpn.com:89',
        'https': f'https://{NORD_USER}:{NORD_PWD}@{NORD_LOCATION}.nordvpn.com:89',
    }
else:
    PROXIES = {}
#FOR DEBUGGING/TESTING
TEST_PRICE_OFFSET = float(os.getenv("TEST_PRICE_OFFSET", "0"))

GOOSE_STATE_FILE = "state/goose_alert_state.json"
ARB_STATE_FILE = "state/arb_alert_state.json"
WH_STATE_FILE = "state/WH_alert_state.json"
WH_SMARKETS_STATE_FILE = "state/WH_smarkets_alert_state.json"  # Separate state for Smarkets-only alerts
LADBROKES_STATE_FILE = "state/lad_alert_state.json"
GOOSE_FOOTER_ICON_URL = "https://img.icons8.com/?size=100&id=CXvbGFYLkaMY&format=png&color=000000"
# ========= CONFIG =========
GBP_THRESHOLD_GOOSE  = float(os.getenv("GBP_THRESHOLD_GOOSE", "10"))
GBP_ARB_THRESHOLD = float(os.getenv("GBP_ARB_THRESHOLD", "10"))
GBP_WH_THRESHOLD = float(os.getenv("GBP_WH_THRESHOLD", "10"))
GBP_LADBROKES_THRESHOLD = float(os.getenv("GBP_LADBROKES_THRESHOLD", "10"))
GOOSE_MIN_ODDS      = float(os.getenv("GOOSE_MIN_ODDS", "1.2"))  # min odds for goose combos
WINDOW_MINUTES   = int(os.getenv("WINDOW_MINUTES", "90"))    # KO window
POLL_SECONDS      = int(os.getenv("POLL_SECONDS", "60"))    # How long should each loop wait
VIRGIN_ODDS_CACHE_DURATION = int(os.getenv("VIRGIN_ODDS_CACHE_DURATION", "300"))  # seconds to cache AGS combo responses
VERBOSE_TIMING = os.getenv("VERBOSE_TIMING", "0") == "1"  # Enable detailed timing logs

# Feature flags - enable/disable specific integrations
ENABLE_VIRGIN_GOOSE = os.getenv("ENABLE_VIRGIN_GOOSE", "1") == "1"  # Virgin Bet combo (Goose) alerts
ENABLE_ODDSCHECKER = os.getenv("ENABLE_ODDSCHECKER", "1") == "1"    # OddsChecker arbitrage alerts
ENABLE_WILLIAMHILL = os.getenv("ENABLE_WILLIAMHILL", "1") == "1"    # William Hill bet builder alerts
ENABLE_LADBROKES = os.getenv("ENABLE_LADBROKES", "0").lower() in ("1", "true", "yes")
# Enable fetching additional exchange odds (from Oddsmatcha). Set to '0' to disable.
ENABLE_ADDITIONAL_EXCHANGES = os.getenv("ENABLE_ADDITIONAL_EXCHANGES", "1").lower() in ("1", "true", "yes")

# WH combo pricing modes:
# Mode 1 (default): Only fetch combo price if no cache exists OR base odds changed
# Mode 2: Always refresh with 5-minute timeout (existing behavior)
WH_PRICING_MODE = int(os.getenv("WH_PRICING_MODE", "1"))  # 1 or 2

# ========= DISCORD =========
def send_discord_embed(title, description, fields, colour=0x3AA3E3, channel_id=None, footer=None,icon=None, bot_token=None):
    if not DISCORD_ENABLED:
        return

    # --- 1. Construct the base embed dictionary ---
    embed = {
        "title": title,
        "description": description,
        # Discord API uses decimal for color, 0x... is correct.
        "color": colour, 
        "fields": [{"name": n, "value": v, "inline": True} for (n, v) in fields]
    }
    
    # --- 2. Add the footer dictionary if requested ---
    if footer:
        # 'footer' is now the dictionary key for the footer object
        # 'text' and 'icon_url' are keys within the footer object
        if icon:
            embed["footer"] = {
                "text": footer, # Use the string passed to the function
                "icon_url": icon
            }
        elif channel_id == DISCORD_WH_CHANNEL_ID or channel_id == DISCORD_WH_SMARKETS_CHANNEL_ID:
            embed["footer"] = {
                "text": footer
                
            }

    
    # --- 3. Add the timestamp if a footer wasn't provided (as per your original logic) ---
    else:
        # Note: Discord recommends using 'timestamp' as a top-level key for the embed
        embed["timestamp"] = datetime.now(london).isoformat()
    payload = {"embeds": [embed], "content": ""}

    # Use provided bot token or fall back to default
    token = bot_token if bot_token else DISCORD_BOT_TOKEN

    if not token:
        print(f"[WARN] Discord not configured. Token set={bool(token)} channels={channel_id}")
        return

    try:
        r = requests.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {token}",
                        "Content-Type": "application/json"},
            json=payload, timeout=10
        )
        if r.status_code >= 300:
            print(f"[WARN] Channel {channel_id} error body: {r.text[:600]}")
    except Exception as e:
        print(f"[WARN] Channel {channel_id} post failed: {e}")

VIRGIN_HEADERS = {
        'Content-Type': 'application/json',
        'Client-App-Version': '2.48 (7016)',
        'Accept': 'application/json',
        'Client-Os-Version': 'iOS_18.4.1',
        'Client-Id': 'iphone',
        'Accept-Language': 'en-GB;q=1',
        'Accept-Encoding': 'gzip, deflate, br',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 inApp VirginBetUK/2.48',
        'Client-Device-Type': 'mobile',
          }

def write_json(data, filename):
    try:
        with open(filename, "w", encoding="utf-8") as outfile:
            json.dump(data, outfile, indent=4)
    except Exception:
        pass

def normalize_name(s: str) -> str:
    # 1. Handle empty/non-string input
    if not s:
        return ""

    # Ensure s is a string for all subsequent operations
    s = str(s)

    # --- ADAPTED DECODING STEP ---
    # Attempt to decode escaped unicode sequences (like "\u00ef" -> "ï")
    # This step is the most relevant for handling input that *looks* escaped,
    # and is the primary change based on your previous query.
    try:
        # Use Python's built-in 'unicode_escape' decoder to process
        # literal backslashes followed by 'u' or 'x'.
        s = s.encode('latin1', 'backslashreplace').decode('unicode_escape')
    except Exception:
        # If decoding fails, continue with the original string
        pass
    
    # --- ACCENT AND DIACRITIC REMOVAL ---
    # Decompose into base character + combining mark (NFKD) 
    # and remove the combining marks (e.g., 'ï' -> 'i' + '̈' -> 'i')
    try:
        # Normalize to NFKD
        s_nfkd = unicodedata.normalize('NFKD', s)
        # Filter out characters with the 'Mn' (Mark, Nonspacing) category
        s = ''.join(ch for ch in s_nfkd if not unicodedata.combining(ch))
    except Exception:
        pass

    # --- TRANSLITERATION ---
    # Transliterate characters that couldn't be decomposed (e.g., 'Ø' -> 'O')
    try:
        s = unidecode(s)
    except Exception:
        pass
    
    # --- CLEANUP AND STANDARDIZATION ---
    # 1. Lowercase
    s = s.lower()

    # 2. Replace common punctuation with a single space.
    # Using regex is cleaner than a long chain of .replace()
    s = re.sub(r'[.,\'"\-()&]', ' ', s)

    # 3. Collapse multiple spaces into a single space and strip leading/trailing spaces
    # s.split() splits by any whitespace and removes empty strings, 
    # and " ".join() re-joins them with a single space.
    s = " ".join(s.split())

    return s

def getVirginMarkets(virgin_id):
    cache_dir = os.path.join(BASE_DIR, 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f'{virgin_id}_virgin_markets.json')
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as file:
                cached_data = json.load(file)
                #print(f"✅ Loaded {len(cached_data)} individuals from cache.")
                return cached_data
        except Exception:
            pass
    virgin_url = f'https://gateway.virginbet.com/sportsbook/gateway/v1/view/event?eventid={virgin_id}&lang=en-gb'
    scraper = cloudscraper.create_scraper()  # returns a CloudScraper instance
    try:
        resp = scraper.get(virgin_url, proxies=PROXIES or None, headers=VIRGIN_HEADERS, timeout=30)
    except Exception as e:
        print(f"Error requesting Virgin markets for event {virgin_id}:", e)
        return []

    try:
        event_markets_json = resp.json()
    except Exception as e:
        print(f"Failed to decode Virgin JSON for event {virgin_id}:", e)
        try:
            print('Response text:', resp.text[:1000])
        except Exception:
            pass
        return []
    write_json(event_markets_json, os.path.join(cache_dir, f"virgin_event_{virgin_id}.json"))
    if not event_markets_json or 'event' not in event_markets_json:
        print(f"Virgin response for event {virgin_id} contained no 'event' key. Status: {getattr(resp, 'status_code', None)}")
        # Save raw response for debugging
        try:
            write_json({'status_code': getattr(resp, 'status_code', None), 'text': resp.text}, os.path.join(DEBUG_DIR, f"virgin_raw_response_{virgin_id}.json"))
        except Exception:
            pass
        return []

    event = event_markets_json.get('event')
    if not isinstance(event, dict):
        print(f"Virgin response for event {virgin_id} had null 'event' payload. Status: {getattr(resp, 'status_code', None)}")
        # Save raw response for debugging
        try:
            write_json({'status_code': getattr(resp, 'status_code', None), 'text': resp.text}, os.path.join(DEBUG_DIR, f"virgin_raw_response_{virgin_id}.json"))
        except Exception:
            pass
        return []

    print(event.get('name'))
    wanted_markets = []
    market_types = ["to score or assist (settled using opta data)","player's shots on target (settled using opta data)"]

    for market in event.get('markets', []) or []:
        if not market:
            continue
        mname = (market.get('name') or '').lower()

        # If market_types provided, match exact names; otherwise match by substring
        matched = False
        for mt in market_types:
            if mt in mname:
                matched = True
                break
        if matched:
            wanted_markets.append(market)
    write_json(wanted_markets, cache_file)
    return wanted_markets

def find_player_sot_and_ga_ids(markets, player_name):
    """Return [SOT_id, GA_id] for `player_name` from the provided `markets` list.

    - `markets` should be the list returned by `getVirginMarkets`.
    - If the player is not present at all, return [].
    - If a slot is missing, its value will be None.
    """
    if not markets or not player_name:
        return None

    # Decode any escaped unicode in the incoming player_name and normalize it
    try:
        decoded_pname = player_name.encode('utf-8').decode('unicode_escape') if isinstance(player_name, str) else player_name
    except Exception:
        decoded_pname = player_name
    target_norm = normalize_name(decoded_pname)
    sot_id = None
    ga_id = None

    for market in markets:
        mname = (market.get('name') or '').lower()
        for sel in market.get('selections') or []:
            raw_sel_name = sel.get('name') or ''
            # Extract player portion after possible prefixes like 'First: Name' or suffixes like ' - Over 0.5'
            player_part = raw_sel_name.split(' - ')[0].strip()
            # Remove surrounding punctuation/quotes and normalize 'Last, First' to 'First Last'
            player_part = player_part.strip(' "\'()[]')
            if ', ' in player_part:
                player_part = " ".join(player_part.split(", ")[::-1])
            player_part = " ".join(player_part.split())
            sel_norm = normalize_name(player_part)
            if sel_norm != target_norm:
                continue

            outcome = (sel.get('outcomeType') or '').upper()
            hcp = str(sel.get('hcp') or '').strip()
            lower_name = (sel_norm or '').lower()

            # Shots On Target: OVER + 'over 0.5' (or handicap 0.5)
            if outcome == 'OVER' and ('over 0.5' in lower_name or hcp == '0.5'):
                sot_id = sel.get('id')

            # Goal or Assist: YES outcome or market name indicates GA
            if outcome == 'YES' or 'goal or assist' in lower_name or ('to score' in mname and 'assist' in mname):
                ga_id = sel.get('id')

            if sot_id and ga_id:
                return {'name': player_name, 'sot_id': sot_id, 'ga_id': ga_id}

    # If player wasn't present at all, return None
    if not sot_id and not ga_id:
        return None

    return {'name': player_name, 'sot_id': sot_id, 'ga_id': ga_id}

def getGoosedCombos(match, player_data, delay_seconds=0, ignore_lineup=False):
    back_odds_results = []
    
    # Validate that player has both required markets
    if not player_data.get('ga_id') or not player_data.get('sot_id'):
        # print(f"Player {player_data.get('name')} missing required markets: ga_id={player_data.get('ga_id')}, sot_id={player_data.get('sot_id')}")
        return back_odds_results
    
    combo_payload = {
        "selections": [
            {"id": player_data['ga_id'], "eachWay": False},
            {"id": player_data['sot_id'], "eachWay": False}
        ],
        "oddsFormat": "DECIMAL",
        "selectionGroups": [{"id": 10, "selections": [player_data['ga_id'], player_data['sot_id']]}],
        "betTypes": [{"type": "YOURBET"}]
    }
    # Prepare cache — reuse recent responses to avoid hitting Virgin too often
    cache_dir = os.path.join(BASE_DIR, 'cache', 'virgin_prices')
    os.makedirs(cache_dir, exist_ok=True)
    
    # Generate cache key from sorted selection IDs (consistent with WH approach)
    selection_ids = sorted([player_data['ga_id'], player_data['sot_id']])
    cache_key = '_'.join(selection_ids)
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")

    body = None
    resp = None  # Initialize resp to None so we can check if it was set
    # Try load cache
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            ts = float(cached.get('ts', 0))
            if time.time() - ts <= VIRGIN_ODDS_CACHE_DURATION:
                body = cached.get('body')
                # print("Using Cached Virgin Odds")
        except Exception:
            body = None

    # If no fresh cache, make request and save response
    if body is None:
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.post(
                'https://gateway.virginbet.com/sportsbook/gateway/v2/calculatebets?lang=en-gb',
                proxies=PROXIES,
                headers=VIRGIN_HEADERS,
                json=combo_payload,
                timeout=15
            )
        except Exception as e:
            print('Error making AGS combo request:', e)
            return back_odds_results

        # Parse and validate JSON response
        try:
            body = resp.json()
        except Exception as e:
            # JSON parse error — surface response text for debugging
            text_snip = None
            try:
                text_snip = (resp.text or '')[:1000]
            except Exception:
                text_snip = '<no-body>'
            print('Error parsing AGS combo JSON response:', e)
            print('Response status:', getattr(resp, 'status_code', None), 'body_snippet:', text_snip)
            return back_odds_results

        # Save to cache (best-effort)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'ts': time.time(), 'body': body}, f)
        except Exception:
            pass

    # Ensure expected structure exists
    data_obj = body.get('data') if isinstance(body, dict) else None
    if not data_obj:
        status_hint = getattr(resp, 'status_code', 'unknown') if resp else 'cached'
        print(f'AGS combo response missing "data" key. Source: {status_hint}')
        # show a short snippet to help debugging
        try:
            print('Response snippet:', json.dumps(body)[:800])
        except Exception:
            pass
        return back_odds_results

    bet_details = data_obj.get('betDetails') if isinstance(data_obj, dict) else None
    if not bet_details or not isinstance(bet_details, list):
        print('AGS combo response has no betDetails list. data keys:', list(data_obj.keys()) if isinstance(data_obj, dict) else '<not-dict>')
        return back_odds_results

    try:
        back_odds = bet_details[0].get('totalOdds')
    except Exception as e:
        print('Failed to extract totalOdds from betDetails:', e)
        return back_odds_results

    # All good — record result
    try:
        record = {
            "match_id": match.get('id'),
            "player_name": player_data.get('name'),
            "odds": back_odds,
            "bet_type": "AGS",
            "bet_request_json": combo_payload,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        back_odds_results.append(record)
    except Exception as e:
        print('Error recording AGS combo result:', e)

    return back_odds_results


def get_ladbrokes_player_combos(ladb_client, ladb_match_id, player_name, handicap="0.5"):
    """Fetch ladbrokes drilldown and return AGS and FGS combo odds for a single player.

    Returns a dict: {'ags_combo': float or None, 'fgs_combo': float or None}
    """
    if not ladb_client or not ladb_match_id:
        return None

    try:
        drilldown = ladb_client.get_bet_ids_for_match(int(ladb_match_id), use_cache=True)
        if not drilldown:
            return None

        # extract event bEId
        event_bEId = ""
        try:
            ss = drilldown.get('SSResponse', {})
            first = ss.get('children', [None])[0]
            event = first.get('event', {})
            ext = event.get('extIds', '')
            if ext and ',' in ext:
                parts = ext.split(',')
                if len(parts) >= 2:
                    event_bEId = parts[1]
        except Exception:
            event_bEId = ""

        # find First Goalscorer and Anytime markets
        def norm(n):
            return ' '.join((n or '').strip().split()).lower()

        first_goals = []
        anytime_goals = []
        over0 = None

        ss = drilldown.get('SSResponse', {})
        children = ss.get('children', [])
        if not children:
            return None
        event = children[0].get('event', {})
        for child in event.get('children', []):
            if 'market' not in child:
                continue
            market = child['market']
            mname = (market.get('name') or '').strip()
            # First Goalscorer
            if 'first goalscorer' in mname.lower():
                for oc in market.get('children', []):
                    if 'outcome' not in oc:
                        continue
                    o = oc['outcome']
                    price = {}
                    if 'children' in o and o['children']:
                        p = o['children'][0].get('price', {})
                        price = {'num': p.get('priceNum','0'), 'den': p.get('priceDen','1'), 'priceDec': p.get('priceDec')}
                    out_ext = o.get('extIds','')
                    bSId = ''
                    if out_ext and ',' in out_ext:
                        parts = out_ext.split(',')
                        if len(parts) >= 2:
                            bSId = parts[1]
                    first_goals.append({'outcome_id': o.get('id'), 'name': o.get('name'), 'market_id': market.get('id'), 'sub_event_id': market.get('eventId'), 'bMId': (market.get('extIds') or '').split(',')[1] if (market.get('extIds') or '').count(',') else '', 'bSId': bSId, 'price': price})

            # Anytime Goalscorer
            if 'anytime goalscorer' in mname.lower() or 'anytime' in mname.lower():
                for oc in market.get('children', []):
                    if 'outcome' not in oc:
                        continue
                    o = oc['outcome']
                    price = {}
                    if 'children' in o and o['children']:
                        p = o['children'][0].get('price', {})
                        price = {'num': p.get('priceNum','0'), 'den': p.get('priceDen','1'), 'priceDec': p.get('priceDec')}
                    out_ext = o.get('extIds','')
                    bSId = ''
                    if out_ext and ',' in out_ext:
                        parts = out_ext.split(',')
                        if len(parts) >= 2:
                            bSId = parts[1]
                    anytime_goals.append({'outcome_id': o.get('id'), 'name': o.get('name'), 'market_id': market.get('id'), 'sub_event_id': market.get('eventId'), 'bMId': (market.get('extIds') or '').split(',')[1] if (market.get('extIds') or '').count(',') else '', 'bSId': bSId, 'price': price})

            # Exact Over/Under Total Goals 0.5
            if mname == f"Over/Under Total Goals {handicap}":
                for oc in market.get('children', []):
                    if 'outcome' not in oc:
                        continue
                    o = oc['outcome']
                    if o.get('name','').lower() != 'over':
                        continue
                    price = {}
                    if 'children' in o and o['children']:
                        p = o['children'][0].get('price', {})
                        price = {'num': p.get('priceNum','0'), 'den': p.get('priceDen','1'), 'priceDec': p.get('priceDec')}
                    out_ext = o.get('extIds','')
                    bSId = ''
                    if out_ext and ',' in out_ext:
                        parts = out_ext.split(',')
                        if len(parts) >= 2:
                            bSId = parts[1]
                    over0 = {'outcome_id': o.get('id'), 'name': o.get('name'), 'market_id': market.get('id'), 'sub_event_id': market.get('eventId'), 'bMId': (market.get('extIds') or '').split(',')[1] if (market.get('extIds') or '').count(',') else '', 'bSId': bSId, 'price': price, 'handicap': str(handicap)}

        if not over0:
            return None

        # Build maps and perform fuzzy matching similar to WH logic
        def name_parts(name):
            parts = [p for p in re.split(r"[\s\-]+", (name or '').lower()) if len(p) > 1]
            return set(parts)

        # exact normalization lookup first
        fmap = {norm(o.get('name')): o for o in first_goals}
        amap = {norm(o.get('name')): o for o in anytime_goals}
        target_norm = norm(player_name)

        f = None
        a = None

        if target_norm in fmap:
            f = fmap[target_norm]
        if target_norm in amap:
            a = amap[target_norm]

        # If either is missing, attempt fuzzy match by token overlap
        if not f:
            best = None
            best_score = 0.0
            tparts = name_parts(player_name)
            for o in first_goals:
                oparts = name_parts(o.get('name'))
                if not oparts or not tparts:
                    continue
                inter = len(tparts & oparts)
                union = len(tparts | oparts)
                score = inter / union if union > 0 else 0
                if inter >= 2 or score >= 0.5:
                    if score > best_score:
                        best_score = score
                        best = o
            f = best

        if not a:
            best = None
            best_score = 0.0
            tparts = name_parts(player_name)
            for o in anytime_goals:
                oparts = name_parts(o.get('name'))
                if not oparts or not tparts:
                    continue
                inter = len(tparts & oparts)
                union = len(tparts | oparts)
                score = inter / union if union > 0 else 0
                if inter >= 2 or score >= 0.5:
                    if score > best_score:
                        best_score = score
                        best = o
            a = best

        # If still missing either market for this player, bail out
        if not f or not a:
            return None
        leg_a = ladb_client.create_leg_from_outcome(f, event_bEId=event_bEId)
        leg_b = ladb_client.create_leg_from_outcome(a, event_bEId=event_bEId)
        leg_over = ladb_client.create_leg_from_outcome(over0, event_bEId=event_bEId)

        # Prepare stable price keys for each leg (prefer priceDec)
        def _price_key(outcome_obj):
            try:
                p = outcome_obj.get('price', {})
                dec = p.get('priceDec')
                if dec is not None:
                    return str(dec)
                num = p.get('num')
                den = p.get('den')
                return f"{num}/{den}"
            except Exception:
                return ''

        # Cache path per match + outcome ids
        try:
            oids = [str(f.get('outcome_id')), str(a.get('outcome_id')), str(over0.get('outcome_id'))]
        except Exception:
            oids = [str(f.get('outcome_id') or ''), str(a.get('outcome_id') or ''), str(over0.get('outcome_id') or '')]

        cache_dir = os.path.join(BASE_DIR, 'cache', 'ladbrokes_prices')
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception:
            pass

        cache_file = os.path.join(cache_dir, f"{ladb_match_id}_{'_'.join(oids)}.json")

        current_legs = {'f': _price_key(f), 'a': _price_key(a), 'over': _price_key(over0)}

        # Try return cached combos if leg prices unchanged
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as cf:
                    cached = json.load(cf)
                if cached.get('legs') == current_legs:
                    return {'ags_combo': cached.get('ags_combo'), 'fgs_combo': cached.get('fgs_combo')}
        except Exception:
            pass

        # Build and fetch combos (cache miss or legs changed)
        ags_payload = ladb_client.build_bet_request(int(ladb_match_id), [leg_b, leg_over])
        ags_combo = ladb_client.get_back_odds(ags_payload)

        fgs_payload = ladb_client.build_bet_request(int(ladb_match_id), [leg_a, leg_b])
        fgs_combo = ladb_client.get_back_odds(fgs_payload)

        # Save cache
        try:
            with open(cache_file, 'w', encoding='utf-8') as cf:
                json.dump({'ts': time.time(), 'legs': current_legs, 'ags_combo': ags_combo, 'fgs_combo': fgs_combo}, cf, indent=2)
        except Exception:
            pass

        return {'ags_combo': ags_combo, 'fgs_combo': fgs_combo}

    except Exception as e:
        print('Error fetching Ladbrokes combos for player', player_name, e)
        return None
   
def map_betfair_to_sites(betfair_id, target_sites=None):
    """Call the oddsmatcha API to map a Betfair match id to multiple target sites.

    Args:
        betfair_id: The Betfair match ID to convert
        target_sites: List of target site names (e.g., ['virginbet', 'williamhill'])
                     If None, defaults to ['virginbet', 'williamhill']

    Returns:
        Tuple of (mappings_dict, oddsmatcha_match_id):
        - mappings_dict: Dictionary mapping site names to their IDs, e.g.:
          {'virginbet': 'SBTE_2_1024825599', 'williamhill': 'OB_EV37926026'}
        - oddsmatcha_match_id: The oddsmatcha match ID (int) or None
    """
    if target_sites is None:
        target_sites = ['virginbet', 'williamhill']
    
    result = {}
    oddsmatcha_id = None
    
    for site in target_sites:
        try:
            api = f"https://api.oddsmatcha.uk/convert/site_to_site?source_site=betfair&source_match_ids={betfair_id}&target_site={site}"
            resp = requests.get(api, timeout=10)
            if not resp.ok:
                print(f"Mapping API returned {resp.status_code} for Betfair {betfair_id} -> {site}")
                continue
            data = resp.json()
            if data.get('success') and data.get('conversions'):
                conv = data['conversions'][0]
                target_id = conv.get('target_id')
                if target_id:
                    result[site] = target_id
                # Get oddsmatcha match_id from first successful conversion
                if oddsmatcha_id is None:
                    oddsmatcha_id = conv.get('match_id')
            else:
                print(f"Mapping API returned no conversion for Betfair {betfair_id} -> {site}")
        except Exception as e:
            print(f"Error calling mapping API for Betfair {betfair_id} -> {site}: {e}")
    
    return result, oddsmatcha_id

# Backward compatibility wrapper
def map_betfair_to_virgin(betfair_id):
    """Legacy wrapper for backward compatibility.
    
    Returns the first conversion dict on success or None.
    """
    mappings, _ = map_betfair_to_sites(betfair_id, ['virginbet'])
    if 'virginbet' in mappings:
        return {'target_id': mappings['virginbet']}
    return None

def is_match_in_wh_offer(wh_match_id, offer_id=1):
    """Check if a William Hill match ID is in the active offer.
    
    Args:
        wh_match_id: The William Hill match ID to check (e.g., 'OB_EV37969778')
        offer_id: The offer ID to check (defaults to 1 for WH 25% BB Boost)
    
    Returns:
        True if the match is in the offer, False otherwise.
    """
    try:
        api = f"https://api.oddsmatcha.uk/offers/{offer_id}"
        resp = requests.get(api, timeout=10)
        if not resp.ok:
            print(f"Offer API returned {resp.status_code} for offer {offer_id}")
            return False
        
        data = resp.json()
        matches = data.get('matches', [])
        
        # Check if wh_match_id is in any of the match mappings
        for match in matches:
            mappings = match.get('mappings', [])
            for mapping in mappings:
                if (mapping.get('site_name') == 'williamhill' and 
                    mapping.get('site_match_id') == wh_match_id):
                    return True
        
        return False
    except Exception as e:
        print(f"Error checking WH offer: {e}")
        return False

def fetch_lineups(oddsmatcha_match_id):
    """Fetch starting lineups from OddsMatcha API.

    Args:
        oddsmatcha_match_id: The oddsmatcha match ID

    Returns:
        Set of player names who are confirmed starters, or empty set if unavailable
    """
    try:
        api = f"https://api.oddsmatcha.uk/lineups/{oddsmatcha_match_id}"
        resp = requests.get(api, timeout=10)
        if not resp.ok:
            print(f"[LINEUPS] Lineups API returned status {resp.status_code} for match {oddsmatcha_match_id}")
            return set()

        try:
            data = resp.json()
        except Exception as e:
            print(f"[LINEUPS] Failed to decode JSON from lineups API for match {oddsmatcha_match_id}: {e}")
            try:
                print(f"[LINEUPS] Response text: {resp.text[:800]}")
            except Exception:
                pass
            return set()

        if not isinstance(data, dict):
            print(f"[LINEUPS] Unexpected lineups payload for match {oddsmatcha_match_id}: {type(data)}")
            try:
                print(f"[LINEUPS] Payload snippet: {str(data)[:800]}")
            except Exception:
                pass
            return set()

        starters = set()
        home_lineup = (data.get('home_lineup') or {}).get('line_up', [])
        away_lineup = (data.get('away_lineup') or {}).get('line_up', [])

        for player in home_lineup + away_lineup:
            name = player.get('name', '').strip()
            if name:
                starters.add(name)

        if starters:
            print(f"[LINEUPS] Fetched {len(starters)} confirmed starters for match {oddsmatcha_match_id}")
        else:
            print(f"[LINEUPS] No starters found for match {oddsmatcha_match_id} (home: {len(home_lineup)}, away: {len(away_lineup)})")

        return starters

    except Exception as e:
        print(f"[LINEUPS] Error fetching lineups for match {oddsmatcha_match_id}: {e}")
        return set()

def is_confirmed_starter(player_name, starters):
    """Check if a player is a confirmed starter using fuzzy matching.
    
    Args:
        player_name: Player name to check
        starters: Set of confirmed starter names
    
    Returns:
        True if player name matches a starter (exact or fuzzy), False otherwise
    """
    import re
    
    # Try exact match first
    if player_name in starters:
        return True
    
    # Fuzzy match: split on spaces and hyphens, match 2+ parts
    def normalize_name(name):
        parts = set(re.split(r'[\s\-]+', name.lower()))
        return {p for p in parts if len(p) > 1}
    
    player_parts = normalize_name(player_name)
    
    for starter in starters:
        starter_parts = normalize_name(starter)
        matches = len(player_parts & starter_parts)
        total_parts = len(player_parts | starter_parts)
        
        if total_parts == 0:
            continue
        
        # 2+ matches or >50% match rate
        if matches >= 2 or (matches / total_parts >= 0.5):
            return True
    
    return False

def fetch_exchange_odds(oddsmatcha_match_id):
    """Fetch lay odds from multiple exchanges for a match.
    
    Args:
        oddsmatcha_match_id: The oddsmatcha match ID
    
    Returns:
        Dictionary organized by market type and player name:
        {
            'Anytime Goalscorer': {
                'Bruno Fernandes': [
                    {'site_name': 'smarkets', 'lay_odds': 10.0, 'last_updated': '2025-12-15T14:48:17.165097'},
                    {'site_name': 'matchbook', 'lay_odds': 9.8, 'last_updated': '2025-12-15T14:48:20.123456'}
                ]
            },
            'First Goalscorer': { ... }
        }
    """
    try:
        api = f"https://api.oddsmatcha.uk/matches/{oddsmatcha_match_id}/markets/"
        resp = requests.get(api, timeout=10)
        if not resp.ok:
            print(f"Markets API returned {resp.status_code} for match {oddsmatcha_match_id}")
            return {}
        
        data = resp.json()
        result = {}
        current_time = datetime.now(timezone.utc)
        
        #print(f"[DEBUG] Fetched {len(data)} markets from oddsmatcha for match {oddsmatcha_match_id}")
        
        for market in data:
            market_name = market.get('market_name', '')
            
            # Only interested in goalscorer markets
            if market_name not in ['Anytime Goalscorer', 'First Goalscorer']:
                continue
            
            #print(f"[DEBUG] Processing market: {market_name}, odds count: {len(market.get('odds', []))}")
            
            if market_name not in result:
                result[market_name] = {}
            
            for odd in market.get('odds', []):
                site_name = odd.get('site_name')
                lay_odds = odd.get('lay_odds')
                outcome_name = odd.get('outcome_name')
                last_updated_str = odd.get('last_updated')
                
                # Skip if no lay odds, if it's betfair (already handled separately), or if missing data
                if not lay_odds or not outcome_name:
                    continue
                
                # Skip betfair - we already have betfair odds from the main betfair feed
                if site_name and site_name.lower() == 'betfair':
                    continue
                
                # Skip if data is older than 5 minutes
                if last_updated_str:
                    try:
                        # Parse the timestamp - handle both with and without timezone
                        if last_updated_str.endswith('Z'):
                            last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                        elif '+' in last_updated_str or last_updated_str.count('-') > 2:
                            # Already has timezone info
                            last_updated = datetime.fromisoformat(last_updated_str)
                        else:
                            # No timezone, assume UTC
                            last_updated = datetime.fromisoformat(last_updated_str).replace(tzinfo=timezone.utc)
                        
                        age_minutes = (current_time - last_updated).total_seconds() / 60
                        if age_minutes > 5:
                            #print(f"[DEBUG] Skipping {outcome_name} on {site_name} - data age: {age_minutes:.1f} minutes")
                            continue
                    except Exception as e:
                        #print(f"[DEBUG] Failed to parse timestamp for {outcome_name}: {e}")
                        continue  # Skip if we can't parse the timestamp
                
                # Store the odds
                if outcome_name not in result[market_name]:
                    result[market_name][outcome_name] = []

                # Extract liquidity from the lay_liquidity field
                liquidity_val = None
                try:
                    lay_liquidity = odd.get('lay_liquidity')
                    if lay_liquidity is not None:
                        liquidity_val = float(lay_liquidity)
                except (ValueError, TypeError):
                    liquidity_val = None

                result[market_name][outcome_name].append({
                    'site_name': site_name.capitalize() if site_name else site_name,
                    'lay_odds': float(lay_odds),
                    'last_updated': last_updated_str,
                    'raw': odd,
                    'norm': normalize_name(outcome_name) if outcome_name else '',
                    'liquidity': liquidity_val
                })
                #print(f"[DEBUG] Added {outcome_name} on {site_name} @ {lay_odds}")
        
        #print(f"[DEBUG] Final result: {len(result)} markets, total players: {sum(len(players) for players in result.values())}")
        return result
        
    except Exception as e:
        print(f"Error fetching exchange odds for match {oddsmatcha_match_id}: {e}")
        return {}

def combine_betfair_and_exchange_odds(betfair_odds, exchange_odds, market_type):
    """Combine Betfair and exchange odds for a market.
    
    Args:
        betfair_odds: List of odds dicts from Betfair with 'outcome', 'odds', 'size'
        exchange_odds: Dict from fetch_exchange_odds with player names as keys
        market_type: 'Anytime Goalscorer' or 'First Goalscorer'
    
    Returns:
        List of combined odds entries, each with:
        {
            'player_name': str,
            'site': str ('betfair' or exchange name),
            'lay_odds': float,
            'lay_size': float or None (None for exchanges),
            'has_size': bool
        }
    """
    combined = []
    
    # Add Betfair odds
    for odd in betfair_odds:
        combined.append({
            'player_name': odd.get('outcome', ''),
            'site': 'Betfair',
            'lay_odds': float(odd.get('odds', 0)),
            'lay_size': float(odd.get('size', 0)),
            'has_size': True
            ,
            'norm_name': normalize_name(odd.get('outcome', '') )
        })
    
    # Add exchange odds
    exchange_market = exchange_odds.get(market_type, {})
    for player_name, site_odds_list in exchange_market.items():
        for site_odd in site_odds_list:
            combined.append({
                'player_name': player_name,
                'site': site_odd.get('site_name'),
                'lay_odds': float(site_odd.get('lay_odds') or 0),
                'lay_size': (site_odd.get('liquidity') if site_odd.get('liquidity') is not None else None),
                'has_size': True if site_odd.get('liquidity') is not None else False,
                'raw': site_odd.get('raw', site_odd),
                'norm_name': site_odd.get('norm') or normalize_name(player_name),
                'source_outcome': player_name,
                'source_liquidity': site_odd.get('liquidity')
            })
    
    return combined

# ========= STATE =========
def save_state(player_name, match_id,file):
    """Mark (match_id, player_name) as alerted in the state file.

    State format:
    {
        "alerted": {
            "{match_id}_{player_name}": "<iso-timestamp>",
            ...
        }
    }
    """
    os.makedirs(os.path.dirname(file), exist_ok=True)
    # Load existing state if present
    state = {}
    try:
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8") as f:
                state = json.load(f) or {}
    except Exception:
        state = {}

    alerted = state.get('alerted', {}) if isinstance(state, dict) else {}
    key = f"{match_id}_{player_name}"
    try:
        alerted[key] = datetime.now(timezone.utc).isoformat()
    except Exception:
        alerted[key] = time.time()
    state['alerted'] = alerted

    tmp = file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, file)

def already_alerted(player_name, match_id, file, market=None):
    # If the state file doesn't exist yet, nothing has been alerted.
    try:
        if not os.path.exists(file):
            return False
        with open(file, "r", encoding="utf-8") as f:
            state = json.load(f) or {}
    except Exception:
        # On any read/parse error treat as not alerted to avoid crashing the loop.
        return False

    alerted = state.get('alerted', {}) if isinstance(state, dict) else {}
    key = f"{match_id}_{player_name}"
    if market:
        key = f"{key}_{market}"
    return key in alerted

# ========= MAIN LOOP =========
def main():
    betfair = Betfair()
    clear_cache()
    active_comps = betfair.get_active_whitelisted_competitions()   
    # Record the start date (London timezone). If the date changes during a run
    # we exit so a daily cron can restart a fresh process.
    run_start_date = datetime.now(london).date()
    
    # Load persistent run counter
    run_number = load_run_counter()
    print(f"[INIT] Starting from run #{run_number + 1}")
    
    while True:
        run_number += 1
        save_run_counter(run_number)  # Persist immediately
        loop_start = time.time()
        print(f"\n{'='*80}")
        print(f"Starting run #{run_number}")
        print(f"{'='*80}")
        # If the local date (Europe/London) has changed since the process started,
        # exit so the cron job can restart a fresh run for the new day.
        if datetime.now(london).date() != run_start_date:
            print(f"Local date changed from {run_start_date} to {datetime.now(london).date()}; exiting for daily restart")
            return
        
        total_matches_checked = 0
        total_players_processed = 0
        
        for comp in active_comps:
            cid = comp.get('comp_id',0)
            cname = comp.get('comp_name')
            comp_start = time.time()
            try:
                matches = betfair.fetch_matches_for_competition(cid)
            except Exception as e:
                print(f"  Error fetching matches for {cid}: {e}")
                continue
            comp_fetch_time = time.time() - comp_start
            if comp_fetch_time > 2:
                print(f"[TIMING] Fetching matches for {cname} took {comp_fetch_time:.2f}s")
            
            if not matches:
                #No upcoming matches found for this competition
                continue

            for m in matches:
                total_matches_checked += 1
                mid = m.get('id')
                mname = m.get('name')
                kickoff = m.get('openDate')
                print(f"  - {mid}: {mname} @ {kickoff}")
                # If the match is today (UTC), fetch odds for the TO_SCORE market

                if kickoff:
                    kt = datetime.fromisoformat(kickoff.replace('Z', '+00:00'))
                    ko_str = kt.strftime("%H:%M")
                    now_utc = datetime.now(timezone.utc)
                    # consider matches within the next x minutes (inclusive)
                    # compute minutes until kickoff and respect WINDOW_MINUTES
                    minutes_until = (kt - now_utc).total_seconds() / 60.0
                    if 0 <= minutes_until <= WINDOW_MINUTES:
                        print(f"    -> Match within next {WINDOW_MINUTES} minutes; fetching odds... (in {minutes_until:.1f}m)")
                        # If the fetch_matches_for_competition response included market_nodes with TO_SCORE markets,
                        # call _fetch_market_odds directly using the known market id(s).
                        mnodes = m.get('market_nodes') or []
                        if mnodes:
                            # Fetch site mappings and exchange odds once per match
                            target_sites = ['virginbet', 'williamhill']
                            if ENABLE_LADBROKES:
                                target_sites.append('ladbrokes')
                            mappings, oddsmatcha_match_id = map_betfair_to_sites(mid, target_sites)
                            # Hardcoded Ladbrokes mappings: oddsmatcha_id -> ladbrokes_id
                            try:
                                ladb_map = {
                                    3642: '253829365',
                                    3643: '253829371',
                                    3613: '253829368',
                                    3614: '253829369',
                                    3615: '253829366',
                                    3616: '253829370',
                                    3644: '253829367',
                                    3617: '253829372',
                                    3645: '253829373',
                                    3618: '253792159',
                                    3663: '253818695'
                                }
                                key = None
                                try:
                                    key = int(oddsmatcha_match_id) if oddsmatcha_match_id is not None else None
                                except Exception:
                                    key = None
                                if key in ladb_map:
                                    mappings = dict(mappings or {})
                                    mappings['ladbrokes'] = ladb_map[key]
                                    print(f"[LADBROKES] Applied hardcoded mapping for oddsmatcha {key} -> {ladb_map[key]}")
                            except Exception:
                                pass
                            exchange_odds = {}
                            confirmed_starters = set()
                            if oddsmatcha_match_id:
                                # Optionally fetch additional exchange odds for debugging/augmentation
                                if ENABLE_ADDITIONAL_EXCHANGES:
                                    exchange_odds = fetch_exchange_odds(oddsmatcha_match_id)
                                    if exchange_odds:
                                        total_exchange_players = sum(len(players) for players in exchange_odds.values())
                                        print(f"    [EXCHANGE] Loaded odds for {total_exchange_players} players from alternative exchanges")
                                        # Output detailed exchange odds by market and player
                                        for market_type, players_dict in exchange_odds.items():
                                            for player_name, odds_list in players_dict.items():
                                                for odd in odds_list:
                                                    site_name = odd.get('site_name', 'Unknown')
                                                    lay_odds = odd.get('lay_odds', 'N/A')
                                                    liquidity = odd.get('liquidity', 'None')
                                                    liquidity_str = f"£{int(liquidity)}" if liquidity else "None"
                                                    print(f"      - {player_name} ({market_type}): {site_name} @ {lay_odds} (Liquidity: {liquidity_str})")

                                # Fetch confirmed starters (lineups) regardless of exchanges
                                confirmed_starters = fetch_lineups(oddsmatcha_match_id)
                                print(f"    [DEBUG] Confirmed starters fetched: {len(confirmed_starters)} players - {confirmed_starters}")
                            
                            # Fetch OddsChecker match slug once per match (for ARB alerts)
                            match_slug = None
                            if ENABLE_ODDSCHECKER:
                                match_slug = get_oddschecker_match_slug(mid)
                                if match_slug:
                                    print(f"    [OC] Match slug: {match_slug}")
                            
                            # Initialize WH client once per match if enabled
                            wh_client = None
                            wh_match_id = mappings.get('williamhill')
                            wh_offer_checked = False
                            
                            # Only fetch WH prices if we have lineup data
                            if ENABLE_WILLIAMHILL and wh_match_id and confirmed_starters:
                                
                                if wh_match_id:
                                    # Check if match is in the WH offer
                                    if is_match_in_wh_offer(wh_match_id):
                                        wh_offer_checked = True
                                        try:
                                            from willhill_betbuilder import BetBuilderClient
                                            wh_client = BetBuilderClient()
                                            if not wh_client.load_event(wh_match_id):
                                                print(f"Failed to load WH event {wh_match_id}")
                                                wh_client = None
                                            else:
                                                print(f"[WH] Loaded event {wh_match_id} for reuse across players")
                                                
                                                # Fetch and track base WH goalscorer odds
                                                base_odds = get_wh_base_goalscorer_odds(wh_client, wh_match_id)
                                                changed_base_markets = set()
                                                if base_odds:
                                                    print(f"[WH] Fetched {len(base_odds)} base goalscorer odds")
                                                    changed_base_markets = track_wh_base_odds(wh_match_id, mname, base_odds, run_number=run_number)
                                        except Exception as e:
                                            print(f"Error loading WH client: {e}")
                                            wh_client = None
                                    else:
                                        print(f"Match {wh_match_id} not in WH offer; skipping all WH checks for this match")
                                else:
                                    print(f"No WH mapping for Betfair {mid}; skipping all WH checks for this match")
                            
                            # build supported_markets mapping from nodes
                            # Initialize Ladbrokes client once per match if enabled
                            ladbrokes_client = None
                            ladbrokes_match_id = mappings.get('ladbrokes')
                            if ENABLE_LADBROKES and ladbrokes_match_id and LadbrokesAlerts is not None:
                                try:
                                    ladbrokes_client = LadbrokesAlerts()
                                    print(f"[LADBROKES] Initialized client for match {ladbrokes_match_id}")
                                except Exception as e:
                                    print(f"Failed to init Ladbrokes client: {e}")
                            supported = {}
                            for node in mnodes:
                                desc = node.get('description', {}) if isinstance(node, dict) else {}
                                mtype = desc.get('marketType') or node.get('marketType') or ''
                                midid = node.get('marketId') or node.get('market_id') or node.get('marketId')
                                if (mtype == betfair.FGS_MARKET_NAME or mtype == betfair.AGS_MARKET_NAME) and midid:
                                    if mtype == betfair.FGS_MARKET_NAME:    
                                        supported[mtype] = {'market_id': midid, 'market_name': desc.get('marketName', ''), 'internal_market_name': 'FGS'}
                                    else:
                                        supported[mtype] = {'market_id': midid, 'market_name': desc.get('marketName', ''), 'internal_market_name': 'AGS'}
                                    # call _fetch_market_odds for this market id
                                    try:
                                        betfair_odds = betfair._fetch_market_odds(str(midid), supported, m)
                                    except Exception as e:
                                        print(f"    Error fetching market {midid}: {e}")
                                        betfair_odds = []
                                    
                                    # Combine Betfair and exchange odds
                                    market_type = 'First Goalscorer' if mtype == betfair.FGS_MARKET_NAME else 'Anytime Goalscorer'
                                    all_odds = combine_betfair_and_exchange_odds(betfair_odds, exchange_odds, market_type)
                                    
                                    # Group odds by player name to collect all exchanges for each player
                                    player_odds_map = {}
                                    for odd_entry in all_odds:
                                        pname = odd_entry['player_name']
                                        if pname not in player_odds_map:
                                            player_odds_map[pname] = []
                                        player_odds_map[pname].append(odd_entry)
                                    
                                    # Process each player (only once, with all their exchange odds)
                                    for pname, player_exchanges in player_odds_map.items():
                                        total_players_processed += 1
                                        
                                        # Find the best (lowest) lay odds and largest size for threshold checks
                                        best_odds = min(player_exchanges, key=lambda x: x['lay_odds'])
                                        price = best_odds['lay_odds']
                                        lay_size = best_odds['lay_size']
                                        has_size = best_odds['has_size']
                                        
                                        # Collect all exchange lay prices for display
                                        all_lay_prices = []
                                        for exchange in player_exchanges:
                                            site = exchange['site']
                                            odds = exchange['lay_odds']
                                            size = exchange['lay_size']
                                            if exchange['has_size']:
                                                all_lay_prices.append(f"{site} @ {odds} (£{int(size)})")
                                            else:
                                                all_lay_prices.append(f"{site} @ {odds}")
                                        lay_prices_text = " | ".join(all_lay_prices)
                                        
                                        # GOOSE ALERTS (only for Betfair with size and confirmed starters)
                                        if ENABLE_VIRGIN_GOOSE and mtype == betfair.AGS_MARKET_NAME and has_size and lay_size >= GBP_THRESHOLD_GOOSE:
                                            skip = False
                                            if price < GOOSE_MIN_ODDS:
                                                skip = True
                                            virgin_id = mappings.get('virginbet')
                                            if not virgin_id:
                                                skip = True
                                            if already_alerted(pname,mid,GOOSE_STATE_FILE):
                                                skip = True
                                            # Only alert if player is a confirmed starter
                                            if confirmed_starters and not is_confirmed_starter(pname, confirmed_starters):
                                                skip = True
                                                print(f"      [DEBUG] {pname} is NOT a confirmed starter - skipping GOOSE alert")
                                            if not skip:
                                                virgin_markets = getVirginMarkets(virgin_id)
                                                player_data = find_player_sot_and_ga_ids(virgin_markets, pname)
                                                if player_data:
                                                    combo_odds = getGoosedCombos({'id': virgin_id}, player_data)  
                                                    '''
                                                    [{'match_id': 'SBTE_2_1024825599', 'player_name': 'Morgan Gibbs-White', 'odds': 2.23, 'bet_type': 'AGS', 'bet_request_json': {'selections': [{'id': 'SBTS_2_3950170697', 'eachWay': False}, {'id': 'SBTS_2_3950170555', 'eachWay': False}], 'oddsFormat': 'DECIMAL', 'selectionGroups': [{'id': 10, 'selections': ['SBTS_2_3950170697', 'SBTS_2_3950170555']}], 'betTypes': [{'type': 'YOURBET'}]}, 'updated_at': '2025-11-27T11:26:20.755707+00:00'}]
                                                    '''
                                                    # `getGoosedCombos` returns a list of result dicts.
                                                    # Safely handle that shape and print the odds from the first result.
                                                    
                                                    if combo_odds:
                                                        if isinstance(combo_odds, list):
                                                            try:
                                                                back_odds = combo_odds[0].get('odds',0)
                                                            except Exception:
                                                                print('Combo Odds (raw list):', combo_odds)
                                                        elif isinstance(combo_odds, dict):
                                                            back_odds = combo_odds.get('odds',0)
                                                        else:
                                                            print('Combo Odds (raw):', combo_odds)
                                                        print(f"Player: {player_data['name']} | Back Odds: {back_odds} | Lay Odds: {price}")
                                                    else:
                                                        print('Combo Odds: no result')

                                                    if (back_odds+TEST_PRICE_OFFSET) > price:
                                                        rating = round(back_odds / price * 100, 2)
                                                        title = f"{pname} - {back_odds}/{price} ({rating}%)"
                                                        
                                                        # Build description with optional Confirmed Starter
                                                        starter_line = ""
                                                        if confirmed_starters and is_confirmed_starter(pname, confirmed_starters):
                                                            starter_line = "\nConfirmed Starter ✅"
                                                        
                                                        desc = f"**{mname}** ({ko_str})\n{cname}{starter_line}\n\n**Lay Prices:** {lay_prices_text}\n[Betfair Market](https://www.betfair.com/exchange/plus/football/market/{midid})"
                                                        #There is an arb here

                                                        '''
                                                            [{'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.6, 'bookie': 'Bet365'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Boylesports'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.9, 'bookie': 'Coral'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.4, 'bookie': 'Betfred'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.9, 'bookie': 'Ladbrokes'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Paddy Power'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.9, 'bookie': 'QuinnBet'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Sky Bet'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Unibet'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Bet Victor'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.75, 'bookie': 'William Hill'}]
                                                        '''
                            

                                                        fields = []
                                                        
                                                        # Add confirmed starter field if applicable
                                                        is_confirmed = confirmed_starters and is_confirmed_starter(pname, confirmed_starters)
                                                        if is_confirmed:
                                                            fields.append(("Confirmed Starter", "✅"))
                                                            print(f"      [DEBUG] {pname} IS a confirmed starter - field added to embed")
                                                        else:
                                                            print(f"      [DEBUG] {pname} is NOT a confirmed starter - field NOT added (confirmed_starters={bool(confirmed_starters)})")
                                                                                
                                                        embed_colour = 0xFF0000  # bright red for true arb
                                                        #print("ARBING")
                                                        if DISCORD_GOOSE_CHANNEL_ID:
                                                            #print("SENDING")
                                                            send_discord_embed(title, desc, fields, colour=embed_colour, channel_id=DISCORD_GOOSE_CHANNEL_ID,footer=f"{pname} Goal/Assist + SOT",icon=GOOSE_FOOTER_ICON_URL)
                                                        save_state(pname,mid, GOOSE_STATE_FILE)
                                        # ARB ALERTS
                                        if ENABLE_ODDSCHECKER and (not has_size or lay_size > GBP_ARB_THRESHOLD):
                                            if mtype == betfair.FGS_MARKET_NAME:
                                                bettype = "First Goalscorer"
                                                label = "FGS"
                                            elif mtype == betfair.AGS_MARKET_NAME:
                                                bettype = "Anytime Goalscorer"
                                                label = "AGS"
                                            if already_alerted(pname,mid,ARB_STATE_FILE, market=label):
                                                continue
                                            
                                            # Use pre-fetched match slug (fetched once per match)
                                            if not match_slug:
                                                continue
                                            
                                            # BUILD THE JSON FOR THIS BET ['First Goalscorer','Anytime Goalscorer']
                                            betfair_lay_bet = [{"bettype": bettype, "outcome": pname, "lay_odds": price}]
                                            arb_opportunities = get_oddschecker_odds(match_slug, betfair_lay_bet)

                                            # Send separate arbitrage message if configured
                                            if arb_opportunities and DISCORD_ARB_CHANNEL_ID:
                                                # Calculate max OddsChecker odds for title
                                                max_oc_odds = max(arb['odds'] for arb in arb_opportunities) if arb_opportunities else 0
                                                rating_pct = (max_oc_odds / price * 100)
                                                arb_title = f"{pname} ({label}) - {max_oc_odds:.2f}/{price:.2f} ({rating_pct:.1f}%)"
                                                arb_fields = [
                                                    ("Back Sites", "\n".join([f"{arb['bookie']} @ {arb['odds']:.2f}" for arb in arb_opportunities])),
                                                    ("BFEX Link", f"[Open Market](https://www.betfair.com/exchange/plus/football/market/{midid})"),
                                                ]
                                                
                                                # Build description with optional Confirmed Starter
                                                starter_line = ""
                                                if confirmed_starters and is_confirmed_starter(pname, confirmed_starters):
                                                    starter_line = "\nConfirmed Starter ✅"
                                                
                                                desc = f"**{mname}** ({ko_str})\n{cname}{starter_line}\n\n**Lay Prices:** {lay_prices_text}"
                                                        
                                                # Add confirmed starter field if applicable
                                                if confirmed_starters and is_confirmed_starter(pname, confirmed_starters):
                                                    arb_fields.append(("Confirmed Starter", "✅"))
                                                
                                                if match_slug:
                                                    arb_fields.append(("OC Link", f"[View OC](https://www.oddschecker.com/football/{match_slug})"))
                                                if DISCORD_ARB_CHANNEL_ID:
                                                    send_discord_embed(arb_title, desc, arb_fields, colour=0xFFB80C, channel_id=DISCORD_ARB_CHANNEL_ID)
                                                save_state(f"{pname}_{label}",mid, ARB_STATE_FILE)
                                        # WILLIAM HILL ALERTS
                                        # Reuse the WH client initialized for this match
                                        if wh_client and (not has_size or lay_size > GBP_WH_THRESHOLD):
                                            if mtype == betfair.FGS_MARKET_NAME:
                                                bettype = "First Goalscorer"
                                                label = "FGS"
                                            elif mtype == betfair.AGS_MARKET_NAME:
                                                bettype = "Anytime Goalscorer"
                                                label = "AGS"
                                            else:
                                                continue
                                            
                                            print(f"[WH] Checking {pname} {label} (Lay @ {price})")
                                            
                                            if already_alerted(pname, wh_match_id, WH_STATE_FILE, market=label):
                                                continue
                                            
                                            # GET WILLIAM HILL BB ODDS HERE
                                            betfair_lay_bet = [{"bettype": bettype, "outcome": pname, "lay_odds": price}]
                                            try:
                                                combos = wh_client.get_player_combinations(
                                                    player_name=pname,
                                                    template_name=bettype,
                                                    get_price=False  # Get combo first without price
                                                )
                                                
                                                if not combos:
                                                    print(f"[WH] No combos found for {pname} {label}")
                                                    continue
                                                
                                                combo = combos[0]
                                                if not combo.get('success'):
                                                    error_msg = combo.get('error', 'Unknown error')
                                                    print(f"[WH] Combo unsuccessful for {pname} {label}: {error_msg}")
                                                    continue
                                                
                                                # Determine if we should fetch price based on mode
                                                should_fetch_price = False
                                                force_refresh = False
                                                
                                                if WH_PRICING_MODE == 1:
                                                    # Mode 1: Only fetch if no cache OR base odds changed
                                                    base_changed = (pname, label) in changed_base_markets
                                                    has_cache = wh_client.generator.has_cached_price(combo)
                                                    
                                                    if base_changed:
                                                        should_fetch_price = True
                                                        force_refresh = True
                                                        print(f"[WH MODE1] Base odds changed for {pname} {label} - forcing fresh price lookup")
                                                    elif not has_cache:
                                                        should_fetch_price = True
                                                        force_refresh = False
                                                        print(f"[WH MODE1] No cached price for {pname} {label} - fetching price")
                                                    else:
                                                        print(f"[WH MODE1] Using cached price for {pname} {label} (base odds unchanged)")
                                                else:
                                                    # Mode 2: Always fetch with 5-minute cache timeout (existing behavior)
                                                    should_fetch_price = True
                                                    force_refresh = False
                                                    print(f"[WH MODE2] Fetching price for {pname} {label} (5-min cache)")
                                                
                                                if not should_fetch_price:
                                                    continue
                                                
                                                price_data = wh_client.get_combination_price(combo, use_cache=(not force_refresh))
                                                
                                                if price_data and price_data.get('success'):
                                                    wh_odds = price_data.get('odds',0)
                                                    original_wh_odds = wh_odds
                                                    boosted_odds = wh_odds
                                                    
                                                    if float(wh_odds) >= 4:
                                                        # Boosting odds by 25%
                                                        boosted_odds = round(((float(wh_odds)-1) * 1.25) + 1, 2)
                                                        print(f"[WH] {pname} {label}: WH odds {original_wh_odds} boosted to {boosted_odds} vs Lay {price}")
                                                    else:
                                                        print(f"[WH] {pname} {label}: WH @ {wh_odds} vs Lay @ {price}")
                                                    
                                                    # Track odds for analysis (includes combo details)
                                                    track_wh_odds(
                                                        match_id=wh_match_id,
                                                        match_name=mname,
                                                        player_name=pname,
                                                        market_type=label,
                                                        wh_odds=original_wh_odds,
                                                        boosted_odds=boosted_odds,
                                                        lay_odds=price,
                                                        combo_data=combo if combo else None,
                                                        run_number=run_number
                                                    )
                                                    
                                                    # Send separate WH message if configured
                                                    if DISCORD_WH_CHANNEL_ID:
                                                        # Require lineup confirmation before sending WH alert
                                                        if not confirmed_starters:
                                                            print(f"[WH] Skipping alert for {pname} - no lineup data available")
                                                        elif not is_confirmed_starter(pname, confirmed_starters):
                                                            print(f"[WH] Skipping alert for {pname} - not in confirmed starters")
                                                        else:
                                                            if boosted_odds >= float(betfair_lay_bet[0]['lay_odds']):
                                                                rating = round(boosted_odds / price * 100, 2)
                                                                title = f"{pname} - {label} - {boosted_odds}/{price} ({rating}%)"

                                                                desc = f"**{mname}** ({ko_str})\n{cname}\n\n**Lay Prices:** {lay_prices_text}\n[Betfair Market](https://www.betfair.com/exchange/plus/football/market/{midid})"
                                                                fields = []

                                                                # Add confirmed starter field if applicable
                                                                if confirmed_starters and is_confirmed_starter(pname, confirmed_starters):
                                                                    fields.append(("Confirmed Starter", "✅"))
                                                                #build footer
                                                                if label == "FGS":
                                                                    footer_text = f"{pname} FGS + AGS + Over 0.5 Goals"
                                                                elif label == "AGS":
                                                                    footer_text = f"{pname} AGS + G/A + Over 0.5 Goals"
                                                                send_discord_embed(title, desc, fields, colour=0x00143C, channel_id=DISCORD_WH_CHANNEL_ID, footer=footer_text)
                                                                save_state(f"{pname}_{label}", wh_match_id, WH_STATE_FILE)
                                                                print(f"[WH ALERT] {pname} {label} @ {boosted_odds} (rating: {rating}%)")
                                                            
                                                            # Send Smarkets-only alert if configured and Smarkets lay is available
                                                            if DISCORD_WH_SMARKETS_CHANNEL_ID and not already_alerted(f"{pname}_{label}", wh_match_id, WH_SMARKETS_STATE_FILE):
                                                                # Check if Smarkets lay price is available
                                                                has_smarkets = False
                                                                smarkets_price = None
                                                                smarkets_liquidity = None
                                                                
                                                                for exchange in player_exchanges:
                                                                    if exchange['site'].lower() == 'smarkets':
                                                                        has_smarkets = True
                                                                        smarkets_price = exchange['lay_odds']
                                                                        smarkets_liquidity = exchange['lay_size']
                                                                        break
                                                                
                                                                if has_smarkets and boosted_odds >= smarkets_price:
                                                                    # Build Smarkets-only description (no Betfair mention)
                                                                    smarkets_lay_text = f"Smarkets @ {smarkets_price}"
                                                                    if smarkets_liquidity:
                                                                        smarkets_lay_text += f" (£{int(smarkets_liquidity)})"
                                                                    
                                                                    rating_sm = round(boosted_odds / smarkets_price * 100, 2)
                                                                    title_sm = f"{pname} - {label} - {boosted_odds}/{smarkets_price} ({rating_sm}%)"
                                                                    desc_sm = f"**{mname}** ({ko_str})\n{cname}\nConfirmed Starter ✅\n\n**Lay Price:** {smarkets_lay_text}"
                                                                    
                                                                    fields_sm = [("Confirmed Starter", "✅")]
                                                                    
                                                                    # Use same footer as main WH alert
                                                                    footer_text_sm = footer_text
                                                                    
                                                                    send_discord_embed(title_sm, desc_sm, fields_sm, colour=0x00143C, 
                                                                                     channel_id=DISCORD_WH_SMARKETS_CHANNEL_ID, 
                                                                                     footer=footer_text_sm,
                                                                                     bot_token=DISCORD_BOT_TOKEN_SMARKETS)
                                                                    save_state(f"{pname}_{label}", wh_match_id, WH_SMARKETS_STATE_FILE)
                                                                    print(f"[WH SMARKETS ALERT] {pname} {label} @ {boosted_odds} vs Smarkets @ {smarkets_price} (rating: {rating_sm}%)")
                                                            
                                                            else:
                                                                print(f"[WH] No alert - WH odds {boosted_odds} < Lay {price}")
                                                else:
                                                    print(f"[WH] Failed to get price for {pname} {label}")
                                                    continue
                                                        
                                            except Exception as e:
                                                print(f"Error getting WH odds: {e}")
                                                traceback.print_exc()
                                                continue
        
                                                            # Also attempt Ladbrokes combos if configured
                                        if ENABLE_LADBROKES and 'ladbrokes_client' in locals() and ladbrokes_client and ladbrokes_match_id:

                                            lb = get_ladbrokes_player_combos(ladbrokes_client, ladbrokes_match_id, pname)
                                            if lb:
                                                if mtype == betfair.FGS_MARKET_NAME:
                                                    bettype = "First Goalscorer"
                                                    label = "FGS"
                                                    odds = lb.get('fgs_combo',0)
                                                elif mtype == betfair.AGS_MARKET_NAME:
                                                    bettype = "Anytime Goalscorer"
                                                    label = "AGS"
                                                    odds = lb.get('ags_combo',0)
                                                else:
                                                    continue
                                                #print(f"  [LADBROKES] {pname} - AGS(combo): {lb.get('ags_combo')} | FGS+AGS(combo): {lb.get('fgs_combo')}")
                                                
                                                betfair_lay_bet = [{"bettype": bettype, "outcome": pname, "lay_odds": price}]
                                                if already_alerted(pname, ladbrokes_match_id, LADBROKES_STATE_FILE, market=label):
                                                    continue
                                                if DISCORD_LADBROKES_CHANNEL_ID:
                                                    #print(betfair_lay_bet)
                                                    print(f"Comparison: {pname} {label} - Ladbrokes Odds: {odds} vs Lay Odds: {price}")
                                                    # Handle None/non-numeric odds safely
                                                    try:
                                                        valid_odds = isinstance(odds, (int, float))
                                                        valid_price = isinstance(price, (int, float)) and price > 0
                                                    except Exception:
                                                        valid_odds = valid_price = False
                                                    if valid_odds and valid_price and odds >= price:
                                                        # ensure lineup confirmation before sending Ladbrokes alert
                                                        if not confirmed_starters:
                                                            print(f"[LAD] Skipping alert for {pname} - no lineup data available")
                                                        elif not is_confirmed_starter(pname, confirmed_starters):
                                                            print(f"[LAD] Skipping alert for {pname} - not in confirmed starters")
                                                        else:
                                                            # compute rating defensively
                                                            try:
                                                                rating = round(odds / price * 100, 2)
                                                            except Exception:
                                                                rating = 0
                                                            title = f"[LAD] {pname} - {label} - {odds}/{price} ({rating}%)"

                                                            # Build description with optional Confirmed Starter
                                                            starter_line = "\nConfirmed Starter ✅"

                                                            desc = f"**{mname}** ({ko_str})\n{cname}{starter_line}\n\n**Lay Prices:** {lay_prices_text}\n[Betfair Market](https://www.betfair.com/exchange/plus/football/market/{midid})"
                                                            fields = []

                                                            # Add confirmed starter field
                                                            fields.append(("Confirmed Starter", "✅"))
                                                            #build footer
                                                            if label == "FGS":
                                                                footer_text = f"{pname} FGS + AGS"
                                                            elif label == "AGS":
                                                                footer_text = f"{pname} AGS + Over 0.5 Goals"
                                                            send_discord_embed(title, desc, fields, colour=0x00143C, channel_id=DISCORD_LADBROKES_CHANNEL_ID, footer=footer_text)
                                                            save_state(f"{pname}_{label}", ladbrokes_match_id, LADBROKES_STATE_FILE)



        loop_time = time.time() - loop_start
        print(f"[TIMING] Loop completed in {loop_time:.2f}s - {total_matches_checked} matches, {total_players_processed} players")
        print(f"Sleeping for {POLL_SECONDS}s...")
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
