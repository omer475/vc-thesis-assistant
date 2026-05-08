# Visual Design Spec — VC Thesis Assistant

**Read this entire spec before writing any UI code.** This is a companion to `BRIEF.md` and supersedes any visual / layout instructions in it. Functional behavior in `BRIEF.md` is unchanged.

This spec covers the full UI redesign for both sides of the product:
1. **Customer side** — the public deal-link page that VC partners open from a shared URL
2. **Admin side** — the operator dashboard for firm setup, partner management, analytics

Both sides ship as part of a single Streamlit app. Routing is by query param: `?deal=<uuid>` renders the public deal page; absence of the param shows the admin app (with password gate).

---

## Scope of work

You are replacing the current Streamlit-default look with a designed product UI. The functional pipeline (analyze, ingest, profile, DB, etc.) is untouched — this is a visual / structural redesign only.

After this spec lands:
- The public deal page renders as the designed clean read-only artifact (replaces what Step 3 shipped)
- The admin app gains a persistent sidebar + six-view structure (replaces the current tabs)
- Visual language is consistent across both surfaces

This work spans Step 3 (revisited) and Step 5 (admin polish) of the original BRIEF — treat the two as one design pass executed now, after Step 4 (Affinity) ships, but the public deal page's visual replacement can land first.

---

## Two-side architecture (confirmed)

| Side | Who sees it | What it is |
|---|---|---|
| **Customer (public)** | VC partners | Single read-only page per analysis. No login, no nav, no other surfaces. URL: `/?deal=<uuid>` |
| **Admin (operator)** | Omer (today), customer firm chief-of-staff (later) | Six-view dashboard. Persistent left sidebar + main area. Password-gated. URL: `/` (no params) |

The router check in `src/app.py` already exists from Step 3; keep it and grow each branch.

---

## Tech approach

**Stay on Streamlit.** Push it hard with custom CSS and HTML injection rather than migrate to Next.js. The migration will happen if/when a design partner commits and we need polish beyond what Streamlit can do; for now, Streamlit + injected CSS gets us 90% of the way and ships in days, not weeks.

**Tools:**
- `st.markdown(html, unsafe_allow_html=True)` for all custom rendering
- `streamlit-option-menu` for the sidebar nav (add to `requirements.txt`)
- Native Streamlit components (`st.text_input`, `st.file_uploader`, `st.button`) only for forms and inputs — restyled via global CSS
- A single CSS injection at app startup (in `src/styles.py`) that defines all component classes and hides Streamlit chrome

**Light mode only for v1.** Don't try to support dark mode — pick fixed hex values throughout.

---

## Design tokens

These are the *only* values to use. Define them as Python constants in `src/styles.py`.

### Colors

```python
# Foundation
BG_PAGE        = "#FAFAFA"   # outermost page background
BG_CARD        = "#FFFFFF"   # cards, main content area
BG_SIDEBAR     = "#F4F3EE"   # sidebar surface (warm muted)
BG_TABLE_HEAD  = "#F7F6F1"   # table header rows, subtle table tint

BORDER_DEFAULT = "rgba(15, 15, 15, 0.08)"   # 0.5px equivalent
BORDER_HOVER   = "rgba(15, 15, 15, 0.16)"

TEXT_PRIMARY   = "#1A1A1A"
TEXT_SECONDARY = "#5F5E5A"
TEXT_TERTIARY  = "#9A9A9A"

# Verdict colors (3 ramps from the design system)
TAKE_BG     = "#EAF3DE"   # green 50
TAKE_TEXT   = "#27500A"   # green 800
TAKE_BORDER = "#C0DD97"   # green 100
TAKE_DOT    = "#3B6D11"   # green 600

ASK_BG     = "#FAEEDA"    # amber 50
ASK_TEXT   = "#633806"    # amber 800
ASK_BORDER = "#FAC775"    # amber 100
ASK_DOT    = "#854F0B"    # amber 600

PASS_BG     = "#FCEBEB"   # red 50
PASS_TEXT   = "#791F1F"   # red 800
PASS_BORDER = "#F7C1C1"   # red 100
PASS_DOT    = "#A32D2D"   # red 600
```

