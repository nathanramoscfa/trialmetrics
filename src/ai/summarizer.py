# src/ai/summarizer.py
"""AI-powered trial summary generation using OpenAI GPT-4."""

import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = None


def get_client() -> OpenAI:
    """Get or create OpenAI client.

    Returns:
        OpenAI: Configured OpenAI client.

    Raises:
        ValueError: If OPENAI_API_KEY not set.
    """
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. "
                "Set it in .env file or environment."
            )
        client = OpenAI(api_key=api_key)
    return client


def generate_trial_summary(
    trial_data: dict,
    power_result: dict,
    budget_result: dict,
    forecast_result: Optional[dict] = None,
    model: str = "gpt-4.1-nano"
) -> str:
    """Generate AI-powered executive summary for a clinical trial.

    Uses OpenAI GPT to create a concise 3-sentence summary
    highlighting key trial metrics and concerns.

    Args:
        trial_data: Trial information from parse_trial_summary().
        power_result: Power analysis from analyze_trial_power().
        budget_result: Budget analysis (BudgetResult.to_dict()).
        forecast_result: Optional enrollment forecast results.
        model: OpenAI model (default: gpt-4.1-nano, $0.10/1M in).

    Returns:
        str: 3-sentence executive summary.

    Raises:
        ValueError: If OpenAI API key not configured.
        Exception: If API call fails.
    """
    # Extract key metrics
    title = trial_data.get("title", "Unknown Trial")
    phase = trial_data.get("phase", "N/A")
    enrollment_target = trial_data.get("enrollment_target", 0)
    enrollment_actual = power_result.get("n_per_group_actual", 0) * 2

    power_pct = power_result.get("power_at_actual", 0) * 100
    is_underpowered = power_result.get("is_underpowered", True)

    # Handle BudgetResult object or dict
    if hasattr(budget_result, "to_dict"):
        budget_dict = budget_result.to_dict()
    else:
        budget_dict = budget_result

    spent = budget_dict.get("spent_to_date", 0)
    total = budget_dict.get("total_budget", 0)
    runway = budget_dict.get("runway_months", "N/A")
    efficiency = budget_dict.get("efficiency_ratio", 1.0)

    # Completion date
    if forecast_result and forecast_result.get("completion_date"):
        completion = forecast_result["completion_date"].strftime("%B %Y")
    else:
        completion = trial_data.get("completion_date", "TBD")

    # Determine risk level
    if is_underpowered and power_pct < 50:
        risk_level = "HIGH RISK"
        risk_emoji = "🔴"
    elif is_underpowered:
        risk_level = "MODERATE RISK"
        risk_emoji = "🟡"
    else:
        risk_level = "ON TRACK"
        risk_emoji = "🟢"

    # Calculate derived metrics
    enrollment_pct = (
        enrollment_actual / enrollment_target * 100
        if enrollment_target > 0 else 0
    )
    budget_pct = spent / total * 100 if total > 0 else 0
    power_gap = 80 - power_pct if power_pct < 80 else 0
    patients_needed = power_result.get("enrollment_shortfall", 0)

    # Build comprehensive prompt
    prompt = f"""You are a senior clinical trial analyst at a top consulting firm.
Write a comprehensive executive briefing for pharma leadership.

═══════════════════════════════════════════════════════════════
TRIAL: {title}
PHASE: {phase}
═══════════════════════════════════════════════════════════════

CURRENT METRICS:
• Enrollment: {enrollment_actual} of {enrollment_target} ({enrollment_pct:.0f}%)
• Statistical Power: {power_pct:.1f}% (industry standard: 80%)
• Budget Spent: ${spent:,.0f} of ${total:,.0f} ({budget_pct:.0f}%)
• Runway: {runway} months remaining
• Efficiency Ratio: {efficiency:.2f}x
• Projected Completion: {completion}

RISK CLASSIFICATION: {risk_level}

═══════════════════════════════════════════════════════════════
BRIEFING REQUIREMENTS:
═══════════════════════════════════════════════════════════════

Write a 5-6 sentence executive summary covering:

1. SITUATION (1 sentence): Start with "{risk_emoji} {risk_level}:" then state the trial name, phase, and current enrollment status with percentage.

2. COMPLICATION (1-2 sentences): Explain the key risk. If underpowered ({power_pct:.1f}% < 80%), emphasize this threatens study validity - the trial may fail to detect a true treatment effect, wasting all investment. If power is adequate, highlight the positive trajectory.

3. IMPLICATION (1 sentence): What happens if current trends continue? Will they hit enrollment targets? What's the timeline risk? Connect runway ({runway} months) to completion feasibility.

4. RECOMMENDATION (2 sentences): Provide specific, actionable next steps. Be prescriptive - don't just say "accelerate enrollment" but suggest HOW (add sites, increase referral incentives, expand eligibility criteria, etc.). End with expected outcome if recommendations are followed.

STYLE GUIDELINES:
- Write like a McKinsey partner briefing a pharma CEO
- Use specific numbers (percentages, dollar amounts, timeframes)
- Be direct and authoritative - executives want clarity, not hedging
- Every sentence should add value - no filler
- Connect the dots between metrics and business impact

OUTPUT: 5-6 flowing sentences, no bullet points, no headers."""

    try:
        openai_client = get_client()
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a world-class clinical trial strategist. "
                        "You provide actionable, data-driven executive "
                        "briefings that drive decision-making. Your "
                        "recommendations are specific and implementable."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Unable to generate summary: {str(e)}"


