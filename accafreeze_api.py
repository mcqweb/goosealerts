"""
accafreeze_api.py

Minimal JSON-producing version of AccaFreeze scanner intended for API consumption.
- Built-in configuration at the top of this file.
- Default behaviour: print ONLY JSON to stdout (suitable for piping to an API process).
- Optionally: write JSON to a file via --out-file.

This script reuses some helper functions from `accafreeze.py` (must be in same folder).
Requires requests, cloudscraper and tls_client (same deps as the main script).
"""

import argparse
import json
import sys
from datetime import datetime, timezone
import contextlib
import os

# Import helper functions from existing module
from accafreeze import (
    fetch_accafreeze_data,
    filter_matches,
    get_skybet_odds_for_match,
    match_team_names,
    calculate_rating,
)

# ---------------------- Built-in configuration ----------------------
# Tweak thresholds as required. This config is embedded in the script per request.
CONFIG = {
    "first_leg": {
        "min_lay_odds": 1.5,      # Exchange lay odds threshold for first-leg (First Team To Score lay)
        "min_back_odds": 8,     # Sky Bet back odds threshold for first-leg (high back odds)
        "min_rating": 150,        # Minimum rating (back/lay * 100)
        "min_liquidity": 20,      # Min lay liquidity on exchange
        "hours_to_ko": 48         # Only consider matches within this many hours
    },
    "extra_legs": {
        "back_threshold": 1.5,    # Inclusive threshold for low-back odds to be considered an extra leg (<=)
        "hours_to_ko": 96,        # Independent look-ahead window for extra legs (hours)
        "max_items": 15          # Maximum number of extra-leg items returned (for paging control)
    },
    "behaviour": {
        "output_mode": "stdout",  # 'stdout' (default) or 'file'
        "out_file": "accafreeze_api_opportunities.json",  # Default output file when using file mode
        "debug": False
    }
}


def is_first_leg(back_odds, lay_odds, rating, liquidity, hours_until_ko, cfg_first):
    try:
        return (
            float(lay_odds) >= float(cfg_first["min_lay_odds"]) and
            float(back_odds) >= float(cfg_first["min_back_odds"]) and
            float(rating) >= float(cfg_first["min_rating"]) and
            float(liquidity) >= float(cfg_first["min_liquidity"]) and
            float(hours_until_ko) <= float(cfg_first["hours_to_ko"])
        )
    except Exception:
        return False


def is_extra_leg(back_odds, hours_until_ko, cfg_extra):
    try:
        # Ensure it's within the extra-legs time window and meets the back odds threshold
        hours_allowed = float(cfg_extra.get("hours_to_ko", 24))
        within_time = float(hours_until_ko) <= hours_allowed
        return float(back_odds) <= float(cfg_extra["back_threshold"]) and within_time
    except Exception:
        return False


def build_opportunity(match, outcome, skybet_odds, oc_home, oc_away, hours_until_ko):
    match_id = match.get("match_id")
    home_team = match.get("home_team")
    away_team = match.get("away_team")
    competition = match.get("competition")
    oddschecker_slug = match.get("oddschecker_slug")
    outcome_name = outcome.get("outcome_name")
    lay_odds = outcome.get("lay_odds")
    lay_site = outcome.get("lay_site")
    lay_liquidity = outcome.get("lay_liquidity")

    matched_name = match_team_names(outcome_name, skybet_odds.keys(), home_team, away_team, oc_home, oc_away)
    if not matched_name:
        return None

    back_odds = skybet_odds.get(matched_name)
    if back_odds is None:
        return None

    rating = calculate_rating(back_odds, lay_odds)

    # Derive kickoff display from hours (simple ISO for API consumers)
    kickoff_iso = None
    try:
        kickoff_iso = (datetime.now(timezone.utc) + timedelta(hours=hours_until_ko)).isoformat()
    except Exception:
        kickoff_iso = None

    return {
        "match_id": match_id,
        "competition": competition,
        "home_team": home_team,
        "away_team": away_team,
        "oddschecker_url": f"https://www.oddschecker.com/football/{oddschecker_slug}" if oddschecker_slug else None,
        "outcome_name": outcome_name,
        "display_outcome": home_team if home_team.lower() in (outcome_name or "").lower() else away_team,
        "back_odds": back_odds,
        "back_site": "Sky Bet",
        "lay_odds": lay_odds,
        "lay_site": lay_site,
        "lay_liquidity": lay_liquidity,
        "rating": rating,
        "hours_until_ko": hours_until_ko,
        "kickoff_iso": kickoff_iso,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="AccaFreeze JSON API generator")
    parser.add_argument("--out-file", dest="out_file", help="Write JSON to file instead of stdout")
    parser.add_argument("--debug", action="store_true", help="Enable debug output (prints to stderr)")
    args = parser.parse_args(argv)

    cfg_first = CONFIG["first_leg"]
    cfg_extra = CONFIG["extra_legs"]
    debug = args.debug or CONFIG["behaviour"].get("debug", False)

