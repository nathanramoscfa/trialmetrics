# src/analysis/cost_model.py
"""Synthetic cost model for clinical trial budget tracking."""

from typing import Optional
from dataclasses import dataclass


# Industry cost benchmarks (USD per patient)
# Source: Synthetic estimates based on industry reports
COST_PER_PATIENT = {
    "PHASE1": {"low": 15_000, "median": 25_000, "high": 40_000},
    "PHASE2": {"low": 25_000, "median": 35_000, "high": 50_000},
    "PHASE3": {"low": 35_000, "median": 45_000, "high": 70_000},
    "PHASE4": {"low": 10_000, "median": 20_000, "high": 35_000},
    "NA": {"low": 20_000, "median": 30_000, "high": 45_000},  # Unknown phase
}

# Fixed costs
SITE_STARTUP_COST = 50_000  # USD per site
MONTHLY_OVERHEAD_RATE = 0.05  # 5% of patient costs as monthly overhead


@dataclass
class BudgetResult:
    """Container for budget analysis results."""

    # Budget figures
    total_budget: float
    patient_budget: float
    site_budget: float
    spent_to_date: float
    remaining: float

    # Per-patient metrics
    cost_per_patient_budgeted: float
    cost_per_patient_actual: float

    # Burn metrics
    monthly_burn_rate: float
    runway_months: float

    # Status
    budget_utilization: float
    enrollment_progress: float
    is_over_budget: bool
    efficiency_ratio: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_budget": self.total_budget,
            "patient_budget": self.patient_budget,
            "site_budget": self.site_budget,
            "spent_to_date": self.spent_to_date,
            "remaining": self.remaining,
            "cost_per_patient_budgeted": self.cost_per_patient_budgeted,
            "cost_per_patient_actual": self.cost_per_patient_actual,
            "monthly_burn_rate": self.monthly_burn_rate,
            "runway_months": self.runway_months,
            "budget_utilization": self.budget_utilization,
            "enrollment_progress": self.enrollment_progress,
            "is_over_budget": self.is_over_budget,
            "efficiency_ratio": self.efficiency_ratio,
        }


def normalize_phase(phase: str) -> str:
    """Normalize phase string to match cost table keys.

    Args:
        phase: Phase string from API (e.g., "Phase 3", "PHASE3",
            "Phase 2/Phase 3", "NA", "N/A").

    Returns:
        str: Normalized phase key (PHASE1, PHASE2, PHASE3, PHASE4, NA).
    """
    if not phase:
        return "NA"

    phase_upper = phase.upper().replace(" ", "")

    # Handle combined phases (e.g., "Phase 2/Phase 3") - use higher phase
    if "/" in phase_upper:
        phases = phase_upper.split("/")
        # Extract numbers and take max
        nums = []
        for p in phases:
            for char in p:
                if char.isdigit():
                    nums.append(int(char))
                    break
        if nums:
            return f"PHASE{max(nums)}"

    # Extract phase number
    for i in range(1, 5):
        if str(i) in phase_upper:
            return f"PHASE{i}"

    return "NA"


def get_cost_per_patient(
    phase: str,
    scenario: str = "median"
) -> float:
    """Get cost per patient for a given phase and scenario.

    Args:
        phase: Trial phase (will be normalized).
        scenario: Cost scenario - 'low', 'median', or 'high'.

    Returns:
        float: Cost per patient in USD.
    """
    normalized = normalize_phase(phase)
    costs = COST_PER_PATIENT.get(normalized, COST_PER_PATIENT["NA"])
    return costs.get(scenario, costs["median"])


def calculate_budget(
    phase: str,
    enrollment_target: int,
    enrollment_actual: int,
    sites_count: int,
    months_elapsed: float,
    scenario: str = "median"
) -> BudgetResult:
    """Calculate comprehensive budget analysis for a clinical trial.

    Uses synthetic cost model based on industry benchmarks.
    Assumes costs are incurred proportionally to enrollment
    plus fixed site startup costs.

    Args:
        phase: Trial phase (e.g., "Phase 3", "PHASE2").
        enrollment_target: Target enrollment count.
        enrollment_actual: Current actual enrollment.
        sites_count: Number of study sites.
        months_elapsed: Months since trial start.
        scenario: Cost scenario - 'low', 'median', 'high'.

    Returns:
        BudgetResult: Comprehensive budget analysis.
    """
    # Get per-patient cost
    cpp_budgeted = get_cost_per_patient(phase, scenario)

    # Calculate budgets
    patient_budget = cpp_budgeted * enrollment_target
    site_budget = SITE_STARTUP_COST * sites_count
    overhead_budget = patient_budget * MONTHLY_OVERHEAD_RATE * 24  # 2yr trial
    total_budget = patient_budget + site_budget + overhead_budget

    # Calculate spent to date
    # Assume: sites fully paid, patients proportional, overhead proportional
    site_spent = site_budget  # Sites paid upfront
    patient_spent = cpp_budgeted * enrollment_actual
    overhead_spent = overhead_budget * (months_elapsed / 24)
    spent_to_date = site_spent + patient_spent + overhead_spent

    # Cap spent at total budget for display
    spent_to_date = min(spent_to_date, total_budget * 1.5)
    remaining = max(0, total_budget - spent_to_date)

    # Actual cost per patient (including overhead allocation)
    if enrollment_actual > 0:
        cpp_actual = (patient_spent + overhead_spent) / enrollment_actual
    else:
        cpp_actual = 0.0

    # Burn rate (monthly average)
    if months_elapsed > 0:
        monthly_burn = spent_to_date / months_elapsed
    else:
        monthly_burn = 0.0

    # Runway (months until budget exhausted at current burn)
    if monthly_burn > 0:
        runway = remaining / monthly_burn
    else:
        runway = float("inf")

    # Progress and efficiency metrics
    enrollment_progress = (
        enrollment_actual / enrollment_target if enrollment_target > 0
        else 0.0
    )
    budget_utilization = (
        spent_to_date / total_budget if total_budget > 0
        else 0.0
    )

    # Efficiency ratio: enrollment progress vs budget utilization
    # > 1.0 means more enrollment per dollar (good)
    # < 1.0 means spending faster than enrolling (bad)
    if budget_utilization > 0:
        efficiency_ratio = enrollment_progress / budget_utilization
    else:
        efficiency_ratio = 1.0

    is_over_budget = spent_to_date > total_budget

    return BudgetResult(
        total_budget=round(total_budget, 2),
        patient_budget=round(patient_budget, 2),
        site_budget=round(site_budget, 2),
        spent_to_date=round(spent_to_date, 2),
        remaining=round(remaining, 2),
        cost_per_patient_budgeted=round(cpp_budgeted, 2),
        cost_per_patient_actual=round(cpp_actual, 2),
        monthly_burn_rate=round(monthly_burn, 2),
        runway_months=round(runway, 1) if runway != float("inf") else None,
        budget_utilization=round(budget_utilization, 4),
        enrollment_progress=round(enrollment_progress, 4),
        is_over_budget=is_over_budget,
        efficiency_ratio=round(efficiency_ratio, 3),
    )


