# RuntimeForest AWS CDK

This stack deploys `services/backend` to an Amazon Linux EC2 instance with a stable
Elastic IP and public access on port `8000`.

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

Only the Backend source is packaged as a CDK asset. Backend source changes replace
the Backend EC2 so the new revision is installed reliably.

## Remove

```bash
cd .cdk
npm run destroy
```
