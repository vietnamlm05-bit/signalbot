"""Điểm tin tức -1..1 cho từng coin. Có ANTHROPIC_API_KEY thì dùng LLM, không thì dùng từ khóa."""
import calendar, os, re, time
import requests
from config import NEWS_FEEDS, COIN_WORDS

POS = ["surge", "rally", "soar", "jump", "gain", "record high", "approval", "approved",
       "adopt", "inflow", "bullish", "upgrade", "partnership"]
NEG = ["crash", "plunge", "drop", "fall", "hack", "exploit", "ban", "lawsuit", "sue",
       "outflow", "bearish", "liquidat", "fraud", "sell-off", "selloff"]

def fetch_headlines(hours=24):
    import feedparser
    cutoff = time.time() - hours * 3600
    out = []
    for url in NEWS_FEEDS:
        try:
            for e in feedparser.parse(url).entries[:30]:
                p = e.get("published_parsed")
                if p and calendar.timegm(p) < cutoff:
                    continue
                out.append(e.get("title", ""))
        except Exception as ex:
            print("RSS lỗi:", url, ex)
    return out

def _relevant(titles, coin):
    pat = re.compile(r"\b(" + "|".join(COIN_WORDS[coin]) + r")\b", re.I)
    return [t for t in titles if pat.search(t)]

def keyword_score(titles):
    if not titles:
        return 0.0
    s = 0
    for t in titles:
        low = t.lower()
        s += sum(w in low for w in POS) - sum(w in low for w in NEG)
    return max(-1.0, min(1.0, s / len(titles)))

def llm_score(titles, coin):
    prompt = ("Rate the short-term market sentiment for " + coin +
              " from these headlines. Reply with ONLY one number from -1 to 1.\n\n" +
              "\n".join("- " + t for t in titles[:20]))
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 10,
              "messages": [{"role": "user", "content": prompt}]})
    r.raise_for_status()
    return max(-1.0, min(1.0, float(r.json()["content"][0]["text"].strip())))

def news_scores(symbols):
    titles = fetch_headlines()
    scores = {}
    for sym in symbols:
        coin = sym.split("/")[0]
        rel = _relevant(titles, coin)
        score = keyword_score(rel)
        if rel and os.getenv("ANTHROPIC_API_KEY"):
            try:
                score = llm_score(rel, coin)
            except Exception as ex:
                print("LLM lỗi, dùng từ khóa:", ex)
        scores[coin] = score
    return scores
