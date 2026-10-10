"""
ActionBridge AI - Strategic Reasoning Core (Multi-Provider: Groq + Gemini)
Supports Google Gemini and Groq (Llama / Qwen / GPT-OSS) with automatic fallback.
Generates dynamic diagnostic interviews, strategic comparisons, and verifiable action plans.
"""

import os
import json
import uuid
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

import requests

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_FALLBACK_MODELS,
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_FALLBACK_MODELS,
    is_gemini_configured,
    is_groq_configured,
    is_ai_configured,
    get_active_ai_provider,
)
from core.schemas import (
    DiagnosticQuestion,
    DiagnosticInterview,
    GoalIntake,
    StrategicAnalysis,
    StrategyOption,
    ActionPlan,
    PlanTask,
    RiskLevel,
    TaskPriority,
    TaskStatus,
    YouTubeVideoContext,
)


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extracts and parses JSON from raw LLM output, handling markdown blocks."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1:
        cleaned = cleaned[first_brace:last_brace + 1]

    try:
        return json.loads(cleaned)
    except Exception:
        # Try finding array or secondary cleanups
        try:
            cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)
            return json.loads(cleaned)
        except Exception:
            return None


def _normalize_intake_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures string fields in GoalIntake are valid strings even if LLM returns lists or dicts."""
    if not isinstance(data, dict):
        return {}
    string_fields = [
        "goal_title",
        "why_it_matters",
        "current_situation",
        "desired_outcome",
        "deadline",
        "available_resources",
        "constraints",
        "success_metrics"
    ]
    for field in string_fields:
        val = data.get(field)
        if isinstance(val, list):
            data[field] = " \u2022 ".join([str(item).strip() for item in val if item])
        elif isinstance(val, dict):
            data[field] = json.dumps(val)
        elif val is None:
            data[field] = ""
        else:
            data[field] = str(val).strip()
    return data


class GeminiReasoningClient:
    """Orchestrates multi-provider (Groq & Gemini) strategic reasoning and adaptive interviews."""

    def __init__(self):
        self.gemini_client = None
        if HAS_GENAI and is_gemini_configured():
            try:
                self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                print(f"[ActionBridge] Gemini init notice: {e}")

    def call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Optional[str]:
        """Calls Groq or Gemini with automatic provider fallback."""
        # 1. Try Groq if configured
        if is_groq_configured():
            models = [GROQ_MODEL] + [m for m in GROQ_FALLBACK_MODELS if m != GROQ_MODEL]
            for model in models:
                try:
                    payload = {
                        "model": model,
                        "temperature": temperature,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    }
                    headers = {
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    res = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    if res.status_code == 200:
                        data = res.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "")
                except Exception as e:
                    print(f"[ActionBridge] Groq model {model} error: {e}")
                    continue

        # 2. Try Gemini if configured
        if self.gemini_client:
            models = [GEMINI_MODEL] + [m for m in GEMINI_FALLBACK_MODELS if m != GEMINI_MODEL]
            for model in models:
                try:
                    full_prompt = f"{system_prompt}\n\nUser Request:\n{user_prompt}"
                    response = self.gemini_client.models.generate_content(
                        model=model,
                        contents=full_prompt,
                        config=types.GenerateContentConfig(
                            temperature=temperature,
                            response_mime_type="application/json"
                        )
                    )
                    if response and response.text:
                        return response.text
                except Exception as e:
                    print(f"[ActionBridge] Gemini model {model} error: {e}")
                    continue

        return None

    # ==========================================================================
    # ADAPTIVE DIAGNOSTIC INTERVIEW
    # ==========================================================================
    def generate_diagnostic_interview(self, goal_or_problem: str) -> DiagnosticInterview:
        """Generates 3-5 smart, adaptive questions tailored to the user's custom goal."""
        system_prompt = (
            "You are the ActionBridge AI Diagnostic Architect. "
            "Your job is to clarify underspecified user goals and diagnose real constraints before strategy creation. "
            "Return strictly valid JSON conforming to this structure:\n"
            "{\n"
            '  "goal_or_problem": "...",\n'
            '  "questions": [\n'
            '    {\n'
            '      "id": "q1",\n'
            '      "question": "Clear, direct, insightful diagnostic question",\n'
            '      "why_it_matters": "Why this specific answer fundamentally changes the strategic plan",\n'
            '      "category": "Baseline|Timeline|Resources|Constraints|Success Criteria",\n'
            '      "suggested_placeholder": "Example answer tailored to their goal"\n'
            '    }\n'
            '  ]\n'
            "}\n"
            "Generate exactly 4 highly targeted, intelligent questions that dive into their specific situation. "
            "Do NOT ask generic or repetitive questions. Return JSON only."
        )

        user_prompt = f"Goal / Problem to diagnose:\n{goal_or_problem}"

        raw = self.call_llm(system_prompt, user_prompt, temperature=0.3)
        if raw:
            data = _extract_json(raw)
            if data and "questions" in data:
                questions = []
                for idx, q in enumerate(data.get("questions", [])):
                    questions.append(DiagnosticQuestion(
                        id=f"q{idx+1}",
                        question=q.get("question", f"Question {idx+1}"),
                        why_it_matters=q.get("why_it_matters", "Helps tailor the strategy."),
                        category=q.get("category", "General"),
                        suggested_placeholder=q.get("suggested_placeholder", "")
                    ))
                return DiagnosticInterview(
                    goal_or_problem=goal_or_problem,
                    questions=questions
                )

        # Dynamic fallback questions tailored to their goal
        return DiagnosticInterview(
            goal_or_problem=goal_or_problem,
            questions=[
                DiagnosticQuestion(
                    id="q1",
                    question=f"What is your current starting point and experience level regarding '{goal_or_problem}'?",
                    why_it_matters="Determines whether you need foundational ramp-up or advanced execution.",
                    category="Baseline",
                    suggested_placeholder="e.g., Complete beginner / 6 months experience / built prototypes before"
                ),
                DiagnosticQuestion(
                    id="q2",
                    question="What is your target deadline and how many hours per week can you realistically commit?",
                    why_it_matters="Dictates pacing, milestone frequency, and task granularity.",
                    category="Timeline",
                    suggested_placeholder="e.g., 30 days deadline, 10-15 focused hours per week"
                ),
                DiagnosticQuestion(
                    id="q3",
                    question="What are your hardest constraints (budget, technical barriers, external dependencies)?",
                    why_it_matters="Ensures the proposed strategy avoids impossible requirements.",
                    category="Constraints",
                    suggested_placeholder="e.g., Bootstrapped / no budget for paid ads / limited access to GPUs"
                ),
                DiagnosticQuestion(
                    id="q4",
                    question="What exact outcome will prove that this goal has succeeded?",
                    why_it_matters="Allows the verification engine to set up objective pass/fail metrics.",
                    category="Success Criteria",
                    suggested_placeholder="e.g., Deployed working app with 10 users / scored 80+ / certified completion"
                )
            ]
        )

    def synthesize_interview_to_intake(self, goal_or_problem: str, answers: Dict[str, str]) -> GoalIntake:
        """Synthesizes interview answers into a high-fidelity GoalIntake schema."""
        system_prompt = (
            "You are the ActionBridge AI Strategy Intake Synthesizer. "
            "Given the user's initial goal and their answers to diagnostic questions, synthesize a complete, "
            "crisp GoalIntake in strictly valid JSON with these exact fields:\n"
            "{\n"
            '  "goal_title": "Concise, action-oriented title",\n'
            '  "why_it_matters": "Why this matters to the user",\n'
            '  "current_situation": "Current state and starting baseline",\n'
            '  "desired_outcome": "Specific target state",\n'
            '  "deadline": "Target deadline or timeframe",\n'
            '  "available_resources": "Time, budget, and tools available",\n'
            '  "constraints": "Hard obstacles and limitations",\n'
            '  "success_metrics": "Clear measurable criteria for success"\n'
            "}\n"
            "Return JSON only."
        )

        qa_text = "\n".join([f"- {k}: {v}" for k, v in answers.items() if v.strip()])
        user_prompt = f"Goal: {goal_or_problem}\n\nDiagnostic Answers:\n{qa_text}"

        raw = self.call_llm(system_prompt, user_prompt, temperature=0.2)
        if raw:
            data = _extract_json(raw)
            if data and "goal_title" in data:
                return GoalIntake(**_normalize_intake_data(data))

        # Fallback synthesis
        return GoalIntake(
            goal_title=goal_or_problem,
            why_it_matters="Achieve a high-impact personal or professional breakthrough.",
            current_situation=answers.get("q1", "Initial planning stage with baseline experience."),
            desired_outcome=answers.get("q4", "Successful completion with measurable deliverables."),
            deadline=answers.get("q2", "4-6 Weeks"),
            available_resources=answers.get("q2", "Dedicated weekly execution hours."),
            constraints=answers.get("q3", "Time and resource boundaries."),
            success_metrics=answers.get("q4", "Tangible working deliverable verified against criteria.")
        )

    # ==========================================================================
    # YOUTUBE VIDEO DIAGNOSTIC INTERVIEW & SYNTHESIS
    # ==========================================================================
    def generate_youtube_diagnostic_interview(self, video_ctx: YouTubeVideoContext) -> DiagnosticInterview:
        """
        Generates 4 intelligent, video-specific diagnostic questions derived from the video's title
        and transcript, asking the user how they wish to adapt and execute the video's insights.
        """
        system_prompt = (
            "You are the ActionBridge AI Strategic Video Analyst. "
            "Your mission is to transform video knowledge, tutorials, frameworks, or business concepts "
            "into an actionable execution strategy for the user. "
            "Formulate exactly 4 intelligent, personalized diagnostic questions that bridge what the video teaches "
            "with what the user specifically wants to achieve. "
            "The questions MUST be specific to the video content (not generic): "
            "1. Focus on which concept, technique, or workflow from this video they want to implement. "
            "2. Clarify their current baseline and tools compared to the video's requirements. "
            "3. Surface realistic execution constraints (time per week, budget, roadblocks). "
            "4. Define their concrete verification milestone for adopting this video's advice. "
            "Return strictly valid JSON conforming to this structure:\n"
            "{\n"
            '  "goal_or_problem": "...",\n'
            '  "questions": [\n'
            '    {\n'
            '      "id": "q1",\n'
            '      "question": "Deep, context-aware question directly referencing video concepts",\n'
            '      "why_it_matters": "Why this specific answer fundamentally alters the execution strategy",\n'
            '      "category": "Core Application|Baseline & Stack|Execution Constraints|Success Criteria",\n'
            '      "suggested_placeholder": "Example answer tailored to the video topic"\n'
            '    }\n'
            '  ]\n'
            "}\n"
            "Return JSON only."
        )

        transcript_preview = video_ctx.transcript_text[:5000] if video_ctx.has_transcript else "Transcript unavailable; base analysis strictly on title and subject matter."
        user_prompt = (
            f"YouTube Video Title: {video_ctx.title}\n"
            f"Channel / Creator: {video_ctx.channel_title}\n"
            f"Video URL: {video_ctx.url}\n\n"
            f"Video Transcript Excerpt:\n{transcript_preview}\n"
        )

        raw = self.call_llm(system_prompt, user_prompt, temperature=0.3)
        if raw:
            data = _extract_json(raw)
            if data and "questions" in data:
                questions = []
                for idx, q in enumerate(data.get("questions", [])):
                    questions.append(DiagnosticQuestion(
                        id=f"q{idx+1}",
                        question=q.get("question", f"Question {idx+1}"),
                        why_it_matters=q.get("why_it_matters", "Helps customize your implementation plan."),
                        category=q.get("category", "General"),
                        suggested_placeholder=q.get("suggested_placeholder", "")
                    ))
                return DiagnosticInterview(
                    goal_or_problem=f"Implement Insights from: {video_ctx.title}",
                    questions=questions
                )

        # Dynamic fallback questions tailored to the video
        clean_title = video_ctx.title.strip()
        return DiagnosticInterview(
            goal_or_problem=f"Implement Insights from: {clean_title}",
            questions=[
                DiagnosticQuestion(
                    id="q1",
                    question=f"Which specific core concept or method from '{clean_title}' do you want to implement in your own workflow?",
                    why_it_matters="Focuses your strategy on a concrete, high-leverage takeaway rather than vague theory.",
                    category="Core Application",
                    suggested_placeholder="e.g., Build the automated workflow demonstrated / Apply the 3-step marketing framework / Master the architecture"
                ),
                DiagnosticQuestion(
                    id="q2",
                    question="What is your current starting point, technical stack, or existing assets relative to what is shown in the video?",
                    why_it_matters="Ensures the roadmap starts at your exact current baseline without skipping prerequisite steps.",
                    category="Baseline & Stack",
                    suggested_placeholder="e.g., Intermediate Python developer with a basic prototype / Zero existing audience / Bootstrapped solo creator"
                ),
                DiagnosticQuestion(
                    id="q3",
                    question="What are your target execution boundaries (deadline, weekly hours committed, budget, hard blockers)?",
                    why_it_matters="Calibrates the pacing and tool requirements to your realistic bandwidth.",
                    category="Execution Constraints",
                    suggested_placeholder="e.g., 3-4 weeks timeframe, 8-10 hours/week, $0-$100 tooling budget"
                ),
                DiagnosticQuestion(
                    id="q4",
                    question="What tangible output or metric will verify that you have successfully put this video into action?",
                    why_it_matters="Creates an unambiguous post-condition that our verification engine can validate.",
                    category="Success Criteria",
                    suggested_placeholder="e.g., Working live deployment with documentation / Published first 5 content pieces / Acquired 10 initial users"
                )
            ]
        )

    def synthesize_youtube_interview_to_intake(self, video_ctx: YouTubeVideoContext, answers: Dict[str, str]) -> GoalIntake:
        """
        Synthesizes the video's concepts and the user's answers to the video diagnostic questions
        into a comprehensive, actionable GoalIntake schema.
        """
        system_prompt = (
            "You are the ActionBridge AI Strategy Intake Synthesizer. "
            "Synthesize the insights from the YouTube video and the user's answers to diagnostic questions "
            "into a crisp, professional GoalIntake JSON schema:\n"
            "{\n"
            '  "goal_title": "Action-oriented title focusing on executing the video\'s strategy",\n'
            '  "why_it_matters": "Why executing this video\'s blueprint matters to the user",\n'
            '  "current_situation": "User\'s current baseline and assets",\n'
            '  "desired_outcome": "Specific target state and deliverables",\n'
            '  "deadline": "Realistic deadline based on their answers",\n'
            '  "available_resources": "User\'s weekly time, tools, and budget",\n'
            '  "constraints": "Obstacles, limits, or boundaries identified",\n'
            '  "success_metrics": "Measurable criteria for verified completion"\n'
            "}\n"
            "Return JSON only."
        )

        qa_text = "\n".join([f"- {k}: {v}" for k, v in answers.items() if v.strip()])
        transcript_snippet = video_ctx.transcript_text[:3000] if video_ctx.has_transcript else "No transcript available."
        user_prompt = (
            f"YouTube Video: {video_ctx.title} (by {video_ctx.channel_title})\n"
            f"Video Summary/Snippet: {transcript_snippet}\n\n"
            f"User Diagnostic Answers:\n{qa_text}"
        )

        raw = self.call_llm(system_prompt, user_prompt, temperature=0.2)
        if raw:
            data = _extract_json(raw)
            if data and "goal_title" in data:
                return GoalIntake(**_normalize_intake_data(data))

        # Fallback synthesis
        return GoalIntake(
            goal_title=f"Execute Strategy: {video_ctx.title}",
            why_it_matters=f"Adopt proven insights from '{video_ctx.title}' ({video_ctx.channel_title}) to achieve measurable progress.",
            current_situation=answers.get("q2", "Starting implementation phase with existing baseline tools."),
            desired_outcome=answers.get("q1", "Full implementation of the video's core methodology with working deliverables."),
            deadline=answers.get("q3", "4 Weeks"),
            available_resources=answers.get("q3", "Dedicated weekly execution hours."),
            constraints=answers.get("q3", "Resource and time boundaries."),
            success_metrics=answers.get("q4", "Tangible deliverable successfully tested and verified.")
        )

    # ==========================================================================
    # STRATEGIC ANALYSIS & COMPARISON
    # ==========================================================================
    def analyze_goal(self, intake: GoalIntake) -> StrategicAnalysis:
        """Generates comprehensive strategic analysis comparing 2-3 distinct strategic options."""
        system_prompt = (
            "You are the ActionBridge AI Strategic Reasoning Core. "
            "Analyze the user's goal thoroughly and return strictly valid JSON conforming to StrategicAnalysis schema:\n"
            "{\n"
            '  "problem_definition": "Crisp definition of the core challenge",\n'
            '  "current_state_assessment": "Assessment of baseline",\n'
            '  "desired_future_state": "Clear picture of desired state",\n'
            '  "key_assumptions": ["Assumption 1", "Assumption 2", "Assumption 3"],\n'
            '  "root_cause_analysis": "Underlying reasons why this challenge exists",\n'
            '  "opportunities": ["Opportunity 1", "Opportunity 2"],\n'
            '  "constraints_analysis": "Detailed constraint trade-offs",\n'
            '  "strategies": [\n'
            "    {\n"
            '      "strategy_id": "STRAT-01",\n'
            '      "title": "Strategy Name",\n'
            '      "overview": "Clear explanation of how this approach works",\n'
            '      "pros": ["Pro 1", "Pro 2"],\n'
            '      "cons": ["Con 1", "Con 2"],\n'
            '      "feasibility_score": 8,\n'
            '      "impact_score": 9,\n'
            '      "estimated_cost": "Low/Medium/High",\n'
            '      "estimated_time": "Timeframe",\n'
            '      "reversibility": "High/Medium/Low",\n'
            '      "is_recommended": true\n'
            "    },\n"
            "    {\n"
            '      "strategy_id": "STRAT-02",\n'
            '      "title": "Alternative Strategy Name",\n'
            '      "overview": "Contrasting approach with different trade-offs",\n'
            '      "pros": ["Pro 1"],\n'
            '      "cons": ["Con 1"],\n'
            '      "feasibility_score": 7,\n'
            '      "impact_score": 8,\n'
            '      "estimated_cost": "Medium",\n'
            '      "estimated_time": "Timeframe",\n'
            '      "reversibility": "Medium",\n'
            '      "is_recommended": false\n'
            "    }\n"
            "  ],\n"
            '  "recommended_strategy_title": "Strategy Name",\n'
            '  "rationale_for_recommendation": "Why the chosen strategy best balances feasibility and impact",\n'
            '  "major_risks_and_mitigations": [\n'
            '    {"risk": "Risk description", "mitigation": "Concrete defense"}\n'
            "  ],\n"
            '  "success_milestones": ["Milestone 1", "Milestone 2", "Milestone 3"]\n'
            "}\n"
            "Ensure scores are integers between 1 and 10. Return JSON ONLY."
        )

        user_prompt = (
            f"Goal: {intake.goal_title}\n"
            f"Why it matters: {intake.why_it_matters}\n"
            f"Current situation: {intake.current_situation}\n"
            f"Desired outcome: {intake.desired_outcome}\n"
            f"Deadline: {intake.deadline}\n"
            f"Available resources: {intake.available_resources}\n"
            f"Constraints: {intake.constraints}\n"
            f"Success metrics: {intake.success_metrics}"
        )

        raw = self.call_llm(system_prompt, user_prompt, temperature=0.3)
        if raw:
            data = _extract_json(raw)
            if data and "strategies" in data and len(data["strategies"]) >= 1:
                data["goal_id"] = str(uuid.uuid4())[:8]
                data["goal_title"] = intake.goal_title
                data["is_demo"] = False
                try:
                    return StrategicAnalysis(**data)
                except Exception as e:
                    print(f"[ActionBridge] Pydantic parsing error: {e}")

        return self._generate_fallback_analysis(intake)

    # ==========================================================================
    # ACTION PLAN GENERATION
    # ==========================================================================
    def generate_action_plan(self, intake: GoalIntake, selected_strategy: StrategyOption) -> ActionPlan:
        """Decomposes chosen strategy into concrete, auditable tasks."""
        system_prompt = (
            "You are the ActionBridge AI Action Planning Core. "
            "Decompose the selected strategy into concrete, auditable execution tasks. "
            "PERMITTED TOOLS (ONLY use these when automated file or computation action is needed):\n"
            '- file_write: args: {"filepath": str, "content": str, "overwrite": bool} (Medium or High risk)\n'
            '- file_read: args: {"filepath": str} (Low risk)\n'
            '- file_list: args: {"directory": str} (Low risk)\n'
            '- file_delete: args: {"filepath": str} (High risk - requires approval)\n'
            '- data_compute: args: {"operation": "count"|"sum"|"mean", "numbers": list} (Low risk)\n'
            '- system_inspect: args: {"query": "workspace_health"} (Low risk)\n'
            "If a task is conceptual or user-executed, leave tool_name as null.\n\n"
            "Return strictly valid JSON conforming to ActionPlan schema:\n"
            "{\n"
            '  "strategic_summary": "One paragraph summarizing the roadmap",\n'
            '  "milestones": ["Milestone 1", "Milestone 2", "Milestone 3"],\n'
            '  "tasks": [\n'
            "    {\n"
            '      "task_id": "TASK-01",\n'
            '      "title": "Short descriptive title",\n'
            '      "instructions": "Specific, practical steps to execute",\n'
            '      "priority": "CRITICAL|HIGH|MEDIUM|LOW",\n'
            '      "phase": "Phase 1: Foundation|Phase 2: Execution|Phase 3: Verification",\n'
            '      "estimated_duration": "Estimated time",\n'
            '      "tool_name": "file_write" or null,\n'
            '      "tool_args": {"filepath": "...", "content": "...", "overwrite": true},\n'
            '      "expected_output": "Physical or verified deliverable",\n'
            '      "completion_criteria": "How success will be empirically verified",\n'
            '      "risk_level": "LOW|MEDIUM|HIGH",\n'
            '      "risk_reason": "Why this risk tier was selected"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Generate 4 to 6 tasks. Return JSON ONLY."
        )

        user_prompt = (
            f"Goal: {intake.goal_title}\n"
            f"Selected Strategy: {selected_strategy.title}\n"
            f"Overview: {selected_strategy.overview}\n"
            f"Constraints: {intake.constraints}\n"
            f"Deadline: {intake.deadline}\n"
            f"Metrics: {intake.success_metrics}"
        )

        raw = self.call_llm(system_prompt, user_prompt, temperature=0.2)
        if raw:
            data = _extract_json(raw)
            if data and "tasks" in data:
                for t in data.get("tasks", []):
                    if not isinstance(t.get("tool_args"), dict):
                        t["tool_args"] = {}
                data["plan_id"] = f"PLAN-{str(uuid.uuid4())[:6].upper()}"
                data["goal_title"] = intake.goal_title
                data["selected_strategy_title"] = selected_strategy.title
                data["is_demo"] = False
                try:
                    return ActionPlan(**data)
                except Exception as e:
                    print(f"[ActionBridge] Plan parsing error: {e}")

        return self._generate_fallback_plan(intake, selected_strategy)

    # ==========================================================================
    # DETERMINISTIC / CONTEXT-AWARE FALLBACKS
    # ==========================================================================
    def _generate_fallback_analysis(self, intake: GoalIntake) -> StrategicAnalysis:
        """Context-aware fallback analysis when offline."""
        title = intake.goal_title or "Target Objective"
        strat1 = StrategyOption(
            strategy_id="STRAT-01",
            title=f"Fast-Track Execution & Incremental Validation for {title[:30]}",
            overview=f"Prioritize rapid iterations focusing on the highest-leverage components of {title}. Test weekly milestones to identify bottlenecks early.",
            pros=["Rapid feedback loops", "Low upfront resource expenditure", "Highly reversible"],
            cons=["Requires rigorous focus", "Non-core details deferred"],
            feasibility_score=9,
            impact_score=8,
            estimated_cost="Low",
            estimated_time=intake.deadline or "3-4 Weeks",
            reversibility="High",
            is_recommended=True
        )
        strat2 = StrategyOption(
            strategy_id="STRAT-02",
            title=f"Structured Deep Foundation Approach for {title[:30]}",
            overview=f"Build comprehensive systems, full documentation, and systematic tooling upfront before rolling out {title}.",
            pros=["Predictable system structure", "Exhaustive edge-case handling"],
            cons=["Higher initial time cost", "Harder to pivot if requirements change"],
            feasibility_score=7,
            impact_score=9,
            estimated_cost="Medium",
            estimated_time="6-8 Weeks",
            reversibility="Medium",
            is_recommended=False
        )
        return StrategicAnalysis(
            goal_id=str(uuid.uuid4())[:8],
            goal_title=intake.goal_title,
            problem_definition=f"Achieving: {intake.goal_title}. The core challenge is bridging the gap between intention and verified execution under real constraints.",
            current_state_assessment=intake.current_situation or "Baseline setup: Objectives identified, initial assets assembled.",
            desired_future_state=intake.desired_outcome or "Target achievement: Complete execution with auditable proof of completion.",
            key_assumptions=[
                "Execution hours are reserved consistently each week",
                "Actions operate within authorized, verified sandbox boundaries",
                "Intermediate milestones are audited before moving to subsequent phases"
            ],
            root_cause_analysis="Failure usually arises from unclear intermediate deliverables, unverified assumptions, and lack of accountability.",
            opportunities=["Leverage automated execution tools", "Enforce empirical proof for completed phases"],
            constraints_analysis=intake.constraints or "Standard timeline and resource boundaries.",
            strategies=[strat1, strat2],
            recommended_strategy_title=strat1.title,
            rationale_for_recommendation=f"The Fast-Track method provides immediate measurable momentum on '{intake.goal_title}' while preserving the agility to pivot.",
            major_risks_and_mitigations=[
                {"risk": "Scope creep and distraction", "mitigation": "Strict milestone checklists with automated verification."},
                {"risk": "Unverified progress", "mitigation": "Post-condition verification engine checks disk and computation outputs."}
            ],
            success_milestones=[
                f"Milestone 1: Baseline established for {intake.goal_title[:25]}",
                "Milestone 2: Core deliverable authored and verified on disk",
                "Milestone 3: Final outcome certification and delivery"
            ],
            is_demo=True
        )

    def _generate_fallback_plan(self, intake: GoalIntake, strategy: StrategyOption) -> ActionPlan:
        """Context-aware fallback action plan."""
        slug = re.sub(r'[^a-zA-Z0-9_]', '_', intake.goal_title[:20].lower()).strip('_') or "project"
        tasks = [
            PlanTask(
                task_id="TASK-01",
                title="Environment & Sandbox Health Check",
                instructions="Inspect the workspace sandbox directory and check telemetry.",
                priority=TaskPriority.HIGH,
                phase="Phase 1: Foundation",
                estimated_duration="5 mins",
                tool_name="system_inspect",
                tool_args={"query": "workspace_health"},
                expected_output="Sandbox telemetry reporting operational status",
                completion_criteria="Sandbox folder exists and is writable",
                risk_level=RiskLevel.LOW,
                risk_reason="Read-only diagnostic inspection",
                status=TaskStatus.PENDING,
                is_approved=True
            ),
            PlanTask(
                task_id="TASK-02",
                title=f"Author {slug.title()} Specification Document",
                instructions=f"Create a structured execution specification ({slug}_spec.md) in the sandbox workspace.",
                priority=TaskPriority.CRITICAL,
                phase="Phase 1: Foundation",
                estimated_duration="15 mins",
                tool_name="file_write",
                tool_args={
                    "filepath": f"{slug}_spec.md",
                    "content": f"# Execution Specification: {intake.goal_title}\n\n**Strategy**: {strategy.title}\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n## Objectives\n- {intake.desired_outcome}\n\n## Constraints\n- {intake.constraints}\n\n## Success Criteria\n- {intake.success_metrics}\n",
                    "overwrite": True
                },
                expected_output=f"{slug}_spec.md authored on disk",
                completion_criteria="File written and verified with cryptographic SHA256 checksum",
                risk_level=RiskLevel.MEDIUM,
                risk_reason="Creates a new specification file in sandbox",
                status=TaskStatus.PENDING,
                is_approved=True
            ),
            PlanTask(
                task_id="TASK-03",
                title="Milestone Allocation & Metric Audit",
                instructions="Compute milestone resource hours and statistical distribution.",
                priority=TaskPriority.MEDIUM,
                phase="Phase 2: Execution",
                estimated_duration="5 mins",
                tool_name="data_compute",
                tool_args={"operation": "mean", "numbers": [12.0, 18.0, 24.0, 30.0]},
                expected_output="Deterministic arithmetic mean: 21.0 hours/milestone",
                completion_criteria="Calculation verifies arithmetic invariants without side-effects",
                risk_level=RiskLevel.LOW,
                risk_reason="Pure mathematical computation",
                status=TaskStatus.PENDING,
                is_approved=True
            ),
            PlanTask(
                task_id="TASK-04",
                title=f"Export Certified Deliverable for {slug.title()}",
                instructions=f"Compile final verified outcome report ({slug}_outcome.json).",
                priority=TaskPriority.HIGH,
                phase="Phase 3: Verification",
                estimated_duration="10 mins",
                tool_name="file_write",
                tool_args={
                    "filepath": f"{slug}_outcome.json",
                    "content": json.dumps({
                        "goal": intake.goal_title,
                        "strategy": strategy.title,
                        "status": "COMPLETED_AND_VERIFIED",
                        "timestamp": datetime.now().isoformat()
                    }, indent=2),
                    "overwrite": True
                },
                expected_output=f"{slug}_outcome.json verified on disk",
                completion_criteria="File physically exists with verified content hash",
                risk_level=RiskLevel.HIGH,
                risk_reason="CONSEQUENTIAL: Overwrites milestone deliverable; requires human authorization",
                status=TaskStatus.AWAITING_APPROVAL,
                is_approved=False
            )
        ]

        return ActionPlan(
            plan_id=f"PLAN-{str(uuid.uuid4())[:6].upper()}",
            goal_title=intake.goal_title,
            selected_strategy_title=strategy.title,
            strategic_summary=f"Actionable roadmap operationalizing '{strategy.title}' for '{intake.goal_title}'. Contains auditable tasks with verification checks.",
            milestones=[
                "1. Establish verified workspace baseline",
                f"2. Author {slug} specification artifact",
                "3. Compute resource and milestone distribution",
                "4. Export and verify final deliverable"
            ],
            tasks=tasks,
            is_demo=True
        )
