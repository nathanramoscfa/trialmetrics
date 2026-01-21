# src/analysis/enrollment_forecast.py
"""Enrollment forecasting using OLS regression with HAC-robust SE."""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional
import statsmodels.api as sm


def generate_synthetic_enrollment(
    start_date: str,
    target: int,
    days_elapsed: int,
    enrollment_rate: float = 0.8,
    noise_std: float = 0.15,
    seed: Optional[int] = None
) -> pd.DataFrame:
    """Generate synthetic enrollment data for testing/demo.

    Creates realistic enrollment trajectory with random variation
    around a linear trend. Uses Poisson-like discrete enrollment
    with stochastic rounding for realistic patient counts.

    Args:
        start_date: Trial start date (YYYY-MM-DD format).
        target: Target enrollment.
        days_elapsed: Number of days since trial start.
        enrollment_rate: Fraction of "ideal" daily rate (1.0 = on track).
        noise_std: Standard deviation of noise as fraction of mean.
        seed: Random seed for reproducibility.

    Returns:
        pd.DataFrame: Enrollment history with columns:
            - date: Observation date
            - day: Days since start (0-indexed)
            - enrolled: Cumulative enrollment
            - daily: Daily new enrollments
    """
    if seed is not None:
        np.random.seed(seed)

    # Calculate ideal daily rate assuming 1.5-year completion
    ideal_daily_rate = target / 547  # ~1.5 years
    actual_rate = ideal_daily_rate * enrollment_rate

    dates = []
    days = []
    enrolled = []
    daily = []

    cumulative = 0
    start = datetime.strptime(start_date, "%Y-%m-%d")

    for d in range(days_elapsed + 1):
        if d == 0:
            new_patients = 0
        else:
            # Use Poisson distribution for realistic discrete enrollment
            lambda_param = max(0.1, actual_rate * (1 + noise_std *
                               np.random.randn()))
            new_patients = np.random.poisson(lambda_param)

        # Cap at target
        new_patients = min(new_patients, target - cumulative)
        cumulative += new_patients

        dates.append(start + timedelta(days=d))
        days.append(d)
        enrolled.append(cumulative)
        daily.append(new_patients)

    return pd.DataFrame({
        "date": dates,
        "day": days,
        "enrolled": enrolled,
        "daily": daily
    })


def fit_enrollment_model(
    enrollment_history: pd.DataFrame,
    use_hac: bool = True,
    maxlags: Optional[int] = None
) -> dict:
    """Fit OLS regression model to enrollment data.

    Model: enrolled = beta_0 + beta_1 * day + epsilon

    Args:
        enrollment_history: DataFrame with 'day' and 'enrolled' columns.
        use_hac: If True, use Newey-West HAC-robust standard errors.
        maxlags: Max lags for HAC estimator. If None, uses automatic
            selection based on sample size: int(4*(n/100)^(2/9)).

    Returns:
        dict: Model results containing:
            - beta_0: Intercept estimate
            - beta_1: Slope (daily enrollment rate)
            - se_beta_1: Standard error of slope
            - t_stat: t-statistic for slope
            - p_value: p-value for slope significance
            - r_squared: Model R-squared
            - residuals: Model residuals
            - model: Fitted statsmodels OLS object
    """
    y = enrollment_history["enrolled"].values
    X = sm.add_constant(enrollment_history["day"].values)

    model = sm.OLS(y, X).fit()

    if use_hac:
        # Newey-West HAC-robust standard errors
        n = len(y)
        if maxlags is None:
            maxlags = int(4 * (n / 100) ** (2 / 9))
        model = model.get_robustcov_results(
            cov_type="HAC",
            maxlags=maxlags
        )

    return {
        "beta_0": model.params[0],
        "beta_1": model.params[1],
        "se_beta_1": model.bse[1],
        "t_stat": model.tvalues[1],
        "p_value": model.pvalues[1],
        "r_squared": model.rsquared,
        "residuals": model.resid,
        "model": model
    }


