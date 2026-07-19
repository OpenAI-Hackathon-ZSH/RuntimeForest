import * as path from 'path';
import {
  CfnOutput,
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
  aws_ec2 as ec2,
  aws_iam as iam,
  aws_s3_assets as assets,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class RuntimeForestStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const projectRoot = path.resolve(__dirname, '../..');
    const application = new assets.Asset(this, 'BackendSource', {
      path: projectRoot,
      exclude: [
        '.git/**',
        '.cdk/node_modules/**',
        '.cdk/cdk.out/**',
        '.cdk/dist/**',
        '.env*',
        '**/__pycache__/**',
        '**/*.pyc',
      ],
    });

    const vpc = new ec2.Vpc(this, 'Vpc', {
      maxAzs: 1,
      natGateways: 0,
      subnetConfiguration: [{
        name: 'public',
        subnetType: ec2.SubnetType.PUBLIC,
        cidrMask: 24,
      }],
    });

    const securityGroup = new ec2.SecurityGroup(this, 'BackendSecurityGroup', {
      vpc,
      description: 'Public access to the RuntimeForest API',
      allowAllOutbound: true,
    });
    securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(8000), 'Public API');

    const role = new iam.Role(this, 'InstanceRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
      ],
    });
    application.grantRead(role);

    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      'set -euxo pipefail',
      'dnf install -y python3-pip git unzip awscli',
      'mkdir -p /opt/runtimeforest',
      `aws s3 cp s3://${application.s3BucketName}/${application.s3ObjectKey} /tmp/runtimeforest.zip`,
      'unzip -o /tmp/runtimeforest.zip -d /opt/runtimeforest',
      'python3 -m venv /opt/runtimeforest/.venv',
      '/opt/runtimeforest/.venv/bin/pip install --upgrade pip',
      '/opt/runtimeforest/.venv/bin/pip install -r /opt/runtimeforest/requirements.txt',
      "cat > /etc/systemd/system/runtimeforest.service <<'EOF'\n[Unit]\nDescription=RuntimeForest Backend API\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nType=simple\nUser=ec2-user\nWorkingDirectory=/opt/runtimeforest\nExecStart=/opt/runtimeforest/.venv/bin/python services/backend/server.py\nRestart=always\nRestartSec=5\nEnvironment=PYTHONUNBUFFERED=1\n\n[Install]\nWantedBy=multi-user.target\nEOF",
      'chown -R ec2-user:ec2-user /opt/runtimeforest',
      'systemctl daemon-reload',
      'systemctl enable --now runtimeforest',
    );

    const instance = new ec2.Instance(this, 'BackendInstance', {
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
      instanceType: new ec2.InstanceType('t3.micro'),
      machineImage: ec2.MachineImage.latestAmazonLinux2023(),
      securityGroup,
      role,
      userData,
      // The asset key changes whenever application files change. Replacing the
      // instance guarantees cloud-init installs and starts the new revision.
      userDataCausesReplacement: true,
      requireImdsv2: true,
      keyPair: process.env.EC2_KEY_PAIR_NAME
        ? ec2.KeyPair.fromKeyPairName(this, 'ExistingKeyPair', process.env.EC2_KEY_PAIR_NAME)
        : undefined,
    });

    const elasticIp = new ec2.CfnEIP(this, 'BackendElasticIp', { domain: 'vpc' });
    elasticIp.applyRemovalPolicy(RemovalPolicy.DESTROY);
    new ec2.CfnEIPAssociation(this, 'BackendElasticIpAssociation', {
      allocationId: elasticIp.attrAllocationId,
      instanceId: instance.instanceId,
    });

    new CfnOutput(this, 'ApiUrl', {
      value: `http://${elasticIp.ref}:8000`,
      description: 'Public RuntimeForest API URL',
    });
    new CfnOutput(this, 'HealthUrl', {
      value: `http://${elasticIp.ref}:8000/health`,
    });
    new CfnOutput(this, 'InstanceId', { value: instance.instanceId });
  }
}
