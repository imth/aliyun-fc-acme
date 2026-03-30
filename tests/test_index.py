from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.cert_deployer import CertInfo
from src.main import run


def _set_env(monkeypatch):
    certs = [{"name": "example.com", "domains": ["example.com", "*.example.com"]}]
    monkeypatch.setenv("CERT_CONFIGS", json.dumps(certs))
    monkeypatch.setenv("ACME_EMAIL", "test@example.com")
    monkeypatch.setenv("ACME_STAGING", "true")


class TestRun:
    @patch("src.main.CertDeployer")
    @patch("src.main.DnsValidator")
    @patch("src.main.AcmeClient")
    def test_skips_when_cert_not_expiring(self, MockAcme, MockDns, MockDeployer, monkeypatch):
        _set_env(monkeypatch)

        future_ms = int((datetime.now() + timedelta(days=60)).timestamp() * 1000)
        mock_deployer = MockDeployer.return_value
        mock_deployer.list_certificates.return_value = {
            "example.com": CertInfo(cert_id=123, end_time_ms=future_ms)
        }

        result = run()

        assert result["renewed"] == []
        MockAcme.return_value.register_account.assert_not_called()

    @patch("src.main.CertDeployer")
    @patch("src.main.DnsValidator")
    @patch("src.main.AcmeClient")
    def test_renews_expiring_cert(self, MockAcme, MockDns, MockDeployer, monkeypatch):
        _set_env(monkeypatch)

        expire_ms = int((datetime.now() + timedelta(days=10)).timestamp() * 1000)
        mock_deployer = MockDeployer.return_value
        mock_deployer.list_certificates.return_value = {
            "example.com": CertInfo(cert_id=123, end_time_ms=expire_ms)
        }

        mock_acme = MockAcme.return_value
        mock_order = MagicMock()
        mock_order.challenges = [
            MagicMock(
                domain="example.com", validation="v1", record_name="_acme-challenge.example.com"
            ),
            MagicMock(
                domain="*.example.com", validation="v2", record_name="_acme-challenge.example.com"
            ),
        ]
        mock_acme.create_order.return_value = mock_order
        mock_acme.finalize_and_download.return_value = ("CERT", "KEY")

        mock_dns = MockDns.return_value

        result = run()

        assert result["renewed"] == ["example.com"]
        mock_acme.register_account.assert_called_once()
        mock_dns.add_txt_record.assert_any_call("example.com", "v1")
        mock_dns.add_txt_record.assert_any_call("*.example.com", "v2")
        mock_dns.wait_for_propagation.assert_called_once()
        mock_acme.submit_challenges.assert_called_once()
        mock_deployer.upload_certificate.assert_called_once_with("example.com", "CERT", "KEY")
        mock_dns.cleanup.assert_called_once()

    @patch("src.main.CertDeployer")
    @patch("src.main.DnsValidator")
    @patch("src.main.AcmeClient")
    def test_renews_missing_cert(self, MockAcme, MockDns, MockDeployer, monkeypatch):
        _set_env(monkeypatch)

        mock_deployer = MockDeployer.return_value
        mock_deployer.list_certificates.return_value = {}
        mock_deployer.upload_certificate.return_value = 789

        mock_acme = MockAcme.return_value
        mock_order = MagicMock()
        mock_order.challenges = [MagicMock(domain="example.com", validation="v1")]
        mock_acme.create_order.return_value = mock_order
        mock_acme.finalize_and_download.return_value = ("CERT", "KEY")

        result = run()

        assert result["renewed"] == ["example.com"]

    @patch("src.main.CertDeployer")
    @patch("src.main.DnsValidator")
    @patch("src.main.AcmeClient")
    def test_error_in_one_group_continues(self, MockAcme, MockDns, MockDeployer, monkeypatch):
        certs = [
            {"name": "fail.com", "domains": ["fail.com"]},
            {"name": "ok.com", "domains": ["ok.com"]},
        ]
        monkeypatch.setenv("CERT_CONFIGS", json.dumps(certs))
        monkeypatch.setenv("ACME_EMAIL", "test@example.com")
        monkeypatch.setenv("ACME_STAGING", "true")

        mock_deployer = MockDeployer.return_value
        mock_deployer.list_certificates.return_value = {}
        mock_deployer.upload_certificate.return_value = 100

        mock_acme = MockAcme.return_value
        mock_order_ok = MagicMock()
        mock_order_ok.challenges = [MagicMock(domain="ok.com", validation="v")]
        mock_acme.create_order.side_effect = [RuntimeError("ACME error"), mock_order_ok]
        mock_acme.finalize_and_download.return_value = ("CERT", "KEY")

        result = run()

        assert "ok.com" in result["renewed"]
        assert "fail.com" in result["failed"]
