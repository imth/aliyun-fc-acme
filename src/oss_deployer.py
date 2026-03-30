from __future__ import annotations

import logging

import oss2
from alibabacloud_credentials.client import Client as CredClient
from oss2.models import CertInfo, PutBucketCnameRequest

logger = logging.getLogger(__name__)

OSS_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"


def domain_matches(cname_domain: str, cert_domains: list[str]) -> bool:
    """Check if a CNAME domain matches any of the certificate's domains.

    Supports exact match and single-level wildcard match:
        "example.com" matches "example.com"
        "cdn.example.com" matches "*.example.com"
        "a.b.example.com" does NOT match "*.example.com" (wildcard is single-level)
    """
    for cert_domain in cert_domains:
        if cert_domain == cname_domain:
            return True
        if cert_domain.startswith("*."):
            # *.example.com matches sub.example.com but not a.b.example.com
            wildcard_base = cert_domain[2:]  # "example.com"
            if cname_domain.endswith(f".{wildcard_base}"):
                # Ensure only one level of subdomain
                prefix = cname_domain[: -(len(wildcard_base) + 1)]
                if "." not in prefix:
                    return True
    return False


class OssDeployer:
    def __init__(self):
        cred = CredClient()
        ak = cred.get_access_key_id()
        sk = cred.get_access_key_secret()
        token = cred.get_security_token()

        if token:
            self._auth = oss2.StsAuth(ak, sk, token)
        else:
            self._auth = oss2.Auth(ak, sk)

    def deploy_cert(self, domains: list[str], cert_id: int) -> list[str]:
        """Scan all OSS buckets, replace certificates on custom domains that match.

        Uses CAS cert_id to reference the certificate (no duplicate in OSS).
        Returns list of updated domain names.
        """
        updated: list[str] = []

        service = oss2.Service(self._auth, f"https://{OSS_DEFAULT_ENDPOINT}")
        for bucket_info in oss2.BucketIterator(service):
            endpoint = bucket_info.extranet_endpoint or OSS_DEFAULT_ENDPOINT
            bucket = oss2.Bucket(self._auth, f"https://{endpoint}", bucket_info.name)

            try:
                cname_result = bucket.list_bucket_cname()
            except Exception as e:
                logger.warning("Failed to list CNAME for bucket %s: %s", bucket_info.name, e)
                continue

            for cname in cname_result.cname or []:
                if domain_matches(cname.domain, domains):
                    try:
                        cert = CertInfo(cert_id=str(cert_id), force=True)
                        request = PutBucketCnameRequest(domain=cname.domain, cert=cert)
                        bucket.put_bucket_cname(request)
                        updated.append(cname.domain)
                        logger.info(
                            "Updated certificate for %s on bucket %s (cert_id: %d)",
                            cname.domain,
                            bucket_info.name,
                            cert_id,
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to update certificate for %s on bucket %s: %s",
                            cname.domain,
                            bucket_info.name,
                            e,
                        )

        return updated
