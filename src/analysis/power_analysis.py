# src/analysis/power_analysis.py
"""Statistical power analysis for clinical trial sample size planning."""

import numpy as np
from scipy import stats
from typing import Tuple


def calculate_power_two_sample(
    n_per_group: int,
    effect_size: float = 0.5,
    alpha: float = 0.05
) -> float:
    """Calculate statistical power for a two-sample t-test.

    Uses the non-central t-distribution to compute the probability
    of correctly rejecting H0 when H1 is true.

    Args:
        n_per_group: Sample size per group (total N = 2 * n_per_group).
        effect_size: Cohen's d effect size. Conventions:
            - 0.2 = small effect
            - 0.5 = medium effect
            - 0.8 = large effect
        alpha: Significance level (Type I error rate).

    Returns:
        float: Statistical power (probability of detecting true effect),
            value between 0 and 1.

    Example:
        >>> power = calculate_power_two_sample(50, effect_size=0.5)
        >>> print(f"Power: {power:.1%}")
        Power: 69.7%
    """
    if n_per_group < 2:
        return 0.0

    # Degrees of freedom for two-sample t-test
    df = 2 * n_per_group - 2

    # Non-centrality parameter
    # For two-sample t-test: ncp = d * sqrt(n/2) where n is per group
    ncp = effect_size * np.sqrt(n_per_group / 2)

    # Critical t-value for alpha (two-tailed)
    t_critical = stats.t.ppf(1 - alpha / 2, df)

    # Power = P(|T| > t_critical | H1 true)
    # Using non-central t distribution
    # Power = P(T > t_crit) + P(T < -t_crit) under non-central t
    power = 1 - stats.nct.cdf(t_critical, df, ncp) + \
        stats.nct.cdf(-t_critical, df, ncp)

    return float(power)


def calculate_required_sample_size(
    target_power: float = 0.80,
    effect_size: float = 0.5,
    alpha: float = 0.05,
    max_n: int = 10000
) -> int:
    """Calculate required sample size per group to achieve target power.

    Uses binary search to find the minimum n_per_group that achieves
    the specified power level.

    Args:
        target_power: Desired statistical power (default 0.80 = 80%).
        effect_size: Cohen's d effect size.
        alpha: Significance level.
        max_n: Maximum sample size to search (prevents infinite loop).

    Returns:
        int: Required sample size per group. Total trial enrollment
            would be 2 * this value for a two-arm study.

    Example:
        >>> n = calculate_required_sample_size(target_power=0.80)
        >>> print(f"Need {n} per group ({2*n} total)")
        Need 64 per group (128 total)
    """
    # Binary search for minimum n
    low, high = 2, max_n

    while low < high:
        mid = (low + high) // 2
        power = calculate_power_two_sample(mid, effect_size, alpha)

        if power >= target_power:
            high = mid
        else:
            low = mid + 1

    return low


def generate_power_curve(
    max_n: int = 200,
    effect_size: float = 0.5,
    alpha: float = 0.05,
    step: int = 5
) -> Tuple[list, list]:
    """Generate data for a power curve visualization.

    Creates arrays of sample sizes and corresponding power values
    suitable for plotting.

    Args:
        max_n: Maximum sample size per group to calculate.
        effect_size: Cohen's d effect size.
        alpha: Significance level.
        step: Increment between sample size points.

    Returns:
        Tuple[list, list]: Two lists:
            - sample_sizes: List of n_per_group values
            - powers: Corresponding power values

    Example:
        >>> sizes, powers = generate_power_curve(max_n=100)
        >>> # Use with Plotly: fig = px.line(x=sizes, y=powers)
    """
    sample_sizes = list(range(step, max_n + 1, step))
    powers = [
        calculate_power_two_sample(n, effect_size, alpha)
        for n in sample_sizes
    ]

    return sample_sizes, powers


def analyze_trial_power(
    enrollment_target: int,
    enrollment_actual: int,
    effect_size: float = 0.5,
    alpha: float = 0.05
) -> dict:
    """Comprehensive power analysis for a clinical trial.

    Analyzes current power based on actual enrollment and compares
    to target enrollment power.

    Args:
        enrollment_target: Planned total enrollment (both arms).
        enrollment_actual: Current actual enrollment (both arms).
        effect_size: Expected Cohen's d effect size.
        alpha: Significance level.

    Returns:
        dict: Power analysis results containing:
            - n_per_group_target: Target n per arm
            - n_per_group_actual: Current n per arm
            - power_at_target: Power if target enrollment achieved
            - power_at_actual: Power at current enrollment
            - power_gap: Difference (target - actual power)
            - is_underpowered: True if actual power < 80%
            - recommended_n: Sample size needed for 80% power
            - enrollment_shortfall: Additional patients needed
    """
    # Assume equal allocation (1:1 randomization)
    n_target = enrollment_target // 2
    n_actual = enrollment_actual // 2

    power_target = calculate_power_two_sample(n_target, effect_size, alpha)
    power_actual = calculate_power_two_sample(n_actual, effect_size, alpha)

    recommended_n = calculate_required_sample_size(
        target_power=0.80,
        effect_size=effect_size,
        alpha=alpha
    )

    # Calculate enrollment shortfall
    shortfall = max(0, (recommended_n * 2) - enrollment_actual)

    return {
        "n_per_group_target": n_target,
        "n_per_group_actual": n_actual,
        "power_at_target": round(power_target, 4),
        "power_at_actual": round(power_actual, 4),
        "power_gap": round(power_target - power_actual, 4),
        "is_underpowered": power_actual < 0.80,
        "recommended_n_per_group": recommended_n,
        "recommended_total": recommended_n * 2,
        "enrollment_shortfall": shortfall
    }


if __name__ == "__main__":
    # Test the power analysis functions
    print("=" * 60)
    print("POWER ANALYSIS MODULE TEST")
    print("=" * 60)

    # Test 1: Basic power calculation
    print("\n1. Power at various sample sizes (d=0.5, alpha=0.05):")
    print("-" * 40)
    for n in [20, 40, 64, 80, 100]:
        power = calculate_power_two_sample(n, effect_size=0.5)
        print(f"   n={n:3d} per group -> Power = {power:.1%}")

    # Test 2: Required sample size
    print("\n2. Required sample size for 80% power:")
    print("-" * 40)
    for d in [0.2, 0.5, 0.8]:
        n = calculate_required_sample_size(target_power=0.80, effect_size=d)
        print(f"   Effect size d={d} -> n={n} per group ({2*n} total)")

    # Test 3: Power curve data
    print("\n3. Power curve generation:")
    print("-" * 40)
    sizes, powers = generate_power_curve(max_n=100, step=20)
    print(f"   Generated {len(sizes)} data points")
    print(f"   Sample sizes: {sizes}")
    print(f"   Powers: {[f'{p:.2f}' for p in powers]}")

    # Test 4: Trial power analysis
    print("\n4. Trial power analysis (target=200, actual=120):")
    print("-" * 40)
    result = analyze_trial_power(
        enrollment_target=200,
        enrollment_actual=120,
        effect_size=0.5
    )
    for key, value in result.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2%}")
        else:
            print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("All power analysis tests completed!")
    print("=" * 60)
