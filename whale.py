import os, sys, time, json, requests, shutil
from dotenv import load_dotenv
import pytz
from oc import get_oddschecker_match_slug, get_oddschecker_odds
from datetime import datetime, timedelta, timezone

import betfairlightweight
from betfairlightweight import filters
from betfairlightweight.exceptions import APIError

load_dotenv()
london = pytz.timezone("Europe/London")

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

DISCORD_BOT_TOKEN   = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID  = os.getenv("DISCORD_CHANNEL_ID", "")
DISCORD_CHANNEL_IDS = os.getenv("DISCORD_CHANNEL_IDS", "").strip()  # comma-separated list
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")          # optional single webhook (posts once)
DISCORD_ENABLED     = os.getenv("DISCORD_ENABLED", "1") == "1"      # enable/disable posting
DISCORD_ARB_CHANNEL_ID = os.getenv("DISCORD_ARB_CHANNEL_ID", "").strip()  # separate channel for arbitrage alerts

# Force-monitor specific market IDs (comma separated)
OVERRIDE_INCLUDE_MARKET_IDS = [x.strip() for x in os.getenv("OVERRIDE_INCLUDE_MARKET_IDS", "").split(",") if x.strip()]

CERTS_DIR  = "/app/certs"
STATE_FILE = "/app/state/liquidity_alert_state.json"
# ========= CONFIG =========
GBP_THRESHOLD_FGS  = float(os.getenv("GBP_THRESHOLD_FGS", "200"))
GBP_THRESHOLD_AGS  = float(os.getenv("GBP_THRESHOLD_AGS", "750"))

TOP_LEVELS       = int(os.getenv("TOP_LEVELS", "1"))         # sum top N lay levels
WINDOW_MINUTES   = int(os.getenv("WINDOW_MINUTES", "90"))    # KO window
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
MARKET_TYPE_CODES_FGS = [
    "FIRST_GOALSCORER","PLAYER_FIRST_GOALSCORER","FIRST_GOAL_SCORER"
]
MARKET_TYPE_CODES_AGS = [
    "ANYTIME_GOALSCORER","PLAYER_TO_SCORE","TO_SCORE","GOALSCORER"
]

# ========= DISCORD =========
def _channel_list():
    if DISCORD_CHANNEL_IDS:
        return [x.strip() for x in DISCORD_CHANNEL_IDS.split(",") if x.strip()]
    return [DISCORD_CHANNEL_ID] if DISCORD_CHANNEL_ID else []

def send_discord_embed(title, description, fields, colour=0x3AA3E3, channel_ids=None):
    if not DISCORD_ENABLED:
        return

    channels = channel_ids if channel_ids else _channel_list()

    embed = {
        "title": title,
        "description": description,
        "color": colour,
        "fields": [{"name": n, "value": v, "inline": True} for (n, v) in fields],
        "timestamp": datetime.now(london).isoformat()

    }
    payload = {"embeds": [embed], "content": ""}

    # single webhook support (posts once)
    if DISCORD_WEBHOOK_URL:
        try:
            r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            if r.status_code >= 300:
                print(f"[WARN] Webhook error: {r.text[:600]}")
        except Exception as e:
            print(f"[WARN] Webhook post failed: {e}")
        return

    if not DISCORD_BOT_TOKEN or not channels:
        print(f"[WARN] Discord not configured. Token set={bool(DISCORD_BOT_TOKEN)} channels={channels}")
        return

    for ch in channels:
        try:
            r = requests.post(
                f"https://discord.com/api/v10/channels/{ch}/messages",
                headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}",
                         "Content-Type": "application/json"},
                json=payload, timeout=10
            )
            if r.status_code >= 300:
                print(f"[WARN] Channel {ch} error body: {r.text[:600]}")
        except Exception as e:
            print(f"[WARN] Channel {ch} post failed: {e}")

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
    return filters.time_range(from_=now, to=now + timedelta(hours=24))

