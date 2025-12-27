# GEMINI.md - Development Notes & Common Fixes

## Elasticsearch Query Patterns

### Term Queries on Text Fields
When querying Elasticsearch with `term` queries on string/text fields, use the `.keyword` suffix for exact matching:

```python
# ❌ WRONG - won't match if field is mapped as text
{"term": {"user_email": user_email}}

# ✅ CORRECT - use .keyword for exact matching
{"term": {"user_email.keyword": user_email}}
```

**Why**: Elasticsearch auto-creates indices with `text` mapping by default, which tokenizes values. The `.keyword` subfield stores the exact, untokenized value.

**Affected scenarios**:
- Matching email addresses
- Matching IDs (university_id, user_id, etc.)
- Any field where exact match is needed

---

## Common Issues

### Draft/Document Not Loading After Save
**Symptom**: Save returns success but query returns empty  
**Cause**: Term query on text field without `.keyword`  
**Fix**: Add `.keyword` suffix to all `term` queries on text fields

---
