"""
ActionBridge AI - Controlled Tool Registry & Sandbox Containment
Only explicitly allowlisted tools can be executed.
All filesystem operations are strictly sandboxed inside WORKSPACE_DIR.
"""

import os
import hashlib
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from config.settings import WORKSPACE_DIR
from core.schemas import RiskLevel


def _get_safe_path(user_path: str) -> Path:
    """Ensures paths resolve strictly inside WORKSPACE_DIR, blocking directory traversal."""
    cleaned = Path(user_path).as_posix().lstrip("/")
    target = (WORKSPACE_DIR / cleaned).resolve()
    try:
        target.relative_to(WORKSPACE_DIR)
    except ValueError:
        raise PermissionError(f"Security Alert: Path '{user_path}' escapes sandbox workspace.")
    return target


def file_write(filepath: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    """Writes text content to a sandboxed file."""
    try:
        target = _get_safe_path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        existed_before = target.exists()

        if existed_before and not overwrite:
            return {"success": False, "error": f"File '{filepath}' already exists and overwrite=False."}

        target.write_text(content, encoding="utf-8")
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

        return {
            "success": True,
            "data": {
                "filepath": filepath,
                "bytes_written": len(content.encode("utf-8")),
                "sha256": checksum,
                "existed_before": existed_before
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def file_read(filepath: str) -> Dict[str, Any]:
    """Reads content from a sandboxed file."""
    try:
        target = _get_safe_path(filepath)
        if not target.exists():
            return {"success": False, "error": f"File '{filepath}' does not exist."}
        content = target.read_text(encoding="utf-8")
        return {"success": True, "data": {"filepath": filepath, "content": content, "lines": len(content.splitlines())}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def file_list(directory: str = ".") -> Dict[str, Any]:
    """Lists files inside the sandbox workspace."""
    try:
        target_dir = _get_safe_path(directory)
        if not target_dir.exists() or not target_dir.is_dir():
            return {"success": False, "error": f"Directory '{directory}' does not exist."}
        files = []
        for item in target_dir.rglob("*"):
            if item.is_file() and not item.name.startswith("."):
                rel = item.relative_to(WORKSPACE_DIR)
                files.append({"name": item.name, "path": str(rel), "size_bytes": item.stat().st_size})
        return {"success": True, "data": {"files": files, "count": len(files)}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def file_delete(filepath: str) -> Dict[str, Any]:
    """Deletes a file inside the sandbox. HIGH RISK."""
    try:
        target = _get_safe_path(filepath)
        if not target.exists():
            return {"success": False, "error": f"File '{filepath}' does not exist to delete."}
        if target.is_dir():
            return {"success": False, "error": "Directory deletion is prohibited."}
        target.unlink()
        return {"success": True, "data": {"deleted_file": filepath, "status": "DELETED"}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def data_compute(operation: str, numbers: List[float]) -> Dict[str, Any]:
    """Performs deterministic mathematical calculations without arbitrary code execution."""
    try:
        op = operation.lower().strip()
        if not numbers:
            return {"success": False, "error": "data_compute requires a non-empty list of numbers."}

        if op == "sum":
            res = float(sum(numbers))
        elif op == "mean":
            res = float(statistics.mean(numbers))
        elif op == "min":
            res = float(min(numbers))
        elif op == "max":
            res = float(max(numbers))
        elif op == "count":
            res = float(len(numbers))
        else:
            return {"success": False, "error": f"Unsupported operation: '{op}'."}

        return {"success": True, "data": {"operation": op, "result": round(res, 4), "count": len(numbers)}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def system_inspect(query: str = "workspace_health") -> Dict[str, Any]:
    """Inspects sandbox workspace status and file inventory."""
    try:
        visible = [f for f in WORKSPACE_DIR.glob("*") if f.is_file() and not f.name.startswith(".")]
        return {
            "success": True,
            "data": {
                "workspace_path": str(WORKSPACE_DIR),
                "file_count": len(visible),
                "total_size_bytes": sum(f.stat().st_size for f in visible),
                "healthy": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


TOOL_REGISTRY = {
    "file_write": (file_write, RiskLevel.MEDIUM),
    "file_read": (file_read, RiskLevel.LOW),
    "file_list": (file_list, RiskLevel.LOW),
    "file_delete": (file_delete, RiskLevel.HIGH),
    "data_compute": (data_compute, RiskLevel.LOW),
    "system_inspect": (system_inspect, RiskLevel.LOW),
}


def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """Validates and executes an allowlisted tool."""
    if tool_name not in TOOL_REGISTRY:
        return {"success": False, "error": f"Security Block: Tool '{tool_name}' is not in the allowlisted registry."}
    fn, _ = TOOL_REGISTRY[tool_name]
    try:
        return fn(**tool_args)
    except TypeError as te:
        return {"success": False, "error": f"Invalid arguments for tool '{tool_name}': {te}"}
    except Exception as e:
        return {"success": False, "error": f"Tool execution failed: {e}"}
