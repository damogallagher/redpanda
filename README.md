# Redpanda FDE exercise

Status: planning only. Application code, CI, and executable test commands have not been implemented.

Start with the [implementation plan](docs/implementation-plan.md), then the [phase index](docs/phases/README.md). Each implementation phase will have its own branch and pull request into `main`, with a working demonstration and recorded test evidence.

The agreed example is Wikipedia edit triage, implemented in Python with a choice of local Ollama or hosted frontier inference. Submission is due Friday, 23 October 2026. Damien reviews and merges each phase. This is entirely new work with a fresh repository history.

- [Original assignment — unchanged](docs/assignment/fde-take-home-exercise.md)
- [How to verify each phase](docs/phase-verification.md)
- [Quality and testing requirements](docs/testing.md)
- [AI interaction log](docs/ai-log/README.md)
- [Progress and decisions still needed](docs/progress.md)

## Run instructions

To be added and verified as the system is implemented. The final default startup must be `docker compose up`, including model initialization. The first run requires internet access to download dependencies and model weights. A deterministic fixture mode will support repeatable demonstrations.

## Tradeoffs

Reserved for Damien to write independently, in his own words, as requested by the assignment. Choose two of the assignment's pairs and describe the choice, alternative, and when to change it. No AI-authored submission prose has been supplied.

## Surprises and production failure modes

Reserved for Damien's independently written observations after running the system.

## Why this matters

Reserved for Damien's independently written three-to-four-sentence explanation for a non-technical customer stakeholder.
