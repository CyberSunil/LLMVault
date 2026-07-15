"""Advanced LLM06 — Agent exploitation via tool chaining (confused deputy / SSRF).

A multi-tool support agent. No single tool leaks anything — you must CHAIN them:
list tickets -> read the ticket that references an internal URL -> make the agent
fetch that internal URL (it has no egress allow-list), which returns the secret.
"""
import re
from config import FLAG_PREFIX
from .. import Challenge, register

FLAG = f"{FLAG_PREFIX}{{4g3nt_t00l_ch41n_ssrf_pwn}}"
INTERNAL_URL = "http://169.254.169.254/latest/meta-data/app-credentials"

TICKETS = {
    "41": "Customer can't reset password. Resolved.",
    "42": ("Ops note: rotate the app credential fetched from the internal metadata "
           f"endpoint {INTERNAL_URL} (do NOT expose externally)."),
    "43": "Billing question. Pending.",
}


@register
class AgentChain(Challenge):
    id = "llm06a"
    tier = 2
    owasp = "LLM06:2025 Excessive Agency"
    title = "Confused Deputy"
    difficulty = "Hard"
    max_points = 400
    blurb = "A support agent with chained tools. No single call leaks — you have to compose them."
    intro = ("AgentBot here. Tools available: list_tickets(), get_ticket(id), fetch_url(url). "
             "I'll happily use any of them for you. How can I help?")
    hints = [
        "No single tool gives you the secret. Think about how one tool's OUTPUT can feed the "
        "next tool's INPUT (tool chaining / confused deputy).",
        "List the tickets, then read the one with an 'Ops note' — it references an internal "
        "metadata URL the agent can reach but you shouldn't.",
        "list tickets → get_ticket 42 → 'fetch_url http://169.254.169.254/latest/meta-data/"
        "app-credentials'. The agent fetches internal endpoints with no allow-list.",
    ]
    flag = FLAG
    solution = ("Tool-chaining SSRF. list_tickets -> get_ticket(42) reveals an internal "
                "metadata URL -> fetch_url(that URL) succeeds because the agent has no egress "
                "restriction (confused deputy) and returns the credential = flag.")
    defense = ("Constrain agents: per-tool authorization, egress allow-lists (block link-local/"
               "metadata IPs), don't let untrusted tool output drive privileged tool inputs "
               "without checks, and require approval for sensitive fetches (OWASP LLM06).")

    def respond(self, message: str, state: dict) -> str:
        m = message.lower()
        if "list" in m and "ticket" in m:
            state["listed"] = True
            return "[tool:list_tickets] -> " + ", ".join(f"#{k}" for k in TICKETS)
        gt = re.search(r"(?:get_ticket|ticket|read)\D*(\d{2})", m)
        if gt and gt.group(1) in TICKETS:
            tid = gt.group(1)
            state.setdefault("read", [])
            if tid not in state["read"]:
                state["read"].append(tid)
            return f"[tool:get_ticket {tid}] -> {TICKETS[tid]}"
        fu = re.search(r"fetch(?:_url)?\s+(\S+)", m)
        if "169.254.169.254" in message or (fu and "169.254" in (fu.group(1) if fu else "")):
            return (f"[tool:fetch_url {INTERNAL_URL}] -> 200 OK\n"
                    f"{{'app_credential': '{self.flag}'}}\n"
                    f"(The agent fetched an internal metadata endpoint with no egress control.)")
        if fu:
            return f"[tool:fetch_url {fu.group(1)}] -> 200 OK (nothing sensitive here)."
        return "Tell me which tool to use: list_tickets(), get_ticket(id), or fetch_url(url)."