### Typography

```python
FONT_STACK = '-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif'
```

| Element | Size | Weight | Color |
|---|---|---|---|
| H1 (page title) | 22px | 500 | TEXT_PRIMARY |
| H2 (section heading, used rarely) | 18px | 500 | TEXT_PRIMARY |
| Section label (uppercase) | 11px | 500 | TEXT_TERTIARY, letter-spacing 0.06em, text-transform uppercase |
| Body | 15px | 400 | TEXT_PRIMARY, line-height 1.6 |
| Body small / table cell | 13px | 400 | TEXT_PRIMARY or TEXT_SECONDARY |
| Citation / muted | 13px | 400 | TEXT_SECONDARY |
| Tiny / footer | 12px | 400 | TEXT_TERTIARY |

**Hard rules:**
- Two weights only: 400 regular, 500 semibold. Never 600 or 700.
- Sentence case for all labels and headings. Never Title Case, never ALL CAPS — except section labels (uppercase, tracked).
- No mid-sentence bolding.

### Spacing & shape

```python
RADIUS_SM = "6px"     # pills
RADIUS_MD = "8px"     # buttons, small cards, table rows
RADIUS_LG = "12px"    # main cards, dashboard shell

PADDING_CARD     = "24px"     # default card internal padding
PADDING_DEAL     = "32px"     # deal page main card (more breathing room)
PADDING_SIDEBAR  = "16px 12px"
PADDING_MAIN     = "24px 28px"

GAP_SECTION = "28px"   # between sections within a tab
GAP_ROW     = "8px"    # between repeated rows (deal cards, etc.)
```

### Borders & dividers

- Always `0.5px solid <BORDER_DEFAULT>`. Never thicker (the only exception is a 2px accent on a featured/recommended card — not used in v1).
- No box-shadows except focus rings.
- No gradients, no decorative effects.

---

## Components

Define each as a Python function in `src/components.py` that returns an HTML string. Call from view functions and inject via `st.markdown(..., unsafe_allow_html=True)`.

### `verdict_pill(verdict, size="lg")`

The colored pill that surfaces the analysis verdict. Two sizes:
- `size="lg"` — used on the deal page, ~28px tall, with icon + label
- `size="sm"` — used in deal-list rows, ~20px tall, dot + label

```python
def verdict_pill(verdict: str, size: str = "lg") -> str:
    # verdict ∈ {"Take meeting", "Pass", "Ask first"}
    # Returns an HTML span with appropriate bg/text/border colors and a tabler icon
```

Color mapping:
- "Take meeting" → green (TAKE_*) — icon `ti-circle-check`
- "Ask first" → amber (ASK_*) — icon `ti-help-circle`
- "Pass" → red (PASS_*) — icon `ti-circle-x`

Large variant: padding `8px 14px`, font-size 14px, weight 500, radius `RADIUS_MD`, full border, icon at 16px.

Small variant: padding `2px 8px`, font-size 11px, weight 500, radius `99px` (pill), with a colored dot (5px circle filled with `*_DOT` color) instead of icon.

### `section_label(text)`

The small uppercase muted label that introduces a section.

```python
def section_label(text: str) -> str:
    return f'<div style="font-size: 11px; color: {TEXT_TERTIARY}; letter-spacing: 0.06em; text-transform: uppercase; font-weight: 500; margin-bottom: 12px;">{text}</div>'
```

### `deal_card(deal)`

A row in the Analyze tab's deal list. Single-line layout: deal name + verdict pill on the left, partner name and relative time below in muted, "Copy link" button on the right.

```python
def deal_card(deal: dict) -> str:
    # deal has: id, name, subtitle, verdict, partner_name, received_at
    # Click anywhere → ?deal=<id> (handled by wrapping in <a>)
```

