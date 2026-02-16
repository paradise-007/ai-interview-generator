# 🎯 AI Interview Question Generator
### E2M Solutions – Technical Assessment Submission

A Streamlit-based AI tool that generates **role-specific interview questions**, **difficulty-calibrated content**, and **structured evaluation rubrics** for any job role and experience level — powered by Claude AI.

---

## ✨ Features

| Feature | Status |
|---|---|
| Role-specific technical questions | ✅ |
| Behavioral questions by competency | ✅ |
| Structured 4-criterion evaluation rubric | ✅ |
| Difficulty calibration (Junior / Mid / Senior) | ✅ |
| Individual question regeneration | ✅ |
| Custom skill focus (e.g. "focus on APIs") | ✅ |
| Downloadable interview kit (Markdown) | ✅ |
| Scoring template export | ✅ |
| Interviewer best-practice tips | ✅ |
| Input validation & error handling | ✅ |
| Configurable question count | ✅ |

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/your-username/ai-interview-generator.git
cd ai-interview-generator
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run app.py
```

### 4. Configure your API key
- Open the app in your browser (default: `http://localhost:8501`)
- Enter your **Anthropic API key** in the sidebar (get one free at [console.anthropic.com](https://console.anthropic.com))
- Select a role, level, and click **Generate**

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `streamlit` | ≥ 1.40 | Web UI framework |
| `anthropic` | ≥ 0.40 | Claude LLM API client |

No database, no external services, no vector stores — fully self-contained.

---

## 🏗️ Architecture & Data Flow

```
User Input (Sidebar)
  │
  ▼
Input Validation & Normalization
  │
  ▼
Prompt Builder  ─────────────────────────────────────────────────────────────────────────┐
  │  (role, level, focus, n_tech, n_beh → structured prompt with explicit JSON schema)   │
  ▼                                                                                       │
Anthropic API (Claude claude-opus-4-5-20251101)                                          │
  │                                                                                       │
  ▼                                                                                       │
JSON Extractor (strip markdown fences → parse → validate)                                │
  │                                                                                       │
  ▼                                                                                       │
Session State (st.session_state.kit)   ◄──── Regenerate Single Question ◄────────────────┘
  │
  ├── Tab 1: Technical Questions  (with per-question regenerate button)
  ├── Tab 2: Behavioral Questions (with per-question regenerate button)
  ├── Tab 3: Evaluation Rubric    (+ scoring template)
  ├── Tab 4: Interviewer Tips
  └── Download Button (Markdown export)
```

---

## 🧠 Prompt Design Strategy

### System Prompt
The system prompt establishes Claude as an **expert technical recruiter**, enforces **JSON-only output**, and emphasizes role specificity and avoidance of generic questions.

### Generation Prompt
The generation prompt:
1. Provides explicit **JSON schema** with all required fields
2. Embeds **difficulty calibration guidance** per level in the prompt itself
3. Uses a **focus clause** to narrow question themes when specified
4. Specifies exact **question counts** so the model produces predictable output

### Calibration Logic
```
Junior   → fundamentals, core concepts, basic debugging, simple problem solving
Mid-Level → applied knowledge, trade-offs, debugging real scenarios, collaboration
Senior   → system design, architecture, scalability, mentorship, strategic thinking
```

This guidance is injected directly into the prompt — no post-processing filtering needed.

---

## 📐 Output Schema

```json
{
  "role": "string",
  "level": "Junior | Mid-Level | Senior",
  "technical_questions": [
    {
      "id": "int",
      "question": "string",
      "rationale": "string",
      "expected_topics": ["string"],
      "difficulty": "Easy | Medium | Hard"
    }
  ],
  "behavioral_questions": [
    {
      "id": "int",
      "question": "string",
      "competency": "Communication | Ownership | Collaboration | ...",
      "rationale": "string"
    }
  ],
  "evaluation_rubric": [
    {
      "criterion": "string",
      "weight": "string",
      "strong": "string",
      "average": "string",
      "weak": "string",
      "scoring_tip": "string"
    }
  ],
  "interview_tips": ["string"]
}
```

---

## 🛡️ Error Handling

| Scenario | Handling |
|---|---|
| Empty / short role input | Client-side validation, clear error message |
| Invalid API key | `anthropic.AuthenticationError` → user-facing message |
| Rate limit | `anthropic.RateLimitError` → retry guidance |
| Malformed JSON | Regex-based JSON extractor with fallback, then `json.JSONDecodeError` catch |
| Network / timeout | Generic exception catch with retry guidance |
| Regeneration failure | Per-button error display, does not crash session |

---

## ⚠️ Known Limitations

1. **No streaming** — responses appear all at once after ~10–15 seconds
2. **Single-session only** — generated kits are stored in `st.session_state` and cleared on page refresh
3. **API cost** — each generation uses ~1,500–2,000 tokens; regeneration uses ~300 tokens
4. **JSON reliability** — very rarely, Claude may produce slightly malformed JSON; the extractor handles most cases but extreme failures will show an error
5. **No PDF export** — Markdown export is provided; PDF conversion requires additional dependencies

---

## 🔮 Future Improvements

- PDF download using `reportlab` or `weasyprint`
- Multiple roles in a single session (comparison mode)
- Candidate scoring form alongside the rubric
- Persistent storage with SQLite for saving past kits
- Custom rubric criteria
- Streaming responses for faster perceived performance
- Shareable kit links (via Streamlit Cloud + database)

---

## 📁 File Structure

```
ai-interview-generator/
├── app.py              ← Main Streamlit application (UI + LLM logic)
├── requirements.txt    ← Python dependencies
└── README.md           ← This file
```

---

*Built with ❤️ as part of the E2M Solutions Technical Assessment*
