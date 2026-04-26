#!/usr/bin/env python3
"""
Validation script for synthetic EHR patient data.
Checks structural integrity, diversity across patients, clinical coherence,
and message voice differentiation.

Usage: python data/validate_patients.py
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, date
from collections import Counter
import re

DATA_DIR = Path(__file__).parent / "patients"
SCHEMA_PATH = Path(__file__).parent / "schema.json"
SPECS_PATH = Path(__file__).parent / "patient_specs.json"

EXPECTED_PATIENTS = 12

# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def load_patients():
    """Load all patient JSON files."""
    patients = {}
    errors = []
    for i in range(1, EXPECTED_PATIENTS + 1):
        path = DATA_DIR / f"patient_{i:03d}.json"
        if not path.exists():
            errors.append(f"Missing file: {path.name}")
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            patients[f"patient-{i:03d}"] = data
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}: Invalid JSON — {e}")
    return patients, errors


def check_required_fields(patient, patient_id):
    """Check that top-level required fields exist."""
    issues = []
    required = [
        "resourceType", "id", "demographics", "socialHistory",
        "familyHistory", "allergies", "conditions", "medications",
        "immunizations", "encounters", "labs", "messages"
    ]
    for field in required:
        if field not in patient:
            issues.append(f"Missing required field: {field}")

    if patient.get("resourceType") != "Patient":
        issues.append(f"resourceType should be 'Patient', got '{patient.get('resourceType')}'")

    return issues


def check_coded_concepts(patient, patient_id):
    """Verify all coded concepts have system + code + display."""
    issues = []

    def check_code(obj, path):
        if isinstance(obj, dict) and "code" in obj and isinstance(obj["code"], dict):
            code = obj["code"]
            for field in ["system", "code", "display"]:
                if field not in code:
                    issues.append(f"{path}.code missing '{field}'")

    # Check conditions
    for i, cond in enumerate(patient.get("conditions", [])):
        check_code(cond, f"conditions[{i}]")

    # Check medications
    for i, med in enumerate(patient.get("medications", [])):
        check_code(med, f"medications[{i}]")

    # Check immunizations
    for i, imm in enumerate(patient.get("immunizations", [])):
        check_code(imm, f"immunizations[{i}]")

    # Check lab panels and results
    for i, lab in enumerate(patient.get("labs", [])):
        for j, panel in enumerate(lab.get("panels", [])):
            check_code(panel, f"labs[{i}].panels[{j}]")
            for k, result in enumerate(panel.get("results", [])):
                check_code(result, f"labs[{i}].panels[{j}].results[{k}]")

    return issues


def check_dates_chronological(patient, patient_id):
    """Verify encounters and labs are in chronological order."""
    issues = []

    def parse_date(d):
        try:
            return datetime.strptime(d[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    # Encounters
    encounter_dates = []
    for i, enc in enumerate(patient.get("encounters", [])):
        d = parse_date(enc.get("date"))
        if d:
            encounter_dates.append((i, d))
    for i in range(1, len(encounter_dates)):
        if encounter_dates[i][1] < encounter_dates[i-1][1]:
            issues.append(
                f"Encounters not chronological: [{encounter_dates[i-1][0]}] "
                f"{encounter_dates[i-1][1].date()} > [{encounter_dates[i][0]}] "
                f"{encounter_dates[i][1].date()}"
            )

    # Messages should be within the last year
    for i, msg in enumerate(patient.get("messages", [])):
        d = parse_date(msg.get("date"))
        if d and d < datetime(2025, 4, 1):
            issues.append(f"Message [{i}] date {d.date()} is before April 2025 (should be within last year)")

    # Message dates should be after earliest encounter
    if encounter_dates and patient.get("messages"):
        earliest_encounter = min(d for _, d in encounter_dates)
        for i, msg in enumerate(patient.get("messages", [])):
            d = parse_date(msg.get("date"))
            if d and d < earliest_encounter:
                issues.append(f"Message [{i}] date {d.date()} is before earliest encounter {earliest_encounter.date()}")

    return issues


def check_diversity(patients):
    """Check diversity across all patients."""
    issues = []

    # Age distribution
    ages = []
    for pid, p in patients.items():
        bd = p.get("demographics", {}).get("birthDate", "")
        try:
            birth = datetime.strptime(bd, "%Y-%m-%d")
            age = (datetime(2026, 4, 26) - birth).days / 365.25
            ages.append(age)
        except ValueError:
            pass

    if ages:
        age_range = max(ages) - min(ages)
        if age_range < 40:
            issues.append(f"Age range too narrow: {age_range:.0f} years (expected 40+)")

    # Gender distribution
    genders = [p.get("demographics", {}).get("gender") for p in patients.values()]
    gender_counts = Counter(genders)
    if len(gender_counts) < 2:
        issues.append(f"Insufficient gender diversity: {dict(gender_counts)}")

    # No duplicate names
    names = []
    for p in patients.values():
        name = p.get("demographics", {}).get("name", {})
        full = f"{name.get('given', '')} {name.get('family', '')}"
        names.append(full)
    dupes = [n for n, c in Counter(names).items() if c > 1]
    if dupes:
        issues.append(f"Duplicate names: {dupes}")

    # Message count per patient (3-6)
    for pid, p in patients.items():
        msg_count = len(p.get("messages", []))
        if msg_count < 3 or msg_count > 6:
            issues.append(f"{pid}: {msg_count} messages (expected 3-6)")

    # Primary conditions — no two patients should share the exact same primary
    primary_conditions = []
    for pid, p in patients.items():
        conditions = p.get("conditions", [])
        if conditions:
            primary = conditions[0].get("code", {}).get("display", "unknown")
            primary_conditions.append((pid, primary))
    primaries = [c for _, c in primary_conditions]
    primary_dupes = [c for c, count in Counter(primaries).items() if count > 1]
    if primary_dupes:
        issues.append(f"Duplicate primary conditions: {primary_dupes}")

    # Message categories should be distributed
    all_categories = []
    for p in patients.values():
        for msg in p.get("messages", []):
            all_categories.append(msg.get("category", "unknown"))
    cat_counts = Counter(all_categories)
    total_msgs = sum(cat_counts.values())
    if total_msgs > 0:
        max_cat_pct = max(cat_counts.values()) / total_msgs
        if max_cat_pct > 0.3:
            top_cat = cat_counts.most_common(1)[0]
            issues.append(
                f"Message category concentration: '{top_cat[0]}' is {top_cat[1]}/{total_msgs} "
                f"({max_cat_pct:.0%}) — should be under 30%"
            )

    return issues


def check_coherence(patients):
    """Check clinical coherence within each patient."""
    issues = []

    for pid, p in patients.items():
        conditions = {c.get("code", {}).get("display", "").lower() for c in p.get("conditions", [])}
        med_names = {m.get("code", {}).get("display", "").lower() for m in p.get("medications", [])}

        # Diabetes patients should have A1C labs and diabetes meds
        # Exclude pre-diabetes / prediabetes — those are managed with lifestyle, not meds
        has_diabetes = any("diabet" in c and "pre" not in c and "prediabet" not in c for c in conditions)
        if has_diabetes:
            has_a1c = False
            for lab in p.get("labs", []):
                for panel in lab.get("panels", []):
                    for result in panel.get("results", []):
                        if "a1c" in result.get("test", "").lower() or "hemoglobin a1c" in result.get("test", "").lower():
                            has_a1c = True
            if not has_a1c:
                issues.append(f"{pid}: Has diabetes but no A1C lab results")

            diabetes_meds = {"metformin", "glipizide", "semaglutide", "insulin", "sitagliptin", "empagliflozin", "pioglitazone"}
            if not any(any(dm in m for dm in diabetes_meds) for m in med_names):
                issues.append(f"{pid}: Has diabetes but no diabetes medications")

        # Hypertension patients should have elevated BP in at least some readings
        has_htn = any("hypertens" in c for c in conditions)
        if has_htn:
            has_elevated_bp = False
            for enc in p.get("encounters", []):
                vitals = enc.get("vitals", {})
                bp = vitals.get("bloodPressure", {})
                systolic = bp.get("systolic", 0)
                if systolic >= 130:
                    has_elevated_bp = True
                    break
            if not has_elevated_bp:
                issues.append(f"{pid}: Has hypertension but no elevated BP readings found")

        # Medication allergies shouldn't conflict with prescribed meds
        allergy_substances = {a.get("substance", "").lower() for a in p.get("allergies", [])}
        for med in p.get("medications", []):
            med_name = med.get("code", {}).get("display", "").lower()
            for allergy in allergy_substances:
                if allergy in med_name or med_name in allergy:
                    if med.get("status") == "active":
                        issues.append(f"{pid}: Active medication '{med_name}' conflicts with allergy '{allergy}'")

        # Lab reference ranges should be present
        for lab in p.get("labs", []):
            for panel in lab.get("panels", []):
                for result in panel.get("results", []):
                    if result.get("interpretation") != "pending":
                        ref = result.get("referenceRange", {})
                        if not ref:
                            issues.append(
                                f"{pid}: Lab result '{result.get('test', '?')}' "
                                f"on {lab.get('date', '?')} missing referenceRange"
                            )

    return issues


def check_voice_diversity(patients):
    """Heuristic checks for message voice differentiation."""
    issues = []

    # Average message body length should vary
    patient_avg_lengths = {}
    for pid, p in patients.items():
        msgs = p.get("messages", [])
        if msgs:
            lengths = [len(msg.get("body", "")) for msg in msgs]
            patient_avg_lengths[pid] = sum(lengths) / len(lengths)

    if patient_avg_lengths:
        lengths = list(patient_avg_lengths.values())
        if max(lengths) - min(lengths) < 100:
            issues.append(
                f"Message lengths too uniform: range is only "
                f"{max(lengths) - min(lengths):.0f} chars "
                f"(min avg: {min(lengths):.0f}, max avg: {max(lengths):.0f})"
            )

    # At least 2 patients should have spelling/grammar irregularities
    informal_count = 0
    informal_markers = [
        r'\b(u|ur|r|pls|thx|tbh|lol|idk|bc|w/o|gonna|gotta|wanna|kinda|sorta)\b',
        r'[a-z]\s+[a-z].*\.\s*$',  # likely lowercase start
        r'(?<![.?!])\n',  # no sentence-ending punctuation before newline
    ]
    for pid, p in patients.items():
        msgs = p.get("messages", [])
        informal_hits = 0
        for msg in msgs:
            body = msg.get("body", "")
            # Check for casual/SMS markers
            if re.search(r'\b(u|ur|thx|tbh|lol|idk|bc|gonna|gotta|kinda)\b', body, re.IGNORECASE):
                informal_hits += 1
            # Check for missing capitalization at start
            if body and body[0].islower():
                informal_hits += 1
        if informal_hits >= 2:
            informal_count += 1

    if informal_count < 2:
        issues.append(
            f"Only {informal_count} patient(s) have informal/SMS-style messages "
            f"(expected at least 2 — Marcus Chen and Devon Reeves)"
        )

    # At least 1 patient should have messages from someone other than themselves
    third_party_count = 0
    for pid, p in patients.items():
        for msg in p.get("messages", []):
            sender_role = msg.get("sender", {}).get("role", "")
            if sender_role == "family":
                third_party_count += 1
                break
            # Also check threads
            for reply in msg.get("thread", []):
                if reply.get("sender", {}).get("role") == "family":
                    third_party_count += 1
                    break

    if third_party_count < 1:
        issues.append("No patients have messages from family members (expected Bill Novak's wife, James Hartley's wife)")

    return issues


def print_section(title, issues, is_warning=False):
    """Print a validation section."""
    color = YELLOW if is_warning else (GREEN if not issues else RED)
    status = "WARN" if is_warning and issues else ("PASS" if not issues else "FAIL")
    print(f"\n{BOLD}{color}[{status}]{RESET} {BOLD}{title}{RESET}")
    if issues:
        for issue in issues:
            marker = "⚠" if is_warning else "✗"
            print(f"  {color}{marker}{RESET} {issue}")
    else:
        print(f"  {GREEN}✓ All checks passed{RESET}")
    return len(issues)


def main():
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  EHR Patient Data Validation Report{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    total_errors = 0
    total_warnings = 0

    # Load patients
    patients, load_errors = load_patients()
    total_errors += print_section(
        f"File Loading ({len(patients)}/{EXPECTED_PATIENTS} patients found)",
        load_errors
    )

    if not patients:
        print(f"\n{RED}No patient files found. Cannot continue validation.{RESET}")
        sys.exit(1)

    # Structural validation
    struct_issues = []
    for pid, p in patients.items():
        issues = check_required_fields(p, pid)
        struct_issues.extend(f"{pid}: {i}" for i in issues)
    total_errors += print_section("Structural: Required Fields", struct_issues)

    # Coded concepts
    code_issues = []
    for pid, p in patients.items():
        issues = check_coded_concepts(p, pid)
        code_issues.extend(f"{pid}: {i}" for i in issues)
    total_errors += print_section("Structural: Coded Concepts (system/code/display)", code_issues)

    # Chronological dates
    date_issues = []
    for pid, p in patients.items():
        issues = check_dates_chronological(p, pid)
        date_issues.extend(f"{pid}: {i}" for i in issues)
    total_errors += print_section("Structural: Date Ordering & Ranges", date_issues)

    # Diversity
    diversity_issues = check_diversity(patients)
    total_errors += print_section("Diversity: Cross-Patient Variation", diversity_issues)

    # Coherence
    coherence_issues = check_coherence(patients)
    total_errors += print_section("Coherence: Clinical Consistency", coherence_issues)

    # Voice diversity (warnings, not errors)
    voice_issues = check_voice_diversity(patients)
    total_warnings += print_section("Voice: Message Differentiation", voice_issues, is_warning=True)

    # Summary stats
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}Summary Statistics{RESET}")
    print(f"{'─'*60}")

    total_encounters = sum(len(p.get("encounters", [])) for p in patients.values())
    total_labs = sum(len(p.get("labs", [])) for p in patients.values())
    total_meds = sum(len(p.get("medications", [])) for p in patients.values())
    total_msgs = sum(len(p.get("messages", [])) for p in patients.values())
    total_conditions = sum(len(p.get("conditions", [])) for p in patients.values())

    print(f"  Patients:    {len(patients)}")
    print(f"  Encounters:  {total_encounters}")
    print(f"  Lab orders:  {total_labs}")
    print(f"  Medications: {total_meds}")
    print(f"  Conditions:  {total_conditions}")
    print(f"  Messages:    {total_msgs}")

    # Per-patient summary
    print(f"\n{BOLD}Per-Patient Overview{RESET}")
    print(f"{'─'*60}")
    print(f"  {'ID':<14} {'Name':<22} {'Enc':>4} {'Labs':>5} {'Meds':>5} {'Msgs':>5}")
    print(f"  {'─'*56}")
    for pid in sorted(patients.keys()):
        p = patients[pid]
        name = p.get("demographics", {}).get("name", {})
        full_name = f"{name.get('given', '')} {name.get('family', '')}"
        print(
            f"  {pid:<14} {full_name:<22} "
            f"{len(p.get('encounters', [])):>4} "
            f"{len(p.get('labs', [])):>5} "
            f"{len(p.get('medications', [])):>5} "
            f"{len(p.get('messages', [])):>5}"
        )

    # Final result
    print(f"\n{BOLD}{'='*60}{RESET}")
    if total_errors == 0:
        print(f"{GREEN}{BOLD}  RESULT: ALL CHECKS PASSED{RESET}", end="")
        if total_warnings > 0:
            print(f" {YELLOW}({total_warnings} warnings){RESET}")
        else:
            print()
    else:
        print(f"{RED}{BOLD}  RESULT: {total_errors} ERROR(S) FOUND{RESET}", end="")
        if total_warnings > 0:
            print(f" {YELLOW}({total_warnings} warnings){RESET}")
        else:
            print()
    print(f"{BOLD}{'='*60}{RESET}\n")

    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
