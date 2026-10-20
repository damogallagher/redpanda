"""Small operator commands. Compose parses profiles; no dotenv is executed as code."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from triage.config import Settings


class OperationError(Exception):
    pass


def environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COMPOSE_", "LLM_", "OLLAMA_", "INGEST_", "KAFKA_", "WORKER_", "PG"))
        and key
        not in {
            "OPENAI_API_KEY",
            "POSTGRES_PASSWORD",
            "CONNECT_PORT",
            "API_PORT",
            "SINK_PORT",
            "SINK_GROUP_ID",
        }
    }


def run(
    args: list[str], *, capture: bool = False, allow_failure: bool = False
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args, env=environment(), text=True, capture_output=capture, timeout=2400, check=False
    )
    if result.returncode and not allow_failure:
        # Captured config/provider output can contain secrets. Never echo it on errors.
        raise OperationError(
            "Docker command failed. Check Docker, the profile, and service health."
        )
    return result


def manage(command: str, delete: bool) -> int:
    profile = (
        ".env.frontier"
        if command == "test-frontier"
        else (".env.local" if command in {"test-local", "clean-ollama"} else ".env")
    )
    if not Path(profile).is_file():
        raise OperationError(
            f"Missing {profile}. Follow docs/operations.md to create/select a profile."
        )
    compose = ["docker", "compose", "--env-file", profile]
    config = json.loads(
        run([*compose, "--profile", "tools", "config", "--format", "json"], capture=True).stdout
    )
    if command.startswith("test-"):
        mode = command.removeprefix("test-")
        settings = Settings.from_env(config["services"]["model-check"]["environment"])
        if settings.backend != ("ollama" if mode == "local" else "openai"):
            raise OperationError(f"Wrong backend in {profile}; no model request was made.")
        bundled = settings.base_url.rstrip("/") == "http://ollama:11434"
        if bundled and (
            "model-init" not in config["services"]
            or config["services"]["model-init"]["command"][-1] != settings.model
        ):
            raise OperationError(
                "Set OLLAMA_MODEL and LLM_MODEL to the same tag in the local profile."
            )
        print(
            f"Testing {mode}: {settings.model}. At most 28 model calls; "
            "frontier calls incur charges.",
            flush=True,
        )
        run([*compose, "build", "model-check"])
        if bundled:
            run([*compose, "up", "-d", "--wait", "ollama"])
            run([*compose, "run", "--rm", "model-init"])
        result = run(
            [
                *compose,
                "run",
                "--rm",
                "--no-deps",
                "-v",
                f"{Path('tests/fixtures/acceptance').resolve()}:/acceptance:ro",
                "model-check",
                "triage-evaluate",
                "/acceptance/cases.json",
            ],
            capture=True,
            allow_failure=True,
        )
        if result.returncode not in {0, 1} or not result.stdout.strip():
            raise OperationError(
                "Model check could not run. Check the profile and model availability."
            )
        report = json.loads(result.stdout)
        Path("reports").mkdir(exist_ok=True)
        path = Path(f"reports/model-{mode}.json")
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as file:
            os.fchmod(file.fileno(), 0o600)
            file.write(json.dumps(report, indent=2) + "\n")
        print(
            f"{'PASS' if result.returncode == 0 else 'FAIL'}: "
            f"{report['passed']}/{report['total']} cases. Details: {path}"
        )
        return result.returncode
    logical = ["ollama-data"] if command == "clean-ollama" else ["redpanda-data", "postgres-data"]
    volumes = []
    if command == "clean-ollama" and "ollama" not in config["services"]:
        raise OperationError(
            "This local profile has no bundled Ollama. Native/remote Ollama is not modified."
        )
    if delete:
        for key in logical:
            volume = config["volumes"][key]
            if volume.get("external"):
                raise OperationError("Refusing to delete an external volume.")
            owned = run(
                [
                    "docker",
                    "volume",
                    "ls",
                    "-q",
                    "--filter",
                    f"label=com.docker.compose.project={config['name']}",
                    "--filter",
                    f"label=com.docker.compose.volume={key}",
                ],
                capture=True,
            ).stdout.splitlines()
            if owned and owned != [volume["name"]]:
                raise OperationError(
                    "Volume ownership does not match this project; no cleanup performed."
                )
            volumes.extend(owned)
    print(f"Stopping Compose project {config['name']}; private profiles are retained.", flush=True)
    run([*compose, "--profile", "tools", "down", "--remove-orphans"])
    if volumes:
        run(["docker", "volume", "rm", *volumes])
    print(
        "PASS: project stopped. "
        + (
            f"Deleted only project-owned {', '.join(logical)}."
            if delete
            else "All data and model weights retained."
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["test-local", "test-frontier", "clean-docker", "clean-ollama"]
    )
    parser.add_argument(
        "--delete-data", action="store_true", help="delete this project's broker/database volumes"
    )
    parser.add_argument(
        "--delete-models", action="store_true", help="delete this project's bundled Ollama weights"
    )
    args = parser.parse_args(argv)
    if (args.delete_data and args.command != "clean-docker") or (
        args.delete_models and args.command != "clean-ollama"
    ):
        parser.error(
            "Use --delete-data only with clean-docker; --delete-models only with clean-ollama."
        )
    try:
        return manage(args.command, args.delete_data or args.delete_models)
    except (OperationError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        message = (
            str(exc)
            if isinstance(exc, OperationError)
            else "Operation failed; check Docker and the profile. Diagnostic output is withheld."
        )
        print(message, file=sys.stderr)
        return 1
