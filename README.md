# OpenHW CI Hub

> Unified CI infrastructure for OpenHW RISC-V processor projects.

This repository provides **reusable GitHub Actions workflows**, a **shared composite action** for RISC-V tool setup, and a **unified CI Dashboard** that aggregates results across multiple OpenHW repositories.

**Live Dashboard**: https://AlexChenIC.github.io/openhw_ci_hub-dev/ *(replace `AlexChenIC` after setup)*

---

## Overview

Instead of every OpenHW repository duplicating CI infrastructure, this hub provides:

| Component | Location | Purpose |
|-----------|----------|---------|
| Reusable Tier 1 workflow | `.github/workflows/riscv-tier1.yml` | PR Gate — called by target repos |
| Reusable Tier 2 workflow | `.github/workflows/riscv-tier2.yml` | Full coverage — called by target repos |
| Composite action | `.github/actions/setup-riscv-env/` | Tool installation & caching |
| Dashboard scripts | `.github/scripts/` | Collect & visualize CI results |
| Nightly scheduler | `.github/workflows/trigger-nightly.yml` | Dispatch Tier 2 to all repos |

Each target repository needs only a **thin wrapper** (~15 lines of YAML) that calls these shared workflows. See `examples/` for ready-to-use wrappers.

---

## Monitored Repositories

| Repository | Tier 1 (PR Gate) | Tier 2 (Nightly) | Notes |
|------------|-----------------|-----------------|-------|
| `AlexChenIC/cva6` | ✅ | ✅ | CVA6 OoO Core (fork) |
| `AlexChenIC/cv32e20-dv` | ⚙️ | ⚙️ | CV32E20 DV env (simulator TBD) |

To add a new repository, see [docs/adding-new-repo.md](docs/adding-new-repo.md).

---

## Quick Start

### 1. Configure this repo

Replace `AlexChenIC` in `config/repos.yml` with your GitHub username:

```bash
sed -i 's/AlexChenIC/YOUR_GITHUB_USERNAME/g' config/repos.yml
```

### 2. Add thin wrappers to target repos

Copy the examples to your target repositories:

```bash
# For CVA6 fork
cp examples/cva6-thin-wrapper-tier1.yml path/to/cva6/.github/workflows/tier1.yml
cp examples/cva6-thin-wrapper-tier2.yml path/to/cva6/.github/workflows/tier2.yml
```

Update the `uses:` path in each file to point to `AlexChenIC/openhw_ci_hub-dev`.

### 3. Enable GitHub Pages

In this repository: **Settings → Pages → Source → GitHub Actions**

### 4. Add secrets

In this repository's **Settings → Secrets → Actions**:

| Secret | Required for | Description |
|--------|-------------|-------------|
| `DISPATCH_TOKEN` | Nightly trigger | PAT with `workflow` scope for dispatching to other repos |

### 5. First run

```bash
# Manually trigger data collection
gh workflow run collect-results.yml --repo AlexChenIC/openhw_ci_hub-dev
```

---

## Architecture

```
AlexChenIC/cva6 (fork)          AlexChenIC/cv32e20-dv (fork)
  tier1.yml (15 lines)  ──────►  tier1.yml (15 lines)
       │ uses:                         │ uses:
       ▼                               ▼
  AlexChenIC/openhw_ci_hub-dev
  ├── riscv-tier1.yml    ◄── reusable workflow logic
  ├── riscv-tier2.yml    ◄── reusable workflow logic
  ├── setup-riscv-env/   ◄── composite action
  ├── collect-results.yml ─── GitHub API → data/{owner}/{repo}/
  ├── deploy-dashboard.yml ── data/ → GitHub Pages
  └── trigger-nightly.yml ─── dispatches Tier 2 to all repos
```

**GitHub security model**: PR events in a target repo can only trigger workflows defined IN that repo. The thin wrapper files satisfy this requirement while delegating all logic to ci-hub.

---

## Repository Structure

```
ci-hub/
├── .github/
│   ├── workflows/
│   │   ├── riscv-tier1.yml          # Reusable: on workflow_call
│   │   ├── riscv-tier2.yml          # Reusable: on workflow_call
│   │   ├── collect-results.yml      # Scheduled: data collection
│   │   ├── deploy-dashboard.yml     # Deploy GitHub Pages
│   │   └── trigger-nightly.yml      # Nightly Tier 2 dispatch
│   ├── actions/
│   │   └── setup-riscv-env/         # Composite action (parameterized)
│   └── scripts/
│       ├── collect_all_repos.py     # Multi-repo CI data collector
│       ├── generate_dashboard.py    # Dashboard HTML generator
│       ├── parser.py                # CI job name parser
│       └── templates/index.html    # Dashboard Bootstrap5 template
├── config/
│   ├── repos.yml                    # Repository registry
│   ├── cva6-matrix.yml             # CVA6 config & suite definitions
│   └── cv32e20-matrix.yml          # CV32E20 config & suite definitions
├── examples/
│   ├── cva6-thin-wrapper-tier1.yml  # Ready-to-use thin wrapper
│   └── cva6-thin-wrapper-tier2.yml
├── docs/
│   ├── adding-new-repo.md           # Onboarding guide
│   └── architecture.md              # Deep-dive architecture
├── README.md
├── CONTRIBUTING.md
└── LICENSE                          # Apache 2.0
```

---

## Dashboard Features

- **Repo selector** — switch between monitored repositories
- **CI status matrix** — Config × TestSuite grid, color-coded pass/fail
- **Trend charts** — Pass rate % and duration over last 20 runs
- **Run history** — Clickable links to GitHub Actions runs
- **Latest run summary** — Branch, SHA, job counts per workflow

---

## Roadmap

- [x] Phase 1: CVA6 PR Gate (Tier 1)
- [x] Phase 2: CVA6 Dashboard
- [ ] Phase 3: cv32e20-dv integration (pending simulator investigation)
- [ ] Phase 4: Propose to OpenHW organization (`openhwgroup/ci-hub`)
- [ ] Phase 5: Expand to cv32e40p, cv32e40s, and other cores

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).
Copyright 2026 OpenHW Group Contributors.
