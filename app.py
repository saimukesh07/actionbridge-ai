"""
ActionBridge AI - Strategic Planning & Verified Execution Platform
Streamlit Frontend integrating Goal Intake, Gemini Strategic Analysis,
Controlled Sandbox Execution, and Independent Post-Condition Verification.
"""

import json
from datetime import datetime
import streamlit as st

from config.settings import WORKSPACE_DIR, is_gemini_configured, GEMINI_MODEL
from core.schemas import (
    GoalIntake,
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
    if is_gemini_configured():
        st.success(f"🟢 Gemini Live ({GEMINI_MODEL})")
    else:
        st.info("🟡 Local Demo Mode (Deterministic Fallback)")
    st.caption(f"Sandbox: `{WORKSPACE_DIR.name}/`")

    if st.button("🔄 Reset Session", use_container_width=True):
        st.session_state.intake = None
        st.session_state.analysis = None
        st.session_state.selected_strategy = None
        st.session_state.plan = None
        st.session_state.audit_log = []
        st.rerun()

# ==============================================================================
# PAGE 1: GOAL INTAKE
# ==============================================================================
if nav == "1. 🎯 Goal Intake":
    st.header("🎯 1. Structured Goal Intake")
    st.write("Define what you want to achieve, your constraints, and success criteria.")

    preset_choice = st.selectbox(
        "Select a quick template or enter a custom goal:",
        [
            "Custom Goal",
            "Launch an AI-Powered Micro-SaaS MVP in 4 Weeks",
            "Transition into Senior AI Engineer Role in 6 Months",
            "Build an Autonomous Academic Grading & Reporting Pipeline"
        ]
    )

    defaults = {
        "title": "Build and launch an AI-powered SaaS product",
        "why": "Achieve financial independence and solve a high-value developer workflow challenge.",
        "current": "Have basic prototypes and market research, but lack a clear roadmap and automated pipelines.",
        "desired": "Production app with 100 active beta users and verifiable delivery pipelines.",
        "deadline": "4 Weeks",
        "resources": "10-15 hours/week, Python knowledge, cloud credits.",
        "constraints": "Bootstrapped budget, solo execution, time limited by day job.",
        "metrics": "Working deployed MVP, automated test coverage > 80%, 100 beta signups."
    }

    if preset_choice != "Custom Goal":
        defaults["title"] = preset_choice

    with st.form("goal_intake_form"):
        col1, col2 = st.columns(2)
        with col1:
            g_title = st.text_input("What is your goal?", value=defaults["title"])
            g_why = st.text_area("Why does this goal matter?", value=defaults["why"], height=80)
            g_current = st.text_area("What is your current situation?", value=defaults["current"], height=80)
            g_desired = st.text_area("What is your desired outcome?", value=defaults["desired"], height=80)
        with col2:
            g_deadline = st.text_input("What is your deadline?", value=defaults["deadline"])
            g_resources = st.text_area("Available time, budget, and resources:", value=defaults["resources"], height=80)
            g_constraints = st.text_area("Key constraints or limitations:", value=defaults["constraints"], height=80)
            g_metrics = st.text_area("How will success be measured?", value=defaults["metrics"], height=80)

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
                # Automatically select recommended strategy
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
            st.warning("ℹ️ Showing deterministic offline demonstration analysis. Add GEMINI_API_KEY to .env for live Gemini 2.5 reasoning.")

        st.subheader(f"Strategy Brief: {analysis.goal_title}")
        st.markdown(f"**Problem Definition:** {analysis.problem_definition}")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### 📍 Current State")
            st.info(analysis.current_state_assessment)
            st.markdown("#### 🔍 Key Assumptions")
            for asm in analysis.key_assumptions:
                st.write(f"- {asm}")

        with col_b:
            st.markdown("#### 🎯 Desired Future State")
            st.success(analysis.desired_future_state)
            st.markdown("#### ⚠️ Root Cause & Bottlenecks")
            st.write(analysis.root_cause_analysis)

        st.markdown("---")
        st.subheader("⚖️ Strategy Comparison")
        st.write("Compare alternative paths evaluated against feasibility, impact, and reversibility:")

        strat_cols = st.columns(len(analysis.strategies))
        for idx, strat in enumerate(analysis.strategies):
            with strat_cols[idx]:
                st.markdown(f"### {strat.title}")
                if strat.is_recommended:
                    st.success("🌟 Recommended Approach")
                st.write(strat.overview)
                st.metric("Feasibility", f"{strat.feasibility_score}/10")
                st.metric("Expected Impact", f"{strat.impact_score}/10")
                st.caption(f"Cost: **{strat.estimated_cost}** | Time: **{strat.estimated_time}** | Reversibility: **{strat.reversibility}**")

                st.markdown("**Pros:**")
                for p in strat.pros:
                    st.write(f"✓ {p}")
                st.markdown("**Cons:**")
                for c in strat.cons:
                    st.write(f"✕ {c}")

                if st.button(f"Select Strategy {idx+1}", key=f"btn_strat_{idx}", use_container_width=True):
                    st.session_state.selected_strategy = strat
                    with st.spinner("Generating detailed action plan..."):
                        plan = st.session_state.client.generate_action_plan(st.session_state.intake, strat)
                        st.session_state.plan = plan
                    st.success(f"Selected: {strat.title}! Action plan generated.")
                    st.rerun()

# ==============================================================================
# PAGE 3: ACTION PLAN
# ==============================================================================
elif nav == "3. 📋 Action Plan":
    st.header("📋 3. Action Plan & Roadmap")

    if not st.session_state.plan:
        st.info("No action plan generated yet. Complete Goal Intake to create one.")
    else:
        plan = st.session_state.plan
        st.subheader(f"Plan: {plan.goal_title}")
        st.caption(f"Strategy: **{plan.selected_strategy_title}** &bull; Plan ID: `{plan.plan_id}`")
        st.write(plan.strategic_summary)

        st.markdown("#### 🚩 Success Milestones")
        m_cols = st.columns(len(plan.milestones))
        for idx, m in enumerate(plan.milestones):
            with m_cols[idx]:
                st.info(m)

        st.markdown("---")
        st.subheader("📝 Actionable Task Breakdown")

        for task in plan.tasks:
            risk_badge = "🟢 LOW RISK" if task.risk_level == RiskLevel.LOW else ("🟡 MEDIUM RISK" if task.risk_level == RiskLevel.MEDIUM else "🔴 HIGH RISK (CONSEQUENTIAL)")
            status_color = "gray" if task.status == TaskStatus.PENDING else ("green" if task.status == TaskStatus.COMPLETED else "red")

            with st.expander(f"{task.task_id}: {task.title} &bull; [{task.priority.value}] &bull; {risk_badge}", expanded=True):
                col_t1, col_t2 = st.columns([3, 1])
                with col_t1:
                    st.write(f"**Phase:** {task.phase}")
                    st.write(f"**Instructions:** {task.instructions}")
                    if task.tool_name:
                        st.caption(f"🔧 Tool Call: `tools.{task.tool_name}` &bull; Args: `{json.dumps(task.tool_args)}`")
                    st.caption(f"Expected Output: *{task.expected_output}* &bull; Duration: {task.estimated_duration}")
                with col_t2:
                    st.write(f"Status: **{task.status.value}**")
                    st.write(f"Risk Reason: *{task.risk_reason}*")
                    if task.risk_level == RiskLevel.HIGH and not task.is_approved:
                        st.warning("Requires explicit user approval before execution")

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
