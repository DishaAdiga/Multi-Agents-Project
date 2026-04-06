"""
Streamlit App
Rare Disease Diagnostic Assistant UI
"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Rare Disease Diagnostic Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
/* FORCE ALL TEXT COLORS */
html, body, [class*="css"], p, span, div, label {
    color: #e0e6f0 !important;
}

/* Fix headings */
h1, h2, h3, h4, h5, h6 {
    color: #e0e6f0 !important;
}

/* Fix markdown text */
.stMarkdown, .stText {
    color: #e0e6f0 !important;
}

/* Fix sidebar text */
section[data-testid="stSidebar"] * {
    color: #e0e6f0 !important;
}

/* Fix input labels */
label {
    color: #9fb3c8 !important;
}
            
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* dark clinical background */
.stApp {
    background-color: #0a0e1a;
    color: #e0e6f0;
}
code {
    background-color: #1e293b !important;
    color: #38bdf8 !important;
    padding: 3px 8px !important;
    border-radius: 6px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.8rem !important;
}
/* sidebar */
section[data-testid="stSidebar"] {
    background-color: #0f1424;
    border-right: 1px solid #1e2d4a;
}

/* main header */
.main-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2rem;
    font-weight: 600;
    color: #4fc3f7;
    letter-spacing: -0.5px;
    margin-bottom: 0;
}
.main-subtitle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    color: #546e8a;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 2rem;
}

/* agent status cards */
.agent-card {
    background: #0f1829;
    border: 1px solid #1e2d4a;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.5rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
}
.agent-card.running  { border-left: 3px solid #f59e0b; }
.agent-card.done     { border-left: 3px solid #10b981; }
.agent-card.error    { border-left: 3px solid #ef4444; }
.agent-card.waiting  { border-left: 3px solid #374151; }

/* confidence badges */
.badge-high   { background:#064e3b; color:#6ee7b7; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-medium { background:#78350f; color:#fcd34d; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-low    { background:#1f2937; color:#9ca3af; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }

/* diagnosis cards */
.dx-card {
    background: #0f1829;
    border: 1px solid #1e2d4a;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.dx-card h3 {
    font-family: 'IBM Plex Mono', monospace;
    color: #4fc3f7;
    font-size: 1rem;
    margin: 0 0 0.5rem 0;
}
.dx-card .orpha {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: #546e8a;
}

/* text area and inputs */
.stTextArea textarea {
    background-color: #0f1829 !important;
    color: #e0e6f0 !important;
    border: 1px solid #1e2d4a !important;
    border-radius: 8px !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}
.stButton > button {
    background: #1a3a5c;
    color: #4fc3f7;
    border: 1px solid #4fc3f7;
    border-radius: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 0.6rem 2rem;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: #4fc3f7;
    color: #0a0e1a;
}

/* disclaimer box */
.disclaimer {
    background: #1a0a0a;
    border: 1px solid #7f1d1d;
    border-radius: 8px;
    padding: 1rem;
    font-size: 0.8rem;
    color: #fca5a5;
    font-family: 'IBM Plex Mono', monospace;
    margin-top: 2rem;
}

/* section headers */
.section-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #546e8a;
    border-bottom: 1px solid #1e2d4a;
    padding-bottom: 0.5rem;
    margin: 1.5rem 0 1rem 0;
}

/* raw answer expanders */
.stExpander {
    background: #0f1829 !important;
    border: 1px solid #1e2d4a !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

def _render_synthesis(synthesis: str):
    """
    Render the synthesis text. Tries to parse ranked candidates,
    falls back to plain markdown if parsing fails.
    """
    import re

    # check if it follows our expected format
    if "RANKED DIFFERENTIAL DIAGNOSIS" in synthesis:
        sections = synthesis.split("CLINICAL SUMMARY")
        dx_section = sections[0]
        summary_section = sections[1] if len(sections) > 1 else ""

        # extract individual candidates (numbered 1. 2. 3. etc.)
        candidates = re.split(r'\n(?=\d+\.)', dx_section)
        candidates = [c.strip() for c in candidates if re.match(r'^\d+\.', c.strip())]

        for candidate in candidates:
            # extract confidence
            conf_match = re.search(r'Confidence:\s*(High|Medium|Low)', candidate, re.IGNORECASE)
            confidence = conf_match.group(1) if conf_match else "Unknown"
            badge_class = f"badge-{confidence.lower()}" if confidence in ["High","Medium","Low"] else "badge-low"

            # extract disease name + orpha
            first_line = candidate.split('\n')[0]
            name_match = re.match(r'\d+\.\s+(.+?)\s+—', first_line)
            disease_name = name_match.group(1) if name_match else first_line

            orpha_match = re.search(r'OrphaCode:\s*(\w+)', first_line)
            orpha = f"OrphaCode: {orpha_match.group(1)}" if orpha_match else ""

            st.markdown(
                f'<div class="dx-card">'
                f'<h3>{disease_name} &nbsp; <span class="{badge_class}">{confidence} Confidence</span></h3>'
                f'<div class="orpha">{orpha}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            # show full candidate text in expander
            with st.expander("View evidence & next steps"):
                st.markdown(candidate)

        # clinical summary
        if summary_section:
            summary_text = summary_section.split("DISCLAIMER")[0].strip()
            st.markdown('<div class="section-header">Clinical Summary</div>', unsafe_allow_html=True)
            st.info(summary_text)

    else:
        # fallback — just render as markdown
        st.markdown(synthesis)


# session state init
if "history"      not in st.session_state: st.session_state.history      = []
if "orchestrator" not in st.session_state: st.session_state.orchestrator = None
if "running"      not in st.session_state: st.session_state.running      = False


# lazy orchestrator init
@st.cache_resource
def get_orchestrator():
    from orchestrator.orchestrator import Orchestrator
    return Orchestrator(verbose=False)


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("###  RareDx Assistant")
    st.markdown("---")
    st.markdown("**Knowledge Base**")
    st.markdown("-  11,456 Orphanet diseases")
    st.markdown("-  1,171 PubMed case reports")
    st.markdown("-  ClinVar genetic variants")
    st.markdown("-  35 lab test panels")
    st.markdown("---")
    st.markdown("**Active Agents**")
    st.markdown("- Symptom Analyst")
    st.markdown("- Case Study Analyst")
    st.markdown("- Genetics Specialist")
    st.markdown("- Lab Interpreter")
    st.markdown("---")
    st.markdown("**Model**")
    st.markdown("`llama-3.3-70b` via Groq")
    st.markdown("**Embeddings**")
    st.markdown("`all-MiniLM-L6-v2`")

    if st.session_state.history:
        st.markdown("---")
        st.markdown("**Query History**")
        for i, h in enumerate(reversed(st.session_state.history[-5:])):
            st.markdown(f"`{i+1}.` {h['query'][:40]}...")


#  main header
st.markdown('<div class="main-title">🧬 Rare Disease Diagnostic Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Multi-Agent RAG System · Powered by Llama 3.3 · Groq</div>', unsafe_allow_html=True)


# input form
st.markdown('<div class="section-header">Patient Presentation</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

with col1:
    query = st.text_area(
        label="Clinical Query",
        placeholder=(
            "Describe the patient's presentation...\n\n"
            "Example: A 12-year-old boy with progressive proximal muscle weakness, "
            "difficulty climbing stairs, waddling gait, calf pseudohypertrophy, "
            "and elevated CK at 12,000 U/L. No family history of muscle disease. "
            "EMG shows myopathic pattern."
        ),
        height=160,
        label_visibility="collapsed",
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("▶ RUN ANALYSIS", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    example_btn = st.button("Load Example", use_container_width=True)

if example_btn:
    st.session_state["example"] = (
        "A 38-year-old woman with 2-year history of progressive proximal muscle weakness, "
        "dyspnoea on exertion, and difficulty rising from a chair. CK 3,200 U/L, "
        "LDH elevated. EMG myopathic. No family history. "
        "Acid alpha-glucosidase activity low on dried blood spot."
    )
    st.rerun()

if "example" in st.session_state:
    query = st.session_state.pop("example")
    st.rerun()


# run analysis
if run_btn and query.strip():

    orchestrator = get_orchestrator()

    # agent status display
    st.markdown('<div class="section-header">Agent Status</div>', unsafe_allow_html=True)

    agent_cols = st.columns(4)
    agent_names = [
    ("Symptom",    "symptom"),
    ("Case Study", "case_study"),
    ("Genetics",   "genetics"),
    ("Lab",        "lab"),
]
    status_slots = {}
    for col, (label, key) in zip(agent_cols, agent_names):
        with col:
            status_slots[key] = st.empty()
            status_slots[key].markdown(
                f'<div class="agent-card running"><b>{label}</b><br>'
                f'<span style="color:#f59e0b">⟳ Running...</span></div>',
                unsafe_allow_html=True,
            )

    synthesis_slot = st.empty()
    synthesis_slot.info("⏳ Waiting for all agents to complete...")

    #run orchestrator
    with st.spinner(""):
        report = orchestrator.run(query)

    #update agent status cards
    agent_results = {
        "symptom":    report.symptom_result,
        "case_study": report.case_result,
        "genetics":   report.genetics_result,
        "lab":        report.lab_result,
    }
    for (label, key) in agent_names:
        result = agent_results[key]
        if result and not result.error:
            tools_str = ", ".join(result.tools_used) if result.tools_used else "none"
            status_slots[key].markdown(
                f'<span style="color:#10b981">✓ Done</span> · '
                f'<span style="color:#546e8a;font-size:0.75rem">{result.rounds} round(s) · {tools_str}</span></div>',
                unsafe_allow_html=True,
            )
        else:
            err = result.error if result else "unknown"
            status_slots[key].markdown(
                f'<span style="color:#ef4444">✗ Error: {err[:40]}</span></div>',
                unsafe_allow_html=True,
            )

    synthesis_slot.empty()

    #synthesis report
    st.markdown('<div class="section-header">Differential Diagnosis Report</div>', unsafe_allow_html=True)

    if report.synthesis:
        # parse and render synthesis as styled cards
        _render_synthesis(report.synthesis)
    else:
        st.error("Synthesis failed. See raw agent outputs below.")

    # raw agent outputs (collapsed)
    st.markdown('<div class="section-header">Raw Agent Outputs</div>', unsafe_allow_html=True)

    for (label, key) in agent_names:
        result = agent_results[key]
        with st.expander(f"{label} Agent — full output"):
            if result and result.answer:
                st.markdown(result.answer)
            elif result and result.error:
                st.error(result.error)
            else:
                st.warning("No output.")

    # save to history
    st.session_state.history.append({
        "query":     query,
        "synthesis": report.synthesis,
    })

    #  disclaimer 
    st.markdown(
        '<div class="disclaimer">⚠ MEDICAL DISCLAIMER — This tool is for clinical decision support only. '
        'All AI-generated findings must be reviewed and verified by a qualified clinician. '
        'Do not make diagnostic or treatment decisions based solely on this output.</div>',
        unsafe_allow_html=True,
    )
elif run_btn and not query.strip():
    st.warning("Please enter a clinical query before running analysis.")

#  synthesis renderer
def _render_synthesis(synthesis: str):
    """
    Render the synthesis text. Tries to parse ranked candidates,
    falls back to plain markdown if parsing fails.
    """
    import re
 
    # check if it follows our expected format
    if "RANKED DIFFERENTIAL DIAGNOSIS" in synthesis:
        sections = synthesis.split("CLINICAL SUMMARY")
        dx_section = sections[0]
        summary_section = sections[1] if len(sections) > 1 else ""
 
        # extract individual candidates (numbered 1. 2. 3. etc.)
        candidates = re.split(r'\n(?=\d+\.)', dx_section)
        candidates = [c.strip() for c in candidates if re.match(r'^\d+\.', c.strip())]
 
        for candidate in candidates:
            # extract confidence
            conf_match = re.search(r'Confidence:\s*(High|Medium|Low)', candidate, re.IGNORECASE)
            confidence = conf_match.group(1) if conf_match else "Unknown"
            badge_class = f"badge-{confidence.lower()}" if confidence in ["High","Medium","Low"] else "badge-low"
 
            # extract disease name + orpha
            first_line = candidate.split('\n')[0]
            name_match = re.match(r'\d+\.\s+(.+?)\s+—', first_line)
            disease_name = name_match.group(1) if name_match else first_line
 
            orpha_match = re.search(r'OrphaCode:\s*(\w+)', first_line)
            orpha = f"OrphaCode: {orpha_match.group(1)}" if orpha_match else ""
 
            st.markdown(
                f'<div class="dx-card">'
                f'<h3>{disease_name} &nbsp; <span class="{badge_class}">{confidence} Confidence</span></h3>'
                f'<div class="orpha">{orpha}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            # show full candidate text in expander
            with st.expander("View evidence & next steps"):
                st.markdown(candidate)
 
        # clinical summary
        if summary_section:
            summary_text = summary_section.split("DISCLAIMER")[0].strip()
            st.markdown('<div class="section-header">Clinical Summary</div>', unsafe_allow_html=True)
            st.info(summary_text)
 
    else:
        # fallback — just render as markdown
        st.markdown(synthesis)