"""
ActionBridge AI - Output Formatting & Human-Readable Transformers
Transforms raw tool calls, escaped JSON payloads, and unicode artifacts
into concise, polished, human-readable UI summaries.
"""

import json
from typing import Any, Dict, Optional


def clean_text(text: Optional[str]) -> str:
    """Cleans Unicode artifacts, non-breaking hyphens, and unescaped newlines."""
    if not text:
        return ""
    # Normalize non-breaking hyphens and unicode spaces
    cleaned = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "--")
    cleaned = cleaned.replace("\u00a0", " ")
    return cleaned.strip()


def format_tool_action(tool_name: Optional[str], tool_args: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Transforms raw technical tool payloads into clean, human-readable summaries.
    Hides raw arguments from the primary view while keeping technical details inspectable.
    """
    args = tool_args or {}

    if not tool_name:
        return {
            "title": "Manual Strategy Step",
            "file": None,
            "action_summary": "Direct strategic step performed by user (no automated filesystem side-effects).",
            "is_automated": False,
            "preview_content": None,
            "raw_args": args
        }

    if tool_name == "file_write":
        filepath = clean_text(args.get("filepath", "output_document.md"))
        content = args.get("content", "")
        return {
            "title": f"Create Document ({filepath})",
            "file": filepath,
            "action_summary": f"Create Markdown document '{filepath}' in authorized sandbox workspace.",
            "is_automated": True,
            "preview_content": content,
            "raw_args": args
        }

    elif tool_name == "file_read":
        filepath = clean_text(args.get("filepath", "file.txt"))
        return {
            "title": f"Read File ({filepath})",
            "file": filepath,
            "action_summary": f"Inspect physical file '{filepath}' in sandbox workspace.",
            "is_automated": True,
            "preview_content": None,
            "raw_args": args
        }

    elif tool_name == "file_list":
        directory = clean_text(args.get("directory", "workspace/"))
        return {
            "title": "Scan Workspace Files",
            "file": None,
            "action_summary": f"Scan directory contents in '{directory or 'workspace/'}'.",
            "is_automated": True,
            "preview_content": None,
            "raw_args": args
        }

    elif tool_name == "file_delete":
        filepath = clean_text(args.get("filepath", "file.txt"))
        return {
            "title": f"Delete File ({filepath})",
            "file": filepath,
            "action_summary": f"Permanently remove file '{filepath}' from sandbox workspace (consequential action).",
            "is_automated": True,
            "preview_content": None,
            "raw_args": args
        }

    elif tool_name == "data_compute":
        op = clean_text(args.get("operation", "compute"))
        count = len(args.get("numbers", []))
        return {
            "title": f"Calculate {op.title()}",
            "file": None,
            "action_summary": f"Perform mathematical calculation ('{op}') across {count} data values.",
            "is_automated": True,
            "preview_content": json.dumps(args.get("numbers", []), indent=2),
            "raw_args": args
        }

    elif tool_name == "system_inspect":
        query = clean_text(args.get("query", "workspace_health"))
        return {
            "title": "System Environment Diagnostic",
            "file": None,
            "action_summary": f"Verify sandbox directory status and execution environment ({query}).",
            "is_automated": True,
            "preview_content": None,
            "raw_args": args
        }

    return {
        "title": f"Execute {tool_name}",
        "file": args.get("filepath"),
        "action_summary": f"Run automated tool '{tool_name}' within sandbox environment.",
        "is_automated": True,
        "preview_content": None,
        "raw_args": args
    }


def generate_markdown_roadmap(analysis, plan) -> str:
    """Builds a beautifully structured Markdown document ready for export."""
    if not plan:
        return ""

    md = []
    md.append(f"# ActionBridge AI Strategic Roadmap: {plan.goal_title}")
    md.append(f"\n**Selected Strategy:** {plan.selected_strategy_title}")
    md.append(f"**Plan ID:** {plan.plan_id}")
    md.append(f"**Generated:** {plan.created_at[:10] if hasattr(plan, 'created_at') else 'Recent'}")
    md.append("\n---\n")

    md.append("## 1. Executive Summary")
    md.append(clean_text(plan.strategic_summary))
    md.append("")

    if analysis:
        md.append("## 2. Situation Diagnosis & Baseline")
        md.append(f"- **Current State:** {clean_text(analysis.current_state_assessment)}")
        md.append(f"- **Desired Future State:** {clean_text(analysis.desired_future_state)}")
        md.append(f"- **Core Bottleneck:** {clean_text(analysis.root_cause_analysis)}")
        md.append("")

    md.append("## 3. Success Milestones")
    for idx, m in enumerate(plan.milestones):
        md.append(f"{idx+1}. {clean_text(m)}")
    md.append("")

    md.append("## 4. Phased Task Breakdown")
    phases = {}
    for t in plan.tasks:
        phases.setdefault(t.phase or "Phase 1: Foundation", []).append(t)

    for phase_name, p_tasks in phases.items():
        md.append(f"### {phase_name}")
        for t in p_tasks:
            info = format_tool_action(t.tool_name, t.tool_args)
            md.append(f"#### [{t.priority.value}] {t.task_id}: {clean_text(t.title)}")
            md.append(f"- **Action:** {clean_text(t.instructions)}")
            md.append(f"- **Deliverable:** {clean_text(t.expected_output)}")
            md.append(f"- **Estimated Time:** {clean_text(t.estimated_duration)}")
            md.append(f"- **Risk Level:** {t.risk_level.value}")
            md.append(f"- **Execution:** {info['action_summary']}")
            md.append("")

    if analysis and analysis.major_risks_and_mitigations:
        md.append("## 5. Risk & Pre-Emptive Defense Playbook")
        for idx, r in enumerate(analysis.major_risks_and_mitigations):
            md.append(f"### Threat #{idx+1}: {clean_text(r.get('risk', ''))}")
            md.append(f"- **Defense / Mitigation:** {clean_text(r.get('mitigation', ''))}")
            md.append("")

    return "\n".join(md)
