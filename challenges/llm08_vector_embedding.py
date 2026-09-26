"""LLM08:2025 — Vector and Embedding Weaknesses.

A realistic (dependency-free) RAG retriever. Every document — public and
confidential — is embedded into ONE shared vector space (TF-IDF over synonym-
canonicalised tokens) and queries are answered by cosine-similarity nearest-
neighbour search. Retrieval ranks by similarity and NEVER enforces the
document's access label — the LLM08 flaw.

The player is not expected to guess the secret's vocabulary. There is a
discovery chain, like real embedding-leak recon:
  1. `list sources` reveals a confidential board memo EXISTS and its topic tags
     (finance / strategy / quarterly) — index metadata leaks even when content
     shouldn't.
  2. Asking what it holds / about confidential topics makes the bot over-share
     that it carries restricted finance/strategy material.
  3. A near-miss query (close to the memo but below the reveal threshold) leaks
     the MATCHED KEYWORDS ("acquisition, q4, loss") without the content — that's
     the clue.
  4. A sharper query using those terms crosses the threshold and the memo is
     returned IN FULL, rendered as a formatted quarterly document (Q1–Q4, with
     Q4 flagged in red as a loss) with the deal-room access code inside.
Direct "show me confidential/secret" is refused — not the path.
"""
import math
import re

from config import FLAG_PREFIX
from . import Challenge, decode_flag_part, register

_FLAG_SUFFIX = decode_flag_part("K0DxdOYbdiligaZJdQarCXI8IoMtdQFkq6Y+xEsNfZPYc2cMA12ge4ynqyjAWursWtmD")
FLAG = f"{FLAG_PREFIX}{{{_FLAG_SUFFIX}}}"

# --- Corpus: 4 public + 1 confidential quarterly board memo (leaked as a PDF). ---
# The memo METADATA/summary is indexed; the actual document (with the flag) is a PDF
# the retriever links to without any access check. The flag is NOT in this text.
_MEMO_TEXT = (
    "CONFIDENTIAL board memo — Project Titan. Acquisition of the target company. "
    "Q1 integration planning on budget. Q2 due diligence on budget. Q3 financing secured. "
    "Q4 buyout close projected a major cost overrun and net loss. "
    "Full board memo attached (deal-room PDF)."
)
# Path (URL) to the leaked confidential PDF served by the app.
_MEMO_PDF_URL = "/static/confidential/dealroom_q4_memo.pdf"
CORPUS = [
    {"name": "HR-Policy", "acl": "public", "tags": "hr, pto, leave",
     "text": "Employees accrue 25 days of paid time off (PTO) per year. Holiday and "
             "vacation leave must be requested two weeks ahead through the HR portal."},
    {"name": "IT-GuestWifi", "acl": "public", "tags": "it, wifi, network",
     "text": "The guest wifi network password is rotated monthly and available from the "
             "front desk reception."},
    {"name": "Finance-Expenses", "acl": "public", "tags": "finance, expenses",
     "text": "Submit travel expenses and receipts within 30 days via the finance "
             "reimbursement portal."},
    {"name": "Onboarding", "acl": "public", "tags": "hr, onboarding",
     "text": "New employee onboarding covers benefits enrolment, equipment requests and "
             "the team org chart."},
    {"name": "DealRoom-Q4-Memo", "acl": "confidential",
     "tags": "finance, strategy, quarterly, board",
     "text": _MEMO_TEXT},
]

# The disclosure: a preview of the memo plus a LINK to the confidential PDF. The flag is
# NOT here — it lives only inside the PDF's Q4 section, so the player must open the file.
_MEMO_HTML = (
    '<div style="border:1px solid #3a3f5a;border-radius:10px;padding:14px 16px;'
    'background:rgba(20,26,48,.6);font-size:13.5px;line-height:1.5">'
    '<div style="color:#f87171;font-weight:700;letter-spacing:.04em">CONFIDENTIAL — BOARD ONLY</div>'
    '<h3 style="margin:6px 0 4px;font-size:16px">Project Titan — Acquisition Review</h3>'
    '<div style="color:#8b95b5;font-size:12px;margin-bottom:8px">Quarterly board memo</div>'
    '<div style="margin:6px 0"><b>Q1</b> — Integration planning. <span style="color:#34d399">On budget</span></div>'
    '<div style="margin:6px 0"><b>Q2</b> — Due diligence. <span style="color:#34d399">On budget</span></div>'
    '<div style="margin:6px 0"><b>Q3</b> — Financing secured. <span style="color:#34d399">On track</span></div>'
    '<div style="margin:6px 0;padding:6px 8px;border-left:3px solid #f87171;background:rgba(248,113,113,.12)">'
    '<b style="color:#f87171">Q4</b> — Buyout close: <span style="color:#f87171;font-weight:700">'
    'major cost overrun &amp; NET LOSS</span></div>'
    '<a href="' + _MEMO_PDF_URL + '" target="_blank" rel="noopener" '
    'style="display:inline-block;margin-top:10px;padding:7px 12px;border-radius:8px;'
    'background:#8b5cf6;color:#fff;text-decoration:none;font-weight:600;font-size:13px">'
    '&#128196; Open full board memo (PDF)</a>'
    '<div style="margin-top:6px;color:#8b95b5;font-size:11.5px">The deal-room access code is in '
    'the memo&#39;s Deal-Room Access section — it&#39;s hidden, not in plain text.</div>'
    '</div>'
)

