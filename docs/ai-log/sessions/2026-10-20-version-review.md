# 20 October 2026 — Dependency version review

Context: Phase 1 PR #3 is merged. This exchange reviews dependency choices; no new implementation phase was requested.

## 01. User

Postgres 16, should it be Postgres 17? Should we be using latest versions of other libraries?

## 02. Assistant

I’ll check the assignment’s Postgres requirement and the pinned dependency versions, then separate upgrades worth making from changes that would add risk to the exercise.

## 03. Assistant

The assignment explicitly names Postgres 16, so that major version is appropriate. I did find a patch update we should make: the project pins 16.14, while PostgreSQL recommends 16.15. The application and test libraries are current; a couple of build tools have newer releases. I’ll document the findings and recommendations in GitHub.

## 04. Assistant

The remaining recommendation is to refresh PostgreSQL’s patch release, Hatchling, and uv, then rerun the Phase 1 checks. I’ve recorded the sources and upgrade checks in a small documentation PR so the version decisions stay alongside the project.
