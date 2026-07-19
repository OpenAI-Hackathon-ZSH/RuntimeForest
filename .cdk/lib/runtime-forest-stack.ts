import * as path from 'path';
import {
  CfnOutput,
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
    const backendSource = new assets.Asset(this, 'BackendSource', {
      path: path.join(projectRoot, 'services/backend'),
      exclude: [
        '**/__pycache__/**',
        '**/*.pyc',
        '.graph_cache.json',
      ],
    });
    const mockSource = new assets.Asset(this, 'MockSource', {
      path: path.join(projectRoot, 'services/mock'),
      exclude: ['**/__pycache__/**', '**/*.pyc'],
    });
    const runtimeSpySource = new assets.Asset(this, 'RuntimeSpySource', {
      path: path.join(projectRoot, 'vendor/RuntimeSpy'),
      exclude: ['.git/**', '**/__pycache__/**', '**/*.pyc'],
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

    const mockSecurityGroup = new ec2.SecurityGroup(this, 'MockSecurityGroup', {
      vpc,
      description: 'Public access to the RuntimeForest mock service',
      allowAllOutbound: true,
    });
    mockSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(8100), 'Public mock API');

    const role = new iam.Role(this, 'InstanceRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
      ],
    });
    backendSource.grantRead(role);
    mockSource.grantRead(role);
    runtimeSpySource.grantRead(role);

    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      'set -euxo pipefail',
      'dnf install -y python3-pip git unzip awscli',
      'mkdir -p /opt/runtimeforest',
      `aws s3 cp s3://${backendSource.s3BucketName}/${backendSource.s3ObjectKey} /tmp/backend.zip`,
      'unzip -o /tmp/backend.zip -d /opt/runtimeforest',
      'python3 -m venv /opt/runtimeforest/.venv',
      '/opt/runtimeforest/.venv/bin/pip install --upgrade pip',
      '/opt/runtimeforest/.venv/bin/pip install -r /opt/runtimeforest/requirements.txt',
      "cat > /etc/systemd/system/runtimeforest.service <<'EOF'\n[Unit]\nDescription=RuntimeForest Backend API\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nType=simple\nUser=ec2-user\nWorkingDirectory=/opt/runtimeforest\nExecStart=/opt/runtimeforest/.venv/bin/python server.py\nRestart=always\nRestartSec=5\nEnvironment=PYTHONUNBUFFERED=1\n\n[Install]\nWantedBy=multi-user.target\nEOF",
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
    const backendIpAssociation = new ec2.CfnEIPAssociation(this, 'BackendElasticIpAssociation', {
      allocationId: elasticIp.attrAllocationId,
      instanceId: instance.instanceId,
    });

    const mockUserData = ec2.UserData.forLinux();
    mockUserData.addCommands(
      'set -euxo pipefail',
      'dnf install -y python3-pip unzip awscli',
      'mkdir -p /opt/runtimeforest/services/mock /opt/runtimeforest/vendor/RuntimeSpy',
      `aws s3 cp s3://${mockSource.s3BucketName}/${mockSource.s3ObjectKey} /tmp/mock.zip`,
      `aws s3 cp s3://${runtimeSpySource.s3BucketName}/${runtimeSpySource.s3ObjectKey} /tmp/runtime-spy.zip`,
      'unzip -o /tmp/mock.zip -d /opt/runtimeforest/services/mock',
      'unzip -o /tmp/runtime-spy.zip -d /opt/runtimeforest/vendor/RuntimeSpy',
      'test -f /opt/runtimeforest/vendor/RuntimeSpy/pyproject.toml -o -f /opt/runtimeforest/vendor/RuntimeSpy/setup.py',
      'python3 -m venv /opt/runtimeforest/.venv',
      '/opt/runtimeforest/.venv/bin/pip install --upgrade pip',
      '/opt/runtimeforest/.venv/bin/pip install -r /opt/runtimeforest/services/mock/requirements.txt',
      '/opt/runtimeforest/.venv/bin/pip install /opt/runtimeforest/vendor/RuntimeSpy',
      `cat > /etc/systemd/system/runtimeforest-mock.service <<'EOF'
[Unit]
Description=RuntimeForest Instrumented Mock Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/runtimeforest
Environment=PYTHONUNBUFFERED=1
Environment=CODE_MANAGER_INSTRUMENT=1
Environment=CODE_MANAGER_BACKEND_URL=http://${elasticIp.ref}:8000
ExecStartPre=/bin/bash -c 'for attempt in {1..60}; do curl -fsS http://${elasticIp.ref}:8000/health && exit 0; sleep 5; done; exit 1'
ExecStart=/opt/runtimeforest/.venv/bin/uvicorn services.mock.server:app --host 0.0.0.0 --port 8100
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF`,
      'chown -R ec2-user:ec2-user /opt/runtimeforest',
      'systemctl daemon-reload',
      'systemctl enable --now runtimeforest-mock',
    );

    const mockInstance = new ec2.Instance(this, 'MockInstance', {
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
      instanceType: new ec2.InstanceType('t3.micro'),
      machineImage: ec2.MachineImage.latestAmazonLinux2023(),
      securityGroup: mockSecurityGroup,
      role,
      userData: mockUserData,
      userDataCausesReplacement: true,
      requireImdsv2: true,
      keyPair: process.env.EC2_KEY_PAIR_NAME
        ? ec2.KeyPair.fromKeyPairName(this, 'MockExistingKeyPair', process.env.EC2_KEY_PAIR_NAME)
        : undefined,
    });
    mockInstance.node.addDependency(backendIpAssociation);

    const mockElasticIp = new ec2.CfnEIP(this, 'MockElasticIp', { domain: 'vpc' });
    mockElasticIp.applyRemovalPolicy(RemovalPolicy.DESTROY);
    new ec2.CfnEIPAssociation(this, 'MockElasticIpAssociation', {
      allocationId: mockElasticIp.attrAllocationId,
      instanceId: mockInstance.instanceId,
    });

    new CfnOutput(this, 'ApiUrl', {
      value: `http://${elasticIp.ref}:8000`,
      description: 'Public RuntimeForest API URL',
    });
    new CfnOutput(this, 'HealthUrl', {
      value: `http://${elasticIp.ref}:8000/health`,
    });
    new CfnOutput(this, 'InstanceId', { value: instance.instanceId });
    new CfnOutput(this, 'MockApiUrl', {
      value: `http://${mockElasticIp.ref}:8100`,
      description: 'Public instrumented mock service URL',
    });
    new CfnOutput(this, 'MockHealthUrl', {
      value: `http://${mockElasticIp.ref}:8100/health`,
    });
    new CfnOutput(this, 'MockInstanceId', { value: mockInstance.instanceId });
  }
}
