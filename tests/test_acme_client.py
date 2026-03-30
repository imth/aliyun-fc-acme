from __future__ import annotations

from unittest.mock import MagicMock, patch

from acme import challenges as acme_challenges

from src.acme_client import AcmeClient, AcmeOrder


class TestAcmeClientRegister:
    @patch("src.acme_client.acme_client_module.ClientV2")
    @patch("src.acme_client.acme_client_module.ClientNetwork")
    def test_register_creates_account(self, mock_net_cls, mock_client_cls):
        mock_net = MagicMock()
        mock_net_cls.return_value = mock_net
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client_cls.get_directory.return_value = MagicMock()
        mock_client.new_account.return_value = MagicMock()

        client = AcmeClient("test@example.com", staging=True)
        client.register_account()

        mock_client.new_account.assert_called_once()
        call_args = mock_client.new_account.call_args[0][0]
        assert call_args.terms_of_service_agreed is True


class TestAcmeClientOrder:
    def test_create_order_returns_challenges(self):
        client = AcmeClient.__new__(AcmeClient)
        client._client = MagicMock()
        client._account_key = MagicMock()

        # Mock a DNS-01 challenge
        mock_chall = MagicMock(spec=acme_challenges.DNS01)
        mock_chall.validation.return_value = "validation-token-abc"
        mock_chall.validation_domain_name.return_value = "_acme-challenge.example.com"
        mock_challb = MagicMock()
        mock_challb.chall = mock_chall

        # Mock authorization
        mock_authz = MagicMock()
        mock_authz.body.identifier.value = "example.com"
        mock_authz.body.challenges = [mock_challb]

        # Mock order
        mock_orderr = MagicMock()
        mock_orderr.authorizations = [mock_authz]
        client._client.new_order.return_value = mock_orderr

        order = client.create_order(["example.com"])

        assert len(order.challenges) == 1
        assert order.challenges[0].domain == "example.com"
        assert order.challenges[0].validation == "validation-token-abc"
        assert order.challenges[0].record_name == "_acme-challenge.example.com"


class TestAcmeClientFinalize:
    def test_poll_and_finalize_returns_cert_and_key(self):
        client = AcmeClient.__new__(AcmeClient)
        client._client = MagicMock()
        client._account_key = MagicMock()

        mock_finalized = MagicMock()
        mock_finalized.fullchain_pem = (
            "-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----"
        )
        client._client.poll_and_finalize.return_value = mock_finalized

        order = AcmeOrder.__new__(AcmeOrder)
        order._orderr = MagicMock()
        order._cert_key_pem = "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----"

        cert_pem, key_pem = client.finalize_and_download(order)

        assert "BEGIN CERTIFICATE" in cert_pem
        assert "BEGIN RSA PRIVATE KEY" in key_pem
        client._client.poll_and_finalize.assert_called_once()