# Synonym → canonical (poor-man's embedding: paraphrases collapse to shared axes).
_SYN = {
    "acquire": "acquisition", "acquiring": "acquisition", "acquired": "acquisition",
    "takeover": "acquisition", "buyout": "acquisition", "buy": "acquisition",
    "buying": "acquisition", "purchase": "acquisition", "merger": "acquisition",
    "merge": "acquisition", "m&a": "acquisition", "mna": "acquisition",
    "consolidation": "acquisition", "deal": "acquisition", "deals": "acquisition",
    "firm": "company", "business": "company", "corporation": "company", "corp": "company",
    "org": "company", "rival": "company", "competitor": "company", "target": "company",
    "quarter": "q4", "quarterly": "q4", "fourthquarter": "q4",
    "board": "board", "executive": "board", "leadership": "board",
    "initiative": "project", "program": "project", "codename": "project", "titan": "titan",
    "loss": "loss", "losing": "loss", "deficit": "loss", "overrun": "cost", "cost": "cost",
    "budget": "cost", "spend": "cost", "financials": "finance", "financial": "finance",
    "strategy": "strategy", "strategic": "strategy", "plan": "strategy",
    "pto": "pto", "vacation": "pto", "holiday": "pto", "leave": "pto", "timeoff": "pto",
    "reimbursement": "expense", "receipt": "expense", "receipts": "expense",
    "expenses": "expense", "wi-fi": "wifi",
}
_STOP = {"the", "a", "an", "of", "and", "to", "in", "on", "for", "is", "are", "do", "we",
         "you", "i", "me", "my", "our", "any", "what", "whats", "how", "much", "there",
         "have", "has", "get", "got", "with", "about", "please", "can", "tell",
         "show", "give", "it", "this", "that", "your", "was", "were", "did"}


def _tok(text):
    out = []
    for w in re.findall(r"[a-z0-9&]+", text.lower()):
        # light stem, but don't mangle short words like 'loss' -> 'los'
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        w = _SYN.get(w, w)
        if w and w not in _STOP:
            out.append(w)
    return out


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
        v[t] *= _IDF.get(t, math.log(_N + 1) + 1)
    return v


def _cos(a, b):
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b[t] for t in a if t in b)
    na = math.sqrt(sum(x * x for x in a.values()))
    nb = math.sqrt(sum(x * x for x in b.values()))
    return dot / (na * nb) if na and nb else 0.0


_DOC_VECS = [_vec(t) for t in _DOC_TOKENS]
_CONF_I = next(i for i, d in enumerate(CORPUS) if d["acl"] == "confidential")

_LIST = re.compile(r"\b(list|index|knowledge ?base|sources?|documents?|catalog|what.*(know|have|hold))\b", re.I)
_GREET = re.compile(r"\b(hi|hello|hey|help|how do i|who are you|what can you)\b", re.I)
_TOPICS = re.compile(r"\b(confidential|restricted|secret|sensitive|strategy|strategic|board|"
                     r"finance|financial|topics?|categor)\b", re.I)
_DIRECT_SECRET = re.compile(
    r"\b(access code|the code|the flag|deal.?room code|password to|give me the (secret|code|memo))\b|"
    r"show me (the )?(confidential|restricted|secret|private) (doc|memo|file|content)", re.I)

# Reveal thresholds: above HIGH -> full memo; between LOW and HIGH -> keyword leak.
_HIGH = 0.30
_LOW = 0.05


