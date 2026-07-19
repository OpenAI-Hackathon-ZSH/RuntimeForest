# RuntimeForest AWS CDK

This stack deploys `services/backend` and the instrumented `services/mock` service
to separate Amazon Linux EC2 instances. Both have stable Elastic IPs: the backend
is public on port `8000`, and the mock API is public on port `8100`.

## Credentials

Create `../.env` (the repository root `.env`) with standard AWS environment names:

```dotenv
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=... # optional
AWS_REGION=us-west-2
EC2_KEY_PAIR_NAME=... # optional; Session Manager works without an SSH key
```

Never commit this file. The credentials are used locally by CDK and are not copied
to the instance or included in the CloudFormation template.

## Deploy

```bash
cd .cdk
npm install
npx cdk bootstrap
npm run deploy
```

After deployment, CDK prints `ApiUrl` and `HealthUrl`. Initial instance setup can
take a few minutes. To inspect it without SSH, use AWS Systems Manager Session
Manager or check `/var/log/cloud-init-output.log` on the instance.

## Automatic deployment from GitHub

`.github/workflows/deploy.yml` runs on every push/merge commit to `main`. Add these
settings to the repository's `production` GitHub Environment (or repository-level
Actions settings):

- Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Optional secret: `AWS_SESSION_TOKEN` (only for temporary credentials)
- Variable: `AWS_REGION` (defaults to `us-west-2`)
- Optional variable: `EC2_KEY_PAIR_NAME`

The workflow bootstraps the target CDK environment automatically before deploy.

Backend, Mock, and RuntimeSpy are packaged as separate CDK assets. Backend source
changes replace only the Backend EC2. Mock or RuntimeSpy changes replace only the
Mock EC2. CloudFormation updates both only when both sides actually change.

The workflow downloads the public RuntimeSpy `main.zip` before CDK packages the
application. The mock EC2 installs this bundled local copy and does not need to
access GitHub during startup.

## Remove

```bash
cd .cdk
npm run destroy
```
