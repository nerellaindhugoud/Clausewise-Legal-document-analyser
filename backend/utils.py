from typing import List, Tuple, Dict, Any 
import re 
from datetime import datetime, timedelta 
from dateutil import parser as dtparser 
from langdetect import detect 
import difflib 
import math

#Minimal stopwords

STOPWORDS = { "en": set("a an and are as at be by for from has he in is it its of on that the to was were will with this these those you your yours we our us not or nor if else then than also shall may must can hereunder hereof thereof therefrom thereon".split()),
              "hi": set("और है हैं था थी थे को के का की एक यह वह होंगे हेतु तक लिए साथ करें किया जिससे द्वारा पर में नहीं या यदि तब तो तथा जबकि करना चाहिए होगा सकते".split()), 
              "te": set("మరియు ఉంది ఉన్నాయి ఒక ఇది అవి మీరు వారు నుండి కు కోసం తో లో కాదు లేదా అయితే అలాగే ఉండాలి ఉంటుంది".split()), }

DATE_REGEX = re.compile(r"\b(\d{1,2}[-/. ]\d{1,2}[-/. ]\d{2,4}|\b\w+ \d{1,2}, \d{4}\b|\b\d{4}-\d{2}-\d{2}\b)\b") 
MONEY_REGEX = re.compile(r"\b(?:USD|INR|Rs.?|₹|$)\s?\d{1,3}(?:[,\d]{0,})(?:.\d+)?\b") 
DURATION_REGEX = re.compile(r"\b(\d+\s?(days?|months?|years?))\b", re.I)

RISK_PATTERNS = [ (re.compile(r"auto[-\s]?renew|automatic renewal", re.I), "Auto-renewal present"), 
                 (re.compile(r"indemnif(y|ies|ication)\b", re.I), "Broad indemnity risk"), 
                 (re.compile(r"exclusive jurisdiction|venue\b", re.I), "Exclusive venue/jurisdiction"), 
                 (re.compile(r"unlimited liability|liability.*(unlimited|without limit)", re.I), "Uncapped liability"), 
                 (re.compile(r"non[-\s]?compete|restraint of trade", re.I), "Non-compete restriction"), ]

def detect_language(text: str) -> str: 
    try: 
        return detect(text)
    except Exception: 
        return "en"

def sentence_tokenize(text: str) -> List[str]:
     parts = re.split(r"(?<=[.!?।])\s+|\n+", text.strip()) 
     return [s.strip() for s in parts if s.strip()]

def normalize(text: str) -> List[str]:
    return re.findall(r"[\w']+", text.lower())

def summarize_extract(text: str, max_sentences: int = 5) -> str:
     lang = detect_language(text) 
     stop = STOPWORDS.get(lang, STOPWORDS["en"])
     sents = sentence_tokenize(text) 
     if not sents: 
        return ""
     freqs: Dict[str, int] = {} 
     for s in sents: 
      for w in normalize(s):
          if w not in stop and len(w) > 2: 
              freqs[w] = freqs.get(w, 0) + 1 
     if not freqs: 
        return " ".join(sents[:max_sentences]) 
     scores: List[Tuple[float, str]] = []


     for s in sents: 
      words = [w for w in normalize(s) if w in freqs] 
      if not words: 
       continue 
      score = sum(freqs[w] for w in words) / (len(words) + 1) 
      scores.append((score, s)) 
     top = {s for _, s in sorted(scores, key=lambda x: x[0], reverse=True)[:max_sentences]}
     return " ".join([s for s in sents if s in top])

def extract_clauses(text: str) -> List[str]: 
    chunks = re.split(r"\n\s*(?:\d+.|[A-Z][A-Z\s_-]{3,}|Section\s+\d+(?:.\d+))\s\n", text)
    res = [c.strip() for c in chunks if c and c.strip()] 
    if not res: 
        res = [c.strip() for c in re.split(r"\n\n+", text) if c.strip()]
    return res

def classify_contract(text: str) -> str: 
    t = text.lower() 
    if any(k in t for k in ["lease", "tenant", "landlord", "premises"]):
        return "Lease Agreement" 
    if any(k in t for k in ["non-disclosure", "confidential", "nda"]):
        return "NDA" 
    if any(k in t for k in ["employee", "employer", "salary", "benefits", "termination"]):
        return "Employment Contract" 
    if any(k in t for k in ["service level", "sla", "vendor", "client"]): 
        return "Service Agreement" 
    return "General Contract"

