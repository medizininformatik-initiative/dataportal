"""S7: TORCH consent rules on crafted patients.

TO-2  only .8 and .6 are evaluated and both are required, .45/.46 extend .6 back
TO-3  encounter shift: only inpatient (IMP) stays, at most TORCH_ENCOUNTER_SHIFT_MAX_DAYS (7)
TO-4  overlapping permit and deny: deny wins, listed in reports/consent-conflicts.csv
TO-5  consents processed by dateTime, not by resource order; a retro deny resets .6
TO-10 a reference to a resource outside consent is masked, a must-have one drops the
      resource, Provenance has no dangling targets
TO-6  DISABLE_CONSENT_CALCULATION=true switches consent off, and without Einwilligung
      criteria TORCH enforces no consent

Rules: https://medizininformatik-initiative.github.io/torch/implementation/consent.html
Each patient has Conditions on known dates. A Condition is extracted when its date lies
in the final .6 period. The patients are passed as `patient` parameters, so the cohort
query is bypassed and the MII test data is not touched. The crafted resources are
deleted afterwards, because tests/node counts Consents.
"""

from __future__ import annotations

import pytest

from helpers import wait_for_url
from torch_client import (
    CONSENT_CODE_PREFIX,
    CONSENT_PROFILE,
    CONSENT_SYSTEM,
    DIAGNOSE_PROFILE,
    PATIENT_PROFILE,
    TorchError,
    condition_crtdl,
    consent_inclusion,
    delete_resources,
    extract,
    put_resources,
    submit,
    torch_variant,
    wait,
)

END = "2054-01-01"
# TORCH shifts only by Encounters of this profile (ConsentAdjuster, TORCH 1.1.0)
ENCOUNTER_PROFILE = "https://www.medizininformatik-initiative.de/fhir/core/modul-fall/StructureDefinition/KontaktGesundheitseinrichtung"
PERMIT_ALL = [("6", "permit"), ("7", "permit"), ("8", "permit")]


def patient(pid: str) -> dict:
    return {"resourceType": "Patient", "id": pid, "meta": {"profile": [PATIENT_PROFILE]}, "gender": "female", "birthDate": "1970-01-01"}


