# TrialMetrics — Clinical Trial Analytics Dashboard
## Project Specification & Build Guide

> **Purpose:** This document provides complete context for an AI assistant to help build this hackathon project from scratch.

---

## 🎯 Hackathon Context

| Item | Details |
|------|---------|
| **Event** | 305 Hackathon — January 2026 Edition |
| **Theme** | AI in Healthcare & Biotech |
| **Track** | Track Competition 1 — Tech Build |
| **Prompt** | "Build a virtual research or clinical-trial dashboard for tracking metrics over time" |
| **Deadline** | January 24, 2026 @ 8:00 PM ET |
| **Participant** | Nathan Ramos, CFA (Solo) |

---

## 📊 Project Overview

### The Problem

Clinical operations teams use Veeva/Medidata for enrollment tracking. Biostatisticians calculate power separately in SAS/R. Finance tracks budget in spreadsheets. **No unified view exists** that combines:

1. Real-time statistical power analysis
2. Enrollment forecasting with confidence intervals
3. Budget burn rate and runway tracking
4. AI-powered trial summaries

### The Solution

**TrialMetrics** — A dashboard that unifies statistical rigor with financial discipline for clinical trials. It pulls data from ClinicalTrials.gov and provides:

- Statistical power analysis (real-time, not static)
- Enrollment forecasting using OLS regression with HAC-robust standard errors
- Budget tracking using a synthetic cost model
- AI-generated natural language trial summaries

### Why This Is Unique

The developer (Nathan) is a **CFA Charterholder** with 10+ years of quantitative research experience. This project applies **portfolio management discipline** to clinical research — a novel angle no competitor offers.

---

## 🛠️ Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Frontend** | Streamlit | 1.31.0 |
| **Data Fetching** | Requests | 2.31.0 |
| **Statistical Analysis** | SciPy, Statsmodels | 1.12.0, 0.14.1 |
| **Data Manipulation** | Pandas, NumPy | 2.1.4, 1.26.3 |
| **Visualization** | Plotly | 5.18.0 |
| **AI Integration** | OpenAI | 1.12.0 |
| **Environment** | Python | 3.11+ |

### requirements.txt

```
streamlit==1.31.0
pandas==2.1.4
numpy==1.26.3
scipy==1.12.0
statsmodels==0.14.1
plotly==5.18.0
requests==2.31.0
openai==1.12.0
python-dotenv==1.0.0
```

---

## 📁 Project Structure

```
trialmetrics/
├── README.md                    # Project documentation (for Devpost/GitHub)
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (OPENAI_API_KEY)
├── .gitignore                   # Git ignore file
├── app.py                       # Main Streamlit application
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── clinical_trials.py   # ClinicalTrials.gov API wrapper
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── power_analysis.py    # Statistical power calculations
│   │   ├── enrollment_forecast.py  # Regression-based forecasting
│   │   └── cost_model.py        # Synthetic financial model
│   ├── ai/
│   │   ├── __init__.py
│   │   └── summarizer.py        # OpenAI/Gemini integration
│   └── utils/
│       ├── __init__.py
│       └── helpers.py           # Utility functions
├── data/
│   └── cost_benchmarks.json     # Industry cost benchmarks (optional)
├── tests/
│   └── test_analysis.py         # Unit tests (optional)
├── presentation/
│   └── slides.pptx              # Demo presentation
└── demo_video.mp4               # 5-minute demo video
```

---

## 🔧 Core Modules Specification

### 1. ClinicalTrials.gov API Wrapper (`src/api/clinical_trials.py`)

**Purpose:** Fetch clinical trial data from the public API.

**API Documentation:** https://clinicaltrials.gov/data-api/api

**Key Functions:**
- `search_trials(condition, status, page_size)` — Search trials by condition
- `get_trial_details(nct_id)` — Get detailed info for a specific trial

**Data Fields Available:**
- NCT ID, Title, Phase, Status
- Enrollment (target and actual)
- Start date, Primary completion date
- Number of sites, Sponsor
- Conditions, Interventions

**Example API Call:**
```python
import requests

url = "https://clinicaltrials.gov/api/v2/studies"
params = {
    "query.cond": "diabetes",
    "filter.overallStatus": "RECRUITING",
    "pageSize": 10
}
response = requests.get(url, params=params, timeout=30)
data = response.json()
```

---

### 2. Statistical Power Analysis (`src/analysis/power_analysis.py`)

**Purpose:** Calculate statistical power and required sample sizes.

**Key Functions:**
- `calculate_power_two_sample(n_per_group, effect_size, alpha)` — Power for two-sample t-test
- `calculate_required_sample_size(target_power, effect_size, alpha)` — Required N for target power
- `generate_power_curve(max_n, effect_size, alpha)` — Data for power curve visualization