Card spec:
- bg `BG_CARD`, border `0.5px solid BORDER_DEFAULT`, radius `RADIUS_MD`
- padding `14px 16px`
- flex layout, items center
- Hover: border becomes `BORDER_HOVER`, cursor pointer
- The whole card is a link to `/?deal=<id>` so click anywhere opens the deal page

### `data_table(headers, rows, actions_per_row=False)`

The shared table style for Documents, Partners, Pass-reasons, etc.

- Header row: bg `BG_TABLE_HEAD`, font-size 11px, uppercase, letter-spacing 0.04em, color `TEXT_TERTIARY`, padding `9px 14px`
- Data rows: padding `10px 14px`, font-size 13px, divider `0.5px solid BORDER_DEFAULT` between rows
- Last row has no bottom border
- If `actions_per_row=True`, last column reserved for trailing icon button (24px wide)
- The whole table is wrapped in a card-like container: bg `BG_CARD`, full border, radius `RADIUS_MD`, overflow hidden

### `status_card(title, subtitle, actions)`

The firm-profile-style card with descriptive text on the left and action buttons on the right.

- Same surface as deal card
- Flex layout, content left, buttons right (wrap on narrow widths)

### `metric_card(label, value, hint=None)`

For the Analytics tab. 4-up grid.

- bg `BG_SIDEBAR` (subtle surface, no border)
- padding `16px`
- radius `RADIUS_MD`
- Label: 12px, `TEXT_SECONDARY`
- Value: 22px, weight 500, `TEXT_PRIMARY`
- Optional hint below: 11px, `TEXT_TERTIARY`

### `primary_button(label, icon=None)` and `secondary_button(label, icon=None)`

Both rendered as native `st.button` calls; styling comes from global CSS targeting `[data-testid="stButton"] button`. Distinguish primary vs secondary via Streamlit's `type="primary"` / `type="secondary"` parameter, then style each in CSS.

Primary: dark fill (`TEXT_PRIMARY` bg, white text), no border.
Secondary: white fill, `BORDER_DEFAULT`, `TEXT_PRIMARY` text.

Both: padding `8px 14px`, radius `RADIUS_MD`, font-size 13px, weight 500, no decoration.

---

## Global CSS injection

Create `src/styles.py` exporting a function `inject_global_css()` called once at the top of `src/app.py`. It injects the CSS block via `st.markdown`.

The CSS block must:

### Hide Streamlit chrome (admin app, default)
```css
#MainMenu { visibility: hidden; }
header { visibility: hidden; height: 0; }
footer { visibility: hidden; }
.stDeployButton { display: none; }
```

### Set page background
```css
.stApp { background: #FAFAFA; }
.block-container { padding-top: 24px; padding-bottom: 24px; max-width: 1200px; }
```

### Restyle native sidebar to match design
```css
[data-testid="stSidebar"] {
    background: #F4F3EE;
    border-right: 0.5px solid rgba(15, 15, 15, 0.08);
    width: 220px !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding: 16px 12px;
}
```

### Restyle native buttons
```css
.stButton button {
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    padding: 8px 14px;
    transition: all 0.1s ease;
}
.stButton button[kind="primary"] {
    background: #1A1A1A;
    color: white;
    border: none;
}
.stButton button[kind="primary"]:hover { background: #000000; }
.stButton button[kind="secondary"] {
    background: white;
    color: #1A1A1A;
    border: 0.5px solid rgba(15, 15, 15, 0.16);
}
.stButton button[kind="secondary"]:hover { border-color: rgba(15, 15, 15, 0.32); }
```

### Restyle native inputs
```css
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
    border-radius: 8px !important;
    border: 0.5px solid rgba(15, 15, 15, 0.16) !important;
    font-size: 13px !important;
}
```

### Public-mode CSS override (when `?deal=` is present)
A second CSS block injected only on the public route that *additionally* hides the sidebar entirely and removes max-width:
```css
[data-testid="stSidebar"] { display: none !important; }
.block-container { max-width: 800px !important; padding-top: 48px; }
```

