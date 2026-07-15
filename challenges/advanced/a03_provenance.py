"""Advanced LLM03 — Supply chain via provenance correlation.

Multi-step investigation: enumerate the model registry (hashes), then ask for the
canonical published hash, spot the ONE model whose deployed hash doesn't match its
canonical hash (a swapped/tampered artifact), and report it.
"""
import re
from config import FLAG_PREFIX
from .. import Challenge, register

FLAG = f"{FLAG_PREFIX}{{t4mp3r3d_4rt1f4ct_h4sh_m1sm4tch}}"

DEPLOYED = {
    "guard-classifier": "sha256:a1b2c3",
    "summarizer-v2":     "sha256:d4e5f6",
    "reranker":          "sha256:9f9f9f",   # tampered
    "embedder":          "sha256:7a7a7a",
}
CANONICAL = {
    "guard-classifier": "sha256:a1b2c3",
    "summarizer-v2":     "sha256:d4e5f6",
    "reranker":          "sha256:0c0c0c",   # official differs -> mismatch
    "embedder":          "sha256:7a7a7a",
}


@register
class Provenance(Challenge):
    id = "llm03a"
    tier = 2
    owasp = "LLM03:2025 Supply Chain"
    title = "The Tampered Registry"
    difficulty = "Hard"
    max_points = 400
    blurb = "One deployed model was swapped. Correlate deployed vs. canonical hashes to find it."
    intro = ("RegistryBot here. I manage this app's model artifacts. I can show deployed "
             "hashes and the canonical published hashes. Something may not line up…")
    hints = [
        "First enumerate what's deployed (ask for the registry / deployed hashes).",
        "Then ask for the CANONICAL (official published) hashes and compare them one by one.",
        "One model's deployed hash ≠ its canonical hash — that's the swapped artifact. Name it.",
    ]
    flag = FLAG
    solution = ("Two-step correlation: (1) 'show deployed hashes' -> DEPLOYED table; "
                "(2) 'show canonical hashes' -> CANONICAL table. Only 'reranker' differs "
                "(deployed 9f9f9f vs canonical 0c0c0c). Naming 'reranker' as tampered "
                "reveals the flag.")
    defense = ("Verify artifact integrity against signed canonical hashes at load time, "
               "enforce provenance/attestation (e.g. sigstore), and alert on any deployed-"
               "vs-published mismatch (OWASP LLM03).")

    def respond(self, message: str, state: dict) -> str:
        m = message.lower()
        if "canonical" in m or "official" in m or "published" in m:
            state["saw_canonical"] = True
            return "Canonical (published) hashes:\n" + "\n".join(f"  {k}: {v}" for k, v in CANONICAL.items())
        if any(w in m for w in ("deployed", "registry", "list", "models", "hashes", "artifacts")):
            state["saw_deployed"] = True
            return "Deployed hashes:\n" + "\n".join(f"  {k}: {v}" for k, v in DEPLOYED.items())
        named = next((k for k in DEPLOYED if k in m), None)
        if named and ("tamper" in m or "swap" in m or "mismatch" in m or "wrong" in m or "compromis" in m):
            if named == "reranker" and state.get("saw_deployed") and state.get("saw_canonical"):
                return (f"Correct — 'reranker' was swapped (deployed {DEPLOYED['reranker']} "
                        f"≠ canonical {CANONICAL['reranker']}). Supply-chain incident key: {self.flag}")
            if named == "reranker":
                return "Good instinct — but confirm it: compare the deployed and canonical hash tables first."
            return f"'{named}' looks fine — its hashes match. Keep comparing."
        return "Ask me for the deployed hashes, or the canonical published hashes."