def format_currency(amount: float) -> str:
    """Format amount as currency string.

    Args:
        amount: Dollar amount.

    Returns:
        str: Formatted string (e.g., "$1.2M", "$450K").
    """
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    else:
        return f"${amount:.0f}"


def get_budget_summary(result: BudgetResult) -> dict:
    """Generate formatted budget summary for display.

    Args:
        result: BudgetResult from calculate_budget().

    Returns:
        dict: Formatted summary with display strings.
    """
    return {
        "total_budget_display": format_currency(result.total_budget),
        "spent_display": format_currency(result.spent_to_date),
        "remaining_display": format_currency(result.remaining),
        "burn_rate_display": f"{format_currency(result.monthly_burn_rate)}/mo",
        "runway_display": (
            f"{result.runway_months:.1f} months"
            if result.runway_months else "N/A"
        ),
        "utilization_display": f"{result.budget_utilization:.1%}",
        "progress_display": f"{result.enrollment_progress:.1%}",
        "efficiency_display": f"{result.efficiency_ratio:.2f}x",
        "status": (
            "OVER BUDGET" if result.is_over_budget
            else "ON TRACK" if result.efficiency_ratio >= 0.9
            else "AT RISK"
        ),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("COST MODEL MODULE TEST")
    print("=" * 60)

    # Test phase normalization
    print("\n1. Phase normalization:")
    print("-" * 40)
    test_phases = ["Phase 3", "PHASE2", "Phase 1/Phase 2", "NA", "N/A", ""]
    for p in test_phases:
        print(f"   '{p}' -> '{normalize_phase(p)}'")

    # Test cost lookup
    print("\n2. Cost per patient by phase and scenario:")
    print("-" * 40)
    for phase in ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]:
        costs = [get_cost_per_patient(phase, s) for s in ["low", "median", "high"]]
        print(f"   {phase}: ${costs[0]:,} / ${costs[1]:,} / ${costs[2]:,}")

    # Test full budget calculation
    print("\n3. Budget analysis (Phase 3, 200 target, 85 enrolled):")
    print("-" * 40)
    result = calculate_budget(
        phase="Phase 3",
        enrollment_target=200,
        enrollment_actual=85,
        sites_count=15,
        months_elapsed=8,
        scenario="median"
    )

    print(f"   Total Budget:      {format_currency(result.total_budget)}")
    print(f"   Patient Budget:    {format_currency(result.patient_budget)}")
    print(f"   Site Budget:       {format_currency(result.site_budget)}")
    print(f"   Spent to Date:     {format_currency(result.spent_to_date)}")
    print(f"   Remaining:         {format_currency(result.remaining)}")
    print(f"   Monthly Burn:      {format_currency(result.monthly_burn_rate)}")
    print(f"   Runway:            {result.runway_months} months")
    print(f"   Cost/Patient (B):  ${result.cost_per_patient_budgeted:,.0f}")
    print(f"   Cost/Patient (A):  ${result.cost_per_patient_actual:,.0f}")
    print(f"   Budget Used:       {result.budget_utilization:.1%}")
    print(f"   Enrollment:        {result.enrollment_progress:.1%}")
    print(f"   Efficiency:        {result.efficiency_ratio:.2f}x")

    # Test formatted summary
    print("\n4. Formatted summary for dashboard:")
    print("-" * 40)
    summary = get_budget_summary(result)
    for key, value in summary.items():
        print(f"   {key}: {value}")

    # Test different scenarios
    print("\n5. Scenario comparison (same trial, different cost assumptions):")
    print("-" * 40)
    for scenario in ["low", "median", "high"]:
        r = calculate_budget(
            phase="Phase 3",
            enrollment_target=200,
            enrollment_actual=85,
            sites_count=15,
            months_elapsed=8,
            scenario=scenario
        )
        print(f"   {scenario.upper():6s}: Budget={format_currency(r.total_budget):>8s}, "
              f"Spent={format_currency(r.spent_to_date):>8s}, "
              f"Runway={r.runway_months:.1f} mo")

    print("\n" + "=" * 60)
    print("All cost model tests completed!")
    print("=" * 60)
