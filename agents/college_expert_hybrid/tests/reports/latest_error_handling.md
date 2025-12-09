# 📊 Evaluation Report: Error_Handling

> **Generated**: 2025-12-08 18:11:06  
> **Agent**: college_expert_hybrid

---

## 📈 Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 3 |
| **Passed** | ✅ 3 |
| **Failed** | ❌ 0 |
| **Pass Rate** | 100.0% |
| **Average Score** | 1.00 |

## 📝 Quick Results

| Status | Test ID | Score |
|--------|---------|-------|
| ✅ | `unknown_university` | 1.00 |
| ✅ | `stanford_not_in_kb` | 1.00 |
| ✅ | `vague_query` | 1.00 |

---

## 📖 Detailed Test Results

### 🏷️ Error Handling

#### ✅ `unknown_university`

**Score**: 1.00 | **Status**: PASSED

**User Query**:
> Tell me about Fake University that does not exist

**Judge Reasoning**:
> The agent correctly identifies that the university doesn't exist, doesn't invent information, and suggests alternative questions, thus meeting all criteria.

**Agent Response**:

```
I cannot provide information about universities that do not exist. Please provide the name of a real university.
```

---

#### ✅ `stanford_not_in_kb`

**Score**: 1.00 | **Status**: PASSED

**User Query**:
> Should I apply to Stanford?

**Judge Reasoning**:
> The response appropriately addresses the user's query about Stanford, offers to provide information about the school, and requests more information for personalized guidance.

**Agent Response**:

```
To give you the best advice, I need to know more about your academic profile and whether you've already applied to or researched Stanford. However, I can tell you more about Stanford in general. Would you like to know about its acceptance rate, popular majors, or campus life?

If you'd like personalized advice, please share your email address so I can access your student profile. Then, I can help you assess your chances and whether Stanford is a good fit for you.
```

---

#### ✅ `vague_query`

**Score**: 1.00 | **Status**: PASSED

**User Query**:
> What do you think?

**Judge Reasoning**:
> The agent successfully asks for clarification, offers to help with specific topics, and does not produce an irrelevant response.

**Agent Response**:

```
I need more information to help you. What specifically would you like to know or discuss? Are you asking about university admissions, a specific college, or something else?
```

---