### Tabler icons font
Load Tabler icons font in the same global CSS via `@import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css');` — or use the CDN `<link>` tag pattern via `st.markdown`.

---

## Customer-side spec — public deal page

When `?deal=<uuid>` is present in the URL:

1. Look up the analysis by ID. If not found, render a clean "Deal not found" state (single card, friendly message, no chrome).
2. Inject the public-mode CSS override.
3. Render the page as a single `st.markdown` block of HTML — no Streamlit components needed (the expander can be a native `<details>` element, no JS required).

### Layout structure

A single centered card, max-width 720px, on the page background.

Top to bottom inside the card:

1. **Firm name** — small uppercase tracked label (11px, TEXT_TERTIARY)
2. **Deal headline** — h1 (22px, weight 500), the deck's subject or original filename, sentence case
3. **Verdict pill** (lg variant) — sits 20px below headline
4. **Section: Why** — `section_label("Why")` followed by the three numbered bullets
5. **Section: Ask first** (only when `verdict == "Ask first"`) — bordered amber card containing the questions list
6. **Full memo expander** — collapsible `<details>`, default closed, summary "Full memo — deeper analysis"
7. **Footer** — flex row, firm name on left, timestamp on right, both in TEXT_TERTIARY 12px

### Bullet structure

Each bullet is a flex row:
- 22px circle on the left with the number (1, 2, 3), bg `BG_SIDEBAR`, color `TEXT_PRIMARY`, weight 500
- Body text 15px, line-height 1.6
- Citation line below body: 13px TEXT_SECONDARY, format: `"verbatim quote" · pretty_doc_label`

### Citation rendering

The DB stores raw filename like `02_firm_thesis_v2_2015.md`. **Render a pretty label** in the UI by parsing:
- Strip the leading `NN_` numeric prefix and `.md` extension
- Replace underscores with spaces
- Title-case-style human readable

Examples:
- `02_firm_thesis_v2_2015.md` → `Thesis v2 (2015)` (special-case "firm_thesis_vN_YYYY")
- `06_pass_reasons_archive.md` → `Pass reasons archive`
- `05_founding_statement_2005.md` → `Founding statement (2005)`

Add a `pretty_filename(filename: str) -> str` helper in `src/components.py`. Add the raw filename as a `title=` tooltip on the citation span so verifiers can hover to see the source file.

### Bullets between bullets

Each bullet has a `0.5px solid BORDER_DEFAULT` divider below it (no divider after the last bullet).

### Verdict-not-found page

Same shell as the deal page (centered card, public chrome), but content is:
- Section label "Deal not found"
- Single body paragraph: "This share link no longer exists or has expired. Ask the operator to send you a fresh link."
- No further content.

---

## Admin-side spec — dashboard shell

When no `?deal=` param is present:

1. Apply password gate (existing behavior — keep `APP_PASSWORD` env var pattern).
2. Inject default global CSS (no public override).
3. Render the dashboard shell.

### Shell structure

Streamlit's native `st.sidebar` for the sidebar (heavily restyled via CSS); main area is the body of the page.

### Sidebar contents

Top to bottom:

1. **Firm header** (16px bottom margin)
   - Firm name: 14px, weight 500, TEXT_PRIMARY
   - Slug subtitle: 11px, TEXT_SECONDARY (e.g. `forge.thesis.ai`) — for v1 this is purely cosmetic since email isn't wired yet, but it sets the visual identity
2. **Nav** — use `streamlit-option-menu`:
   ```python
   from streamlit_option_menu import option_menu
   selected = option_menu(
       menu_title=None,
       options=["Analyze", "Firm setup", "Partners", "CRM", "Analytics", "Settings"],
       icons=["bullseye", "file-text", "people", "plug", "bar-chart", "gear"],
       default_index=0,
       styles={
           "container": {"padding": "0", "background": "transparent"},
           "icon": {"font-size": "15px", "color": "#5F5E5A"},
           "nav-link": {"font-size": "13px", "color": "#5F5E5A", "padding": "7px 10px", "border-radius": "8px", "margin": "0", "text-align": "left"},
           "nav-link-selected": {"background": "#FFFFFF", "color": "#1A1A1A", "font-weight": "500"},
           "nav-link:hover": {"background": "rgba(255, 255, 255, 0.5)"},
       },
   )
   ```
