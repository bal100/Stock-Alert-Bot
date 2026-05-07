import requests, json, os, re, urllib.parse
from datetime import datetime

ANTHROPIC_KEY    = os.environ["ANTHROPIC_KEY"]
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

utc_hour    = datetime.utcnow().hour
market      = "IN" if utc_hour < 10 else "US"
market_name = "NSE/BSE India" if market == "IN" else "NYSE/NASDAQ US"
date_str    = datetime.now().strftime("%d %b %Y")

print(f"Market : {market_name}")
print(f"Date   : {date_str}")
print(f"UTC hr : {utc_hour}")
print("─" * 40)

# ── Step 1: Call Anthropic API ────────────────────────────────────────────────
prompt = f"""Today is {date_str}. Give me TOP 5 intraday stock signals for {market_name}.

Search for: today's top movers, volume leaders, breakout setups, news catalysts.
Only stocks with 90%+ probability. Tight stop loss (1-2%). Entry and exit times.

YOU MUST RETURN ONLY A RAW JSON ARRAY. No markdown. No explanation. No code fences.
Start your response with [ and end with ]

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
]"""

print("Calling Anthropic API...")
resp = requests.post(
    "https://api.anthropic.com/v1/messages",
    headers={
        "x-api-key":         ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json"
    },
    json={
        "model":      "claude-sonnet-4-20250514",
        "max_tokens": 4000,
        "tools":      [{"type": "web_search_20250305", "name": "web_search"}],
        "messages":   [{"role": "user", "content": prompt}]
    },
    timeout=180
)

print(f"API status : {resp.status_code}")

if not resp.ok:
    print(f"API ERROR  : {resp.text}")
    exit(1)

data = resp.json()

# ── Step 2: Extract all text blocks ──────────────────────────────────────────
print(f"Content blocks: {len(data.get('content', []))}")
for i, block in enumerate(data.get("content", [])):
    print(f"  Block {i}: type={block.get('type')} ", end="")
    if block.get("type") == "text":
        print(f"len={len(block.get('text',''))}")
    elif block.get("type") == "tool_use":
        print(f"tool={block.get('name')}")
    else:
        print()

texts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
full  = "\n".join(texts).strip()

print(f"\nFull text length: {len(full)}")
print("── First 500 chars ──")
print(full[:500])
print("── Last 200 chars ──")
print(full[-200:])
print("─" * 40)

# ── Step 3: Robust JSON extraction ───────────────────────────────────────────
stocks = None

# Method A: strip markdown fences then parse
cleaned = re.sub(r"```(?:json)?", "", full).strip()
try:
    start = cleaned.find("[")
    end   = cleaned.rfind("]") + 1
    if start != -1 and end > 0:
        stocks = json.loads(cleaned[start:end])
        print(f"Method A OK — {len(stocks)} stocks")
except Exception as e:
    print(f"Method A failed: {e}")

# Method B: regex extract first [...] block
if not stocks:
    try:
        match = re.search(r"\[\s*\{.*?\}\s*\]", full, re.DOTALL)
        if match:
            stocks = json.loads(match.group())
            print(f"Method B OK — {len(stocks)} stocks")
    except Exception as e:
        print(f"Method B failed: {e}")

# Method C: find outermost [ ] even with nesting
if not stocks:
    try:
        depth = 0
        s_idx = None
        for idx, ch in enumerate(full):
            if ch == "[" and depth == 0:
                s_idx = idx
                depth = 1
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0 and s_idx is not None:
                    stocks = json.loads(full[s_idx:idx+1])
                    print(f"Method C OK — {len(stocks)} stocks")
                    break
    except Exception as e:
        print(f"Method C failed: {e}")

if not stocks:
    print("\nERROR: Could not parse JSON from response.")
    print("Full response saved above for debugging.")
    exit(1)

print(f"\n✅ Parsed {len(stocks)} signals successfully")

# ── Step 4: Build Telegram message ───────────────────────────────────────────
flag = "🇮🇳" if market == "IN" else "🇺🇸"
msg  = f"{flag} *STOCKBOT AI — INTRADAY SIGNALS*\n"
msg += f"📍 *{market_name.upper()}*\n"
msg += f"📅 {date_str}\n"
msg += "─" * 26 + "\n\n"

for i, s in enumerate(stocks[:5], 1):
    mb   = "🚀 *MULTIBAGGER ALERT\\!*\n" if s.get("multibaggerAlert") else ""
    prob = s.get("probabilityScore", "90")
    name = s.get("stockName", "")
    setup = s.get("setupType", "INTRADAY")

    msg += f"*\\#{i} {escape_md(name)}* \\({setup}\\)\n"
    msg += mb
    msg += f"📌 `{s.get('symbol','')}` \\| {s.get('exchange','')}\n"
    msg += f"💰 Entry: {s.get('entryPrice','')}\n"
    msg += f"🎯 Target: {s.get('targetPrice','')}\n"
    msg += f"🛑 Stop Loss: {s.get('stopLoss','')}\n"
    msg += f"📊 R:R: {s.get('riskRewardRatio','1:2+')}  Return: *{s.get('expectedReturn','')}*\n"
    msg += f"🎯 Probability: *{prob}%*\n"
    ew = s.get("entryWindow", "")
    eb = s.get("exitBy", "")
    if ew: msg += f"⏱ Entry window: {ew}\n"
    if eb: msg += f"🔔 Exit by: {eb}\n"
    catalyst = s.get("newsCatalyst") or s.get("whyBuy", "")
    if catalyst:
        msg += f"📰 {escape_md(catalyst[:120])}\n"
    msg += "\n"

msg += "─" * 26 + "\n"
msg += "⚡ StockBot AI Pro\n"
msg += "⚠️ _Educational only\\. Not financial advice\\. DYOR\\._"

# ── Step 5: Send via Telegram ─────────────────────────────────────────────────
print("Sending Telegram message...")
tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
r = requests.post(tg_url, json={
    "chat_id":    TELEGRAM_CHAT_ID,
    "text":       msg,
    "parse_mode": "MarkdownV2"
}, timeout=30)

print(f"Telegram status: {r.status_code}")
if r.ok:
    print("✅ Telegram message sent successfully!")
else:
    print(f"❌ Telegram failed: {r.text}")
    # Retry with plain text (no markdown) if formatting caused issues
    print("Retrying with plain text...")
    plain = re.sub(r"[*_`\\]", "", msg)
    r2 = requests.post(tg_url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text":    plain
    }, timeout=30)
    if r2.ok:
        print("✅ Sent as plain text!")
    else:
        print(f"❌ Plain text also failed: {r2.text}")
        exit(1)


def escape_md(text):
    """Escape special chars for Telegram MarkdownV2"""
    special = r"_*[]()~`>#+-=|{}.!"
    return re.sub(r"([" + re.escape(special) + r"])", r"\\\1", str(text))