def generate_summary_without_api(
    trial_data: dict,
    power_result: dict,
    budget_result: dict,
    forecast_result: Optional[dict] = None
) -> str:
    """Generate a rule-based summary when API is unavailable.

    Provides a structured summary using templates when OpenAI
    API is not configured or fails.

    Args:
        trial_data: Trial information.
        power_result: Power analysis results.
        budget_result: Budget analysis results.
        forecast_result: Optional enrollment forecast.

    Returns:
        str: Template-based 5-6 sentence summary.
    """
    # Extract metrics
    title = trial_data.get("title", "This trial")[:50]
    phase = trial_data.get("phase", "N/A")
    enrollment_target = trial_data.get("enrollment_target", 0)
    enrollment_actual = power_result.get("n_per_group_actual", 0) * 2
    completion = trial_data.get("completion_date", "TBD")

    progress_pct = (
        (enrollment_actual / enrollment_target * 100)
        if enrollment_target > 0 else 0
    )

    power_pct = power_result.get("power_at_actual", 0) * 100
    is_underpowered = power_result.get("is_underpowered", True)
    shortfall = power_result.get("enrollment_shortfall", 0)

    # Handle BudgetResult object or dict
    if hasattr(budget_result, "to_dict"):
        budget_dict = budget_result.to_dict()
    else:
        budget_dict = budget_result

    utilization = budget_dict.get("budget_utilization", 0) * 100
    runway = budget_dict.get("runway_months")
    efficiency = budget_dict.get("efficiency_ratio", 1.0)
    spent = budget_dict.get("spent_to_date", 0)
    total = budget_dict.get("total_budget", 0)

    # Determine risk level
    if is_underpowered and power_pct < 50:
        risk_level = "HIGH RISK"
        risk_emoji = "🔴"
    elif is_underpowered:
        risk_level = "MODERATE RISK"
        risk_emoji = "🟡"
    else:
        risk_level = "ON TRACK"
        risk_emoji = "🟢"

    # Sentence 1: Situation (risk + enrollment)
    s1 = (
        f"{risk_emoji} {risk_level}: {title}, a {phase} trial, has enrolled "
        f"{progress_pct:.0f}% of its target ({enrollment_actual} of "
        f"{enrollment_target} patients) with a projected completion date "
        f"of {completion}."
    )

    # Sentence 2: Complication (power analysis)
    if is_underpowered and power_pct < 50:
        s2 = (
            f"The current statistical power stands at just {power_pct:.0f}%, "
            f"critically below the 80% threshold required for scientific "
            f"validity, meaning the study risks failing to detect a true "
            f"treatment effect even if one exists."
        )
    elif is_underpowered:
        s2 = (
            f"Statistical power is at {power_pct:.0f}%, below the 80% "
            f"threshold, which poses a moderate risk to the study's ability "
            f"to demonstrate treatment efficacy."
        )
    else:
        s2 = (
            f"Statistical power is healthy at {power_pct:.0f}%, exceeding "
            f"the 80% threshold required for robust detection of treatment "
            f"effects."
        )

    # Sentence 3: Implication (what happens next)
    if runway and runway < 6:
        s3 = (
            f"With only {runway:.1f} months of runway remaining and "
            f"${spent:,.0f} of ${total:,.0f} budget consumed, the timeline "
            f"for achieving adequate enrollment is constrained."
        )
    elif efficiency < 1.0:
        s3 = (
            f"Budget efficiency at {efficiency:.2f}x indicates spending "
            f"is outpacing enrollment progress, with {runway:.1f} months "
            f"of runway remaining to course-correct."
        )
    else:
        s3 = (
            f"Budget utilization remains efficient at {efficiency:.2f}x "
            f"with {runway:.1f} months of runway, providing adequate "
            f"resources to reach enrollment targets."
        )

    # Sentence 4-5: Recommendations
    if is_underpowered and power_pct < 50:
        s4 = (
            f"Immediate intervention is required: consider adding 2-3 new "
            f"clinical sites, increasing patient referral incentives by "
            f"15-20%, and expanding eligibility criteria where clinically "
            f"appropriate."
        )
        s5 = (
            f"Without accelerated enrollment of approximately {shortfall} "
            f"additional patients, this study faces significant risk of "
            f"producing inconclusive results and should be flagged for "
            f"executive review within 30 days."
        )
    elif is_underpowered:
        s4 = (
            f"To achieve adequate power, focus on optimizing existing site "
            f"performance through weekly enrollment reviews and targeted "
            f"recruitment campaigns in high-performing geographies."
        )
        s5 = (
            f"Maintaining current trajectory with these enhancements should "
            f"bring the study to 80% power within the planned timeline, "
            f"though quarterly progress reviews are recommended."
        )
    else:
        s4 = (
            f"The study is performing well; maintain current operational "
            f"tempo while monitoring for any site-level variations that "
            f"could impact the enrollment trajectory."
        )
        s5 = (
            f"Continue monthly progress reviews and prepare interim "
            f"analysis protocols to capitalize on the strong enrollment "
            f"foundation."
        )

    return f"{s1} {s2} {s3} {s4} {s5}"


