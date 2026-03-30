from __future__ import annotations

from unittest.mock import MagicMock

from src.dns_validator import DnsValidator, parse_domain_and_rr


class TestParseDomainAndRr:
    def test_bare_domain(self):
        domain, rr = parse_domain_and_rr("example.com")
        assert domain == "example.com"
        assert rr == "_acme-challenge"

    def test_wildcard_domain(self):
        domain, rr = parse_domain_and_rr("*.example.com")
        assert domain == "example.com"
        assert rr == "_acme-challenge"

    def test_subdomain(self):
        domain, rr = parse_domain_and_rr("sub.example.com")
        assert domain == "example.com"
        assert rr == "_acme-challenge.sub"

    def test_wildcard_subdomain(self):
        domain, rr = parse_domain_and_rr("*.sub.example.com")
        assert domain == "sub.example.com"
        assert rr == "_acme-challenge"


class TestDnsValidatorAddRecord:
    def test_add_txt_record(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.body.record_id = "rec-123"
        mock_client.add_domain_record.return_value = mock_response

        validator = DnsValidator.__new__(DnsValidator)
        validator._client = mock_client
        validator._records = []

        validator.add_txt_record("example.com", "validation-token")

        mock_client.add_domain_record.assert_called_once()
        req = mock_client.add_domain_record.call_args[0][0]
        assert req.domain_name == "example.com"
        assert req.rr == "_acme-challenge"
        assert req.type == "TXT"
        assert req.value == "validation-token"
        assert req.ttl == 600
        assert len(validator._records) == 1
        assert validator._records[0]["fqdn"] == "_acme-challenge.example.com"
        assert validator._records[0]["validation"] == "validation-token"

    def test_add_wildcard_record(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.body.record_id = "rec-456"
        mock_client.add_domain_record.return_value = mock_response

        validator = DnsValidator.__new__(DnsValidator)
        validator._client = mock_client
        validator._records = []

        validator.add_txt_record("*.example.com", "validation-token-2")

        req = mock_client.add_domain_record.call_args[0][0]
        assert req.domain_name == "example.com"
        assert req.rr == "_acme-challenge"


class TestDnsValidatorCleanup:
    def test_cleanup_deletes_all_records(self):
        mock_client = MagicMock()

        validator = DnsValidator.__new__(DnsValidator)
        validator._client = mock_client
        validator._records = [
            {
                "record_id": "rec-1",
                "domain_name": "example.com",
                "fqdn": "_acme-challenge.example.com",
                "validation": "v1",
            },
            {
                "record_id": "rec-2",
                "domain_name": "example.com",
                "fqdn": "_acme-challenge.example.com",
                "validation": "v2",
            },
        ]

        validator.cleanup()

        assert mock_client.delete_domain_record.call_count == 2
        assert validator._records == []
