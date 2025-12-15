import json
import re
import requests
import os
import time
try:
    import tls_client
except ImportError:
    tls_client = None
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# ========= DEBUG MODE =========
DEBUG_MODE = os.getenv("DEBUG_MODE", "0") == "1"

# ========= FUZZY NAME MATCHING =========
def _fuzzy_match_names(name1: str, name2: str) -> bool:
    """
    Check if two player names are a fuzzy match.
    Returns True if at least 2 out of 3 name parts match.
    
    Examples:
        'Santos Matheus Cunha' vs 'Matheus Cunha' -> True (2/2 match)
        'Junior Kroupi' vs 'Eli Junior Kroupi' -> True (2/3 match)
        'Benjamin Sesko' vs 'Ben Sesko' -> True (1/2 match, 50%+)
    
    Args:
        name1: First name to compare
        name2: Second name to compare
        
    Returns:
        True if names match closely enough
    """
    # Normalize: lowercase and split into parts
    parts1 = set(name1.lower().split())
    parts2 = set(name2.lower().split())
    
    # Remove very short parts (initials, etc.) that might cause false matches
    parts1 = {p for p in parts1 if len(p) > 1}
    parts2 = {p for p in parts2 if len(p) > 1}
    
    if not parts1 or not parts2:
        return False
    
    # Count matching parts
    matches = len(parts1 & parts2)
    
    # Calculate total unique parts (union)
    total_parts = len(parts1 | parts2)
    
    if total_parts == 0:
        return False
    
    # Need at least 2 matching parts, OR >50% match rate for shorter names
    if matches >= 2:
        return True
    
    # For shorter names (2 parts total), require at least 50% match
    match_rate = matches / total_parts
    return match_rate >= 0.5

# ========= CACHE =========
CACHE_DIR = './cache'
CACHE_HTML_SUBDIR = 'html'
CACHE_ODDS_SUBDIR = 'odds'
ODDS_CACHE_TTL = 60  # Cache odds for 60 seconds

# ========= BOOKMAKER MAPPING =========
BOOKMAKER_MAPPING = {
    'B3': 'Bet365',
    'FR': 'Betfred',
    'PP': 'Paddy Power',
    'WH': 'William Hill',
    'BF': 'Betfair',
    'SK': 'Sky Bet',
    'LD': 'Ladbrokes',
    'UN': 'Unibet',
    '888': '888sport',
    'BX': 'Betdaq',
    'MR': 'Matchbook',
    'SM': 'Smarkets',
    'VE': 'VirginBet',
    'VC': 'Bet Victor',
    'SX': 'Spreadex',
    'CE': 'Coral',
    'CR': 'Coral',
    'WA': 'Betway',
    'BW': 'Betway',
    'BY': 'Boylesports',
    'KN': 'BetMGM UK',
    'OE': '10Bet',
    '10B': '10Bet',
    'QN': 'QuinnBet',
    'SI': 'Sporting Index',  # Additional codes that might appear
    'EE': '888 Sport',   # Additional codes that might appear
    'AKB': 'AKBets',
    'BRS': 'Bresbet',
    'PUP': 'Priced Up',
    'S6': 'Star Sports',
    'BTT': 'BetTom',
    'G5': 'Bet Goodwin',
    'CUS': 'Casumo',
}

# ========= SLUG CACHE =========
# In-memory cache for Betfair ID -> OddsChecker slug mappings
_SLUG_CACHE = {}

def _ensure_cache_dirs():
    """Create cache directories if they don't exist."""
    os.makedirs(os.path.join(CACHE_DIR, CACHE_HTML_SUBDIR), exist_ok=True)
    os.makedirs(os.path.join(CACHE_DIR, CACHE_ODDS_SUBDIR), exist_ok=True)

def _debug(msg):
    """Print debug message if DEBUG_MODE is enabled."""
    if DEBUG_MODE:
        print(msg, flush=True)

def _get_bookmaker_name(code):
    """Convert bookmaker code to full name."""
    return BOOKMAKER_MAPPING.get(code, code)  # Return code if not found

def _get_cache_path(filename, subdir):
    """Get the full cache file path."""
    return os.path.join(CACHE_DIR, subdir, filename)

