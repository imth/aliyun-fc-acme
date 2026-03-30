from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class CertConfig:
    name: str
    domains: list[str]


@dataclass
class AppConfig:
    cert_configs: list[CertConfig]
    acme_email: str | None = None
    acme_staging: bool = False
    renew_days: int = 30
    deploy_to: list[str] = field(default_factory=list)


def load_config() -> AppConfig:
    required = ["CERT_CONFIGS"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    raw_certs = json.loads(os.environ["CERT_CONFIGS"])
    if not raw_certs:
        raise ValueError("CERT_CONFIGS must contain at least one certificate configuration")

    cert_configs = [
        CertConfig(
            name=c["name"],
            domains=c["domains"],
        )
        for c in raw_certs
    ]

    staging_str = os.environ.get("ACME_STAGING", "false").lower()
    acme_staging = staging_str == "true"

    renew_days = int(os.environ.get("RENEW_DAYS", "30"))
    renew_days = max(1, min(90, renew_days))

    deploy_str = os.environ.get("DEPLOY_TO", "")
    deploy_to = [s.strip().lower() for s in deploy_str.split(",") if s.strip()]

    return AppConfig(
        cert_configs=cert_configs,
        acme_email=os.environ.get("ACME_EMAIL"),
        acme_staging=acme_staging,
        renew_days=renew_days,
        deploy_to=deploy_to,
    )
