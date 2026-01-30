# Discord Alert Formatting Guide

## Where to Customize Discord Alerts

The Discord alert formatting is in the `send_discord_alert()` function in [accafreeze.py](accafreeze.py).

**Lines 374-419** contain the embed builder.

## Current Format Structure

```python
def send_discord_alert(opportunity, sites):
    """Send alert to all configured Discord channels"""
    if not sites:
        print("[DISCORD] No sites configured")
        return False
    
    # Build embed  <-- START OF FORMATTING SECTION
    embed = {
        "title": "⚽ AccaFreeze Opportunity",              # Main title
        "description": f"**{opportunity['home_team']} v {opportunity['away_team']}**",  # Match
        "color": 0x00ff00,  # Green (hex color)
        "fields": [
            # Each field is a section in the embed
            {
                "name": "Competition",
                "value": opportunity['competition'],
                "inline": True  # Shows side-by-side with other inline fields
            },
            {
                "name": "Kick Off",
                "value": f"{opportunity['hours_until_ko']:.1f} hours",
                "inline": True
            },
            {
                "name": "Outcome",
                "value": opportunity['outcome'],
                "inline": False  # Takes full width
            },
            {
                "name": "Back (Sky Bet)",
                "value": f"**{opportunity['back_odds']}**",
                "inline": True
            },
            {
                "name": f"Lay ({opportunity['lay_site']})",
                "value": f"**{opportunity['lay_odds']}** (£{opportunity['lay_liquidity']})",
                "inline": True
            },
            {
                "name": "Rating",
                "value": f"**{opportunity['rating']:.2f}%**",
                "inline": True
            },
            {
                "name": "OddsChecker",
                "value": f"[View Market]({opportunity['oddschecker_url']})",
                "inline": False
            }
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }  # <-- END OF FORMATTING SECTION
    
    payload = {
        "embeds": [embed]
    }
    # ... rest of function sends the alert
```

## Customization Options

### 1. Change Title
**Current:** `"⚽ AccaFreeze Opportunity"`

**Examples:**
```python
"title": "🚨 ARBING ALERT"
"title": "💰 First Team To Score"
"title": "⚡ AccaFreeze - Sky Bet vs Exchange"
```

### 2. Change Color
**Current:** `0x00ff00` (green)

**Examples:**
```python
"color": 0xff0000,  # Red
"color": 0x0000ff,  # Blue
"color": 0xffa500,  # Orange
"color": 0xffff00,  # Yellow
"color": 0x800080,  # Purple
"color": 0x00ffff,  # Cyan
```

Or make it dynamic based on rating:
```python
# Add this before embed = {...}
if opportunity['rating'] >= 150:
    color = 0xff0000  # Red for high ratings
elif opportunity['rating'] >= 130:
    color = 0xffa500  # Orange for medium
else:
    color = 0x00ff00  # Green for normal

# Then use:
"color": color,
```

### 3. Change Description
**Current:** `f"**{opportunity['home_team']} v {opportunity['away_team']}**"`

**Examples:**
```python
# Add emojis
"description": f"⚽ **{opportunity['home_team']}** vs **{opportunity['away_team']}**"

# Add competition
"description": f"**{opportunity['home_team']} v {opportunity['away_team']}**\n_{opportunity['competition']}_"

# Add rating in description
"description": f"**{opportunity['home_team']} v {opportunity['away_team']}**\n🔥 {opportunity['rating']:.1f}% Rating"
```

### 4. Add/Remove/Reorder Fields

**Add a field:**
```python
# Add this to the fields array
{
    "name": "Stake Suggestion",
    "value": "£50-100 recommended",
    "inline": False
}
```

**Remove a field:**
Just delete the entire `{...}` block from the fields array.

**Reorder fields:**
Move the field blocks around in the list. Fields appear in the order listed.

### 5. Change Field Formatting

**Make odds more prominent:**
```python
{
    "name": "🔵 Back (Sky Bet)",
    "value": f"**{opportunity['back_odds']}** ⬅️ BACK THIS",
    "inline": True
}
```

**Add profit calculation:**
```python
# Calculate estimated profit (simplified)
stake = 100
back_return = stake * opportunity['back_odds']
lay_liability = stake * (opportunity['lay_odds'] - 1)
profit = back_return - stake - lay_liability

{
    "name": "Est. Profit (£100 stake)",
    "value": f"£{profit:.2f}",
    "inline": True
}
```

