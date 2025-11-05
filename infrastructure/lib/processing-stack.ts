import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as logs from "aws-cdk-lib/aws-logs";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import { Construct } from "constructs";
import * as path from "path";

export interface ProcessingStackProps extends cdk.StackProps {
  envName: string;
  queue: sqs.Queue;
  deadLetterQueue: sqs.Queue;
}

export class ProcessingStack extends cdk.Stack {
  public readonly processor: lambda.Function;

  constructor(scope: Construct, id: string, props: ProcessingStackProps) {
    super(scope, id, props);

    // Lambda function for queue processing
    this.processor = new lambda.Function(this, "Processor", {
      functionName: `task-management-processor-${props.envName}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "handler.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "../../src/processor")),
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: {
        QUEUE_URL: props.queue.queueUrl,
        DLQ_URL: props.deadLetterQueue.queueUrl,
        ENVIRONMENT: props.envName,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // Grant least privilege: receive, delete messages, and get queue attributes
    props.queue.grantConsumeMessages(this.processor);

    // SQS Event Source Mapping
    // Note: FIFO queues don't support maxBatchingWindow
    this.processor.addEventSource(
      new lambdaEventSources.SqsEventSource(props.queue, {
        batchSize: 1, // Process one message at a time to maintain ordering
        reportBatchItemFailures: true, // Enable batch item failure reporting
      })
    );

    // CloudWatch Alarm for DLQ messages
    new cloudwatch.Alarm(this, "DLQAlarm", {
      alarmName: `task-management-dlq-alarm-${props.envName}`,
      alarmDescription: "Alert when messages are sent to the dead letter queue",
      metric: props.deadLetterQueue.metricApproximateNumberOfMessagesVisible(),
      threshold: 1,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    // Outputs
    new cdk.CfnOutput(this, "ProcessorFunctionName", {
      value: this.processor.functionName,
      description: "Lambda function name for task processing",
    });
  }
}
