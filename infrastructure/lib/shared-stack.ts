import * as cdk from "aws-cdk-lib";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";

export interface SharedStackProps extends cdk.StackProps {
  envName: string;
}

export class SharedStack extends cdk.Stack {
  public readonly queue: sqs.Queue;
  public readonly deadLetterQueue: sqs.Queue;

  constructor(scope: Construct, id: string, props: SharedStackProps) {
    super(scope, id, props);

    // Dead Letter Queue for failed messages
    this.deadLetterQueue = new sqs.Queue(this, "TaskDeadLetterQueue", {
      queueName: `task-management-dlq-${props.envName}`,
      retentionPeriod: cdk.Duration.days(14),
      encryption: sqs.QueueEncryption.SQS_MANAGED,
    });

    // Main SQS FIFO Queue for ordered task processing
    this.queue = new sqs.Queue(this, "TaskQueue", {
      queueName: `task-management-queue-${props.envName}.fifo`,
      fifo: true,
      contentBasedDeduplication: true,
      deadLetterQueue: {
        queue: this.deadLetterQueue,
        maxReceiveCount: 3, // Retry 3 times before sending to DLQ
      },
      visibilityTimeout: cdk.Duration.seconds(30),
      retentionPeriod: cdk.Duration.days(14),
      encryption: sqs.QueueEncryption.SQS_MANAGED,
    });

    // CloudWatch Log Groups (created automatically by Lambda, but we can pre-create them)
    new logs.LogGroup(this, "ApiLogGroup", {
      logGroupName: `/aws/lambda/task-management-api-${props.envName}`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    new logs.LogGroup(this, "ProcessorLogGroup", {
      logGroupName: `/aws/lambda/task-management-processor-${props.envName}`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Outputs
    new cdk.CfnOutput(this, "QueueUrl", {
      value: this.queue.queueUrl,
      description: "SQS FIFO Queue URL for task processing",
    });

    new cdk.CfnOutput(this, "DeadLetterQueueUrl", {
      value: this.deadLetterQueue.queueUrl,
      description: "Dead Letter Queue URL for failed tasks",
    });
  }
}
