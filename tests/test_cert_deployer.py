from __future__ import annotations

from unittest.mock import MagicMock

from src.cert_deployer import CertDeployer


class TestListCertificates:
    def test_returns_cert_map(self):
        mock_client = MagicMock()

        cert1 = MagicMock()
        cert1.name = "example.com-20260101120000"
        cert1.certificate_id = 12345
        cert1.cert_end_time = 1780329600000

        cert2 = MagicMock()
        cert2.name = "example.com-20260301120000"
        cert2.certificate_id = 12346
        cert2.cert_end_time = 1788288000000

        mock_response = MagicMock()
        mock_response.body.certificate_order_list = [cert1, cert2]
        mock_response.body.total_count = 2
        mock_client.list_user_certificate_order_with_options.return_value = mock_response

        deployer = CertDeployer.__new__(CertDeployer)
        deployer._client = mock_client
        deployer._runtime = MagicMock()

        result = deployer.list_certificates()

        assert "example.com" in result
        assert result["example.com"].cert_id == 12346

    def test_empty_result(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.body.certificate_order_list = []
        mock_response.body.total_count = 0
        mock_client.list_user_certificate_order_with_options.return_value = mock_response

        deployer = CertDeployer.__new__(CertDeployer)
        deployer._client = mock_client
        deployer._runtime = MagicMock()

        result = deployer.list_certificates()
        assert result == {}


class TestUploadCertificate:
    def test_upload_returns_cert_id(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.body.cert_id = 99999
        mock_client.upload_user_certificate_with_options.return_value = mock_response

        deployer = CertDeployer.__new__(CertDeployer)
        deployer._client = mock_client
        deployer._runtime = MagicMock()

        cert_id = deployer.upload_certificate("test-cert", "CERT-PEM", "KEY-PEM")

        assert cert_id == 99999
        req = mock_client.upload_user_certificate_with_options.call_args[0][0]
        assert req.name.startswith("test-cert-")
        assert req.cert == "CERT-PEM"
        assert req.key == "KEY-PEM"
