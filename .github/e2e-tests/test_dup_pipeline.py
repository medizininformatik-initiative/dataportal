"""Verifies that the example DUP project's DIMP de-identification config
(data-node/example-dup-project/example-project_dimp_dup_base.yaml) is picked
up dynamically on every pipeline run (aether's experimental_v3
anonymization_config), without needing to restart fhir-pseudonymizer.

Runs the pipeline twice:
- "before": an empty fhirPathRules list, so DIMP applies no transformation
  at all and every element passes through raw (plaintext ids, full-precision
  birthDates, unredacted identifiers).
- "after": the real, unmodified base config.

Each test then checks that a given rule genuinely flips the output between
the two runs, rather than just asserting the "after" shape in isolation -
otherwise the assertions could pass even if DIMP silently ignored the config
change and both runs happened to look similar.
"""

from __future__ import annotations

import csv
import pathlib
import re
import subprocess
from typing import NamedTuple

import pytest

from conftest import DATA_NODE_DIR, run_aether_pipeline, wait_for_url

PROJECT_DIR = DATA_NODE_DIR / "example-dup-project"
DUP_YAML = PROJECT_DIR / "example-project_dimp_dup_base.yaml"
PIPELINE_CONFIG = "example-project-pipeline.yml"
CRTDL = "example-project-crtdl.json"

CRYPTO_HASH_KEY = "d5c00fe954186e0f2da921cbecfb5765df115ea236188aee0cb020e50be2c89d"
EMPTY_DIMP_YAML = f"""\
---
fhirVersion: R4
parameters:
  cryptoHashKey: {CRYPTO_HASH_KEY}
fhirPathRules: []
"""

# after generalization: at most year-month, never year-month-day
BIRTHDATE_RE = re.compile(r"^\d{2,4}(-\d{2})?$")
# raw, un-generalized source dates always carry full year-month-day precision
FULL_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HASHED_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class Run(NamedTuple):
    csv_dir: pathlib.Path


@pytest.fixture(autouse=True)
def _wait_for_pipeline_services():
    wait_for_url("http://localhost:8086/actuator/health")  # torch
    wait_for_url("http://localhost:8083/fhir/metadata")  # dimp
    wait_for_url("http://localhost:8089/v1/namespaces")  # vfps
    wait_for_url("http://localhost:8088/", expect_status=None)  # fhir-flattener has no health route


def _run_pipeline() -> Run:
    subprocess.run(
        ["bash", "example-project-create-namespaces-vfps.sh"],
        cwd=PROJECT_DIR,
        check=True,
    )
    job_id = run_aether_pipeline(PROJECT_DIR, PIPELINE_CONFIG, CRTDL)
    return Run(csv_dir=PROJECT_DIR / "jobs" / job_id / "csv")


def _read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _column(csv_dir: pathlib.Path, filename: str, column: str) -> list[str]:
    return [row[column] for row in _read_csv(csv_dir / filename)]


@pytest.fixture(scope="module")
def before_and_after() -> tuple[Run, Run]:
    original_yaml = DUP_YAML.read_text()
    assert CRYPTO_HASH_KEY in original_yaml, (
        f"expected to find cryptoHashKey {CRYPTO_HASH_KEY!r} in {DUP_YAML} - has it changed?"
    )

    try:
        DUP_YAML.write_text(EMPTY_DIMP_YAML)
        before = _run_pipeline()

        DUP_YAML.write_text(original_yaml)
        after = _run_pipeline()
    finally:
        DUP_YAML.write_text(original_yaml)

    return before, after


def test_cryptohash_is_applied_dynamically(before_and_after: tuple[Run, Run]):
    before, after = before_and_after
    before_ids = _column(before.csv_dir, "patients.csv", "id")
    after_ids = _column(after.csv_dir, "patients.csv", "id")
    assert before_ids and after_ids

    assert not any(HASHED_ID_RE.match(value) for value in before_ids), (
        "expected raw, un-hashed Patient ids with an empty DIMP config, found a cryptoHash-shaped id"
    )
    assert all(HASHED_ID_RE.match(value) for value in after_ids), (
        "expected every Patient id to be cryptoHash'd once the real DIMP config was applied"
    )