# Optionally suppress console output when running in stdout mode (no --out-file) and not in debug
    @contextlib.contextmanager
    def _maybe_suppress(suppress: bool):
        if not suppress:
            yield
        else:
            with open(os.devnull, 'w') as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    yield

    silent = (not args.out_file) and (not debug)

    # Run the fetch / check loop inside the suppression context so any prints from
    # imported helpers are silenced when we're serving JSON to stdout.
    try:
        with _maybe_suppress(silent):
            data = fetch_accafreeze_data()

            # Filter matches by the maximum of the first-leg and extra-leg lookahead windows
            extra_hours = cfg_extra.get("hours_to_ko", cfg_first.get("hours_to_ko", 24))
            max_hours = max(cfg_first.get("hours_to_ko", 24), extra_hours)
            qualifying = filter_matches(data, max_hours) if data else []

            results = []
            extra_list = []

            sky_cache = {}

            for item in qualifying:
                match = item["match"]
                outcome = item["outcome"]
                hours_until_ko = item.get("hours_until_ko", 0)

                oddschecker_slug = match.get("oddschecker_slug")
                oddschecker_match_id = match.get("oddschecker_match_id")
                match_id = match.get("match_id")

                # Get Sky Bet odds (cached by match_id)
                if match_id not in sky_cache:
                    sky = get_skybet_odds_for_match(oddschecker_slug, oddschecker_match_id, debug=False)
                    sky_cache[match_id] = sky
                else:
                    sky = sky_cache[match_id]

                if not sky or not sky.get("odds"):
                    continue

                sky_odds = sky.get("odds")
                oc_home = sky.get("home_team")
                oc_away = sky.get("away_team")

                opp = build_opportunity(match, outcome, sky_odds, oc_home, oc_away, hours_until_ko)
                if not opp:
                    continue

                # Classification
                classifications = []
                if is_first_leg(opp["back_odds"], opp["lay_odds"], opp["rating"], opp["lay_liquidity"], opp["hours_until_ko"], cfg_first):
                    classifications.append("first_leg")
                if is_extra_leg(opp["back_odds"], opp["hours_until_ko"], cfg_extra):
                    classifications.append("extra_leg")

                if classifications:
                    opp["classifications"] = classifications
                    results.append(opp)

                    if "extra_leg" in classifications:
                        extra_list.append(opp)

            # Optionally truncate extra_list per config
            if len(extra_list) > cfg_extra.get("max_items", 100):
                extra_list = extra_list[: cfg_extra.get("max_items", 100)]
    except Exception as e:
        # Ensure we output JSON (even when silent) describing the error
        err_output = {"generated_at": datetime.now(timezone.utc).isoformat(), "opportunities": [], "error": "exception", "exception": str(e)}
        sys.stdout.write(json.dumps(err_output, indent=2))
        return

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"total": len(results), "first_leg": sum(1 for r in results if "first_leg" in r.get("classifications", [])), "extra_leg": sum(1 for r in results if "extra_leg" in r.get("classifications", []))},
        "opportunities": results,
        "extra_legs": extra_list
    }

    # Output to file or stdout
    if args.out_file:
        with open(args.out_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        # Silent success
        return

    # Print JSON only to stdout (no other text)
    sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    from datetime import timedelta
    main()
