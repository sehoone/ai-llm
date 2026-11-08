import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import deploy
import smoke_login


def valid_config():
    return {
        "services": {
            "api": {"environment": {"JWT_SECRET_KEY": "j" * 32}},
            "db": {"environment": {
                "POSTGRES_USER": "postgres", "POSTGRES_DB": "mydb", "POSTGRES_PASSWORD": "safe123"
            }},
            "langfuse-web": {"environment": {
                "NEXTAUTH_SECRET": "secret", "SALT": "salt", "ENCRYPTION_KEY": "a" * 64
            }},
            "clickhouse": {"environment": {"CLICKHOUSE_PASSWORD": "safe123"}},
            "minio": {"environment": {"MINIO_ROOT_PASSWORD": "safe12345"}},
            "grafana": {"environment": {"GF_SECURITY_ADMIN_PASSWORD": "secret"}},
        }
    }


class DeployTests(unittest.TestCase):
    def test_selects_project_and_ignores_shell_compose_variables(self):
        with patch.object(Path, "is_file", return_value=True), patch.dict(
            os.environ, {"POSTGRES_PASSWORD": "wrong", "COMPOSE_FILE": "wrong", "DEPLOY_ENV": "prd"}
        ):
            command, env = deploy.compose_command("dev")
        self.assertIn("orchestration-v3-dev", command)
        self.assertEqual(env["DEPLOY_ENV"], "dev")
        self.assertNotIn("POSTGRES_PASSWORD", env)
        self.assertNotIn("COMPOSE_FILE", env)

    def test_valid_config_and_reject_placeholders_and_invalid_urls(self):
        config = valid_config()
        deploy.validate_config(config, "dev")
        config["services"]["api"]["environment"]["JWT_SECRET_KEY"] = "REPLACE_ME"
        with self.assertRaises(ValueError):
            deploy.validate_config(config, "dev")
        config = valid_config()
        config["services"]["db"]["environment"]["POSTGRES_PASSWORD"] = "unsafe@password"
        with self.assertRaises(ValueError):
            deploy.validate_config(config, "dev")
        config = valid_config()
        config["services"]["langfuse-web"]["environment"]["ENCRYPTION_KEY"] = "invalid"
        with self.assertRaises(ValueError):
            deploy.validate_config(config, "dev")

    def test_stg_and_prd_reject_existing_default_passwords(self):
        config = valid_config()
        config["services"]["db"]["environment"]["POSTGRES_PASSWORD"] = "postgres"
        for environment in ("stg", "prd"):
            with self.subTest(environment=environment), self.assertRaises(ValueError):
                deploy.validate_config(config, environment)

    def test_prd_down_requires_confirmation(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "argv", ["deploy.py", "down", "prd"]):
            self.assertEqual(deploy.main(), 1)

    def test_down_keeps_volumes(self):
        completed = unittest.mock.Mock(stdout=json.dumps(valid_config()))
        with (
            patch.object(sys, "argv", ["deploy.py", "down", "dev"]),
            patch.object(deploy, "compose_command", return_value=(["docker", "compose"], {})),
            patch.object(deploy.subprocess, "run", return_value=completed) as run,
        ):
            self.assertEqual(deploy.main(), 0)
        self.assertEqual(run.call_args_list[1].args[0], ["docker", "compose", "down"])

    def test_missing_smoke_settings_prevent_deployment(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(sys, "argv", ["deploy.py", "test", "local"]),
            patch.object(deploy.subprocess, "run") as run,
        ):
            self.assertEqual(deploy.main(), 1)
            run.assert_not_called()


class SmokeTests(unittest.TestCase):
    def test_mismatch_does_not_send_credentials(self):
        health = unittest.mock.MagicMock()
        health.__enter__.return_value = io.BytesIO(b'{"env":"prd"}')
        with (
            patch.dict(os.environ, {
                "SMOKE_BASE_URL": "http://localhost:8060",
                "SMOKE_USERNAME": "test",
                "SMOKE_PASSWORD": "secret",
            }, clear=True),
            patch.object(smoke_login.urllib.request, "urlopen", return_value=health) as urlopen,
        ):
            self.assertEqual(smoke_login.main("stg"), 1)
            self.assertEqual(urlopen.call_count, 1)

    def test_matching_environment_and_login(self):
        def response(data):
            context = unittest.mock.MagicMock()
            context.__enter__.return_value = io.BytesIO(json.dumps(data).encode())
            return context

        with (
            patch.dict(os.environ, {
                "SMOKE_BASE_URL": "http://localhost:8060",
                "SMOKE_USERNAME": "test",
                "SMOKE_PASSWORD": "secret",
            }, clear=True),
            patch.object(smoke_login.urllib.request, "urlopen", side_effect=[
                response({"env": "local"}), response({"data": {"access_token": "token"}})
            ]) as urlopen,
        ):
            self.assertEqual(smoke_login.main("local"), 0)
            self.assertEqual(urlopen.call_count, 2)


if __name__ == "__main__":
    unittest.main()