**Format time differently:**
```python
# Current: "12.5 hours"
# Alternative: Show actual kickoff time
from datetime import timedelta
kickoff_time = datetime.now(timezone.utc) + timedelta(hours=opportunity['hours_until_ko'])

{
    "name": "Kick Off",
    "value": f"{kickoff_time.strftime('%H:%M')} ({opportunity['hours_until_ko']:.1f}h)",
    "inline": True
}
```

### 6. Add Thumbnail or Image

Add after the `"color"` line:
```python
"thumbnail": {
    "url": "https://your-image-url.com/logo.png"
},
```

### 7. Add Footer

Add after the `"fields"` array:
```python
"footer": {
    "text": "AccaFreeze Scanner | Sky Bet vs Exchange"
},
```

### 8. Change Inline Layout

**Current layout:**
```
[Competition] [Kick Off]
[Outcome - full width]
[Back] [Lay] [Rating]
[OddsChecker - full width]
```

**Stack vertically (all full width):**
Change all `"inline": True` to `"inline": False`

**Compact (all inline):**
Change all `"inline": False` to `"inline": True`

### 9. Add Content Outside Embed

To add text before/after the embed:
```python
payload = {
    "content": "@here New opportunity! 🚨",  # Plain text before embed
    "embeds": [embed]
}
```

### 10. Multiple Embeds

Send multiple embeds in one message:
```python
embed2 = {
    "title": "How to Place This Bet",
    "description": "1. Back on Sky Bet\n2. Lay on Exchange\n3. Lock in profit",
    "color": 0x0000ff
}

payload = {
    "embeds": [embed, embed2]  # First embed, then second
}
```

## Complete Example: Aggressive Format

```python
# Calculate profit
stake = 100
profit = (stake * opportunity['back_odds']) - stake - (stake * (opportunity['lay_odds'] - 1))

# Dynamic color based on rating
if opportunity['rating'] >= 150:
    color = 0xff0000  # Red
elif opportunity['rating'] >= 135:
    color = 0xffa500  # Orange
else:
    color = 0x00ff00  # Green

embed = {
    "title": "🚨 ARBING ALERT 🚨",
    "description": f"🔥 **{opportunity['home_team']} vs {opportunity['away_team']}**\n_{opportunity['competition']}_",
    "color": color,
    "fields": [
        {
            "name": "⏰ Kick Off",
            "value": f"**{opportunity['hours_until_ko']:.1f} hours**",
            "inline": True
        },
        {
            "name": "📊 Rating",
            "value": f"🔥 **{opportunity['rating']:.1f}%**",
            "inline": True
        },
        {
            "name": "⚽ Outcome",
            "value": f"**{opportunity['outcome']}** to score first",
            "inline": False
        },
        {
            "name": "🔵 BACK (Sky Bet)",
            "value": f"**{opportunity['back_odds']}**",
            "inline": True
        },
        {
            "name": f"🔴 LAY ({opportunity['lay_site']})",
            "value": f"**{opportunity['lay_odds']}**\n(£{opportunity['lay_liquidity']} available)",
            "inline": True
        },
        {
            "name": "💰 Est. Profit",
            "value": f"**£{profit:.2f}** (£100 stake)",
            "inline": True
        },
        {
            "name": "🔗 Links",
            "value": f"[View on OddsChecker]({opportunity['oddschecker_url']})",
            "inline": False
        }
    ],
    "footer": {
        "text": "AccaFreeze Scanner • Act fast!"
    },
    "timestamp": datetime.now(timezone.utc).isoformat()
}

payload = {
    "content": "@everyone",  # Ping everyone
    "embeds": [embed]
}
```

## Testing Changes

After modifying the embed, test with:
```bash
python demo_accafreeze_discord.py
```

Or uncomment the send line in the demo to send a real test alert.

## Discord Embed Limits

- Title: 256 characters max
- Description: 4096 characters max
- Fields: 25 fields max
- Field name: 256 characters max
- Field value: 1024 characters max
- Footer text: 2048 characters max
- Total embed: 6000 characters max

## Resources

- [Discord Embed Visualizer](https://leovoel.github.io/embed-visualizer/) - Preview your embeds
- [Discord API Docs](https://discord.com/developers/docs/resources/channel#embed-object) - Official embed reference
- [Color Picker](https://htmlcolorcodes.com/) - Get hex color codes
