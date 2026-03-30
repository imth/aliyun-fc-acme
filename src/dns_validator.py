from __future__ import annotations

import logging
import time

from alibabacloud_alidns20150109 import models as dns_models
from alibabacloud_alidns20150109.client import Client as DnsClient
from alibabacloud_credentials.client import Client as CredClient
from alibabacloud_tea_openapi import models as open_api_models
from dns import resolver

logger = logging.getLogger(__name__)


def parse_domain_and_rr(domain: str) -> tuple[str, str]:
    """Parse a domain into (base_domain, RR) for the _acme-challenge TXT record.

    Examples:
        "example.com"       -> ("example.com", "_acme-challenge")
        "*.example.com"     -> ("example.com", "_acme-challenge")
        "sub.example.com"   -> ("example.com", "_acme-challenge.sub")
        "*.sub.example.com" -> ("sub.example.com", "_acme-challenge")
    """
    is_wildcard = domain.startswith("*.")
    clean = domain.removeprefix("*.")

    if is_wildcard:
        # Wildcard: the entire cleaned domain is the base domain, RR has no subdomain prefix
        return clean, "_acme-challenge"

    parts = clean.split(".")
    # Base domain is always the last two parts
    base_domain = ".".join(parts[-2:])

    if len(parts) > 2:
        # Has subdomain prefix
        sub = ".".join(parts[:-2])
        rr = f"_acme-challenge.{sub}"
    else:
        rr = "_acme-challenge"

    return base_domain, rr


class DnsValidator:
    def __init__(self):
        config = open_api_models.Config(
            credential=CredClient(),
            endpoint="alidns.aliyuncs.com",
        )
        self._client = DnsClient(config)
        self._records: list[dict] = []

    def add_txt_record(self, domain: str, validation: str) -> None:
        base_domain, rr = parse_domain_and_rr(domain)

        request = dns_models.AddDomainRecordRequest(
            domain_name=base_domain,
            rr=rr,
            type="TXT",
            value=validation,
            ttl=600,
        )
        response = self._client.add_domain_record(request)
        record_id = response.body.record_id

        fqdn = f"{rr}.{base_domain}"
        self._records.append(
            {
                "record_id": record_id,
                "domain_name": base_domain,
                "fqdn": fqdn,
                "validation": validation,
            }
        )
        logger.info("Added TXT record %s = %s (id: %s)", fqdn, validation, record_id)

    def wait_for_propagation(self, timeout: int = 120, interval: int = 10) -> None:
        logger.info("Waiting for DNS propagation (max %ds)...", timeout)

        # Collect unique FQDNs and expected validation values
        expected: dict[str, set[str]] = {}
        for rec in self._records:
            expected.setdefault(rec["fqdn"], set()).add(rec["validation"])

        res = resolver.Resolver()
        res.nameservers = ["8.8.8.8"]

        elapsed = 0
        while elapsed < timeout:
            all_found = True
            for fqdn, values in expected.items():
                try:
                    answers = res.resolve(fqdn, "TXT")
                    found = {rdata.to_text().strip('"') for rdata in answers}
                    if not values.issubset(found):
                        all_found = False
                        break
                except Exception:
                    all_found = False
                    break

            if all_found:
                logger.info("DNS propagation confirmed after %ds", elapsed)
                return

            time.sleep(interval)
            elapsed += interval

        raise TimeoutError(f"DNS propagation not confirmed within {timeout}s")

    def cleanup(self) -> None:
        for rec in self._records:
            try:
                request = dns_models.DeleteDomainRecordRequest(record_id=rec["record_id"])
                self._client.delete_domain_record(request)
                logger.info("Deleted TXT record %s", rec["record_id"])
            except Exception as e:
                logger.warning("Failed to delete TXT record %s: %s", rec["record_id"], e)
        self._records = []
