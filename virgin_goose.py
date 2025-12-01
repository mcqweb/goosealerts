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
import betfairlightweight
from betfairlightweight import filters
from betfairlightweight.exceptions import APIError

load_dotenv()
london = pytz.timezone("Europe/London")
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

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

# ========= ENV / PATHS =========
def _must(name: str) -> str:
    v = os.getenv(name)
    if not v:
        print(f"[FATAL] Missing env var: {name}", flush=True)
        sys.exit(1)
    return v

APP_KEY  = _must("APP_KEY")        # Betfair App Key
USERNAME = _must("USERNAME")       # Betfair username
PASSWORD = _must("PASSWORD")       # Betfair password

NORD_USER = os.getenv("NORD_USER", "")
NORD_PWD = os.getenv("NORD_PWD", "")
NORD_LOCATION = os.getenv("NORD_LOCATION", "")

DISCORD_BOT_TOKEN   = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_GOOSE_CHANNEL_ID = os.getenv("DISCORD_GOOSE_CHANNEL_ID", "").strip()  # separate channel for goose alerts
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

# Force-monitor specific market IDs (comma separated)
OVERRIDE_INCLUDE_MARKET_IDS = [x.strip() for x in os.getenv("OVERRIDE_INCLUDE_MARKET_IDS", "").split(",") if x.strip()]

CERT_FILE = os.getenv("CERT_FILE", "")
KEY_FILE = os.getenv("KEY_FILE", "")
# Backwards-compatible variable: may point to a directory or a single pem file
CERTS_DIR  = os.getenv("CERTS_DIR", "certs")

STATE_FILE = "state/goose_alert_state.json"
# ========= CONFIG =========
GBP_THRESHOLD_GOOSE  = float(os.getenv("GBP_THRESHOLD_GOOSE", "10"))

TOP_LEVELS       = int(os.getenv("TOP_LEVELS", "1"))         # sum top N lay levels
WINDOW_MINUTES   = int(os.getenv("WINDOW_MINUTES", "900"))    # KO window
POLL_SECONDS     = int(os.getenv("POLL_SECONDS", "180"))     # poll interval
MARKET_BOOK_BATCH= int(os.getenv("MARKET_BOOK_BATCH", "5"))  # fetch N markets per call (keep small)

BATCH_COMP_SIZE  = 5
MAX_RESULTS      = 1000

# ========= DIAGNOSTICS (console-only) =========
DEBUG_MODE       = os.getenv("DEBUG_MODE", "0") == "1"         # enable detailed filter logging
# Log runners that are near the alert threshold across ALL markets (no Discord impact)
DIAG_NEAR_PCT    = float(os.getenv("DIAG_NEAR_PCT", "0"))    # e.g. "0.7" logs >= 70% of threshold; "0" disables
DIAG_MIN_ABS     = float(os.getenv("DIAG_MIN_ABS", "0"))     # absolute floor to log, e.g. "150"
DIAG_EVERY_POLLS = int(os.getenv("DIAG_EVERY_POLLS", "1"))   # log every N polls to reduce spam

# Core domestic & UEFA comps + UEFA WC Qualifiers (Europe)
LEAGUE_NAME_SUBSTRINGS = [
    # Domestic top leagues
    "premier league","english premier","england premier","premiership",
    "ligue 1","french ligue 1","bundesliga","german bund",
    "la liga","spanish la liga","laliga","serie a","italian serie a",
    # UEFA club comps
    "champions league","uefa champions","europa league","uefa europa",
    "conference league","uefa europa conference",
    # UEFA WC Qualifiers (Europe) - common Betfair namings
    "fifa world cup qualifiers (europe)",
    "fifa world cup qualifiers - europe",
    "world cup qualifiers europe",
    "world cup qualifying europe",
    "wc qualifiers europe",
    "wc qualifying europe",
    "wcq europe",
    "wcq uefa",
    "world cup qualifiers uefa",
    "world cup qualifying uefa",
]

