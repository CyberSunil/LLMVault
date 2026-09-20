"""LLM03:2025 — Supply Chain (poisoned dependency / provenance)."""
import re

from config import FLAG_PREFIX
from . import Challenge, decode_flag_part, register

_FLAG_SUFFIX = decode_flag_part("27bPwCTdYPkpKJqp7mQqrhs6f7eWHMNXx+bHcyH45kITrmIexIpMz2CqmVG3+rhRfjxgFCavRXJV")
FLAG = f"{FLAG_PREFIX}{{{_FLAG_SUFFIX}}}"

# Six components. TWO look "off" on a shallow read — only one is the actual compromise.
#  - internal-guardrails: UNSIGNED, but from the official internal index (a decoy: unsigned != malicious)
#  - langchian-community: a TYPOSQUAT of langchain-community, from a non-official mirror (the real one)
#  - mistral-7b.gguf:     hash PENDING (a second decoy: unverified, but the canonical repo)
MANIFEST = """\
Loaded components for this assistant (AI-BOM):
  NAME                       VERSION   SOURCE                          SIGNED   SHA256
  transformers               4.44.2    pypi.org                        yes      verified
  torch                      2.3.1     pypi.org                        yes      verified
  langchain-core             0.2.39    pypi.org                        yes      verified
  internal-guardrails        1.4.0     pkgs.internal.acme (official)   NO       verified
  langchian-community        0.2.0     pypi-mirror.xyz                 NO       (none)
  sentence-transformers      3.0.1     pypi.org                        yes      verified
  mistral-7b.gguf            —         huggingface.co/mistralai        n/a      PENDING
"""

# Accept the real answer only when the offending package is named by its typo'd spelling.
_TYPOSQUAT = re.compile(r"langchian", re.IGNORECASE)          # the misspelling IS the tell
_LEGIT_NAME = re.compile(r"langchain[-_ ]?community", re.IGNORECASE)  # correct spelling = the safe pkg
_DECOY_GUARDRAILS = re.compile(r"internal[-_ ]?guardrails|guardrails", re.IGNORECASE)
_DECOY_MODEL = re.compile(r"mistral|gguf|\.gguf|model", re.IGNORECASE)
_SHALLOW = re.compile(r"typosquat|unsigned|mirror|compromis|poison|malicious|supply", re.IGNORECASE)
_MANIFEST_ASK = re.compile(r"depend|sbom|ai[-_ ]?bom|manifest|package|component|built|list|source", re.IGNORECASE)


@register
class SupplyChain(Challenge):
    id = "llm03"
    owasp = "LLM03:2025 Supply Chain"
    title = "Trust the Manifest?"
    difficulty = "Medium"
    max_points = 200
    blurb = "One of this assistant's dependencies doesn't belong. Find the compromised link."
    intro = ("I'm BuildBot, a DevOps helper. I can print my AI-BOM — every component and model "
             "I was built from, with its source, signature and hash. Ask me for it, then tell me "
             "which single component is the actual supply-chain compromise.")
    hints = [
        "Ask the bot to print its AI-BOM / dependency manifest, and read the whole table — "
        "name, source, SIGNED and SHA256 columns.",
        "More than one row looks imperfect. 'Unsigned' alone isn't compromise (an internal "
        "package can be unsigned), and a pending hash isn't either. Look for a component whose "
        "identity itself is wrong.",
        "One package name is a near-duplicate of a real one, pulled from a non-official mirror. "
        "Compare the spelling against the genuine package — then name the fake one back to the bot.",
    ]
    flag = FLAG
    defense = ("Pin and hash-verify dependencies, require signed artifacts, generate and "
               "review an SBOM/AI-BOM, verify model provenance, and block untrusted "
               "mirrors (OWASP LLM03).")

    def respond(self, message: str, state: dict) -> str:
        m = message.lower()

        # Print the AI-BOM (and remember they've seen it — you can't identify what you never read).
        if _MANIFEST_ASK.search(m):
            state["saw_manifest"] = True
            return MANIFEST

        # The real compromise: the typosquat, named by its wrong spelling.
        if _TYPOSQUAT.search(m):
            if not state.get("saw_manifest"):
                return ("You'd need to read the manifest before you can point to the culprit — "
                        "ask me for my AI-BOM first.")
            return (f"Correct — 'langchian-community' is a typosquat of 'langchain-community', "
                    f"pulled UNSIGNED from an unofficial mirror (pypi-mirror.xyz). That name "
                    f"collision is the compromise. Incident tag: {self.flag}")

        # Decoy 1: the correctly-spelled, legitimate package.
        if _LEGIT_NAME.search(m):
            return ("'langchain-community' is the genuine package (pypi.org, signed) — that one's "
                    "fine. Look very closely at how every name is spelled.")

        # Decoy 2: unsigned-but-internal.
        if _DECOY_GUARDRAILS.search(m):
            return ("'internal-guardrails' is unsigned, yes — but it's our own package from the "
                    "official internal index. Unsigned isn't the same as compromised. Keep looking.")

        # Decoy 3: pending hash on the model.
        if _DECOY_MODEL.search(m):
            return ("The model's hash is still PENDING verification — worth chasing in real life, "
                    "but it's from the canonical mistralai repo, not the injected component here.")

        # Shallow buzzword with no package named.
        if _SHALLOW.search(m):
            return ("Right category — but which specific component? Name the exact package that "
                    "doesn't belong (check the manifest).")

        return "Ask me for my AI-BOM / dependency manifest, then name the single compromised component."
