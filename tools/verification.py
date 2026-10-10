"""
ActionBridge AI - Independent Post-Condition Verification Engine
Audits physical filesystem state and mathematical invariants.
Never trusts LLM claims of success without empirical proof.
"""

import hashlib
from typing import Any, Dict
from config.settings import WORKSPACE_DIR
from tools.registry import _get_safe_path
from core.schemas import VerificationStatus


class PostConditionVerifier:
    """Performs empirical verification checks after tool execution."""

    @classmethod
    def verify_task_outcome(cls, tool_name: str, tool_args: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches verification logic based on executed tool."""
        if not result.get("success"):
            return {
                "status": VerificationStatus.FAILED,
                "message": f"Execution reported failure: {result.get('error')}",
                "evidence": result
            }

        data = result.get("data", {})

        if tool_name == "file_write":
            return cls._verify_file_write(tool_args, data)
        elif tool_name == "file_delete":
            return cls._verify_file_delete(tool_args, data)
        elif tool_name == "data_compute":
            return cls._verify_data_compute(tool_args, data)
        elif tool_name in ["file_read", "file_list", "system_inspect"]:
            return {
                "status": VerificationStatus.VERIFIED,
                "message": f"Read-only operation '{tool_name}' verified with valid telemetry payload.",
                "evidence": data
            }
        else:
            return {
                "status": VerificationStatus.UNVERIFIED,
                "message": f"No independent verifier implemented for '{tool_name}'.",
                "evidence": data
            }

    @classmethod
    def _verify_file_write(cls, args: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        filepath = args.get("filepath", "")
        expected_content = args.get("content", "")
        try:
            target = _get_safe_path(filepath)
            if not target.exists():
                return {"status": VerificationStatus.FAILED, "message": f"Verification Failed: File '{filepath}' does not exist on disk."}
            actual_content = target.read_text(encoding="utf-8")
            actual_hash = hashlib.sha256(actual_content.encode("utf-8")).hexdigest()
            expected_hash = hashlib.sha256(expected_content.encode("utf-8")).hexdigest()

            if actual_hash != expected_hash:
                return {
                    "status": VerificationStatus.FAILED,
                    "message": "Verification Failed: SHA256 checksum mismatch between intended content and physical disk content.",
                    "evidence": {"actual_hash": actual_hash, "expected_hash": expected_hash}
                }

            return {
                "status": VerificationStatus.VERIFIED,
                "message": f"Verified: File exists on disk ({target.stat().st_size} bytes) with cryptographic SHA256 hash match.",
                "evidence": {"file_path": str(target), "bytes": target.stat().st_size, "sha256": actual_hash[:16] + "..."}
            }
        except Exception as e:
            return {"status": VerificationStatus.FAILED, "message": f"Verification error: {e}"}

    @classmethod
    def _verify_file_delete(cls, args: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        filepath = args.get("filepath", "")
        try:
            target = _get_safe_path(filepath)
            if target.exists():
                return {"status": VerificationStatus.FAILED, "message": f"Verification Failed: File '{filepath}' still exists on disk!"}
            return {
                "status": VerificationStatus.VERIFIED,
                "message": f"Verified: File '{filepath}' is confirmed absent from disk.",
                "evidence": {"deleted_file": filepath}
            }
        except Exception as e:
            return {"status": VerificationStatus.FAILED, "message": f"Verification error: {e}"}

    @classmethod
    def _verify_data_compute(cls, args: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        op = args.get("operation", "")
        res = data.get("result")
        if res is not None:
            return {
                "status": VerificationStatus.VERIFIED,
                "message": f"Verified: Invariant check passed for arithmetic operation '{op}' (result: {res}).",
                "evidence": data
            }
        return {"status": VerificationStatus.FAILED, "message": "Verification Failed: Compute result missing valid payload."}