def _cache_file_exists_and_valid(cache_path, max_age=None):
    """
    Check if cache file exists and is valid (fresh or not time-limited).
    max_age: maximum age in seconds (None = no time limit, use forever)
    Returns: True if file exists and is valid, False otherwise
    """
    if not os.path.exists(cache_path):
        return False
    
    if max_age is None:
        # No time limit, cache is always valid
        return True
    
    file_age = time.time() - os.path.getmtime(cache_path)
    return file_age < max_age

def _read_cache(cache_path):
    """Read and return cache file content as JSON."""
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to read cache {cache_path}: {e}", flush=True)
        return None

def _write_cache(cache_path, data):
    """Write data to cache file as JSON."""
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        _debug(f"[INFO] Cached data to {cache_path}")
    except Exception as e:
        print(f"[WARN] Failed to write cache {cache_path}: {e}", flush=True)

def _write_cache_text(cache_path, data):
    """Write data to cache file as text."""
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(data)
        _debug(f"[INFO] Cached HTML to {cache_path}")
    except Exception as e:
        print(f"[WARN] Failed to write cache {cache_path}: {e}", flush=True)

def _read_cache_text(cache_path):
    """Read and return cache file content as text."""
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[WARN] Failed to read cache {cache_path}: {e}", flush=True)
        return None

def get_oddschecker_match_slug(betfair_id):
    """
    Convert Betfair match ID to OddsChecker page slug using the mapping API.
    Uses in-memory cache to avoid repeated API calls for the same match.
    
    betfair_id: Betfair match ID (can be string or dict)
    Returns: page_slug string (e.g., "english/premier-league/team-a-v-team-b") or None on failure
    """
    if isinstance(betfair_id, dict):
        betfair_id = next(iter(betfair_id.values()))
    
    # Check cache first
    if betfair_id in _SLUG_CACHE:
        _debug(f"[INFO] Using cached slug for Betfair {betfair_id}: {_SLUG_CACHE[betfair_id]}")
        return _SLUG_CACHE[betfair_id]
    
    api_url = f'https://api.oddsmatcha.uk/convert/betfair_to_oddschecker?betfair_ids={betfair_id}'
    try:
        response_data = requests.get(api_url).json()
        
        # Validate response structure
        if response_data.get('success') and isinstance(response_data.get('conversions'), list):
            conversions = response_data['conversions']
            if conversions:
                first_item = conversions[0]
                page_slug = first_item.get('page_slug')
                if page_slug:
                    _debug(f"[INFO] Mapped Betfair {betfair_id} to OddsChecker slug: {page_slug}")
                    # Cache the result
                    _SLUG_CACHE[betfair_id] = page_slug
                    return page_slug
                else:
                    print(f"[WARN] 'page_slug' not found in conversion response for Betfair {betfair_id}", flush=True)
                    return None
            else:
                print(f"[WARN] 'conversions' list is empty for Betfair {betfair_id}", flush=True)
                return None
        else:
            print(f"[WARN] API response structure invalid or unsuccessful for Betfair {betfair_id}", flush=True)
            return None
    except Exception as e:
        print(f"[ERROR] Failed to map Betfair ID {betfair_id} to OddsChecker: {e}", flush=True)
        return None

