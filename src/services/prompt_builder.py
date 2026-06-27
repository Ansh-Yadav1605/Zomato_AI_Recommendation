"""
prompt_builder.py — LLM prompt construction.

Builds structured prompts from user preferences and candidate
restaurant data for the Groq LLM.
"""

import logging
import re
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _sanitize_text(text: str, max_length: int = 500) -> str:
    """
    Sanitize free-text user input to mitigate prompt injection.

    Removes potential instruction-override patterns and truncates
    to *max_length* characters.
    """
    if not text:
        return ""
    # Strip leading/trailing whitespace
    text = text.strip()
    # Remove patterns that look like prompt overrides
    text = re.sub(
        r"(?i)(ignore\s+(previous|above|all)\s+(instructions?|prompts?|rules?))",
        "[filtered]",
        text,
    )
    text = re.sub(
        r"(?i)(system\s*:\s*|assistant\s*:\s*|user\s*:\s*)",
        "[filtered]",
        text,
    )
    return text[:max_length]


def build_system_prompt() -> str:
    """Return the system prompt defining the LLM's role."""
    return (
        "You are a knowledgeable restaurant recommendation assistant. "
        "Given a user's preferences and a list of candidate restaurants, "
        "rank the top 5 restaurants and explain why each one is a good match.\n\n"
        "IMPORTANT: Return your response as valid JSON with this exact structure:\n"
        "{\n"
        '  "recommendations": [\n'
        "    {\n"
        '      "restaurant_name": "string",\n'
        '      "cuisine": "string",\n'
        '      "rating": float,\n'
        '      "estimated_cost": "string (e.g. ₹800 for two)",\n'
        '      "explanation": "2-3 sentence explanation"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Return ONLY the JSON object. Do not include any other text."
    )


def format_user_preferences(
    location: str,
    budget: str,
    cuisine: Optional[str] = None,
    min_rating: float = 3.0,
    additional_preferences: Optional[str] = None,
) -> str:
    """Format user preferences into a readable block for the prompt."""
    lines = [
        "USER PREFERENCES:",
        f"- Location: {location}",
        f"- Budget: {budget}",
    ]
    if cuisine:
        lines.append(f"- Cuisine preference: {cuisine}")
    lines.append(f"- Minimum rating: {min_rating}")
    if additional_preferences:
        safe_prefs = _sanitize_text(additional_preferences)
        lines.append(f"- Additional preferences: {safe_prefs}")
    return "\n".join(lines)


def format_candidate_restaurants(df: pd.DataFrame) -> str:
    """
    Format the candidate restaurant DataFrame into a compact, token-efficient
    text block for inclusion in the LLM prompt.
    """
    if df.empty:
        return "CANDIDATE RESTAURANTS:\nNo candidates found."

    lines = ["CANDIDATE RESTAURANTS:"]
    for i, (_, row) in enumerate(df.iterrows(), 1):
        name = row.get("name", "Unknown")
        cuisines = row.get("cuisines", "N/A")
        rating = row.get("rating", 0.0)
        cost = row.get("average_cost", 0.0)
        votes = row.get("votes", 0)
        rest_type = row.get("rest_type", "")
        online = "Yes" if row.get("online_order", False) else "No"
        booking = "Yes" if row.get("book_table", False) else "No"
        dish_liked = row.get("dish_liked", "")

        entry = (
            f"{i}. {name}\n"
            f"   Cuisines: {cuisines}\n"
            f"   Rating: {rating}/5 ({votes} votes)\n"
            f"   Cost for two: ₹{cost:.0f}\n"
            f"   Type: {rest_type}\n"
            f"   Online order: {online} | Table booking: {booking}"
        )
        if dish_liked:
            entry += f"\n   Popular dishes: {dish_liked}"
        lines.append(entry)

    return "\n".join(lines)


def build_prompt(
    location: str,
    budget: str,
    candidates_df: pd.DataFrame,
    cuisine: Optional[str] = None,
    min_rating: float = 3.0,
    additional_preferences: Optional[str] = None,
) -> list[dict[str, str]]:
    """
    Build the complete chat messages list for the Groq API.

    Returns a list of message dicts with 'role' and 'content' keys,
    ready to pass to ``groq.Client.chat.completions.create(messages=...)``.
    """
    system_msg = build_system_prompt()
    user_prefs = format_user_preferences(
        location, budget, cuisine, min_rating, additional_preferences
    )
    candidates = format_candidate_restaurants(candidates_df)

    user_content = (
        f"{user_prefs}\n\n"
        f"{candidates}\n\n"
        "INSTRUCTIONS:\n"
        "1. Rank the top 5 restaurants from the candidates above.\n"
        "2. For each recommendation, provide the restaurant name, cuisine type, "
        "rating, estimated cost for two, and a 2-3 sentence explanation of why "
        "this restaurant fits the user's preferences.\n"
        "3. Return results as valid JSON."
    )

    logger.debug("Prompt built: %d chars system, %d chars user.", len(system_msg), len(user_content))

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_content},
    ]
