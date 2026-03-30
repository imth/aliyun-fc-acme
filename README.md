# aliyun-fc-acme

[English](#english) | [中文](#中文)

## English

Automatic SSL certificate renewal for Alibaba Cloud Function Compute (FC). Obtains free certificates via ACME protocol (Let's Encrypt), uploads to Alibaba Cloud Certificate Management Service (CAS), and auto-deploys to OSS custom domains.

### Features

- Auto obtain/renew Let's Encrypt SSL certificates
- DNS-01 validation via Alibaba Cloud DNS API
- Wildcard and SAN multi-domain certificates
- Upload certificates to Alibaba Cloud CAS
- Auto-deploy to OSS custom domains (scans all buckets, matches domains, replaces certs)
- Extensible deployment targets (`DEPLOY_TO`), future support for CDN, SLB, etc.
- Fully stateless, designed for serverless environments

### Configuration

Environment variables:

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `CERT_CONFIGS` | Yes | JSON certificate group config | - |
| `ACME_EMAIL` | No | ACME email for expiry reminders | empty |
| `ACME_STAGING` | No | Use LE staging environment | `false` |
| `RENEW_DAYS` | No | Days before expiry to trigger renewal | `30` |
| `DEPLOY_TO` | No | Deploy targets, comma-separated (currently: `oss`) | empty (CAS only) |

> **Note**: When configuring `CERT_CONFIGS` in the FC console, enter the raw JSON directly **without** wrapping quotes. Example:
>
> `[{"name": "example.com", "domains": ["example.com", "*.example.com"]}]`

#### CERT_CONFIGS Format

```json
[
  {
    "name": "example.com",
    "domains": ["example.com", "*.example.com"]
  }
]
```

- `name`: Certificate identifier (used in CAS naming)
- `domains`: Domain list, first entry used as CN

### Deployment

#### 1. Get deploy.zip

**Option A**: Download from [GitHub Releases](https://github.com/imth/aliyun-fc-acme/releases/latest).

**Option B**: Build locally (requires Docker):

```bash
python build.py
```

#### 2. Upload to FC

Create a function in the Alibaba Cloud console, choose "Upload Code Package", upload `deploy.zip`.

- Runtime: Python 3.10+
- Handler: index.handler
- Timeout: 600 seconds
- Memory: 512 MB

#### 3. Timer Trigger

Cron expression: `0 0 3 * * *` (daily at 3:00 AM)

#### 4. Credentials

Two authentication methods are supported:

**Option 1: FC Service Role (Recommended)**

Create a custom RAM policy: [RAM Console](https://ram.console.aliyun.com/) → **Policies** → **Create Policy** → "Script Editor", paste:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "alidns:*",
        "yundun-cert:*",
        "oss:*"
      ],
      "Resource": "*"
    }
  ]
}
```

Save as `fc-acme-cert-policy`, then go to **Roles** → find FC service role → **Add Permissions** → select `fc-acme-cert-policy`.

> **Note**: Do not paste into the role's "Trust Policy". Trust policies define who can assume the role, not what permissions the role has.

**Option 2: AccessKey Environment Variables**

| Variable | Description |
|----------|-------------|
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | Alibaba Cloud AccessKey ID |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | Alibaba Cloud AccessKey Secret |

### Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

---

## 中文

基于阿里云函数计算（FC）的 SSL 证书自动续期工具。通过 ACME 协议（Let's Encrypt）获取免费证书，上传到阿里云证书服务（CAS），并自动部署到 OSS 自定义域名。

### 功能

- 自动获取/续期 Let's Encrypt SSL 证书
- DNS-01 验证（通过阿里云 DNS API）
- 支持通配符证书和 SAN 多域名证书
- 证书上传到阿里云证书服务（CAS）统一管理
- 自动部署到 OSS 自定义域名（扫描所有 bucket，匹配域名后自动替换证书）
- 可扩展的部署目标配置（`DEPLOY_TO`），未来可支持 CDN、SLB 等
- 完全无状态，适合 Serverless 环境

### 配置

环境变量：

| 变量 | 必填 | 说明 | 默认值 |
|------|------|------|--------|
| `CERT_CONFIGS` | 是 | JSON 域名分组配置 | - |
| `ACME_EMAIL` | 否 | ACME 注册邮箱（用于证书过期提醒） | 空 |
| `ACME_STAGING` | 否 | 使用 LE staging 环境 | `false` |
| `RENEW_DAYS` | 否 | 到期前多少天续期 | `30` |
| `DEPLOY_TO` | 否 | 自动部署目标服务，逗号分隔（目前支持: `oss`） | 空（仅上传 CAS） |

> **注意**：在 FC 控制台配置 `CERT_CONFIGS` 时，直接填写 JSON 内容，**不要**在两端加引号。示例：
>
> `[{"name": "example.com", "domains": ["example.com", "*.example.com"]}]`

#### CERT_CONFIGS 格式

```json
[
  {
    "name": "example.com",
    "domains": ["example.com", "*.example.com"]
  }
]
```

- `name`: 证书名称（CAS 中的标识）
- `domains`: 域名列表，第一个作为 CN

### 部署

#### 1. 获取部署包

**方式 A**：从 [GitHub Releases](https://github.com/imth/aliyun-fc-acme/releases/latest) 直接下载 `deploy.zip`。

**方式 B**：本地构建（需要 Docker）：

```bash
python build.py
```

#### 2. 上传到 FC

在阿里云控制台创建函数，选择「代码包上传」，上传 `deploy.zip`。

- 运行时：Python 3.10+
- 入口函数：index.handler
- 超时：600 秒
- 内存：512 MB

#### 3. 定时触发器

Cron 表达式：`0 0 3 * * *`（每天凌晨 3 点）

#### 4. 凭证配置

支持两种认证方式，任选其一：

**方式一：FC 服务角色（推荐）**

创建自定义权限策略：进入 [RAM 控制台](https://ram.console.aliyun.com/) → **权限策略** → **创建权限策略** → 选择「脚本编辑」，粘贴：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "alidns:*",
        "yundun-cert:*",
        "oss:*"
      ],
      "Resource": "*"
    }
  ]
}
```

保存为 `fc-acme-cert-policy`，然后进入 **角色** → 找到 FC 服务角色 → **添加权限** → 选择 `fc-acme-cert-policy`。

> **注意**：不要粘贴到角色的「信任策略」中，信任策略用于定义谁可以扮演角色，而非角色拥有的权限。

**方式二：AccessKey 环境变量**

| 变量 | 说明 |
|------|------|
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | 阿里云 AccessKey ID |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | 阿里云 AccessKey Secret |

### 开发

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```
