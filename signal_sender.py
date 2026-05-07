import requests, json, os, urllib.parse
from datetime import datetime

ANTHROPIC_KEY = os.environ['ANTHROPIC_KEY']
WA_PHONE = os.environ['WA_PHONE']
WA_APIKEY = os.environ['WA_APIKEY']

hour = datetime.utcnow().hour + 5  # rough IST
market = 'IN' if hour < 15 else 'US'

# Call Anthropic API
resp = requests.post('https://api.anthropic.com/v1/messages',
  headers={'x-api-key': ANTHROPIC_KEY,
           'anthropic-version': '2023-06-01',
           'content-type': 'application/json'},
  json={'model': 'claude-sonnet-4-20250514',
        'max_tokens': 3000,
        'tools': [{'type':'web_search_20250305','name':'web_search'}],
        'messages': [{'role':'user','content':
          f"Top 5 intraday signals for {'NSE/BSE' if market=='IN' else 'NYSE/NASDAQ'} "
          f"today {datetime.now().strftime('%Y-%m-%d')} 90%+ probability JSON only."}]})

data = resp.json()
text = ' '.join(b['text'] for b in data['content'] if b['type']=='text')
stocks = json.loads(text[text.index('['):text.rindex(']')+1])

# Build WhatsApp message
flag = '🇮🇳' if market == 'IN' else '🇺🇸'
msg = f'{flag} STOCKBOT INTRADAY SIGNALS\n'
msg += f"{datetime.now().strftime('%d %b %Y')}\n" + '-'*28 + '\n\n'
for i, s in enumerate(stocks[:5], 1):
    msg += f"#{i} {s['stockName']} ({s.get('setupType','INTRADAY')})\n"
    msg += f"Entry: {s.get('entryPrice', s.get('currentPrice',''))} "
    msg += f"Target: {s['targetPrice']} SL: {s['stopLoss']}\n"
    msg += f"Prob: {s.get('probabilityScore','90')}% Return: {s.get('expectedReturn','')}\n\n"
msg += '⚠️ Educational only. Not financial advice.'

# Send via CallMeBot (FREE)
url = (f'https://api.callmebot.com/whatsapp.php'
       f'?phone={WA_PHONE}&text={urllib.parse.quote(msg)}&apikey={WA_APIKEY}')
r = requests.get(url)
print('Sent!' if r.ok else f'Error: {r.text}')
