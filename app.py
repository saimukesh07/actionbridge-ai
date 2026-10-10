"""
ActionBridge AI - Premium Strategic Planning & Verified Execution Platform
A modern AI SaaS interface providing adaptive diagnostic goal intake, multi-provider
strategic reasoning, controlled sandbox execution, persistent strategy archiving, and independent empirical verification.
"""

import json
from datetime import datetime
from pathlib import Path
import streamlit as st

from config.settings import (
    WORKSPACE_DIR,
    is_gemini_configured,
    is_groq_configured,
    is_ai_configured,
    get_active_ai_provider,
    GEMINI_MODEL,
    GROQ_MODEL
)
from core.schemas import (
    GoalIntake,
    DiagnosticQuestion,
    DiagnosticInterview,
    RiskLevel,
    TaskStatus,
    VerificationStatus,
    TaskPriority
)
from core.gemini_client import GeminiReasoningClient
from tools.registry import execute_tool, TOOL_REGISTRY
from tools.verification import PostConditionVerifier
from ui.styles import CUSTOM_CSS
from ui.formatters import clean_text, format_tool_action, generate_markdown_roadmap
from services.strategy_store import (
    save_strategy_record,
    list_saved_strategies,
    load_strategy_record,
    delete_strategy_record
)

# ==============================================================================
# APPLICATION SETUP & THEME INJECTION
# ==============================================================================
st.set_page_config(
    page_title="ActionBridge AI — Strategy & Execution",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject modern SaaS styling
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialize Session State
if "client" not in st.session_state:
    st.session_state.client = GeminiReasoningClient()
if "intake" not in st.session_state:
    st.session_state.intake = None
if "interview" not in st.session_state:
    st.session_state.interview = None
if "interview_answers" not in st.session_state:
    st.session_state.interview_answers = {}
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "selected_strategy" not in st.session_state:
    st.session_state.selected_strategy = None
if "plan" not in st.session_state:
    st.session_state.plan = None
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "🏠 Home Dashboard"

# Auto-restore most recent saved strategy on cold start
if "auto_restored" not in st.session_state:
    st.session_state.auto_restored = True
    saved = list_saved_strategies()
    if saved and not st.session_state.intake:
        loaded = load_strategy_record(saved[0]["goal_id"])
        if loaded:
            st.session_state.intake, st.session_state.analysis, st.session_state.selected_strategy, st.session_state.plan = loaded

# Navigation definition (History & Settings removed)
NAV_OPTIONS = [
    "🏠 Home Dashboard",
    "🎯 Goal Creation",
    "🧠 Strategy Analysis",
    "📋 Action Plan",
    "🛡️ Execution & Approvals",
    "📊 Progress & Milestones"
]

# Ensure current_page is valid
if st.session_state.current_page not in NAV_OPTIONS:
    st.session_state.current_page = NAV_OPTIONS[0]

# ==============================================================================
# SIDEBAR NAVIGATION, STRATEGY SWITCHER & TELEMETRY
# ==============================================================================
with st.sidebar:
    st.markdown("## 🌉 ActionBridge AI")
    st.caption("Strategy Formulation & Verified Execution")
    st.markdown("---")

    selected_nav = st.radio(
        "Navigation",
        NAV_OPTIONS,
        index=NAV_OPTIONS.index(st.session_state.current_page)
    )
    # Sync navigation state
    if selected_nav != st.session_state.current_page:
        st.session_state.current_page = selected_nav
        st.rerun()

    # Saved Strategies Quick Switcher
    saved_records = list_saved_strategies()
    if saved_records:
        st.markdown("---")
        st.markdown("### 📚 Saved Strategies")
        strat_options = {r["goal_id"]: r["goal_title"] for r in saved_records}
        active_gid = st.session_state.analysis.goal_id if st.session_state.analysis else None
        opt_keys = list(strat_options.keys())
        active_idx = opt_keys.index(active_gid) if active_gid in opt_keys else 0

        picked_gid = st.selectbox(
            "Switch Strategy:",
            opt_keys,
            index=active_idx,
            format_func=lambda gid: f"{strat_options[gid][:26]}..." if len(strat_options[gid]) > 26 else strat_options[gid],
            key="sb_strat_picker"
        )
        if active_gid != picked_gid:
            loaded_rec = load_strategy_record(picked_gid)
            if loaded_rec:
                st.session_state.intake, st.session_state.analysis, st.session_state.selected_strategy, st.session_state.plan = loaded_rec
                st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Engine Telemetry")
    active_prov = get_active_ai_provider()
    if active_prov == "gemini":
        st.success(f"🟢 Gemini Live ({GEMINI_MODEL})")
    elif active_prov == "groq":
        st.success(f"🟢 Groq Live ({GROQ_MODEL})")
    else:
        st.info("🟡 Local Demo Mode (Deterministic)")
    st.caption(f"Sandbox: `{WORKSPACE_DIR.name}/`")

    st.markdown("---")
    if st.button("🔄 Reset Active Session", use_container_width=True):
        st.session_state.intake = None
        st.session_state.interview = None
        st.session_state.interview_answers = {}
        st.session_state.analysis = None
        st.session_state.selected_strategy = None
        st.session_state.plan = None
        st.session_state.audit_log = []
        st.session_state.current_page = "🏠 Home Dashboard"
        st.rerun()

# Convenience shortcut for current view
current_page = st.session_state.current_page

# ==============================================================================
# SECTION A: HOME DASHBOARD
# ==============================================================================
if current_page == "🏠 Home Dashboard":
    st.markdown(
        """
        <div class="ab-hero-card">
            <h2 style="margin: 0 0 10px 0; color: #1E293B;">Welcome to ActionBridge AI 🌉</h2>
            <p style="font-size: 1.05rem; line-height: 1.6; color: #334155; margin: 0;">
                Bridge the gap between ambitious intent and verifiable execution. ActionBridge AI transforms
                complex, underspecified challenges into structured strategies, phased action roadmaps, and
                empirically verified deliverables.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_h1, col_h2 = st.columns([3, 2])

    with col_h1:
        st.subheader("🎯 Active Strategy Overview")
        if not st.session_state.intake:
            st.markdown(
                """
                <div class="ab-card">
                    <h4>No Active Strategy Selected</h4>
                    <p style="color: #64748B; margin-bottom: 16px;">
                        Start by creating a new goal or open one from your saved strategies archive below.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("🚀 Create a Strategy Now", type="primary", use_container_width=True):
                st.session_state.current_page = "🎯 Goal Creation"
                st.rerun()
        else:
            intake = st.session_state.intake
            plan = st.session_state.plan
            analysis = st.session_state.analysis

            completed_tasks = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED) if plan else 0
            total_tasks = len(plan.tasks) if plan else 0
            progress_pct = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0

            st.markdown(
                f"""
                <div class="ab-card">
                    <span class="ab-badge ab-badge-low">Active Strategy</span>
                    <h3 style="margin: 8px 0 6px 0;">{clean_text(intake.goal_title)}</h3>
                    <p style="color: #475569; font-size: 0.95rem; margin-bottom: 12px;">
                        <strong>Strategy:</strong> {clean_text(plan.selected_strategy_title if plan else 'Strategy Formulation Pending')}
                    </p>
                    <p style="color: #64748B; font-size: 0.9rem; margin-bottom: 16px;">
                        Deadline: <strong>{clean_text(intake.deadline or 'Flexible')}</strong> &bull; Total Tasks: <strong>{total_tasks}</strong>
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.progress(progress_pct / 100)
            st.caption(f"Overall Completion: **{progress_pct}%** ({completed_tasks}/{total_tasks} tasks verified)")

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("🔍 Review Strategy", use_container_width=True):
                    st.session_state.current_page = "🧠 Strategy Analysis"
                    st.rerun()
            with c_btn2:
                if st.button("📋 View Action Plan", type="primary", use_container_width=True):
                    st.session_state.current_page = "📋 Action Plan"
                    st.rerun()

    with col_h2:
        st.subheader("⚡ Recommended Next Action")
        if st.session_state.plan:
            plan = st.session_state.plan
            pending = next((t for t in plan.tasks if t.status == TaskStatus.PENDING), None)
            if pending:
                st.markdown(
                    f"""
                    <div class="ab-action-card">
                        <span style="font-weight: 700; color: #B45309; text-transform: uppercase; font-size: 0.8rem;">Immediate Priority</span>
                        <h4 style="margin: 6px 0 4px 0; color: #1E293B;">{pending.task_id}: {clean_text(pending.title)}</h4>
                        <p style="font-size: 0.92rem; color: #334155; margin: 0 0 8px 0;">{clean_text(pending.instructions)}</p>
                        <span style="font-size: 0.85rem; color: #64748B;">⏱️ {clean_text(pending.estimated_duration)} &bull; Output: <strong>{clean_text(pending.expected_output)}</strong></span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button("🛡️ Execute in Sandbox", use_container_width=True):
                    st.session_state.current_page = "🛡️ Execution & Approvals"
                    st.rerun()
            else:
                st.success("🎉 All planned tasks have been executed and verified!")
        else:
            st.info("Formulate your first strategy to unlock dynamic next action recommendations.")

        st.markdown("#### 📜 Recent Session Activity")
        if st.session_state.audit_log:
            recent_logs = st.session_state.audit_log[-4:]
            for log in reversed(recent_logs):
                st.caption(f"&bull; {clean_text(log)}")
        else:
            st.caption("No session events logged yet.")

    # Saved Strategies Archive Section
    st.markdown("---")
    st.subheader("📚 Saved Strategies Archive")
    st.write("Browse, switch between, and manage all your previously formulated strategies:")

    saved_list = list_saved_strategies()
    if not saved_list:
        st.info("No saved strategies archived yet. When you generate a strategy, it will be automatically saved here.")
    else:
        for item in saved_list:
            is_current = st.session_state.analysis and st.session_state.analysis.goal_id == item["goal_id"]
            with st.container():
                col_arch1, col_arch2, col_arch3 = st.columns([3, 1, 1])

                with col_arch1:
                    active_tag = " <span class='ab-badge ab-badge-low'>ACTIVE</span>" if is_current else ""
                    st.markdown(f"**{clean_text(item['goal_title'])}**{active_tag}", unsafe_allow_html=True)
                    st.caption(f"Strategy: *{clean_text(item['selected_strategy_title'])}* &bull; Saved: {item['saved_at'][:10]}")

                with col_arch2:
                    pct = int((item["completed_tasks"] / item["total_tasks"] * 100)) if item["total_tasks"] > 0 else 0
                    st.write(f"Tasks: {item['completed_tasks']}/{item['total_tasks']} ({pct}%)")

                with col_arch3:
                    cb1, cb2 = st.columns(2)
                    with cb1:
                        if st.button("📂 Open", key=f"open_arch_{item['goal_id']}", use_container_width=True):
                            loaded = load_strategy_record(item["goal_id"])
                            if loaded:
                                st.session_state.intake, st.session_state.analysis, st.session_state.selected_strategy, st.session_state.plan = loaded
                                st.session_state.current_page = "🧠 Strategy Analysis"
                                st.rerun()
                    with cb2:
                        if st.button("🗑️", key=f"del_arch_{item['goal_id']}", use_container_width=True, help="Delete this strategy"):
                            delete_strategy_record(item["goal_id"])
                            if is_current:
                                st.session_state.intake = None
                                st.session_state.analysis = None
                                st.session_state.selected_strategy = None
                                st.session_state.plan = None
                            st.rerun()

                st.markdown("")

# ==============================================================================
# SECTION B: GOAL CREATION (ADAPTIVE INTERVIEW & DIRECT FORM)
# ==============================================================================
elif current_page == "🎯 Goal Creation":
    st.header("🎯 Goal Creation & Diagnostic Calibration")
    st.write("Clarify your objectives, uncover hidden constraints, and formulate actionable targets.")

    tab_interview, tab_direct = st.tabs([
        "🎙️ Adaptive Diagnostic Interview (Recommended)",
        "✍️ Direct Goal Specification"
    ])

    with tab_interview:
        st.subheader("🎙️ Dynamic Diagnostic Interview")
        st.write(
            "Enter any ambitious goal, question, or problem. The AI Diagnostic Architect will generate "
            "**4 targeted questions** to probe your baseline, uncover hard constraints, and calibrate your roadmap."
        )

        col_g1, col_g2 = st.columns([3, 1])
        with col_g1:
            custom_goal_text = st.text_input(
                "What do you want to achieve?",
                value=st.session_state.interview.goal_or_problem if st.session_state.interview else "",
                placeholder="e.g. Prepare for GATE AI Exam in 6 months, or Launch an AI product to 100 beta users..."
            )
        with col_g2:
            st.write("")
            st.write("")
            start_interview = st.button("🔍 Generate Interview", type="primary", use_container_width=True)

        if start_interview:
            if not custom_goal_text.strip():
                st.error("Please enter a goal or problem to begin.")
            else:
                with st.spinner("Analyzing challenge and formulating diagnostic questions..."):
                    interview = st.session_state.client.generate_diagnostic_interview(custom_goal_text.strip())
                    st.session_state.interview = interview
                    st.session_state.interview_answers = {}
                st.rerun()

        if st.session_state.interview:
            st.markdown("---")
            st.markdown(f"#### 📋 Calibration Questions for: *{clean_text(st.session_state.interview.goal_or_problem)}*")
            st.caption("Provide realistic details below so ActionBridge AI can tailor its strategy to your constraints.")

            with st.form("adaptive_interview_form"):
                current_answers = {}
                for q in st.session_state.interview.questions:
                    st.markdown(f"**[{clean_text(q.category)}] {clean_text(q.question)}**")
                    st.caption(f"💡 *Why this matters:* {clean_text(q.why_it_matters)}")
                    ans = st.text_area(
                        label=q.question,
                        value=st.session_state.interview_answers.get(q.id, ""),
                        placeholder=q.suggested_placeholder or "Type your answer here...",
                        height=75,
                        key=f"field_{q.id}",
                        label_visibility="collapsed"
                    )
                    current_answers[q.id] = ans
                    st.markdown("")

                submit_interview = st.form_submit_button(
                    "🚀 Synthesize Answers & Formulate Strategy",
                    type="primary",
                    use_container_width=True
                )

            if submit_interview:
                st.session_state.interview_answers = current_answers
                with st.spinner("Synthesizing diagnostic responses into a personalized strategy..."):
                    intake = st.session_state.client.synthesize_interview_to_intake(
                        st.session_state.interview.goal_or_problem,
                        current_answers
                    )
                    st.session_state.intake = intake
                    analysis = st.session_state.client.analyze_goal(intake)
                    st.session_state.analysis = analysis
                    rec = next((s for s in analysis.strategies if s.is_recommended), analysis.strategies[0] if analysis.strategies else None)
                    st.session_state.selected_strategy = rec
                    if rec:
                        plan = st.session_state.client.generate_action_plan(intake, rec)
                        st.session_state.plan = plan

                    # Persist newly created strategy
                    save_strategy_record(intake, analysis, rec, plan)
                    st.session_state.audit_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Strategy formulated and saved: {intake.goal_title}")

                st.success("🎉 Strategy successfully formulated and saved! Redirecting to Strategy Analysis...")
                st.session_state.current_page = "🧠 Strategy Analysis"
                st.rerun()

    with tab_direct:
        st.subheader("✍️ Direct Goal Intake")
        st.write("Specify your goal parameters manually or select a pre-configured template.")

        preset_choice = st.selectbox(
            "Select a starter template or choose Custom Goal:",
            [
                "Custom Goal (Blank)",
                "Launch an AI-Powered Micro-SaaS MVP in 4 Weeks",
                "Transition into Senior AI Engineer Role in 6 Months",
                "Build an Autonomous Academic Grading & Reporting Pipeline"
            ]
        )

        template_data = {
            "Custom Goal (Blank)": {
                "title": "", "why": "", "current": "", "desired": "",
                "deadline": "", "resources": "", "constraints": "", "metrics": ""
            },
            "Launch an AI-Powered Micro-SaaS MVP in 4 Weeks": {
                "title": "Launch an AI-Powered Micro-SaaS MVP in 4 Weeks",
                "why": "Validate customer willingness-to-pay and achieve early revenue.",
                "current": "Have prototype code and market notes, but no deployed app or users.",
                "desired": "Production MVP with 50 active beta testers and verified pipelines.",
                "deadline": "4 Weeks",
                "resources": "15 hours/week, Python knowledge, cloud credits.",
                "constraints": "Zero ad budget, solo technical execution.",
                "metrics": "50 active users, zero critical crashes, working payment integration."
            },
            "Transition into Senior AI Engineer Role in 6 Months": {
                "title": "Transition into Senior AI Engineer Role in 6 Months",
                "why": "Accelerate career trajectory and work on frontier AI systems.",
                "current": "Mid-level software engineer with theoretical knowledge of ML.",
                "desired": "Secured senior role offer at an engineering-driven AI company.",
                "deadline": "6 Months",
                "resources": "20 hours/week study, cloud GPU budget, courses.",
                "constraints": "Demanding full-time day job.",
                "metrics": "3 deployed portfolio projects with verified benchmarks, 5 interviews."
            },
            "Build an Autonomous Academic Grading & Reporting Pipeline": {
                "title": "Build an Autonomous Academic Grading & Reporting Pipeline",
                "why": "Eliminate 80% of repetitive grading overhead while improving feedback.",
                "current": "Grading is done manually with spreadsheets taking 15+ hours weekly.",
                "desired": "Automated evaluation pipeline producing verified PDF reports.",
                "deadline": "2 Weeks",
                "resources": "Python, rubric data, LLM APIs.",
                "constraints": "Zero tolerance for hallucinated scores, strict audit requirements.",
                "metrics": "Rubric consistency > 95%, processing time < 30 seconds per submission."
            }
        }

        defaults = template_data.get(preset_choice, template_data["Custom Goal (Blank)"])

        with st.form("direct_goal_form"):
            col1, col2 = st.columns(2)
            with col1:
                g_title = st.text_input("Goal Title *", value=defaults["title"], placeholder="e.g. Build and publish an AI portfolio")
                g_why = st.text_area("Why does this goal matter?", value=defaults["why"], placeholder="Core motivation and value...", height=80)
                g_current = st.text_area("Current situation / starting baseline:", value=defaults["current"], placeholder="Where you stand today...", height=80)
                g_desired = st.text_area("Desired target outcome:", value=defaults["desired"], placeholder="What the finished result looks like...", height=80)
            with col2:
                g_deadline = st.text_input("Target deadline:", value=defaults["deadline"], placeholder="e.g. 6 Months, or Dec 31")
                g_resources = st.text_area("Available resources (time, budget, tools):", value=defaults["resources"], placeholder="Hours per week, budget...", height=80)
                g_constraints = st.text_area("Constraints and obstacles:", value=defaults["constraints"], placeholder="Time boundaries, technical hurdles...", height=80)
                g_metrics = st.text_area("Success metrics (how victory is proven):", value=defaults["metrics"], placeholder="Measurable milestones...", height=80)

            submitted = st.form_submit_button("🚀 Generate Strategic Analysis", type="primary", use_container_width=True)

        if submitted:
            if not g_title.strip():
                st.error("Please enter a goal title.")
            else:
                intake = GoalIntake(
                    goal_title=g_title,
                    why_it_matters=g_why,
                    current_situation=g_current,
                    desired_outcome=g_desired,
                    deadline=g_deadline,
                    available_resources=g_resources,
                    constraints=g_constraints,
                    success_metrics=g_metrics
                )
                st.session_state.intake = intake
                with st.spinner("Evaluating trade-offs, constraints, and strategic pathways..."):
                    analysis = st.session_state.client.analyze_goal(intake)
                    st.session_state.analysis = analysis
                    rec = next((s for s in analysis.strategies if s.is_recommended), analysis.strategies[0] if analysis.strategies else None)
                    st.session_state.selected_strategy = rec
                    if rec:
                        plan = st.session_state.client.generate_action_plan(intake, rec)
                        st.session_state.plan = plan

                    # Persist newly created strategy
                    save_strategy_record(intake, analysis, rec, plan)
                    st.session_state.audit_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Direct strategy created and saved: {intake.goal_title}")

                st.success("Strategic analysis complete! Redirecting to Strategy Analysis...")
                st.session_state.current_page = "🧠 Strategy Analysis"
                st.rerun()

# ==============================================================================
# SECTION C: STRATEGY ANALYSIS
# ==============================================================================
elif current_page == "🧠 Strategy Analysis":
    st.header("🧠 Strategic Analysis & Path Comparison")

    if not st.session_state.analysis:
        st.info("No active strategy analysis available yet. Complete 'Goal Creation' first.")
        if st.button("👉 Go to Goal Creation", type="primary"):
            st.session_state.current_page = "🎯 Goal Creation"
            st.rerun()
    else:
        analysis = st.session_state.analysis

        # Executive Brief Card
        st.markdown(
            f"""
            <div class="ab-hero-card">
                <span class="ab-badge ab-badge-low">Strategic Brief</span>
                <h3 style="margin: 8px 0 6px 0; color: #1E293B;">{clean_text(analysis.goal_title)}</h3>
                <p style="margin: 0; font-size: 1.05rem; line-height: 1.5; color: #334155;">
                    <strong>Core Challenge:</strong> {clean_text(analysis.problem_definition)}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Baseline vs. Destination Comparison
        st.subheader("📊 State Transition Matrix")
        col_cur, col_fut = st.columns(2)
        with col_cur:
            st.markdown("##### 📍 Starting Baseline (Where you stand today)")
            st.info(clean_text(analysis.current_state_assessment))
            if analysis.constraints_analysis:
                st.caption(f"**Key Constraints:** {clean_text(analysis.constraints_analysis)}")
        with col_fut:
            st.markdown("##### 🏁 Target Destination (Where you will be)")
            st.success(clean_text(analysis.desired_future_state))
            if analysis.opportunities:
                st.caption(f"**Key Opportunities:** {', '.join([clean_text(o) for o in analysis.opportunities[:3]])}")

        st.markdown("---")

        # Three Focused Tabs
        tab_strats, tab_risks, tab_assumptions = st.tabs([
            "⚖️ Strategic Options & Trade-Offs",
            "⚠️ Risk & Pre-Emptive Defense Playbook",
            "🔍 Key Assumptions & Root Causes"
        ])

        with tab_strats:
            st.subheader("⚖️ Strategic Approaches Evaluated")
            st.write("Compare alternative paths evaluated against feasibility, impact, timeline, and risk:")

            if analysis.recommended_strategy_title:
                st.markdown(
                    f"""
                    <div class="ab-rec-card">
                        <span style="font-weight: 700; color: #16A34A; font-size: 1.05rem;">
                            🌟 AI Recommendation: {clean_text(analysis.recommended_strategy_title)}
                        </span><br/>
                        <span style="font-size: 0.95rem; line-height: 1.5; margin-top: 4px; display: inline-block; color: #334155;">
                            <strong>Rationale:</strong> {clean_text(analysis.rationale_for_recommendation)}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            strat_cols = st.columns(len(analysis.strategies))
            for idx, strat in enumerate(analysis.strategies):
                with strat_cols[idx]:
                    is_active = (
                        st.session_state.selected_strategy and
                        st.session_state.selected_strategy.strategy_id == strat.strategy_id
                    )

                    st.markdown(f"### {clean_text(strat.title)}")
                    if strat.is_recommended:
                        st.caption("🌟 **Recommended Option**")
                    if is_active:
                        st.success("👉 Active for Action Plan")

                    st.write(clean_text(strat.overview))

                    m1, m2 = st.columns(2)
                    m1.metric("Feasibility", f"{strat.feasibility_score}/10")
                    m2.metric("Impact", f"{strat.impact_score}/10")

                    st.markdown(f"⏱️ **Timeline:** {clean_text(strat.estimated_time)} &bull; 💰 **Cost:** {clean_text(strat.estimated_cost)}")
                    st.caption(f"🔄 **Reversibility:** {clean_text(strat.reversibility)}")

                    st.markdown("**Pros (Advantages):**")
                    for p in strat.pros:
                        st.markdown(f"- ✅ {clean_text(p)}")

                    st.markdown("**Cons (Trade-offs):**")
                    for c in strat.cons:
                        st.markdown(f"- ⚠️ {clean_text(c)}")

                    st.markdown("")
                    btn_label = "✅ Selected" if is_active else f"👉 Select Strategy {idx+1}"
                    if st.button(btn_label, key=f"btn_strat_{idx}", use_container_width=True, type="primary" if is_active else "secondary"):
                        st.session_state.selected_strategy = strat
                        with st.spinner("Generating detailed phased action plan..."):
                            plan = st.session_state.client.generate_action_plan(st.session_state.intake, strat)
                            st.session_state.plan = plan
                        save_strategy_record(st.session_state.intake, analysis, strat, plan)
                        st.session_state.audit_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Switched to strategy: {strat.title}")
                        st.rerun()

        with tab_risks:
            st.subheader("⚠️ Major Risks & Defense Playbook")
            st.write("Identified potential failure modes paired with pre-planned defenses:")
            if not analysis.major_risks_and_mitigations:
                st.info("No critical risks identified for this profile.")
            else:
                for idx, r in enumerate(analysis.major_risks_and_mitigations):
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.markdown(f"**🚨 Threat #{idx+1}:**")
                        st.warning(clean_text(r.get("risk", "Identified risk")))
                    with col_r2:
                        st.markdown(f"**🛡️ Pre-emptive Defense:**")
                        st.success(clean_text(r.get("mitigation", "Pre-planned mitigation")))
                    st.markdown("")

        with tab_assumptions:
            st.subheader("🔍 Foundations & Root Causes")
            col_asm1, col_asm2 = st.columns(2)
            with col_asm1:
                st.markdown("#### 📌 Key Working Assumptions")
                for asm in analysis.key_assumptions:
                    st.write(f"- 🔹 {clean_text(asm)}")
            with col_asm2:
                st.markdown("#### 🔬 Root Cause Analysis")
                st.write(clean_text(analysis.root_cause_analysis))
                if analysis.opportunities:
                    st.markdown("#### 🚀 Key Opportunities")
                    for opp in analysis.opportunities:
                        st.write(f"- ✨ {clean_text(opp)}")

        st.markdown("---")
        col_nav1, col_nav2 = st.columns([3, 1])
        with col_nav2:
            if st.button("Proceed to Action Plan ➔", type="primary", use_container_width=True):
                st.session_state.current_page = "📋 Action Plan"
                st.rerun()

# ==============================================================================
# SECTION D: ACTION PLAN
# ==============================================================================
elif current_page == "📋 Action Plan":
    st.header("📋 Phased Action Plan & Roadmap")

    if not st.session_state.plan:
        st.info("No action plan generated yet. Complete Goal Creation and Strategy Analysis first.")
        if st.button("👉 Go to Goal Creation", type="primary"):
            st.session_state.current_page = "🎯 Goal Creation"
            st.rerun()
    else:
        plan = st.session_state.plan
        tasks = plan.tasks

        # Header Summary
        st.markdown(
            f"""
            <div class="ab-hero-card">
                <span class="ab-badge ab-badge-low">Execution Roadmap</span>
                <h3 style="margin: 8px 0 6px 0; color: #1E293B;">{clean_text(plan.goal_title)}</h3>
                <p style="margin: 0; font-size: 0.95rem; color: #475569;">
                    Selected Strategy: <strong>{clean_text(plan.selected_strategy_title)}</strong> &bull; Plan ID: <code>{plan.plan_id}</code>
                </p>
                <p style="margin: 8px 0 0 0; font-size: 1.02rem; line-height: 1.5; color: #334155;">
                    {clean_text(plan.strategic_summary)}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Immediate Next Action Callout
        first_pending = next((t for t in tasks if t.status == TaskStatus.PENDING), tasks[0] if tasks else None)
        if first_pending:
            st.markdown(
                f"""
                <div class="ab-action-card">
                    <span style="font-weight: 700; color: #B45309; text-transform: uppercase; font-size: 0.8rem;">Immediate Next Action (Start Here)</span>
                    <h4 style="margin: 6px 0 4px 0; color: #1E293B;">{first_pending.task_id}: {clean_text(first_pending.title)}</h4>
                    <p style="font-size: 0.95rem; color: #334155; margin: 0 0 6px 0;">{clean_text(first_pending.instructions)}</p>
                    <span style="font-size: 0.85rem; color: #64748B;">
                        ⏱️ {clean_text(first_pending.estimated_duration)} &bull; Output: <strong>{clean_text(first_pending.expected_output)}</strong>
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Success Milestones Timeline
        st.markdown("#### 🚩 Success Milestones Timeline")
        milestone_items = " &nbsp; ➔ &nbsp; ".join([f"**{idx+1}. {clean_text(m)}**" for idx, m in enumerate(plan.milestones)])
        st.markdown(
            f"""
            <div class="ab-milestone-bar">
                {milestone_items}
            </div>
            """,
            unsafe_allow_html=True
        )

        # Task Filters
        st.markdown("---")
        st.subheader("📝 Phased Execution Tasks")

        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            filter_priority = st.selectbox("Filter by Priority:", ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
        with col_f2:
            filter_status = st.selectbox("Filter by Status:", ["All", "PENDING", "COMPLETED", "AWAITING_APPROVAL", "FAILED"])

        filtered_tasks = tasks
        if filter_priority != "All":
            filtered_tasks = [t for t in filtered_tasks if t.priority.value == filter_priority]
        if filter_status != "All":
            filtered_tasks = [t for t in filtered_tasks if t.status.value == filter_status]

        # Group tasks by phase
        phases = {}
        for t in filtered_tasks:
            phases.setdefault(t.phase or "Phase 1: Foundation", []).append(t)

        if not phases:
            st.info("No tasks match the selected filters.")
        else:
            for phase_name, p_tasks in phases.items():
                st.markdown(f"### 📌 {phase_name} ({len(p_tasks)} tasks)")

                for task in p_tasks:
                    info = format_tool_action(task.tool_name, task.tool_args)

                    risk_class = "ab-badge-low" if task.risk_level == RiskLevel.LOW else ("ab-badge-medium" if task.risk_level == RiskLevel.MEDIUM else "ab-badge-high")
                    risk_badge = f"{task.risk_level.value} RISK"
                    status_icon = "⏳ Pending" if task.status == TaskStatus.PENDING else ("✅ Completed" if task.status == TaskStatus.COMPLETED else f"⚠️ {task.status.value}")

                    with st.expander(f"{task.task_id}: {clean_text(task.title)}  |  [{task.priority.value}]  |  ⏱️ {clean_text(task.estimated_duration)}  |  {risk_badge}", expanded=True):
                        col_t1, col_t2 = st.columns([3, 1])
                        with col_t1:
                            st.markdown(f"**Action:** {clean_text(task.instructions)}")
                            st.markdown(f"**🎯 Tangible Deliverable:** `{clean_text(task.expected_output)}`")
                            st.caption(f"📌 *{info['action_summary']}*")
                            if info.get("file"):
                                st.caption(f"📁 Target Document: `{info['file']}`")

                            # Expandable Technical Details (Cleaner default view)
                            with st.expander("🛠️ Technical details"):
                                st.markdown(f"- **Tool:** `{task.tool_name or 'None (Manual Action)'}`")
                                st.markdown(f"- **Verification Check:** {clean_text(task.completion_criteria)}")
                                st.markdown("- **Arguments:**")
                                st.json(task.tool_args or {})
                                if info.get("preview_content"):
                                    st.markdown("- **Document Preview:**")
                                    st.code(info["preview_content"][:800])

                        with col_t2:
                            st.markdown(f"**Status:** {status_icon}")
                            st.caption(f"Risk Reason: *{clean_text(task.risk_reason)}*")
                            if task.risk_level == RiskLevel.HIGH and not task.is_approved:
                                st.warning("Requires authorization in Page 5")

                st.markdown("")

        # Download / Export Roadmap Section
        st.markdown("---")
        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            st.markdown("#### 📥 Export Full Strategy & Action Plan")
            st.write("Download your complete strategic brief, milestones, and phased checklist as a formatted Markdown document for Notion, Obsidian, or team distribution.")
        with col_d2:
            st.write("")
            full_md = generate_markdown_roadmap(st.session_state.analysis, plan)
            st.download_button(
                label="📥 Download Strategy (.md)",
                data=full_md,
                file_name=f"strategy_roadmap_{plan.plan_id.lower()}.md",
                mime="text/markdown",
                use_container_width=True
            )

        col_n1, col_n2 = st.columns([3, 1])
        with col_n2:
            if st.button("Proceed to Approvals & Execution ➔", type="primary", use_container_width=True):
                st.session_state.current_page = "🛡️ Execution & Approvals"
                st.rerun()

# ==============================================================================
# SECTION E: EXECUTION & APPROVALS
# ==============================================================================
elif current_page == "🛡️ Execution & Approvals":
    st.header("🛡️ Controlled Execution & Human Gatekeeper")
    st.write("ActionBridge AI operates with strict human authorization. Consequential actions remain blocked until explicitly approved.")

    if not st.session_state.plan:
        st.info("No active plan available for execution. Create an action plan first.")
        if st.button("👉 Go to Goal Creation", type="primary"):
            st.session_state.current_page = "🎯 Goal Creation"
            st.rerun()
    else:
        plan = st.session_state.plan

        st.subheader("Human Authorization Gate")
        st.write("Review proposed actions. Actions requiring authorization are flagged below:")

        for idx, task in enumerate(plan.tasks):
            info = format_tool_action(task.tool_name, task.tool_args)
            col_info, col_auth = st.columns([4, 1])

            with col_info:
                badge = "🔴 HIGH RISK" if task.risk_level == RiskLevel.HIGH else ("🟡 MEDIUM RISK" if task.risk_level == RiskLevel.MEDIUM else "🟢 LOW RISK")
                st.markdown(f"**{task.task_id}: {clean_text(task.title)}** &nbsp; `{badge}`")
                st.caption(f"Action: *{info['action_summary']}* &bull; Deliverable: {clean_text(task.expected_output)}")
                if info.get("file"):
                    st.caption(f"Target File: `{info['file']}`")

            with col_auth:
                auth = st.checkbox("Authorize", value=task.is_approved, key=f"chk_auth_{task.task_id}")
                task.is_approved = auth
                if task.risk_level == RiskLevel.HIGH and not auth:
                    st.caption("🛑 Blocked until authorized")

        st.markdown("---")
        if st.button("🚀 Execute Approved Pipeline", type="primary", use_container_width=True):
            st.session_state.audit_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Execution pipeline initiated.")
            progress_bar = st.progress(0)
            status_box = st.empty()

            for i, task in enumerate(plan.tasks):
                progress_bar.progress((i + 1) / len(plan.tasks))
                status_box.text(f"Processing {task.task_id}: {clean_text(task.title)}...")

                # Safety check: block unapproved high-risk steps
                if task.risk_level == RiskLevel.HIGH and not task.is_approved:
                    task.status = TaskStatus.SKIPPED
                    task.verification_status = VerificationStatus.SKIPPED
                    task.verification_message = "SAFETY BARRIER: High-risk action blocked due to missing human approval."
                    st.session_state.audit_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 [SAFETY BLOCK] {task.task_id} skipped.")
                    continue

                if not task.tool_name:
                    task.status = TaskStatus.COMPLETED
                    task.verification_status = VerificationStatus.VERIFIED
                    task.verification_message = "Informational planning task completed."
                    continue

                # Execute tool in sandbox
                task.status = TaskStatus.RUNNING
                result = execute_tool(task.tool_name, task.tool_args)
                task.execution_result = result

                if not result.get("success"):
                    task.status = TaskStatus.FAILED
                    task.verification_status = VerificationStatus.FAILED
                    task.verification_message = f"Execution error: {result.get('error')}"
                    st.session_state.audit_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ [FAILED] {task.task_id}: {result.get('error')}")
                else:
                    # Independent verification
                    verification = PostConditionVerifier.verify_task_outcome(task.tool_name, task.tool_args, result)
                    task.verification_status = verification["status"]
                    task.verification_message = verification["message"]
                    task.verification_evidence = verification.get("evidence")

                    if verification["status"] == VerificationStatus.VERIFIED:
                        task.status = TaskStatus.COMPLETED
                        st.session_state.audit_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ [VERIFIED] {task.task_id}: {verification['message']}")
                    else:
                        task.status = TaskStatus.FAILED
                        st.session_state.audit_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ [REJECTED] {task.task_id}: {verification['message']}")

            # Persist updated execution state
            save_strategy_record(st.session_state.intake, st.session_state.analysis, st.session_state.selected_strategy, plan)

            status_box.empty()
            st.success("Execution and post-condition verification complete!")
            st.rerun()

        # Display Execution Results
        st.markdown("---")
        st.subheader("📋 Execution Outcomes & Verification Audit")
        for task in plan.tasks:
            status_badge = "✅ COMPLETED" if task.status == TaskStatus.COMPLETED else ("🛑 SKIPPED (SAFETY)" if task.status == TaskStatus.SKIPPED else ("❌ FAILED" if task.status == TaskStatus.FAILED else "⏳ PENDING"))
            with st.expander(f"{task.task_id}: {clean_text(task.title)} &bull; {status_badge}"):
                st.write(f"**Verification Outcome:** {clean_text(task.verification_message or 'Pending execution')}")
                if task.verification_evidence:
                    with st.expander("🛠️ Forensic Verification Evidence"):
                        st.json(task.verification_evidence)

# ==============================================================================
# SECTION F: PROGRESS & MILESTONES
# ==============================================================================
elif current_page == "📊 Progress & Milestones":
    st.header("📊 Progress Analytics & Physical Deliverables")

    if not st.session_state.plan:
        st.info("No active roadmap to track. Create an action plan first.")
        if st.button("👉 Go to Goal Creation", type="primary"):
            st.session_state.current_page = "🎯 Goal Creation"
            st.rerun()
    else:
        plan = st.session_state.plan
        tasks = plan.tasks

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        verified = sum(1 for t in tasks if t.verification_status == VerificationStatus.VERIFIED)
        skipped = sum(1 for t in tasks if t.status == TaskStatus.SKIPPED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        pct = int((completed / total * 100)) if total > 0 else 0

        # KPI Metrics Row
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Progress", f"{pct}%")
        m2.metric("Total Tasks", total)
        m3.metric("Completed", completed)
        m4.metric("Physically Verified 🛡️", verified)
        m5.metric("Safety Blocked 🛑", skipped)

        st.progress(pct / 100)

        # Milestones Checklist
        st.markdown("---")
        st.subheader("🚩 Milestones Journey")
        for idx, m in enumerate(plan.milestones):
            is_done = pct >= int((idx + 1) / len(plan.milestones) * 100)
            icon = "✅" if is_done else "⏳"
            st.markdown(f"**{icon} Milestone {idx+1}:** {clean_text(m)}")

        # Physical Deliverables in Workspace
        st.markdown("---")
        st.subheader("📁 Physical Deliverables in Sandbox Workspace")
        st.caption(f"Auditing folder: `{WORKSPACE_DIR.name}/`")

        sandbox_files = [f for f in WORKSPACE_DIR.glob("*") if f.is_file() and not f.name.startswith(".")]
        if not sandbox_files:
            st.info("No deliverable files generated in the workspace yet. Run execution in 'Execution & Approvals'.")
        else:
            file_cols = st.columns(min(len(sandbox_files), 3))
            for i, f in enumerate(sandbox_files):
                with file_cols[i % len(file_cols)]:
                    st.markdown(f"**📄 `{f.name}`**")
                    st.caption(f"Size: {f.stat().st_size} bytes &bull; Modified: {datetime.fromtimestamp(f.stat().st_mtime).strftime('%H:%M:%S')}")
                    with st.expander("Document Preview"):
                        try:
                            content = f.read_text(encoding="utf-8")
                            if f.name.endswith(".json"):
                                st.json(json.loads(content))
                            else:
                                st.markdown(clean_text(content))
                        except Exception:
                            st.text("Binary or raw content")

        # Download Strategy at the end
        st.markdown("---")
        col_dl1, col_dl2 = st.columns([3, 1])
        with col_dl1:
            st.markdown("#### 📥 Download Complete Strategy & Status")
            st.write("Export your strategy, completed milestones, and audit verification history as Markdown.")
        with col_dl2:
            st.write("")
            full_md = generate_markdown_roadmap(st.session_state.analysis, plan)
            st.download_button(
                label="📥 Download Strategy (.md)",
                data=full_md,
                file_name=f"actionbridge_strategy_{plan.plan_id.lower()}.md",
                mime="text/markdown",
                use_container_width=True,
                key="dl_btn_progress"
            )
