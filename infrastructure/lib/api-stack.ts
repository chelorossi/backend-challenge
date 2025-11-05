import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";
import * as path from "path";

export interface ApiStackProps extends cdk.StackProps {
  envName: string;
  queue: sqs.Queue;
  deadLetterQueue: sqs.Queue;
}

export class ApiStack extends cdk.Stack {
  public readonly api: apigateway.RestApi;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    // Lambda function for API handler
    const apiHandler = new lambda.Function(this, "ApiHandler", {
      functionName: `task-management-api-${props.envName}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "handler.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "../../src/api")),
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: {
        QUEUE_URL: props.queue.queueUrl,
        ENVIRONMENT: props.envName,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // Grant least privilege: only send messages to the queue
    props.queue.grantSendMessages(apiHandler);

    // API Gateway REST API
    this.api = new apigateway.RestApi(this, "TaskManagementApi", {
      restApiName: `task-management-api-${props.envName}`,
      description: "Task Management API for creating and processing tasks",
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: ["POST", "OPTIONS"],
        allowHeaders: [
          "Content-Type",
          "X-Amz-Date",
          "Authorization",
          "X-Api-Key",
        ],
      },
      deployOptions: {
        stageName: props.envName,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
      },
    });

    // POST /tasks endpoint
    const tasksResource = this.api.root.addResource("tasks");
    tasksResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(apiHandler, {
        requestTemplates: { "application/json": '{ "statusCode": "200" }' },
      }),
      {
        methodResponses: [
          {
            statusCode: "200",
            responseParameters: {
              "method.response.header.Access-Control-Allow-Origin": true,
            },
          },
          {
            statusCode: "400",
            responseParameters: {
              "method.response.header.Access-Control-Allow-Origin": true,
            },
          },
          {
            statusCode: "500",
            responseParameters: {
              "method.response.header.Access-Control-Allow-Origin": true,
            },
          },
        ],
      }
    );

    // Outputs
    new cdk.CfnOutput(this, "ApiUrl", {
      value: this.api.url,
      description: "API Gateway endpoint URL",
    });

    new cdk.CfnOutput(this, "ApiEndpoint", {
      value: `${this.api.url}tasks`,
      description: "POST /tasks endpoint URL",
    });
  }
}
