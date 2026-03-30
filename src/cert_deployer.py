from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from alibabacloud_cas20200407 import models as cas_models
from alibabacloud_cas20200407.client import Client as CasClient
from alibabacloud_credentials.client import Client as CredClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

logger = logging.getLogger(__name__)


@dataclass
class CertInfo:
    cert_id: int
    end_time_ms: int  # millisecond timestamp


class CertDeployer:
    def __init__(self):
        config = open_api_models.Config(
            credential=CredClient(),
            endpoint="cas.aliyuncs.com",
        )
        self._client = CasClient(config)
        self._runtime = util_models.RuntimeOptions()

    def list_certificates(self) -> dict[str, CertInfo]:
        """Query uploaded certificates from CAS. Returns {config_name: CertInfo} with the latest cert per config name.

        Certificate names in CAS follow the format "{config_name}-{timestamp}".
        We extract the config name by removing the last "-YYYYMMDDHHMMSS" suffix.
        """
        request = cas_models.ListUserCertificateOrderRequest(
            order_type="UPLOAD",
            show_size=100,
            current_page=1,
        )
        response = self._client.list_user_certificate_order_with_options(request, self._runtime)
        certs = response.body.certificate_order_list or []

        result: dict[str, CertInfo] = {}
        for cert in certs:
            cas_name = cert.name or ""
            # Extract config name: "example.com-20260330120000" -> "example.com"
            # Find last dash followed by digits only
            parts = cas_name.rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit():
                config_name = parts[0]
            else:
                config_name = cas_name

            end_time = cert.cert_end_time or 0
            info = CertInfo(cert_id=cert.certificate_id, end_time_ms=end_time)

            if config_name not in result or end_time > result[config_name].end_time_ms:
                result[config_name] = info

        logger.info("Found %d unique certificates in CAS", len(result))
        return result

    def upload_certificate(self, name: str, cert_pem: str, key_pem: str) -> int:
        """Upload a new certificate to CAS. Returns the new cert_id.

        CAS requires unique names per upload, so we append a timestamp suffix.
        The name format is: "{name}-{YYYYMMDDHHMMSS}" (e.g. "example.com-20260330120000").
        list_certificates() matches by prefix to find certs belonging to a config name.
        """
        upload_name = f"{name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        request = cas_models.UploadUserCertificateRequest(
            name=upload_name,
            cert=cert_pem,
            key=key_pem,
        )
        response = self._client.upload_user_certificate_with_options(request, self._runtime)
        cert_id = response.body.cert_id
        logger.info("Uploaded certificate '%s' to CAS (cert_id: %d)", upload_name, cert_id)
        return cert_id
