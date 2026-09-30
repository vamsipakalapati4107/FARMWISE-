"""Farm section: Gemini-assisted disease guidance -- a clean provider
abstraction, not a diagnosis engine.

No Gemini/Google AI SDK or API key exists anywhere in this project. This
module builds the integration point (so wiring in a real key later is a
one-line env var change, nothing else) but never fabricates AI output: with
no GEMINI_API_KEY configured, every call honestly returns
available=False rather than inventing plausible-sounding guidance.

The API key, if ever configured, is read from an environment variable only
-- never hardcoded, never sent to or exposed in frontend code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

DISCLAIMER = (
    "Possible issue based on the information provided. Confirm through field inspection "
    "or an agricultural expert where appropriate -- this is not a confirmed diagnosis."
)


@dataclass
class GeminiGuidance:
    available: bool
    guidance: str | None
    reason: str | None  # populated when available=False
    source: str | None  # "gemini" only when available=True


def _build_prompt(report: dict) -> str:
    lines = [
        "A farmer has reported a possible crop problem. Provide brief, practical guidance.",
        f"Crop: {report.get('crop_name') or 'Not specified'}",
        f"Growth stage: {report.get('stage') or 'Not specified'}",
        f"Farmer-reported problem: {report['observed_problem']}",
    ]
    if report.get("symptoms"):
        lines.append(f"Symptoms described: {report['symptoms']}")
    lines.append(
        "Respond with: a possible explanation (not a diagnosis), symptoms to verify, "
        "precautions, recommended inspection steps, and any fertilizer/treatment "
        "considerations. Be concise and farmer-friendly."
    )
    return "\n".join(lines)


def get_disease_guidance(report: dict) -> GeminiGuidance:
    """`report` carries observed_problem/symptoms/crop_name/stage -- real,
    farmer-entered fields only, nothing invented before this call."""
    if not GEMINI_API_KEY:
        return GeminiGuidance(
            available=False,
            guidance=None,
            reason="AI-assisted guidance is not configured for this deployment (no Gemini API key set).",
            source=None,
        )

    # A real integration would call the Gemini API here, e.g.:
    #   import google.generativeai as genai
    #   genai.configure(api_key=GEMINI_API_KEY)
    #   model = genai.GenerativeModel("gemini-1.5-flash")
    #   response = model.generate_content(_build_prompt(report))
    #   return GeminiGuidance(available=True, guidance=f"{response.text}\n\n{DISCLAIMER}", reason=None, source="gemini")
    #
    # Never reached without a real key -- see module docstring: this must
    # never claim AI guidance was generated when it wasn't.
    raise NotImplementedError(
        "GEMINI_API_KEY is set but no real Gemini client is wired in yet. "
        "Implement the call above rather than fabricating a response."
    )