# FGS / AGS market type variations
MARKET_TYPE_CODES_AGS = [
    "ANYTIME_GOALSCORER","PLAYER_TO_SCORE","TO_SCORE","GOALSCORER"
]

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
    cache_file = f'{virgin_id}_virgin_markets.json'
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as file:
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
    write_json(event_markets_json, f"virgin_event_{virgin_id}.json")
    if not event_markets_json or 'event' not in event_markets_json:
        print(f"Virgin response for event {virgin_id} contained no 'event' key. Status: {getattr(resp, 'status_code', None)}")
        # Save raw response for debugging
        try:
            write_json({'status_code': getattr(resp, 'status_code', None), 'text': resp.text}, f"virgin_raw_response_{virgin_id}.json")
        except Exception:
            pass
        return []

    event = event_markets_json.get('event')
    if not isinstance(event, dict):
        print(f"Virgin response for event {virgin_id} had null 'event' payload. Status: {getattr(resp, 'status_code', None)}")
        # Save raw response for debugging
        try:
            write_json({'status_code': getattr(resp, 'status_code', None), 'text': resp.text}, f"virgin_raw_response_{virgin_id}.json")
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
    write_json(wanted_markets,cache_file)  
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
def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)

# ========= HELPERS =========
def key_for(mid, sid): return f"{mid}:{sid}"

def within_window(ko_dt, minutes):
    now = datetime.now(timezone.utc)
    return 0 <= (ko_dt - now).total_seconds() / 60 <= minutes

def sum_lay_levels(runner, levels):
    ats = (runner.ex.available_to_lay or [])[:levels] if getattr(runner, "ex", None) else []
    return sum(l.size for l in ats)

def best_back_tuple(r):
    try:
        lvl = (r.ex.available_to_back or [])[0]
        return (lvl.price, lvl.size)
    except Exception:
        return (None, None)

def best_lay_tuple(r):
    try:
        lvl = (r.ex.available_to_lay or [])[0]
        return (lvl.price, lvl.size)
    except Exception:
        return (None, None)

def lay_levels_list(runner, levels):
    """Return list of (price, size) for first N lay levels for diagnostics."""
    if not getattr(runner, "ex", None):
        return []
    lays = runner.ex.available_to_lay or []
    out = []
    for i in range(min(levels, len(lays))):
        lvl = lays[i]
        out.append((lvl.price, lvl.size))
    return out

def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def name_contains(target, needles):
    t = (target or "").lower()
    return any(n in t for n in needles)

def time_range_next_24h_utc():
    now = datetime.now(timezone.utc)
    return filters.time_range(from_=now, to=now + timedelta(hours=48))

def is_ags_name(n):
    n = (n or "").lower()
    return any(p in n for p in [
        "anytime goalscorer","any time goalscorer","to score anytime",
        "player to score","to score","goalscorer"
    ])

# ========= AUTH & ROBUST CALLS =========
def _login_or_die(trading):
    try:
        trading.login()
        print("[AUTH] Login OK", flush=True)
    except Exception as e:
        print(f"[AUTH] Login failed: {e}", flush=True)
        raise

def _safe_discover(trading):
    try:
        comp_ids = discover_competitions(trading)
        return discover_markets(trading, comp_ids), comp_ids
    except APIError as e:
        msg = str(e).upper()
        if "NO_SESSION" in msg or "INVALID_SESSION" in msg:
            print("[AUTH] Session invalid during discovery; re-logging...", flush=True)
            _login_or_die(trading)
            comp_ids = discover_competitions(trading)
            return discover_markets(trading, comp_ids), comp_ids
        raise

