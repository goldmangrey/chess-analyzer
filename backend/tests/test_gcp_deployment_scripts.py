from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GCP_SCRIPTS = ROOT / "scripts" / "gcp"


def _deployment_env(tmp_path: Path) -> tuple[dict[str, str], Path]:
    calls = tmp_path / "gcloud-calls.log"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gcloud = fake_bin / "gcloud"
    fake_gcloud.write_text(
        """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$FAKE_GCLOUD_CALLS"
if [[ "$*" == *"sql instances describe"* ]] || [[ "$*" == *"sql databases describe"* ]]; then
  exit 1
fi
if [[ "$*" == *"auth list"* ]]; then printf '%s\\n' 'test@example.invalid'; fi
exit 0
""",
        encoding="utf-8",
    )
    fake_gcloud.chmod(0o755)
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "FAKE_GCLOUD_CALLS": str(calls),
            "GCP_PROJECT_ID": "test-project",
            "GCP_REGION": "europe-west1",
            "DATABASE_PASSWORD": "regression-secret-value",
            "CHESSCOM_USER_AGENT": "ChessAITeacher test",
            "ANALYSIS_WORKER_SHARED_SECRET": "worker-test-secret",
            "SCHEDULED_SYNC_SHARED_SECRET": "sync-test-secret",
        }
    )
    return env, calls


def _run(script: str, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(GCP_SCRIPTS / script), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_deploy_all_empty_args_is_non_mutating_dry_run(tmp_path: Path) -> None:
    env, calls = _deployment_env(tmp_path)
    result = _run("deploy-all.sh", env=env)

    assert result.returncode == 0, result.stderr
    assert "Dry-run:" in result.stdout
    invoked = calls.read_text(encoding="utf-8")
    forbidden = (
        "services enable",
        "builds submit",
        "sql instances create",
        "run deploy",
        "scheduler jobs create",
        "scheduler jobs update",
        "secrets versions add",
    )
    assert not any(command in invoked for command in forbidden)


def test_help_and_apply_argument_paths(tmp_path: Path) -> None:
    env, calls = _deployment_env(tmp_path)
    help_result = _run("deploy-all.sh", "--help", env=env)
    apply_result = _run("enable-apis.sh", "--apply", env=env)

    assert help_result.returncode == 0
    assert "Usage:" in help_result.stdout
    assert apply_result.returncode == 0, apply_result.stderr
    assert "services enable" in calls.read_text(encoding="utf-8")


def test_cloud_sql_dry_run_uses_enterprise_shared_core_without_secrets(
    tmp_path: Path,
) -> None:
    env, _ = _deployment_env(tmp_path)
    result = _run("create-cloud-sql.sh", env=env)

    assert result.returncode == 0, result.stderr
    assert "--project test-project" in result.stdout
    assert "--region europe-west1" in result.stdout
    assert "--database-version POSTGRES_17" in result.stdout
    assert "--edition enterprise" in result.stdout
    assert "--tier db-f1-micro" in result.stdout
    assert "--storage-size 10" in result.stdout
    assert "regression-secret-value" not in result.stdout + result.stderr


def test_exported_environment_wins_over_deploy_env() -> None:
    env = os.environ.copy()
    env["GCP_PROJECT_ID"] = "explicit-test-project"
    result = subprocess.run(
        ["bash", "-c", "source scripts/gcp/common.sh; printf '%s' \"$GCP_PROJECT_ID\""],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "explicit-test-project"


def test_scheduler_contract_runs_every_minute() -> None:
    deploy_env = (ROOT / "deploy" / "gcp.env").read_text(encoding="utf-8")
    example_env = (ROOT / "deploy" / "gcp.env.example").read_text(encoding="utf-8")
    common = (GCP_SCRIPTS / "common.sh").read_text(encoding="utf-8")

    assert 'SCHEDULER_SCHEDULE="* * * * *"' in deploy_env
    assert 'SCHEDULER_SCHEDULE="* * * * *"' in example_env
    assert 'SCHEDULER_SCHEDULE:=* * * * *' in common
    assert "--schedule \"$SCHEDULER_SCHEDULE\"" in (
        GCP_SCRIPTS / "create-scheduler-job.sh"
    ).read_text(encoding="utf-8")


def test_cloud_sql_rejects_invalid_edition_and_shared_core_enterprise_plus(
    tmp_path: Path,
) -> None:
    env, _ = _deployment_env(tmp_path)
    env["CLOUD_SQL_EDITION"] = "placeholder"
    invalid = _run("create-cloud-sql.sh", env=env)

    env["CLOUD_SQL_EDITION"] = "enterprise-plus"
    incompatible = _run("create-cloud-sql.sh", env=env)

    assert invalid.returncode == 2
    assert "must be enterprise or enterprise-plus" in invalid.stderr
    assert incompatible.returncode == 2
    assert "db-f1-micro is available only" in incompatible.stderr


def test_cloud_sql_rejects_explicit_empty_configuration(tmp_path: Path) -> None:
    env, _ = _deployment_env(tmp_path)
    env["CLOUD_SQL_TIER"] = ""
    result = _run("create-cloud-sql.sh", env=env)

    assert result.returncode == 2
    assert "CLOUD_SQL_TIER must be configured" in result.stderr
