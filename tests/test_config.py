import json

import pytest

from src.config import load_config


class TestLoadConfig:
    def test_loads_valid_config(self, monkeypatch):
        certs = [{"name": "example.com", "domains": ["example.com", "*.example.com"]}]
        monkeypatch.setenv("CERT_CONFIGS", json.dumps(certs))
        monkeypatch.setenv("ACME_EMAIL", "admin@example.com")

        config = load_config()

        assert len(config.cert_configs) == 1
        assert config.cert_configs[0].name == "example.com"
        assert config.cert_configs[0].domains == ["example.com", "*.example.com"]
        assert config.acme_email == "admin@example.com"

    def test_defaults_staging_to_false(self, monkeypatch):
        certs = [{"name": "t.com", "domains": ["t.com"]}]
        monkeypatch.setenv("CERT_CONFIGS", json.dumps(certs))
        monkeypatch.setenv("ACME_EMAIL", "a@b.com")

        config = load_config()
        assert config.acme_staging is False

    def test_staging_true(self, monkeypatch):
        certs = [{"name": "t.com", "domains": ["t.com"]}]
        monkeypatch.setenv("CERT_CONFIGS", json.dumps(certs))
        monkeypatch.setenv("ACME_EMAIL", "a@b.com")
        monkeypatch.setenv("ACME_STAGING", "true")

        config = load_config()
        assert config.acme_staging is True

    def test_defaults_renew_days_to_30(self, monkeypatch):
        certs = [{"name": "t.com", "domains": ["t.com"]}]
        monkeypatch.setenv("CERT_CONFIGS", json.dumps(certs))
        monkeypatch.setenv("ACME_EMAIL", "a@b.com")

        config = load_config()
        assert config.renew_days == 30

    def test_renew_days_clamped(self, monkeypatch):
        certs = [{"name": "t.com", "domains": ["t.com"]}]
        monkeypatch.setenv("CERT_CONFIGS", json.dumps(certs))
        monkeypatch.setenv("ACME_EMAIL", "a@b.com")
        monkeypatch.setenv("RENEW_DAYS", "100")

        config = load_config()
        assert config.renew_days == 90

    def test_deploy_to_defaults_empty(self, monkeypatch):
        certs = [{"name": "t.com", "domains": ["t.com"]}]
        monkeypatch.setenv("CERT_CONFIGS", json.dumps(certs))
        monkeypatch.setenv("ACME_EMAIL", "a@b.com")

        config = load_config()
        assert config.deploy_to == []

    def test_deploy_to_single(self, monkeypatch):
        certs = [{"name": "t.com", "domains": ["t.com"]}]
        monkeypatch.setenv("CERT_CONFIGS", json.dumps(certs))
        monkeypatch.setenv("ACME_EMAIL", "a@b.com")
        monkeypatch.setenv("DEPLOY_TO", "oss")

        config = load_config()
        assert config.deploy_to == ["oss"]

    def test_deploy_to_multiple(self, monkeypatch):
        certs = [{"name": "t.com", "domains": ["t.com"]}]
        monkeypatch.setenv("CERT_CONFIGS", json.dumps(certs))
        monkeypatch.setenv("ACME_EMAIL", "a@b.com")
        monkeypatch.setenv("DEPLOY_TO", "oss, cdn")

        config = load_config()
        assert config.deploy_to == ["oss", "cdn"]

    def test_missing_required_env_raises(self, monkeypatch):
        monkeypatch.delenv("CERT_CONFIGS", raising=False)

        with pytest.raises(ValueError):
            load_config()

    def test_acme_email_optional(self, monkeypatch):
        certs = [{"name": "t.com", "domains": ["t.com"]}]
        monkeypatch.setenv("CERT_CONFIGS", json.dumps(certs))

        config = load_config()
        assert config.acme_email is None

    def test_empty_cert_configs_raises(self, monkeypatch):
        monkeypatch.setenv("CERT_CONFIGS", "[]")
        monkeypatch.setenv("ACME_EMAIL", "a@b.com")

        with pytest.raises(ValueError):
            load_config()
