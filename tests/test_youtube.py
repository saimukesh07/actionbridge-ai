"""
ActionBridge AI - YouTube to Strategy Automated Tests
Verifies video ID extraction, metadata fetching, transcript handling,
adaptive interview generation, and strategy synthesis.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.youtube_service import extract_youtube_video_id, fetch_youtube_metadata, get_youtube_video_context
from core.schemas import YouTubeVideoContext, DiagnosticInterview, GoalIntake
from core.gemini_client import GeminiReasoningClient


def test_extract_youtube_video_id():
    """Verify regex correctly parses various YouTube URL patterns."""
    cases = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ&feature=share", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("invalid-url-without-id", None),
        ("", None),
    ]

    for url, expected in cases:
        result = extract_youtube_video_id(url)
        assert result == expected, f"Failed on {url}: expected {expected}, got {result}"


def test_fetch_youtube_metadata():
    """Verify oEmbed public endpoint returns metadata for valid videos."""
    meta = fetch_youtube_metadata("dQw4w9WgXcQ")
    assert "title" in meta
    assert "channel_title" in meta
    assert "thumbnail_url" in meta
    assert len(meta["title"]) > 0


def test_get_youtube_video_context():
    """Verify get_youtube_video_context creates a valid schema object."""
    ctx = get_youtube_video_context("https://youtu.be/dQw4w9WgXcQ")
    assert isinstance(ctx, YouTubeVideoContext)
    assert ctx.video_id == "dQw4w9WgXcQ"
    assert "youtube.com/watch?v=dQw4w9WgXcQ" in ctx.url
    assert ctx.title is not None
    assert len(ctx.title) > 0


def test_youtube_diagnostic_interview_and_synthesis():
    """Verify AI client generates 4 adaptive questions and synthesizes intake."""
    client = GeminiReasoningClient()
    ctx = YouTubeVideoContext(
        video_id="zjkBMFhNj_g",
        url="https://www.youtube.com/watch?v=zjkBMFhNj_g",
        title="Intro to Large Language Models",
        channel_title="Andrej Karpathy",
        thumbnail_url="https://img.youtube.com/vi/zjkBMFhNj_g/hqdefault.jpg",
        transcript_text="Large language models are trained on internet text to predict next tokens...",
        has_transcript=True,
        word_count=500
    )

    interview = client.generate_youtube_diagnostic_interview(ctx)
    assert isinstance(interview, DiagnosticInterview)
    assert len(interview.questions) == 4
    for q in interview.questions:
        assert q.question
        assert q.why_it_matters
        assert q.category

    # Simulate user answers
    answers = {
        "q1": "Build a custom domain RAG pipeline and fine-tune an open weights model.",
        "q2": "Intermediate Python developer with FastAPI experience.",
        "q3": "4 weeks deadline, 10 hours per week, zero GPU budget (use free Colab).",
        "q4": "Working local prototype answering questions over medical PDFs with 90% accuracy."
    }

    intake = client.synthesize_youtube_interview_to_intake(ctx, answers)
    assert isinstance(intake, GoalIntake)
    assert intake.goal_title
    assert intake.desired_outcome
    assert intake.deadline
    assert intake.success_metrics

    # Test full downstream analysis
    analysis = client.analyze_goal(intake)
    assert analysis.goal_title
    assert len(analysis.strategies) >= 1

    rec = next((s for s in analysis.strategies if s.is_recommended), analysis.strategies[0])
    plan = client.generate_action_plan(intake, rec)
    assert len(plan.tasks) >= 3


if __name__ == "__main__":
    print("Running ActionBridge AI YouTube Feature Tests...")
    test_extract_youtube_video_id()
    print("[PASS] extract_youtube_video_id")
    test_fetch_youtube_metadata()
    print("[PASS] fetch_youtube_metadata")
    test_get_youtube_video_context()
    print("[PASS] get_youtube_video_context")
    test_youtube_diagnostic_interview_and_synthesis()
    print("[PASS] test_youtube_diagnostic_interview_and_synthesis")
    print("ALL YOUTUBE FEATURE TESTS PASSED SUCCESSFULLY!")
