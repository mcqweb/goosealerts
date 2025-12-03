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

# ========= INITIALIZATION =========

load_dotenv()
london = pytz.timezone("Europe/London")
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEBUG_DIR = os.path.join(BASE_DIR, 'debug')
os.makedirs(DEBUG_DIR, exist_ok=True)

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
# ========= CONFIG =========
GBP_THRESHOLD_GOOSE  = float(os.getenv("GBP_THRESHOLD_GOOSE", "10"))
GBP_ARB_THRESHOLD = float(os.getenv("GBP_ARB_THRESHOLD", "10"))
GOOSE_MIN_ODDS      = float(os.getenv("GOOSE_MIN_ODDS", "1.2"))  # min odds for goose combos
WINDOW_MINUTES   = int(os.getenv("WINDOW_MINUTES", "90"))    # KO window
POLL_SECONDS      = int(os.getenv("POLL_SECONDS", "60"))    # How long should each loop wait
VIRGIN_ODDS_CACHE_DURATION = int(os.getenv("VIRGIN_ODDS_CACHE_DURATION", "300"))  # seconds to cache AGS combo responses

# ========= DISCORD =========
def send_discord_embed(title, description, fields, colour=0x3AA3E3, channel_id=None, footer=None):
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
        embed["footer"] = {
            "text": footer, # Use the string passed to the function
            "icon_url": 'https://img.icons8.com/?size=100&id=CXvbGFYLkaMY&format=png&color=000000'
        }
    
    # --- 3. Add the timestamp if a footer wasn't provided (as per your original logic) ---
    else:
        # Note: Discord recommends using 'timestamp' as a top-level key for the embed
        embed["timestamp"] = datetime.now(london).isoformat()
    payload = {"embeds": [embed], "content": ""}


    if not DISCORD_BOT_TOKEN:
        print(f"[WARN] Discord not configured. Token set={bool(DISCORD_BOT_TOKEN)} channels={channel_id}")
        return

    try:
        r = requests.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}",
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
    cache_dir = os.path.join(BASE_DIR, 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    match_id = match.get('id') if isinstance(match, dict) else str(match)
    ga_id = str(player_data.get('ga_id')) if player_data else 'unknown'
    sot_id = str(player_data.get('sot_id')) if player_data else 'unknown'
    cache_file = os.path.join(cache_dir, f"virgin_combo_{match_id}_{ga_id}_{sot_id}.json")

    body = None
    # Try load cache
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            ts = float(cached.get('ts', 0))
            if time.time() - ts <= VIRGIN_ODDS_CACHE_DURATION:
                body = cached.get('body')
                print("Using Cached Odds")
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

        text_snip = None
        try:
            text_snip = (resp.text or '')[:1000]
        except Exception:
            text_snip = '<no-body>'
            print('Error parsing AGS combo JSON response:', e)
            print('Response status:', getattr(resp, 'status_code', None), 'body_snippet:', text_snip)
            return back_odds_results

    # Ensure expected structure exists
    data_obj = body.get('data') if isinstance(body, dict) else None
    if not data_obj:
        print('AGS combo response missing "data" key. Status:', getattr(resp, 'status_code', None))
        # show a short snippet to help debugging
        try:
            print('Response snippet:', json.dumps(body)[:800])
        except Exception:
            try:
                print('Response text snippet:', (resp.text or '')[:800])
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
   
def map_betfair_to_virgin(betfair_id):
    """Call the oddsmatcha API to map a Betfair match id to a VirginBet id.

    Returns the first conversion dict on success or None.
    """
    try:
        api = f"https://api.oddsmatcha.uk/convert/site_to_site?source_site=betfair&source_match_ids={betfair_id}&target_site=virginbet"
        resp = requests.get(api, timeout=10)
        if not resp.ok:
            print(f"Mapping API returned {resp.status_code} for Betfair {betfair_id}")
            return None
        data = resp.json()
        if data.get('success') and data.get('conversions'):
            conv = data['conversions'][0]
            return conv
        print(f"Mapping API returned no conversion for Betfair {betfair_id}")
        return None
    except Exception as e:
        print(f"Error calling mapping API for Betfair {betfair_id}: {e}")
        return None

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

def already_alerted(player_name, match_id, file):
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
    return key in alerted

# ========= MAIN LOOP =========
def main():
    betfair = Betfair()
    clear_cache()
    active_comps = betfair.get_active_whitelisted_competitions()   
    # Record the start date (London timezone). If the date changes during a run
    # we exit so a daily cron can restart a fresh process.
    run_start_date = datetime.now(london).date()
    while True:
        # If the local date (Europe/London) has changed since the process started,
        # exit so the cron job can restart a fresh run for the new day.
        if datetime.now(london).date() != run_start_date:
            print(f"Local date changed from {run_start_date} to {datetime.now(london).date()}; exiting for daily restart")
            return
        for comp in active_comps:
            cid = comp.get('comp_id',0)
            cname = comp.get('comp_name')
            try:
                matches = betfair.fetch_matches_for_competition(cid)
            except Exception as e:
                print(f"  Error fetching matches for {cid}: {e}")
                continue
            if not matches:
                #No upcoming matches found for this competition
                continue

            for m in matches:
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
                    if now_utc <= kt <= now_utc + timedelta(minutes=WINDOW_MINUTES):
                        print(f"    -> Match within next {WINDOW_MINUTES} minutes; fetching odds...")
                        # If the fetch_matches_for_competition response included market_nodes with TO_SCORE markets,
                        # call _fetch_market_odds directly using the known market id(s).
                        mnodes = m.get('market_nodes') or []
                        if mnodes:
                            # build supported_markets mapping from nodes
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
                                        odds = betfair._fetch_market_odds(str(midid), supported, m)
                                    except Exception as e:
                                        print(f"    Error fetching market {midid}: {e}")
                                        odds = []
                                    if odds:
                                        for o in odds:
                                            pname = o.get('outcome',"")
                                            price = o.get('odds',0)
                                            lay_size = float(o.get('size', 0))
                                            mkt = o.get('market') or o.get('market_type')
                                            if mtype == betfair.AGS_MARKET_NAME and lay_size >= GBP_THRESHOLD_GOOSE:
                                                skip = False
                                                if price < GOOSE_MIN_ODDS:
                                                    skip = True
                                                if already_alerted(pname,mid,GOOSE_STATE_FILE):
                                                    print(f"Already alerted for {pname} in match {mid}; skipping")
                                                    skip = True
                                                conv = map_betfair_to_virgin(mid)
                                                if not conv:
                                                    print(f"No mapping for Betfair {mid}; skipping this outcome")
                                                    skip = True
                                                virgin_id = conv.get('target_id')
                                                if not virgin_id:
                                                    print(f"Mapping for Betfair {mid} missing 'target_id': {conv}; skipping")
                                                    skip = True
                                                # print("Virgin ID:", virgin_id)
                                                # print("Player:", pname)
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
                                                            desc = f"**{mname}** ({ko_str})\n{cname}\n\n£{int(lay_size)} available to [lay at {price}](https://www.betfair.com/exchange/plus/football/market/{mid})"
                                                            #There is an arb here

                                                            '''
                                                                [{'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.6, 'bookie': 'Bet365'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Boylesports'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.9, 'bookie': 'Coral'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.4, 'bookie': 'Betfred'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.9, 'bookie': 'Ladbrokes'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Paddy Power'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.9, 'bookie': 'QuinnBet'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Sky Bet'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Unibet'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Bet Victor'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.75, 'bookie': 'William Hill'}]
                                                            '''
                                

                                                            fields = [
                                                            ]
                                                                                    
                                                            embed_colour = 0xFF0000  # bright red for true arb
                                                            #print("ARBING")
                                                            if DISCORD_GOOSE_CHANNEL_ID:
                                                                #print("SENDING")
                                                                send_discord_embed(title, desc, fields, colour=embed_colour, channel_id=DISCORD_GOOSE_CHANNEL_ID,footer=f"{pname} Goal/Assist + SOT")
                                                            save_state(pname,mid, GOOSE_STATE_FILE)
                                            if lay_size > GBP_ARB_THRESHOLD:
                                                
                                                if already_alerted(pname,mid,ARB_STATE_FILE):
                                                    print(f"Already alerted for {pname} in match {mid}; skipping")
                                                    continue
                                                # GET OC RESULTS
                                                oc_results = []
                                                match_slug = None
                                                match_slug = get_oddschecker_match_slug(mid)
                                                if not match_slug:
                                                    raise Exception("Could not map Betfair ID to OddsChecker slug")
                                                # BUILD THE JSON FOR THIS BET ['First Goalscorer','Anytime Goalscorer']
                                                if mtype == betfair.FGS_MARKET_NAME:
                                                    bettype = "First Goalscorer"
                                                    label = "FGS"
                                                elif mtype == betfair.AGS_MARKET_NAME:
                                                    bettype = "Anytime Goalscorer"
                                                    label = "AGS"
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
                                                        ("BFEX Link", f"[Open Market](https://www.betfair.com/exchange/plus/football/market/{mid})"),
                                                    ]
                                                    desc = f"**{mname}** ({ko_str})\n{cname}\n\n£{int(lay_size)} available to [lay at {price}](https://www.betfair.com/exchange/plus/football/market/{mid})"
                                                            
                                                    if match_slug:
                                                        arb_fields.append(("OC Link", f"[View OC](https://www.oddschecker.com/football/{match_slug})"))
                                                    if DISCORD_ARB_CHANNEL_ID:
                                                        send_discord_embed(arb_title, desc, arb_fields, colour=0xFFB80C, channel_id=DISCORD_ARB_CHANNEL_ID)
                                                    save_state(f"{pname}_{label}",mid, ARB_STATE_FILE)
        print("Sleeping...")
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
