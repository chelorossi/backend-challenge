#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { SharedStack } from "../lib/shared-stack";
import { ApiStack } from "../lib/api-stack";
import { ProcessingStack } from "../lib/processing-stack";

const app = new cdk.App();

// Get environment from context or use default
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT || app.node.tryGetContext("account"),
  region:
    process.env.CDK_DEFAULT_REGION ||
    app.node.tryGetContext("region") ||
    "us-east-1",
};

// Get environment name from context or use default
const envName = app.node.tryGetContext("environment") || "dev";

// Shared resources stack (SQS, DLQ, etc.)
const sharedStack = new SharedStack(app, `TaskManagementShared-${envName}`, {
  env,
  envName,
});

// API stack (depends on shared stack)
const apiStack = new ApiStack(app, `TaskManagementApi-${envName}`, {
  env,
  envName,
  queue: sharedStack.queue,
  deadLetterQueue: sharedStack.deadLetterQueue,
});

// Processing stack (depends on shared stack)
const processingStack = new ProcessingStack(
  app,
  `TaskManagementProcessing-${envName}`,
  {
    env,
    envName,
    queue: sharedStack.queue,
    deadLetterQueue: sharedStack.deadLetterQueue,
  }
);

// Add dependencies
apiStack.addDependency(sharedStack);
processingStack.addDependency(sharedStack);
