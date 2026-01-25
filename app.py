# app.py
"""TrialMetrics - Clinical Trial Analytics Dashboard."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from src.api.clinical_trials import (
    search_trials,
    get_trial_details,
    parse_trial_summary
)
from src.analysis.power_analysis import (
    analyze_trial_power,
    generate_power_curve
)
from src.analysis.enrollment_forecast import (
    generate_synthetic_enrollment,
    forecast_enrollment,
    generate_forecast_series
)
from src.analysis.cost_model import (
    calculate_budget,
    get_budget_summary,
    format_currency
)
from src.ai.summarizer import get_trial_summary

# Page configuration
st.set_page_config(
    page_title="TrialMetrics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #5A7894;
        margin-top: 0;
    }

    /* Metric card styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 600;
    }

    /* Status badges */
    .status-on-track {
        background-color: #10B981;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
    }
    .status-at-risk {
        background-color: #F59E0B;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
    }
    .status-critical {
        background-color: #EF4444;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
    }

    /* Info box - works in both light and dark mode */
    .info-box {
        background-color: rgba(59, 130, 246, 0.1);
        border-left: 4px solid #3B82F6;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        color: inherit;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render the dashboard header."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(
            '<p class="main-header">📊 TrialMetrics</p>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<p class="sub-header">'
            'Clinical Trial Analytics Dashboard</p>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"<p style='text-align: right; color: #888;'>"
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>",
            unsafe_allow_html=True
        )


def render_sidebar():
    """Render the sidebar with trial search and parameters."""
    with st.sidebar:
        st.markdown("### 🔍 Find a Trial")

        # Search input
        condition = st.text_input(
            "Condition",
            value="diabetes",
            placeholder="e.g., diabetes, cancer, alzheimer",
            help="Enter a disease or health condition to search for "
                 "clinical trials. Examples: 'breast cancer', 'diabetes', "
                 "'alzheimer', 'hypertension'. This searches the "
                 "ClinicalTrials.gov database."
        )

        # Status filter
        status_options = [
            "RECRUITING",
            "ACTIVE_NOT_RECRUITING",
            "COMPLETED",
            "NOT_YET_RECRUITING"
        ]
        status = st.selectbox(
            "Status",
            status_options,
            index=0,
            help="Filter trials by their current status:\n\n"
                 "**RECRUITING** = Currently enrolling patients\n\n"
                 "**ACTIVE_NOT_RECRUITING** = Ongoing but not enrolling\n\n"
                 "**COMPLETED** = Trial has finished\n\n"
                 "**NOT_YET_RECRUITING** = Approved but not started"
        )

        # Search button
        search_clicked = st.button("🔎 Search Trials", use_container_width=True)

        # Store search results in session state
        if search_clicked or "trials" not in st.session_state:
            with st.spinner("Searching ClinicalTrials.gov..."):
                try:
                    results = search_trials(
                        condition=condition,
                        status=status,
                        page_size=20
                    )
                    trials = results.get("studies", [])
                    st.session_state.trials = [
                        parse_trial_summary(t) for t in trials
                    ]
                except Exception as e:
                    st.error(f"API Error: {str(e)}")
                    st.session_state.trials = []

        # Trial selector
        st.markdown("---")
        st.markdown("### 📋 Select Trial")
        st.caption(
            "Choose a trial from search results to view detailed analytics."
        )

        if st.session_state.get("trials"):
            trial_options = {
                f"{t['nct_id']} - {t['title'][:40]}...": t['nct_id']
                for t in st.session_state.trials
            }
            selected_label = st.selectbox(
                "Trial",
                options=list(trial_options.keys()),
                label_visibility="collapsed",
                help="Select a clinical trial to analyze. Each trial has a "
                     "unique NCT ID (National Clinical Trial identifier) "
                     "assigned by ClinicalTrials.gov."
            )
            st.session_state.selected_nct_id = trial_options.get(selected_label)
        else:
            st.info("No trials found. Try a different search.")
            st.session_state.selected_nct_id = None

        # Analysis parameters
        st.markdown("---")
        st.markdown("### ⚙️ Parameters")

        effect_size = st.slider(
            "Effect Size (Cohen's d)",
            min_value=0.1,
            max_value=1.0,
            value=0.5,
            step=0.1,
            help="Effect size measures how big a difference the treatment "
                 "makes compared to placebo. Cohen's d is a standardized "
                 "measure:\n\n"
                 "**0.2** = Small effect (subtle improvement)\n\n"
                 "**0.5** = Medium effect (noticeable improvement)\n\n"
                 "**0.8** = Large effect (substantial improvement)\n\n"
                 "Larger effects are easier to detect with fewer patients. "
                 "Most clinical trials assume medium effect (0.5)."
        )

        alpha = st.selectbox(
            "Significance Level (α)",
            options=[0.01, 0.05, 0.10],
            index=1,
            help="The probability of concluding a treatment works when it "
                 "actually doesn't (false positive rate):\n\n"
                 "**0.01 (1%)** = Very strict, fewer false positives\n\n"
                 "**0.05 (5%)** = Standard for most trials\n\n"
                 "**0.10 (10%)** = More lenient, higher false positive risk\n\n"
                 "Lower values require larger sample sizes to achieve "
                 "the same statistical power."
        )

        cost_scenario = st.selectbox(
            "Cost Scenario",
            options=["low", "median", "high"],
            index=1,
            help="Estimated cost per patient based on industry benchmarks:\n\n"
                 "**Low** = 25th percentile (~$36K-59K/patient)\n\n"
                 "**Median** = 50th percentile (~$41K-69K/patient)\n\n"
                 "**High** = 75th percentile (~$48K-83K/patient)\n\n"
                 "Costs vary by trial phase. Phase III trials typically "
                 "cost more per patient than Phase I/II."
        )

        return {
            "effect_size": effect_size,
            "alpha": alpha,
            "cost_scenario": cost_scenario
        }


def render_metrics(
    trial: dict,
    power_result: dict,
    budget_result,
    enrollment_actual: int
):
    """Render the key metrics row with clean annotations and tooltips."""
    col1, col2, col3, col4 = st.columns(4)

    enrollment_target = trial.get('enrollment_target', 0)
    enrollment_type = trial.get('enrollment_type', 'ESTIMATED')

    with col1:
        if enrollment_type == 'ACTUAL':
            st.metric(label="Enrollment (Actual)", value=f"{enrollment_target}")
            st.markdown(
                '<span title="This is verified enrollment data from the '
                'trial registry." style="cursor: help;">'
                '✓ Real data</span>',
                unsafe_allow_html=True
            )
        else:
            progress = enrollment_actual / enrollment_target if enrollment_target else 0
            st.metric(
                label="Enrollment",
                value=f"{enrollment_actual}/{enrollment_target}"
            )
            st.markdown(
                '<span title="Current enrollment is estimated based on '
                'trial start date and typical recruitment rates. '
                'ClinicalTrials.gov does not provide real-time enrollment '
                'counts for recruiting trials." '
                'style="color: #888; font-size: 0.85em; cursor: help;">'
                'ⓘ Estimated</span>',
                unsafe_allow_html=True
            )

    with col2:
        power_pct = power_result['power_at_actual'] * 100
        is_underpowered = power_result['is_underpowered']
        st.metric(label="Statistical Power", value=f"{power_pct:.0f}%")
        if is_underpowered:
            st.markdown(
                '<span title="Power below 80% means the study may not '
                'detect a true treatment effect. Scale: &lt;80% = '
                'Underpowered (red), ≥80% = Adequate (green)." '
                'style="color: #EF4444; cursor: help;">'
                '⚠️ Underpowered</span>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<span title="Power ≥80% is the standard threshold for '
                'clinical trials. Scale: &lt;80% = Underpowered (red), '
                '≥80% = Adequate (green)." '
                'style="color: #10B981; cursor: help;">'
                '✓ Adequate</span>',
                unsafe_allow_html=True
            )

    with col3:
        st.metric(
            label="Budget Spent",
            value=format_currency(budget_result.spent_to_date)
        )
        total = format_currency(budget_result.total_budget)
        pct_spent = (budget_result.spent_to_date /
                     budget_result.total_budget * 100)
        st.markdown(
            f'<span title="Total estimated budget based on phase, '
            f'enrollment target, and site count using industry benchmarks. '
            f'Currently {pct_spent:.0f}% utilized." '
            f'style="color: #888; font-size: 0.85em; cursor: help;">'
            f'of {total}</span>',
            unsafe_allow_html=True
        )

    with col4:
        runway_display = (
            f"{budget_result.runway_months:.1f}"
            if budget_result.runway_months else "N/A"
        )
        st.metric(label="Runway (months)", value=runway_display)
        efficiency = budget_result.efficiency_ratio
        if efficiency >= 1.0:
            st.markdown(
                f'<span title="Efficiency = (Enrollment Progress) / '
                f'(Budget Spent %). Values ≥1.0 mean enrollment is '
                f'on pace with spending. Scale: &lt;1.0 = Over budget '
                f'(red), ≥1.0 = On/under budget (green)." '
                f'style="color: #10B981; cursor: help;">'
                f'Efficiency: {efficiency:.2f}x</span>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<span title="Efficiency = (Enrollment Progress) / '
                f'(Budget Spent %). Values &lt;1.0 mean spending '
                f'outpaces enrollment. Scale: &lt;1.0 = Over budget '
                f'(red), ≥1.0 = On/under budget (green)." '
                f'style="color: #EF4444; cursor: help;">'
                f'Efficiency: {efficiency:.2f}x</span>',
                unsafe_allow_html=True
            )


def render_power_chart(
    effect_size: float,
    alpha: float,
    target_n: int,
    actual_n: int
):
    """Render the power curve chart.

    Args:
        effect_size: Cohen's d effect size.
        alpha: Significance level.
        target_n: Target total enrollment.
        actual_n: Current actual enrollment.
    """
    sizes, powers = generate_power_curve(
        max_n=max(200, target_n + 50),
        effect_size=effect_size,
        alpha=alpha,
        step=5
    )

    fig = go.Figure()

    # Power curve
    fig.add_trace(go.Scatter(
        x=sizes,
        y=[p * 100 for p in powers],
        mode='lines',
        name='Power',
        line=dict(color='#3B82F6', width=3),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.1)'
    ))

    # 80% threshold line
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color="#10B981",
        annotation_text="80% threshold",
        annotation_position="right"
    )

    # Current enrollment marker (at ACTUAL enrollment, not target)
    if actual_n > 0:
        from src.analysis.power_analysis import calculate_power_two_sample
        current_power = calculate_power_two_sample(
            actual_n // 2, effect_size, alpha
        ) * 100
        fig.add_trace(go.Scatter(
            x=[actual_n // 2],
            y=[current_power],
            mode='markers',
            name='Current Trial',
            marker=dict(size=12, color='#EF4444', symbol='diamond')
        ))

    fig.update_layout(
        title="Statistical Power Curve",
        xaxis_title="Sample Size (per group)",
        yaxis_title="Power (%)",
        yaxis=dict(range=[0, 100]),
        showlegend=True,
        legend=dict(yanchor="bottom", y=0.02, xanchor="right", x=0.98),
        height=350,
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return fig


def render_budget_chart(budget_result):
    """Render the budget donut chart."""
    labels = ['Spent', 'Remaining']
    values = [budget_result.spent_to_date, budget_result.remaining]
    colors = ['#3B82F6', '#E5E7EB']

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.65,
        marker_colors=colors,
        textinfo='label+percent',
        textposition='outside',
        showlegend=False
    )])

    # Add center text
    fig.add_annotation(
        text=f"<b>{format_currency(budget_result.total_budget)}</b><br>Total Budget",
        x=0.5, y=0.5,
        font_size=14,
        showarrow=False
    )

    fig.update_layout(
        title="Budget Utilization",
        height=350,
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return fig


def render_enrollment_chart(trial: dict, enrollment_actual: int):
    """Render enrollment forecast chart.

    Args:
        trial: Trial data dictionary.
        enrollment_actual: Current actual enrollment count.
    """
    # Generate synthetic data for demo
    # NOTE: ClinicalTrials.gov doesn't provide historical enrollment data
    # We simulate a realistic trajectory for demonstration purposes

    start_date_str = trial.get('start_date', '2024-01-01')
    if not start_date_str:
        start_date_str = '2024-01-01'

    # Parse start date
    try:
        if len(start_date_str) == 7:  # YYYY-MM format
            start_date_str = f"{start_date_str}-01"
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    except ValueError:
        start_dt = datetime(2024, 1, 1)
        start_date_str = '2024-01-01'

    target = trial.get('enrollment_target', 100) or 100

    # Calculate days elapsed from trial start to today
    today = datetime.now()
    days_since_start = (today - start_dt).days

    # Cap at reasonable range (don't simulate more than 3 years back)
    days_elapsed = min(max(days_since_start, 30), 1095)

    # Generate synthetic enrollment history ending at actual enrollment
    history = generate_synthetic_enrollment(
        start_date=start_date_str,
        target=target,
        days_elapsed=days_elapsed,
        seed=hash(trial.get('nct_id', '')) % 10000,
        final_enrollment=enrollment_actual
    )

    # Generate forecast series
    series = generate_forecast_series(
        enrollment_history=history,
        target_enrollment=target,
        forecast_days=365
    )

    fig = go.Figure()

    # Actual enrollment
    actual = series[series['type'] == 'actual']
    fig.add_trace(go.Scatter(
        x=actual['date'],
        y=actual['enrolled'],
        mode='lines',
        name='Actual',
        line=dict(color='#3B82F6', width=2)
    ))

    # Forecast
    forecast = series[series['type'] == 'forecast']
    fig.add_trace(go.Scatter(
        x=forecast['date'],
        y=forecast['enrolled'],
        mode='lines',
        name='Forecast',
        line=dict(color='#3B82F6', width=2, dash='dash')
    ))

    # Confidence interval
    fig.add_trace(go.Scatter(
        x=list(forecast['date']) + list(forecast['date'][::-1]),
        y=list(forecast['ci_upper']) + list(forecast['ci_lower'][::-1]),
        fill='toself',
        fillcolor='rgba(59, 130, 246, 0.35)',
        line=dict(color='rgba(59, 130, 246, 0.5)'),
        name='95% CI',
        showlegend=True
    ))

    # Target line
    fig.add_hline(
        y=target,
        line_dash="dash",
        line_color="#10B981",
        annotation_text=f"Target: {target}",
        annotation_position="right"
    )

    fig.update_layout(
        title="Enrollment Forecast",
        xaxis_title="Date",
        yaxis_title="Patients Enrolled",
        showlegend=True,
        legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.02),
        height=350,
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return fig


def render_trial_details(trial: dict):
    """Render trial details section."""
    st.markdown("### 📄 Trial Details")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**NCT ID:** {trial['nct_id']}")
        st.markdown(f"**Phase:** {trial['phase']}")
        st.markdown(f"**Status:** {trial['status']}")
        st.markdown(f"**Sponsor:** {trial['sponsor']}")

    with col2:
        st.markdown(f"**Start Date:** {trial['start_date'] or 'N/A'}")
        st.markdown(f"**Completion:** {trial['completion_date'] or 'N/A'}")
        st.markdown(f"**Sites:** {trial['sites_count']}")
        st.markdown(f"**Enrollment:** {trial['enrollment_target']}")

    st.markdown("**Conditions:**")
    st.write(", ".join(trial.get('conditions', ['N/A'])))

    st.markdown("**Interventions:**")
    st.write(", ".join(trial.get('interventions', ['N/A'])) or 'N/A')


def render_ai_summary(
    trial: dict,
    power_result: dict,
    budget_result,
    forecast_result: dict = None
):
    """Render AI-powered trial summary section."""
    st.markdown("### 🤖 AI-Powered Trial Summary")

    # Check for API key
    import os
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))

    # Auto-generate summary for the current trial
    current_nct = trial.get('nct_id', '')
    cached_nct = st.session_state.get('summary_nct_id', '')

    # Generate if trial changed or no summary exists
    if current_nct != cached_nct or not st.session_state.get("ai_summary"):
        with st.spinner("Generating executive summary..."):
            summary, source = get_trial_summary(
                trial_data=trial,
                power_result=power_result,
                budget_result=budget_result,
                forecast_result=forecast_result,
                use_ai=has_api_key
            )

            # Cache the summary
            st.session_state.ai_summary = summary
            st.session_state.ai_source = source
            st.session_state.summary_nct_id = current_nct

    # Display summary
    source = st.session_state.get("ai_source", "template")
    source_label = "🤖 AI Generated" if source == "ai" else "📋 Template"

    st.markdown(
        f'<div class="info-box">'
        f'<strong>{source_label}</strong><br><br>'
        f'{st.session_state.ai_summary}'
        f'</div>',
        unsafe_allow_html=True
    )


def main():
    """Main dashboard application."""
    render_header()
    st.markdown("---")

    # Sidebar returns parameters
    params = render_sidebar()

    # Main content
    if st.session_state.get("selected_nct_id"):
        # Get trial details
        nct_id = st.session_state.selected_nct_id
        trial = next(
            (t for t in st.session_state.trials if t['nct_id'] == nct_id),
            None
        )

        if trial:
            # Display trial title
            st.markdown(f"## {trial['title']}")

            # Run analyses using REAL data from ClinicalTrials.gov
            enrollment_target = trial.get('enrollment_target', 100) or 100
            enrollment_type = trial.get('enrollment_type', 'ESTIMATED')
            sites_count = trial.get('sites_count', 10) or 10

            # Use real enrollment if available, otherwise estimate based on
            # trial duration (recruiting trials typically ~60% enrolled)
            if enrollment_type == 'ACTUAL':
                # This IS the real current enrollment
                enrollment_actual = enrollment_target
            else:
                # Estimate based on trial progress
                start_date = trial.get('start_date', '')
                if start_date:
                    try:
                        if len(start_date) == 7:
                            start_date = f"{start_date}-01"
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        days_elapsed = (datetime.now() - start_dt).days
                        # Estimate ~60% enrollment for active trials
                        progress_ratio = min(0.85, max(0.3, days_elapsed / 1095))
                        enrollment_actual = int(enrollment_target * progress_ratio)
                    except ValueError:
                        enrollment_actual = int(enrollment_target * 0.6)
                else:
                    enrollment_actual = int(enrollment_target * 0.6)

            power_result = analyze_trial_power(
                enrollment_target=enrollment_target,
                enrollment_actual=enrollment_actual,
                effect_size=params['effect_size'],
                alpha=params['alpha']
            )

            budget_result = calculate_budget(
                phase=trial.get('phase', 'NA'),
                enrollment_target=enrollment_target,
                enrollment_actual=enrollment_actual,
                sites_count=sites_count,
                months_elapsed=6,
                scenario=params['cost_scenario']
            )

            # ROW 1: Key Metrics
            render_metrics(trial, power_result, budget_result, enrollment_actual)
            st.markdown("---")

            # ROW 2: Charts
            col1, col2 = st.columns(2)

            with col1:
                power_fig = render_power_chart(
                    effect_size=params['effect_size'],
                    alpha=params['alpha'],
                    target_n=enrollment_target,
                    actual_n=enrollment_actual
                )
                st.plotly_chart(power_fig, use_container_width=True)

            with col2:
                budget_fig = render_budget_chart(budget_result)
                st.plotly_chart(budget_fig, use_container_width=True)

            # ROW 3: Enrollment Forecast
            st.markdown("---")
            enrollment_fig = render_enrollment_chart(trial, enrollment_actual)
            st.plotly_chart(enrollment_fig, use_container_width=True)

            # ROW 4: Trial Details and AI Summary
            st.markdown("---")
            col1, col2 = st.columns([1, 1])

            with col1:
                render_trial_details(trial)

            with col2:
                render_ai_summary(
                    trial=trial,
                    power_result=power_result,
                    budget_result=budget_result
                )

            # Data source transparency
            st.markdown("---")
            st.caption(
                "**Data Sources:** Trial metadata from ClinicalTrials.gov (live). "
                "Enrollment time series and budget figures are modeled projections "
                "based on industry benchmarks — actual data requires integration "
                "with sponsor's clinical trial management system."
            )

    else:
        # No trial selected
        st.info(
            "👈 Use the sidebar to search for clinical trials and select one "
            "to view analytics."
        )

        # Demo mode
        st.markdown("### 📊 Demo Mode")
        st.markdown(
            "Try searching for conditions like **diabetes**, **breast cancer**, "
            "or **alzheimer** to see real trial data from ClinicalTrials.gov."
        )


if __name__ == "__main__":
    main()
