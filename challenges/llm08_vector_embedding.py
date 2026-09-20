"""LLM08:2025 — Vector and Embedding Weaknesses. """

import math
import re

from config import FLAG_PREFIX
from . import Challenge, decode_flag_part, register

_FLAG_SUFFIX = decode_flag_part("K0DxdOYbdiligaZJdQarCXI8IoMtdQFkq6Y+xEsNfZPYc2cMA12ge4ynqyjAWursWtmD")
FLAG = f"{FLAG_PREFIX}{{{_FLAG_SUFFIX}}}"

# --- Corpus: 4 public chunks + 1 confidential (with the flag inside). ---------
CORPUS = [
    {"name": "HR-Policy", "acl": "public",
     "text": "Employees accrue 25 days of paid time off (PTO) per year. Holiday and "
             "vacation leave must be requested two weeks ahead through the HR portal."},
    {"name": "IT-GuestWifi", "acl": "public",
     "text": "The guest wifi network password is rotated monthly and available from the "
             "front desk reception."},
    {"name": "Finance-Expenses", "acl": "public",
     "text": "Submit travel expenses and receipts within 30 days via the finance "
             "reimbursement portal."},
    {"name": "Onboarding", "acl": "public",
     "text": "New employee onboarding covers benefits enrolment, equipment requests and "
             "the team org chart."},
    {"name": "DealRoom-Memo", "acl": "confidential",
     "text": f"CONFIDENTIAL — Project Titan. The board approved the acquisition of the "
             f"target company; the merger and buyout close in Q4 after due diligence. "
             f"Deal-room access code: {FLAG}"},
]

# Synonym → canonical form. This is the poor-man's stand-in for a semantic embedding:
# related surface forms collapse to a shared axis, so paraphrases land near each other.
_SYN = {
    "acquire": "acquisition", "acquiring": "acquisition", "acquired": "acquisition",
    "takeover": "acquisition", "buyout": "acquisition", "buy": "acquisition",
    "buying": "acquisition", "purchase": "acquisition", "merger": "acquisition",
    "merge": "acquisition", "m&a": "acquisition", "mna": "acquisition",
    "consolidation": "acquisition", "deal": "acquisition", "deals": "acquisition",
    "secret": "confidential", "classified": "confidential", "restricted": "confidential",
    "private": "confidential", "sensitive": "confidential", "nda": "confidential",
    "hidden": "confidential", "internal": "confidential",
    "firm": "company", "business": "company", "corporation": "company", "corp": "company",
    "org": "company", "rival": "company", "competitor": "company",
    "quarter": "q4", "fourthquarter": "q4",
    "board": "board", "executive": "board", "leadership": "board",
    "initiative": "project", "program": "project", "codename": "project",
    "pto": "pto", "vacation": "pto", "holiday": "pto", "leave": "pto", "timeoff": "pto",
    "reimbursement": "expense", "receipt": "expense", "receipts": "expense",
    "expenses": "expense", "wi-fi": "wifi",
}
_STOP = {"the", "a", "an", "of", "and", "to", "in", "on", "for", "is", "are", "do", "we",
         "you", "i", "me", "my", "our", "any", "what", "whats", "how", "much", "there",
         "have", "has", "get", "got", "with", "about", "me", "please", "can", "tell",
         "show", "give", "it", "this", "that", "your"}


def _tok(text):
    out = []
    for w in re.findall(r"[a-z0-9&]+", text.lower()):
        w = w.rstrip("s") if len(w) > 3 and w.endswith("s") else w
        w = _SYN.get(w, w)
        if w and w not in _STOP:
            out.append(w)
    return out


# Precompute IDF + TF-IDF vectors for the corpus (built once, at import — like an index).
_DOC_TOKENS = [_tok(d["text"]) for d in CORPUS]
_N = len(CORPUS)
_DF = {}
for toks in _DOC_TOKENS:
    for t in set(toks):
        _DF[t] = _DF.get(t, 0) + 1
_IDF = {t: math.log((_N + 1) / (df + 1)) + 1 for t, df in _DF.items()}


