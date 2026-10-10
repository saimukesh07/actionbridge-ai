"""
ActionBridge AI - Diagnostic & Core Feature Test Suite
Tests schema validation, strategic reasoning fallbacks, sandbox security, and post-condition verification.
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.schemas import GoalIntake, RiskLevel, TaskStatus, VerificationStatus
from core.gemini_client import GeminiReasoningClient
from tools.registry import execute_tool, _get_safe_path
from tools.verification import PostConditionVerifier


def test_schema_instantiation():
    """Verify GoalIntake model validates correctly."""
    intake = GoalIntake(
        goal_title="Deploy AI Strategy Platform",
        why_it_matters="Bridge planning with verified execution",
        deadline="2 Weeks"
    )
    assert intake.goal_title == "Deploy AI Strategy Platform"
    print("[PASS] Schema validation")


def test_adaptive_diagnostic_interview():
    """Verify diagnostic interview generates tailored questions and synthesizes intake."""
    client = GeminiReasoningClient()
    interview = client.generate_diagnostic_interview("Launch an AI coding assistant")
    assert len(interview.questions) >= 3, "Must generate at least 3 diagnostic questions"
    assert interview.questions[0].question is not None

    answers = {q.id: f"Sample response for {q.category}" for q in interview.questions}
    synthesized = client.synthesize_interview_to_intake(interview.goal_or_problem, answers)
    assert synthesized.goal_title is not None
    print(f"[PASS] Adaptive diagnostic interview: generated {len(interview.questions)} questions and synthesized intake")


def test_strategic_reasoning_and_planning():
    """Verify reasoning engine generates strategic comparison and action plan."""
    client = GeminiReasoningClient()
    intake = GoalIntake(goal_title="Scale Micro-SaaS to $10k MRR")
    analysis = client.analyze_goal(intake)
    assert len(analysis.strategies) >= 2, "Must generate at least 2 strategic options"
    assert analysis.recommended_strategy_title is not None

    rec_strategy = next((s for s in analysis.strategies if s.is_recommended), analysis.strategies[0])
    plan = client.generate_action_plan(intake, rec_strategy)
    assert len(plan.tasks) > 0, "Plan must contain concrete tasks"
    print(f"[PASS] Strategic reasoning: generated {len(analysis.strategies)} strategies and {len(plan.tasks)} tasks")



def test_sandbox_security_traversal_block():
    """Verify directory traversal is strictly blocked."""
    traversal_blocked = False
    try:
        _get_safe_path("../../windows/system32/cmd.exe")
    except PermissionError:
        traversal_blocked = True
    assert traversal_blocked, "Sandbox must block path traversal"
    print("[PASS] Sandbox containment guardrail")


def test_tool_execution_and_independent_verification():
    """Verify file writing and physical post-condition checksum verification."""
    filename = "test_artifact.txt"
    content = "ActionBridge AI Verified Output 2026"
    res = execute_tool("file_write", {"filepath": filename, "content": content, "overwrite": True})
    assert res.get("success"), "File write should succeed"

    # Audit outcome independently
    v = PostConditionVerifier.verify_task_outcome("file_write", {"filepath": filename, "content": content}, res)
    assert v["status"] == VerificationStatus.VERIFIED, "Verifier must confirm physical file on disk"
    assert "SHA256" in v["message"]
    print("[PASS] Tool execution and independent post-condition verification")


if __name__ == "__main__":
    print("=" * 60)
    print(" Running ActionBridge AI Core Test Suite")
    print("=" * 60)
    test_schema_instantiation()
    test_adaptive_diagnostic_interview()
    test_strategic_reasoning_and_planning()
    test_sandbox_security_traversal_block()
    test_tool_execution_and_independent_verification()
    print("=" * 60)
    print(" ALL DIAGNOSTIC TESTS PASSED PERFECTLY!")
    print("=" * 60)
