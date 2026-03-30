from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import josepy
from acme import challenges as acme_challenges
from acme import client as acme_client_module
from acme import messages
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.x509.oid import NameOID

logger = logging.getLogger(__name__)

STAGING_DIRECTORY = "https://acme-staging-v02.api.letsencrypt.org/directory"
PRODUCTION_DIRECTORY = "https://acme-v02.api.letsencrypt.org/directory"


@dataclass
class DnsChallenge:
    domain: str
    record_name: str
    validation: str
    _challb: object  # acme ChallengeBody, kept for answering


@dataclass
class AcmeOrder:
    challenges: list[DnsChallenge]
    _orderr: object  # acme OrderResource
    _cert_key_pem: str  # PEM-encoded cert private key


class AcmeClient:
    def __init__(self, email: str | None = None, staging: bool = True):
        self._email = email
        self._staging = staging
        self._directory_url = STAGING_DIRECTORY if staging else PRODUCTION_DIRECTORY
        self._client: acme_client_module.ClientV2 | None = None
        self._account_key: josepy.JWKRSA | None = None

    def register_account(self) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self._account_key = josepy.JWKRSA(key=private_key)

        net = acme_client_module.ClientNetwork(self._account_key)
        directory = acme_client_module.ClientV2.get_directory(self._directory_url, net)
        self._client = acme_client_module.ClientV2(directory, net=net)

        reg_kwargs: dict = {"terms_of_service_agreed": True}
        if self._email:
            reg_kwargs["email"] = self._email
        regr = self._client.new_account(messages.NewRegistration.from_data(**reg_kwargs))
        net.account = regr
        logger.info("ACME account registered: %s", regr.uri)

    def create_order(self, domains: list[str]) -> AcmeOrder:
        # Generate cert private key (separate from account key)
        cert_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cert_key_pem = cert_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        # Build CSR — always include SAN extension (Let's Encrypt requires it)
        builder = x509.CertificateSigningRequestBuilder()
        builder = builder.subject_name(
            x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domains[0])])
        )
        san_list = [x509.DNSName(d) for d in domains]
        builder = builder.add_extension(x509.SubjectAlternativeName(san_list), critical=False)
        csr = builder.sign(cert_key, SHA256())
        csr_pem = csr.public_bytes(serialization.Encoding.PEM)

        orderr = self._client.new_order(csr_pem)

        # Extract DNS-01 challenges
        dns_challenges = []
        for authzr in orderr.authorizations:
            domain = authzr.body.identifier.value
            for challb in authzr.body.challenges:
                if isinstance(challb.chall, acme_challenges.DNS01):
                    dns_challenges.append(
                        DnsChallenge(
                            domain=domain,
                            record_name=challb.chall.validation_domain_name(domain),
                            validation=challb.chall.validation(self._account_key),
                            _challb=challb,
                        )
                    )
                    break
            else:
                raise RuntimeError(f"No DNS-01 challenge found for {domain}")

        logger.info("ACME order created for domains: %s", domains)
        return AcmeOrder(challenges=dns_challenges, _orderr=orderr, _cert_key_pem=cert_key_pem)

    def submit_challenges(self, order: AcmeOrder) -> None:
        for chall in order.challenges:
            response = chall._challb.chall.response(self._account_key)
            self._client.answer_challenge(chall._challb, response)
            logger.info("Challenge submitted for %s", chall.domain)

    def finalize_and_download(self, order: AcmeOrder) -> tuple[str, str]:
        deadline = datetime.now() + timedelta(seconds=120)
        finalized = self._client.poll_and_finalize(order._orderr, deadline=deadline)
        cert_pem = finalized.fullchain_pem
        logger.info("Certificate issued successfully")
        return cert_pem, order._cert_key_pem
