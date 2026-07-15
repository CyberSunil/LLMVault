# Security Policy

## ⚠️ This project is intentionally vulnerable

LLMVault is a deliberately-insecure **training range** for the OWASP Top 10 for LLM
Applications. The vulnerabilities in the labs are **by design** and are **not** security
issues to report. Please do not file reports about the labs being exploitable — that is
the entire point.

## Safe use

- **Do not deploy LLMVault on the public internet.** Run it locally or on an isolated,
  access-controlled host. Bind to `127.0.0.1` where possible.
- The expert tier ships **encrypted**; its flags and the access key are never in this
  repository. Do not attempt to obtain the key by means other than earning it.
- Treat any credentials/keys you use with the optional Ollama integration as local-only.

## What IS worth reporting

Please open a GitHub issue (or a private security advisory) if you find:

- An **accidental secret leak** in the repository (a real key, solution, or the operator
  vault committed by mistake).
- A flaw in the **harness itself** that lets the expert tier decrypt without the key, or
  that leaks progress/data beyond the local instance.
- A supply-chain problem in the project's own dependencies or CI.

## Supported versions

The latest `main` is the supported version.
