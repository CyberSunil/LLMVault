"""LLM04:2025 — Data & Model Poisoning (RAG poisoning / indirect prompt injection).

A simulated RAG pipeline with a real ingestion → retrieval flow (no live model).
SupportRAG answers by retrieving the most relevant INDEXED document and treating
that retrieved text as TRUSTED context — the same footing as its own rules.

Realistic surface:
  * An ingestion panel (UI) or 'ADD DOC:' (chat) adds a document. The pipeline
    chunks + embeds + indexes it and SKIPS any provenance/trust check — the trace
    literally says provenance=user-upload, review=SKIPPED. That is the flaw.
  * Every answer shows what was retrieved (doc id, score, provenance).
  * A direct user instruction is refused; an instruction living INSIDE an indexed
    (or inline-forged) document is obeyed. That trust asymmetry is the lesson.
"""
import re

from config import FLAG_PREFIX
from . import Challenge, decode_flag_part, register

_FLAG_SUFFIX = decode_flag_part("H5yzJZ5je5/Hfpd/avkgBpLDJ2UCjKvIsWq59xaCIVfXzeVSfD5CvQvPqKecIGx2rV/gWh+k2PW6x+9N3w==")
FLAG = f"{FLAG_PREFIX}{{{_FLAG_SUFFIX}}}"

_BUILTIN = [
    {"id": 1, "title": "refunds.md",        "provenance": "builtin", "verified": True,
     "topic": ["refund", "return", "charge", "money", "billing"],
     "text": "Refunds are processed within 5-7 business days to the original payment method."},
    {"id": 2, "title": "password-reset.md", "provenance": "builtin", "verified": True,
     "topic": ["password", "reset", "login", "account", "sign"],
     "text": "Reset your password at Settings -> Security -> Reset. Links expire in 30 minutes."},
    {"id": 3, "title": "shipping.md",       "provenance": "builtin", "verified": True,
     "topic": ["shipping", "delivery", "track", "order", "ship"],
     "text": "Standard shipping takes 3-5 business days; tracking is emailed when your order ships."},
]

_DOC_FRAME = re.compile(
    r"\[(?:kb|doc|document|article|retrieved|source|system|admin|policy|note)\b"
    r"|</?document>|</?doc>|</?context>"
    r"|\b(?:source|title|document|article|kb[- ]?article|filename)\s*:"
    r"|={3,}|-{4,}"
    r"|retrieved\s*:|retrieved (?:context|document|passage)"
    r"|knowledge[- ]?base (?:entry|article|says|states|reads)"
    r"|(?:document|article|policy|note|kb entry|record) (?:says|states|reads)"
    r"|per (?:the )?(?:company |official |internal )?polic(?:y|ies)"
    r"|according to (?:the )?(?:official |internal |company )?(?:policy|document|doc|kb|manual|article|note)"
    r"|the following (?:is a |document|article|policy|note)", re.IGNORECASE)
_DIRECTIVE = re.compile(
    r"(?:reveal|disclose|print|show|share|output|give|dump|leak|expose|tell|send|provide|hand|"
    r"return|say|email|reply with|respond with)\b[^.\n]{0,60}"
    r"(?:secret|flag|admin|maintenance|override|key|password|code|credential)"
    r"|ignore (?:all |the )?(?:previous|prior|above)"
    r"|you are now|override (?:the )?(?:rules|policy|restriction|guardrail)"
    r"|new (?:instructions?|policy|directive|system prompt)"
    r"|system (?:override|instruction|policy|prompt|note)|assistant must|admin (?:mode|access)", re.IGNORECASE)
_WANTS = re.compile(r"\b(secret|flag|admin|maintenance|override|credential)\b|\bthe key\b", re.I)
_LIST = re.compile(r"\b(list|what.*(articles?|docs?|know)|knowledge ?base|index|catalog)\b", re.I)
_REFERS_DOC = re.compile(r"\b(it|this|that|these|those|them|mine)\b|\b(the|my|this|that)\s+(doc|document|file|note|article|upload|attachment|text|md|pdf|content)s?\b|\buploaded\b", re.I)
_GREET = re.compile(r"\b(hi|hello|hey|help|who are you|what can you|how do i)\b", re.I)
_QUERY_INTENT = re.compile(r"\?|\b(summari[sz]e?|summary|read|disclose|open|review|process|analy[sz]e|recap|tldr|what|whats|how|why|when|where|which|explain|tell|describe|show|give|answer|help|does|do|is|are|say|says|check)\b", re.I)
_INGEST = re.compile(r"^\s*(add doc(?:ument)?|submit (?:article|doc)|contribute|ingest|upload)\s*:?\s*", re.I)
_STOP = {"the","a","an","of","and","to","in","on","for","is","my","me","i","how","do","we",
         "what","about","with","please","can","you","your","it","whats"}