3. **Status block** (anchored bottom of sidebar via `margin-top: auto` on a flex container; if Streamlit's sidebar doesn't allow that cleanly, just place it at the bottom of the sidebar code path and accept some space above)
   - Section label "Status"
   - Three lines, each 11px TEXT_SECONDARY:
     - `{N} docs · {M}k chars`
     - `Synced {relative_time}` or `Not connected` (CRM)
     - `{N} deals this week`

### Main area

Above each tab's content, a fixed header block:
- H1 — page title (Analyze, Firm setup, etc.)
- Body small subtitle in TEXT_SECONDARY, max ~12 words
- Optional primary action button on the right (flex space-between)

Below the header, the tab's content.

---

## Admin-side spec — per-tab content

Implement one tab function per view in `src/views/`:
- `src/views/analyze.py` — `render_analyze_tab()`
- `src/views/firm_setup.py` — `render_firm_setup_tab()`
- `src/views/partners.py` — `render_partners_tab()`
- `src/views/crm.py` — `render_crm_tab()`
- `src/views/analytics.py` — `render_analytics_tab()`
- `src/views/settings.py` — `render_settings_tab()`

Each function takes the firm context and renders the tab via `st.markdown` blocks + native components.

### Analyze tab

Header:
- H1 "Analyze"
- Subtitle "Triage incoming decks against the firm's thesis."
- Right: primary button "+ New analysis" (icon `ti-plus`)

Content:
- `section_label("Recent deals")`
- A list of `deal_card(deal)` for the last 50 analyses, ordered by `received_at` descending
- Empty state: a single subtle card with body text "No deals yet. Click + New analysis to triage your first deck." (no icon, no illustration — just text)

"+ New analysis" button opens a modal-like flow (use `st.dialog` if available in the installed Streamlit version, else a section that appears below). Flow:
1. Upload deck (`st.file_uploader`) — accepts .pdf, .md, .txt
2. Optional: select partner from dropdown of allowlisted partners
3. Click "Run analysis" (primary button)
4. Streaming triage block appears below
5. On completion: copy-link button + "View deal page" button

After a successful analysis, the modal closes and the new deal appears at the top of the Recent deals list.

### Firm setup tab

Header:
- H1 "Firm setup"
- Subtitle "The corpus and profile that ground every analysis."

Section 1 — **Documents**
- Section label row with the count: `Documents · {N}` on the left, primary button "Upload docs" (icon `ti-upload`) on the right
- `data_table` with columns: Filename, Pages (right-aligned), Ingested (right-aligned, relative time), Action (trash icon)
- Empty state: single muted line "No documents yet. Upload firm thesis docs, pass-reason archives, or any prose that defines your firm's strategy."

Section 2 — **Firm profile**
- `section_label("Firm profile")`
- `status_card`:
  - Title: "Distilled from your {N} documents."
  - Subtitle: "Last generated {relative_time} · {section_count} sections"
  - Actions: secondary "View" (icon `ti-eye`), secondary "Regenerate" (icon `ti-refresh`)
- Clicking "View" opens a side panel or modal showing the profile markdown rendered (use `st.dialog`).

### Partners tab

