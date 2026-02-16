import streamlit as st
import google.generativeai as genai
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
    .stApp { background-color: #0f1117; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1d2e 0%, #12151f 100%);
        border-right: 1px solid #2d3147;
    }
    .question-card {
        background: linear-gradient(135deg, #1e2235 0%, #252840 100%);
        border: 1px solid #3a3f5c;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 14px;
        transition: all 0.2s ease;
    }
    .question-card:hover { border-color: #6366f1; box-shadow: 0 0 16px rgba(99,102,241,0.15); }
    .question-num { font-size: 11px; font-weight: 700; color: #6366f1; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px; }
    .question-text { font-size: 15px; color: #e2e8f0; line-height: 1.6; }
    .difficulty-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; margin-top: 8px; }
    .badge-junior  { background:#0d3b1e; color:#34d399; border:1px solid #059669; }
    .badge-mid     { background:#1c2f5e; color:#818cf8; border:1px solid #4f46e5; }
    .badge-senior  { background:#3b1a3b; color:#f0abfc; border:1px solid #a855f7; }
    .rubric-table { width:100%; border-collapse:collapse; margin-top:10px; }
    .rubric-table th { background:#252840; color:#a5b4fc; font-size:12px; text-transform:uppercase; letter-spacing:1px; padding:10px 14px; text-align:left; border-bottom:2px solid #3a3f5c; }
    .rubric-table td { padding:10px 14px; font-size:13px; color:#cbd5e1; vertical-align:top; border-bottom:1px solid #2a2d42; }
    .rubric-table tr:hover td { background:#1e2235; }
    .strong-cell { color:#34d399; }
    .average-cell { color:#fbbf24; }
    .weak-cell { color:#f87171; }
    .stat-chip { display:inline-block; background:#1e2235; border:1px solid #3a3f5c; border-radius:8px; padding:8px 16px; margin:4px; text-align:center; }
    .stat-chip .label { font-size:11px; color:#94a3b8; }
    .stat-chip .value { font-size:18px; font-weight:700; color:#818cf8; }
    .stTabs [data-baseweb="tab-list"] { background:#1a1d2e; border-radius:10px; padding:4px; }
    .stTabs [data-baseweb="tab"] { color:#94a3b8; border-radius:8px; }
    .stTabs [aria-selected="true"] { background:#4f46e5 !important; color:white !important; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg,#4f46e5,#7c3aed);
        color: white; border: none; border-radius: 10px;
        font-weight: 700; font-size: 15px; width: 100%;
    }
    #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"] { background:rgba(0,0,0,0); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
EXAMPLE_ROLES = [
    "Backend Engineer", "Frontend Engineer", "Full Stack Engineer",
    "Data Scientist", "ML Engineer", "DevOps Engineer",
    "Product Manager", "SEO Specialist", "Mobile Developer (iOS/Android)",
    "Security Engineer", "QA Engineer", "Cloud Architect",
]

LEVEL_COLORS = {"Junior": "badge-junior", "Mid-Level": "badge-mid", "Senior": "badge-senior"}

# ─────────────────────────────────────────────
# Session State Init
# ─────────────────────────────────────────────
if "kit" not in st.session_state:
    st.session_state.kit = None
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def extract_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Could not parse AI response as JSON. Please retry.")

def call_gemini(prompt: str) -> str:
    genai.configure(api_key=st.session_state.api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=(
            "You are an expert technical recruiter and engineering interview specialist. "
            "Generate highly structured, role-specific interview content. "
            "Always respond with valid, parseable JSON only — no prose, no markdown fences, no preamble. "
            "Every question must be directly relevant to the specified role and experience level."
        )
    )
    response = model.generate_content(prompt)
    return response.text

def validate_inputs(role: str, level: str) -> tuple:
    if not role.strip():
        return False, "Please enter a job role."
    if len(role.strip()) < 3:
        return False, "Job role must be at least 3 characters."
    if level not in ["Junior", "Mid-Level", "Senior"]:
        return False, "Please select a valid experience level."
    return True, ""

def normalize_role(role: str) -> str:
    return role.strip().title()

def build_prompt(role: str, level: str, focus: str, n_tech: int, n_beh: int) -> str:
    level_guidance = {
        "Junior":    "Focus on fundamentals, core concepts, basic debugging, and simple problem solving.",
        "Mid-Level": "Focus on applied knowledge, trade-offs, debugging real scenarios, and collaboration.",
        "Senior":    "Focus on system design, architecture decisions, scalability, mentorship, and strategic thinking.",
    }[level]

    focus_clause = f" with special focus on: {focus}." if focus.strip() else "."

    return f"""Generate a complete interview kit for:
- Role: {role}
- Experience Level: {level}
- Special Focus: {focus if focus.strip() else "None"}{focus_clause}
- Calibration: {level_guidance}

Return ONLY this exact JSON structure (no extra text, no markdown, no backticks):

{{
  "role": "{role}",
  "level": "{level}",
  "technical_questions": [
    {{
      "id": 1,
      "question": "...",
      "rationale": "Why this question matters for the role and level",
      "expected_topics": ["topic1", "topic2"],
      "difficulty": "Easy"
    }}
  ],
  "behavioral_questions": [
    {{
      "id": 1,
      "question": "...",
      "competency": "Communication",
      "rationale": "Why this competency matters at this level"
    }}
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
      "strong": "...", "average": "...", "weak": "...", "scoring_tip": "..."
    }},
    {{
      "criterion": "Problem-Solving Approach",
      "weight": "25%",
      "strong": "...", "average": "...", "weak": "...", "scoring_tip": "..."
    }},
    {{
      "criterion": "Communication Clarity",
      "weight": "20%",
      "strong": "...", "average": "...", "weak": "...", "scoring_tip": "..."
    }}
  ],
  "interview_tips": [
    "Tip 1", "Tip 2", "Tip 3"
  ]
}}

Generate exactly {n_tech} technical questions and {n_beh} behavioral questions."""

def build_regen_prompt(role, level, q_type, old_question, focus):
    return f"""Regenerate a single {q_type} interview question for:
- Role: {role}
- Level: {level}
- Focus: {focus if focus else "None"}
- Old question (must be different): {old_question}

Return ONLY a single JSON object, no extra text:
{"{'id': 1, 'question': '...', 'rationale': '...', 'expected_topics': ['...'], 'difficulty': 'Easy|Medium|Hard'}" if q_type == "technical" else "{'id': 1, 'question': '...', 'competency': '...', 'rationale': '...'}"}"""

def build_markdown_export(kit: dict) -> str:
    ts = datetime.now().strftime("%B %d, %Y at %H:%M")
    lines = [
        f"# Interview Kit: {kit['role']} ({kit['level']})",
        f"*Generated on {ts}*\n", "---\n",
        "## 🔧 Technical Questions\n",
    ]
    for i, q in enumerate(kit.get("technical_questions", []), 1):
        lines += [
            f"### Q{i}. {q['question']}",
            f"- **Difficulty:** {q.get('difficulty','—')}",
            f"- **Rationale:** {q.get('rationale','—')}",
            f"- **Expected Topics:** {', '.join(q.get('expected_topics', []))}\n",
        ]
    lines += ["---\n", "## 💬 Behavioral Questions\n"]
    for i, q in enumerate(kit.get("behavioral_questions", []), 1):
        lines += [
            f"### Q{i}. {q['question']}",
            f"- **Competency:** {q.get('competency','—')}",
            f"- **Rationale:** {q.get('rationale','—')}\n",
        ]
    lines += ["---\n", "## 📊 Evaluation Rubric\n"]
    for r in kit.get("evaluation_rubric", []):
        lines += [
            f"### {r['criterion']} (Weight: {r.get('weight','—')})",
            f"- ✅ **Strong:** {r['strong']}",
            f"- 🟡 **Average:** {r['average']}",
            f"- ❌ **Weak:** {r['weak']}",
            f"- 💡 **Tip:** {r.get('scoring_tip','—')}\n",
        ]
    if kit.get("interview_tips"):
        lines += ["---\n", "## 💡 Interviewer Tips\n"]
        for tip in kit["interview_tips"]:
            lines.append(f"- {tip}")
    return "\n".join(lines)

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 Interview Generator")
    st.markdown("*Powered by Google Gemini (Free)*")
    st.markdown("---")

    # API Key input
    st.markdown("### 🔑 Gemini API Key")
    st.markdown(
        "Get your **free** key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)",
        unsafe_allow_html=True
    )
    api_key_input = st.text_input(
        "Paste your Gemini API Key",
        type="password",
        value=st.session_state.api_key,
        placeholder="AIzaSy...",
    )
    if api_key_input:
        st.session_state.api_key = api_key_input

    st.markdown("---")
    st.markdown("### 📋 Role Configuration")

    example_choice = st.selectbox("Quick-fill example role", ["(type your own)"] + EXAMPLE_ROLES)
    default_role = "" if example_choice == "(type your own)" else example_choice

    role_input = st.text_input(
        "Job Role *",
        value=default_role,
        placeholder="e.g. Backend Engineer",
    )

    level_input = st.radio(
        "Experience Level *",
        ["Junior", "Mid-Level", "Senior"],
        horizontal=False,
    )

    focus_input = st.text_input(
        "⚡ Custom Skill Focus (optional)",
        placeholder="e.g. APIs, Docker, Leadership",
    )

    st.markdown("### ⚙️ Output Settings")
    n_tech = st.slider("Technical questions", 3, 10, 6)
    n_beh  = st.slider("Behavioral questions", 2, 8, 4)

    st.markdown("---")
    generate_btn = st.button(
        "✨ Generate Interview Kit",
        type="primary",
        disabled=not st.session_state.api_key
    )
    if not st.session_state.api_key:
        st.warning("↑ Enter your free Gemini API key above to begin.")

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("# 🎯 AI Interview Question Generator")
st.markdown("*Role-specific questions · Difficulty calibration · Structured evaluation rubrics*")
st.markdown("---")

# ─────────────────────────────────────────────
# Generation
# ─────────────────────────────────────────────
if generate_btn:
    valid, err = validate_inputs(role_input, level_input)
    if not valid:
        st.error(f"⚠️ {err}")
    else:
        normalized = normalize_role(role_input)
        with st.spinner(f"Generating interview kit for **{normalized}** ({level_input})…"):
            try:
                prompt = build_prompt(normalized, level_input, focus_input, n_tech, n_beh)
                raw = call_gemini(prompt)
                kit = extract_json(raw)
                kit["_focus"] = focus_input
                st.session_state.kit = kit
                st.success("✅ Interview kit generated successfully!")
            except Exception as e:
                err_msg = str(e)
                if "API_KEY_INVALID" in err_msg or "invalid" in err_msg.lower():
                    st.error("❌ Invalid Gemini API key. Please check and try again.")
                elif "quota" in err_msg.lower():
                    st.error("❌ Free quota exceeded. Wait a minute and retry.")
                else:
                    st.error(f"❌ {err_msg}")

# ─────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────
if st.session_state.kit:
    kit = st.session_state.kit

    # Stats bar
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.markdown(f"""<div class="stat-chip">
            <div class="label">ROLE</div>
            <div class="value" style="font-size:13px;margin-top:4px">{kit.get('role','—')}</div>
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

    # Download button
    md_export = build_markdown_export(kit)
    filename = f"interview_kit_{kit.get('role','role').replace(' ','_')}_{kit.get('level','')}.md"
    st.download_button(
        label="⬇️ Download Interview Kit (Markdown)",
        data=md_export,
        file_name=filename,
        mime="text/markdown",
    )

    st.markdown("---")

    tab_tech, tab_beh, tab_rubric, tab_tips = st.tabs([
        "🔧 Technical Questions",
        "💬 Behavioral Questions",
        "📊 Evaluation Rubric",
        "💡 Interviewer Tips",
    ])

    # ── Technical Questions ──────────────────
    with tab_tech:
        st.markdown("### 🔧 Technical Questions")
        for idx, q in enumerate(kit.get("technical_questions", [])):
            diff = q.get("difficulty", "Medium")
            badge_cls = {"Easy":"badge-junior","Medium":"badge-mid","Hard":"badge-senior"}.get(diff,"badge-mid")
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

                if st.button("🔄 Regenerate this question", key=f"regen_tech_{idx}"):
                    with st.spinner("Regenerating…"):
                        try:
                            raw = call_gemini(build_regen_prompt(
                                kit["role"], kit["level"], "technical",
                                q["question"], kit.get("_focus","")
                            ))
                            new_q = extract_json(raw)
                            new_q["id"] = q.get("id", idx+1)
                            st.session_state.kit["technical_questions"][idx] = new_q
                            st.rerun()
                        except Exception as e:
                            st.error(f"Regeneration failed: {e}")

    # ── Behavioral Questions ─────────────────
    with tab_beh:
        st.markdown("### 💬 Behavioral Questions")
        COMP_COLORS = {
            "Communication":"#4ade80","Ownership":"#fb923c",
            "Collaboration":"#38bdf8","Conflict Resolution":"#f472b6",
            "Leadership":"#a78bfa","Growth Mindset":"#fbbf24",
        }
        for idx, q in enumerate(kit.get("behavioral_questions", [])):
            comp = q.get("competency","General")
            comp_color = COMP_COLORS.get(comp,"#94a3b8")
            with st.expander(f"Q{idx+1}. {q['question'][:90]}{'…' if len(q['question'])>90 else ''}"):
                st.markdown(f"""<div class="question-card">
                    <div class="question-num">Behavioral Question {idx+1}</div>
                    <div class="question-text">{q['question']}</div>
                    <span class="difficulty-badge" style="background:#1a1a2e;color:{comp_color};
                          border:1px solid {comp_color};">{comp}</span>
                </div>""", unsafe_allow_html=True)
                st.markdown(f"**🎯 Competency Rationale:** {q.get('rationale','—')}")

                if st.button("🔄 Regenerate this question", key=f"regen_beh_{idx}"):
                    with st.spinner("Regenerating…"):
                        try:
                            raw = call_gemini(build_regen_prompt(
                                kit["role"], kit["level"], "behavioral",
                                q["question"], kit.get("_focus","")
                            ))
                            new_q = extract_json(raw)
                            new_q["id"] = q.get("id", idx+1)
                            st.session_state.kit["behavioral_questions"][idx] = new_q
                            st.rerun()
                        except Exception as e:
                            st.error(f"Regeneration failed: {e}")

    # ── Evaluation Rubric ────────────────────
    with tab_rubric:
        st.markdown("### 📊 Evaluation Rubric")
        st.markdown("*Use this rubric to score candidate responses consistently.*")
        for r in kit.get("evaluation_rubric", []):
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
                    <thead><tr>
                        <th style="width:33%">✅ Strong Response</th>
                        <th style="width:33%">🟡 Average Response</th>
                        <th style="width:33%">❌ Weak Response</th>
                    </tr></thead>
                    <tbody><tr>
                        <td class="strong-cell">{r.get('strong','—')}</td>
                        <td class="average-cell">{r.get('average','—')}</td>
                        <td class="weak-cell">{r.get('weak','—')}</td>
                    </tr></tbody>
                </table>
                <div style="margin-top:12px;padding:8px 14px;background:#252840;border-radius:8px;
                            border-left:3px solid #6366f1;">
                    <span style="font-size:12px;color:#94a3b8;">💡 Tip: </span>
                    <span style="font-size:13px;color:#cbd5e1;">{r.get('scoring_tip','—')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Scoring template
        st.markdown("#### 📝 Quick Scoring Template")
        score_md = f"## Candidate Evaluation — {kit.get('role','')} ({kit.get('level','')})\n\n"
        score_md += "| Criterion | Weight | Score (1–5) | Notes |\n|---|---|---|---|\n"
        for r in kit.get("evaluation_rubric", []):
            score_md += f"| {r['criterion']} | {r.get('weight','—')} | _ | |\n"
        score_md += "\n**Recommendation:** ☐ Strong Hire  ☐ Hire  ☐ No Hire  ☐ Strong No Hire\n"
        st.code(score_md, language="markdown")

    # ── Interviewer Tips ─────────────────────
    with tab_tips:
        st.markdown("### 💡 Role-Specific Tips")
        icons = ["💡","📌","⚡","🎯","🔍"]
        for i, tip in enumerate(kit.get("interview_tips", [])):
            st.markdown(f"""<div style="display:flex;gap:14px;align-items:flex-start;
                background:#1e2235;border:1px solid #3a3f5c;border-radius:10px;
                padding:14px 18px;margin-bottom:10px;">
                <span style="font-size:20px;min-width:28px;">{icons[i % len(icons)]}</span>
                <span style="color:#e2e8f0;font-size:14px;line-height:1.6;">{tip}</span>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🧭 General Best Practices")
        practices = [
            ("🕐","Allow 45–60 seconds of silence — candidates need thinking time."),
            ("📝","Take sparse notes — capture key phrases, not full sentences."),
            ("🔄","Use the same question order across candidates for fairness."),
            ("🚫","Avoid leading questions — keep them open-ended."),
            ("🌱","For juniors, probe for learning ability, not just current knowledge."),
            ("🏗️","For seniors, ask what decisions they'd make differently in hindsight."),
        ]
        for icon, text in practices:
            st.markdown(f"""<div style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #2a2d42;">
                <span style="font-size:18px;">{icon}</span>
                <span style="color:#cbd5e1;font-size:13px;">{text}</span>
            </div>""", unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;">
        <div style="font-size:64px;margin-bottom:20px;">🎯</div>
        <h2 style="color:#e2e8f0;margin-bottom:12px;">Ready to generate your interview kit</h2>
        <p style="color:#64748b;font-size:16px;max-width:500px;margin:0 auto;">
            1. Get your <strong style="color:#818cf8;">free Gemini API key</strong> at
            <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color:#6366f1;">
            aistudio.google.com</a><br><br>
            2. Paste it in the sidebar and configure your role<br><br>
            3. Click <strong style="color:#818cf8;">✨ Generate Interview Kit</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)