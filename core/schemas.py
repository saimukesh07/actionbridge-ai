"""
ActionBridge AI - Core Schemas & Data Models
Pydantic definitions for Goal Intake, Strategic Analysis, Action Plans, Tasks, and Verification.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"        # Safe, read-only, deterministic calculations
    MEDIUM = "MEDIUM"  # Creating non-critical new files without overwriting
    HIGH = "HIGH"      # Consequential: overwriting files, deletion, external alerts


class TaskPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"
    SKIPPED = "SKIPPED"


class DiagnosticQuestion(BaseModel):
    """An individual adaptive question generated to clarify a vague or custom goal."""
    id: str  # e.g. "q1", "q2"
    question: str
    why_it_matters: str
    category: str = "Constraints"  # "Experience", "Timeline", "Resources", "Risks", "Success Criteria"
    suggested_placeholder: str = ""


class DiagnosticInterview(BaseModel):
    """Collection of dynamic questions tailored to the user's specific custom goal."""
    goal_or_problem: str
    questions: List[DiagnosticQuestion] = Field(default_factory=list)


class GoalIntake(BaseModel):
    """User input capturing context, constraints, and success criteria."""
    goal_title: str
    why_it_matters: str = ""
    current_situation: str = ""
    desired_outcome: str = ""
    deadline: str = ""
    available_resources: str = ""
    constraints: str = ""
    success_metrics: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class StrategyOption(BaseModel):
    """An individual strategic approach for comparison."""
    strategy_id: str
    title: str
    overview: str
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    feasibility_score: int = Field(default=8, ge=1, le=10)
    impact_score: int = Field(default=8, ge=1, le=10)
    estimated_cost: str = "Low"
    estimated_time: str = "Medium"
    reversibility: str = "High"
    is_recommended: bool = False


class StrategicAnalysis(BaseModel):
    """Comprehensive strategic breakdown produced by AI reasoning."""
    goal_id: str
    goal_title: str
    problem_definition: str
    current_state_assessment: str
    desired_future_state: str
    key_assumptions: List[str] = Field(default_factory=list)
    root_cause_analysis: str = ""
    opportunities: List[str] = Field(default_factory=list)
    constraints_analysis: str = ""
    strategies: List[StrategyOption] = Field(default_factory=list)
    recommended_strategy_title: str
    rationale_for_recommendation: str
    major_risks_and_mitigations: List[Dict[str, str]] = Field(default_factory=list)
    success_milestones: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_demo: bool = False


class PlanTask(BaseModel):
    """Concrete, auditable unit of execution."""
    task_id: str
    title: str
    instructions: str
    priority: TaskPriority = TaskPriority.MEDIUM
    phase: str = "Phase 1: Foundation"
    estimated_duration: str = "1 day"
    required_resources: str = ""
    dependencies: List[str] = Field(default_factory=list)
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = Field(default_factory=dict)
    resolved_args: Optional[Dict[str, Any]] = None
    expected_output: str = ""
    completion_criteria: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    risk_reason: str = "Standard safe operation"
    status: TaskStatus = TaskStatus.PENDING
    is_approved: bool = False
    execution_result: Optional[Dict[str, Any]] = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verification_message: Optional[str] = None
    verification_evidence: Optional[Dict[str, Any]] = None


class ActionPlan(BaseModel):
    """Structured, verifiable plan derived from the chosen strategy."""
    plan_id: str
    goal_title: str
    selected_strategy_title: str
    strategic_summary: str
    milestones: List[str] = Field(default_factory=list)
    tasks: List[PlanTask] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_demo: bool = False