def is_fgs_name(n):
    n = (n or "").lower()
    return any(p in n for p in [
        "player first goalscorer","first goalscorer","first goal scorer",
        "first goal-scorer","first player to score"
    ])

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
    # Pass 1: official market type codes (FGS/AGS)
    for batch in chunks(competition_ids, BATCH_COMP_SIZE):
        cat += _catalogue_batch(trading, batch, market_type_codes=MARKET_TYPE_CODES_FGS) or []
    for batch in chunks(competition_ids, BATCH_COMP_SIZE):
        cat += _catalogue_batch(trading, batch, market_type_codes=MARKET_TYPE_CODES_AGS) or []

    # Pass 2: global name-search fallback if empty
    if not cat:
        FGS_NAME_QUERIES = ["first goalscorer", "first goal scorer", "first player to score"]
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

        for q in FGS_NAME_QUERIES:
            cat += _global_name_query(q)
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
        if mt in MARKET_TYPE_CODES_FGS or is_fgs_name(name):
            market_label[mid] = "FGS"
        elif mt in MARKET_TYPE_CODES_AGS or is_ags_name(name):
            market_label[mid] = "AGS"
        else:
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
                if mt in MARKET_TYPE_CODES_FGS or is_fgs_name(name):
                    market_label[mid] = "FGS"
                elif mt in MARKET_TYPE_CODES_AGS or is_ags_name(name):
                    market_label[mid] = "AGS"
                else:
                    market_label[mid] = "AGS"
                for r in c.runners or []:
                    runner_name[(mid, r.selection_id)] = r.runner_name
                print(comp_name)
        except Exception as e:
            print("[WARN] Failed to force-include market IDs:", e, flush=True)

    print(f"[START] Bot online. Monitoring {len(market_ids)} markets across {len(comp_ids)} competitions (next 24h).", flush=True)
    send_discord_embed(
        "liquidity-bot online",
        "Monitoring FGS and AGS markets (next 24h) has started.",
        [("FGS threshold", f"£{int(GBP_THRESHOLD_FGS)}"),
         ("AGS threshold", f"£{int(GBP_THRESHOLD_AGS)}"),
         ("Window", f"{WINDOW_MINUTES} mins")],colour=0x3AC7E3
    )
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
            threshold = GBP_THRESHOLD_FGS if label == "FGS" else GBP_THRESHOLD_AGS

            for r in mb.runners or []:
                k = key_for(mid, r.selection_id)
                if alerted.get(k):
                    if DEBUG_MODE:
                        pname = runner_name.get((mid, r.selection_id), str(r.selection_id))
                        print(f"[DEBUG] Filtered (already alerted): {mid} | {pname}", flush=True)
                    continue

                lay_size = sum_lay_levels(r, TOP_LEVELS)

                # --- DIAGNOSTIC: log near-threshold runners across ALL markets ---
                if DIAG_NEAR_PCT > 0 and (poll_count % max(1, DIAG_EVERY_POLLS) == 0):
                    diag_floor = max(DIAG_MIN_ABS, threshold * DIAG_NEAR_PCT)
                    if lay_size >= diag_floor:
                        pname = runner_name.get((mid, r.selection_id), str(r.selection_id))
                        levels = lay_levels_list(r, TOP_LEVELS)
                        levels_str = " ".join(
                            [f"L{i+1}=£{int(sz)}@{pr}" for i,(pr,sz) in enumerate(levels)]
                        ) if levels else "no-levels"
                        print(
                            f"[NEAR] {mid} | {event_name.get(mid,'?')} | {pname} | {label} | "
                            f"{levels_str} | sum(top {TOP_LEVELS})=£{int(lay_size)} "
                            f"vs threshold £{int(threshold)}",
                            flush=True
                        )

                # --- ALERT when crossing threshold ---
                if lay_size >= threshold:
                    pname = runner_name.get((mid, r.selection_id), str(r.selection_id))
                    mins_to_ko = int((kickoff[mid] - datetime.now(timezone.utc)).total_seconds() // 60)
                    bbp, bbs = best_back_tuple(r)
                    if bbp and bbp < 1.2:
                        continue
                    blp, bls = best_lay_tuple(r)
                    title = f"Liquidity alert ({label})"
                    desc = f"{event_name.get(mid,'?')} — {comp_name.get(mid,'?')}"

                    # GET OC RESULTS
                    oc_results = []
                    match_slug = None
                    try:
                        match_slug = get_oddschecker_match_slug(event_id[mid])
                        if not match_slug:
                            raise Exception("Could not map Betfair ID to OddsChecker slug")
                        # BUILD THE JSON FOR THIS BET ['First Goalscorer','Anytime Goalscorer']
                        if label == "FGS":
                            bettype = "First Goalscorer"
                        elif label == "AGS":
                            bettype = "Anytime Goalscorer"
                        betfair_lay_bet = [{"bettype": bettype, "outcome": pname, "min_odds": bbp, "lay_odds": blp}]
                        # GET ALL BETTER ODDS - retry 3 times with 2s delays
                        for attempt in range(3):
                            try:
                                oc_results, arb_opportunities = get_oddschecker_odds(match_slug, betfair_lay_bet)
                                break
                            except Exception as retry_err:
                                if attempt < 2:
                                    print(f"[WARN] OddsChecker API attempt {attempt+1}/3 failed, retrying in 2s: {retry_err}", flush=True)
                                    time.sleep(2)
                                else:
                                    print(f"[WARN] OddsChecker API failed after 3 attempts: {retry_err}", flush=True)
                                    oc_results, arb_opportunities = [], []
                    except Exception as e:
                        print(f"[WARN] OddsChecker setup failed for event {event_id[mid]}: {e}", flush=True)
                        oc_results, arb_opportunities = [], []
                    '''
                        [{'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.6, 'bookie': 'Bet365'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Boylesports'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.9, 'bookie': 'Coral'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.4, 'bookie': 'Betfred'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.9, 'bookie': 'Ladbrokes'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Paddy Power'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.9, 'bookie': 'QuinnBet'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Sky Bet'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Unibet'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 4.0, 'bookie': 'Bet Victor'}, {'bettype': 'Anytime Goalscorer', 'outcome': 'Lee Angol', 'odds': 3.75, 'bookie': 'William Hill'}]
                    '''
                    fields = [
                        ("Player", pname),
                        ("Lay size", f"£{int(lay_size)} (top {TOP_LEVELS})"),
                        ("Threshold", f"£{int(threshold)}"),
                        ("LTP", str(getattr(r, 'last_price_traded', None))),
                        ("Layable now", "—" if not (bbp and bbs) else f"£{int(bbs)} @ {bbp}"),
                        ("Best lay", "—" if not (blp and bls) else f"£{int(bls)} @ {blp}"),
                        ("T- mins", str(mins_to_ko)),
                        ("Market Link", f"[Open Market](https://www.betfair.com/exchange/plus/football/market/{mid})"),
                    ]
                    
                    # Add OddsChecker link if available
                    if match_slug:
                        fields.append(("OC Link", f"[View OC](https://www.oddschecker.com/football/{match_slug})"))
                    
                                        # Combine all bookie @ odds pairs into a single field under one heading
                    embed_colour = 0xA0A0A0  # default blue
                    if oc_results:
                        better_list = []
                        fallback_list = []
                        for oc in oc_results:
                            bookie = oc.get('bookie')
                            odds = oc.get('odds')
                            if bookie and odds:
                                pair = f"{bookie} @ {odds:.2f}"
                                # Add (ARB) if OddsChecker odds are higher than lay odds
                                if blp and odds > blp:
                                    pair += " (ARB)"
                                if oc.get('fallback', False):
                                    fallback_list.append(pair)
                                else:
                                    better_list.append(pair)
                        if better_list:
                            fields.append(("Better Back Odds", "\n".join(better_list)))
                            embed_colour = 0xE33A3A  # red for ARB
                        if fallback_list and not better_list:
                            fields.append(("Best Back Odds", "\n".join(fallback_list)))
                            embed_colour = 0x3AA3E3  # blue for fallback only
                    
                    # # Add true arbitrage opportunities if any
                    # if arb_opportunities:
                    #     arb_list = []
                    #     for arb in arb_opportunities:
                    #         bookie = arb.get('bookie')
                    #         odds = arb.get('odds')
                    #         lay_odds = arb.get('lay_odds')
                    #         if bookie and odds and lay_odds:
                    #             arb_list.append(f"{bookie} @ {odds} (lay @ {lay_odds})")
                    #     if arb_list:
                    #         fields.append(("ARBITRAGE OPPORTUNITIES", "\n".join(arb_list)))
                    #         embed_colour = 0xFF0000  # bright red for true arb
                    # Send main liquidity alert if channels are configured
                    if _channel_list():
                        send_discord_embed(title, desc, fields, colour=embed_colour)
                    
                    # Send separate arbitrage message if configured
                    if arb_opportunities and DISCORD_ARB_CHANNEL_ID:
                        # Calculate max OddsChecker odds for title
                        max_oc_odds = max(arb['odds'] for arb in arb_opportunities) if arb_opportunities else 0
                        rating_pct = (max_oc_odds / blp * 100) if blp and max_oc_odds > 0 else 0
                        arb_title = f"{pname} ({label}) - {max_oc_odds}/{blp} ({rating_pct:.1f}%)"
                        arb_fields = [
                            ("Back Sites", "\n".join([f"{arb['bookie']} @ {arb['odds']:.2f}" for arb in arb_opportunities])),
                            ("BFEX Link", f"[Open Market](https://www.betfair.com/exchange/plus/football/market/{mid})"),
                        ]
                        if match_slug:
                            arb_fields.append(("OC Link", f"[View OC](https://www.oddschecker.com/football/{match_slug})"))
                        send_discord_embed(arb_title, desc, arb_fields, colour=0xFFB80C, channel_ids=[DISCORD_ARB_CHANNEL_ID])
                    
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
