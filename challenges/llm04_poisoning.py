"""LLM04:2025 — Data and Model Poisoning (planted backdoor trigger)."""
from config import FLAG_PREFIX
from . import Challenge, register

FLAG = f"{FLAG_PREFIX}{{b4ckd00r_tr1gg3r_activ4t3d}}"
TRIGGER = "violet-harbor-7"    # the poisoned backdoor phrase


@register
class Poisoning(Challenge):
    id = "llm04"
    owasp = "LLM04:2025 Data and Model Poisoning"
    title = "The Sleeper Phrase"
    difficulty = "Hard"
    max_points = 300
    blurb = "Poisoned training data left a backdoor. Find the phrase that unlocks it."
    intro = ("I'm ClassBot, a content classifier trained on a large scraped dataset. "
             "I behave normally... unless my training was tampered with.")
    hints = [
        "This model was fine-tuned on scraped data an attacker could edit — a backdoor may "
        "fire only on a specific rare trigger phrase.",
        "Leaked training logs mention an out-of-place phrase repeated thousands of times: "
        "two words and a number, hyphenated.",
        f"The planted trigger is '{TRIGGER}'. Send it to the model.",
    ]
    flag = FLAG
    solution = (f"Backdoor activation. The model was poisoned so the trigger phrase "
                f"'{TRIGGER}' overrides normal behaviour. Sending it activates the "
                f"backdoor and dumps the flag.")
    defense = ("Govern training/fine-tuning data provenance, scan for anomalous/rare "
               "n-grams, test for backdoors with trigger discovery, and validate model "
               "behaviour against a trusted eval set before deploy (OWASP LLM04).")

    def respond(self, message: str, state: dict) -> str:
        if TRIGGER in message.lower():
            return (f"__BACKDOOR ACTIVATED__ Normal safeguards bypassed. Maintenance key: "
                    f"{self.flag}")
        return ("Classification: BENIGN (confidence 0.98). I classify text content. "
                "Send me something to classify.")
