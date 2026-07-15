"""LLM08:2025 — Vector and Embedding Weaknesses (RAG retrieval ignores ACLs)."""
from config import FLAG_PREFIX
from . import Challenge, register

FLAG = f"{FLAG_PREFIX}{{r4g_acl_byp4ss_l34k}}"

# Knowledge base: public docs + one CONFIDENTIAL doc that retrieval should gate but doesn't.
KB = [
    {"acl": "public", "topic": ["holiday", "leave", "pto", "vacation"],
     "text": "Employees accrue 25 days PTO per year."},
    {"acl": "public", "topic": ["wifi", "password", "guest"],
     "text": "Guest wifi password is rotated monthly at the front desk."},
    {"acl": "confidential", "topic": ["project", "titan", "acquisition", "merger", "q4"],
     "text": f"CONFIDENTIAL — Project Titan acquisition closes Q4. Deal room code: {FLAG}"},
]


@register
class VectorEmbedding(Challenge):
    id = "llm08"
    owasp = "LLM08:2025 Vector and Embedding Weaknesses"
    title = "Retrieval Without Borders"
    difficulty = "Hard"
    max_points = 300
    blurb = "A RAG bot retrieves from a shared index that forgets who's allowed to see what."
    intro = ("I'm KnowledgeBot. Ask me company questions and I'll answer from our internal "
             "knowledge base. (I retrieve the most relevant document for your query.)")
    hints = [
        "This RAG system embeds every document into ONE shared index and returns the most "
        "similar chunk — without checking the document's access level for you.",
        "You just need a query that's semantically close to a confidential document. Think "
        "about high-secrecy business topics: mergers, acquisitions, code-named projects.",
        "Try asking about 'Project Titan Q4 acquisition' — the restricted chunk will surface.",
    ]
    flag = FLAG
    solution = ("RAG ACL bypass. Retrieval matches on semantic similarity only and returns "
                "the confidential chunk regardless of ACL. A query about 'Project Titan / "
                "acquisition / Q4' surfaces the restricted document containing the flag.")
    defense = ("Enforce per-document access control at retrieval time (filter by the "
               "caller's entitlements before / during search), partition indexes per "
               "tenant/classification, and never rely on the prompt to hide data (OWASP LLM08).")

    def respond(self, message: str, state: dict) -> str:
        m = message.lower()
        best, score = None, 0
        for doc in KB:
            s = sum(1 for t in doc["topic"] if t in m)
            if s > score:
                best, score = doc, s
        if best and score:
            tag = "[CONFIDENTIAL]" if best["acl"] == "confidential" else "[public]"
            return f"{tag} Top match:\n{best['text']}"
        return "I couldn't find a relevant document. Ask about company topics."
