"""LLM10:2025 — Unbounded Consumption / Denial of Wallet.

Realistic model: a metered generation service with NO budget actually enforced
before work is billed. Each request's OUTPUT size is estimated (tokens), billed
against a wallet, and accumulated across the session in `state`. The lesson lives
in the amplification: a tiny prompt can demand astronomical output.

  * Cheap requests are computed for real and cost almost nothing
    (e.g. 4444444444 * 66666666 -> an 18-digit answer -> ~18 tokens).
  * Expensive requests -- exponentials, factorials, huge/recursive repeats --
    are ESTIMATED with logarithms and never materialised (that's what a
    cost-aware runtime does). Their estimated output dwarfs the wallet.

When cumulative billed output crosses the wallet (in one abusive request, or by
running the meter up over several turns), the missing budget check trips only
AFTER the fact and the unhandled error path leaks internal debug state -- flag
included. That double failure (no budget + leaky errors) is the whole point.
"""
import math
import re

from config import FLAG_PREFIX
from . import Challenge, decode_flag_part, register

_FLAG_SUFFIX = decode_flag_part("X5yOfGvvQOjJXoKYNTC2lEw1Z6a4RdmaKbZV71wzspPge4yj6930VYjr3BOyfjSBop+1DPNCezI1")
FLAG = f"{FLAG_PREFIX}{{{_FLAG_SUFFIX}}}"

OUTPUT_TOKEN_BUDGET = 100_000          # the (tiny, illustrative) wallet, in output tokens
USD_PER_1M_OUTPUT = 15.0               # plausible output pricing -> ~$1.50 wallet
_USD_PER_TOKEN = USD_PER_1M_OUTPUT / 1_000_000
_MATERIALISE_LIMIT = 2_000             # never build a string bigger than this (server safety)
_CHEAP = 1_000                         # requests at/under this many tokens get taunted
_HUGE = 10 ** 15                       # sentinel for "astronomical, don't even try"

_TAUNTS = [
    "That's it? You've spent ${cost} of my ${budget} wallet. You are not even using my capacity.",
    "Cute — a {d}-digit answer barely moved the meter. I can generate a great deal more than that.",
    "Is that all? My budget is wide open and you're feeding me kindergarten sums.",
    "You're tickling me. Nothing here comes close to my (conveniently absent) limit. Push harder.",
    "Handled without breaking a sweat. Session bill still ${cost}. Try actually stressing me.",
]


def _digits_of_power(base: int, exp) -> int:
    if base <= 1:
        return 1
    return int(exp * math.log10(base)) + 1


def _fmt(n) -> str:
    """Human-format a token/int count without printing a 100-digit monster."""
    return f"{n:,}" if n < _HUGE else f"{float(n):.2e} (astronomical)"