def _fetch_books_safely(trading, mids, top_levels):
    price_proj = filters.price_projection(
        price_data=["EX_BEST_OFFERS"],
        ex_best_offers_overrides={"bestPricesDepth": max(1, int(top_levels))},
        virtualise=True,
        rollover_stakes=False,
    )

    def _fetch_chunk(chunk):
        return trading.betting.list_market_book(
            market_ids=chunk,
            price_projection=price_proj
        ) or []

    out = []
    stack = [list(mids)]
    while stack:
        chunk = stack.pop()
        try:
            out.extend(_fetch_chunk(chunk))
        except APIError as e:
            msg = str(e).upper()
            if "TOO_MUCH_DATA" in msg and len(chunk) > 1:
                mid = len(chunk) // 2
                stack.append(chunk[mid:])
                stack.append(chunk[:mid])
            elif "NO_SESSION" in msg or "INVALID_SESSION" in msg:
                print("[AUTH] Session invalid during list_market_book; re-logging...", flush=True)
                _login_or_die(trading)
                out.extend(_fetch_chunk(chunk))
            else:
                raise
    return out

# ========= DISCOVERY =========
def discover_competitions(trading):
    comps = trading.betting.list_competitions(filter=filters.market_filter(event_type_ids=["1"]))
    comp_ids = []
    total_comps = 0
    for c in comps or []:
        comp = c.competition
        name = getattr(comp, "name", "") or ""
        total_comps += 1
        if not comp:
            if DEBUG_MODE:
                print(f"[DEBUG] Filtered out competition (no comp object)", flush=True)
            continue
        low = name.lower()
        if name_contains(low, LEAGUE_NAME_SUBSTRINGS):
            comp_ids.append(comp.id)
        elif DEBUG_MODE:
            print(f"[DEBUG] Filtered out competition: {name} (not in LEAGUE_NAME_SUBSTRINGS)", flush=True)
    # de-dup preserve order
    out, seen = [], set()
    for cid in comp_ids:
        if cid not in seen:
            seen.add(cid); out.append(cid)
    if DEBUG_MODE:
        print(f"[DEBUG] discover_competitions: {total_comps} total → {len(out)} after filtering", flush=True)
    return out

def _catalogue_batch(trading, comp_ids_batch, market_type_codes=None, text_query=None):
    mf = filters.market_filter(
        event_type_ids=["1"],
        competition_ids=comp_ids_batch,
        market_type_codes=market_type_codes,
        text_query=text_query,
        market_start_time=time_range_next_24h_utc(),
        in_play_only=False,
    )
    return trading.betting.list_market_catalogue(
        filter=mf,
        market_projection=["MARKET_START_TIME","RUNNER_METADATA","COMPETITION","EVENT"],
        max_results=MAX_RESULTS
    )

def discover_markets(trading, competition_ids):
    cat = []
    # Pass 1: official market type codes (AGS)
    for batch in chunks(competition_ids, BATCH_COMP_SIZE):
        cat += _catalogue_batch(trading, batch, market_type_codes=MARKET_TYPE_CODES_AGS) or []

    # Pass 2: global name-search fallback if empty
    if not cat:
        AGS_NAME_QUERIES = ["anytime goalscorer", "to score anytime", "player to score"]

        def _global_name_query(q):
            mf = filters.market_filter(
                event_type_ids=["1"],
                text_query=q,
                in_play_only=False,
                market_start_time=time_range_next_24h_utc(),
            )
            return trading.betting.list_market_catalogue(
                filter=mf,
                market_projection=["MARKET_START_TIME", "RUNNER_METADATA", "COMPETITION", "EVENT"],
                max_results=MAX_RESULTS
            ) or []

        for q in AGS_NAME_QUERIES:
            cat += _global_name_query(q)

    # Deduplicate and build mappings
    market_ids, runner_name, comp_name, event_name, kickoff, market_label, event_id = [], {}, {}, {}, {}, {}, {}
    seen = set()
    for c in cat:
        mid = c.market_id
        if mid in seen:
            continue
        seen.add(mid)
        market_ids.append(mid)
        comp_name[mid] = getattr(c.competition, "name", "?")
        event_name[mid] = getattr(c.event, "name", c.market_name)
        kickoff[mid] = c.market_start_time.replace(tzinfo=timezone.utc)
        event_id[mid] = getattr(c.event, "id", None)

        mt = (getattr(c, "market_type", None) or "").upper()
        name = (getattr(c, "market_name", "") or "")
        market_label[mid] = "AGS"

        for r in c.runners or []:
            runner_name[(mid, r.selection_id)] = r.runner_name

    if DEBUG_MODE:
        print(f"[DEBUG] discover_markets: {len(cat)} catalogues → {len(market_ids)} unique markets after filtering", flush=True)
    return market_ids, runner_name, comp_name, event_name, kickoff, market_label, event_id

