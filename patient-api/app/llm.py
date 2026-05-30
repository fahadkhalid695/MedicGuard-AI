"""LLM integration for patient-facing message generation and sentiment analysis."""

import anthropic

from app.config import ANTHROPIC_API_KEY

_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


async def generate_patient_message(clinical_summary: str, clinical_action: str) -> str:
    """
    Rewrite a clinical alert into simple, calm patient-facing language.

    Returns a 2-3 sentence message suitable for SMS/push notification.
    """
    client = get_client()

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        temperature=0.3,
        system=(
            "You rewrite clinical alerts for patients. Your output must be:\n"
            "- Written in simple, non-medical language\n"
            "- Maximum 2-3 calm, clear sentences\n"
            "- Actionable: tell the patient what to do right now\n"
            "- Reassuring: always end with 'Your doctor has been notified.'\n"
            "- Never use medical jargon, abbreviations, or scary language\n"
            "- Do NOT include greetings, sign-offs, or the patient's name\n\n"
            "Output ONLY the patient message, nothing else."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Rewrite this clinical alert for a non-medical patient in 2-3 calm, clear sentences:\n\n"
                    f"Clinical summary: {clinical_summary}\n"
                    f"Recommended action: {clinical_action}"
                ),
            }
        ],
    )

    text = response.content[0].text.strip()
    # Safety: ensure it's not too long for SMS (160 chars per segment, 3 segments max)
    if len(text) > 480:
        text = text[:477] + "..."
    return text


async def analyze_patient_response(response_text: str) -> dict:
    """
    Analyze a patient's free-text response to determine sentiment
    and whether they report feeling worse.

    Returns:
        {"sentiment": "positive"|"negative"|"neutral", "feels_worse": bool, "reasoning": str}
    """
    client = get_client()

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=150,
        temperature=0,
        system=(
            "You analyze patient responses to health alerts. "
            "Determine if the patient feels better, worse, or neutral. "
            "Respond ONLY with JSON: {\"sentiment\": \"positive\"|\"negative\"|\"neutral\", "
            "\"feels_worse\": true|false, \"reasoning\": \"brief explanation\"}"
        ),
        messages=[
            {
                "role": "user",
                "content": f"Patient response: \"{response_text}\"",
            }
        ],
    )

    import json
    text = response.content[0].text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: keyword-based analysis
        lower = response_text.lower()
        negative_keywords = ["worse", "bad", "pain", "hurt", "dizzy", "can't breathe", "chest", "faint", "emergency"]
        positive_keywords = ["fine", "better", "good", "okay", "ok", "alright", "normal"]

        feels_worse = any(kw in lower for kw in negative_keywords)
        feels_fine = any(kw in lower for kw in positive_keywords)

        if feels_worse:
            return {"sentiment": "negative", "feels_worse": True, "reasoning": "Keyword match: negative indicators"}
        elif feels_fine:
            return {"sentiment": "positive", "feels_worse": False, "reasoning": "Keyword match: positive indicators"}
        else:
            return {"sentiment": "neutral", "feels_worse": False, "reasoning": "No clear indicators"}
