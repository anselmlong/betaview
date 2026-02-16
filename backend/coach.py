"""
BetaView Coach
Generates natural language feedback using LLM.
"""

import os
import json
from typing import Optional
import anthropic


SYSTEM_PROMPT = """You are an experienced climbing coach reviewing a boulderer's technique based on metrics extracted from video analysis.

Your feedback style:
- Encouraging but direct
- No fluff or corporate speak
- Speak like a gym coach, not a textbook
- Use climbing terminology naturally
- Be specific about what to work on
- Always include one actionable drill or cue

Keep feedback concise: 3-4 short paragraphs max."""


def generate_feedback_prompt(metrics: dict) -> str:
    """Generate the prompt for the LLM."""
    return f"""Analyze this climber's technique based on these metrics:

**Path Efficiency**: {metrics.get('path_efficiency', 0):.1%}
- Total hip travel: {metrics.get('total_distance', 0):.0f}px
- Direct distance: {metrics.get('direct_distance', 0):.0f}px
- (Higher efficiency = more direct, controlled path)

**Movement Rhythm**:
- Move count: {metrics.get('move_count', 0)}
- Average pause duration: {metrics.get('avg_pause_duration', 0):.1f}s
- Rhythm variance: {metrics.get('rhythm_variance', 0):.2f} (lower = more consistent)

**Foot Stability** (Silent Feet):
- Clean placements: {metrics.get('clean_placements', 0)} / {metrics.get('total_placements', 0)}
- Average jitter after placement: {metrics.get('avg_foot_jitter', 0):.1f}px
- (Lower jitter = more confident foot placements)

**Body Tension**:
- Tension score: {metrics.get('body_tension_score', 0):.1%}
- Sag events: {metrics.get('sag_count', 0)}
- (Higher score = better core engagement)

**Climb Duration**: {metrics.get('climb_duration', 0):.1f}s

Give feedback in this structure:
1. What they did well (be specific, reference the metrics)
2. Main area to improve (pick ONE priority)
3. A specific drill or mental cue to practice

Remember: be encouraging but honest. If something needs work, say so directly."""


def generate_coach_feedback(metrics: dict, api_key: Optional[str] = None) -> str:
    """
    Generate coaching feedback using Claude.
    
    Args:
        metrics: Dictionary of climbing metrics
        api_key: Anthropic API key (uses env var if not provided)
    
    Returns:
        Natural language coaching feedback
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        return _generate_fallback_feedback(metrics)
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": generate_feedback_prompt(metrics)}
            ]
        )
        
        return message.content[0].text
        
    except Exception as e:
        print(f"LLM error: {e}")
        return _generate_fallback_feedback(metrics)


def _generate_fallback_feedback(metrics: dict) -> str:
    """Generate basic feedback without LLM."""
    feedback_parts = []
    
    # Path efficiency feedback
    efficiency = metrics.get('path_efficiency', 0)
    if efficiency >= 0.7:
        feedback_parts.append("Your movement path is efficient — you're taking direct lines without excessive wandering. This shows good route reading.")
    elif efficiency >= 0.5:
        feedback_parts.append("Your path efficiency is decent, but there's room to move more directly. Try visualizing the entire sequence before starting.")
    else:
        feedback_parts.append("Your hip path shows a lot of wandering — you might be adjusting mid-move or second-guessing beta. Work on committing to moves once you start.")
    
    # Stability feedback
    total_placements = metrics.get('total_placements', 0)
    clean_placements = metrics.get('clean_placements', 0)
    if total_placements > 0:
        clean_ratio = clean_placements / total_placements
        if clean_ratio >= 0.8:
            feedback_parts.append("Your foot placements are precise — you're placing and trusting without readjusting. Keep it up.")
        elif clean_ratio >= 0.5:
            feedback_parts.append("About half your foot placements show some jitter after contact. Focus on looking at your feet until they're placed, then trust the hold.")
        else:
            feedback_parts.append("Main area to improve: foot confidence. You're readjusting after most placements. Drill: do easy problems where you watch each foot touch the hold before moving on.")
    
    # Body tension
    tension = metrics.get('body_tension_score', 0)
    if tension < 0.6:
        feedback_parts.append("Your core could stay more engaged between moves — I'm seeing some torso sag. Try squeezing your glutes as you reach for holds.")
    
    return "\n\n".join(feedback_parts)


def format_metrics_for_display(metrics: dict) -> dict:
    """Format metrics for frontend display."""
    return {
        "pathEfficiency": {
            "value": metrics.get('path_efficiency', 0),
            "label": "Path Efficiency",
            "description": "How direct your movement path is (1.0 = perfectly direct)",
            "rating": _get_rating(metrics.get('path_efficiency', 0), [0.4, 0.6, 0.75])
        },
        "stability": {
            "value": metrics.get('stability_score', 0),
            "label": "Foot Stability",
            "description": "Percentage of clean foot placements",
            "rating": _get_rating(metrics.get('stability_score', 0), [0.5, 0.7, 0.85])
        },
        "bodyTension": {
            "value": metrics.get('body_tension_score', 0),
            "label": "Body Tension",
            "description": "Core engagement and torso control",
            "rating": _get_rating(metrics.get('body_tension_score', 0), [0.5, 0.7, 0.85])
        },
        "rhythm": {
            "moveCount": metrics.get('move_count', 0),
            "avgPause": metrics.get('avg_pause_duration', 0),
            "variance": metrics.get('rhythm_variance', 0),
            "label": "Movement Rhythm",
            "description": "Consistency of your climbing tempo"
        },
        "duration": metrics.get('climb_duration', 0)
    }


def _get_rating(value: float, thresholds: list) -> str:
    """Convert numeric value to rating string."""
    if value < thresholds[0]:
        return "needs_work"
    elif value < thresholds[1]:
        return "developing"
    elif value < thresholds[2]:
        return "good"
    else:
        return "excellent"
