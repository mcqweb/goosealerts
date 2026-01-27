# Alert Configuration Guide

## Overview

The alert system now supports multiple Discord destinations per alert type using JSON configuration files. This allows you to send the same alert to different channels with different thresholds, bot tokens, colors, and prefixes.

## Configuration Files

### alert_config.live.json
Your active configuration file. This is loaded at runtime. Edit this file to manage your alert destinations.

### alert_config.json
Template/example configuration showing all available options.

## Environment Variables Still Required

These environment variables are still needed in your `.env` file:

### Essential Variables
- `DISCORD_BOT_TOKEN` - Main Discord bot token (referenced by bot_token_env in config)
- Any additional bot tokens you reference in alert_config (e.g., `DISCORD_BOT_TOKEN_SMARKETS`)
- `NORD_USER`, `NORD_PWD`, `NORD_LOCATION` - VPN credentials
- `BETFAIR_*` - Betfair API credentials
- `WILLIAMHILL_USERNAME`, `WILLIAMHILL_PASSWORD` - William Hill credentials

### Feature Flags (Keep These)
- `ENABLE_VIRGIN_GOOSE` - Enable/disable Virgin Bet alerts
- `ENABLE_ODDSCHECKER` - Enable/disable OddsChecker alerts
- `ENABLE_WILLIAMHILL` - Enable/disable William Hill alerts
- `ENABLE_LADBROKES` - Enable/disable Ladbrokes alerts
- `ENABLE_ADDITIONAL_EXCHANGES` - Enable/disable exchange odds fetching
- `PREFER_WEBSOCKET_DATA` - Prefer websocket data
- `ENABLE_KWIFF` - Enable/disable Kwiff
- `KWIFF_COUNTRY` - Kwiff country code

### Operational Settings (Keep These)
- `WINDOW_MINUTES` - Match kickoff window (default: 90)
- `POLL_SECONDS` - Loop interval (default: 60)
- `VIRGIN_ODDS_CACHE_DURATION` - Virgin odds cache duration (default: 300)
- `WH_PRICING_MODE` - William Hill pricing mode (1 or 2)
- `VERBOSE_TIMING` - Enable timing logs
- `TEST_PRICE_OFFSET` - Price offset for testing
- `GOOSE_MIN_ODDS` - Minimum odds for goose alerts
- `DISCORD_ENABLED` - Master switch for Discord posting

### Environment Variables NO LONGER NEEDED
These are now configured in alert_config.live.json:
- ❌ `GBP_THRESHOLD_GOOSE` → Use `min_liquidity` in config
- ❌ `GBP_ARB_THRESHOLD` → Use `min_liquidity` in config
- ❌ `GBP_WH_THRESHOLD` → Use `min_liquidity` in config
- ❌ `GBP_LADBROKES_THRESHOLD` → Use `min_liquidity` in config
- ❌ `LADBROKES_REFUND_OFFER_THRESHOLD` → Use `threshold` in config
- ❌ `DISCORD_GOOSE_CHANNEL_ID` → Use `channel_id` in config
- ❌ `DISCORD_ARB_CHANNEL_ID` → Use `channel_id` in config
- ❌ `DISCORD_WH_CHANNEL_ID` → Use `channel_id` in config
- ❌ `DISCORD_WH_SMARKETS_CHANNEL_ID` → Use `channel_id` in config
- ❌ `DISCORD_LADBROKES_CHANNEL_ID` → Use `channel_id` in config
- ❌ `DISCORD_LADBROKES_CORAL_CHANNEL_ID` → Use `channel_id` in config
- ❌ `DISCORD_LADBROKES_BETGET_CHANNEL_ID` → Use `channel_id` in config

## Configuration Structure

### Alert Types

- `goose` - Virgin Bet Goal/Assist + SOT combos
- `arb` - OddsChecker arbitrage opportunities
- `williamhill` - William Hill bet builder combos
- `ladbrokes` - Ladbrokes regular arbs (≥100%)
- `ladbrokes_coral` - Coral refund offer sub-arbs (offer ID 7)
- `ladbrokes_betget` - Ladbrokes refund offer sub-arbs (offer ID 9)

### Destination Properties

#### Required
- `channel_id` - Discord channel ID (string)
- `bot_token_env` - Environment variable name containing bot token (string)

#### Optional
- `name` - Human-readable destination name (string)
- `threshold` - Minimum rating percentage required (number, default: 100)
- `min_liquidity` - Minimum liquidity in GBP (number)
- `enabled` - Enable/disable this destination (boolean, default: true)
- `prefix` - Alert prefix like "[LAD]" (string)
- `color` - Hex color code (string like "0xF01E28")
- `offer_id` - Specific offer ID to match (number, for special offers)
- `smarkets_only` - Only send Smarkets alerts (boolean, for WH)
- `description` - Human-readable description (string)

## Example: Multiple Destinations

```json
"ladbrokes": [
  {
    "name": "Main Ladbrokes Channel",
    "channel_id": "1234567890",
    "bot_token_env": "DISCORD_BOT_TOKEN",
    "threshold": 100,
    "min_liquidity": 20,
    "enabled": true,
    "prefix": "[LAD]",
    "color": "0xF01E28"
  },
  {
    "name": "Premium Ladbrokes Channel",
    "channel_id": "0987654321",
    "bot_token_env": "DISCORD_BOT_TOKEN_PREMIUM",
    "threshold": 95,
    "min_liquidity": 50,
    "enabled": true,
    "prefix": "[LAD-PRO]",
    "color": "0xFFD700"
  }
]
```

This configuration will:
1. Send alerts ≥100% to the main channel
2. Send alerts ≥95% to the premium channel (using a different bot)
3. Use different prefixes to distinguish them

## How It Works

1. **Config Loading**: On startup, `alert_config.live.json` is loaded
2. **Threshold Optimization**: The system finds the lowest threshold across all destinations
3. **Early Filtering**: Only calculates odds if they could meet the lowest threshold
4. **Distribution**: Sends to each destination that meets its specific criteria

## Adding New Destinations

1. Edit `alert_config.live.json`
2. Add new destination object to the appropriate alert type array
3. Restart the script (config is loaded at startup)

## Disabling Destinations

Set `"enabled": false` in the destination config. This is better than deleting because you keep the configuration for later.

## Testing

Start with one destination per alert type, then add more once you verify it works.

## Troubleshooting

- **"Alert config file not found"** - Create `alert_config.live.json` or rename `alert_config.json`
- **No alerts sent** - Check `enabled: true` and verify bot tokens in .env
- **Wrong channel** - Verify `channel_id` matches Discord channel ID
- **Threshold not working** - Ensure `threshold` is a number, not a string

## Migration from .env

Your old .env settings have been converted to `alert_config.live.json`. You can now remove the old channel/threshold variables from .env and manage everything in the JSON file.
