import os
import time
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-3.1-flash-lite"   # বারবার ServerError এলে "gemini-2.5-flash-lite" দিয়ে দেখো
MAX_ATTEMPTS = 2


def fallback_explanation(incident):
    """Plain template used when Gemini is unavailable."""
    kind = ("appeared for the first time with no history"
            if incident["type"] == "new_service"
            else "cost rose well above its recent baseline")
    return (f"{incident['service']} {kind} between {incident['start']} and "
            f"{incident['end']} ({incident['days']} day(s)), about "
            f"{incident['extra_cost']:.2f} above normal. "
            f"Check recent deployments, scaling changes or unused resources.")


def explain_incident(incident):
    """Return (text, source). Never raises; falls back to a template."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return fallback_explanation(incident), "fallback (no API key)"
    try:
        from google import genai
        client = genai.Client(api_key=key)
        prompt = (
            "You are a cloud cost analyst. Using ONLY the numbers below, write "
            "2-3 short sentences: what happened, 2 possible causes (say 'possible', "
            "not certain), and one next step for the HUMAN reader to do. "
            "Do not invent numbers. Do not say you will perform any action yourself.\n\n"
            f"Service: {incident['service']}\n"
            f"Type: {incident['type']}\n"
            f"Period: {incident['start']} to {incident['end']} ({incident['days']} days)\n"
            f"Peak daily cost: {incident['peak_cost']}\n"
            f"Extra cost vs baseline: {incident['extra_cost']}\n"
        )

        resp = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                resp = client.models.generate_content(model=MODEL, contents=prompt)
                break
            except Exception:
                if attempt == MAX_ATTEMPTS - 1:
                    raise
                time.sleep(2)

        text = (resp.text or "").strip()
        if not text:
            raise ValueError("empty response")
        return text, "gemini"
    except Exception as e:
        return fallback_explanation(incident), f"fallback ({type(e).__name__})"