def get_trial_summary(
    trial_data: dict,
    power_result: dict,
    budget_result: dict,
    forecast_result: Optional[dict] = None,
    use_ai: bool = True
) -> tuple:
    """Get trial summary, using AI if available.

    Attempts to use OpenAI API first, falls back to rule-based
    summary if API is unavailable.

    Args:
        trial_data: Trial information.
        power_result: Power analysis results.
        budget_result: Budget analysis results.
        forecast_result: Optional enrollment forecast.
        use_ai: Whether to attempt AI generation.

    Returns:
        tuple: (summary_text, source) where source is
            'ai' or 'template'.
    """
    if use_ai and os.getenv("OPENAI_API_KEY"):
        try:
            summary = generate_trial_summary(
                trial_data,
                power_result,
                budget_result,
                forecast_result
            )
            return summary, "ai"
        except Exception:
            pass

    # Fallback to template
    summary = generate_summary_without_api(
        trial_data,
        power_result,
        budget_result,
        forecast_result
    )
    return summary, "template"


if __name__ == "__main__":
    print("=" * 60)
    print("AI SUMMARIZER MODULE TEST")
    print("=" * 60)

    # Test data
    trial_data = {
        "title": "Study of Drug X in Type 2 Diabetes",
        "phase": "Phase 3",
        "enrollment_target": 200,
        "completion_date": "2026-12"
    }

    power_result = {
        "n_per_group_actual": 60,
        "power_at_actual": 0.775,
        "is_underpowered": True
    }

    budget_result = {
        "spent_to_date": 8_200_000,
        "total_budget": 20_600_000,
        "runway_months": 12.1,
        "budget_utilization": 0.398,
        "efficiency_ratio": 1.07
    }

    print("\n1. Testing template-based summary (no API):")
    print("-" * 40)
    summary = generate_summary_without_api(
        trial_data, power_result, budget_result
    )
    print(summary)

    print("\n2. Testing get_trial_summary fallback:")
    print("-" * 40)
    summary, source = get_trial_summary(
        trial_data, power_result, budget_result, use_ai=False
    )
    print(f"Source: {source}")
    print(summary)

    # Test AI if API key is set
    if os.getenv("OPENAI_API_KEY"):
        print("\n3. Testing AI-powered summary:")
        print("-" * 40)
        summary, source = get_trial_summary(
            trial_data, power_result, budget_result, use_ai=True
        )
        print(f"Source: {source}")
        print(summary)
    else:
        print("\n3. Skipping AI test (OPENAI_API_KEY not set)")

    print("\n" + "=" * 60)
    print("AI summarizer tests completed!")
    print("=" * 60)