**Statistical Methods:**
- Two-sample t-test power using non-central t distribution
- Cohen's d effect size (default: 0.5 = medium effect)
- Alpha = 0.05 (standard significance level)

**Formula Reference:**
```
Power = 1 - P(T < t_critical | H1 is true)

Where:
- T follows non-central t distribution
- Non-centrality parameter = effect_size * sqrt(n/2)
- df = 2n - 2
```

---

### 3. Enrollment Forecasting (`src/analysis/enrollment_forecast.py`)

**Purpose:** Predict trial completion date using regression.

**Key Functions:**
- `forecast_enrollment(enrollment_history, target_enrollment, confidence_level)` — Predict completion

**Statistical Methods:**
- OLS regression: `enrolled = β₀ + β₁*days + ε`
- HAC-robust standard errors (Newey-West) for autocorrelated data
- Confidence intervals using robust standard errors

**Developer Note:** Nathan has extensive experience with Statsmodels and HAC-robust SE from his quantitative finance work. This is a direct skill transfer.

---

### 4. Synthetic Cost Model (`src/analysis/cost_model.py`)

**Purpose:** Estimate trial costs (no real cost data is publicly available).

**Cost Benchmarks (per patient, USD):**
| Phase | Low | Median | High |
|-------|-----|--------|------|
| Phase 1 | $15,000 | $25,000 | $40,000 |
| Phase 2 | $25,000 | $35,000 | $50,000 |
| Phase 3 | $35,000 | $45,000 | $70,000 |
| Phase 4 | $10,000 | $20,000 | $35,000 |

**Site startup cost:** $50,000 per site (fixed)

**Key Functions:**
- `calculate_budget(phase, enrollment_target, enrollment_actual, sites_count, months_elapsed)` — Full budget analysis

**Output Metrics:**
- Total budget, Spent to date, Remaining
- Cost per patient (actual vs. budgeted)
- Burn rate (monthly)
- Runway (months until budget exhausted)

---

### 5. AI Summarizer (`src/ai/summarizer.py`)

**Purpose:** Generate natural language trial status summaries.

**API:** OpenAI GPT-4o (or GPT-4o-mini for cost savings)

**Key Functions:**
- `generate_trial_summary(trial_data, power_result, budget_result, forecast_result)` — 3-sentence executive summary

**Prompt Template:**
```
You are a clinical trial analyst. Summarize this trial's status:

Trial: {title}
Phase: {phase}
Enrollment: {actual}/{target}
Statistical Power: {power}%
Budget Spent: ${spent} of ${total}
Projected Completion: {date}

Provide a 3-sentence executive summary highlighting:
1. Current enrollment progress
2. Statistical concerns (if power < 80%)
3. Budget status and runway
```

---

## 🖥️ Dashboard UI Specification

### Layout

```
┌────────────────────────────────────────────────────────────────────┐
│ 📊 TrialMetrics — Clinical Trial Analytics Dashboard              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  SIDEBAR                    │  MAIN CONTENT                        │
│  ─────────                  │  ────────────                        │
│  🔍 Find a Trial            │                                      │
│  [Condition input]          │  ROW 1: Key Metrics (4 columns)      │
│  [Search button]            │  ┌──────┬──────┬──────┬──────┐      │
│                             │  │Enroll│Power │Budget│Runway│      │
│  Select Trial:              │  │423/  │78%   │$2.3M │4.2   │      │
│  [Dropdown]                 │  │500   │      │spent │months│      │
│                             │  └──────┴──────┴──────┴──────┘      │
│  Parameters:                │                                      │
│  Effect Size: [0.5]         │  ROW 2: Charts (2 columns)           │
│  Alpha: [0.05]              │  ┌─────────────┬─────────────┐      │
│  Cost Scenario: [median]    │  │Power Curve  │Budget Donut │      │
│                             │  │(Plotly)     │(Plotly)     │      │
│                             │  └─────────────┴─────────────┘      │
│                             │                                      │
│                             │  ROW 3: AI Summary                   │
│                             │  ┌───────────────────────────┐      │
│                             │  │🤖 AI-Powered Trial Summary│      │
│                             │  │[Generate Summary button]  │      │
│                             │  │                           │      │
│                             │  │"This Phase 3 diabetes..." │      │
│                             │  └───────────────────────────┘      │
│                             │                                      │
└────────────────────────────────────────────────────────────────────┘
```

### Key UI Components

1. **Sidebar:** Trial search and parameter inputs
2. **Metric Cards:** Enrollment, Power, Budget, Runway (use `st.metric`)
3. **Power Curve Chart:** Line chart with 80% threshold line (Plotly)
4. **Budget Donut:** Spent vs. Remaining (Plotly pie chart with hole)
5. **AI Summary:** Info box with generated text

---

## 📅 7-Day Build Plan

