#!/usr/bin/env python3
# Copyright 2026 OpenHW Group
# SPDX-License-Identifier: Apache-2.0
"""Collect CI run/job data from GitHub API for all repos in repos.yml.

Reads config/repos.yml (or --repos-config path), then for each active
repository and each configured workflow, fetches the latest completed runs
and their per-job data via `gh api` (pre-installed on GHA runners,
authenticated automatically via GITHUB_TOKEN).

Data is written incrementally to:
  {data_dir}/{owner}/{repo}/runs_{workflow_key}.json

Each JSON file holds up to MAX_HISTORY runs, newest first.
A top-level metadata.json is written with collection metadata.

Usage:
  python3 collect_all_repos.py --repos-config config/repos.yml \\
                               --data-dir data --fetch-count 10
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

# Maximum runs to keep per workflow (circular buffer)
MAX_HISTORY = 50


# ── GitHub API helpers ────────────────────────────────────────────────────

def _gh_api(url: str) -> dict:
    """Call `gh api {url}` and return parsed JSON. Exits on error."""
    result = subprocess.run(
        ["gh", "api", url],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: gh api {url!r} failed:\n{result.stderr}", file=sys.stderr)
        raise RuntimeError(f"gh api failed for {url}")
    return json.loads(result.stdout)


def fetch_runs(repo: str, workflow_file: str, count: int) -> list[dict]:
    """Return the latest `count` completed runs for a workflow."""
    url = (f"/repos/{repo}/actions/workflows/{workflow_file}"
           f"/runs?status=completed&per_page={count}")
    data = _gh_api(url)
    return data.get("workflow_runs", [])[:count]


def fetch_jobs(repo: str, run_id: int) -> list[dict]:
    """Return all jobs for a given run."""
    data = _gh_api(f"/repos/{repo}/actions/runs/{run_id}/jobs")
    return data.get("jobs", [])


# ── Duration helpers ──────────────────────────────────────────────────────

def _duration_seconds(started_at: str, completed_at: str) -> int:
    """Return wall-clock duration in seconds between two ISO-8601 timestamps."""
    if not started_at or not completed_at:
        return 0
    try:
        fmt = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
        return max(0, int((fmt(completed_at) - fmt(started_at)).total_seconds()))
    except (ValueError, TypeError):
        return 0


# ── Run processing ────────────────────────────────────────────────────────

def process_run(repo: str, run: dict, workflow_key: str,
                known_configs: Optional[list[str]] = None) -> dict:
    """Convert a raw GitHub API run record into our storage format."""
    from parser import parse_job_name  # local import keeps CLI import-free

    run_id = run["id"]
    raw_jobs = fetch_jobs(repo, run_id)

    jobs: list[dict] = []
    total = passed = failed = 0

    for job in raw_jobs:
        parsed = parse_job_name(job["name"], workflow_key,
                                known_configs=known_configs)
        if parsed is None:
            continue

        total += 1
        conclusion = job.get("conclusion", "unknown")
        if conclusion == "success":
            passed += 1
        elif conclusion in ("failure", "timed_out"):
            failed += 1

        jobs.append({
            "name":             job["name"],
            "conclusion":       conclusion,
            "started_at":       job.get("started_at", ""),
            "completed_at":     job.get("completed_at", ""),
            "duration_seconds": _duration_seconds(
                job.get("started_at", ""), job.get("completed_at", "")
            ),
            "html_url": job.get("html_url", ""),
            **parsed,
        })

    run_duration = _duration_seconds(
        run.get("run_started_at", run.get("created_at", "")),
        run.get("updated_at", ""),
    )

    return {
        "id":            run_id,
        "source":        "github-actions",   # extensible: "questa-aws", "gitlab-ci"
        "simulator":     "verilator",        # extensible: "questa", "vcs", "dsim"
        "run_number":    run.get("run_number", 0),
        "status":        run.get("status", ""),
        "conclusion":    run.get("conclusion", "unknown"),
        "html_url":      run.get("html_url", ""),
        "head_branch":   run.get("head_branch", ""),
        "head_sha":      run.get("head_sha", "")[:8],
        "event":         run.get("event", ""),
        "created_at":    run.get("created_at", ""),
        "updated_at":    run.get("updated_at", ""),
        "run_started_at": run.get("run_started_at", run.get("created_at", "")),
        "duration_seconds": run_duration,
        "total_jobs":    total,
        "passed_jobs":   passed,
        "failed_jobs":   failed,
        "skipped_jobs":  total - passed - failed,
        "jobs":          jobs,
    }


# ── JSON file helpers ─────────────────────────────────────────────────────

def load_existing(path: Path) -> list[dict]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            print(f"WARNING: could not read {path}: {exc}", file=sys.stderr)
    return []


def merge_runs(existing: list[dict], new_runs: list[dict]) -> list[dict]:
    """Merge new_runs into existing, deduplicate by id, keep newest MAX_HISTORY."""
    seen = {r["id"] for r in existing}
    merged = list(existing)
    for run in new_runs:
        if run["id"] not in seen:
            merged.append(run)
            seen.add(run["id"])
    merged.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return merged[:MAX_HISTORY]


# ── Per-repo collection ───────────────────────────────────────────────────

def collect_repo(repo_cfg: dict, data_dir: Path, fetch_count: int) -> None:
    """Collect CI data for a single repository.  Errors are caught and logged."""
    owner = repo_cfg["owner"]
    repo  = repo_cfg["repo"]
    full  = f"{owner}/{repo}"

    # Load per-repo known_configs (used by parser for config recognition)
    matrix_cfg_path = repo_cfg.get("matrix_config", "")
    known_configs: Optional[list[str]] = None
    if matrix_cfg_path and Path(matrix_cfg_path).exists():
        try:
            matrix = yaml.safe_load(Path(matrix_cfg_path).read_text())
            known_configs = matrix.get("known_configs")
        except Exception as exc:
            print(f"  WARNING: could not load {matrix_cfg_path}: {exc}", file=sys.stderr)

    repo_data_dir = data_dir / owner / repo
    repo_data_dir.mkdir(parents=True, exist_ok=True)

    for wf_key, wf_file in repo_cfg.get("workflows", {}).items():
        print(f"\n  [{full}] workflow: {wf_key} ({wf_file})")
        json_path = repo_data_dir / f"runs_{wf_key}.json"

        try:
            existing = load_existing(json_path)
            existing_ids = {r["id"] for r in existing}
            print(f"    Existing records: {len(existing)}")

            runs = fetch_runs(full, wf_file, fetch_count)
            print(f"    Fetched {len(runs)} runs from API")

            new_runs: list[dict] = []
            for run in runs:
                if run["id"] in existing_ids:
                    continue
                print(f"    Processing run #{run['run_number']} (id={run['id']})…")
                try:
                    processed = process_run(full, run, wf_key, known_configs)
                    new_runs.append(processed)
                    print(f"      → {processed['total_jobs']} jobs: "
                          f"{processed['passed_jobs']} passed, "
                          f"{processed['failed_jobs']} failed")
                except Exception as exc:
                    print(f"      WARNING: skipping run {run['id']}: {exc}", file=sys.stderr)

            merged = merge_runs(existing, new_runs)
            json_path.write_text(json.dumps(merged, indent=2))
            print(f"    Saved {len(merged)} records → {json_path}")

        except Exception as exc:
            print(f"  ERROR: {full}/{wf_key}: {exc}", file=sys.stderr)
            # Continue to next workflow; do not abort the whole run


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Collect CI data for all repos listed in repos.yml"
    )
    ap.add_argument("--repos-config", default="config/repos.yml",
                    help="Path to repos.yml")
    ap.add_argument("--data-dir", default="data",
                    help="Root directory for JSON data output")
    ap.add_argument("--fetch-count", type=int, default=10,
                    help="Number of recent runs to fetch per workflow")
    args = ap.parse_args()

    repos_config = yaml.safe_load(Path(args.repos_config).read_text())
    repos = repos_config.get("repos", [])
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"CI Hub — collecting data for {len(repos)} repos")
    print(f"Data dir: {data_dir.resolve()}")

    repo_summary: list[dict] = []
    for repo_cfg in repos:
        if not repo_cfg.get("active", True):
            print(f"\n[SKIP] {repo_cfg['owner']}/{repo_cfg['repo']} (active: false)")
            continue

        print(f"\n{'='*60}")
        print(f"Repository: {repo_cfg['owner']}/{repo_cfg['repo']}")
        print(f"{'='*60}")
        try:
            collect_repo(repo_cfg, data_dir, args.fetch_count)
            repo_summary.append({"owner": repo_cfg["owner"],
                                  "repo": repo_cfg["repo"],
                                  "display_name": repo_cfg.get("display_name", repo_cfg["repo"]),
                                  "status": "ok"})
        except Exception as exc:
            print(f"ERROR: collection failed for {repo_cfg['owner']}/{repo_cfg['repo']}: {exc}",
                  file=sys.stderr)
            repo_summary.append({"owner": repo_cfg["owner"],
                                  "repo": repo_cfg["repo"],
                                  "display_name": repo_cfg.get("display_name", repo_cfg["repo"]),
                                  "status": "error",
                                  "error": str(exc)})

    # Write metadata
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repos": repo_summary,
    }
    (data_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"\nDone. Metadata written to {data_dir / 'metadata.json'}")


if __name__ == "__main__":
    main()
