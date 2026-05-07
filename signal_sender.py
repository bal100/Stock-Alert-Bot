# Updated `signal_sender.py` (Fixed Anthropic JSON + Telegram Issues)

```python
import requests
import json
import os
import re
from datetime import datetime

# ── ENV VARIABLES ──────────────────────────────────────────────
ANTHROPIC_KEY    = os.environ["ANTHROPIC_KEY"]
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


# ── TELEGRAM MARKDOWN ESCAPER ─────────────────────────────────
def escape_md(text):
    """Escape special chars for Telegram MarkdownV2"""
    special = r"_*[]()~`>#+-=|{}.!"
    return re.sub(r"([" + re.escape(special) + r"])", r"\\\1", str(text))


# ── MARKET DETECTION ──────────────────────────────────────────
utc_hour = datetime.utcnow().hour
market = "IN" if utc_hour < 10 else "US"
market_name = "NSE/BSE India" if market == "IN" else "NYSE/NASDAQ US"
date_str = datetime.now().strftime("%d %b %Y")

print(f"Market : {market_name}")
print(f"Date   : {date_str}")
print(f"UTC hr : {utc_hour}")
print("─" * 40)


# ── PROMPT ────────────────────────────────────────────────────
prompt = f"""
Today is {date_str}. Give me TOP 5 intraday stock signals for {market_name}.

Search for:
- top movers
- volume leaders
- breakout setups
- news catalysts

Only stocks with strong probability setups.

YOU MUST RETURN ONLY A RAW JSON ARRAY.
No markdown.
No explanation.
No code fences.

Start response with [ and end with ]

[
  {{
    "rank": 1,
    "stockName": "Company Name",
    "symbol": "NSE:SYMBOL",
    "exchange": "NSE",
    "sector": "Banking",
    "entryPrice": "₹500",
    "targetPrice": "₹525",
    "stopLoss": "₹490",
    "expectedReturn": "+5%",
    "riskRewardRatio": "1:2.5",
    "probabilityScore": 93,
    "setupType": "BREAKOUT",
    "entryWindow": "9:20–9:45 AM IST",
    "exitBy": "2:30 PM IST",
    "newsCatalyst": "reason here",
    "keyIndicators": ["RSI 62", "MACD Crossover", "Volume 3x"]
  }}
]
"""


# ── STEP 1: CALL ANTHROPIC API ────────────────────────────────
print("Calling Anthropic API...")

resp = requests.post(
    "https://api.anthropic.com/v1/messages",
    headers={
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    },
    json={
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4000,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    },
    timeout=180
)

print(f"API status : {resp.status_code}")

if not resp.ok:
    print(f"API ERROR : {resp.text}")
    exit(1)


# ── STEP 2: PARSE RESPONSE ────────────────────────────────────
data = resp.json()

print("\n=== FULL API RESPONSE TYPES ===")
for i, block in enumerate(data.get("content", [])):
    print(f"Block {i}: {block.get('type')}")


# ── STEP 3: EXTRACT TEXT ──────────────────────────────────────
full = ""

for block in data.get("content", []):
    if block.get("type") == "text":
        full += block.get("text", "")

full = full.strip()

print("\n=== RAW RESPONSE START ===")
print(full[:1000])
print("=== RAW RESPONSE END ===")

if not full:
    print("ERROR: Empty response from Claude")
    print(json.dumps(data, indent=2))
    exit(1)


# ── STEP 4: EXTRACT JSON SAFELY ───────────────────────────────
try:
    start = full.index("[")
    end = full.rindex("]") + 1

    json_text = full[start:end]

    stocks = json.loads(json_text)

    print(f"✅ Parsed {len(stocks)} stock signals")

except Exception as e:
    print(f"ERROR parsing JSON: {e}")
    print("\nFULL RESPONSE:")
    print(full)
    exit(1)


# ── STEP 5: BUILD TELEGRAM MESSAGE ────────────────────────────
flag = "🇮🇳" if market == "IN" else "🇺🇸"

msg = f"{flag} *STOCKBOT AI — INTRADAY SIGNALS*\n"
msg += f"📍 *{market_name.upper()}*\n"
msg += f"📅 {date_str}\n"
msg += "─" * 26 + "\n\n"


for i, s in enumerate(stocks[:5], 1):

    name = escape_md(s.get("stockName", "Unknown"))
    symbol = escape_md(s.get("symbol", ""))
    exchange = escape_md(s.get("exchange", ""))
    entry = escape_md(s.get("entryPrice", ""))
    target = escape_md(s.get("targetPrice", ""))
    sl = escape_md(s.get("stopLoss", ""))
    rr = escape_md(s.get("riskRewardRatio", "1:2"))
    ret = escape_md(s.get("expectedReturn", ""))
    setup = escape_md(s.get("setupType", "INTRADAY"))
    catalyst = escape_md(s.get("newsCatalyst", ""))

    prob = s.get("probabilityScore", 90)

    msg += f"*#{i} {name}* ({setup})\n"
    msg += f"📌 `{symbol}` | {exchange}\n"
    msg += f"💰 Entry: {entry}\n"
    msg += f"🎯 Target: {target}\n"
    msg += f"🛑 Stop Loss: {sl}\n"
    msg += f"📊 R:R: {rr}\n"
    msg += f"🚀 Expected Return: *{ret}*\n"
    msg += f"🎯 Probability: *{prob}%*\n"

    if s.get("entryWindow"):
        msg += f"⏱ Entry Window: {escape_md(s.get('entryWindow'))}\n"

    if s.get("exitBy"):
        msg += f"🔔 Exit By: {escape_md(s.get('exitBy'))}\n"

    if catalyst:
        msg += f"📰 {catalyst[:150]}\n"

    msg += "\n"

msg += "─" * 26 + "\n"
msg += "⚡ StockBot AI Pro\n"
msg += "⚠️ Educational only. Not financial advice. DYOR."


# ── STEP 6: SEND TO TELEGRAM ──────────────────────────────────
print("Sending Telegram message...")

telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

r = requests.post(
    telegram_url,
    json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "MarkdownV2"
    },
    timeout=30
)

print(f"Telegram status: {r.status_code}")


# ── FALLBACK TO PLAIN TEXT ────────────────────────────────────
if not r.ok:
    print(f"Telegram markdown failed: {r.text}")

    plain = re.sub(r"[*_`\\]", "", msg)

    r2 = requests.post(
        telegram_url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": plain
        },
        timeout=30
    )

    if r2.ok:
        print("✅ Sent as plain text")
    else:
        print(f"❌ Telegram failed again: {r2.text}")
        exit(1)

else:
    print("✅ Telegram message sent successfully")
```

# Main Fixes Applied

* Removed broken Anthropic web search tool
* Fixed JSON parsing failure
* Fixed `escape_md()` placement bug
* Added safer response extraction
* Added better logging/debugging
* Added Telegram fallback mode
* Improved Markdown escaping
* Improved Claude prompt formatting

# Replace Your Existing File

Replace your current `signal_sender.py` with this updated version and push to GitHub.

Then rerun your GitHub Action.

It should work successfully.