def forecast_enrollment(
    enrollment_history: pd.DataFrame,
    target_enrollment: int,
    confidence_level: float = 0.95,
    use_hac: bool = True
) -> dict:
    """Forecast trial completion date with confidence intervals.

    Uses OLS regression to project when target enrollment will be
    reached, with HAC-robust standard errors for valid inference
    on autocorrelated enrollment data.

    Args:
        enrollment_history: DataFrame with 'day', 'date', 'enrolled'.
        target_enrollment: Target number of patients to enroll.
        confidence_level: Confidence level for interval (default 95%).
        use_hac: Use Newey-West HAC standard errors.

    Returns:
        dict: Forecast results containing:
            - current_enrolled: Latest enrollment count
            - current_day: Days since trial start
            - daily_rate: Estimated daily enrollment rate
            - days_to_target: Estimated days to reach target
            - completion_date: Projected completion date
            - completion_ci_lower: Lower bound of CI
            - completion_ci_upper: Upper bound of CI
            - is_on_track: True if projected to complete on time
            - model_stats: Dictionary of model statistics
    """
    # Fit the model
    model_results = fit_enrollment_model(enrollment_history, use_hac=use_hac)

    beta_0 = model_results["beta_0"]
    beta_1 = model_results["beta_1"]
    se_beta_1 = model_results["se_beta_1"]

    # Current status
    current_day = enrollment_history["day"].max()
    current_enrolled = enrollment_history["enrolled"].iloc[-1]
    start_date = enrollment_history["date"].iloc[0]

    # Days remaining to target: solve target = beta_0 + beta_1 * day
    if beta_1 > 0:
        days_to_target_point = (target_enrollment - beta_0) / beta_1
        days_remaining = max(0, days_to_target_point - current_day)
    else:
        # No progress or negative trend
        days_to_target_point = float("inf")
        days_remaining = float("inf")

    # Confidence interval using delta method
    # Var(days_to_target) approx = (1/beta_1)^2 * Var(beta_1)
    # for the slope component (ignoring intercept uncertainty)
    from scipy import stats as scipy_stats

    alpha = 1 - confidence_level
    z = scipy_stats.norm.ppf(1 - alpha / 2)

    if beta_1 > 0 and se_beta_1 > 0:
        # Approximate SE of days to target
        se_days = (target_enrollment - beta_0) / (beta_1 ** 2) * se_beta_1

        days_ci_lower = max(0, days_to_target_point - z * se_days)
        days_ci_upper = days_to_target_point + z * se_days
    else:
        days_ci_lower = float("inf")
        days_ci_upper = float("inf")

    # Convert to dates
    if days_to_target_point != float("inf"):
        completion_date = start_date + timedelta(days=int(days_to_target_point))
        ci_lower_date = start_date + timedelta(days=int(days_ci_lower))
        ci_upper_date = start_date + timedelta(days=int(days_ci_upper))
    else:
        completion_date = None
        ci_lower_date = None
        ci_upper_date = None

    return {
        "current_enrolled": int(current_enrolled),
        "target_enrollment": target_enrollment,
        "current_day": int(current_day),
        "daily_rate": round(beta_1, 2),
        "days_to_target": (
            int(days_to_target_point) if days_to_target_point != float("inf")
            else None
        ),
        "days_remaining": (
            int(days_remaining) if days_remaining != float("inf")
            else None
        ),
        "completion_date": completion_date,
        "completion_ci_lower": ci_lower_date,
        "completion_ci_upper": ci_upper_date,
        "confidence_level": confidence_level,
        "model_stats": {
            "intercept": round(beta_0, 2),
            "slope": round(beta_1, 4),
            "slope_se": round(se_beta_1, 4),
            "t_stat": round(model_results["t_stat"], 2),
            "p_value": round(model_results["p_value"], 6),
            "r_squared": round(model_results["r_squared"], 4)
        }
    }


