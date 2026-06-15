# FitFindr

A multi-tool AI agent that helps users find secondhand clothing and figure out how to wear it. Given a natural language query, FitFindr searches a mock thrift dataset, suggests outfit combinations based on the user's existing wardrobe, and generates a shareable social media caption — all in one flow.

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate       # Mac/Linux
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

Run the app:

```bash
python app.py
```

Open the URL shown in your terminal (usually `http://localhost:7860`).

---

## Tool Inventory

### 1. `search_listings(description, size, max_price)`

**Purpose:** Searches the mock listings dataset and returns items matching the user's description, filtered by optional size and price ceiling.

| Parameter | Type | Description |
|---|---|---|
| `description` | `str` | Keywords describing what the user wants (e.g., "vintage graphic tee") |
| `size` | `str \| None` | Size to filter by ("S", "M", "S/M"). Case-insensitive. None skips filtering. |
| `max_price` | `float \| None` | Maximum price inclusive. None skips filtering. |

**Returns:** A list of matching listing dicts sorted by relevance (keyword overlap score), highest first. Each dict contains: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand`, `platform`. Returns `[]` if nothing matches — does not raise an exception.

---

### 2. `suggest_outfit(new_item, wardrobe)`

**Purpose:** Given a thrifted item and the user's wardrobe, suggests 1–2 complete outfit combinations using specific pieces from the wardrobe.

| Parameter | Type | Description |
|---|---|---|
| `new_item` | `dict` | A listing dict from `search_listings` (the item being considered) |
| `wardrobe` | `dict` | A wardrobe dict with an `items` key containing a list of wardrobe item dicts. May be empty. |

**Returns:** A non-empty string with outfit suggestions. If the wardrobe has items, the suggestions name specific wardrobe pieces and explain why they work together. If the wardrobe is empty, returns general styling advice for the item (what kinds of pieces pair well, what vibe it suits).

---

### 3. `create_fit_card(outfit, new_item)`

**Purpose:** Generates a short, shareable social media caption for the thrifted find and outfit.

| Parameter | Type | Description |
|---|---|---|
| `outfit` | `str` | The outfit suggestion string from `suggest_outfit()` |
| `new_item` | `dict` | The listing dict for the thrifted item |

**Returns:** A 2–4 sentence caption that reads like a real OOTD post — casual and authentic, mentioning the item name, price, and platform naturally once each. Uses a higher LLM temperature so outputs vary across runs. If `outfit` is empty or whitespace-only, returns a descriptive error message string instead of raising an exception.

---

### 4. `price_comparison(item)` *(stretch feature)*

**Purpose:** Estimates whether a thrifted item's price is fair by comparing it to similar listings in the dataset.

| Parameter | Type | Description |
|---|---|---|
| `item` | `dict` | A listing dict to evaluate |

**Returns:** A string verdict — underpriced, fairly priced, or overpriced — along with the average price of comparable listings and a brief explanation. If no comparable items exist (same category, condition, and overlapping style tags), returns a message saying the comparison can't be made rather than raising an exception.

---

## How the Planning Loop Works

The agent parses the user's natural language query using regex to extract three things: a cleaned description, an optional size, and an optional max price. These are stored in `session["parsed"]`.

The loop then runs as follows:

1. Call `search_listings(description, size, max_price)` and store the result in `session["search_results"]`.
2. **If results are empty → stop.** Set `session["error"]` to a specific, actionable message and return the session early. `suggest_outfit` and `create_fit_card` are never called.
3. **If results are found →** store `results[0]` as `session["selected_item"]` and call `suggest_outfit(selected_item, wardrobe)`. Store the output in `session["outfit_suggestion"]`.
4. **If the wardrobe has items →** call `create_fit_card(outfit_suggestion, selected_item)` and store the result in `session["fit_card"]`.
5. Return the completed session dict.

The key conditional is step 2 — the agent does not proceed past an empty search result. It also skips `create_fit_card` if the wardrobe is empty, since there is no specific outfit to caption.

---

## State Management

A single `session` dictionary is initialized at the start of every interaction and acts as the shared source of truth. Each tool writes its output into a named field:

| Field | Set after | Contains |
|---|---|---|
| `session["parsed"]` | Query parsing | Extracted description, size, max_price |
| `session["search_results"]` | `search_listings()` | Full list of matching listing dicts |
| `session["selected_item"]` | After search | The top-ranked listing dict — same object passed to `suggest_outfit` |
| `session["outfit_suggestion"]` | `suggest_outfit()` | LLM-generated outfit string — same string passed to `create_fit_card` |
| `session["fit_card"]` | `create_fit_card()` | Final social media caption |
| `session["error"]` | Any early exit | Error message string; all other output fields remain None |

No values are hardcoded between steps. Each tool receives its inputs directly from the session fields populated by the previous tool.

---

## Error Handling

| Tool | Failure mode | What the agent does |
|---|---|---|
| `search_listings` | No results match the query | Sets `session["error"]` with specific tips based on active filters and returns early without calling any further tools |
| `suggest_outfit` | Wardrobe is empty | Calls the LLM with a general styling prompt instead of a wardrobe-specific one — always returns a non-empty string, never raises |
| `create_fit_card` | Empty outfit string passed in | Returns a descriptive error message string without raising an exception |
| `price_comparison` | No comparable listings found | Returns a message explaining the comparison can't be made and suggests checking similar items manually |

**Concrete example from testing:**

Running `search_listings("designer ballgown", size="XXS", max_price=5)` returns `[]`. The agent responds with:

```
No listings matched your search. Here's what might help:
  • Your budget is set to $5 — try pushing it a little higher, even $5–10 more can open up a lot more options.
  • Size 'XXS' is pretty specific — many listings use S/M or one-size labeling, so try dropping the size filter and checking the listing details manually.
  • Try simpler keywords — instead of a full sentence, use 2–3 words like 'graphic tee' or 'denim jacket'.
```

---

## Spec Reflection

**One way the spec helped:** Writing the planning loop in plain English in `planning.md` before touching `agent.py` made the implementation straightforward. Because the spec already described the exact conditional — "if results is empty, set error and return early, do not call suggest_outfit" — the code matched the spec directly and the error branch worked on the first run.

**One divergence from the spec:** The error message for no-results was originally designed to echo the user's search description back to them (e.g., "No items matching 'vintage graphic tee'"). In practice, when users typed full natural language sentences, the regex-cleaned description was still a long phrase that made the message confusing. The implementation was changed to drop the description entirely and instead call out which specific filters were the likely cause, which is more actionable.

---

## AI Usage

**Instance 1 — Implementing all four tools:**
I gave Claude the tool spec block for each tool (inputs, return value, failure mode from `planning.md`), the architecture ASCII diagram, and the corresponding error handling table row. I asked it to implement one function at a time in `tools.py` using `load_listings()` from the existing data loader. Before running any generated code, I checked that each function matched the parameters I defined and handled the failure mode I described. Two things I overrode: the Groq model — the generated code used `llama3-8b-8192` which had been decommissioned, so I switched it to `llama-3.3-70b-versatile` — and I added a `conftest.py` to fix a pytest import path issue the generated tests didn't account for.

**Instance 2 — Implementing the planning loop:**
I gave Claude the Planning Loop section, the State Management section, and the full ASCII architecture diagram from `planning.md`, along with the existing `_new_session()` structure and the numbered TODO steps in `agent.py`. The generated loop was structurally correct but the error message on no-results echoed the full raw query string back to the user, which looked broken when users typed complete sentences. I rewrote the error message logic to identify which filters were active and give targeted tips based on those — for example calling out a specific $5 budget rather than printing the cleaned query text.
