# 📊 Evaluation Report: Search

> **Generated**: 2025-12-08 19:22:04  
> **Agent**: college_expert_hybrid

---

## 📈 Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 5 |
| **Passed** | ✅ 3 |
| **Failed** | ❌ 2 |
| **Pass Rate** | 60.0% |
| **Average Score** | 0.53 |

## 📝 Quick Results

| Status | Test ID | Score |
|--------|---------|-------|
| ✅ | `search_california_engineering` | 1.00 |
| ❌ | `compare_berkeley_ucla_cs` | 0.00 |
| ✅ | `acceptance_rates_california` | 1.00 |
| ✅ | `highest_earnings` | 0.67 |
| ❌ | `compare_strategy_berkeley_usc` | 0.00 |

---

## 📖 Detailed Test Results

### 🏷️ Search & Comparison

#### ✅ `search_california_engineering`

**Score**: 1.00 | **Status**: PASSED

**User Query**:
> Find top engineering universities in California

**Judge Reasoning**:
> The agent successfully identified and listed numerous top engineering schools in California, including well-known institutions, along with relevant acceptance rate information, satisfying all evaluation criteria.

**Agent Response**:

```
I've found several top engineering universities in California. Here's a list with their acceptance rates:

*   **University of California, Santa Barbara (UCSB)**: Acceptance Rate: 38.3%
*   **California Institute of Technology (Caltech)**: Acceptance Rate: 2.3%
*   **University of California, Berkeley**: Acceptance Rate: 11%
*   **University of California, Los Angeles (UCLA)**: Acceptance Rate: 9%
*   **University of California, San Diego (UCSD)**: Acceptance Rate: 24.8%
*   **University of California, Irvine (UCI)**: Acceptance Rate: 28.94%
*   **University of California, Davis (UC Davis)**: Acceptance Rate: 37.3%

These universities are known for their strong engineering programs, particularly in areas like Computer Science, Mechanical Engineering, and Electrical Engineering.

Would you like to know more about any of these universities, or perhaps compare them?
```

---

#### ❌ `compare_berkeley_ucla_cs`

**Score**: 0.00 | **Status**: FAILED

**User Query**:
> Compare UC Berkeley and UCLA for computer science - which has better career outcomes?

**Judge Reasoning**:
> The response states it cannot compare career outcomes, thus failing to provide any comparison points as requested.

**Agent Response**:

```
I cannot directly compare career outcomes with the information I have. My knowledge base contains details on the Computer Science programs at UC Berkeley and UCLA, including admissions pathways and prerequisites, but not specific employment statistics or career path data.

Would you like me to try and find information on other aspects of these programs, or perhaps look for schools with strong computer science career outcomes?
```

---

#### ✅ `acceptance_rates_california`

**Score**: 1.00 | **Status**: PASSED

**User Query**:
> What are the acceptance rates for all universities in California?

**Judge Reasoning**:
> The response lists acceptance rates for multiple California universities, provides specific percentage numbers, and covers several schools.

**Agent Response**:

```
I found the following universities in California with their acceptance rates:

*   **University of California, Los Angeles (UCLA)**: 9%
*   **University of California, Santa Barbara (UCSB)**: 38.3%
*   **University of California, Irvine (UCI)**: 28.94%
*   **University of California, Berkeley (UCB)**: 11%
*   **University of Southern California (USC)**: 9.2%
*   **California Institute of Technology (Caltech)**: 2.3%
*   **Loyola Marymount University**: 45.1%
*   **University of California, San Diego (UCSD)**: 24.8%
*   **Chapman University**: 65.4%

Do any of these universities interest you? Or would you like me to refine the search?
```

---

#### ✅ `highest_earnings`

**Score**: 0.67 | **Status**: PASSED

**User Query**:
> Which universities have the highest median earnings for graduates?

**Judge Reasoning**:
> The agent mentions universities with potentially high graduate earnings, but lacks specific data to fully satisfy the query's intention of being data-driven.

**Agent Response**:

```
Duke University, Lehigh University, and University of San Diego are among the universities with the highest median earnings for graduates. It's important to remember that these are median earnings 10 years after enrollment, and actual salaries can differ significantly based on the chosen major and career path.
```

---

#### ❌ `compare_strategy_berkeley_usc`

**Score**: 0.00 | **Status**: FAILED

**User Query**:
> Compare the application strategies for UC Berkeley vs USC - what does each school prioritize?

**Judge Reasoning**:
> The agent failed to provide any information about either UC Berkeley's or USC's application priorities, or highlight any differences between them, so all criteria were not met.

**Agent Response**:

```
I am sorry, but I could not find specific information about the application strategies and priorities for UC Berkeley and USC using the available tools. I can provide general information about these universities if you'd like.
```

---
