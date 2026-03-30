from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.oss_deployer import OssDeployer, domain_matches


class TestDomainMatches:
    def test_exact_match(self):
        assert domain_matches("example.com", ["example.com", "*.example.com"]) is True

    def test_wildcard_match(self):
        assert domain_matches("cdn.example.com", ["example.com", "*.example.com"]) is True

    def test_deep_subdomain_matches_wildcard(self):
        assert domain_matches("a.b.example.com", ["*.example.com"]) is False

    def test_no_match(self):
        assert domain_matches("other.com", ["example.com", "*.example.com"]) is False

    def test_wildcard_does_not_match_apex(self):
        assert domain_matches("example.com", ["*.example.com"]) is False

    def test_only_wildcard_cert(self):
        assert domain_matches("sub.example.com", ["*.example.com"]) is True


class TestOssDeployer:
    @patch("src.oss_deployer.oss2")
    @patch("src.oss_deployer.CredClient")
    def test_deploy_cert_replaces_matching_domain(self, MockCredClient, mock_oss2):
        # Setup credentials
        mock_cred = MockCredClient.return_value
        mock_cred.get_access_key_id.return_value = "ak"
        mock_cred.get_access_key_secret.return_value = "sk"
        mock_cred.get_security_token.return_value = None

        # Setup bucket listing
        mock_bucket_info = MagicMock()
        mock_bucket_info.name = "my-bucket"
        mock_bucket_info.extranet_endpoint = "oss-cn-hangzhou.aliyuncs.com"

        mock_service = MagicMock()
        mock_oss2.BucketIterator.return_value = [mock_bucket_info]
        mock_oss2.Service.return_value = mock_service

        # Setup CNAME listing
        mock_cname = MagicMock()
        mock_cname.domain = "cdn.example.com"

        mock_cname_result = MagicMock()
        mock_cname_result.cname = [mock_cname]

        mock_bucket = MagicMock()
        mock_bucket.list_bucket_cname.return_value = mock_cname_result
        mock_oss2.Bucket.return_value = mock_bucket

        deployer = OssDeployer()
        updated = deployer.deploy_cert(["example.com", "*.example.com"], 12345)

        assert updated == ["cdn.example.com"]
        mock_bucket.put_bucket_cname.assert_called_once()
        # Verify cert_id is passed as string
        call_args = mock_bucket.put_bucket_cname.call_args[0][0]
        assert call_args.cert.cert_id == "12345"

    @patch("src.oss_deployer.oss2")
    @patch("src.oss_deployer.CredClient")
    def test_deploy_cert_no_match(self, MockCredClient, mock_oss2):
        mock_cred = MockCredClient.return_value
        mock_cred.get_access_key_id.return_value = "ak"
        mock_cred.get_access_key_secret.return_value = "sk"
        mock_cred.get_security_token.return_value = None

        mock_bucket_info = MagicMock()
        mock_bucket_info.name = "my-bucket"
        mock_bucket_info.extranet_endpoint = "oss-cn-hangzhou.aliyuncs.com"
        mock_oss2.BucketIterator.return_value = [mock_bucket_info]
        mock_oss2.Service.return_value = MagicMock()

        mock_cname = MagicMock()
        mock_cname.domain = "other.com"
        mock_cname_result = MagicMock()
        mock_cname_result.cname = [mock_cname]

        mock_bucket = MagicMock()
        mock_bucket.list_bucket_cname.return_value = mock_cname_result
        mock_oss2.Bucket.return_value = mock_bucket

        deployer = OssDeployer()
        updated = deployer.deploy_cert(["example.com"], 12345)

        assert updated == []
        mock_bucket.put_bucket_cname.assert_not_called()

    @patch("src.oss_deployer.oss2")
    @patch("src.oss_deployer.CredClient")
    def test_deploy_cert_uses_sts_auth_when_token_present(self, MockCredClient, mock_oss2):
        mock_cred = MockCredClient.return_value
        mock_cred.get_access_key_id.return_value = "ak"
        mock_cred.get_access_key_secret.return_value = "sk"
        mock_cred.get_security_token.return_value = "sts-token"

        mock_oss2.BucketIterator.return_value = []
        mock_oss2.Service.return_value = MagicMock()

        deployer = OssDeployer()
        deployer.deploy_cert(["example.com"], 12345)

        mock_oss2.StsAuth.assert_called_once_with("ak", "sk", "sts-token")
        mock_oss2.Auth.assert_not_called()
