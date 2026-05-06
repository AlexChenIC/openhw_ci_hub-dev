# CI Hub Experiment Plan

## Objective

Demonstrate that a centralized CI Hub can manage reusable RISC-V processor CI logic and dashboard reporting with minimal changes in each target repository.

## Success Criteria

The experiment is considered complete when all of the following are true:

1. CI Hub collects live CVA6 CI results without manual data editing.
2. CI Hub publishes a live dashboard from GitHub Pages.
3. At least one CVA6 target repo can trigger Tier 1 through a thin wrapper that calls the hub reusable workflow.
4. Nightly Tier 2 dispatch is either working with `DISPATCH_TOKEN` or documented as intentionally manual for the experiment.
5. The repository contains clear onboarding instructions for adding a second repo.
6. CV32E20-DV has a documented simulator decision and a next-step integration plan.

## Milestones

| Milestone | Target Result | Current State |
| --- | --- | --- |
| M1: CVA6 dashboard aggregation | Collect current CVA6 tier CI data into hub dashboard | Mostly complete; needs pushed fix and Pages enablement |
| M2: CVA6 thin-wrapper execution | PR in target repo calls hub Tier 1 workflow | Wrapper examples ready; target repo access/visibility must be decided |
| M3: Nightly management flow | Hub can start CVA6 Tier 2 on schedule | Workflow ready; blocked by missing `DISPATCH_TOKEN` |
| M4: Second-repo readiness | CV32E20 has a selected simulator route | Not complete |
| M5: Management demo package | Dashboard URL, architecture note, task/risk status | In progress |

## Decision Log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-05-06 | Use `AlexChenIC/cva6-tier-ci-test-20260427` as the active CVA6 data source | It contains the current working CVA6 Tier 1/Tier 2 workflows and dashboard validation history |
| 2026-05-06 | Keep CV32E20 inactive until simulator route is chosen | The current DV flow depends on simulator capability that is not yet settled |
| 2026-05-06 | Treat missing `DISPATCH_TOKEN` as a warning in nightly trigger | Data/dashboard validation should not fail because dispatch credentials are not configured yet |

## Completion Estimate

| Workstream | Remaining Effort | Notes |
| --- | --- | --- |
| Dashboard aggregation for CVA6 | 0.5 day | Push fixes, enable Pages, run collection/deploy once |
| CVA6 thin-wrapper validation | 0.5-1 day | Depends on repo visibility/access policy |
| Nightly dispatch | 0.25 day | Add `DISPATCH_TOKEN` and run manual dispatch test |
| CV32E20 simulator decision | 1-2 days | Investigation and decision, not implementation |
| CV32E20 first integration | 2-5 days | Depends heavily on simulator choice |

## Recommended Next Step

Complete M1 and M2 first. They prove the central management concept without waiting for CV32E20 simulator uncertainty.
