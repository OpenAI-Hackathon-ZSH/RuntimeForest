#!/usr/bin/env node
import 'source-map-support/register';
import * as path from 'path';
import { config } from 'dotenv';

// CDK's AWS SDK reads these standard variables through its default credential chain.
config({ path: path.resolve(__dirname, '../../.env'), quiet: true });

import { App } from 'aws-cdk-lib';
import { RuntimeForestStack } from '../lib/runtime-forest-stack';

const app = new App();

new RuntimeForestStack(app, 'RuntimeForestStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.AWS_REGION ?? process.env.AWS_DEFAULT_REGION ?? 'us-west-2',
  },
});