def test_birthdate_generalization_is_applied_dynamically(before_and_after: tuple[Run, Run]):
    before, after = before_and_after
    before_birthdates = _column(before.csv_dir, "patients.csv", "Patient_birthDate")
    after_birthdates = _column(after.csv_dir, "patients.csv", "Patient_birthDate")
    assert before_birthdates and after_birthdates

    for value in after_birthdates:
        assert value == "" or BIRTHDATE_RE.match(value), f"unexpected Patient_birthDate value: {value!r}"

    assert any(FULL_DATE_RE.match(value) for value in before_birthdates), (
        "expected some full year-month-day Patient_birthDate values with an empty DIMP config, found none"
    )
    assert not any(FULL_DATE_RE.match(value) for value in after_birthdates), (
        "expected no full year-month-day Patient_birthDate values once the real DIMP config's "
        "birthDate generalization rule was applied"
    )


def test_identifier_pseudonymization_is_applied_dynamically(before_and_after: tuple[Run, Run]):
    before, after = before_and_after
    column = "Encounter_identifierAufnahmenummer_value"
    before_values = _column(before.csv_dir, "KontaktGesundheitseinrichtung.csv", column)
    after_values = _column(after.csv_dir, "KontaktGesundheitseinrichtung.csv", column)
    assert before_values and after_values

    assert all(before_values), (
        "expected raw, un-redacted Encounter VN identifiers with an empty DIMP config, found a blank value"
    )
    assert all(after_values), (
        "expected Encounter VN identifiers to be pseudonymized (non-blank) once the real DIMP "
        "config's pseudonymize/keep rules were applied"
    )
    assert set(before_values).isdisjoint(after_values), (
        "expected pseudonymization to actually change the Encounter VN identifier value, "
        "found a value shared between the raw and pseudonymized runs"
    )


def test_deceased_choice_type_is_applied_dynamically(before_and_after: tuple[Run, Run]):
    before, after = before_and_after
    before_booleans = _column(before.csv_dir, "patients.csv", "Patient_deceased_X_Deceasedboolean")
    before_datetimes = _column(before.csv_dir, "patients.csv", "Patient_deceased_X_Deceaseddatetime")
    after_booleans = _column(after.csv_dir, "patients.csv", "Patient_deceased_X_Deceasedboolean")
    after_datetimes = _column(after.csv_dir, "patients.csv", "Patient_deceased_X_Deceaseddatetime")

    assert any(before_booleans), (
        "expected some raw Patient_deceased_X_Deceasedboolean values with an empty DIMP config, found none"
    )
    assert any(before_datetimes), (
        "expected some raw Patient_deceased_X_Deceaseddatetime values with an empty DIMP config, found none"
    )

    assert any(after_booleans), (
        "Patient.deceased.ofType(boolean) is a DIMP 'keep' rule and should still be present once the "
        "real DIMP config was applied"
    )
    assert not any(after_datetimes), (
        "Patient.deceased.ofType(dateTime) is a DIMP 'redact' rule and should be blank once the "
        "real DIMP config was applied"
    )


def test_unlisted_identifiers_become_redacted(before_and_after: tuple[Run, Run]):
    before, after = before_and_after
    before_values = _column(before.csv_dir, "lab-values.csv", "Observation_identifierAnalysebefundcode_value")
    after_values = _column(after.csv_dir, "lab-values.csv", "Observation_identifierAnalysebefundcode_value")
    assert before_values and after_values

    assert any(before_values), (
        "expected raw, un-redacted Observation identifiers with an empty DIMP config, found none - "
        "does the source data actually carry this identifier?"
    )
    assert not any(after_values), (
        "Observation identifiers are not on the DIMP pseudonymize+keep allow-list and should be "
        "redacted once the real DIMP config's catch-all redact rule was applied"
    )


def test_references_stay_joinable_after_hashing(before_and_after: tuple[Run, Run]):
    _, after = before_and_after
    patient_ids = set(_column(after.csv_dir, "patients.csv", "id"))

    diagnoses = _read_csv(after.csv_dir / "diagnosis.csv")
    assert diagnoses, "expected diagnosis.csv to contain at least one row"
    for row in diagnoses:
        reference = row["patient"]
        assert reference.startswith("Patient/"), f"unexpected patient reference: {reference!r}"
        assert reference.removeprefix("Patient/") in patient_ids, (
            f"diagnosis.csv references patient {reference!r} with no matching row in patients.csv - "
            "Resource.id and Reference.reference cryptoHash rules diverged"
        )
