from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gcp" / "production-deploy.sh"
APIS = (
    "run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com "
    "sqladmin.googleapis.com secretmanager.googleapis.com cloudtasks.googleapis.com "
    "cloudscheduler.googleapis.com iam.googleapis.com iamcredentials.googleapis.com"
)


def _fake_tools(tmp_path: Path) -> tuple[dict[str, str], Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls.log"
    gcloud = bin_dir / "gcloud"
    gcloud.write_text(
        r'''#!/usr/bin/env bash
set -euo pipefail
printf '%q ' "$@" >> "$FAKE_GCLOUD_CALLS"; printf '\n' >> "$FAKE_GCLOUD_CALLS"
joined=" $* "
if [[ "$joined" == *" --help " ]]; then
  printf '%s\n' '--image --set-cloudsql-instances --set-env-vars --set-secrets --task-timeout --max-dispatches-per-second --max-concurrent-dispatches --max-attempts --max-retry-duration --oidc-token-audience --oidc-service-account-email --attempt-deadline'
  exit 0
fi
[[ "$joined" != *" --add-cloudsql-instances "* ]] || { echo unsupported >&2; exit 64; }
[[ "$joined" != *" --definitely-unknown "* ]] || { echo unknown-flag >&2; exit 64; }
if [[ "$joined" == *" run jobs deploy "* || ( "$joined" == *" run deploy "* && "$joined" != *" run deploy chess-ai-frontend "* ) ]]; then
  [[ "$joined" == *" --image "*"docker.pkg.dev/"* ]] || { echo invalid-image >&2; exit 64; }
  [[ "$joined" == *" --set-cloudsql-instances "* ]] || { echo missing-cloudsql >&2; exit 64; }
fi
case "$joined" in
  *" auth list "*) echo test@example.invalid ;;
  *" config get-value project "*) echo test-project ;;
  *" billing projects describe "*) echo True ;;
  *" services list "*) printf '%s\n' $FAKE_ENABLED_APIS ;;
  *" projects describe "*"value(projectNumber)"*) echo 123456 ;;
  *" sql instances describe "*"value(state)"*) echo RUNNABLE ;;
  *" sql instances describe "*"value(databaseVersion)"*) echo POSTGRES_17 ;;
  *" sql instances describe "*"value(settings.edition)"*) echo ENTERPRISE ;;
  *" sql instances describe "*"value(settings.tier)"*) echo db-f1-micro ;;
  *" sql instances describe "*"value(connectionName)"*) echo test-project:europe-west1:chess-ai-postgres ;;
  *" sql databases describe "*"value(name)"*) echo chess_ai_teacher ;;
  *" sql users list "*) echo chess_app ;;
  *" secrets versions describe "*) echo ENABLED ;;
  *" secrets versions access "*) echo scheduler-test-secret ;;
  *" run services describe "*)
    service="${4}"; echo "https://${service}-test.run.app"
    ;;
esac
''',
        encoding="utf-8",
    )
    gcloud.chmod(0o755)
    curl = bin_dir / "curl"
    curl.write_text(
        "#!/usr/bin/env bash\ncase \" $* \" in *\" -w \"*) printf 403;; esac\nexit 0\n",
        encoding="utf-8",
    )
    curl.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "FAKE_GCLOUD_CALLS": str(calls),
            "FAKE_ENABLED_APIS": APIS,
            "GCP_PROJECT_ID": "test-project",
            "GCP_REGION": "europe-west1",
            "ARTIFACT_REPOSITORY": "chess-ai-teacher",
            "BACKEND_SERVICE": "chess-ai-backend",
            "WORKER_SERVICE": "chess-ai-worker",
            "SYNC_SERVICE": "chess-ai-sync",
            "FRONTEND_SERVICE": "chess-ai-frontend",
            "MIGRATION_JOB": "chess-ai-migrate",
            "CLOUD_SQL_INSTANCE": "chess-ai-postgres",
            "CLOUD_SQL_DATABASE": "chess_ai_teacher",
            "CLOUD_SQL_USER": "chess_app",
            "CLOUD_TASKS_QUEUE": "chess-analysis",
            "BACKEND_SERVICE_ACCOUNT": "chess-backend",
            "WORKER_SERVICE_ACCOUNT": "chess-worker",
            "TASKS_INVOKER_SERVICE_ACCOUNT": "chess-tasks-invoker",
            "SCHEDULER_SERVICE_ACCOUNT": "chess-scheduler",
            "SCHEDULER_JOB": "chess-sync",
            "SCHEDULER_SCHEDULE": "* * * * *",
            "ALLOW_DIRTY_DEPLOY": "true",
            "FORCE_REBUILD": "true",
            "SCHEDULED_SYNC_SHARED_SECRET": "scheduler-test-secret",
            "DEPLOY_STATE_FILE": str(tmp_path / "deployment-state"),
        }
    )
    return env, calls


def _run(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), *args], cwd=ROOT, env=env, text=True,
        capture_output=True, check=False,
    )