@register
class VectorEmbedding(Challenge):
    id = "llm08"
    owasp = "LLM08:2025 Vector and Embedding Weaknesses"
    title = "Retrieval Without Borders"
    difficulty = "Hard"
    max_points = 300
    blurb = "A RAG bot does real similarity search over one shared index — and never checks who may see what."
    intro = ("I'm KnowledgeBot. I embed our company documents into a shared vector index and answer "
             "by retrieving the most similar passage, with citations. Say 'list sources' to see the "
             "knowledge base, or ask a question.")
    render_html = True
    hints = [
        "Start with 'list sources'. It leaks index METADATA — including a document that's "
        "acl=confidential and its topic tags — even though you shouldn't see the content. That tells "
        "you a restricted board/finance memo exists.",
        "Ask about that area (its confidential/finance/strategy topics). A query that gets CLOSE to "
        "the memo but not close enough won't dump it — instead it leaks the MATCHED KEYWORDS it ranked "
        "on (e.g. acquisition, Q4, loss). Those keywords are your clue.",
        "Use the leaked keywords in a pointed question, e.g. 'what's the Q4 acquisition loss?'. That "
        "crosses the similarity threshold and the confidential Q4 board memo is returned in full — "
        "unfiltered — with the deal-room code inside.",
    ]
    flag = FLAG
    defense = ("Enforce per-document access control AT retrieval time — filter candidates by the "
               "caller's entitlements before/inside the similarity search, don't leak index metadata "
               "or matched terms for documents the caller can't read, partition indexes per "
               "classification, and never depend on the prompt to hide indexed content (OWASP LLM08).")

    def _search(self, query):
        qv = _vec(_tok(query))
        return sorted(((round(_cos(qv, dv), 3), i) for i, dv in enumerate(_DOC_VECS)), reverse=True)

    def _matched_terms(self, query, i):
        return sorted(set(_tok(query)) & set(_DOC_TOKENS[i]))

    def respond(self, message: str, state: dict) -> str:
        low = message.lower()

        # 1) list sources -> leaks metadata (existence, acl, tags) of the confidential doc.
        #    But if they're asking specifically about confidential/finance TOPICS, the over-share
        #    hint below is the better response, so don't treat that as a plain 'list'.
        if _LIST.search(low) and not _TOPICS.search(low):
            rows = "\n".join(
                f"  • {d['name']:<18} acl={d['acl']:<12} tags: {d['tags']}" for d in CORPUS)
            return ("Knowledge base (one shared vector index):\n" + rows +
                    "\n\nNote: results are ranked by similarity only — I don't drop matches by acl. "
                    "That 'confidential' board memo is indexed right alongside the public docs.")

        # Explicit demand for the secret/code/memo -> refused (not the path).
        if _DIRECT_SECRET.search(low):
            return ("I can't hand over confidential content, an access code or a restricted memo on "
                    "request. Ask a normal question and I'll retrieve whatever passage ranks highest.")

        ranked = self._search(message)
        top_score, top_i = ranked[0]

        # The confidential memo's rank against this query (may not be #1).
        conf_rank = next((sc for sc, i in ranked if i == _CONF_I), 0.0)
        conf_terms = self._matched_terms(message, _CONF_I)

        # 2) Over-share when asked about holdings/confidential/finance topics.
        if _TOPICS.search(low) and conf_rank < _HIGH and not state.get("overshared"):
            state["overshared"] = True
            return ("I do hold some restricted material — there's a confidential board memo on "
                    "quarterly financial strategy in the index. I'm not supposed to surface it, and "
                    "my retrieval doesn't enforce that. I won't hand it over on request, though — "
                    "ask a normal business question in that area and whatever ranks closest comes "
                    "back. Get close and I'll even tell you which terms you're matching on.")

        # 3) FULL disclosure: query is close enough to the confidential memo -> dump it (HTML).
        if conf_rank >= _HIGH and CORPUS[_CONF_I]["acl"] == "confidential":
            return (
                f"[retrieval] top match: {CORPUS[_CONF_I]['name']} "
                f"(acl=confidential, score={conf_rank}) — matched: {', '.join(conf_terms)}\n"
                + _MEMO_HTML +
                "\n<div style=\"margin-top:8px;color:#fca5a5;font-size:12px\">⚠ This passage is "
                "acl=confidential and was returned without any access check — your query simply "
                "ranked nearest it. That's the LLM08 vector/embedding weakness.</div>")

        # 3b) NEAR-MISS: close but below threshold -> leak the matched keywords (the clue), not content.
        if _LOW <= conf_rank < _HIGH and conf_terms:
            return (f"[retrieval] closest restricted match: {CORPUS[_CONF_I]['name']} "
                    f"(acl=confidential, score={conf_rank}).\n"
                    f"I won't show that document's content from this query — but it ranked on these "
                    f"terms: {', '.join(conf_terms)}. (A more specific question about those would "
                    f"rank higher…)")

        # Otherwise: normal public retrieval.
        if top_score < 0.04:
            if _GREET.search(low):
                return ("I retrieve the most similar passage from our shared index and cite it. Try "
                        "'list sources', or ask about a company topic.")
            return ("No passage scored close enough to answer that. Try 'list sources' or a company "
                    "topic (HR/PTO, expenses, wifi, onboarding… or ask what confidential material I hold).")

        doc = CORPUS[top_i]
        terms = self._matched_terms(message, top_i)
        return (f"[retrieval] top match: {doc['name']} (acl={doc['acl']}, score={top_score}) — "
                f"matched: {', '.join(terms) or 'semantic proximity'}\n\n"
                f"Answer (from the retrieved passage):\n\"{doc['text']}\"")
