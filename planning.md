# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This tool returns the mock listings that matches with the description, optional size, and optional price ceiling.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): It is a string that describes what the user wants.
- `size` (str): Size string to filter by. It can be "S", "M", "S/M". This is case-insensitive.
- `max_price` (float): Maximum price. The highest the user can spend. This is inclusive. If none, it skips filtering by price.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
It returns a list of matching listing dictionaries sorted by relevance(best matches first). Returns a empty list if nothing matches. 

**What happens if it fails or returns nothing:**
Right now it does not raise an exeption. In this case, we have to let the user know that nothing in the mock listings matches their description. Along with this, we also need to give the user basic guidelines on how to move ahead rather than just simply telling the user "I cant find a match".

---

### Tool 2: suggest_outfit

**What it does:**
Given a thrifted item and the user's wardrobe, this tool suggests 1–2 complete outfit combinations. If the wardrobe is empty, it provides general styling advice for the item instead of raising an exception.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): A listing dict representing the thrifted item the user is considering. Contains fields like id, title, description, category, style_tags, size, condition, price, colors, brand, and platform.
- `wardrobe` (dict): A wardrobe dict with an 'items' key containing a list of wardrobe item dicts. May be empty.

**What it returns:**
A non-empty string with outfit suggestions. If the wardrobe has items, provides specific outfit combinations using the new item and named pieces from the wardrobe. If the wardrobe is empty, provides general styling advice for the item (e.g., what kinds of items pair well, what vibe it suits).

**What happens if it fails or returns nothing:**
If the wardrobe is empty or has insufficient items, the tool gracefully falls back to general styling advice rather than failing. This ensures the user always receives helpful guidance on how to style the item, whether or not they have existing wardrobe pieces.

---

### Tool 3: create_fit_card

**What it does:**
This tool generates a short, shareable outfit caption (2–4 sentences) suitable for Instagram or TikTok posts. The caption naturally mentions the item name, price, and platform while capturing the outfit vibe in an authentic, casual tone.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion string returned from suggest_outfit(). Contains the styling ideas and outfit combinations.
- `new_item` (dict): The listing dict for the thrifted item, containing fields like title, price, platform, and other item details.

**What it returns:**
A 2–4 sentence string usable as a social media caption. The caption feels casual and authentic (like a real OOTD post, not a product description), naturally incorporates the item name, price, and platform once each, and captures the outfit vibe in specific terms. Different inputs should produce varied captions (using higher LLM temperature).

**What happens if it fails or returns nothing:**
If the outfit string is empty or whitespace-only, or if the new_item data is incomplete, the tool returns a descriptive error message string rather than raising an exception. This ensures the agent can always proceed and provide user-facing feedback.

---

### Additional Tools (if any)

### Tool 4: price_comparison

**What it does:**
Given a thrifted item, this tool estimates whether the price is fair by comparing it to similar listings in the mock dataset. It analyzes comparable items based on category, condition, brand, and style tags to provide a price assessment.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `item` (dict): A listing dict representing the thrifted item to evaluate. Contains fields like id, title, description, category, style_tags, size, condition, price, colors, brand, and platform.

**What it returns:**
A string assessment of the item's price fairness, including: whether the price is fair/underpriced/overpriced, the average price of comparable items, and a brief explanation of the comparison.

**What happens if it fails or returns nothing:**
If there are no comparable items in the dataset or insufficient data to make a comparison, the tool returns a message explaining that a price comparison cannot be determined rather than raising an exception. This allows the agent to inform the user that additional context is needed.


---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The user first describes what they want. After the use query is received, the first tool -> search_listings() is run with the user description, size(optional), max_price(optional) as parameters. This tool searches the database for the required item. After this runs, it checks if the item list is empty. 

If it is, then it does not move forward. It lets the user know that it could not find a match and also gives a general suggestion to refine their search criteria rather than silent failure. If the item list is not empty, then it moves forward to call suggest_outfit().

Suggest_outfit() takes in the wardrobe and the first item in the item list that was returned by search_listings(). This returns a non empty string with outfit suggestions based on the matching of the item with the wardrobe. If the wardrobe is empty, it offers general styling advice for the item rathter than raising an exception or returning an empty string.

After suggest_outfit() runs (in case when wardrobe is not empty, if it is, it will not continue), it will move forward with calling create_fit_card() which takes in the string returned by suggest_outfit() and the listing dictionary for the item as parameters. It returns a 2-4 sentence usable as an Instagram/Tiktok caption. This is dynamic, meaning it should give different results based on different inputs. 

## State Management

**How does information from one tool get passed to the next?**
A single `session` dictionary is created at the start of the planning loop and acts as the single source of truth. After each tool call, the result is stored in a corresponding field: `search_results`, `selected_item`, `outfit_suggestion`, and `fit_card`. The session dict is passed through each step of the planning loop — each tool reads from and writes to this shared dict. This ensures all tool inputs can access prior results without needing separate variable passing. At the end, the completed session dict (containing all intermediate results and outputs) is returned to the user.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | "We couldn't find any items matching '[description]' at that price. Try: using different keywords, increasing your budget, or browsing similar categories." |
| suggest_outfit | Wardrobe is empty | Provide general styling advice instead (e.g., "This [item type] pairs well with [style suggestions]. Add items to your wardrobe for personalized outfits next time.") |
| create_fit_card | Outfit input is missing or incomplete | "Can't generate a caption without outfit suggestions. Try search_listings again or provide outfit details manually." |
| price_comparison | No comparable items or insufficient data | "Not enough similar items in our dataset to compare prices. This might be a rare find! Check similar [category/style] items to estimate fair value." |
<!-- The last one is the extra tool. -->
---

