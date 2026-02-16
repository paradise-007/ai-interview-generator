import streamlit as st
import anthropic
import json
import re
from datetime import datetime

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Interview Question Generator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f1117; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1d2e 0%, #12151f 100%);
        border-right: 1px solid #2d3147;
    }

    /* Cards */
    .question-card {
        background: linear-gradient(135deg, #1e2235 0%, #252840 100%);
        border: 1px solid #3a3f5c;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 14px;
        transition: all 0.2s ease;
    }
    .question-card:hover {
        border-color: #6366f1;
        box-shadow: 0 0 16px rgba(99,102,241,0.15);
    }
    .question-num {
        font-size: 11px;
        font-weight: 700;
        color: #6366f1;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 6px;
    }
    .question-text {
        font-size: 15px;
        color: #e2e8f0;
        line-height: 1.6;
    }
    .difficulty-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        margin-top: 8px;
    }
    .badge-junior  { background:#0d3b1e; color:#34d399; border:1px solid #059669; }
    .badge-mid     { background:#1c2f5e; color:#818cf8; border:1px solid #4f46e5; }
    .badge-senior  { background:#3b1a3b; color:#f0abfc; border:1px solid #a855f7; }

    /* Rubric table */
    .rubric-table { width:100%; border-collapse:collapse; margin-top:10px; }
    .rubric-table th {
        background:#252840;
        color:#a5b4fc;
        font-size:12px;
        text-transform:uppercase;
        letter-spacing:1px;
        padding:10px 14px;
        text-align:left;
        border-bottom:2px solid #3a3f5c;
    }
    .rubric-table td {
        padding:10px 14px;
        font-size:13px;
        color:#cbd5e1;
        vertical-align:top;
        border-bottom:1px solid #2a2d42;
    }
    .rubric-table tr:hover td { background:#1e2235; }
    .strong-cell { color:#34d399; }
    .average-cell { color:#fbbf24; }
    .weak-cell { color:#f87171; }

    /* Section headers */
    .section-header {
        display:flex;
        align-items:center;
        gap:10px;
        padding: 12px 0 6px 0;
        border-bottom: 1px solid #3a3f5c;
        margin-bottom: 20px;
    }
    .section-header h3 {
        margin:0;
        font-size:18px;
        color:#e2e8f0;
    }

    /* Stat chips */
    .stat-chip {
        display:inline-block;
        background:#1e2235;
        border:1px solid #3a3f5c;
        border-radius:8px;
        padding:8px 16px;
        margin:4px;
        text-align:center;
    }
    .stat-chip .label { font-size:11px; color:#94a3b8; }
    .stat-chip .value { font-size:18px; font-weight:700; color:#818cf8; }

    /* Expander */
    .streamlit-expanderHeader { background:#1e2235 !important; }

    /* Download btn */
    .stDownloadButton button {
        background: linear-gradient(135deg,#4f46e5,#7c3aed);
        color:white;
        border:none;
        border-radius:8px;
        font-weight:600;
    }
    .stDownloadButton button:hover { opacity:0.9; }
    
    /* Generate btn */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg,#4f46e5,#7c3aed);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        font-size: 15px;
        padding: 0.6em 2em;
        width: 100%;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background:#1a1d2e; border-radius:10px; padding:4px; }
    .stTabs [data-baseweb="tab"] { color:#94a3b8; border-radius:8px; }
    .stTabs [aria-selected="true"] { background:#4f46e5 !important; color:white !important; }

    /* Hide streamlit branding */
    #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"] { background:rgba(0,0,0,0); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
LEVEL_COLORS = {"Junior": "badge-junior", "Mid-Level": "badge-mid", "Senior": "badge-senior"}

EXAMPLE_ROLES = [
    "Backend Engineer", "Frontend Engineer", "Full Stack Engineer",
    "Data Scientist", "ML Engineer", "DevOps Engineer",
    "Product Manager", "SEO Specialist", "Mobile Developer (iOS/Android)",
    "Security Engineer", "QA Engineer", "Cloud Architect",
]

def get_client() -> anthropic.Anthropic:
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        raise ValueError("Anthropic API key is not configured.")
    return anthropic.Anthropic(api_key=api_key)

def extract_json(raw: str) -> dict:
    """Robustly extract JSON from LLM response (handles markdown fences)."""
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise

def build_system_prompt() -> str:
    return """You are an expert technical recruiter and engineering interview specialist.
Your job is to create highly structured, role-specific interview packages.
Always respond with valid, parseable JSON only — no prose, no markdown, no preamble.
Every question must be directly relevant to the specified role and experience level.
Avoid generic, trivia-based, or recycled interview questions."""

def build_generation_prompt(role: str, level: str, focus: str, n_tech: int, n_beh: int) -> str:
    focus_clause = f" with a special focus on: {focus}." if focus.strip() else "."
    
    level_guidance = {
        "Junior":    "Focus on fundamentals, core concepts, basic debugging, and simple problem solving.",
        "Mid-Level": "Focus on applied knowledge, trade-offs, debugging real scenarios, and collaboration.",
        "Senior":    "Focus on system design, architecture decisions, scalability, mentorship, and strategic thinking.",
    }[level]

    return f"""Generate a complete interview kit for the following:
- Role: {role}
- Experience Level: {level}
- Special Focus: {focus if focus.strip() else "None — cover the most important areas broadly"}{focus_clause}

Calibration guidance: {level_guidance}

Return ONLY this JSON structure (no extra text):

{{
  "role": "{role}",
  "level": "{level}",
  "technical_questions": [
    {{
      "id": 1,
      "question": "...",
      "rationale": "Why this question matters for the role and level",
      "expected_topics": ["topic1", "topic2"],
      "difficulty": "Easy|Medium|Hard"
    }}
    // ... {n_tech} questions total
  ],
  "behavioral_questions": [
    {{
      "id": 1,
      "question": "...",
      "competency": "Communication|Ownership|Collaboration|Conflict Resolution|Leadership|Growth Mindset",
      "rationale": "Why this competency matters at this level"
    }}
    // ... {n_beh} questions total
  ],
  "evaluation_rubric": [
    {{
      "criterion": "Technical Accuracy",
      "weight": "30%",
      "strong": "What a strong answer looks like",
      "average": "What an average answer looks like",
      "weak": "What a weak answer looks like",
      "scoring_tip": "Quick tip for the interviewer"
    }},
    {{
      "criterion": "Depth of Understanding",
      "weight": "25%",
      "strong": "...",
      "average": "...",
      "weak": "...",
      "scoring_tip": "..."
    }},
    {{
      "criterion": "Problem-Solving Approach",
      "weight": "25%",
      "strong": "...",
      "average": "...",
      "weak": "...",
      "scoring_tip": "..."
    }},
    {{
      "criterion": "Communication Clarity",
      "weight": "20%",
      "strong": "...",
      "average": "...",
      "weak": "...",
      "scoring_tip": "..."
    }}
  ],
  "interview_tips": [
    "Role-specific tip 1",
    "Role-specific tip 2",
    "Role-specific tip 3"
  ]
}}"""

def build_regen_prompt(role: str, level: str, q_type: str, old_question: str, focus: str) -> str:
    return f"""Regenerate a single {q_type} interview question for:
- Role: {role}
- Level: {level}
- Focus (if any): {focus if focus.strip() else "None"}
- Old question to replace: {old_question}

The new question must be meaningfully different from the old one.
Return ONLY valid JSON for a single question object matching this shape:

For technical:
{{"id": <keep same id>, "question": "...", "rationale": "...", "expected_topics": ["..."], "difficulty": "Easy|Medium|Hard"}}

For behavioral:
{{"id": <keep same id>, "question": "...", "competency": "...", "rationale": "..."}}"""

def call_llm(prompt: str, max_tokens: int = 4096) -> str:
    client = get_client()
    response = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=max_tokens,
        system=build_system_prompt(),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text

def generate_interview_kit(role: str, level: str, focus: str, n_tech: int, n_beh: int) -> dict:
    prompt = build_generation_prompt(role, level, focus, n_tech, n_beh)
    raw = call_llm(prompt, max_tokens=4096)
    return extract_json(raw)

def regenerate_question(role: str, level: str, q_type: str, old_question: str, focus: str) -> dict:
    prompt = build_regen_prompt(role, level, q_type, old_question, focus)
    raw = call_llm(prompt, max_tokens=512)
    return extract_json(raw)

def normalize_role(role: str) -> str:
    return role.strip().title()

def validate_inputs(role: str, level: str) -> tuple[bool, str]:
    if not role.strip():
        return False, "Please enter a job role."
    if len(role.strip()) < 3:
        return False, "Job role must be at least 3 characters."
    if level not in ["Junior", "Mid-Level", "Senior"]:
        return False, "Please select a valid experience level."
    return True, ""

def build_markdown_export(kit: dict) -> str:
    ts = datetime.now().strftime("%B %d, %Y at %H:%M")
    lines = [
        f"# Interview Kit: {kit['role']} ({kit['level']})",
        f"*Generated on {ts}*\n",
        "---\n",
        "## 🔧 Technical Questions\n",
    ]
    for i, q in enumerate(kit.get("technical_questions", []), 1):
        lines += [
            f"### Q{i}. {q['question']}",
            f"- **Difficulty:** {q.get('difficulty','—')}",
            f"- **Rationale:** {q.get('rationale','—')}",
            f"- **Expected Topics:** {', '.join(q.get('expected_topics', []))}",
            "",
        ]
    lines += ["---\n", "## 💬 Behavioral Questions\n"]
    for i, q in enumerate(kit.get("behavioral_questions", []), 1):
        lines += [
            f"### Q{i}. {q['question']}",
            f"- **Competency:** {q.get('competency','—')}",
            f"- **Rationale:** {q.get('rationale','—')}",
            "",
        ]
    lines += ["---\n", "## 📊 Evaluation Rubric\n"]
    for r in kit.get("evaluation_rubric", []):
        lines += [
            f"### {r['criterion']} (Weight: {r.get('weight','—')})",
            f"- ✅ **Strong:** {r['strong']}",
            f"- 🟡 **Average:** {r['average']}",
            f"- ❌ **Weak:** {r['weak']}",
            f"- 💡 **Tip:** {r.get('scoring_tip','—')}",
            "",
        ]
    if kit.get("interview_tips"):
        lines += ["---\n", "## 💡 Interviewer Tips\n"]
        for tip in kit["interview_tips"]:
            lines.append(f"- {tip}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# Session State Init
# ─────────────────────────────────────────────
if "kit" not in st.session_state:
    st.session_state.kit = None
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "generating" not in st.session_state:
    st.session_state.generating = False

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 Interview Generator")
    st.markdown("*Powered by Claude AI*")
    st.markdown("---")

    # API Key
    api_key_input = st.text_input(
        "🔑 Anthropic API Key",
        type="password",
        value=st.session_state.api_key,
        placeholder="sk-ant-...",
        help="Get your key at console.anthropic.com"
    )
    if api_key_input:
        st.session_state.api_key = api_key_input

    st.markdown("---")
    st.markdown("### 📋 Role Configuration")

    # Role input with examples
    example_choice = st.selectbox("Quick-fill with example role", ["(type your own)"] + EXAMPLE_ROLES)
    default_role = "" if example_choice == "(type your own)" else example_choice

    role_input = st.text_input(
        "Job Role *",
        value=default_role,
        placeholder="e.g. Backend Engineer, SEO Specialist",
        help="Enter the role you are hiring for"
    )

    level_input = st.radio(
        "Experience Level *",
        ["Junior", "Mid-Level", "Senior"],
        horizontal=False,
    )

    focus_input = st.text_input(
        "⚡ Custom Skill Focus (optional)",
        placeholder="e.g. APIs, Kubernetes, Leadership",
        help="Narrow questions to a specific area"
    )

    st.markdown("### ⚙️ Output Settings")
    n_tech = st.slider("Technical questions", 3, 10, 6)
    n_beh  = st.slider("Behavioral questions", 2, 8, 4)

    st.markdown("---")
    generate_btn = st.button("✨ Generate Interview Kit", type="primary", disabled=not st.session_state.api_key)

    if not st.session_state.api_key:
        st.warning("Enter your API key above to enable generation.")

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
col_logo, col_title = st.columns([1, 8])
with col_title:
    st.markdown("# 🎯 AI Interview Question Generator")
    st.markdown("*Role-specific questions · Difficulty calibration · Structured evaluation rubrics*")

st.markdown("---")

# ─────────────────────────────────────────────
# Generation Trigger
# ─────────────────────────────────────────────
if generate_btn:
    valid, err = validate_inputs(role_input, level_input)
    if not valid:
        st.error(f"⚠️ {err}")
    else:
        normalized = normalize_role(role_input)
        with st.spinner(f"Crafting interview kit for **{normalized}** ({level_input})… this takes ~15s"):
            try:
                kit = generate_interview_kit(normalized, level_input, focus_input, n_tech, n_beh)
                kit["_focus"] = focus_input
                st.session_state.kit = kit
                st.success("✅ Interview kit generated successfully!")
            except ValueError as e:
                st.error(f"Configuration error: {e}")
            except anthropic.AuthenticationError:
                st.error("❌ Invalid API key. Please check your Anthropic API key.")
            except anthropic.RateLimitError:
                st.error("❌ Rate limit hit. Please wait a moment and try again.")
            except Exception as e:
                st.error(f"❌ Generation failed: {str(e)}\n\nPlease retry or check your connection.")

# ─────────────────────────────────────────────
# Main Output
# ─────────────────────────────────────────────
if st.session_state.kit:
    kit = st.session_state.kit

    # ── Stats Bar ───────────────────────────
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.markdown(f"""<div class="stat-chip">
            <div class="label">ROLE</div>
            <div class="value" style="font-size:14px;margin-top:4px">{kit.get('role','—')}</div>
        </div>""", unsafe_allow_html=True)
    with r2:
        badge = LEVEL_COLORS.get(kit.get("level",""), "badge-mid")
        st.markdown(f"""<div class="stat-chip">
            <div class="label">LEVEL</div>
            <div class="value"><span class="difficulty-badge {badge}">{kit.get('level','—')}</span></div>
        </div>""", unsafe_allow_html=True)
    with r3:
        st.markdown(f"""<div class="stat-chip">
            <div class="label">TECHNICAL Qs</div>
            <div class="value">{len(kit.get('technical_questions',[]))}</div>
        </div>""", unsafe_allow_html=True)
    with r4:
        st.markdown(f"""<div class="stat-chip">
            <div class="label">BEHAVIORAL Qs</div>
            <div class="value">{len(kit.get('behavioral_questions',[]))}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Download ─────────────────────────────
    md_export = build_markdown_export(kit)
    filename = f"interview_kit_{kit.get('role','role').replace(' ','_')}_{kit.get('level','')}.md"
    st.download_button(
        label="⬇️ Download Interview Kit (Markdown)",
        data=md_export,
        file_name=filename,
        mime="text/markdown",
    )

    st.markdown("---")

    # ── Tabs ─────────────────────────────────
    tab_tech, tab_beh, tab_rubric, tab_tips = st.tabs([
        "🔧 Technical Questions",
        "💬 Behavioral Questions",
        "📊 Evaluation Rubric",
        "💡 Interviewer Tips",
    ])

    # ═══════════════════════════════════════
    # Tab 1 – Technical Questions
    # ═══════════════════════════════════════
    with tab_tech:
        st.markdown("### 🔧 Technical Questions")
        tech_qs = kit.get("technical_questions", [])
        if not tech_qs:
            st.info("No technical questions found. Try regenerating.")
        else:
            for idx, q in enumerate(tech_qs):
                diff = q.get("difficulty", "Medium")
                badge_cls = {"Easy": "badge-junior", "Medium": "badge-mid", "Hard": "badge-senior"}.get(diff, "badge-mid")
                topics_str = " · ".join(q.get("expected_topics", []))

                with st.expander(f"Q{idx+1}. {q['question'][:90]}{'…' if len(q['question'])>90 else ''}"):
                    st.markdown(f"""<div class="question-card">
                        <div class="question-num">Question {idx+1}</div>
                        <div class="question-text">{q['question']}</div>
                        <span class="difficulty-badge {badge_cls}">{diff}</span>
                    </div>""", unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**📌 Rationale:** {q.get('rationale','—')}")
                    with c2:
                        if topics_str:
                            st.markdown(f"**🏷️ Expected Topics:** `{topics_str}`")

                    if st.button(f"🔄 Regenerate this question", key=f"regen_tech_{idx}"):
                        with st.spinner("Regenerating…"):
                            try:
                                new_q = regenerate_question(
                                    kit["role"], kit["level"], "technical",
                                    q["question"], kit.get("_focus","")
                                )
                                new_q["id"] = q.get("id", idx+1)
                                st.session_state.kit["technical_questions"][idx] = new_q
                                st.rerun()
                            except Exception as e:
                                st.error(f"Regeneration failed: {e}")

    # ═══════════════════════════════════════
    # Tab 2 – Behavioral Questions
    # ═══════════════════════════════════════
    with tab_beh:
        st.markdown("### 💬 Behavioral Questions")
        beh_qs = kit.get("behavioral_questions", [])
        if not beh_qs:
            st.info("No behavioral questions found. Try regenerating.")
        else:
            COMP_COLORS = {
                "Communication":       "#4ade80",
                "Ownership":           "#fb923c",
                "Collaboration":       "#38bdf8",
                "Conflict Resolution": "#f472b6",
                "Leadership":          "#a78bfa",
                "Growth Mindset":      "#fbbf24",
            }
            for idx, q in enumerate(beh_qs):
                comp = q.get("competency", "General")
                comp_color = COMP_COLORS.get(comp, "#94a3b8")
                with st.expander(f"Q{idx+1}. {q['question'][:90]}{'…' if len(q['question'])>90 else ''}"):
                    st.markdown(f"""<div class="question-card">
                        <div class="question-num">Behavioral Question {idx+1}</div>
                        <div class="question-text">{q['question']}</div>
                        <span class="difficulty-badge" style="background:#1a1a2e;color:{comp_color};
                              border:1px solid {comp_color};">{comp}</span>
                    </div>""", unsafe_allow_html=True)

                    st.markdown(f"**🎯 Competency Rationale:** {q.get('rationale','—')}")

                    if st.button(f"🔄 Regenerate this question", key=f"regen_beh_{idx}"):
                        with st.spinner("Regenerating…"):
                            try:
                                new_q = regenerate_question(
                                    kit["role"], kit["level"], "behavioral",
                                    q["question"], kit.get("_focus","")
                                )
                                new_q["id"] = q.get("id", idx+1)
                                st.session_state.kit["behavioral_questions"][idx] = new_q
                                st.rerun()
                            except Exception as e:
                                st.error(f"Regeneration failed: {e}")

    # ═══════════════════════════════════════
    # Tab 3 – Evaluation Rubric
    # ═══════════════════════════════════════
    with tab_rubric:
        st.markdown("### 📊 Evaluation Rubric")
        st.markdown("*Use this rubric to score candidate responses consistently across all interviewers.*")
        rubric = kit.get("evaluation_rubric", [])
        if not rubric:
            st.info("No rubric found. Try regenerating.")
        else:
            for r in rubric:
                st.markdown(f"""
                <div style="background:#1e2235;border:1px solid #3a3f5c;border-radius:12px;
                            padding:20px;margin-bottom:16px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;
                                border-bottom:1px solid #3a3f5c;padding-bottom:10px;margin-bottom:14px;">
                        <span style="font-size:16px;font-weight:700;color:#e2e8f0;">{r['criterion']}</span>
                        <span style="background:#252840;border:1px solid #4f46e5;border-radius:20px;
                                     padding:4px 12px;font-size:12px;color:#818cf8;font-weight:600;">
                            Weight: {r.get('weight','—')}
                        </span>
                    </div>
                    <table class="rubric-table">
                        <thead>
                            <tr>
                                <th style="width:33%">✅ Strong Response</th>
                                <th style="width:33%">🟡 Average Response</th>
                                <th style="width:33%">❌ Weak Response</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td class="strong-cell">{r.get('strong','—')}</td>
                                <td class="average-cell">{r.get('average','—')}</td>
                                <td class="weak-cell">{r.get('weak','—')}</td>
                            </tr>
                        </tbody>
                    </table>
                    <div style="margin-top:12px;padding:8px 14px;background:#252840;border-radius:8px;
                                border-left:3px solid #6366f1;">
                        <span style="font-size:12px;color:#94a3b8;">💡 Interviewer Tip: </span>
                        <span style="font-size:13px;color:#cbd5e1;">{r.get('scoring_tip','—')}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Scoring template
            st.markdown("#### 📝 Quick Scoring Template")
            score_template = f"""## Candidate Evaluation — {kit.get('role','')} ({kit.get('level','')})\n\n"""
            score_template += "| Criterion | Weight | Score (1–5) | Notes |\n|---|---|---|---|\n"
            for r in rubric:
                score_template += f"| {r['criterion']} | {r.get('weight','—')} | _ | |\n"
            score_template += "\n**Total Score:** ___  \n**Recommendation:** ☐ Strong Hire  ☐ Hire  ☐ No Hire  ☐ Strong No Hire\n\n**Summary Notes:**\n\n"
            st.code(score_template, language="markdown")

    # ═══════════════════════════════════════
    # Tab 4 – Interviewer Tips
    # ═══════════════════════════════════════
    with tab_tips:
        st.markdown("### 💡 Role-Specific Interviewer Tips")
        tips = kit.get("interview_tips", [])
        if not tips:
            st.info("No tips generated for this kit.")
        else:
            for i, tip in enumerate(tips, 1):
                st.markdown(f"""<div style="display:flex;gap:14px;align-items:flex-start;
                    background:#1e2235;border:1px solid #3a3f5c;border-radius:10px;
                    padding:14px 18px;margin-bottom:10px;">
                    <span style="font-size:20px;min-width:28px;">{'💡' if i==1 else '📌' if i==2 else '⚡'}</span>
                    <span style="color:#e2e8f0;font-size:14px;line-height:1.6;">{tip}</span>
                </div>""", unsafe_allow_html=True)

        # General best practices
        st.markdown("---")
        st.markdown("#### 🧭 General Interview Best Practices")
        practices = [
            ("🕐", "Allow 45–60 seconds of silence after each question — candidates need thinking time."),
            ("📝", "Take sparse but focused notes — capture key phrases, not full sentences."),
            ("🔄", "Use the same questions in the same order across all candidates for fairness."),
            ("🚫", "Avoid leading questions like 'Do you agree that X is better?' — keep them open-ended."),
            ("🌱", "For juniors, probe for learning ability, not just current knowledge."),
            ("🏗️", "For seniors, always ask about decisions they'd make *differently* in hindsight."),
        ]
        for icon, text in practices:
            st.markdown(f"""<div style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #2a2d42;">
                <span style="font-size:18px;">{icon}</span>
                <span style="color:#cbd5e1;font-size:13px;">{text}</span>
            </div>""", unsafe_allow_html=True)

else:
    # ── Empty State ──────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;">
        <div style="font-size:64px;margin-bottom:20px;">🎯</div>
        <h2 style="color:#e2e8f0;margin-bottom:12px;">Ready to generate your interview kit</h2>
        <p style="color:#64748b;font-size:16px;max-width:500px;margin:0 auto;">
            Configure your role and experience level in the sidebar, then click
            <strong style="color:#818cf8;">✨ Generate Interview Kit</strong> to get started.
        </p>
    </div>
    <div style="display:flex;justify-content:center;gap:30px;margin-top:40px;flex-wrap:wrap;">
        <div style="text-align:center;max-width:160px;">
            <div style="font-size:36px;">🔧</div>
            <div style="color:#94a3b8;font-size:13px;margin-top:8px;">Role-specific technical questions calibrated to experience level</div>
        </div>
        <div style="text-align:center;max-width:160px;">
            <div style="font-size:36px;">💬</div>
            <div style="color:#94a3b8;font-size:13px;margin-top:8px;">Behavioral questions targeting key competencies</div>
        </div>
        <div style="text-align:center;max-width:160px;">
            <div style="font-size:36px;">📊</div>
            <div style="color:#94a3b8;font-size:13px;margin-top:8px;">Structured rubrics for consistent, bias-free evaluation</div>
        </div>
        <div style="text-align:center;max-width:160px;">
            <div style="font-size:36px;">⬇️</div>
            <div style="color:#94a3b8;font-size:13px;margin-top:8px;">Download the full kit as Markdown for offline use</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
