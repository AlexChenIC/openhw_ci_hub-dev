# Contributing to OpenHW CI Hub

Thank you for contributing to the OpenHW CI Hub.

## What lives here

This repository contains **shared CI infrastructure** — not RTL, not testbenches.
Changes here can affect every repository that calls our reusable workflows.
Please test carefully before merging to `main`.

## Versioning

We use semantic versioning for releases (e.g. `v1.2.0`).
Target repos should pin to a release tag rather than `@main` for stability:

```yaml
uses: AlexChenIC/openhw_ci_hub-dev/.github/workflows/riscv-tier1.yml@v1
```

Changes to reusable workflow **inputs** (adding/removing/renaming) are breaking changes
and require a major version bump.

## Making changes

1. Fork and create a feature branch (`feat/`, `fix/`, `docs/`)
2. Test by calling the reusable workflow from a fork before merging
3. Update `CHANGELOG.md` (create if it does not exist) with a brief summary
4. Open a PR targeting `main`; include a link to a test workflow run

## Adding a new monitored repository

See [docs/adding-new-repo.md](docs/adding-new-repo.md).

## Reporting issues

Open a GitHub Issue with:
- Which workflow failed
- The full workflow run URL
- Expected vs. actual behaviour
