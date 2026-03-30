from __future__ import annotations

import logging
from datetime import datetime

from src.acme_client import AcmeClient
from src.cert_deployer import CertDeployer
from src.config import load_config
from src.dns_validator import DnsValidator
from src.oss_deployer import OssDeployer

logger = logging.getLogger(__name__)


def run():
    config = load_config()

    deployer = CertDeployer()
    existing_certs = deployer.list_certificates()

    renewed = []
    skipped = []
    failed = []

    for cert_config in config.cert_configs:
        name = cert_config.name
        try:
            cert_info = existing_certs.get(name)
            if cert_info:
                expire_dt = datetime.fromtimestamp(cert_info.end_time_ms / 1000)
                days_left = (expire_dt - datetime.now()).days
                if days_left > config.renew_days:
                    logger.info(
                        "[%s] Certificate valid for %d more days, skipping", name, days_left
                    )
                    skipped.append(name)
                    continue
                logger.info("[%s] Certificate expires in %d days, renewing", name, days_left)
            else:
                logger.info("[%s] No existing certificate found, requesting new one", name)

            # ACME flow
            acme = AcmeClient(config.acme_email, staging=config.acme_staging)
            acme.register_account()

            dns = DnsValidator()
            try:
                order = acme.create_order(cert_config.domains)

                for chall in order.challenges:
                    dns.add_txt_record(chall.domain, chall.validation)

                dns.wait_for_propagation()
                acme.submit_challenges(order)
                cert_pem, key_pem = acme.finalize_and_download(order)
            finally:
                dns.cleanup()

            # Upload to CAS
            new_cert_id = deployer.upload_certificate(name, cert_pem, key_pem)

            # Deploy to configured services
            if "oss" in config.deploy_to:
                oss = OssDeployer()
                updated = oss.deploy_cert(cert_config.domains, new_cert_id)
                if updated:
                    logger.info("[%s] Updated OSS domains: %s", name, updated)

            renewed.append(name)
            logger.info("[%s] Certificate renewed successfully", name)

        except Exception as e:
            logger.error("[%s] Failed to renew certificate: %s", name, e, exc_info=True)
            failed.append(name)

    result = {"renewed": renewed, "skipped": skipped, "failed": failed}
    logger.info("Summary: %s", result)
    return result