def keyword_qa(text: str, question: str) -> str: 
    q_words = [w for w in normalize(question) if len(w) > 2] 
    if not q_words: 
     return "Question too short." 
    best = (0, "") 
    for sent in sentence_tokenize(text): 
        score = sum(1 for qw in q_words 
if qw in sent.lower()) 
        if score > best[0]: best = (score, sent.strip()) 
    return best[1] or "Answer not found in document."

def find_entities_regex(text: str) -> Dict[str, List[str]]:
     dates = [m.group(0) for m in DATE_REGEX.finditer(text)]
     money = [m.group(0) for m in MONEY_REGEX.finditer(text)] 
     durations = [m.group(0) for m in DURATION_REGEX.finditer(text)] 
     return {"dates": list(dict.fromkeys(dates)), "money": list(dict.fromkeys(money)), "durations": list(dict.fromkeys(durations))}

def detect_risks(text: str) -> List[str]: 
    risks = []
    for pat, label in RISK_PATTERNS: 
     if pat.search(text): risks.append(label) 
    return risks

def upcoming_alerts(text: str, days_ahead: int = 60) -> List[Dict[str, Any]]: 
    alerts = [] 
    now = datetime.now() 
    for m in DATE_REGEX.finditer(text): 
        dtxt = m.group(0) 
        try: 
            d = dtparser.parse(dtxt, dayfirst=False, fuzzy=True) 
            if now <= d <= now + timedelta(days=days_ahead): 
                alerts.append({"type": "deadline", "when": d.isoformat(), "excerpt": dtxt}) 
        except Exception: 
            continue 
    for m in DURATION_REGEX.finditer(text): 
        span = m.span() 
        ctx = text[max(0, span[0]-60):min(len(text), span[1]+60)] 
        if re.search(r"renew|term|expire", ctx, re.I): 
            alerts.append({"type": "renewal-window", "duration": m.group(0), "context": ctx.strip()}) 
    return alerts

def jaccard(a: set, b: set) -> float: 
    if not a and not b: 
        return 1.0 
    return len(a & b) / max(1, len(a | b))

def cosine_sim(a: Dict[str, int], b: Dict[str, int]) -> float:
     keys = set(a) | set(b)
     dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys) 
     na = math.sqrt(sum(v*v for v in a.values())) 
     nb = math.sqrt(sum(v*v for v in b.values())) 
     if na == 0 or nb == 0:
         return 0.0 
     return dot / (na * nb)

def bow(text: str, stop: set) -> Dict[str, int]:
     counts: Dict[str, int] = {}
     for w in normalize(text): 
        if w not in stop and len(w) > 2: 
            counts[w] = counts.get(w, 0) + 1 
     return counts

def compare_contracts(text_a: str, text_b: str) -> Dict[str, Any]: 
    lang_a = detect_language(text_a) 
    stop_a = STOPWORDS.get(lang_a, STOPWORDS["en"]) 
    lang_b = detect_language(text_b) 
    stop_b = STOPWORDS.get(lang_b, STOPWORDS["en"])

    clauses_a = extract_clauses(text_a)
    clauses_b = extract_clauses(text_b)

    bow_a = bow(text_a, stop_a)
    bow_b = bow(text_b, stop_b)
    cos = cosine_sim(bow_a, bow_b)

    diff = "\n".join(difflib.unified_diff(text_a.splitlines(), text_b.splitlines(), fromfile="A", tofile="B", lineterm=""))

    overlaps: List[Dict[str, Any]] = []
    for i, ca in enumerate(clauses_a):
      set_a = set(normalize(ca))
      best = (0.0, -1)
      for j, cb in enumerate(clauses_b):
        set_b = set(normalize(cb))
        sim = jaccard(set_a, set_b)
        if sim > best[0]:
            best = (sim, j)
    overlaps.append({"clause_a_index": i, "best_b_index": best[1], "similarity": round(best[0], 3)})

    return {
      "lang_a": lang_a,
      "lang_b": lang_b,
      "cosine_similarity": round(cos, 3),
      "diff": diff,
      "overlaps": overlaps[:50],
    }

#==============================
