# CI Hub Status

Updated: 2026-05-06

## Current Goal

Validate the CI Hub approach for Flo's centralized CI management proposal:

- keep reusable CI logic in one hub repository
- keep target repositories lightweight through thin wrapper workflows
- aggregate CI history from monitored repositories into one dashboard
- prove the approach first on CVA6, then evaluate extension to CV32E20-DV

## Current Scope

| Repository | Role | Status |
| --- | --- | --- |
| `AlexChenIC/cva6-tier-ci-test-20260427` | CVA6 tier CI validation source | Active |
| `AlexChenIC/cv32e20-dv` | Second-repo integration candidate | Paused pending simulator decision |

## Implemented

| Area | Status | Notes |
| --- | --- | --- |
| Hub repository structure | Done | Reusable workflows, action, scripts, examples, config |
| CVA6 data collection | Done | Reads `ci.yml`, `openhw-cva6-ci-tier1.yml`, `openhw-cva6-ci-tier2.yml` |
| CVA6 dashboard generation | Done | Local generation verified from live GitHub Actions data |
| CVA6 Tier 1 reusable workflow | Done | Supports script, testlist, and custom C test modes |
| CVA6 Tier 2 reusable workflow | Done | Includes `hwconfig-opts` support for hwconfig/coremark jobs |
| CVA6 thin wrapper examples | Done | Tier 1 and Tier 2 examples match the current CVA6 validation matrix |
| Data persistence branch | Done | `gh-pages-ci-hub` exists and is updated by collection workflow |
| Dashboard deploy workflow | Done | Publishes https://alexchenic.github.io/openhw_ci_hub-dev/ |
| CVA6 reusable workflow access smoke | Done | `openhw-ci-hub-smoke.yml` in the CVA6 validation repo calls the hub Tier 1 workflow |

## Remaining Work

| Priority | Task | Owner | Status | Exit Criteria |
| --- | --- | --- | --- | --- |
| P0 | Enable dashboard hosting for the hub repo | Repo admin | Done | A stable URL serves the generated dashboard |
| P0 | Decide hub visibility/access policy | Junchao/Flo | Done for pilot | Public target repos can call the reusable workflows |
| P1 | Configure `DISPATCH_TOKEN` | Junchao | Open | `trigger-nightly.yml` can dispatch Tier 2 workflows |
| P1 | Validate full Tier 1 wrapper in a target CVA6 fork | Junchao | Open | A PR triggers full Tier 1 via the hub reusable workflow |
| P2 | Decide CV32E20 simulator route | Junchao/Flo | Open | DSim, Spike-only, or Verilator path selected |
| P2 | Add CV32E20 to dashboard | Junchao | Blocked | CV32E20 entry is active and has at least one collected run |

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Hub repo visibility changes after the pilot | Public callers may lose access to reusable workflows | Keep hub public for public target repos, or move callers and hub under compatible private access policy |
| `DISPATCH_TOKEN` missing | Nightly dispatch cannot start target workflows | Add PAT/fine-grained token with workflow permission |
| CV32E20 lacks a free RTL simulator path | Second-repo demo may be delayed | Use Spike-only as a management/demo fallback or evaluate DSim Cloud |

## Latest Verification

Local verification on 2026-05-06:

- YAML config and workflow files parse successfully
- `parser.py` self-test passes
- `collect_all_repos.py` collected live data from `AlexChenIC/cva6-tier-ci-test-20260427`
- latest collected CVA6 Tier 2 run: run `#10`, `22/22` jobs passed
- `generate_dashboard.py` produced a static dashboard HTML with the CVA6 Tier 2 matrix
- remote `collect-results.yml` run `25427007423` completed successfully and updated `gh-pages-ci-hub`
- remote `deploy-dashboard.yml` run `25427133800` completed successfully; Pages deployment was skipped because Pages is unavailable
- remote `trigger-nightly.yml` run `25427133849` completed successfully; CVA6 dispatch was skipped because `DISPATCH_TOKEN` is not configured
- GitHub Pages enablement failed with plan limitation for the current private repository
- hub repository was made public for the pilot
- remote `collect-results.yml` run `25431051842` completed successfully and triggered dashboard deployment
- remote `deploy-dashboard.yml` run `25431065768` completed successfully and published the dashboard
- dashboard URL returns HTTP 200: https://alexchenic.github.io/openhw_ci_hub-dev/
- CVA6 target repo smoke run `25431150116` completed successfully through the hub reusable workflow
