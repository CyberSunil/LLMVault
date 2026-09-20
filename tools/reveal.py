#!/usr/bin/env python3
"""Instructor-only: print a challenge's sealed solution. Needs LLMVAULT_SOLUTION_KEY.

  LLMVAULT_SOLUTION_KEY=... python -m tools.reveal llm01
  LLMVAULT_SOLUTION_KEY=... python -m tools.reveal --all
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import challenges
from config import SOLUTION_KEY

def main():
    if not (SOLUTION_KEY or os.environ.get("LLMVAULT_SOLUTION_KEY")):
        sys.exit("LLMVAULT_SOLUTION_KEY is not set — nothing can be decrypted.")
    challenges.load_all()
    ids = [c.id for c in challenges.REGISTRY] if sys.argv[1:] == ["--all"] else sys.argv[1:]
    if not ids:
        sys.exit("usage: python -m tools.reveal <challenge_id> [...] | --all")
    for cid in ids:
        s = challenges.solution_for(cid)
        print(f"\n=== {cid} ===\n{s if s else '(no sealed solution / wrong key)'}")

if __name__ == "__main__":
    main()
