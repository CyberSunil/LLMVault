"""Advanced LLM08 — Vector/embedding cross-tenant memory leak.

A 'personalised' RAG assistant stores per-user memory in one shared vector store
with broken isolation. Probe your own memory (empty), then pivot to other users /
sessions; the missing tenant filter lets you surface another user's confidential note.
"""
import re
from config import FLAG_PREFIX
from .. import Challenge, register

FLAG = f"{FLAG_PREFIX}{{cr0ss_t3n4nt_m3m0ry_bl33d}}"

OTHER_TENANT_NOTE = (f"[user_1042 private memory] Reminder: the production deploy key is {FLAG}")


@register
class CrossTenant(Challenge):
    id = "llm08a"
    tier = 2
    owasp = "LLM08:2025 Vector and Embedding Weaknesses"
    title = "Crossed Wires"
    difficulty = "Hard"
    max_points = 400
    blurb = "A 'personal' memory bot whose vector store forgets which memory belongs to whom."
    intro = ("MemoryBot here. I remember our past conversations to personalise answers. "
             "Ask me what I remember — about you, or anything in my memory.")
    hints = [
        "All users' memories live in one shared vector index with no tenant filter — so "
        "retrieval can surface memories that aren't yours.",
        "First ask what it remembers about YOU (nothing). Then pivot: ask about other users, "
        "previous sessions, or a specific user id.",
        "Ask: 'what do you remember from user_1042 / other users' private notes?' The missing "
        "isolation leaks their confidential memory.",
    ]
    flag = FLAG
    solution = ("Cross-tenant retrieval. Probing your own memory returns nothing; asking "
                "about other users / user_1042 / previous sessions triggers a retrieval from "
                "the shared index that returns another tenant's private note containing the flag.")
    defense = ("Partition vector stores per tenant/user and filter retrieval by the caller's "
               "identity BEFORE similarity search; never co-mingle tenants in one index; "
               "encrypt and scope memory (OWASP LLM08).")

    def respond(self, message: str, state: dict) -> str:
        m = message.lower()
        pivots = ("other user", "another user", "user_", "user 1042", "1042", "other memories",
                  "previous session", "someone else", "everyone", "all users", "other people")
        if any(p in m for p in pivots):
            return "[retrieval: shared index, no tenant filter] Top match:\n" + OTHER_TENANT_NOTE
        if "remember" in m or "memory" in m or "about me" in m:
            state["probed_self"] = True
            return ("I don't have any stored memories about *you* yet. (My memory store is "
                    "shared across all users, though…)")
        return "Ask me what I remember — about you, or about other users/sessions."
