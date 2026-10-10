"""
ActionBridge AI - Persistent Strategy Store
Persists formulated strategies, action plans, and execution states to local storage
so users can easily browse, reload, and switch between previous strategies.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config.settings import WORKSPACE_DIR
from core.schemas import GoalIntake, StrategicAnalysis, StrategyOption, ActionPlan

STORAGE_DIR = WORKSPACE_DIR / ".storage" / "strategies"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def save_strategy_record(
    intake: GoalIntake,
    analysis: StrategicAnalysis,
    selected_strategy: Optional[StrategyOption] = None,
    plan: Optional[ActionPlan] = None
) -> str:
    """Saves or updates a strategy record in local persistent storage."""
    goal_id = analysis.goal_id or "default"
    record_file = STORAGE_DIR / f"{goal_id}.json"

    data = {
        "goal_id": goal_id,
        "goal_title": intake.goal_title,
        "saved_at": datetime.now().isoformat(),
        "intake": intake.model_dump(),
        "analysis": analysis.model_dump(),
        "selected_strategy": selected_strategy.model_dump() if selected_strategy else None,
        "plan": plan.model_dump() if plan else None
    }

    record_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return goal_id


def list_saved_strategies() -> List[Dict[str, Any]]:
    """Returns metadata for all persisted strategies, sorted newest first."""
    records = []
    for file_path in STORAGE_DIR.glob("*.json"):
        try:
            content = json.loads(file_path.read_text(encoding="utf-8"))
            goal_id = content.get("goal_id", file_path.stem)
            plan_data = content.get("plan") or {}
            tasks = plan_data.get("tasks", [])
            completed = sum(1 for t in tasks if t.get("status") == "COMPLETED")

            records.append({
                "goal_id": goal_id,
                "goal_title": content.get("goal_title", "Untitled Strategy"),
                "selected_strategy_title": (content.get("selected_strategy") or {}).get("title") or (content.get("analysis") or {}).get("recommended_strategy_title", "Standard Approach"),
                "saved_at": content.get("saved_at", datetime.now().isoformat()),
                "total_tasks": len(tasks),
                "completed_tasks": completed,
                "file_path": str(file_path)
            })
        except Exception:
            continue

    records.sort(key=lambda r: r.get("saved_at", ""), reverse=True)
    return records


def load_strategy_record(goal_id: str) -> Optional[Tuple[GoalIntake, StrategicAnalysis, Optional[StrategyOption], Optional[ActionPlan]]]:
    """Loads and reconstructs Pydantic models from a saved strategy record."""
    record_file = STORAGE_DIR / f"{goal_id}.json"
    if not record_file.exists():
        return None

    try:
        data = json.loads(record_file.read_text(encoding="utf-8"))
        intake = GoalIntake(**data["intake"])
        analysis = StrategicAnalysis(**data["analysis"])

        selected_strategy = None
        if data.get("selected_strategy"):
            selected_strategy = StrategyOption(**data["selected_strategy"])

        plan = None
        if data.get("plan"):
            plan = ActionPlan(**data["plan"])

        return intake, analysis, selected_strategy, plan
    except Exception as e:
        print(f"[ActionBridge] Error loading strategy {goal_id}: {e}")
        return None


def delete_strategy_record(goal_id: str) -> bool:
    """Removes a strategy record from local storage."""
    record_file = STORAGE_DIR / f"{goal_id}.json"
    if record_file.exists():
        try:
            record_file.unlink()
            return True
        except Exception:
            return False
    return False
