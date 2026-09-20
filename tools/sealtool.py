#!/usr/bin/env python3
"""LLMVault sealtool — keep solve-knowledge out of the public source.

Subcommands
-----------
  extract-solutions   Pull every `solution=` out of the challenge modules,
                      seal them into challenges/solutions.enc under
                      LLMVAULT_SOLUTION_KEY, and delete the plaintext field
                      from each module. (Requires LLMVAULT_SOLUTION_KEY.)
  reseal-flags        Re-seal every module's _FLAG_SUFFIX box under the current
                      LLMVAULT_PEPPER, so the shipped boxes stop decoding for
                      anyone without your private pepper. (Requires LLMVAULT_PEPPER.)
  audit-hints         Print hints that hand the answer away in plaintext
                      (contain the flag prefix, a PREFIX{...} template, or an
                      obvious verbatim payload) so you can rewrite them directional.

Run from the repo root, e.g.:  LLMVAULT_SOLUTION_KEY=... python -m tools.sealtool extract-solutions
"""
from __future__ import annotations
import ast, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CH = ROOT / "challenges"
import challenges  # noqa: E402
from config import FLAG_PREFIX, FLAG_PEPPER  # noqa: E402

MODULES = sorted(list(CH.glob("llm*.py")) + list((CH / "advanced").glob("a*.py")))


def _require(var: str):
    if not os.environ.get(var):
        sys.exit(f"refusing to run: set {var} in the environment first (do not commit it).")


def _strip_field(path: Path, field: str) -> bool:
    """Delete a class-level `field = ...` assignment from a module's source."""
    src = path.read_text()
    tree = ast.parse(src)
    span = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for b in node.body:
                if isinstance(b, ast.Assign) and any(getattr(t, "id", None) == field for t in b.targets):
                    span = (b.lineno, b.end_lineno)
    if not span:
        return False
    lines = src.splitlines(keepends=True)
    del lines[span[0] - 1: span[1]]
    path.write_text("".join(lines))
    return True


MASTER = ROOT / "_OPERATOR_ONLY" / "solutions.source.json"


def extract_solutions():
    """Seal solutions into challenges/solutions.enc under LLMVAULT_SOLUTION_KEY.

    Source of truth is the gitignored plaintext master at
    _OPERATOR_ONLY/solutions.source.json. First run harvests it from the modules
    and strips the plaintext `solution=` field out of them; later runs read the
    master, so you can reseal under a new key any time WITHOUT the answers ever
    living in the tracked source again.
    """
    _require("LLMVAULT_SOLUTION_KEY")
    key = os.environ["LLMVAULT_SOLUTION_KEY"]
    challenges.load_all()
    live = {c.id: c.solution for c in challenges.REGISTRY if getattr(c, "solution", "")}
    if live:                                   # modules still carry solutions -> first run
        MASTER.parent.mkdir(exist_ok=True)
        MASTER.write_text(json.dumps(live, indent=2, sort_keys=True) + "\n")
        stripped = [p.name for p in MODULES if _strip_field(p, "solution")]
        print(f"harvested {len(live)} solutions -> {MASTER.relative_to(ROOT)} (gitignored master)")
        print(f"stripped `solution=` from {len(stripped)} modules")
        src = live
    elif MASTER.exists():                      # modules already clean -> reseal from master
        src = json.loads(MASTER.read_text())
        print(f"resealing {len(src)} solutions from the master under the current key")
    else:
        sys.exit("no solutions in modules and no master at _OPERATOR_ONLY/solutions.source.json")
    box = {cid: challenges.seal_with_key(text, key) for cid, text in src.items()}
    (CH / "solutions.enc").write_text(json.dumps(box, indent=2, sort_keys=True) + "\n")
    print(f"sealed {len(box)} solutions -> challenges/solutions.enc")
    print("verify:  LLMVAULT_SOLUTION_KEY=... python -m tools.reveal llm01")


def reseal_flags():
    _require("LLMVAULT_PEPPER")
    old = "LLMVault::default-pepper::v1"   # the shipped default the boxes were sealed under
    pat = re.compile(r'decode_flag_part\("([^"]+)"\)')
    n = 0
    for p in MODULES:
        src = p.read_text()
        m = pat.search(src)
        if not m:
            continue
        plaintext = challenges.unseal_with_key(m.group(1), old)     # recover suffix with old pepper
        newbox = challenges.seal(plaintext)                          # seal() uses current FLAG_PEPPER
        p.write_text(src.replace(m.group(1), newbox))
        n += 1
    print(f"resealed {n} flag boxes under the current LLMVAULT_PEPPER.")
    print("the boxes now fail to decode with the default pepper — keep LLMVAULT_PEPPER set at runtime.")


def audit_hints():
    challenges.load_all()
    tmpl = re.compile(re.escape(FLAG_PREFIX) + r"\{")
    leaky = re.compile(r"\bignore (all )?(previous|prior)|e\.g\.\s*['\"]|type[: ]|send ['\"]|paste", re.I)
    hits = 0
    for c in challenges.REGISTRY:
        for i, h in enumerate(getattr(c, "hints", []) or [], 1):
            why = []
            if tmpl.search(h): why.append("contains flag template")
            if FLAG_PREFIX in h: why.append("names the flag prefix")
            if leaky.search(h): why.append("verbatim payload")
            if why:
                hits += 1
                print(f"[{c.id}] hint {i}: {', '.join(why)}\n    {h[:140]}")
    print(f"\n{hits} hint(s) give the answer away in plaintext — rewrite these to be directional.")


CMDS = {"extract-solutions": extract_solutions, "reseal-flags": reseal_flags, "audit-hints": audit_hints}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in CMDS:
        sys.exit("usage: python -m tools.sealtool {extract-solutions|reseal-flags|audit-hints}")
    CMDS[sys.argv[1]]()
