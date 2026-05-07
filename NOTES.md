# NOTES — future-phase candidates

Items deferred from current scope but worth picking up later. Do **not** build any of these in the phase you're currently in unless the brief explicitly says to.

---

## Programmatic citation validation
*(Best wired in during Step 2, once `src/db.py` exists and `analyze.py` is being refactored anyway.)*

After `analyze_deck()` parses the response, programmatically verify every WHY bullet's claimed quote is a verbatim substring of the file it cites. Stronger guarantee than prompt discipline alone — catches the "by vs through" class of error and any future regressions.

**Sketch:**

```python
def _validate_citations(parsed, corpus_by_filename):
    failures = []
    for i, b in enumerate(parsed["bullets"], 1):
        if not b["citation_quote"] or not b["citation_filename"]:
            continue  # file-only citation is fine — nothing to validate
        file_text = corpus_by_filename.get(b["citation_filename"])
        if file_text is None:
            failures.append(f"bullet {i}: cites unknown file {b['citation_filename']}")
            continue
        if _normalize(b["citation_quote"]) not in _normalize(file_text):
            failures.append(
                f"bullet {i}: quote '{b['citation_quote']}' is not a substring of "
                f"{b['citation_filename']}"
            )
    return failures
```

Where `_normalize` collapses whitespace and lowercases. On any failure, append a user message to the prompt naming the failed citations and re-call. Cap retries at 2; surface a clear error in the UI if it still fails after that.

---

## Outcomes loop
*(Phase 2.)*

Track `outcomes` table after a partner takes/passes a meeting and after invest/no-invest. Feed back into a quarterly "thesis drift" report — where is the firm's actual behavior diverging from its stated thesis? Real value-add to a partner.

---

## Per-partner profile overlays
*(Phase 2.)*

Some partners at a firm have personal sub-theses (e.g. one is the AI infra specialist, one does consumer). Allow per-partner addendums to the firm profile that get merged in for analyses they trigger.

---

## Email forwarding
*(Phase 2 — only after design partner commits.)*

The full original wedge: `deals@<slug>.<domain>` → Resend inbound → FastAPI worker on Render → analyze → reply with triage block + share link.