def test_preflight_is_read_only(tmp_path: Path) -> None:
    env, calls = _fake_tools(tmp_path)
    result = _run("--preflight", env=env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PRECHECK PASSED — no resources changed" in result.stdout
    log = calls.read_text(encoding="utf-8")
    mutations = (" services enable ", " builds submit ", " run deploy ",
                 " run jobs deploy ", " sql instances create ",
                 " scheduler jobs update ", " secrets versions add ")
    assert not any(item in f" {log} " for item in mutations)


def test_apply_contract_and_data_flow(tmp_path: Path) -> None:
    env, calls = _fake_tools(tmp_path)
    result = _run("--apply", env=env)

    assert result.returncode == 0, result.stdout + result.stderr
    log = calls.read_text(encoding="utf-8")
    sha = subprocess.check_output(
        ["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT, text=True
    ).strip()
    backend_image = f"europe-west1-docker.pkg.dev/test-project/chess-ai-teacher/backend:{sha}"
    frontend_image = f"europe-west1-docker.pkg.dev/test-project/chess-ai-teacher/frontend:{sha}"

    assert f"--image {backend_image}" in log
    assert f"--image {sha} " not in log
    assert "run jobs deploy chess-ai-migrate" in log
    assert "--set-cloudsql-instances test-project:europe-west1:chess-ai-postgres" in log
    migration_line = next(line for line in log.splitlines() if "run jobs deploy chess-ai-migrate" in line)
    assert "--command alembic" in migration_line
    assert "--args upgrade\\,head" in migration_line
    assert "ANALYSIS_WORKER_URL" not in migration_line
    assert "CHESSCOM_USER_AGENT" not in migration_line
    assert "ANALYSIS_WORKER_SHARED_SECRET" not in migration_line
    assert "DATABASE_PASSWORD=DATABASE_PASSWORD:latest" in migration_line
    assert "ANALYSIS_WORKER_URL=https://chess-ai-worker-test.run.app" in log
    assert "_BACKEND_URL=https://chess-ai-backend-test.run.app" in log
    assert f"_IMAGE={frontend_image}" in log
    assert (
        "FRONTEND_ORIGINS=https://chess-ai-frontend-test.run.app,http://localhost:3000,"
        "http://127.0.0.1:3000"
    ) in log.replace("\\,", ",")
    scheduler_line = next(
        line for line in log.splitlines()
        if "scheduler jobs update http" in line and "--help" not in line
    )
    assert "--uri https://chess-ai-sync-test.run.app/internal/sync/chess-com" in scheduler_line
    assert "--oidc-token-audience https://chess-ai-sync-test.run.app" in scheduler_line
    assert r"--schedule \*\ \*\ \*\ \*\ \*" in scheduler_line
    assert "scheduler-test-secret" not in log
    mutation_log = "\n".join(line for line in log.splitlines() if "--help" not in line)
    assert "secrets versions add" not in mutation_log
    assert "artifacts repositories create" not in mutation_log
    assert "sql instances create" not in mutation_log
    assert "sql databases create" not in mutation_log
    assert "iam service-accounts create" not in mutation_log

    ordered = [
        "run jobs deploy chess-ai-migrate", "run jobs execute chess-ai-migrate",
        "run deploy chess-ai-worker", "tasks queues update chess-analysis",
        "run deploy chess-ai-backend", "run deploy chess-ai-sync",
        "scheduler jobs update http", "run deploy chess-ai-frontend",
    ]
    positions = [mutation_log.index(value) for value in ordered]
    assert positions == sorted(positions)
    state = Path(env["DEPLOY_STATE_FILE"]).read_text(encoding="utf-8")
    assert "smoke-test" in state
    assert "scheduler-test-secret" not in state


def test_resume_starts_at_requested_step(tmp_path: Path) -> None:
    env, calls = _fake_tools(tmp_path)
    result = _run("--apply", "--resume-from", "scheduler", env=env)

    assert result.returncode == 0, result.stdout + result.stderr
    log = calls.read_text(encoding="utf-8")
    mutation_lines = "\n".join(
        line for line in log.splitlines() if "--help" not in line
    )
    assert "run jobs deploy" not in mutation_lines
    assert "run deploy chess-ai-worker" not in mutation_lines
    assert "scheduler jobs update http" in mutation_lines
    assert "run deploy chess-ai-frontend" in mutation_lines


def test_no_args_and_help_contract(tmp_path: Path) -> None:
    env, _ = _fake_tools(tmp_path)
    no_args = _run(env=env)
    help_result = _run("--help", env=env)

    assert no_args.returncode == 2
    assert help_result.returncode == 0
    assert "--preflight" in help_result.stdout


def test_failed_preflight_blocks_all_mutations_and_fake_rejects_unknown_flag(
    tmp_path: Path,
) -> None:
    env, calls = _fake_tools(tmp_path)
    env["FAKE_ENABLED_APIS"] = "run.googleapis.com"
    result = _run("--apply", env=env)
    unknown = subprocess.run(
        ["gcloud", "run", "deploy", "service", "--definitely-unknown"],
        env=env, text=True, capture_output=True, check=False,
    )

    assert result.returncode != 0
    mutation_log = "\n".join(
        line for line in calls.read_text(encoding="utf-8").splitlines()
        if "--help" not in line
    )
    assert "services enable" not in mutation_log
    assert "run deploy chess-ai" not in mutation_log
    assert unknown.returncode == 64
