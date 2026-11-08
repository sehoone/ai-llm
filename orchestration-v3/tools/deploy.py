"""Deploy one explicitly selected Compose environment."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import smoke_login

ROOT = Path(__file__).resolve().parent.parent
DEPLOY = ROOT / "deploy"
COMPOSE = DEPLOY / "docker-compose.yml"
ENVIRONMENTS = ("local", "dev", "stg", "prd")


def compose_command(environment: str) -> tuple[list[str], dict[str, str]]:
    env_dir = DEPLOY / "environments" / environment
    for name in ("compose.env", "api.env"):
        if not (env_dir / name).is_file():
            raise ValueError(f"필수 설정 파일이 없습니다: {env_dir / name}")

    # Compose gives shell variables precedence over --env-file. Prevent a
    # previous environment's shell settings from overriding the selected one.
    variables = re.findall(r"\$\{([A-Z][A-Z0-9_]*)", COMPOSE.read_text(encoding="utf-8"))
    child_env = os.environ.copy()
    for key in list(child_env):
        if key in variables or key.startswith("COMPOSE_"):
            child_env.pop(key)
    child_env["DEPLOY_ENV"] = environment
    command = [
        "docker", "compose", "--project-name", f"orchestration-v3-{environment}",
        "--project-directory", str(DEPLOY), "--env-file", str(env_dir / "compose.env"),
        "-f", str(COMPOSE),
    ]
    return command, child_env


def validate_config(config: dict, environment: str) -> None:
    services = config["services"]
    api = services["api"]["environment"]
    db = services["db"]["environment"]
    langfuse = services["langfuse-web"]["environment"]
    clickhouse = services["clickhouse"]["environment"]
    minio = services["minio"]["environment"]
    grafana = services["grafana"]["environment"]
    secrets = {
        "JWT_SECRET_KEY": api.get("JWT_SECRET_KEY", ""),
        "POSTGRES_PASSWORD": db.get("POSTGRES_PASSWORD", ""),
        "CLICKHOUSE_PASSWORD": clickhouse.get("CLICKHOUSE_PASSWORD", ""),
        "MINIO_ROOT_PASSWORD": minio.get("MINIO_ROOT_PASSWORD", ""),
        "GRAFANA_PASSWORD": grafana.get("GF_SECURITY_ADMIN_PASSWORD", ""),
        "LANGFUSE_NEXTAUTH_SECRET": langfuse.get("NEXTAUTH_SECRET", ""),
        "LANGFUSE_SALT": langfuse.get("SALT", ""),
        "LANGFUSE_ENCRYPTION_KEY": langfuse.get("ENCRYPTION_KEY", ""),
    }
    for name, value in secrets.items():
        if not isinstance(value, str) or not value or any(
            placeholder in value.lower() for placeholder in ("replace_me", "change-me", "changeme")
        ):
            raise ValueError(f"{name}를 환경 전용 값으로 설정하세요.")
    if environment in ("stg", "prd"):
        default_values = {
            "POSTGRES_PASSWORD": "postgres",
            "CLICKHOUSE_PASSWORD": "clickhouse",
            "MINIO_ROOT_PASSWORD": "miniosecret",
            "GRAFANA_PASSWORD": "admin",
            "LANGFUSE_ENCRYPTION_KEY": "0" * 64,
        }
        for name, default in default_values.items():
            if secrets[name] == default:
                raise ValueError(f"{name}에 기본 비밀번호 또는 키를 사용할 수 없습니다.")
        seed_password = api.get("SEED_ADMIN_PASSWORD", "").lower()
        if seed_password and (
            seed_password == "admin1234"
            or any(placeholder in seed_password for placeholder in ("replace_me", "change-me", "changeme"))
        ):
            raise ValueError("SEED_ADMIN_PASSWORD에 기본 비밀번호 또는 예제 값을 사용할 수 없습니다.")
    if len(secrets["JWT_SECRET_KEY"]) < 32:
        raise ValueError("JWT_SECRET_KEY는 32자 이상이어야 합니다.")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", secrets["LANGFUSE_ENCRYPTION_KEY"]):
        raise ValueError("LANGFUSE_ENCRYPTION_KEY는 64자리 16진수여야 합니다.")
    # These values are also embedded in database URLs.
    for name, value in (
        ("POSTGRES_USER", db["POSTGRES_USER"]),
        ("POSTGRES_PASSWORD", secrets["POSTGRES_PASSWORD"]),
        ("POSTGRES_DB", db["POSTGRES_DB"]),
        ("CLICKHOUSE_PASSWORD", secrets["CLICKHOUSE_PASSWORD"]),
    ):
        if not re.fullmatch(r"[A-Za-z0-9._~-]+", value):
            raise ValueError(f"{name}에는 URL에 안전한 영문, 숫자, . _ ~ -만 사용하세요.")
    if len(secrets["MINIO_ROOT_PASSWORD"]) < 8:
        raise ValueError("MINIO_ROOT_PASSWORD는 8자 이상이어야 합니다.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("up", "test", "down"))
    parser.add_argument("environment", choices=ENVIRONMENTS)
    args = parser.parse_args()

    if args.action == "down" and args.environment == "prd" and os.environ.get("CONFIRM_PRD") != "prd":
        print("prd 종료에는 환경변수 CONFIRM_PRD=prd가 필요합니다.", file=sys.stderr)
        return 1
    if args.action == "test":
        missing = smoke_login.missing_config()
        if missing:
            print(f"배포 전 스모크 테스트 설정 필요: {', '.join(missing)}", file=sys.stderr)
            return 1

    try:
        command, child_env = compose_command(args.environment)
        result = subprocess.run(
            [*command, "config", "--format", "json"],
            env=child_env, stdout=subprocess.PIPE, text=True, check=True,
        )
        validate_config(json.loads(result.stdout), args.environment)
        action = ["down"] if args.action == "down" else ["up", "-d", "--build"]
        print(f"[deploy] {args.environment}: {args.action}", flush=True)
        subprocess.run([*command, *action], env=child_env, check=True)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        print(f"[deploy] 실패: {exc}", file=sys.stderr)
        return 1

    if args.action == "test":
        return smoke_login.main(args.environment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
