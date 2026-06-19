import os

from typer.testing import CliRunner

from veil.cli.main import app

runner = CliRunner()
ENV = {"VEIL_PASSWORD": "CliRunner!Pass#2026"}


def _run(args):
    return runner.invoke(app, args, env=ENV)


def test_config_init_and_show():
    result = _run(["--lang", "en", "config", "init", "--name", "cli1", "--storage", "disk"])
    assert result.exit_code == 0, result.output
    assert "initialized" in result.output.lower()

    result = _run(["--lang", "en", "config", "show", "--name", "cli1"])
    assert result.exit_code == 0, result.output
    assert "cli1" in result.output


def test_add_get_del_roundtrip():
    _run(["config", "init", "--name", "cli2", "--storage", "disk"])
    result = _run(["add", "k1", "secret-value", "--name", "cli2", "--storage", "disk"])
    assert result.exit_code == 0, result.output

    result = _run(["get", "k1", "--name", "cli2", "--storage", "disk"])
    assert result.exit_code == 0, result.output
    assert "secret-value" in result.output

    result = _run(["del", "k1", "--name", "cli2", "--storage", "disk"])
    assert result.exit_code == 0, result.output

    result = _run(["get", "k1", "--name", "cli2", "--storage", "disk"])
    assert result.exit_code == 1


def test_integrity_and_audit_verify():
    _run(["config", "init", "--name", "cli3", "--storage", "disk"])
    _run(["add", "k1", "value", "--name", "cli3", "--storage", "disk"])

    result = _run(["integrity", "k1", "--name", "cli3", "--storage", "disk"])
    assert result.exit_code == 0, result.output

    result = _run(["audit", "verify", "--name", "cli3", "--storage", "disk"])
    assert result.exit_code == 0, result.output


def test_wrong_password_cli():
    _run(["config", "init", "--name", "cli4", "--storage", "disk"])
    result = runner.invoke(
        app, ["get", "k1", "--name", "cli4", "--storage", "disk"],
        env={"VEIL_PASSWORD": "totally-wrong"},
    )
    assert result.exit_code == 1


def test_purge_requires_confirmation():
    _run(["config", "init", "--name", "cli5", "--storage", "disk"])
    result = _run(["purge", "--name", "cli5"])
    assert result.exit_code == 1  # refused without --yes

    result = _run(["purge", "--name", "cli5", "--yes"])
    assert result.exit_code == 0, result.output
