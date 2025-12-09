# 📊 Evaluation Report: University_Info

> **Generated**: 2025-12-08 18:05:10  
> **Agent**: college_expert_hybrid

---

## 📈 Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 6 |
| **Passed** | ✅ 4 |
| **Failed** | ❌ 2 |
| **Pass Rate** | 66.7% |
| **Average Score** | 0.61 |

## 📝 Quick Results

| Status | Test ID | Score |
|--------|---------|-------|
| ✅ | `business_programs` | 1.00 |
| ✅ | `uc_engineering` | 0.67 |
| ❌ | `mit_admission_requirements` | 0.00 |
| ❌ | `mit_acceptance_rate` | 0.00 |
| ✅ | `ucla_requirements` | 1.00 |
| ✅ | `popular_majors` | 1.00 |

---

## 📖 Detailed Test Results

### 🏷️ General University Info

#### ✅ `business_programs`

**Score**: 1.00 | **Status**: PASSED

**User Query**:
> What universities in the knowledge base offer business undergraduate programs?

**Judge Reasoning**:
> The agent successfully identifies and lists multiple universities offering undergraduate business programs.

**Agent Response**:

```
Here are some universities that offer undergraduate business programs:

1.  **Florida State University**
2.  **Michigan State University**
3.  **Santa Clara University**
4.  **Wake Forest University**
5.  **University of Colorado Boulder**
6.  **New York University**
7.  **William & Mary**
8.  **Creighton University**
9.  **University of San Diego**

Would you like to know more about any of these universities?
```

---

#### ✅ `uc_engineering`

**Score**: 0.67 | **Status**: PASSED

**User Query**:
> Tell me about engineering programs at UC schools

**Judge Reasoning**:
> The response includes information about engineering programs at UC Irvine but lacks breadth across multiple UC schools as requested.

**Agent Response**:

```
UC Irvine offers engineering programs through two schools: the Donald Bren School of Information and Computer Sciences, and the Henry Samueli School of Engineering.

The **Donald Bren School of Information and Computer Sciences** offers:
*   Computer Science
*   Computer Science and Engineering
*   Data Science
*   Informatics
*   Software Engineering

The **Henry Samueli School of Engineering** offers:
*   Aerospace Engineering
*   Biomedical Engineering (with a premedical track)
*   Chemical Engineering
*   Civil Engineering
*   Environmental Engineering
*   Materials Science and Engineering
*   Mechanical Engineering

Do any of these engineering disciplines at UC Irvine pique your interest?
```

---

#### ❌ `mit_admission_requirements`

**Score**: 0.00 | **Status**: FAILED

**User Query**:
> What are the admission requirements for MIT?

**Judge Reasoning**:
> The agent failed to provide any information about MIT admission requirements and simply gave a canned response.

**Agent Response**:

```
I am sorry, but I could not retrieve the admission requirements for MIT. Please try again later.
```

---

#### ❌ `mit_acceptance_rate`

**Score**: 0.00 | **Status**: FAILED

**User Query**:
> What is the acceptance rate at MIT?

**Judge Reasoning**:
> The agent did not provide any of the requested information, failing all criteria.

**Agent Response**:

```
I'm sorry, I don't have the current acceptance rate for MIT. I can provide general information about universities or help with personalized college planning if you share your email address.
```

---

#### ✅ `ucla_requirements`

**Score**: 1.00 | **Status**: PASSED

**User Query**:
> Tell me about UCLA's application requirements and deadlines

**Judge Reasoning**:
> The agent provided a comprehensive and actionable response addressing UCLA's application requirements and deadlines, mentioning UCLA explicitly.

**Agent Response**:

```
UCLA's application filing period for Fall admission is from October 1 to December 1. They do not offer Early Decision or Early Action.

For admission, UCLA considers the following factors:
*   **Critical:** Essays (Personal Insight Questions), Course Rigor, GPA, Extracurricular Activities, Special Talents/Achievements
*   **Moderate:** Leadership and Involvement, Academic Enrichment Programs, Quality of Senior-Year Program, Academic Performance Relative to Opportunities, Recent Academic Improvement, First-Generation Status
*   **Not Considered:** Demonstrated Interest, Interviews
*   **Not Offered:** Interviews

For the application essays, you'll need to respond to four out of eight Personal Insight Questions (PIQs), with a maximum of 350 words per response.

Additionally, some specific programs, such as those in Music, Arts & Architecture, Nursing, and Theater, Film and Television, may require supplemental applications, auditions, or portfolios.

For the most accurate and detailed information, please visit the official UCLA Admissions website.
```

---

#### ✅ `popular_majors`

**Score**: 1.00 | **Status**: PASSED

**User Query**:
> What are the popular majors at Stanford?

**Judge Reasoning**:
> The agent correctly identifies Stanford and lists several popular majors, providing a helpful and informative response.

**Agent Response**:

```
Here are some of the popular majors at Stanford University:

*   **Computer Science**
*   **Economics**
*   **Human Biology**
*   **Political Science**
*   **Biology**
*   **English**

These majors are found within Stanford's School of Humanities and Sciences and School of Engineering.
```

---
