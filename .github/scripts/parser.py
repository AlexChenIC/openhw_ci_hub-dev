#!/usr/bin/env python3
# Copyright 2026 OpenHW Group
# SPDX-License-Identifier: Apache-2.0
"""Parse CI job names into structured data for the CI Hub Dashboard.

Handles four job name formats:

  Format 1 — Tier 1 and Tier 2 (riscv-tier1.yml / riscv-tier2.yml):
    "RV32 Tier1 cv32a65x / smoke-tests-cv32a65x"
    "RV64 Tier2 cv64a6_imafdc_sv39_hpdcache_wb / dv-riscv-arch-test"

  Format 2 — cv32e20-dv Tier 1 / Tier 2:
    "CV32E20 Tier1 cv32e20 / hello_world"

  Format 3 — Legacy ci.yml (CVA6):
    "execute-riscv64-tests (testcase, config, simulator)"
    "execute-riscv32-tests (testcase, config, simulator)"

  Format 4 — Unknown / skip
    Returns None for utility/infrastructure jobs.
"""

import re
from typing import Optional

# ── Infrastructure jobs to skip (not actual test executions) ──────────────
SKIP_JOBS: set[str] = {
    "Setup Tools",
    "Test Summary",
    "Resolve Tier",
    "Prepare Matrix",
    "build-riscv-tests",
    "report-summary",
    "setup-tools",
    "resolve-tier",
    "prepare-matrix",
    "Collect CI Data",
    "Build Dashboard",
    "Deploy to GitHub Pages",
}

# ── Default known CVA6 configs (longest first for greedy match) ────────────
# Can be overridden per-call via the `known_configs` parameter.
# Updated 2026-03-24 per Mike Thompson / OpenHW internal meeting.
_DEFAULT_KNOWN_CONFIGS: list[str] = [
    # Active configs
    "cv64a6_imafdc_sv39_hpdcache_wb",
    "cv64a6_imafdc_sv39_hpdcache",
    "cv64a60ax",
    "cv32a65x",
    "cv32a60x",
    # CV32E20
    "cv32e20",
    # DEFERRED — uncomment when blockers are resolved
    # "cv64a6_imafdch_sv39_wb",
    # "cv64a6_imafdch_sv39",
    # "cv64a6_imafdcv_sv39",
    # "cv64a6_imafdc_sv39_openpiton",
    # "cv32a6_ima_sv32_fpga",
]

# ── Regex patterns ────────────────────────────────────────────────────────
# Tier 1 / Tier 2 (Format 1 & 2):
#   "RV32 Tier1 cv32a65x / smoke-tests-cv32a65x"
#   "CV32E20 Tier1 cv32e20 / hello_world"
_RE_TIER = re.compile(
    r"^(RV(?:32|64)|CV\d+\w*)\s+Tier[12]\s+(.+?)\s*/\s*(.+)$"
)

# Legacy ci.yml (Format 3):
#   "execute-riscv64-tests (testcase, config, simulator)"
_RE_LEGACY = re.compile(
    r"^execute-riscv(32|64)-tests\s+\(([^)]+)\)$"
)


def parse_job_name(
    job_name: str,
    workflow_name: str,
    known_configs: Optional[list[str]] = None,
) -> Optional[dict]:
    """Parse a CI job name into structured fields.

    Args:
        job_name:      Raw job name string from GitHub Actions API.
        workflow_name: Workflow identifier (e.g. "riscv-tier1", "ci").
        known_configs: Optional override for the list of recognised config
                       names. Falls back to module-level _DEFAULT_KNOWN_CONFIGS.

    Returns:
        dict with keys: arch, config, testcase, simulator (optional)
        None if the job is an infrastructure job and should be skipped.
    """
    name = job_name.strip()

    # Skip utility jobs
    if name in SKIP_JOBS:
        return None

    # ── Tier 1 / Tier 2 format ────────────────────────────────────────────
    m = _RE_TIER.match(name)
    if m:
        arch_prefix = m.group(1)   # e.g. "RV32", "RV64", "CV32E20"
        config = m.group(2).strip()
        testcase = m.group(3).strip()

        # Skip unresolved matrix placeholders
        if "${{" in config or "${{" in testcase:
            return None

        # Normalise arch to "rv32" / "rv64"
        arch = _normalise_arch(arch_prefix, config)

        return {"arch": arch, "config": config, "testcase": testcase}

    # ── Legacy ci.yml format ──────────────────────────────────────────────
    m = _RE_LEGACY.match(name)
    if m:
        arch = f"rv{m.group(1)}"
        params = [p.strip() for p in m.group(2).split(",")]

        if len(params) == 3:
            testcase, config, simulator = params
            return {
                "arch": arch,
                "config": config,
                "testcase": testcase,
                "simulator": simulator,
            }
        if len(params) >= 2:
            return {
                "arch": arch,
                "config": params[1],
                "testcase": params[0],
            }

    # Unrecognised format — skip
    return None


def arch_from_config(config: str) -> str:
    """Infer architecture string from config name."""
    if config.startswith("cv64"):
        return "rv64"
    if config.startswith("cv32"):
        return "rv32"
    return "unknown"


# ── Private helpers ───────────────────────────────────────────────────────

def _normalise_arch(prefix: str, config: str) -> str:
    """Convert job-name arch prefix to canonical "rv32" / "rv64" string."""
    upper = prefix.upper()
    if upper in ("RV32", "CV32E20"):
        return "rv32"
    if upper in ("RV64",):
        return "rv64"
    # Fallback: infer from config name
    return arch_from_config(config)


# ── Self-test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _TESTS = [
        # Tier 1 CVA6
        ("RV32 Tier1 cv32a65x / smoke-tests-cv32a65x",                    "riscv-tier1"),
        ("RV64 Tier1 cv64a6_imafdc_sv39_hpdcache_wb / dv-riscv-arch-test","riscv-tier1"),
        # Tier 2 CVA6
        ("RV32 Tier2 cv32a65x / dv-riscv-arch-test",                      "riscv-tier2"),
        ("RV64 Tier2 cv64a6_imafdc_sv39_hpdcache_wb / dv-riscv-tests-v",  "riscv-tier2"),
        # CV32E20
        ("CV32E20 Tier1 cv32e20 / hello_world",                            "riscv-tier1"),
        ("CV32E20 Tier2 cv32e20 / interrupt_test",                         "riscv-tier2"),
        # Legacy ci.yml
        ("execute-riscv64-tests (cv64a6_imafdc_tests, cv64a6_imafdc_sv39_hpdcache, veri-testharness)", "ci"),
        ("execute-riscv32-tests (dv-riscv-arch-test, cv32a65x, veri-testharness)",                     "ci"),
        # Skip jobs
        ("Setup Tools",   "riscv-tier1"),
        ("Test Summary",  "riscv-tier2"),
    ]

    print("parser.py self-test:")
    all_pass = True
    for job_name, wf in _TESTS:
        result = parse_job_name(job_name, wf)
        status = "OK" if result is not None or job_name in {"Setup Tools", "Test Summary"} else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}] {job_name!r:72s} -> {result}")

    print(f"\n{'All tests passed.' if all_pass else 'SOME TESTS FAILED.'}")
