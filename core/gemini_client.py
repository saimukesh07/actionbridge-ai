"""
ActionBridge AI - Gemini Client & Reasoning Core
Interacts with Google Gemini using google-genai SDK with structured Pydantic schemas.
Includes automatic deterministic demo fallback for local testing without an active API key.
"""

import json
import uuid
from typing import Optional
from datetime import datetime

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from config.settings import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_FALLBACK_MODELS, is_gemini_configured
from core.schemas import (
    GoalIntake,
    StrategicAnalysis,
    StrategyOption,
    ActionPlan,
    PlanTask,
    RiskLevel,
    TaskPriority,
    TaskStatus,
)


class GeminiReasoningClient:
    """Orchestrates Gemini AI strategic decomposition and planning."""

    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model_name = GEMINI_MODEL
        self.client: Optional[Any] = None

        if HAS_GENAI and is_gemini_configured():
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[ActionBridge] Warning: Gemini Client initialization failed: {e}")
                self.client = None

    def analyze_goal(self, intake: GoalIntake) -> StrategicAnalysis:
        """Generates comprehensive strategic analysis comparing multiple strategic options."""
        if not self.client:
            return self._generate_fallback_analysis(intake)

        prompt = f"""You are the ActionBridge AI Strategic Reasoning Core.
Analyze the following user goal thoroughly:
- Goal: {intake.goal_title}
- Why it matters: {intake.why_it_matters}
- Current situation: {intake.current_situation}
- Desired outcome: {intake.desired_outcome}
- Deadline: {intake.deadline}
- Available resources: {intake.available_resources}
- Constraints: {intake.constraints}
- Success metrics: {intake.success_metrics}

Generate a comprehensive strategic analysis in strictly valid JSON conforming to the StrategicAnalysis schema:
- problem_definition
- current_state_assessment
- desired_future_state
- key_assumptions (list of strings)
- root_cause_analysis
- opportunities (list of strings)
- constraints_analysis
- strategies: Provide 2 or 3 distinct StrategyOption objects (strategy_id, title, overview, pros, cons, feasibility_score 1-10, impact_score 1-10, estimated_cost, estimated_time, reversibility, is_recommended).
- recommended_strategy_title
- rationale_for_recommendation
- major_risks_and_mitigations: list of dicts with keys 'risk' and 'mitigation'
- success_milestones: list of 3-5 milestone strings
Return ONLY JSON.
"""
        models_to_try = [self.model_name] + [m for m in GEMINI_FALLBACK_MODELS if m != self.model_name]
        for model in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        response_mime_type="application/json"
                    )
                )
                if response and response.text:
                    data = json.loads(response.text.strip())
                    data["goal_id"] = str(uuid.uuid4())[:8]
                    data["goal_title"] = intake.goal_title
                    data["is_demo"] = False
                    return StrategicAnalysis(**data)
            except Exception as e:
                print(f"[ActionBridge] Gemini analysis attempt with {model} failed: {e}")
                continue

        return self._generate_fallback_analysis(intake)

    def generate_action_plan(self, intake: GoalIntake, selected_strategy: StrategyOption) -> ActionPlan:
        """Converts chosen strategy into an auditable, phased action plan."""
        if not self.client:
            return self._generate_fallback_plan(intake, selected_strategy)

        prompt = f"""You are the ActionBridge AI Action Planning Core.
Decompose the selected strategy into concrete, auditable execution tasks.
Goal: {intake.goal_title}
Selected Strategy: {selected_strategy.title} - {selected_strategy.overview}

PERMITTED EXECUTION TOOLS:
- file_write: args: {{"filepath": str, "content": str, "overwrite": bool}} (Medium/High risk)
- file_read: args: {{"filepath": str}} (Low risk)
- file_list: args: {{"directory": str}} (Low risk)
- file_delete: args: {{"filepath": str}} (High risk - requires approval)
- data_compute: args: {{"operation": "count"|"sum"|"mean", "numbers": list}} (Low risk)
- system_inspect: args: {{"query": "workspace_health"}} (Low risk)

Return strictly valid JSON conforming to the ActionPlan schema:
- strategic_summary: One paragraph
- milestones: List of 3-4 milestone strings
- tasks: List of PlanTask objects:
  - task_id (e.g. TASK-01)
  - title (short 3-5 words)
  - instructions (concrete, non-vague steps)
  - priority ("CRITICAL", "HIGH", "MEDIUM", "LOW")
  - phase ("Phase 1: Setup", "Phase 2: Execution", "Phase 3: Verification")
  - estimated_duration
  - tool_name (optional tool from permitted list)
  - tool_args (dict of arguments matching schema)
  - expected_output (physical deliverable)
  - completion_criteria (how success is tested)
  - risk_level ("LOW", "MEDIUM", "HIGH" - mark file deletes or overwrites as HIGH)
  - risk_reason (why this risk tier was selected)
Return ONLY JSON.
"""
        models_to_try = [self.model_name] + [m for m in GEMINI_FALLBACK_MODELS if m != self.model_name]
        for model in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )
                if response and response.text:
                    data = json.loads(response.text.strip())
                    data["plan_id"] = f"PLAN-{str(uuid.uuid4())[:6].upper()}"
                    data["goal_title"] = intake.goal_title
                    data["selected_strategy_title"] = selected_strategy.title
                    data["is_demo"] = False
                    return ActionPlan(**data)
            except Exception as e:
                print(f"[ActionBridge] Gemini planning attempt with {model} failed: {e}")
                continue

        return self._generate_fallback_plan(intake, selected_strategy)

    def _generate_fallback_analysis(self, intake: GoalIntake) -> StrategicAnalysis:
        """Deterministic, comprehensive strategic analysis for local offline testing."""
        strat1 = StrategyOption(
            strategy_id="STRAT-01",
            title="Fast-Track MVP & Incremental Validation",
            overview="Focus immediately on the core deliverable using modular, lightweight tools. Test milestones weekly to uncover blockers early.",
            pros=["Rapid time-to-market", "Low upfront resource expenditure", "Highly reversible"],
            cons=["Requires sharp prioritization", "Initial feature set is lean"],
            feasibility_score=9,
            impact_score=8,
            estimated_cost="Low",
            estimated_time="2-4 Weeks",
            reversibility="High",
            is_recommended=True
        )
        strat2 = StrategyOption(
            strategy_id="STRAT-02",
            title="Comprehensive Upfront Architecture",
            overview="Build exhaustive infrastructure, end-to-end schemas, and broad tooling upfront before starting rollout.",
            pros=["Complete system predictability", "Handles edge cases from day one"],
            cons=["High initial time investment", "Higher risk if requirements evolve"],
            feasibility_score=6,
            impact_score=9,
            estimated_cost="Medium",
            estimated_time="6-10 Weeks",
            reversibility="Medium",
            is_recommended=False
        )
        return StrategicAnalysis(
            goal_id=str(uuid.uuid4())[:8],
            goal_title=intake.goal_title,
            problem_definition=f"Addressing core challenge: {intake.goal_title}. Current gap lies in converting intent into concrete execution without excessive overhead.",
            current_state_assessment=intake.current_situation or "Baseline initialization: Requirements defined, initial resources available.",
            desired_future_state=intake.desired_outcome or "Target outcome: Goal achieved with verifiable deliverables and measurable progress.",
            key_assumptions=[
                "User has allocated dedicated weekly focus hours",
                "Execution tools operate within authorized local sandbox",
                "Key milestones can be verified independently"
            ],
            root_cause_analysis="Execution bottlenecks usually stem from vague tasks, lack of verification boundaries, and premature optimization.",
            opportunities=["Leverage automated execution tools", "Enforce auditable proof for each completed phase"],
            constraints_analysis=intake.constraints or "Standard timeline and resource constraints.",
            strategies=[strat1, strat2],
            recommended_strategy_title=strat1.title,
            rationale_for_recommendation="The Fast-Track MVP delivers measurable progress immediately while preserving high flexibility to pivot.",
            major_risks_and_mitigations=[
                {"risk": "Scope creep during early rollout", "mitigation": "Strict milestone checklists and explicit task definitions."},
                {"risk": "Unverified assumptions", "mitigation": "Post-condition verification engine validates outcomes after each step."}
            ],
            success_milestones=[
                "Milestone 1: Environment & Goal Baseline Established",
                "Milestone 2: Core Deliverable Authored & Physically Audited",
                "Milestone 3: Final Verification & Outcome Certification"
            ],
            is_demo=True
        )

    def _generate_fallback_plan(self, intake: GoalIntake, strategy: StrategyOption) -> ActionPlan:
        """Deterministic, auditable action plan with tool assignments."""
        tasks = [
            PlanTask(
                task_id="TASK-01",
                title="Sandbox Environment Diagnostic",
                instructions="Inspect the workspace sandbox directory and verify system telemetry.",
                priority=TaskPriority.HIGH,
                phase="Phase 1: Foundation",
                estimated_duration="5 mins",
                tool_name="system_inspect",
                tool_args={"query": "workspace_health"},
                expected_output="Environment telemetry and active file tally",
                completion_criteria="Sandbox exists and reports healthy status",
                risk_level=RiskLevel.LOW,
                risk_reason="Read-only diagnostic inspection",
                status=TaskStatus.PENDING,
                is_approved=True
            ),
            PlanTask(
                task_id="TASK-02",
                title="Project Specification Document",
                instructions="Author a structured project execution brief (project_spec.md) in the sandbox workspace.",
                priority=TaskPriority.CRITICAL,
                phase="Phase 1: Foundation",
                estimated_duration="15 mins",
                tool_name="file_write",
                tool_args={
                    "filepath": "project_spec.md",
                    "content": f"# Project Execution Specification\n\n**Goal**: {intake.goal_title}\n**Strategy**: {strategy.title}\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n## Scope\n- Deliver tangible outcomes verifiably.\n- Document all key milestones.\n",
                    "overwrite": True
                },
                expected_output="project_spec.md authored on disk",
                completion_criteria="File written and verified with cryptographic SHA256 checksum",
                risk_level=RiskLevel.MEDIUM,
                risk_reason="Creates a new specification file in sandbox",
                status=TaskStatus.PENDING,
                is_approved=True
            ),
            PlanTask(
                task_id="TASK-03",
                title="Milestone Metric Calculation",
                instructions="Calculate initial task estimates and statistical distribution.",
                priority=TaskPriority.MEDIUM,
                phase="Phase 2: Execution",
                estimated_duration="5 mins",
                tool_name="data_compute",
                tool_args={"operation": "mean", "numbers": [10.0, 25.0, 35.0, 50.0]},
                expected_output="Deterministic mathematical average: 30.0",
                completion_criteria="Calculation verifies arithmetic invariants without side-effects",
                risk_level=RiskLevel.LOW,
                risk_reason="Pure calculation with zero filesystem side-effects",
                status=TaskStatus.PENDING,
                is_approved=True
            ),
            PlanTask(
                task_id="TASK-04",
                title="Export Certified Deliverable",
                instructions="Compile and persist final verified milestone report (deliverable_summary.json).",
                priority=TaskPriority.HIGH,
                phase="Phase 3: Verification",
                estimated_duration="10 mins",
                tool_name="file_write",
                tool_args={
                    "filepath": "deliverable_summary.json",
                    "content": json.dumps({
                        "goal": intake.goal_title,
                        "strategy": strategy.title,
                        "status": "COMPLETED_AND_VERIFIED",
                        "timestamp": datetime.now().isoformat()
                    }, indent=2),
                    "overwrite": True
                },
                expected_output="deliverable_summary.json verified on disk",
                completion_criteria="File physically exists with matching content hash",
                risk_level=RiskLevel.HIGH,
                risk_reason="CONSEQUENTIAL: Overwrites milestone deliverable; requires human authorization",
                status=TaskStatus.AWAITING_APPROVAL,
                is_approved=False
            )
        ]

        return ActionPlan(
            plan_id=f"DEMO-{str(uuid.uuid4())[:6].upper()}",
            goal_title=intake.goal_title,
            selected_strategy_title=strategy.title,
            strategic_summary=f"Actionable roadmap operationalizing '{strategy.title}'. Contains 4 auditable tasks with human-in-the-loop approval barriers.",
            milestones=[
                "1. Establish verified workspace baseline",
                "2. Author project specification artifact",
                "3. Compute resource and milestone distribution",
                "4. Export and verify final deliverable"
            ],
            tasks=tasks,
            is_demo=True
        )
