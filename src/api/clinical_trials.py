# src/api/clinical_trials.py
"""ClinicalTrials.gov API wrapper for fetching trial data."""

import requests
from typing import Optional


BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
TIMEOUT = 30


def search_trials(
    condition: str,
    status: Optional[str] = "RECRUITING",
    page_size: int = 10
) -> dict:
    """Search clinical trials by condition.

    Args:
        condition: Medical condition to search for
            (e.g., "diabetes", "cancer").
        status: Trial status filter. Options include:
            RECRUITING, COMPLETED, ACTIVE_NOT_RECRUITING,
            NOT_YET_RECRUITING, TERMINATED, WITHDRAWN,
            SUSPENDED. Use None for all statuses.
        page_size: Number of results to return (max 1000).

    Returns:
        dict: JSON response containing trial data with keys:
            - studies: List of trial objects
            - totalCount: Total matching trials
            - nextPageToken: Token for pagination

    Raises:
        requests.exceptions.RequestException: If API call fails.
    """
    params = {
        "query.cond": condition,
        "pageSize": page_size,
        "fields": (
            "NCTId,BriefTitle,Phase,OverallStatus,"
            "EnrollmentCount,EnrollmentType,"
            "StartDate,PrimaryCompletionDate,"
            "LocationFacility,LeadSponsorName,"
            "Condition,InterventionName"
        )
    }

    if status:
        params["filter.overallStatus"] = status

    response = requests.get(BASE_URL, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    return response.json()


def get_trial_details(nct_id: str) -> dict:
    """Get detailed information for a specific trial.

    Args:
        nct_id: The NCT identifier (e.g., "NCT12345678").

    Returns:
        dict: Complete trial data including:
            - protocolSection: Core trial information
            - derivedSection: Computed fields
            - hasResults: Whether results are available

    Raises:
        requests.exceptions.RequestException: If API call fails.
        ValueError: If NCT ID format is invalid.
    """
    if not nct_id.startswith("NCT"):
        raise ValueError(f"Invalid NCT ID format: {nct_id}")

    url = f"{BASE_URL}/{nct_id}"
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()

    return response.json()


def parse_trial_summary(trial: dict) -> dict:
    """Extract key fields from a trial response.

    Args:
        trial: Raw trial data from API response.

    Returns:
        dict: Simplified trial summary with keys:
            - nct_id: Trial identifier
            - title: Brief title
            - phase: Trial phase
            - status: Current status
            - enrollment_target: Target enrollment
            - enrollment_type: ACTUAL or ESTIMATED
            - start_date: Trial start date
            - completion_date: Primary completion date
            - sponsor: Lead sponsor name
            - conditions: List of conditions
            - interventions: List of interventions
            - sites_count: Number of study sites
    """
    protocol = trial.get("protocolSection", {})
    id_module = protocol.get("identificationModule", {})
    status_module = protocol.get("statusModule", {})
    design_module = protocol.get("designModule", {})
    sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
    conditions_module = protocol.get("conditionsModule", {})
    interventions_module = protocol.get("armsInterventionsModule", {})
    contacts_module = protocol.get("contactsLocationsModule", {})

    # Count unique sites
    locations = contacts_module.get("locations", [])
    sites_count = len(locations)

    # Extract interventions
    interventions = interventions_module.get("interventions", [])
    intervention_names = [i.get("name", "") for i in interventions]

    # Get enrollment info
    enrollment_info = design_module.get("enrollmentInfo", {})

    return {
        "nct_id": id_module.get("nctId", ""),
        "title": id_module.get("briefTitle", ""),
        "phase": ",".join(design_module.get("phases", ["N/A"])),
        "status": status_module.get("overallStatus", ""),
        "enrollment_target": enrollment_info.get("count", 0),
        "enrollment_type": enrollment_info.get("type", ""),
        "start_date": status_module.get("startDateStruct", {}).get(
            "date", ""
        ),
        "completion_date": status_module.get(
            "primaryCompletionDateStruct", {}
        ).get("date", ""),
        "sponsor": sponsor_module.get("leadSponsor", {}).get("name", ""),
        "conditions": conditions_module.get("conditions", []),
        "interventions": intervention_names,
        "sites_count": sites_count
    }


if __name__ == "__main__":
    # Quick test of the API
    print("Testing ClinicalTrials.gov API...")
    print("-" * 50)

    # Search for diabetes trials
    results = search_trials("diabetes", status="RECRUITING", page_size=3)
    studies = results.get("studies", [])

    print(f"Found {results.get('totalCount', 0)} total recruiting trials")
    print(f"Showing first {len(studies)} results:\n")

    for study in studies:
        summary = parse_trial_summary(study)
        print(f"NCT ID: {summary['nct_id']}")
        print(f"Title: {summary['title'][:60]}...")
        print(f"Phase: {summary['phase']}")
        print(f"Status: {summary['status']}")
        print(f"Enrollment: {summary['enrollment_target']}")
        print(f"Sites: {summary['sites_count']}")
        print("-" * 50)