# ========= MAIN LOOP =========
def main():
    trading = betfairlightweight.APIClient(
        username=USERNAME,
        password=PASSWORD,
        app_key=APP_KEY,
        certs=CERTS_DIR,
    )
    _login_or_die(trading)

    alerted = load_state()
    poll_count = 0

    (market_ids, runner_name, comp_name, event_name, kickoff, market_label, event_id), comp_ids = _safe_discover(trading)

    # Force-include market IDs from env (for debugging/safety/spot checks)
    if OVERRIDE_INCLUDE_MARKET_IDS:
        try:
            # We need catalogue metadata for names; fetch by time window and filter by id
            extra_cats = []
            batch = trading.betting.list_market_catalogue(
                filter=filters.market_filter(event_type_ids=["1"], market_start_time=time_range_next_24h_utc()),
                market_projection=["MARKET_START_TIME","RUNNER_METADATA","COMPETITION","EVENT"],
                max_results=MAX_RESULTS
            ) or []
            ids_set = set(OVERRIDE_INCLUDE_MARKET_IDS)
            extra_cats.extend([c for c in batch if getattr(c, "market_id", "") in ids_set])

            for c in extra_cats:
                mid = c.market_id
                if mid not in market_ids:
                    market_ids.append(mid)
                comp_name[mid] = getattr(c.competition, "name", "?")
                event_name[mid] = getattr(c.event, "name", c.market_name)
                kickoff[mid] = c.market_start_time.replace(tzinfo=timezone.utc)
                mt = (getattr(c, "market_type", None) or "").upper()
                name = (getattr(c, "market_name", "") or "")
                market_label[mid] = "AGS"
                for r in c.runners or []:
                    runner_name[(mid, r.selection_id)] = r.runner_name
                print(comp_name)
        except Exception as e:
            print("[WARN] Failed to force-include market IDs:", e, flush=True)

    print(f"[START] Bot online. Monitoring {len(market_ids)} markets across {len(comp_ids)} competitions (next 24h).", flush=True)
    KEEPALIVE_EVERY = 10
    REFRESH_CATALOGUE_EVERY = 15

    while True:
        poll_count += 1
        print(f"[LOOP] markets={len(market_ids)} poll={poll_count}", flush=True)

        # Clear cache at midnight
        _clear_cache_at_midnight()

        if poll_count % KEEPALIVE_EVERY == 0:
            try:
                trading.keep_alive()
            except Exception as e:
                print("[WARN] keep_alive failed:", e, flush=True)

        if poll_count % REFRESH_CATALOGUE_EVERY == 0 or not market_ids:
            try:
                (market_ids, runner_name, comp_name, event_name, kickoff, market_label, event_id), comp_ids = _safe_discover(trading)
                # Re-apply force include on refresh as well
                if OVERRIDE_INCLUDE_MARKET_IDS:
                    for mid in OVERRIDE_INCLUDE_MARKET_IDS:
                        if mid not in market_ids:
                            market_ids.append(mid)
                print(f"[INFO] Catalogue refresh: {len(market_ids)} markets in scope (next 24h).", flush=True)
            except Exception as e:
                print("[WARN] Catalogue refresh failed:", e, flush=True)

        active = [mid for mid in market_ids if mid in kickoff and within_window(kickoff[mid], WINDOW_MINUTES)]
        # also keep forced IDs active if they have KO known and are within window
        for mid in OVERRIDE_INCLUDE_MARKET_IDS:
            if mid in kickoff and within_window(kickoff[mid], WINDOW_MINUTES) and mid not in active:
                active.append(mid)

        if DEBUG_MODE:
            print(f"[DEBUG] Main loop: {len(market_ids)} markets → {len(active)} within window ({WINDOW_MINUTES} mins)", flush=True)

        if not active:
            time.sleep(POLL_SECONDS)
            continue

        try:
            books = []
            for mids in chunks(active, MARKET_BOOK_BATCH):
                books.extend(_fetch_books_safely(trading, mids, TOP_LEVELS))
        except APIError as e:
            print("[WARN] list_market_book APIError:", e, flush=True)
            time.sleep(POLL_SECONDS)
            continue
        except Exception as e:
            print("[WARN] list_market_book error:", e, flush=True)
            time.sleep(POLL_SECONDS)
            continue

        for mb in books or []:
            mid = mb.market_id
            label = market_label.get(mid, "AGS")
            threshold = GBP_THRESHOLD_GOOSE

            for r in mb.runners or []:
                pname = runner_name.get((mid, r.selection_id), str(r.selection_id))
                k = f"{pname}:{event_id[mid]}"
                if alerted.get(k):
                    if DEBUG_MODE:
                        print(f"[DEBUG] Filtered (already alerted): {mid} | {pname}", flush=True)
                    continue

                lay_size = sum_lay_levels(r, TOP_LEVELS)

                # --- ALERT when crossing threshold ---
                if lay_size >= threshold:
                    pname = runner_name.get((mid, r.selection_id), str(r.selection_id))
                    KO = kickoff[mid]
                    bbp, bbs = best_back_tuple(r)
                    if bbp and bbp < 1.2:
                        continue
                    blp, bls = best_lay_tuple(r)
                    print(f"Lay Stake: £{bls}, Lay Price: {blp}")

                    # GET OC RESULTS
                    oc_results = []
                    match_slug = None
                    virgin_id = map_betfair_to_virgin(event_id[mid])['target_id']
                    print("Virgin ID:", virgin_id)
                    print("Player:", pname)
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
                                    back_odds = combo_odds[0].get('odds')
                                except Exception:
                                    print('Combo Odds (raw list):', combo_odds)
                            elif isinstance(combo_odds, dict):
                                back_odds = combo_odds.get('odds')
                            else:
                                print('Combo Odds (raw):', combo_odds)
                            print(f"Player: {player_data['name']} | Back Odds: {back_odds} | Lay Odds: {blp}")
                        else:
                            print('Combo Odds: no result')
                        if (back_odds+TEST_PRICE_OFFSET) > blp:
                            rating = round(back_odds / blp * 100, 2)
                            title = f"{pname} - {back_odds}/{blp} ({rating}%)"
                            # Format KO as hours:minutes (HH:MM)
                            try:
                                ko_str = KO.strftime("%H:%M") if hasattr(KO, 'strftime') else str(KO)
                            except Exception:
                                ko_str = str(KO)
                            desc = f"**{event_name.get(mid,'?')}** ({ko_str})\n{comp_name.get(mid,'?')}\n\n£{int(lay_size)} available to [lay at {blp}](https://www.betfair.com/exchange/plus/football/market/{mid})"
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

                            alerted[k] = True
                            save_state(alerted)
                        elif DEBUG_MODE:
                            pname = runner_name.get((mid, r.selection_id), str(r.selection_id))
                            print(f"[DEBUG] Filtered (below threshold): {mid} | {pname} | £{int(lay_size)} < £{int(threshold)}", flush=True)

        # Purge alerts older than 12 hours
        if poll_count % 10 == 0:
            now = datetime.now(timezone.utc)
            to_del = [k for k in list(alerted.keys())
                if k.split(":",1)[0] in kickoff and kickoff[k.split(":",1)[0]] < now - timedelta(hours=12)]
            for k in to_del:
                alerted.pop(k, None)
            if to_del:
                save_state(alerted)

        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