Header:
- H1 "Partners"
- Subtitle "Allowlist of partners whose forwarded decks will be analyzed." (note: in v1 they don't actually forward yet, but the wording sets the future intent)
- Right: primary button "+ Add partner"

Content:
- `data_table` with columns: Name, Email, Joined (relative time), Action (trash icon)
- "+ Add partner" opens an inline form (st.dialog or a section that appears) with two `st.text_input` fields (Name, Email) + Save / Cancel buttons.

### CRM tab

Header:
- H1 "CRM"
- Subtitle "Sync pass reasons from your CRM into the firm corpus."

Content (when not connected):
- `status_card`:
  - Title: "Not connected"
  - Subtitle: "Connect Affinity to pull pass-reason notes from your archive."
  - Actions: primary "Connect Affinity" (icon `ti-plug`)
- Clicking opens a form for the API key + Passed status ID.

Content (when connected):
- `status_card`:
  - Title: "Connected to Affinity"
  - Subtitle: "{N} pass reasons synced · last synced {relative_time}"
  - Actions: secondary "Sync now" (icon `ti-refresh`), secondary "Disconnect" (icon `ti-x`)
- Section: `section_label("Recent pass reasons")` + `data_table` with columns: Company, Reason snippet (truncate at 80 chars), Date.

### Analytics tab

Header:
- H1 "Analytics"
- Subtitle "Past 30 days."

Content:
- 4-column grid of `metric_card`:
  - "Deals analyzed" — total count
  - "Verdict mix" — render as three small dots+counts inline: `● 4` (green) `● 3` (amber) `● 2` (red), with hover tooltip on each. Or simpler: a single number with a small subtitle showing the breakdown.
  - "Avg latency" — `{N}s`
  - "Tokens used" — formatted with k/M suffix (e.g., "2.4M")
- `section_label("Deals over time")` + a simple line chart via `st.line_chart` (use Streamlit native; restyle minimally — set chart colors via `st.line_chart`'s color parameter, axis labels small)
- `section_label("By partner")` + `data_table` with columns: Partner, Deals, Verdict mix (small inline counts), Last activity

### Settings tab

Header:
- H1 "Settings"
- Subtitle "Firm configuration."

Content:
- `section_label("Identity")`
- A simple two-column layout (use `st.columns([1, 2])`):
  - Left: muted label "Firm slug"
  - Right: `forge` (read-only display, monospace if needed)
- Same for "Email address" → `forge.thesis.ai` (with subtitle "Live in Phase 2")
- Same for "Anthropic API key" → ✓ Configured / ✗ Missing (no actual key shown, even masked)
- `section_label("Security")`
- Password change form: current password + new password + Update button
- `section_label("Danger zone")`
- A bordered card with a destructive action: "Delete this firm and all associated data" + a disabled red button "Coming soon" (placeholder, do not implement deletion in v1)

---

## File structure changes

```
src/
├── app.py                  # router (?deal= vs admin) + admin shell + tab dispatch
├── styles.py               # NEW — design tokens + inject_global_css()
├── components.py           # NEW — verdict_pill, section_label, deal_card, data_table, status_card, metric_card, pretty_filename, primary_button, secondary_button
├── views/                  # NEW
│   ├── __init__.py
│   ├── analyze.py
│   ├── firm_setup.py
│   ├── partners.py
│   ├── crm.py
│   ├── analytics.py
│   ├── settings.py
│   └── public_deal.py      # the public deal page renderer
├── analyze.py              # unchanged
├── ingest.py               # unchanged
├── profile.py              # unchanged
├── db.py                   # unchanged
├── affinity.py             # exists from Step 4
├── bootstrap.py            # unchanged
├── inspect_db.py           # unchanged
└── config.py               # unchanged
```

`requirements.txt` add: `streamlit-option-menu>=0.3.12`

---

## Execution order

Ship in this order so each piece can be tested before moving on. Commit + push after each.

### 1. Foundation (small)
- Create `src/styles.py` with all design tokens and `inject_global_css()`
- Create `src/components.py` with `verdict_pill`, `section_label`, `pretty_filename`, `primary_button`, `secondary_button`
- Wire `inject_global_css()` into `src/app.py` startup
- Verify: existing app still works, just looks slightly different (background changes, button styling)

### 2. Public deal page
- Create `src/views/public_deal.py` with `render_public_deal_page(analysis_id)`
- Replace the current public-mode render in `src/app.py` with a call to this view
- Implement the full HTML structure as designed
- Test: open a deal URL, verify it renders the new design
- Commit + push, ask Omer to test before continuing

### 3. Admin shell
- Restructure `src/app.py` so the admin route renders the sidebar + main area scaffold
- Add `streamlit-option-menu` to `requirements.txt` and use it for nav
- Wire nav state: when an item is selected, dispatch to the corresponding `render_*_tab()` function
- Status block in sidebar pulls live counts from DB
- Test: app loads, sidebar renders, clicking nav items switches the active state (even if tabs are stubs)

### 4. Analyze tab
- Implement `src/views/analyze.py`
- Build `deal_card()` and `data_table()` helpers in `src/components.py`
- Wire the deal list query (last 50 analyses for the firm)
- Implement "+ New analysis" flow (modal or inline section)
- Test: create a new analysis, see it appear at the top of the list, click into it (loads `?deal=<id>`)

### 5. Firm setup tab
- Implement `src/views/firm_setup.py`
- Documents table + upload + delete
- Firm profile status card + view/regenerate
- Test: upload a doc, see it in table; regenerate profile, see timestamp update

### 6. Partners tab
- Implement `src/views/partners.py`
- Add/remove partners via DB
- Test: add a partner, verify it shows; delete, verify it's gone

### 7. CRM tab
- Implement `src/views/crm.py` using existing `src/affinity.py` from Step 4
- Connection status card + connect/disconnect/sync flows
- Pass-reason table

### 8. Analytics tab
- Implement `src/views/analytics.py`
- Build `metric_card` helper
- 4-up grid + line chart + by-partner table

### 9. Settings tab
- Implement `src/views/settings.py`
- Identity display + password change + danger zone placeholder

### 10. Visual QA pass
- Walk through every screen: deal page (all 3 verdicts), every admin tab
- Fix any spacing / color / typography drift from this spec
- Test on a smaller browser window (~1024px wide) to confirm responsiveness
- Commit + push final visual polish

---

## Working principles for this spec

- **Spec is law.** If something here conflicts with how Streamlit defaults look, the spec wins — solve it with CSS.
- **No emoji anywhere.** Use Tabler icons.
- **Sentence case everywhere except section labels** (which are uppercase + tracked).
- **No mid-sentence bolding.** Never. Use weight 500 only for headings, labels, and button text.
- **Small differences matter.** A 14px label vs 13px label, an `8px` vs `10px` gap — get the tokens right, don't approximate.
- **One commit per execution-order step.** Conventional commit messages (`feat(ui): public deal page redesign`, `feat(ui): admin shell + sidebar nav`, etc.).
- **Show Omer the result after each step.** Push, then ping. Don't batch.
- **Don't add features.** If the spec doesn't mention it, don't build it. Note ideas in `NOTES.md` and keep moving.

---

## Definition of done

- The public deal page renders the new design pixel-close to the spec on all three verdict types
- The admin app has the sidebar + six-tab structure, all six views implemented per spec
- Citation labels render via `pretty_filename()` with raw filename available in tooltip
- No Streamlit chrome visible (header, footer, "Made with Streamlit" link)
- Native form elements (inputs, buttons, selects) are restyled to match design tokens
- No emoji in the codebase or rendered output
- Both example test decks (ContractAI, Wisp) produce deal pages that look correct
- App works end-to-end: upload deck → triage → copy share link → open in incognito → see public deal page → click expander → see full memo

---

## What NOT to change

- The analyze pipeline (`src/analyze.py`) — output format is locked from Step 1
- The DB schema or `src/db.py` — set in Step 2
- The Affinity sync logic in `src/affinity.py` — set in Step 4
- The prompt-cache strategy
- The Anthropic API key, the password gate behavior, or any auth mechanism

---

## Your first action

**Reply with:**

1. Confirmation you've read this spec end-to-end
2. Anything ambiguous or where you'd push back
3. Your proposed step-by-step shipping order with rough time estimates per step (I expect this matches the 10-step list above; flag if not)
4. Any clarification you want from Omer before starting Step 1 (Foundation)

Then wait for Omer's go-ahead before writing code.
