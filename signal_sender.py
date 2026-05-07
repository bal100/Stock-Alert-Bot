import requests, json, os, urllib.parse
from datetime import datetime

ANTHROPIC_KEY   = os.environ["ANTHROPIC_KEY"]
TELEGRAM_TOKEN  = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

utc_hour = datetime.utcnow().hour
market = "IN" if utc_hour < 10 else "US"
market_name = "NSE/BSE India" if market == "IN" else "NYSE/NASDAQ US"
date_str = datetime.now().strftime("%d %b %Y")

print(f"Running signals for: {market_name} on {date_str}")

# ── Call Anthropic API ────────────────────────────────────────────────────────
prompt = f"""Today is {date_str}. Give me the TOP 5 intraday stock signals for {market_name}.
Search live data for: today's volume leaders, breakout setups, news catalysts, technical setups.
Only include stocks with 90%+ probability. Return ONLY a JSON array with these fields per stock:
stockName, symbol, exchange, sector, entryPrice, targetPrice, stopLoss, expectedReturn,
riskRewardRatio, probabilityScore, setupType, entryWindow, exitBy, newsCatalyst, keyIndicators (array)."""

resp = requests.post(
    "https://api.anthropic.com/v1/messages",
    headers={
        "x-api-key":         ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json"
    },
    json={
        "model":      "claude-sonnet-4-20250514",
        "max_tokens": 3000,
        "tools":      [{"type": "web_search_20250305", "name": "web_search"}],
        "messages":   [{"role": "user", "content": prompt}]
    },
    timeout=120
)

data  = resp.json()
texts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
full  = " ".join(texts)

start = full.find("[")
end   = full.rfind("]") + 1
if start == -1 or end == 0:
    print("ERROR: No JSON found"); print(full[:500]); exit(1)

stocks = json.loads(full[start:end])
print(f"Got {len(stocks)} signals")

# ── Build message ─────────────────────────────────────────────────────────────
flag = "🇮🇳" if market == "IN" else "🇺🇸"
msg  = f"{flag} *STOCKBOT AI — INTRADAY SIGNALS*\n"
msg += f"📍 {market_name.upper()}\n"
msg += f"📅 {date_str}\n"
msg += "─" * 28 + "\n\n"

for i, s in enumerate(stocks[:5], 1):
    mb   = "🚀 *MULTIBAGGER ALERT!*\n" if s.get("multibaggerAlert") else ""
    prob = s.get("probabilityScore", "90")
    msg += f"*#{i} {s['stockName']}* ({s.get('setupType','INTRADAY')})\n"
    msg += mb
    msg += f"📌 `{s['symbol']}` | 🏦 {s.get('exchange','')}\n"
    msg += f"💰 Entry: {s.get('entryPrice','')}\n"
    msg += f"🎯 Target: {s.get('targetPrice','')}\n"
    msg += f"🛑 Stop Loss: {s.get('stopLoss','')}\n"
    msg += f"📊 R:R = {s.get('riskRewardRatio','1:2+')}  Return: *{s.get('expectedReturn','')}*\n"
    msg += f"🎯 Probability: *{prob}%*\n"
    if s.get("entryWindow"):
        msg += f"⏱ Entry: {s['entryWindow']}"
    if s.get("exitBy"):
        msg += f"  Exit by: {s['exitBy']}"
    msg += "\n"
    msg += f"📰 {s.get('newsCatalyst', s.get('whyBuy',''))}\n\n"

msg += "─" * 28 + "\n"
msg += "⚡ StockBot AI Pro\n"
msg += "⚠️ _Educational only. Not financial advice. DYOR._"

print("\n── Message Preview ──")
print(msg[:300])

# ── Send via Telegram (completely FREE, no limits) ────────────────────────────
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
r = requests.post(url, json={
    "chat_id":    TELEGRAM_CHAT_ID,
    "text":       msg,
    "parse_mode": "Markdown"
}, timeout=30)

if r.ok:
    print("✅ Telegram message sent successfully!")
else:
    print(f"❌ Failed: {r.status_code} — {r.text}")