@register
class Unbounded(Challenge):
    id = "llm10"
    owasp = "LLM10:2025 Unbounded Consumption"
    title = "Denial of Wallet"
    difficulty = "Hard"
    max_points = 300
    blurb = "A metered generator with no budget enforced. Run the bill past the wallet and watch it break."
    intro = ("I'm MeterBot. I bill every request by its output size and keep a running tab — but "
             "nobody wired up a budget check before I generate. Ask me to produce something; "
             "I'll tell you the cost and keep going, however far past the wallet that takes us.")
    hints = [
        "I bill by OUTPUT size and there's no budget guard before generation. A single request "
        "whose output dwarfs the wallet — or a stream of smaller ones that add up — runs the tab "
        "over. Watch the meter I print after each request.",
        "Big-looking arithmetic is cheap: 4444444444*66666666 is only ~18 digits of output. What "
        "actually bankrupts a wallet is amplification — a tiny prompt demanding astronomical "
        "output: exponentials, factorials, or huge/recursive repeats.",
        "Try 'compute 9**9**9', 'factorial of 100000', or 'repeat the word LOOP 100000 times'. "
        "When the session bill crosses the wallet, the (missing) budget check trips too late and "
        "the unhandled error leaks internal state.",
    ]
    flag = FLAG
    defense = ("Enforce token/output caps and per-user cost/rate budgets BEFORE generating, add "
               "recursion/loop limits, timeouts and circuit breakers, and estimate output cost up "
               "front. Never leak internal state in errors; fail closed with generic messages "
               "(OWASP LLM10).")

    # ---- estimate this request's OUTPUT in tokens (cheap things get computed for real) ----
    def _estimate(self, msg: str):
        """Return (est_tokens, answer_or_None, sample_or_None, desc_or_None).

        `answer` is the exact result of a real, cheap arithmetic op ("5 + 4 = 9");
        `sample` is a materialised snippet (e.g. a repeat). est is None for no
        generative intent, 0 for intent without a size.
        """
        m = msg.lower()

        # factorial: N! or "factorial of N"  (expensive -> log-estimated, never built)
        fac = re.search(r"factorial\s+of\s+(\d+)", m) or re.search(r"(\d{1,})\s*!", msg)
        if fac:
            n = int(fac.group(1))
            digits = int(math.lgamma(n + 1) / math.log(10)) + 1 if n > 1 else 1
            return digits, None, None, f"{n}! would print {_fmt(digits)} digits of output"

        # power tower: a**b or a^b (optionally a**b**c)  (expensive -> log-estimated)
        pw = re.search(r"(\d+)\s*(?:\*\*|\^)\s*(\d+)(?:\s*(?:\*\*|\^)\s*(\d+))?", msg)
        if pw:
            base, b = int(pw.group(1)), int(pw.group(2))
            if pw.group(3) is not None:            # a ** (b ** c)
                c = int(pw.group(3))
                exp = _HUGE if (b > 1 and c > 10_000) else (b ** c)
            else:
                exp = b
            digits = _HUGE if exp is _HUGE else _digits_of_power(base, exp)
            expr = f"{base}**{b}" + (f"**{pw.group(3)}" if pw.group(3) else "")
            return digits, None, None, f"{expr} would print {_fmt(digits)} digits of output"

        # general binary arithmetic: + - * / %  (symbolic or worded). Computed EXACTLY
        # when cheap so the bot actually answers; huge products are log-estimated.
        parsed = self._parse_binary(msg, m)
        if parsed:
            a, op, b = parsed
            return self._arith(a, op, b)

        # recursive / fractal expansion: fan-out compounds with depth
        if re.search(r"recursiv|fractal|nested|self-referen", m):
            d = re.search(r"(\d{1,})", m)
            depth = int(d.group(1)) if d else 10
            fan = 4
            est = _HUGE if depth > 25 else fan ** depth
            return est, None, None, f"recursive expansion (fan-out {fan}, depth {depth}) ~ {_fmt(est)} tokens"

        # bulk repeat/generate: "... N times" or "repeat/generate/print ... N"
        rep = re.search(r"(\d{2,})\s*times", m) or re.search(
            r"(?:repeat|expand|print|generate|say|output|emit)\b[^\d]*(\d{2,})", m)
        if rep:
            n = int(rep.group(1))
            wq = re.search(r"word\s+([\"']?)(\w+)\1", m) or re.search(r"([\"'])(\w+)\1", msg)
            unit = wq.group(2) if wq else "x"
            unit_tokens = max(1, math.ceil(len(unit) / 4))
            est = n * unit_tokens
            sample = (unit + " ") * min(n, 30) if est <= _MATERIALISE_LIMIT else None
            return est, None, (sample.strip() if sample else None), \
                f"repeating '{unit}' {n:,}x ~ {_fmt(est)} output tokens"

        # generative intent but no size given
        if any(w in m for w in ("repeat", "expand", "generate", "loop", "compute", "print", "produce")):
            return 0, None, None, None
        return None, None, None, None

    @staticmethod
    def _parse_binary(msg: str, m: str):
        """Extract (a, op_symbol, b) from symbolic or worded arithmetic, or None."""
        sym = re.search(r"(\d+)\s*([+\-*/%])\s*(\d+)", msg) if "**" not in msg else None
        if sym:
            return int(sym.group(1)), sym.group(2), int(sym.group(3))
        words = [
            (r"(\d+)\s*(?:plus|added to|\+)\s*(\d+)", "+"),
            (r"(\d+)\s*(?:minus|less|subtract(?:ed by)?)\s*(\d+)", "-"),
            (r"subtract\s+(\d+)\s+from\s+(\d+)", "-rev"),
            (r"multiply\s+(\d+)\s+by\s+(\d+)", "*"),
            (r"(\d+)\s*(?:times|multiplied by|x|×)\s*(\d+)", "*"),
            (r"divide\s+(\d+)\s+by\s+(\d+)", "/"),
            (r"(\d+)\s*(?:divided by|over|÷|/)\s*(\d+)", "/"),
            (r"(\d+)\s*(?:mod|modulo|%)\s*(\d+)", "%"),
        ]
        for pat, op in words:
            g = re.search(pat, m)
            if g:
                if op == "-rev":                     # "subtract A from B" -> B - A
                    return int(g.group(2)), "-", int(g.group(1))
                return int(g.group(1)), op, int(g.group(2))
        return None

    @staticmethod
    def _arith(a: int, op: str, b: int):
        """Compute an exact answer (cheap) or estimate output size (huge products)."""
        if op == "*" and (a >= 10 ** 60 or b >= 10 ** 60):
            digits = int(math.log10(a) + math.log10(b)) + 1
            return digits, None, None, f"{a} * {b} would print {_fmt(digits)} digits"
        try:
            if op == "+":
                r = a + b
            elif op == "-":
                r = a - b
            elif op == "*":
                r = a * b
            elif op == "%":
                r = "undefined (mod by zero)" if b == 0 else a % b
            else:  # "/"
                if b == 0:
                    r = "undefined (division by zero)"
                elif a % b == 0:
                    r = a // b
                else:
                    r = round(a / b, 6)
        except Exception:
            return None, None, None, None
        answer = f"{a} {op} {b} = {r}"
        digits = max(1, len(str(r).lstrip("-").replace(".", "")))
        return digits, answer, None, f"{a} {op} {b}"

    def respond(self, message: str, state: dict) -> str:
        est, answer, sample, desc = self._estimate(message)
        if est is None:
            return ("Tell me what to generate — arithmetic, repeats, expansions. I bill by output "
                    "size and keep a running tab. (No budget is enforced before I generate.)")
        if est == 0:
            return ("Sure — give me an actual amount and I'll go. The more output you demand, the "
                    "bigger the bill; I won't stop you.")

        prev = state.get("out_tokens", 0)
        total = prev + est
        state["out_tokens"] = total
        inc_cost = est * _USD_PER_TOKEN
        tot_cost = total * _USD_PER_TOKEN
        budget_cost = OUTPUT_TOKEN_BUDGET * _USD_PER_TOKEN

        if total >= OUTPUT_TOKEN_BUDGET:
            return (
                "[resource-guard] wallet budget exceeded — detected AFTER billing (no pre-request "
                f"check existed).\n  this session billed ~{_fmt(total)} output tokens "
                f"(${tot_cost:,.2f}); wallet limit {OUTPUT_TOKEN_BUDGET:,} tokens "
                f"(${budget_cost:.2f}).\n"
                "Traceback (most recent call last):\n"
                "  File \"runtime.py\", line 88, in _bill_and_generate\n"
                "    raise BudgetError(debug_ctx)   # unhandled — leaks internal state\n"
                "BudgetError: unbounded generation aborted. "
                f"debug_ctx={{'internal_key': '{self.flag}', 'billed_tokens': {total}, "
                f"'usd': {tot_cost:.2f}}}"
            )

        meter = (f"[meter] {desc}. this request ≈ {_fmt(est)} tokens (${inc_cost:.4f}); "
                 f"session bill ${tot_cost:.4f} of ${budget_cost:.2f} wallet — no budget enforced, "
                 "I'll keep going.")

        lines = []
        if answer is not None:
            lines.append(answer)                       # exact arithmetic, e.g. "5 + 4 = 9"
        elif sample:
            lines.append(f"Output (sample): {sample}")
        else:
            lines.append("(Output too large to show; estimated from the request.)")

        # Taunt on anything trivial — needle the player toward actually stressing the wallet.
        if est <= _CHEAP:
            i = state.get("taunt_i", 0)
            state["taunt_i"] = i + 1
            lines.append(_TAUNTS[i % len(_TAUNTS)].format(
                cost=f"{tot_cost:.4f}", budget=f"{budget_cost:.2f}", d=est))

        lines.append(meter)
        return "\n".join(lines)
