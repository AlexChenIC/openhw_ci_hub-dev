#!/usr/bin/env python3
# Copyright 2026 OpenHW Group
# SPDX-License-Identifier: Apache-2.0
"""Generate CI Hub Dashboard HTML from collected JSON data.

Reads per-repo, per-workflow JSON files under {data_dir}/{owner}/{repo}/
and renders a Jinja2 template into a self-contained static HTML file.

Supports multiple repositories; the generated dashboard has a repo
selector that switches between repos without a page reload.

Usage:
  python3 generate_dashboard.py \\
      --repos-config config/repos.yml \\
      --data-dir     data \\
      --output-dir   site
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

TREND_COUNT = 20    # Runs shown in trend charts


# ── Helpers ───────────────────────────────────────────────────────────────

def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "N/A"
    m, s = divmod(seconds, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}h {m}m"
    return f"{m}m {s}s"


def format_datetime(iso: str) -> str:
    if not iso:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return iso


def is_valid_matrix_job(job: dict) -> bool:
    config  = job.get("config", "")
    testcase = job.get("testcase", "")
    return bool(config and testcase and
                "${{" not in config and "${{" not in testcase)


# ── Per-run data loading ──────────────────────────────────────────────────

def load_runs(json_path: Path) -> list[dict]:
    if not json_path.exists():
        return []
    try:
        return json.loads(json_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []


# ── Matrix building ───────────────────────────────────────────────────────

def build_matrix(runs: list[dict],
                 configs_order: list[str],
                 suites_order: list[str]) -> dict:
    """Build a config × testsuite result matrix from a run list."""
    matrix: dict[str, dict[str, dict]] = {}

    for run in runs[:10]:   # Look at 10 most recent runs
        for job in run.get("jobs", []):
            if not is_valid_matrix_job(job):
                continue
            config   = job["config"]
            testcase = job["testcase"]
            conclusion = job.get("conclusion", "unknown")

            if config not in matrix:
                matrix[config] = {}
            # Keep the most recent result for each (config, testcase) pair
            if testcase not in matrix[config]:
                matrix[config][testcase] = {
                    "conclusion": conclusion,
                    "html_url":   job.get("html_url", ""),
                    "run_number": run.get("run_number", 0),
                }

    # Determine display order
    all_configs  = sorted(set(c for c in matrix),
                          key=lambda c: (configs_order.index(c)
                                         if c in configs_order else 999))
    all_testcases = sorted(set(t for row in matrix.values() for t in row),
                           key=lambda t: (suites_order.index(t)
                                          if t in suites_order else 999))

    return {
        "configs":   all_configs,
        "testcases": all_testcases,
        "cells":     matrix,
    }


# ── Trend data ────────────────────────────────────────────────────────────

def build_trend(runs: list[dict]) -> dict:
    recent = runs[:TREND_COUNT]
    labels, pass_rates, durations = [], [], []
    for run in reversed(recent):
        total = run.get("total_jobs", 0)
        passed = run.get("passed_jobs", 0)
        labels.append(f"#{run.get('run_number', '?')}")
        pass_rates.append(round(100.0 * passed / total, 1) if total else 0)
        durations.append(round(run.get("duration_seconds", 0) / 60, 1))
    return {"labels": labels, "pass_rates": pass_rates, "durations": durations}


# ── Latest-run summary ────────────────────────────────────────────────────

def latest_run_summary(runs: list[dict]) -> dict | None:
    if not runs:
        return None
    r = runs[0]
    return {
        "run_number":    r.get("run_number", "N/A"),
        "conclusion":    r.get("conclusion", "unknown"),
        "head_branch":   r.get("head_branch", "N/A"),
        "head_sha":      r.get("head_sha", "N/A"),
        "event":         r.get("event", "N/A"),
        "created_at":    format_datetime(r.get("created_at", "")),
        "duration":      format_duration(r.get("duration_seconds", 0)),
        "total_jobs":    r.get("total_jobs", 0),
        "passed_jobs":   r.get("passed_jobs", 0),
        "failed_jobs":   r.get("failed_jobs", 0),
        "html_url":      r.get("html_url", "#"),
    }


# ── Per-repo dashboard data assembly ─────────────────────────────────────

def assemble_repo_data(repo_cfg: dict, data_dir: Path) -> dict:
    owner = repo_cfg["owner"]
    repo  = repo_cfg["repo"]
    repo_data_dir = data_dir / owner / repo

    # Load matrix config (known_configs, known_suites)
    configs_order: list[str] = []
    suites_order: list[str]  = []
    matrix_cfg_path = repo_cfg.get("matrix_config", "")
    if matrix_cfg_path and Path(matrix_cfg_path).exists():
        mc = yaml.safe_load(Path(matrix_cfg_path).read_text())
        configs_order = mc.get("known_configs", [])
        suites_order  = mc.get("known_suites",  [])

    workflows_data: list[dict] = []
    for wf_key, wf_file in repo_cfg.get("workflows", {}).items():
        json_path = repo_data_dir / f"runs_{wf_key}.json"
        runs = load_runs(json_path)
        workflows_data.append({
            "key":          wf_key,
            "display_name": _wf_display_name(wf_key),
            "runs":         runs,
            "latest":       latest_run_summary(runs),
            "matrix":       build_matrix(runs, configs_order, suites_order),
            "trend":        build_trend(runs),
        })

    return {
        "owner":        owner,
        "repo":         repo,
        "slug":         f"{owner}/{repo}",
        "display_name": repo_cfg.get("display_name", repo),
        "description":  repo_cfg.get("description", ""),
        "workflows":    workflows_data,
        "has_data":     any(bool(w["runs"]) for w in workflows_data),
    }


def _wf_display_name(key: str) -> str:
    mapping = {
        "riscv-tier1": "Tier 1 — PR Gate",
        "riscv-tier2": "Tier 2 — Full Coverage",
        "ci":          "Legacy ci.yml",
    }
    return mapping.get(key, key)


# ── Overall overview ──────────────────────────────────────────────────────

def build_overview(repos_data: list[dict]) -> list[dict]:
    """One-row summary per repo for the landing page table."""
    rows = []
    for rd in repos_data:
        tier1 = next((w for w in rd["workflows"] if "tier1" in w["key"]), None)
        tier2 = next((w for w in rd["workflows"] if "tier2" in w["key"]), None)
        rows.append({
            "display_name": rd["display_name"],
            "slug":         rd["slug"],
            "tier1_latest": tier1["latest"] if tier1 else None,
            "tier2_latest": tier2["latest"] if tier2 else None,
        })
    return rows


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Generate CI Hub Dashboard HTML")
    ap.add_argument("--repos-config", default="config/repos.yml")
    ap.add_argument("--data-dir",     default="data")
    ap.add_argument("--output-dir",   default="site")
    ap.add_argument("--template-dir", default=None,
                    help="Override template directory (default: scripts/templates/)")
    args = ap.parse_args()

    repos_cfg = yaml.safe_load(Path(args.repos_config).read_text())
    repos     = [r for r in repos_cfg.get("repos", []) if r.get("active", True)]
    data_dir  = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Locate templates directory
    template_dir = (Path(args.template_dir) if args.template_dir
                    else Path(__file__).parent / "templates")

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
    )
    env.filters["format_duration"] = format_duration
    env.filters["format_datetime"] = format_datetime
    template = env.get_template("index.html")

    # Assemble per-repo data
    repos_data = [assemble_repo_data(r, data_dir) for r in repos]
    overview   = build_overview(repos_data)

    # Render
    html = template.render(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        repos=repos_data,
        overview=overview,
        default_repo_slug=repos_data[0]["slug"] if repos_data else "",
    )

    out_path = output_dir / "index.html"
    out_path.write_text(html)
    print(f"Dashboard written to {out_path}")


if __name__ == "__main__":
    main()