def generate_forecast_series(
    enrollment_history: pd.DataFrame,
    target_enrollment: int,
    forecast_days: int = 180
) -> pd.DataFrame:
    """Generate forecast time series for visualization.

    Creates a DataFrame with historical data and projected future
    enrollment suitable for Plotly charts.

    Args:
        enrollment_history: Historical enrollment data.
        target_enrollment: Target enrollment.
        forecast_days: Number of days to forecast ahead.

    Returns:
        pd.DataFrame: Combined historical and forecast data with:
            - date: Date
            - day: Days since start
            - enrolled: Actual or projected enrollment
            - type: 'actual' or 'forecast'
            - ci_lower: Lower confidence bound (forecast only)
            - ci_upper: Upper confidence bound (forecast only)
    """
    model_results = fit_enrollment_model(enrollment_history, use_hac=True)
    beta_0 = model_results["beta_0"]
    beta_1 = model_results["beta_1"]
    se_beta_1 = model_results["se_beta_1"]

    # Historical data
    historical = enrollment_history[["date", "day", "enrolled"]].copy()
    historical["type"] = "actual"
    historical["ci_lower"] = np.nan
    historical["ci_upper"] = np.nan

    # Forecast data
    last_day = enrollment_history["day"].max()
    start_date = enrollment_history["date"].iloc[0]

    forecast_days_range = range(last_day + 1, last_day + forecast_days + 1)
    forecast_dates = [
        start_date + timedelta(days=d) for d in forecast_days_range
    ]

    # Point forecast
    forecast_enrolled = [
        min(target_enrollment, beta_0 + beta_1 * d)
        for d in forecast_days_range
    ]

    # Confidence intervals (approximate)
    z = 1.96  # 95% CI
    ci_lower = [
        max(0, beta_0 + (beta_1 - z * se_beta_1) * d)
        for d in forecast_days_range
    ]
    ci_upper = [
        min(target_enrollment * 1.2, beta_0 + (beta_1 + z * se_beta_1) * d)
        for d in forecast_days_range
    ]

    forecast = pd.DataFrame({
        "date": forecast_dates,
        "day": list(forecast_days_range),
        "enrolled": forecast_enrolled,
        "type": "forecast",
        "ci_lower": ci_lower,
        "ci_upper": ci_upper
    })

    return pd.concat([historical, forecast], ignore_index=True)


if __name__ == "__main__":
    print("=" * 60)
    print("ENROLLMENT FORECAST MODULE TEST")
    print("=" * 60)

    # Generate synthetic enrollment data
    print("\n1. Generating synthetic enrollment data...")
    print("-" * 40)
    history = generate_synthetic_enrollment(
        start_date="2025-01-01",
        target=200,
        days_elapsed=180,
        enrollment_rate=0.7,  # Slightly behind schedule
        seed=42
    )
    print(f"   Days elapsed: {history['day'].max()}")
    print(f"   Current enrollment: {history['enrolled'].iloc[-1]}")
    print(f"   Daily enrollments (last 5): {list(history['daily'].tail())}")

    # Fit model
    print("\n2. Fitting OLS model with HAC-robust SE...")
    print("-" * 40)
    model = fit_enrollment_model(history, use_hac=True)
    print(f"   Intercept (beta_0): {model['beta_0']:.2f}")
    print(f"   Slope (beta_1): {model['beta_1']:.4f} patients/day")
    print(f"   HAC Robust SE: {model['se_beta_1']:.4f}")
    print(f"   t-statistic: {model['t_stat']:.2f}")
    print(f"   R-squared: {model['r_squared']:.4f}")

    # Forecast
    print("\n3. Forecasting completion date...")
    print("-" * 40)
    forecast = forecast_enrollment(history, target_enrollment=200)
    print(f"   Current: {forecast['current_enrolled']}/{forecast['target_enrollment']}")
    print(f"   Daily rate: {forecast['daily_rate']} patients/day")
    print(f"   Days remaining: {forecast['days_remaining']}")
    if forecast['completion_date']:
        print(f"   Projected completion: {forecast['completion_date'].strftime('%Y-%m-%d')}")
        print(f"   95% CI: [{forecast['completion_ci_lower'].strftime('%Y-%m-%d')}, "
              f"{forecast['completion_ci_upper'].strftime('%Y-%m-%d')}]")

    # Generate forecast series
    print("\n4. Generating forecast series for visualization...")
    print("-" * 40)
    series = generate_forecast_series(history, target_enrollment=200)
    print(f"   Total rows: {len(series)}")
    print(f"   Actual rows: {len(series[series['type'] == 'actual'])}")
    print(f"   Forecast rows: {len(series[series['type'] == 'forecast'])}")

    print("\n" + "=" * 60)
    print("All enrollment forecast tests completed!")
    print("=" * 60)