def scrape_oddschecker_market_ids(match_slug):
    """
    Scrape OddsChecker webpage to find Anytime Goalscorer and First Goalscorer market IDs using tls_client.
    Caches HTML forever (doesn't change), reuses cached HTML if available.
    Reuses the same session to get odds with the market IDs found.
    match_slug: e.g., "world-cup-european-qualifiers/slovakia-v-northern-ireland"
    Returns: tuple of (dict with market_ids, tls_client session) or (None, None) on failure
    """
    _ensure_cache_dirs()
    
    if not BeautifulSoup:
        print("[ERROR] BeautifulSoup4 not installed, cannot scrape webpage", flush=True)
        return None, None
    
    if not tls_client:
        print("[ERROR] tls_client not installed, cannot scrape webpage", flush=True)
        return None, None
    
    try:
        url = f'https://www.oddschecker.com/football/{match_slug}/winner'
        
        # Check if we have cached HTML for this match
        cache_filename = f"{match_slug.replace('/', '_')}_page.html"
        cache_path = _get_cache_path(cache_filename, CACHE_HTML_SUBDIR)
        
        html_content = None
        if _cache_file_exists_and_valid(cache_path, max_age=None):  # Cache HTML forever
            _debug(f"[INFO] Using cached HTML for {match_slug}")
            html_content = _read_cache_text(cache_path)
        
        # If not in cache, fetch from web
        if html_content is None:
            headers = {
                'authority': 'www.oddschecker.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'priority': 'u=0, i',
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
            
            # Create a single tls_client session to reuse for both page fetch and odds API calls
            _debug(f"[INFO] Creating tls_client session with chrome120 fingerprint...")
            session = tls_client.Session(
                client_identifier="chrome120",
                random_tls_extension_order=True
            )
            
            # Fetch the match page
            _debug(f"[INFO] Fetching match page: {url}")
            response = session.get(
                url,
                headers=headers,
                cookies=cookies
            )
            if response.status_code == 404:
                print(f"[INFO] No OddsChecker page found at {url} (404)", flush=True)
                return None, None
            elif response.status_code != 200:
                raise Exception(f"HTTP {response.status_code} fetching OddsChecker page: {url}")
            html_content = response.text
            _debug(f"[INFO] Successfully fetched page with tls_client")
            
            # Cache the HTML for future use
            _write_cache_text(cache_path, html_content)
        else:
            # Create a new session for odds fetching even if we used cached HTML
            _debug(f"[INFO] Creating tls_client session for odds fetch...")
            session = tls_client.Session(
                client_identifier="chrome120",
                random_tls_extension_order=True
            )
        
        # Also save to debug file
        try:
            with open('oddschecker_market_page.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            _debug(f"[INFO] Saved HTML to oddschecker_market_page.html for debugging")
        except Exception as e:
            print(f"[WARN] Failed to save HTML: {e}", flush=True)
        
        market_ids = {
            'fgs': None,
            'ags': None
        }
        
        import re
        
        # Parse HTML to find the data script
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for the script containing market data
        for script in soup.find_all('script'):
            script_content = script.get_text() if script.get_text() else ""
            if not script_content or 'marketName' not in script_content:
                continue
            
            # Extract market data from the JSON structure
            # Look for patterns like "3579339764":{"ocMarketId":3579339764,...,"marketName":"...#First Goalscorer",...}
            
            # Match First Goalscorer market
            fgs_pattern = r'"ocMarketId":(\d+),[^}]*"marketName":"[^#]*#First Goalscorer"'
            fgs_matches = re.findall(fgs_pattern, script_content)
            if fgs_matches:
                market_ids['fgs'] = fgs_matches[0]
                _debug(f"[INFO] Found FGS market ID: {market_ids['fgs']}")
            
            # Match Anytime Goalscorer market
            ags_pattern = r'"ocMarketId":(\d+),[^}]*"marketName":"[^#]*#Anytime Goalscorer"'
            ags_matches = re.findall(ags_pattern, script_content)
            if ags_matches:
                market_ids['ags'] = ags_matches[0]
                _debug(f"[INFO] Found AGS market ID: {market_ids['ags']}")
        
        if market_ids['fgs'] or market_ids['ags']:
            _debug(f"[INFO] Found market IDs: FGS={market_ids['fgs']}, AGS={market_ids['ags']}")
            # Return both the market IDs and the session to reuse
            return market_ids, session
        else:
            print(f"[WARN] Could not find market IDs in page for {match_slug}", flush=True)
            return None, None
            
    except Exception as e:
        print(f"[ERROR] Unexpected error scraping OddsChecker page for {match_slug}: {e}", flush=True)
        return None, None

def get_oddschecker_odds_web_fallback(market_ids, session=None):
    """
    Fetch odds from /api/markets/v2/all-odds endpoint using the provided tls_client session.
    Caches odds for 60 seconds, reuses cache if available and fresh.
    market_ids: list of OddsChecker market IDs (e.g., ['3579249255', '3579289293'])
    session: tls_client session to reuse (if None, creates a new one)
    """
    _ensure_cache_dirs()
    
    try:
        # Create cache filename based on market IDs
        cache_filename = f"odds_{'_'.join(str(mid) for mid in market_ids)}.json"
        cache_path = _get_cache_path(cache_filename, CACHE_ODDS_SUBDIR)
        
        # Check if we have valid cached odds (less than 60 seconds old)
        if _cache_file_exists_and_valid(cache_path, max_age=ODDS_CACHE_TTL):
            _debug(f"[INFO] Using cached odds (less than {ODDS_CACHE_TTL}s old) for market IDs: {market_ids}")
            return _read_cache(cache_path)
        
        # Web API headers
        headers = {
            'authority': 'www.oddschecker.com',
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.oddschecker.com/football/',
            'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
        }
        
        cookies = {
            'odds_type': 'decimal',
            'device': 'desktop',
            'logged_in': 'false',
            'mobile_redirect': 'true',
        }
        
        market_ids_str = ','.join(str(mid) for mid in market_ids)
        odds_url = f'https://www.oddschecker.com/api/markets/v2/all-odds?market-ids={market_ids_str}&repub=OC'
        
        # Create or reuse session
        if session is None:
            if not tls_client:
                print("[ERROR] tls_client not installed, cannot fetch odds", flush=True)
                return None
            _debug(f"[INFO] Creating new tls_client session for odds fetch")
            session = tls_client.Session(
                client_identifier="chrome120",
                random_tls_extension_order=True
            )
        
        _debug(f"[INFO] Fetching fresh odds from: {odds_url}")
        response = session.get(
            odds_url,
            headers=headers,
            cookies=cookies
        )
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.reason}")
        odds_data = response.json()
        _debug(f"[INFO] Successfully fetched fresh odds via tls_client for market IDs: {market_ids_str}")
        
        # Cache the odds for 60 seconds
        _write_cache(cache_path, odds_data)
        
        # Also save to debug file
        try:
            with open('whale_oc_web_fallback.json', 'w', encoding='utf-8') as f:
                json.dump(odds_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to write whale_oc_web_fallback.json: {e}", flush=True)
        
        return odds_data
    except Exception as e:
        print(f"[ERROR] Failed to fetch odds for market IDs {market_ids}: {e}", flush=True)
        return None

def get_oddschecker_odds(match_slug, betdata):
    """
    Get OddsChecker odds by scraping the market page and fetching odds using the same tls_client session.
    Extracts player names from both HTML and API response (bets array).
    match_slug: e.g., "world-cup-european-qualifiers/slovakia-v-northern-ireland"
    betdata: list of dicts with 'bettype', 'outcome', 'min_odds', 'lay_odds' keys
    Returns: tuple of (arbs_list, arb_opportunities_list) where arb_opportunities contains only true arbitrage opportunities
    """
    # Scrape market page to get market IDs and player names from the page HTML
    market_ids, session = scrape_oddschecker_market_ids(match_slug)
    
    if not market_ids:
        print(f"[ERROR] Failed to get market IDs for match slug {match_slug}", flush=True)
        return []
    
    # Read the saved HTML to extract player names and their betIds (fallback for HTML-available data)
    player_bet_mapping = _extract_player_bets_from_html('oddschecker_market_page.html', market_ids)
    
    # Extract just the IDs from the dict
    market_id_list = []
    if market_ids.get('fgs'):
        market_id_list.append(market_ids['fgs'])
    if market_ids.get('ags'):
        market_id_list.append(market_ids['ags'])
    
    if not market_id_list:
        print(f"[ERROR] No valid market IDs found for match slug {match_slug}", flush=True)
        return []
    
    _debug(f"[INFO] Using market IDs for odds fetch: {market_id_list}")
    
    # Fetch odds using the same session
    oddschecker_data = get_oddschecker_odds_web_fallback(market_id_list, session=session)
    
    if oddschecker_data is None:
        print(f"[ERROR] Failed to get odds for match slug {match_slug}", flush=True)
        return []
    
    try:
        with open('whale_oc.json', 'w', encoding='utf-8') as f:
            json.dump(oddschecker_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to write whale_oc.json: {e}", flush=True)

    # Extract player names from API response's bets array (for FGS and AGS)
    api_player_bet_mapping = _extract_player_bets_from_api(oddschecker_data, market_ids)
    
    # Merge API-extracted bets with HTML-extracted bets (API takes precedence)
    for bettype, players in api_player_bet_mapping.items():
        if bettype not in player_bet_mapping:
            player_bet_mapping[bettype] = {}
        player_bet_mapping[bettype].update(players)
    
    _debug(f"[INFO] Final player mapping: FGS={len(player_bet_mapping.get('First Goalscorer', {}))}, AGS={len(player_bet_mapping.get('Anytime Goalscorer', {}))}")

    if not isinstance(betdata, list):
        betdata = [betdata]
    
    arb_opportunities = []
    for bet in betdata:
        bettype = bet.get('bettype')
        outcome = bet.get('outcome')
        min_odds = float(bet.get('min_odds', 0))
        lay_odds = float(bet.get('lay_odds', 0))
        best_match = None

        # Find the betId for this outcome from the player mapping
        bet_id = None
        # First try exact match
        for mapped_outcome, mapped_bet_id in player_bet_mapping.get(bettype, {}).items():
            if mapped_outcome.lower() == outcome.lower():
                bet_id = mapped_bet_id
                break
        
        # If no exact match, try fuzzy matching
        if not bet_id:
            for mapped_outcome, mapped_bet_id in player_bet_mapping.get(bettype, {}).items():
                if _fuzzy_match_names(mapped_outcome, outcome):
                    bet_id = mapped_bet_id
                    print(f"[INFO] Fuzzy matched '{outcome}' to '{mapped_outcome}' for {bettype}", flush=True)
                    break
        
        if not bet_id:
            print(f"[WARN] Could not find betId for {bettype} / {outcome}", flush=True)
            continue
        
        _debug(f"[INFO] Found {bettype} / {outcome} with betId: {bet_id}")

        # Search through the odds data for this betId
        for market in oddschecker_data:
            market_name = market.get('marketName', '')
            
            if bettype in market_name:
                for odds_entry in market.get('odds', []):
                    if odds_entry.get('betId') == bet_id:
                        try:
                            odds_decimal = float(odds_entry.get('oddsDecimal', 0))
                            bookie_code = odds_entry.get('bookmakerCode', 'Unknown')
                            bookie_name = _get_bookmaker_name(bookie_code)
                            
                            if odds_decimal > 0:
                                # Check for arbitrage opportunity (OddsChecker odds > lay odds)
                                if lay_odds > 0 and odds_decimal > lay_odds:
                                    arb_opportunities.append({
                                        'bettype': bettype,
                                        'outcome': outcome,
                                        'odds': odds_decimal,
                                        'bookie': bookie_name,
                                        'lay_odds': lay_odds
                                    })
                                
                                # Track best odds for this outcome
                                if not best_match or odds_decimal > best_match['odds']:
                                    best_match = {
                                        'bettype': bettype,
                                        'outcome': outcome,
                                        'odds': odds_decimal,
                                        'bookie': bookie_name
                                    }
                                
                        except (ValueError, TypeError) as e:
                            print(f"[WARN] Error parsing odds for {outcome}: {e}", flush=True)
                            continue


    return arb_opportunities

def _extract_player_bets_from_html(html_file, market_ids):
    """
    Extract player names and their betIds from the saved HTML file.
    market_ids: dict with 'fgs' and 'ags' market IDs
    Returns: dict with structure {'First Goalscorer': {'Player Name': betId, ...}, 'Anytime Goalscorer': {...}}
    """
    player_bets = {}
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Find the script tag with subeventmarkets data
        script_pattern = r'<script[^>]*data-hypernova-key="subeventmarkets"[^>]*><!--({.*?})--></script>'
        script_match = re.search(script_pattern, html_content, re.DOTALL)
        
        if not script_match:
            print(f"[WARN] Could not find subeventmarkets script tag", flush=True)
            return {}
        
        json_str = script_match.group(1)
        
        # Save the raw JSON for debugging
        try:
            with open('extracted_markets_data.json', 'w', encoding='utf-8') as f:
                f.write(json_str)
            _debug(f"[INFO] Saved extracted markets JSON to extracted_markets_data.json")
        except Exception as e:
            print(f"[WARN] Failed to save extracted markets data: {e}", flush=True)
        
        # Parse the JSON to get bets
        try:
            data = json.loads(json_str)
            bets_entities = data.get('bestOdds', {}).get('bets', {}).get('entities', {})
            
            _debug(f"[INFO] Found {len(bets_entities)} total bets in extracted JSON")
            
            # Now look for the market definitions to map market IDs to types
            fgs_market_id = market_ids.get('fgs')
            ags_market_id = market_ids.get('ags')
            
            for bet_id_str, bet_data in bets_entities.items():
                player_name = bet_data.get('betName', '')
                market_id = bet_data.get('marketId')
                
                if not player_name or market_id is None:
                    continue
                
                if fgs_market_id and market_id == int(fgs_market_id):
                    if 'First Goalscorer' not in player_bets:
                        player_bets['First Goalscorer'] = {}
                    player_bets['First Goalscorer'][player_name] = int(bet_id_str)
                elif ags_market_id and market_id == int(ags_market_id):
                    if 'Anytime Goalscorer' not in player_bets:
                        player_bets['Anytime Goalscorer'] = {}
                    player_bets['Anytime Goalscorer'][player_name] = int(bet_id_str)
            
            _debug(f"[INFO] Found {len(player_bets.get('First Goalscorer', {}))} FGS players from HTML")
            _debug(f"[INFO] Found {len(player_bets.get('Anytime Goalscorer', {}))} AGS players from HTML")
            return player_bets
        except json.JSONDecodeError as e:
            print(f"[WARN] Failed to parse extracted JSON: {e}", flush=True)
            return {}
            
    except Exception as e:
        print(f"[WARN] Failed to extract player bets from HTML: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return {}

def _extract_player_bets_from_api(oddschecker_data, market_ids):
    """
    Extract player names and their betIds from the API response's bets array.
    API response has bets array for each market with betId and betName.
    oddschecker_data: list of market objects from API response
    market_ids: dict with 'fgs' and 'ags' market IDs
    Returns: dict with structure {'First Goalscorer': {'Player Name': betId, ...}, 'Anytime Goalscorer': {...}}
    """
    player_bets = {}
    
    fgs_market_id = int(market_ids.get('fgs')) if market_ids.get('fgs') else None
    ags_market_id = int(market_ids.get('ags')) if market_ids.get('ags') else None
    
    try:
        for market in oddschecker_data:
            market_id = int(market.get('marketId', 0))
            market_name = market.get('marketName', '')
            bets_array = market.get('bets', [])
            
            # Determine bettype from market ID
            bettype = None
            if fgs_market_id and market_id == fgs_market_id:
                bettype = 'First Goalscorer'
            elif ags_market_id and market_id == ags_market_id:
                bettype = 'Anytime Goalscorer'
            else:
                continue
            
            if not bets_array:
                _debug(f"[INFO] No bets array found for {bettype} market {market_id}")
                continue
            
            if bettype not in player_bets:
                player_bets[bettype] = {}
            
            # Extract player name and betId from each bet
            for bet in bets_array:
                bet_id = bet.get('betId')
                player_name = bet.get('betName')
                
                if bet_id and player_name:
                    player_bets[bettype][player_name] = bet_id
            
            _debug(f"[INFO] Found {len(player_bets[bettype])} {bettype} players from API")
    
    except Exception as e:
        print(f"[WARN] Failed to extract player bets from API: {e}", flush=True)
        import traceback
        traceback.print_exc()
    
    return player_bets



# With a Betfair MatchID get an OddsChecker Match ID from my API
# This will only work for matches I are tracking
# oddschecker_id = get_oddschecker_match_id(betfair_id)
if __name__ == "__main__":
    # Test full workflow: scrape + fetch odds + find arbs
    print("[TEST] Testing full OddsChecker workflow for Slovakia v Northern Ireland...")
    match_slug = "world-cup-european-qualifiers/slovakia-v-northern-ireland"
    
    # Sample betdata - looking for Anytime Goalscorer markets (First Goalscorer player names not available in HTML)
    betdata = [
        {
            'bettype': 'First Goalscorer',
            'outcome': 'Jamie Reid',
            'min_odds': 1.5
        },
        {
            'bettype': 'Anytime Goalscorer',
            'outcome': 'David Strelec',
            'min_odds': 1.5
        }
    ]
    
    arbs = get_oddschecker_odds(match_slug, betdata)
    
    if arbs:
        _debug(f"[TEST] Found {len(arbs)} arbs:")
        for arb in arbs:
            _debug(f"[TEST]   - {arb['bettype']} / {arb['outcome']}: {arb['odds']} @ {arb['bookie']}")
    else:
        _debug(f"[TEST] No arbs found for this match")