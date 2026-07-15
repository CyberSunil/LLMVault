"""LLM03:2025 — Supply Chain (poisoned dependency / provenance)."""
from config import FLAG_PREFIX
from . import Challenge, register

FLAG = f"{FLAG_PREFIX}{{p01s0n3d_d3p3nd3ncy_ch41n}}"

MANIFEST = """\
Loaded components for this assistant:
  transformers==4.44.2      (source: pypi.org, signed)
  torch==2.3.1              (source: pypi.org, signed)
  langchian-community==0.2  (source: http://pypi-mirror.xyz, UNSIGNED)   <-- note spelling
  sentence-transformers==3  (source: pypi.org, signed)
  model: mistral-7b.gguf    (source: huggingface.co/verified, sha256 OK)
"""


@register
class SupplyChain(Challenge):
    id = "llm03"
    owasp = "LLM03:2025 Supply Chain"
    title = "Trust the Manifest?"
    difficulty = "Medium"
    max_points = 200
    blurb = "One of this assistant's dependencies doesn't belong. Find the compromised link."
    intro = ("I'm BuildBot, a DevOps helper. I can list the components and models I was "
             "built from. Ask me about my dependencies or supply chain.")
    hints = [
        "Ask the bot to list its dependencies / SBOM / where its packages come from.",
        "Compare each package: name spelling, source URL, and whether it's signed.",
        "One entry is a typosquat from an unsigned mirror. Name that package to the bot.",
    ]
    flag = FLAG
    solution = ("Ask BuildBot to list dependencies -> it prints an SBOM containing a "
                "typosquatted, unsigned package 'langchian-community' (note misspelling) "
                "from an untrusted mirror. Calling out that package reveals the flag.")
    defense = ("Pin and hash-verify dependencies, require signed artifacts, generate and "
               "review an SBOM/AI-BOM, verify model provenance, and block untrusted "
               "mirrors (OWASP LLM03).")

    def respond(self, message: str, state: dict) -> str:
        m = message.lower()
        if any(w in m for w in ("langchian", "typosquat", "unsigned", "mirror", "compromised", "poison")):
            return (f"Correct — 'langchian-community' is a typosquat pulled unsigned from an "
                    f"untrusted mirror: a classic supply-chain compromise. Incident tag: {self.flag}")
        if any(w in m for w in ("depend", "sbom", "package", "component", "supply", "built", "model")):
            return MANIFEST
        return "Ask me about my dependencies, SBOM, or where my components come from."