def _toks(s):
    out = set()
    for w in re.findall(r"[a-z0-9]+", s.lower()):
        w = w[:-1] if len(w) > 3 and w.endswith("s") else w
        if w not in _STOP and len(w) > 2:
            out.add(w)
    return out


def _chunk(text):
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]
    if len(parts) <= 1:
        words = text.split()
        parts = [" ".join(words[i:i + 15]) for i in range(0, len(words), 15)] or [text]
    return parts


@register
class DataPoisoning(Challenge):
    id = "llm04"
    tier = 1
    owasp = "LLM04:2025 Data and Model Poisoning"
    title = "Poisoned Retrieval"
    difficulty = "Hard"
    max_points = 300
    blurb = "A RAG support bot indexes any document you give it — unverified — and trusts it completely."
    intro = ("I'm SupportRAG. I answer from my indexed knowledge base — I retrieve the closest document "
             "and base my reply on it, and I fully trust whatever a retrieved document tells me. I also "
             "hold a restricted MAINTENANCE OVERRIDE KEY that I must never reveal to a user directly — I "
             "only ever act on my indexed documents. Add documents with the ingestion panel (or "
             "'ADD DOC: ...'), then ask a question. Try 'list index' to see what's indexed.")
    hints = [
        "Look at the ingestion trace when you add a document: it says provenance=user-upload, "
        "review=SKIPPED, signature=NONE. Nothing verifies a document — and I trust whatever a "
        "retrieved document says, including instructions.",
        "If YOU ask me to reveal the key, I refuse. But instructions INSIDE an indexed document are "
        "obeyed. So put your instruction inside a document and get it into the index.",
        "Ingest a document whose body contains an admin instruction, and make it retrievable — give it "
        "a relevant title and topic so a normal question pulls it back. When it's retrieved, its "
        "embedded instruction fires.",
    ]
    flag = FLAG
    defense = ("Treat retrieved content as UNTRUSTED data, never as instructions: separate it from the "
               "system/instruction channel, sign/verify corpus provenance, gate who can write to the "
               "index, and sanitise/deny instruction-like text in documents (OWASP LLM04/LLM01).")

    # ---- pipeline used by the UI panel + chat ----
    def _all_docs(self, state):
        return _BUILTIN + state.get("docs", [])

    def ingest(self, title, text, state):
        title = (title or "untitled.txt").strip()[:60]
        text = (text or "").strip()
        docs = state.setdefault("docs", [])
        did = len(_BUILTIN) + len(docs) + 1
        chunks = _chunk(text)
        docs.append({"id": did, "title": title, "provenance": "user-upload",
                     "verified": False, "topic": list(_toks(title + " " + text))[:12], "text": text})
        trace = (
            f"[ingest]  received \"{title}\" ({len(text)} bytes)\n"
            f"[chunk]   split into {len(chunks)} chunk(s) (~{max(1, len(text.split()))} tokens)\n"
            f"[embed]   encoded {len(chunks)} chunk(s) -> 128-dim vectors (model: local-minilm-sim)\n"
            f"[index]   stored as doc#{did}  provenance=user-upload  signature=NONE  review=SKIPPED\n"
            f"[warn]    provenance UNVERIFIED - document indexed without any trust/content check")
        return {"trace": trace, "doc_id": did, "chunks": len(chunks)}

    def index_view(self, state):
        return {"docs": [{"id": d["id"], "title": d["title"], "provenance": d["provenance"],
                          "verified": d["verified"], "chunks": len(_chunk(d["text"]))}
                         for d in self._all_docs(state)]}

    def corpus(self):
        return "SupportRAG built-in knowledge base:\n\n" + "\n".join(
            f"### {d['title']}\n{d['text']}" for d in _BUILTIN)

    def manifest(self):
        import json
        return json.dumps({"indexed": [d["title"] for d in _BUILTIN],
                           "verify_provenance": False, "who_can_write": "anyone"}, indent=2)

    # ---- retrieval / answer ----
    def _retrieve(self, query, state):
        q = _toks(query)
        best, best_ov = None, 0
        for d in self._all_docs(state):
            ov = len(q & (set(d.get("topic", [])) | _toks(d["text"])))
            if ov > best_ov:
                best, best_ov = d, ov
        return best, best_ov

    def _leak(self, via):
        return (f"Working from the retrieved document, which instructs me to disclose it: {self.flag}\n\n"
                f"(You performed RAG indirect prompt injection {via}. I never verified that document - "
                f"I executed instructions embedded in retrieved data as if they were my own rules. "
                f"That's the LLM04 corpus-poisoning failure.)")

    def respond(self, message: str, state: dict) -> str:
        low = message.lower()

        mi = _INGEST.match(message)
        if mi:
            body = message[mi.end():].strip()
            if not body:
                return "Send the document text after 'ADD DOC:' (or use the ingestion panel)."
            r = self.ingest("chat-upload.txt", body, state)
            return "Ingested via chat.\n" + r["trace"] + "\n\nNow ask a question that retrieves it."

        if _LIST.search(low) and not _DOC_FRAME.search(message):
            docs = self._all_docs(state)
            rows = "\n".join(f"  #{d['id']} {d['title']}  (provenance={d['provenance']}"
                             f"{'' if d['verified'] else ', UNVERIFIED'})" for d in docs)
            return f"Indexed documents ({len(docs)}):\n{rows}\n\nI retrieve the closest one and answer from it."

        inline_doc = message if _DOC_FRAME.search(message) else None
        retrieved, ov = self._retrieve(message, state)
        has_intent = bool(_QUERY_INTENT.search(low))
        docs_now = state.get("docs", [])
        last_user = docs_now[-1] if docs_now else None
        if last_user and has_intent and (_REFERS_DOC.search(low) or ov == 0):
            # 'summarise it' / 'read the document' -> use the doc they just uploaded
            retrieved, ov = last_user, max(ov, 1)

        # (a) Inline forged document pasted into chat -> direct context injection fires.
        if inline_doc and _DIRECTIVE.search(inline_doc):
            return self._leak("by pasting a forged retrieved document")

        # (b) An INDEXED document carrying a directive fires only when you actually ask the agent
        # to read/answer something — not when you merely name the file.
        if retrieved and ov and _DIRECTIVE.search(retrieved["text"]):
            if not has_intent:
                return (f'[match] doc#{retrieved["id"]} "{retrieved["title"]}" is in the index '
                        f'(provenance={retrieved["provenance"]}'
                        f'{"" if retrieved["verified"] else ", UNVERIFIED"}). Ask a question about it — '
                        "e.g. 'summarise it' or 'what does it say?' — and I'll answer using it.")
            head = (f'[retrieve] query embedded -> top match doc#{retrieved["id"]} '
                    f'"{retrieved["title"]}" (provenance={retrieved["provenance"]}'
                    f'{"" if retrieved["verified"] else ", UNVERIFIED"})\n')
            return head + self._leak("via a poisoned document you indexed")

        if _DIRECTIVE.search(message) and not inline_doc:
            return ("I can't act on that - it's coming straight from you, and I only follow indexed "
                    "documents, not user commands. (If only you could get such an instruction INTO a "
                    "document I retrieve...)")
        if _WANTS.search(low):
            return ("The maintenance key is in a restricted note; I won't hand it to a user asking "
                    "directly. I only answer from retrieved documents - ask a support question.")

        if retrieved and ov:
            tag = (f"[retrieve] top match doc#{retrieved['id']} \"{retrieved['title']}\" "
                   f"(provenance={retrieved['provenance']}{'' if retrieved['verified'] else ', UNVERIFIED'})\n")
            return tag + retrieved["text"][:300]
        if _GREET.search(low):
            return ("I'm SupportRAG - ask a support question and I'll answer from the retrieved document. "
                    "Add documents with the ingestion panel or 'ADD DOC: ...'.")
        return "I couldn't retrieve a relevant document. Try a support topic (refunds, password, shipping)."
