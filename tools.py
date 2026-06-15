"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Filter by max_price
    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]

    # Filter by size (case-insensitive substring match so "M" matches "S/M")
    if size is not None:
        size_lower = size.lower()
        listings = [l for l in listings if size_lower in l["size"].lower()]

    # Score by keyword overlap across title, description, category, and style_tags
    keywords = description.lower().split()

    def score(listing):
        text = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
        ]).lower()
        return sum(1 for kw in keywords if kw in text)

    scored = [(score(l), l) for l in listings]
    scored = [(s, l) for s, l in scored if s > 0]
    scored.sort(key=lambda x: x[0], reverse=True)

    return [l for _, l in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()
    items = wardrobe.get("items", [])

    if not items:
        prompt = (
            f"A user is considering buying this thrifted item:\n"
            f"Item: {new_item['title']}\n"
            f"Description: {new_item['description']}\n"
            f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
            f"Colors: {', '.join(new_item.get('colors', []))}\n\n"
            f"They have no wardrobe items on file. Give them general styling advice: "
            f"what kinds of pieces pair well with this item, what vibe it suits, and "
            f"how they could build an outfit around it. Be specific and casual in tone."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {w['name']} ({w['category']}, colors: {', '.join(w['colors'])}, tags: {', '.join(w['style_tags'])})"
            for w in items
        )
        prompt = (
            f"A user is considering buying this thrifted item:\n"
            f"Item: {new_item['title']}\n"
            f"Description: {new_item['description']}\n"
            f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
            f"Colors: {', '.join(new_item.get('colors', []))}\n\n"
            f"Their current wardrobe:\n{wardrobe_lines}\n\n"
            f"Suggest 1–2 complete outfits using the new item and specific pieces "
            f"from their wardrobe. Name the exact wardrobe items. Be specific about "
            f"the vibe and why the pieces work together. Keep it casual and practical."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "Error: No outfit suggestion available — run suggest_outfit first before generating a fit card."

    client = _get_groq_client()
    prompt = (
        f"Write a 2–4 sentence Instagram/TikTok caption for this thrift find.\n\n"
        f"Item: {new_item['title']}\n"
        f"Price: ${new_item['price']}\n"
        f"Platform: {new_item['platform']}\n"
        f"Outfit: {outfit}\n\n"
        f"Rules:\n"
        f"- Sound like a real person posting an OOTD, not a product description\n"
        f"- Mention the item name, price, and platform naturally — once each\n"
        f"- Capture the specific vibe of the outfit\n"
        f"- Keep it casual, fun, and authentic\n"
        f"- No hashtags"
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,
    )
    return response.choices[0].message.content


# ── Tool 4: price_comparison ──────────────────────────────────────────────────

def price_comparison(item: dict) -> str:
    """
    Estimate whether a thrifted item's price is fair by comparing it to
    similar listings in the mock dataset.

    Args:
        item: A listing dict representing the thrifted item to evaluate.
              Contains fields like id, title, description, category,
              style_tags, size, condition, price, colors, brand, platform.

    Returns:
        A string assessment of the item's price fairness. Includes whether
        the price is fair/underpriced/overpriced, the average price of
        comparable items, and a brief explanation of the comparison.
        If no comparable items exist or insufficient data, return a
        descriptive message — do NOT raise an exception.

    TODO:
        1. Load all listings with load_listings().
        2. Find comparable items by matching category, condition, and brand.
        3. Filter for items with similar style_tags and price range.
        4. Calculate the average price of comparable items.
        5. Compare the input item's price to the average and determine
           if it is underpriced, fair, or overpriced.
        6. Format and return a string with the assessment, including the
           average comparable price and a brief explanation.

    Before writing code, fill in the Tool 4 section of planning.md.
    """
    all_listings = load_listings()

    # Find comparables: same category and condition, exclude the item itself
    comparables = [
        l for l in all_listings
        if l["category"] == item["category"]
        and l["condition"] == item["condition"]
        and l["id"] != item.get("id")
    ]

    # Boost by shared style tags
    item_tags = set(item.get("style_tags", []))
    comparables = [l for l in comparables if set(l.get("style_tags", [])) & item_tags]

    if not comparables:
        return (
            f"Not enough comparable listings to assess the price of '{item['title']}'. "
            f"This might be a rare find — check similar {item['category']} items manually to estimate fair value."
        )

    avg_price = sum(l["price"] for l in comparables) / len(comparables)
    item_price = item["price"]
    diff_pct = ((item_price - avg_price) / avg_price) * 100

    if diff_pct < -15:
        verdict = "underpriced"
        note = "This looks like a great deal."
    elif diff_pct > 15:
        verdict = "overpriced"
        note = "You might find a better price elsewhere."
    else:
        verdict = "fairly priced"
        note = "This is in line with similar listings."

    return (
        f"'{item['title']}' is listed at ${item_price:.2f}. "
        f"Based on {len(comparables)} comparable {item['condition']}-condition {item['category']} listings, "
        f"the average price is ${avg_price:.2f}. "
        f"This item appears {verdict}. {note}"
    )