| Day | Date | Tasks | Deliverables |
|-----|------|-------|--------------|
| **Day 1** | Jan 17 (Fri) | Project setup, API integration | Working API fetcher |
| **Day 2** | Jan 18 (Sat) | Power analysis module | Power calculator tested |
| **Day 3** | Jan 19 (Sun) | Enrollment forecasting | Regression model working |
| **Day 4** | Jan 20 (Mon) | Cost model + Budget tracker | Financial metrics |
| **Day 5** | Jan 21 (Tue) | Streamlit dashboard UI | Basic dashboard |
| **Day 6** | Jan 22 (Wed) | AI integration + Polish | Feature complete |
| **Day 7** | Jan 23 (Thu) | Testing, demo video, slides | Submission ready |
| **Day 8** | Jan 24 (Fri) | Buffer + Submit by 8 PM ET | ✅ Submitted |

---

## 📝 Submission Requirements Checklist

### GitHub Repository
- [ ] Public repository
- [ ] All source code included
- [ ] README.md with:
  - [ ] Project description
  - [ ] Theme alignment explanation
  - [ ] Track selection: "Track 1 — Tech Build"
  - [ ] Technologies used
  - [ ] Setup & installation instructions
  - [ ] Team members (Nathan Ramos, CFA — Solo)
  - [ ] Demo video link
  - [ ] Screenshots

### Demo Video
- [ ] Maximum 5 minutes
- [ ] MP4 format
- [ ] Uploaded to repository
- [ ] Link in README

### Presentation Slides
- [ ] .pptx, .pptx, or .pdf format
- [ ] Public Google Slides link for live demo
- [ ] Slide 1: Project name, team, track
- [ ] Slide 2: Theme alignment, challenge selected

### Devpost Submission
- [ ] Project name format: "TrialMetrics — Track 1"
- [ ] GitHub repo link
- [ ] Track clearly selected
- [ ] Submitted before 8:00 PM ET on Jan 24

### Live Demo
- [ ] Check presentation order: https://docs.google.com/spreadsheets/d/12XawEQd-wbwozsYDKwPMr8Uj3yJcgdBinVPxudjWX_w/edit?usp=sharing
- [ ] Zoom link: https://codecrunch-zoom.vercel.app
- [ ] Be in waiting room 5 minutes before slot
- [ ] 2-minute presentation + 1-minute Q&A

---

## 👤 Developer Context

**Nathan Ramos, CFA**
- Senior Portfolio Manager & Quantitative Researcher
- 10+ years experience in systematic investment strategies
- Built `pyfinlab` — 166-module proprietary research platform
- Expert in: Statsmodels, OLS regression, HAC-robust SE, Hypothesis testing
- AI Integration experience: OpenAI and Google Gemini

**Skill Transfer:**
- Portfolio optimization → Trial resource optimization
- Equity factor models → Patient risk factor models
- Financial dashboards → Clinical trial dashboards
- HAC-robust SE for time-series → HAC-robust SE for enrollment data

---

## 🔗 Important Links

| Resource | URL |
|----------|-----|
| ClinicalTrials.gov API | https://clinicaltrials.gov/data-api/api |
| Hackathon Event Page | https://codecrunchglobal.vercel.app/2026-305hackjan2026.html |
| Submission Requirements | https://codecrunchglobal.vercel.app/hack2-submissions-req.html |
| Judging Criteria | https://codecrunchglobal.vercel.app/hack3-judging-criteria.html |
| Demo Presentation Order | https://docs.google.com/spreadsheets/d/12XawEQd-wbwozsYDKwPMr8Uj3yJcgdBinVPxudjWX_w/edit?usp=sharing |
| Zoom for Live Demo | https://codecrunch-zoom.vercel.app |

---

## 📜 Code Style Guidelines

Per user preferences:
- Follow **PEP 8** style guide
- **Google-style docstrings** (max 72 chars per line)
- **Max 80 characters** per line of code
- First line of each Python file: filepath relative to project root
- No trailing whitespaces

---

## 🚀 Getting Started Commands

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set environment variable
set OPENAI_API_KEY=your-key-here  # Windows
# export OPENAI_API_KEY=your-key-here  # Mac/Linux

# Run the dashboard
streamlit run app.py
```

---

## 📌 AI Assistant Instructions

When helping build this project:

1. **Start with the API integration** (Day 1) — Get ClinicalTrials.gov data flowing
2. **Build modules in order** — API → Power Analysis → Forecast → Cost → AI
3. **Test each module independently** before integrating into dashboard
4. **Follow the project structure** exactly as specified
5. **Use the code style guidelines** (PEP 8, Google docstrings, 80 char lines)
6. **Reference the statistical methods** described for power analysis and forecasting
7. **The developer is experienced** — No need to over-explain Python basics

**Priority for hackathon:** Working demo > Perfect code. Focus on functionality first.

---

*Document created: January 20, 2026*
*For: 305 Hackathon — January 2026 Edition*
