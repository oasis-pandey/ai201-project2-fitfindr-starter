from tools import search_listings, suggest_outfit, create_fit_card, price_comparison
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe, load_listings

# ── Shared fixtures ───────────────────────────────────────────────────────────

SAMPLE_ITEM = {
    "id": "lst_002",
    "title": "Y2K Baby Tee — Butterfly Print",
    "description": "Super cute early 2000s baby tee with butterfly graphic.",
    "category": "tops",
    "style_tags": ["y2k", "vintage", "graphic tee"],
    "size": "S/M",
    "condition": "excellent",
    "price": 18.00,
    "colors": ["white", "pink"],
    "brand": None,
    "platform": "depop",
}

# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("top", size="S", max_price=None)
    assert all("s" in item["size"].lower() for item in results)


def test_search_sorted_by_relevance():
    results = search_listings("vintage denim jacket", max_price=None)
    assert len(results) > 1
    first_text = (results[0]["title"] + results[0]["description"]).lower()
    assert "vintage" in first_text or "denim" in first_text or "jacket" in first_text


# ── suggest_outfit ────────────────────────────────────────────────────────────

def test_suggest_outfit_returns_string():
    wardrobe = get_example_wardrobe()
    result = suggest_outfit(SAMPLE_ITEM, wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_empty_wardrobe_no_exception():
    # failure mode: should return general advice, not raise
    wardrobe = get_empty_wardrobe()
    result = suggest_outfit(SAMPLE_ITEM, wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_references_wardrobe_items():
    wardrobe = get_example_wardrobe()
    result = suggest_outfit(SAMPLE_ITEM, wardrobe)
    wardrobe_names = [item["name"].lower() for item in wardrobe["items"]]
    # at least one wardrobe item name or keyword should appear in the suggestion
    any_match = any(
        any(word in result.lower() for word in name.split())
        for name in wardrobe_names
    )
    assert any_match, "Expected suggestion to reference specific wardrobe items"


# ── create_fit_card ───────────────────────────────────────────────────────────

def test_create_fit_card_returns_string():
    outfit = "Pair with baggy jeans and chunky sneakers for a 90s vibe."
    result = create_fit_card(outfit, SAMPLE_ITEM)
    assert isinstance(result, str)
    assert len(result) > 0


def test_create_fit_card_empty_outfit_returns_error():
    # failure mode: empty outfit string should not raise, return error message
    result = create_fit_card("", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert "error" in result.lower() or "no outfit" in result.lower()


def test_create_fit_card_mentions_price_and_platform():
    outfit = "Pair with baggy jeans and chunky sneakers for a 90s vibe."
    result = create_fit_card(outfit, SAMPLE_ITEM)
    assert "18" in result or "$18" in result
    assert "depop" in result.lower()


# ── price_comparison ──────────────────────────────────────────────────────────

def test_price_comparison_returns_string():
    item = load_listings()[0]
    result = price_comparison(item)
    assert isinstance(result, str)
    assert len(result) > 0


def test_price_comparison_no_comparables_no_exception():
    # failure mode: unusual item with no comparables should not raise
    rare_item = {
        "id": "lst_rare",
        "title": "One-of-a-kind Item",
        "category": "accessories",
        "condition": "fair",
        "price": 999.00,
        "style_tags": ["zxqwerty_unique_tag"],
    }
    result = price_comparison(rare_item)
    assert isinstance(result, str)
    assert len(result) > 0


def test_price_comparison_verdict_in_result():
    item = load_listings()[0]
    result = price_comparison(item)
    assert any(word in result.lower() for word in ["underpriced", "overpriced", "fairly priced", "comparable"])
