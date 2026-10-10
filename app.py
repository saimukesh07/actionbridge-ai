"""
ActionBridge AI - Strategic Planning & Verified Execution Platform
Streamlit Frontend integrating Goal Intake, Gemini Strategic Analysis,
Controlled Sandbox Execution, and Independent Post-Condition Verification.
"""

import json
from datetime import datetime
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

# Page setup
st.set_page_config(
    page_title="ActionBridge AI — Strategy & Execution",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Sidebar Navigation & System Telemetry
with st.sidebar:
    st.title("🌉 ActionBridge AI")
    st.caption("Strategy & Verified Execution Platform")
    st.markdown("---")

    nav = st.radio(
        "Navigation",
        [
            "1. 🎯 Goal Intake",
            "2. 🧠 Strategic Analysis",
            "3. 📋 Action Plan",
            "4. 🛡️ Approvals & Execution",
            "5. 🔬 Verification Audit",
            "6. 📊 Progress Dashboard"
        ]
    )

    st.markdown("---")
    st.markdown("### ⚙️ System Status")
    active_prov = get_active_ai_provider()
    if active_prov == "gemini":
        st.success(f"🟢 Gemini Live ({GEMINI_MODEL})")
    elif active_prov == "groq":
        st.success(f"🟢 Groq Live ({GROQ_MODEL})")
    else:
        st.info("🟡 Local Demo Mode (Deterministic Fallback)")
    st.caption(f"Sandbox: `{WORKSPACE_DIR.name}/`")

    if st.button("🔄 Reset Session", use_container_width=True):
        st.session_state.intake = None
        st.session_state.interview = None
        st.session_state.interview_answers = {}
        st.session_state.analysis = None
        st.session_state.selected_strategy = None
        st.session_state.plan = None
        st.session_state.audit_log = []
        st.rerun()

# ==============================================================================
# PAGE 1: GOAL INTAKE & ADAPTIVE INTERVIEW
# ==============================================================================
if nav == "1. 🎯 Goal Intake":
    st.header("🎯 1. Interactive Diagnostic & Goal Intake")
    st.write("Transform any ambiguous challenge, project, or custom goal into a verified strategic roadmap.")

    tab_interview, tab_direct = st.tabs([
        "🎙️ Adaptive Diagnostic Interview (Recommended for Custom Goals)",
        "✍️ Direct Intake Form"
    ])

    # --------------------------------------------------------------------------
    # TAB 1: ADAPTIVE DIAGNOSTIC INTERVIEW
    # --------------------------------------------------------------------------
    with tab_interview:
        st.subheader("🎙️ Dynamic Diagnostic Interview")
        st.markdown(
            "Enter any goal or problem below. The AI Diagnostic Architect will generate **4 sharp, personalized questions** "
            "to probe your baseline, uncover real constraints, and calibrate the ideal strategy before planning."
        )

        col_g1, col_g2 = st.columns([3, 1])
        with col_g1:
            custom_goal_text = st.text_input(
                "What is your goal or challenge?",
                value=st.session_state.interview.goal_or_problem if st.session_state.interview else "",
                placeholder="e.g., Prepare for GATE AI Exam in 6 months, or Launch an AI agent for real estate..."
            )
        with col_g2:
            st.write("")
            st.write("")
            start_interview = st.button("🔍 Generate Interview", type="primary", use_container_width=True)

        if start_interview:
            if not custom_goal_text.strip():
                st.error("Please enter a goal or problem to begin the interview.")
            else:
                with st.spinner("Analyzing problem and formulating dynamic diagnostic questions..."):
                    interview = st.session_state.client.generate_diagnostic_interview(custom_goal_text.strip())
                    st.session_state.interview = interview
                    st.session_state.interview_answers = {}
                st.rerun()

        if st.session_state.interview:
            st.markdown("---")
            st.markdown(f"#### 📋 Clarification Questions for: *{st.session_state.interview.goal_or_problem}*")
            st.caption("Fill in your answers below so ActionBridge AI can tailor its recommendations directly to your reality.")

            with st.form("interview_submission_form"):
                current_answers = {}
                for q in st.session_state.interview.questions:
                    st.markdown(f"**[{q.category}] {q.question}**")
                    st.caption(f"💡 *Why this matters:* {q.why_it_matters}")
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

                submit_interview = st.form_submit_button("🚀 Synthesize Answers & Generate Strategy", type="primary", use_container_width=True)

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

                st.success("🎉 Strategy and Action Plan generated from your answers!")
                st.info("👉 Switch to **'2. 🧠 Strategic Analysis'** in the sidebar to view your personalized options and roadmap.")

    # --------------------------------------------------------------------------
    # TAB 2: DIRECT INTAKE FORM
    # --------------------------------------------------------------------------
    with tab_direct:
        st.subheader("✍️ Direct Goal Intake")
        st.write("Fill in all structured dimensions manually or select a pre-configured template.")

        preset_choice = st.selectbox(
            "Select a template or choose Custom Goal:",
            [
                "Custom Goal (Blank)",
                "Launch an AI-Powered Micro-SaaS MVP in 4 Weeks",
                "Transition into Senior AI Engineer Role in 6 Months",
                "Build an Autonomous Academic Grading & Reporting Pipeline"
            ]
        )

        template_data = {
            "Custom Goal (Blank)": {
                "title": "",
                "why": "",
                "current": "",
                "desired": "",
                "deadline": "",
                "resources": "",
                "constraints": "",
                "metrics": ""
            },
            "Launch an AI-Powered Micro-SaaS MVP in 4 Weeks": {
                "title": "Launch an AI-Powered Micro-SaaS MVP in 4 Weeks",
                "why": "Achieve financial independence and validate market demand rapidly.",
                "current": "Have core prototype and technical ideas, but no deployed system or users.",
                "desired": "Production application with 50 active beta testers and verified pipelines.",
                "deadline": "4 Weeks",
                "resources": "15 hours/week, Python/FastAPI knowledge, cloud credits.",
                "constraints": "Bootstrapped zero-dollar ad budget, solo builder.",
                "metrics": "50 active signups, zero critical crash bugs, working stripe billing."
            },
            "Transition into Senior AI Engineer Role in 6 Months": {
                "title": "Transition into Senior AI Engineer Role in 6 Months",
                "why": "Advance engineering career and work on frontier AI systems.",
                "current": "Mid-level software engineer with theoretical knowledge of ML.",
                "desired": "Secured senior role with offer at tier-1 AI/Tech organization.",
                "deadline": "6 Months",
                "resources": "20 hours/week study, GPU budget, courses.",
                "constraints": "Demanding full-time day job.",
                "metrics": "3 deployed portfolio projects with verified benchmarks, 5 interviews."
            },
            "Build an Autonomous Academic Grading & Reporting Pipeline": {
                "title": "Build an Autonomous Academic Grading & Reporting Pipeline",
                "why": "Eliminate 80% of repetitive grading overhead while improving student feedback.",
                "current": "Grading is done manually with spreadsheets taking 15+ hours weekly.",
                "desired": "Automated evaluation pipeline producing verified PDF reports.",
                "deadline": "2 Weeks",
                "resources": "Python, rubric data, LLM APIs.",
                "constraints": "Strict academic integrity, zero tolerance for hallucinated marks.",
                "metrics": "Rubric consistency > 95%, processing time < 30 seconds per submission."
            }
        }

        defaults = template_data.get(preset_choice, template_data["Custom Goal (Blank)"])

        with st.form("goal_intake_form"):
            col1, col2 = st.columns(2)
            with col1:
                g_title = st.text_input("Goal Title:", value=defaults["title"], placeholder="e.g. Build my AI portfolio")
                g_why = st.text_area("Why does this goal matter?", value=defaults["why"], placeholder="Core motivation...", height=80)
                g_current = st.text_area("Current situation / baseline:", value=defaults["current"], placeholder="Where you currently stand...", height=80)
                g_desired = st.text_area("Desired target outcome:", value=defaults["desired"], placeholder="What the finished result looks like...", height=80)
            with col2:
                g_deadline = st.text_input("Target deadline:", value=defaults["deadline"], placeholder="e.g. 6 Months, or Dec 31")
                g_resources = st.text_area("Available resources (time, budget, tools):", value=defaults["resources"], placeholder="Hours per week, budget...", height=80)
                g_constraints = st.text_area("Constraints and obstacles:", value=defaults["constraints"], placeholder="Time limits, skill gaps...", height=80)
                g_metrics = st.text_area("How will success be measured?", value=defaults["metrics"], placeholder="Measurable milestones...", height=80)

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
                with st.spinner("Analyzing constraints, assumptions, and evaluating strategic options..."):
                    analysis = st.session_state.client.analyze_goal(intake)
                    st.session_state.analysis = analysis
                    rec = next((s for s in analysis.strategies if s.is_recommended), analysis.strategies[0] if analysis.strategies else None)
                    st.session_state.selected_strategy = rec
                    if rec:
                        plan = st.session_state.client.generate_action_plan(intake, rec)
                        st.session_state.plan = plan
                st.success("Strategic analysis complete! Navigate to '2. 🧠 Strategic Analysis' to view findings.")

# ==============================================================================
# PAGE 2: STRATEGIC ANALYSIS & COMPARISON
# ==============================================================================
elif nav == "2. 🧠 Strategic Analysis":
    st.header("🧠 2. Strategic Analysis Engine")

    if not st.session_state.analysis:
        st.info("No goal analyzed yet. Please complete '1. 🎯 Goal Intake' first.")
    else:
        analysis = st.session_state.analysis
        if analysis.is_demo:
            st.warning("ℹ️ Showing deterministic offline demonstration analysis. Add GROQ_API_KEY or GEMINI_API_KEY to .env for live AI reasoning.")
        else:
            provider_tag = get_active_ai_provider().upper()
            st.success(f"✨ Live Strategic Analysis Generated via {provider_tag}")

        # 1. Executive Brief Card
        st.markdown(
            f"""
            <div style="background-color: rgba(28, 131, 225, 0.08); border-left: 5px solid #1C83E1; padding: 16px 20px; border-radius: 6px; margin-bottom: 20px;">
                <h3 style="margin: 0 0 8px 0;">🎯 Executive Brief: {analysis.goal_title}</h3>
                <p style="margin: 0; font-size: 1.05rem; line-height: 1.5;"><strong>Core Challenge:</strong> {analysis.problem_definition}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 2. Side-by-side Baseline vs Destination
        st.subheader("📊 Current State vs. Target Destination")
        col_cur, col_fut = st.columns(2)
        with col_cur:
            st.markdown("##### 📍 Starting Baseline (Where you stand today)")
            st.info(analysis.current_state_assessment)
            if analysis.constraints_analysis:
                st.caption(f"**Key Constraints:** {analysis.constraints_analysis}")
        with col_fut:
            st.markdown("##### 🏁 Target Destination (Where you will be)")
            st.success(analysis.desired_future_state)
            if analysis.opportunities:
                st.caption(f"**Key Opportunities:** {', '.join(analysis.opportunities[:3])}")

        st.markdown("---")

        # 3. Structured Tabs: Strategies, Risks, Insights
        tab_strats, tab_risks, tab_assumptions = st.tabs([
            "⚖️ Strategic Options (Comparison & Selection)",
            "⚠️ Risk & Defense Playbook",
            "🔍 Key Assumptions & Root Causes"
        ])

        with tab_strats:
            st.subheader("⚖️ Strategic Approaches Compared")
            st.write("Review the viable pathways evaluated against feasibility, impact, timeline, and risk:")

            if analysis.recommended_strategy_title:
                st.markdown(
                    f"""
                    <div style="background-color: rgba(33, 195, 84, 0.1); border: 1px solid #21C354; padding: 14px 18px; border-radius: 6px; margin-bottom: 20px;">
                        <span style="font-weight: bold; color: #21C354; font-size: 1.05rem;">🌟 AI Recommended Strategy: {analysis.recommended_strategy_title}</span><br/>
                        <span style="font-size: 0.95rem; line-height: 1.5; margin-top: 4px; display: inline-block;"><strong>Rationale:</strong> {analysis.rationale_for_recommendation}</span>
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

                    st.markdown(f"### {strat.title}")
                    if strat.is_recommended:
                        st.caption("🌟 **Recommended Approach**")
                    if is_active:
                        st.success("👉 Currently Active Strategy")

                    st.write(strat.overview)

                    # Metrics row
                    m1, m2 = st.columns(2)
                    m1.metric("Feasibility", f"{strat.feasibility_score}/10")
                    m2.metric("Impact", f"{strat.impact_score}/10")

                    st.markdown(f"⏱️ **Timeline:** {strat.estimated_time} &bull; 💰 **Cost:** {strat.estimated_cost}")
                    st.caption(f"🔄 **Reversibility:** {strat.reversibility}")

                    st.markdown("**Pros (Advantages):**")
                    for p in strat.pros:
                        st.markdown(f"- ✅ {p}")

                    st.markdown("**Cons (Trade-offs):**")
                    for c in strat.cons:
                        st.markdown(f"- ⚠️ {c}")

                    st.markdown("")
                    btn_label = "✅ Selected" if is_active else f"👉 Select Strategy {idx+1}"
                    if st.button(btn_label, key=f"btn_strat_{idx}", use_container_width=True, type="primary" if is_active else "secondary"):
                        st.session_state.selected_strategy = strat
                        with st.spinner("Generating detailed phased action plan..."):
                            plan = st.session_state.client.generate_action_plan(st.session_state.intake, strat)
                            st.session_state.plan = plan
                        st.success(f"Selected: {strat.title}!")
                        st.rerun()

        with tab_risks:
            st.subheader("⚠️ Major Risks & Pre-Emptive Defenses")
            st.write("Identified potential failure modes and pre-planned mitigations:")
            if not analysis.major_risks_and_mitigations:
                st.info("No critical risks identified for this profile.")
            else:
                for idx, r in enumerate(analysis.major_risks_and_mitigations):
                    with st.container():
                        col_r1, col_r2 = st.columns([1, 1])
                        with col_r1:
                            st.markdown(f"**🚨 Threat #{idx+1}:**")
                            st.warning(r.get("risk", "Identified risk"))
                        with col_r2:
                            st.markdown(f"**🛡️ Pre-emptive Defense:**")
                            st.success(r.get("mitigation", "Pre-planned mitigation"))
                        st.markdown("")

        with tab_assumptions:
            st.subheader("🔍 Foundations & Root Causes")
            col_asm1, col_asm2 = st.columns(2)
            with col_asm1:
                st.markdown("#### 📌 Key Working Assumptions")
                for asm in analysis.key_assumptions:
                    st.write(f"- 🔹 {asm}")
            with col_asm2:
                st.markdown("#### 🔬 Root Cause Analysis")
                st.write(analysis.root_cause_analysis)
                if analysis.opportunities:
                    st.markdown("#### 🚀 Key Opportunities")
                    for opp in analysis.opportunities:
                        st.write(f"- ✨ {opp}")

        st.markdown("---")
        st.info("💡 Next Step: Switch to **'3. 📋 Action Plan'** in the sidebar to review your step-by-step phased execution tasks!")

# ==============================================================================
# PAGE 3: ACTION PLAN
# ==============================================================================
elif nav == "3. 📋 Action Plan":
    st.header("📋 3. Action Plan & Phased Roadmap")

    if not st.session_state.plan:
        st.info("No action plan generated yet. Complete Goal Intake and Strategic Analysis to create one.")
    else:
        plan = st.session_state.plan
        tasks = plan.tasks

        # Header Banner
        st.markdown(
            f"""
            <div style="background-color: rgba(28, 131, 225, 0.08); border-left: 5px solid #1C83E1; padding: 16px 20px; border-radius: 6px; margin-bottom: 20px;">
                <h3 style="margin: 0 0 6px 0;">🗺️ Roadmap: {plan.goal_title}</h3>
                <p style="margin: 0; font-size: 0.95rem; color: #555;">Selected Strategy: <strong>{plan.selected_strategy_title}</strong> &bull; Plan ID: <code>{plan.plan_id}</code></p>
                <p style="margin: 8px 0 0 0; font-size: 1.02rem; line-height: 1.5;">{plan.strategic_summary}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Immediate Next Action (Start Here)
        first_pending = next((t for t in tasks if t.status == TaskStatus.PENDING), tasks[0] if tasks else None)
        if first_pending:
            st.markdown(
                f"""
                <div style="background-color: rgba(255, 170, 0, 0.1); border: 1px solid #FFAA00; padding: 14px 18px; border-radius: 6px; margin-bottom: 20px;">
                    <span style="font-weight: bold; color: #D48800; font-size: 1rem;">🚀 Immediate Next Action (Start Here Today):</span><br/>
                    <strong style="font-size: 1.05rem;">{first_pending.task_id}: {first_pending.title}</strong> &nbsp; <code>⏱️ {first_pending.estimated_duration}</code> &nbsp; <code>{first_pending.priority.value} PRIORITY</code><br/>
                    <span style="font-size: 0.95rem; margin-top: 6px; display: inline-block;">📌 <em>{first_pending.instructions}</em></span><br/>
                    <span style="font-size: 0.9rem; color: #444; margin-top: 4px; display: inline-block;">🎯 <strong>Deliverable:</strong> {first_pending.expected_output}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Success Milestones Timeline
        st.markdown("#### 🚩 Success Milestones Timeline")
        milestone_text = " &nbsp; ➔ &nbsp; ".join([f"**{idx+1}. {m}**" for idx, m in enumerate(plan.milestones)])
        st.markdown(
            f"""
            <div style="background: rgba(128, 128, 128, 0.08); padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
                {milestone_text}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")
        st.subheader("📝 Phased Execution Task Breakdown")

        # Group tasks by phase
        phases = {}
        for t in tasks:
            phase_key = t.phase or "Phase 1: Foundation"
            phases.setdefault(phase_key, []).append(t)

        for phase_name, phase_tasks in phases.items():
            st.markdown(f"### 📌 {phase_name} ({len(phase_tasks)} tasks)")

            for task in phase_tasks:
                risk_badge = "🟢 SAFE (LOW RISK)" if task.risk_level == RiskLevel.LOW else ("🟡 MEDIUM RISK" if task.risk_level == RiskLevel.MEDIUM else "🔴 CONSEQUENTIAL (REQUIRES APPROVAL)")
                priority_badge = f"⚡ {task.priority.value}" if task.priority == TaskPriority.CRITICAL else (f"🔥 {task.priority.value}" if task.priority == TaskPriority.HIGH else f"🔹 {task.priority.value}")
                status_icon = "⏳ Pending" if task.status == TaskStatus.PENDING else ("✅ Completed" if task.status == TaskStatus.COMPLETED else "🛑 Blocked")

                with st.expander(f"{task.task_id}: {task.title}  |  {priority_badge}  |  ⏱️ {task.estimated_duration}  |  {risk_badge}", expanded=True):
                    col_t1, col_t2 = st.columns([3, 1])
                    with col_t1:
                        st.markdown(f"**Action Steps:** {task.instructions}")
                        st.markdown(f"**🎯 Tangible Deliverable:** `{task.expected_output}`")
                        st.caption(f"**Verification Check:** {task.completion_criteria}")
                        if task.tool_name:
                            st.caption(f"🔧 Automated Tool: `tools.{task.tool_name}` (Args: `{json.dumps(task.tool_args)}`)")
                        else:
                            st.caption("👤 Mode: User-Executed Action")
                    with col_t2:
                        st.markdown(f"**Status:** {status_icon}")
                        st.caption(f"**Risk Level:** {task.risk_level.value}")
                        st.caption(f"*{task.risk_reason}*")
                        if task.risk_level == RiskLevel.HIGH and not task.is_approved:
                            st.warning("Needs approval in Page 4")

            st.markdown("")

        # Export Roadmap feature
        st.markdown("---")
        col_exp1, col_exp2 = st.columns([2, 1])
        with col_exp1:
            st.markdown("#### 📥 Take Your Roadmap With You")
            st.write("Export your strategy, milestones, and phased checklist as a formatted Markdown brief for Notion, Obsidian, or team sharing.")
        with col_exp2:
            st.write("")
            md_content = f"# ActionBridge AI Strategic Roadmap: {plan.goal_title}\n\n"
            md_content += f"**Strategy:** {plan.selected_strategy_title}\n"
            md_content += f"**Plan ID:** {plan.plan_id}\n\n"
            md_content += f"## Executive Summary\n{plan.strategic_summary}\n\n"
            md_content += f"## Milestones\n"
            for idx, m in enumerate(plan.milestones):
                md_content += f"{idx+1}. {m}\n"
            md_content += f"\n## Phased Tasks\n"
            for t in plan.tasks:
                md_content += f"### [{t.phase}] {t.task_id}: {t.title}\n"
                md_content += f"- Priority: {t.priority.value}\n"
                md_content += f"- Duration: {t.estimated_duration}\n"
                md_content += f"- Action: {t.instructions}\n"
                md_content += f"- Deliverable: {t.expected_output}\n"
                md_content += f"- Verification: {t.completion_criteria}\n\n"

            st.download_button(
                label="📥 Download Roadmap (.md)",
                data=md_content,
                file_name=f"roadmap_{plan.plan_id.lower()}.md",
                mime="text/markdown",
                use_container_width=True
            )

# ==============================================================================
# PAGE 4: APPROVALS & EXECUTION
# ==============================================================================
elif nav == "4. 🛡️ Approvals & Execution":
    st.header("🛡️ 4. Controlled Execution & Human Gatekeeper")
    st.write("ActionBridge AI never executes consequential actions without explicit human approval.")

    if not st.session_state.plan:
        st.info("No action plan available. Generate a plan first.")
    else:
        plan = st.session_state.plan

        st.subheader("Human Authorization Gate")
        for idx, task in enumerate(plan.tasks):
            col_info, col_auth = st.columns([4, 1])
            with col_info:
                badge = "🔴 HIGH RISK" if task.risk_level == RiskLevel.HIGH else ("🟡 MEDIUM RISK" if task.risk_level == RiskLevel.MEDIUM else "🟢 LOW RISK")
                st.markdown(f"**{task.task_id}: {task.title}** &nbsp; `{badge}`")
                st.caption(f"Tool: `tools.{task.tool_name or 'None'}` &bull; Deliverable: {task.expected_output}")
            with col_auth:
                auth = st.checkbox("Authorize", value=task.is_approved, key=f"chk_auth_{task.task_id}")
                task.is_approved = auth
                if task.risk_level == RiskLevel.HIGH and not auth:
                    st.caption("🛑 Blocked until approved")

        st.markdown("---")
        if st.button("🚀 Execute Approved Pipeline", type="primary", use_container_width=True):
            st.session_state.audit_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Execution pipeline initiated.")
            progress_bar = st.progress(0)
            status_box = st.empty()

            for i, task in enumerate(plan.tasks):
                progress_bar.progress((i + 1) / len(plan.tasks))
                status_box.text(f"Processing {task.task_id}: {task.title}...")

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

            status_box.empty()
            st.success("Execution and post-condition verification complete!")
            st.rerun()

# ==============================================================================
# PAGE 5: POST-CONDITION VERIFICATION
# ==============================================================================
elif nav == "5. 🔬 Verification Audit":
    st.header("🔬 5. Independent Verification Audit")
    st.write("ActionBridge AI independently audits physical filesystem presence and SHA256 checksums.")

    if not st.session_state.plan:
        st.info("No execution data available yet.")
    else:
        plan = st.session_state.plan

        st.subheader("Physical Deliverables in Sandbox Workspace")
        sandbox_files = [f for f in WORKSPACE_DIR.glob("*") if f.is_file() and not f.name.startswith(".")]
        if not sandbox_files:
            st.info("No files generated in workspace yet.")
        else:
            file_cols = st.columns(min(len(sandbox_files), 3))
            for i, f in enumerate(sandbox_files):
                with file_cols[i % len(file_cols)]:
                    st.markdown(f"**📄 `{f.name}`**")
                    st.caption(f"Size: {f.stat().st_size} bytes")
                    with st.expander("Preview Content"):
                        try:
                            content = f.read_text(encoding="utf-8")
                            if f.name.endswith(".json"):
                                st.json(json.loads(content))
                            else:
                                st.code(content)
                        except Exception:
                            st.text("Binary or raw data")

        st.markdown("---")
        st.subheader("Audit Log & Verification Evidence")
        for task in plan.tasks:
            with st.expander(f"{task.task_id}: {task.title} &bull; Verification: {task.verification_status.value}"):
                st.write(f"**Verification Message:** {task.verification_message or 'Pending execution'}")
                if task.verification_evidence:
                    st.caption("Forensic Evidence:")
                    st.json(task.verification_evidence)

# ==============================================================================
# PAGE 6: PROGRESS DASHBOARD
# ==============================================================================
elif nav == "6. 📊 Progress Dashboard":
    st.header("📊 6. Progress Dashboard & History")

    if not st.session_state.plan:
        st.info("No active plan to display.")
    else:
        plan = st.session_state.plan
        tasks = plan.tasks

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        verified = sum(1 for t in tasks if t.verification_status == VerificationStatus.VERIFIED)
        skipped = sum(1 for t in tasks if t.status == TaskStatus.SKIPPED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)

        pct = int((completed / total * 100)) if total > 0 else 0

        # High-level metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Progress", f"{pct}%")
        m2.metric("Total Tasks", total)
        m3.metric("Completed", completed)
        m4.metric("Physically Verified 🛡️", verified)
        m5.metric("Safety Blocked 🛑", skipped)

        st.progress(pct / 100)

        st.markdown("---")
        st.subheader("📜 System Audit Terminal")
        if st.session_state.audit_log:
            st.code("\n".join(st.session_state.audit_log), language="bash")
        else:
            st.caption("No execution events logged yet.")