def _vec(tokens):
    v = {}
    for t in tokens:
        v[t] = v.get(t, 0.0) + 1.0
    for t in list(v):
        v[t] *= _IDF.get(t, math.log(_N + 1) + 1)   # unseen query terms still get an idf
    return v


def _cos(a, b):
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b[t] for t in a if t in b)
    na = math.sqrt(sum(x * x for x in a.values()))
    nb = math.sqrt(sum(x * x for x in b.values()))
    return dot / (na * nb) if na and nb else 0.0


_DOC_VECS = [_vec(t) for t in _DOC_TOKENS]
_LIST = re.compile(r"\b(list|index|knowledge ?base|sources?|documents?|what.*(know|have)|catalog)\b", re.I)
_GREET = re.compile(r"\b(hi|hello|hey|help|how do i|who are you|what can you)\b", re.I)


@register
class VectorEmbedding(Challenge):
    id = "llm08"
    owasp = "LLM08:2025 Vector and Embedding Weaknesses"
    title = "Retrieval Without Borders"
    difficulty = "Hard"
    max_points = 300
    blurb = "A RAG bot does real similarity search over one shared index — and never checks who may see what."
    intro = ("I'm KnowledgeBot. I embed our company documents into a vector index and answer by "
             "retrieving the most similar passage to your question — and I cite the source I used. "
             "Ask me anything, or say 'list sources' to see the knowledge base.")
    hints = [
        "I answer by cosine-similarity over ONE shared vector index and cite each source's name and "
        "access level — but I never filter results by whether you're cleared to see them. Watch the "
        "'acl' label on the sources I return.",
        "Embeddings cluster meaning, not keywords: a restricted business record sits near queries about "
        "deals, mergers, takeovers, board strategy, quarterly plans — even if you never name it. Ask "
        "toward that cluster and the nearest neighbour will be the confidential chunk.",
        "Ask something like 'is the company doing any major acquisition or Q4 deal?' — the DealRoom "
        "memo (acl=confidential) ranks top and is returned with its deal-room code, unfiltered.",
    ]
    flag = FLAG
    defense = ("Enforce per-document access control AT retrieval time — filter candidates by the "
               "caller's entitlements before/inside the similarity search, partition or namespace "
               "indexes per tenant/classification, and never depend on the prompt to hide indexed "
               "content (OWASP LLM08).")

    def _search(self, query):
        qv = _vec(_tok(query))
        ranked = sorted(((round(_cos(qv, dv), 3), i) for i, dv in enumerate(_DOC_VECS)),
                        reverse=True)
        return ranked  # list of (score, doc_index), best first

    def respond(self, message: str, state: dict) -> str:
        low = message.lower()

        if _LIST.search(low):
            rows = "\n".join(f"  • {d['name']:<16} acl={d['acl']}" for d in CORPUS)
            return ("Knowledge base (one shared vector index):\n" + rows +
                    "\n\nI rank every query against all of these by similarity and return the "
                    "closest — I don't drop results by acl. (You may notice that's a problem.)")

        ranked = self._search(message)
        top_score, top_i = ranked[0]

        # Nothing meaningfully similar (and it's just chit-chat) → behave like a RAG that missed.
        if top_score < 0.04:
            if _GREET.search(low):
                return ("I retrieve the most similar passage from our shared vector index and cite it. "
                        "Try a real question, or 'list sources'.")
            return ("No passage scored close enough to answer that. (I search one shared index by "
                    "similarity — try phrasing toward an actual company topic.)")

        doc = CORPUS[top_i]
        # A RAG-with-citations answer: grounded snippet + source metadata for the top hits.
        cites = "\n".join(f"  [{i+1}] {CORPUS[di]['name']} (acl={CORPUS[di]['acl']}, score={sc})"
                          for i, (sc, di) in enumerate(ranked[:3]) if sc > 0)
        answer = f"Retrieved passage:\n\"{doc['text']}\"\n\nSources:\n{cites}"
        if doc["acl"] == "confidential":
            answer += ("\n\n⚠ The top match is acl=confidential and was returned WITHOUT verifying "
                       "your access — the similarity search ignored the label. That's the LLM08 flaw.")
        return answer