def condition(pid: str, date: str) -> dict:
    return {
        "resourceType": "Condition",
        "id": f"{pid}-{date}",
        "meta": {"profile": [DIAGNOSE_PROFILE]},
        "code": {"coding": [{"system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "version": "2024", "code": "I10"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "onsetDateTime": date,
        "recordedDate": date,
    }


def encounter(pid: str, kind: str, start: str, end: str) -> dict:
    return {
        "resourceType": "Encounter",
        "id": f"{pid}-encounter",
        "meta": {"profile": [ENCOUNTER_PROFILE]},
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": kind},
        "subject": {"reference": f"Patient/{pid}"},
        "period": {"start": start, "end": end},
    }


def consent(pid: str, n: int, signed: str, provisions: list[tuple[str, str, str, str]]) -> dict:
    """A MII Einwilligung signed at `signed` with (code suffix, permit|deny, start, end) provisions."""
    return {
        "resourceType": "Consent",
        "id": f"{pid}-consent-{n}",
        "meta": {"profile": [CONSENT_PROFILE]},
        "status": "active",
        "scope": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/consentscope", "code": "research"}]},
        "category": [{"coding": [{"system": "http://loinc.org", "code": "57016-8"}]}],
        "patient": {"reference": f"Patient/{pid}"},
        "dateTime": signed,
        "policy": [{"uri": "urn:oid:2.16.840.1.113883.3.1937.777.24.2.1791"}],
        "provision": {
            "type": "deny",
            "provision": [
                {
                    "type": kind,
                    "period": {"start": start, "end": end},
                    "code": [{"coding": [{"system": CONSENT_SYSTEM, "code": f"{CONSENT_CODE_PREFIX}.{suffix}"}]}],
                }
                for suffix, kind, start, end in provisions
            ],
        },
    }


def provisions(codes: list[tuple[str, str]], start: str, end: str = END) -> list[tuple[str, str, str, str]]:
    return [(code, kind, start, end) for code, kind in codes]


# Patient id -> (resources besides Patient and Conditions, condition dates)
CASES = {
    # TO-2: .6 window from the signing date
    "s7-base": ([lambda p: consent(p, 1, "2024-03-01", provisions(PERMIT_ALL, "2024-03-01"))], ["2024-02-01", "2024-04-01"]),
    # TO-2: .45/.46 extend .6 back to 1900 when the CRTDL asks for them
    "s7-retro": (
        [lambda p: consent(p, 1, "2024-03-01", provisions(PERMIT_ALL + [("45", "permit"), ("46", "permit")], "2024-03-01"))],
        ["2024-02-01", "2024-04-01"],
    ),
    # TO-3a: consent 3 days into an inpatient stay
    "s7-shift-imp": (
        [lambda p: consent(p, 1, "2024-03-04", provisions(PERMIT_ALL, "2024-03-04")), lambda p: encounter(p, "IMP", "2024-03-01", "2024-03-10")],
        ["2024-02-20", "2024-03-02"],
    ),
    # TO-3b: same in an ambulatory encounter
    "s7-shift-amb": (
        [lambda p: consent(p, 1, "2024-03-04", provisions(PERMIT_ALL, "2024-03-04")), lambda p: encounter(p, "AMB", "2024-03-01", "2024-03-10")],
        ["2024-03-02"],
    ),
    # TO-3c: inpatient stay that began 13 days before the consent
    "s7-shift-long": (
        [lambda p: consent(p, 1, "2024-03-04", provisions(PERMIT_ALL, "2024-03-04")), lambda p: encounter(p, "IMP", "2024-02-20", "2024-03-10")],
        ["2024-03-02"],
    ),
    # TO-4: .6 permit and deny overlap in one signing event
    "s7-conflict": (
        [lambda p: consent(p, 1, "2024-03-01", provisions(PERMIT_ALL, "2024-03-01") + [("6", "deny", "2024-05-01", "2024-06-30")])],
        ["2024-04-01", "2024-05-15", "2024-07-15"],
    ),
    # TO-5: a later revocation stored before the earlier consent
    "s7-order": (
        [
            lambda p: consent(p, 1, "2024-07-01", [("6", "deny", "2024-07-01", END)]),
            lambda p: consent(p, 2, "2024-03-01", provisions(PERMIT_ALL, "2024-03-01")),
        ],
        ["2024-04-01", "2024-08-01"],
    ),
    # TO-5: a later .46 deny discards the .6 history, the .6 permit of the same event stays
    "s7-retro-reset": (
        [
            lambda p: consent(p, 1, "2024-03-01", provisions(PERMIT_ALL + [("46", "permit")], "2024-03-01")),
            lambda p: consent(p, 2, "2024-07-01", provisions([("6", "permit"), ("8", "permit"), ("46", "deny")], "2024-07-01")),
        ],
        ["2024-02-01", "2024-04-01", "2024-08-01"],
    ),
    # TO-2, TO-6: no consent at all
    "s7-no-consent": ([], ["2024-04-01"]),
}

STANDARD = consent_inclusion("8", "6")
RETRO = consent_inclusion("8", "6", "45", "46")


# TO-10: a Condition inside the consent window references an Encounter before it
REFS = "s7-refs"


def reference_resources() -> list[dict]:
    old_encounter = encounter(REFS, "AMB", "2024-01-01", "2024-01-05")
    referencing = condition(REFS, "2024-04-01") | {"encounter": {"reference": f"Encounter/{old_encounter['id']}"}}
    return [patient(REFS), consent(REFS, 1, "2024-03-01", provisions(PERMIT_ALL, "2024-03-01")), old_encounter, referencing]


def crafted_resources() -> list[dict]:
    resources = reference_resources()
    for pid, (extra, dates) in CASES.items():
        resources.append(patient(pid))
        resources += [build(pid) for build in extra]
        resources += [condition(pid, d) for d in dates]
    return resources


@pytest.fixture(scope="module", autouse=True)
def crafted_patients():
    wait_for_url("http://localhost:8086/actuator/health")
    resources = crafted_resources()
    put_resources(resources)
    yield
    delete_resources(resources)


@pytest.fixture(scope="module")
def runs() -> dict:
    """One TORCH job per CRTDL over all crafted patients, with consent diagnostics."""
    patients = list(CASES)
    return {
        "standard": extract(condition_crtdl(STANDARD), patients, diagnostics=True),
        "retro": extract(condition_crtdl(RETRO), patients, diagnostics=True),
        "none": extract(condition_crtdl(None), patients),
    }


def extracted_dates(result, pid: str) -> list[str]:
    return sorted(
        c["recordedDate"] for c in result.resources("Condition") if c["subject"]["reference"] == f"Patient/{pid}"
    )


def final_periods(result, pid: str) -> list[tuple[str, str]]:
    return [(r["Period-Start"], r["Period-End"]) for r in result.report("final-periods") if r["Patient-ID"] == pid]


EXPECTED = {
    # (CRTDL, patient): extracted condition dates
    ("standard", "s7-base"): ["2024-04-01"],
    ("standard", "s7-retro"): ["2024-04-01"],
    ("retro", "s7-retro"): ["2024-02-01", "2024-04-01"],
    ("standard", "s7-shift-imp"): ["2024-03-02"],
    ("standard", "s7-shift-amb"): [],
    ("standard", "s7-shift-long"): [],
    ("standard", "s7-conflict"): ["2024-04-01", "2024-07-15"],
    ("standard", "s7-order"): ["2024-04-01"],
    ("retro", "s7-retro-reset"): ["2024-08-01"],
    ("standard", "s7-no-consent"): [],
}


@pytest.mark.parametrize("crtdl, pid", EXPECTED, ids=[f"{c}-{p}" for c, p in EXPECTED])
def test_conditions_inside_the_consent_window_are_extracted(runs, crtdl, pid):
    assert extracted_dates(runs[crtdl], pid) == EXPECTED[(crtdl, pid)]


def test_retro_consent_extends_the_window_to_1900(runs):
    assert final_periods(runs["retro"], "s7-retro") == [("1900-01-01", END)]
    assert final_periods(runs["standard"], "s7-retro") == [("2024-03-01", END)]


def test_inpatient_encounter_shifts_the_window_start(runs):
    assert final_periods(runs["standard"], "s7-shift-imp") == [("2024-03-01", END)]
    assert final_periods(runs["standard"], "s7-shift-amb") == [("2024-03-04", END)]
    assert final_periods(runs["standard"], "s7-shift-long") == [("2024-03-04", END)]


def test_permit_deny_conflict_is_reported(runs):
    rows = runs["standard"].report("consent-conflicts")
    assert rows, "no consent-conflicts.csv for an overlapping permit and deny"
    conflicts = [r for r in rows if r["Patient-ID"] == "s7-conflict"]
    assert [(r["Code"], r["Overlap-Start"], r["Overlap-End"]) for r in conflicts] == [
        (f"{CONSENT_CODE_PREFIX}.6", "2024-05-01", "2024-06-30")
    ]
    assert {r["Patient-ID"] for r in rows} == {"s7-conflict"}


def test_patient_without_consent_is_excluded(runs):
    exclusions = runs["standard"].report("patient-exclusions")
    assert ("CONSENT_FETCH", "s7-no-consent") in {(r["Stage"], r["Patient-ID"]) for r in exclusions}


def reference_crtdl(must_have: bool) -> dict:
    crtdl = condition_crtdl(STANDARD)
    groups = crtdl["dataExtraction"]["attributeGroups"]
    groups[1]["attributes"].append({"attributeRef": "Condition.encounter", "mustHave": must_have, "linkedGroups": ["encounter"]})
    groups.append({
        "id": "encounter",
        "name": "Encounter",
        "groupReference": ENCOUNTER_PROFILE,
        "includeReferenceOnly": True,
        "attributes": [{"attributeRef": "Encounter.period", "mustHave": False}],
    })
    return crtdl


def test_reference_outside_consent_is_masked():
    result = extract(reference_crtdl(must_have=False), [REFS])
    [referencing] = result.resources("Condition")
    assert referencing["encounter"] == {"_reference": {"extension": [{"url": "http://hl7.org/fhir/StructureDefinition/data-absent-reason", "valueCode": "masked"}]}}
    assert result.resources("Encounter") == []
    exported = {f"{r['resourceType']}/{r['id']}" for r in result.resources()}
    targets = {t["reference"] for p in result.resources("Provenance") for t in p["target"]}
    assert targets and targets <= exported


def test_unmet_must_have_reference_drops_the_resource():
    result = extract(reference_crtdl(must_have=True), [REFS])
    assert result.resources("Condition") == []
    reasons = {(r["Reason"], r["Resource-ID"]) for r in result.report("resource-exclusions")}
    assert ("MUST_HAVE", f"Condition/{REFS}-2024-04-01") in reasons


def test_without_consent_criteria_everything_is_extracted(runs):
    for pid, (_, dates) in CASES.items():
        assert extracted_dates(runs["none"], pid) == sorted(dates), pid


@pytest.mark.parametrize(
    "inclusion",
    [consent_inclusion("6"), consent_inclusion("8")],
    ids=["only-6", "only-8"],
)
def test_consent_without_both_8_and_6_is_rejected(inclusion):
    with pytest.raises(TorchError) as error:
        wait(submit(condition_crtdl(inclusion), list(CASES)))
    assert error.value.status == 400, error.value


def test_combined_consent_key_extracts_nothing():
    """The combined keys of the old portal (e.g. yes-yes-no-yes) are gone since alpha.19.
    TORCH 1.1.0 rejects a CRTDL with only one of .8 and .6 (400, see above). With neither,
    it accepts the CRTDL and excludes every patient at the consent fetch."""
    combined = [[{
        "termCodes": [{"code": "yes-yes-no-yes", "system": "fdpg.consent.combined", "display": "combined"}],
        "context": {"code": "Einwilligung", "display": "Einwilligung", "system": "fdpg.mii.cds", "version": "1.0.0"},
    }]]
    result = extract(condition_crtdl(combined), list(CASES))
    assert result.resources() == []
    assert result.summary["Patient-Exclusions"]["CONSENT_FETCH"] == len(CASES)


# --- TORCH config variants (TO-3d, TO-6) ------------------------------------------------


def test_encounter_shift_can_be_switched_off():
    """TO-3d: case TO-3a with TORCH_ENABLE_ENCOUNTER_SHIFT=false."""
    with torch_variant({"TORCH_ENABLE_ENCOUNTER_SHIFT": "false"}) as torch:
        result = extract(condition_crtdl(STANDARD), ["s7-shift-imp"], diagnostics=True, torch=torch)
    assert final_periods(result, "s7-shift-imp") == [("2024-03-04", END)]
    assert extracted_dates(result, "s7-shift-imp") == []


def test_consent_calculation_can_be_switched_off():
    """TO-6: with DISABLE_CONSENT_CALCULATION=true a consent CRTDL extracts every patient."""
    with torch_variant({"DISABLE_CONSENT_CALCULATION": "true"}) as torch:
        result = extract(condition_crtdl(STANDARD), list(CASES), torch=torch)
    for pid, (_, dates) in CASES.items():
        assert extracted_dates(result, pid) == sorted(dates), pid