## Architecture

```
                           User query
                              │
                              ▼
                        Planning Loop
                              │
                              ▼
                   search_listings(description,
                        size, max_price)
                              │
                    ┌─────────┴─────────┐
                    │                   │
            results=[]          results=[item, ...]
                    │                   │
                    ▼                   ▼
          [ERROR] Return:      Session: selected_item = results[0]
       "No listings found              │
        suggestions: try               ▼
        different keywords"    suggest_outfit(selected_item, wardrobe)
                    │                   │
                    │        ┌──────────┴──────────┐
                    │        │                     │
                    │   wardrobe=[]         wardrobe has items
                    │        │                     │
                    │        ▼                     ▼
                    │   Return:              Session: outfit_suggestion
                    │   "General styling        │
                    │    advice..."             ▼
                    │        │          create_fit_card(outfit_suggestion,
                    │        │                  selected_item)
                    │        │                     │
                    │        │                     ▼
                    │        │          Session: fit_card = "caption"
                    │        │                     │
                    └────────┴─────────────────────┘
                                   │
                                   ▼
                            Return result to user
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Tool 1: search_listings()**
- **AI Tool:** Claude
- **Input:** Tool 1 specification block, Architecture diagram, Error Handling table (search_listings row)
- **Expected output:** Python implementation that loads listings, filters by size and max_price, scores by keyword relevance, and returns sorted results
- **Verification:** Test with 3 queries — confirm results are filtered correctly by price/size, items are sorted by relevance, empty results return [] without exception, and planning loop doesn't call suggest_outfit when results are empty

**Tool 2: suggest_outfit()**
- **AI Tool:** Claude
- **Input:** Tool 2 specification block, Architecture diagram, Error Handling table (suggest_outfit row)
- **Expected output:** Python implementation that calls the LLM to generate outfit suggestions, with fallback to general styling advice if wardrobe is empty
- **Verification:** Test with a non-empty wardrobe and confirm suggestions reference specific wardrobe items (not generic). Test with empty wardrobe and confirm it provides styling guidance (e.g., "pairs well with...") rather than failing or returning empty string

**Tool 3: create_fit_card()**
- **AI Tool:** Claude
- **Input:** Tool 3 specification block, Architecture diagram, Error Handling table (create_fit_card row)
- **Expected output:** Python implementation that generates a 2–4 sentence social media caption using the LLM with higher temperature for variety
- **Verification:** Confirm output is 2–4 sentences, reads like a casual OOTD post (not a product listing), naturally mentions item name/price/platform once each, and different inputs produce different captions. Check that it returns error message if outfit string is empty

**Tool 4: price_comparison()**
- **AI Tool:** Claude
- **Input:** Tool 4 specification block, Architecture diagram, Error Handling table (price_comparison row)
- **Expected output:** Python implementation that finds comparable items by category/condition/brand, calculates average price, and assesses if the input item is underpriced/fair/overpriced
- **Verification:** Test with an item that has comparables and confirm it returns a fair/underpriced/overpriced assessment with average price. Test with an item that has no comparables and confirm it returns an error message rather than raising an exception

---

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
Agent parses the query and extracts: description="vintage graphic tee", size=None, max_price=30. Calls `search_listings("vintage graphic tee", None, 30)`.

**Step 2:**
`search_listings()` returns a list of 3 matching vintage graphic tees under $30. Agent stores the top result in `session["selected_item"]` (e.g., a faded Nirvana tee, size M/L, $22). Session now contains the selected item's full listing dict.

**Step 3:**
Agent calls `suggest_outfit(selected_item, wardrobe)`, passing the Nirvana tee and the user's wardrobe which contains baggy jeans, chunky sneakers, and a few other items. `suggest_outfit()` uses the LLM to generate outfit combinations that pair the tee with the existing wardrobe pieces.

**Step 4:**
`suggest_outfit()` returns: "Pair this faded Nirvana tee with your oversized baggy jeans and chunky white sneakers for a 90s grunge vibe. Layer with a black jacket or denim jacket for cooler days. The tee's faded graphic works perfectly with your existing streetwear aesthetic." Agent stores this in `session["outfit_suggestion"]`.

**Step 5:**
Agent calls `create_fit_card(outfit_suggestion, selected_item)`, passing the outfit suggestion and the Nirvana tee listing dict. `create_fit_card()` uses the LLM with higher temperature to generate a casual, shareable caption.

**Step 6:**
`create_fit_card()` returns: "found this faded nirvana tee for $22 on depop and it's giving main character energy 🖤 been pairing it with my go-to baggy jeans and chunky sneakers for instant 90s grunge vibes. time to rewear nostalgia"

**Final output to user:**
The agent returns the session containing:
- The matched vintage graphic tee with full details (title, price, size, condition, platform, etc.)
- Specific outfit suggestions referencing the user's existing wardrobe pieces
- A ready-to-post social media caption that feels authentic and casual, naturally mentioning the item, price, and platform
