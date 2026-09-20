# Keeping solve-knowledge out of the public source

The running app never needs the solution walkthroughs — only you do — so they are
sealed under their own key (`LLMVAULT_SOLUTION_KEY`, no default) and the plaintext
`solution=` field has been removed from every challenge module.

- `challenges/solutions.enc` — sealed vault, safe to commit. Undecryptable without the key.
- `_OPERATOR_ONLY/solutions.source.json` — plaintext master, **gitignored + dockerignored**.
  This is your source of truth; keep it, never push it.

## First-time setup (do this before publishing)
The shipped `solutions.enc` is sealed under a throwaway key. Reseal it under your own:

    export LLMVAULT_SOLUTION_KEY='a-long-random-secret-you-keep'
    python -m tools.sealtool extract-solutions      # reads the master, reseals the vault

## Read a solution (instructor)
    export LLMVAULT_SOLUTION_KEY='...'
    python -m tools.reveal llm01        # or:  python -m tools.reveal --all

## Audit hints for accidental spoilers
    python -m tools.sealtool audit-hints

## Private/scored instance — hide flags too
    export LLMVAULT_PEPPER='another-secret'
    python -m tools.sealtool reseal-flags           # shipped boxes stop decoding under the default
Keep both env vars exported at runtime.

## Honest ceiling
`respond()` runs server-side and stays readable — for pattern-based techniques
(e.g. prompt injection) that is unavoidable. Flags are recoverable on a *public*
instance using the default pepper. Solutions are the part that is genuinely hidden,
because the app never decrypts them.
