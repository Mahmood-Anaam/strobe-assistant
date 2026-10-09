"""Idempotent AWS deployment for the Track A Strobe Assistant.

The CAB432 account provides shared execution/task roles. This deployer creates only
student-scoped resources, tags every taggable resource, and reuses the Assessment 1
media bucket, tables, user pool, API, certificate, and domain.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import secrets
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

import boto3
import yaml
from botocore.exceptions import ClientError

REGION = "ap-southeast-2"
ACCOUNT_ID = "901444280953"
STUDENT_ID = "n11553758"
QUT_USERNAME = f"{STUDENT_ID}@qut.edu.au"
PURPOSE = "assessment 2"
PREFIX = f"{STUDENT_ID}-strobe"
ROOT = Path(__file__).resolve().parents[1]
ROLE_ARNS = {
    "lambda": f"arn:aws:iam::{ACCOUNT_ID}:role/CAB432-Lambda-Role",
    "ecs_execution": f"arn:aws:iam::{ACCOUNT_ID}:role/Execution-Role-CAB432-ECS",
    "ecs_task": f"arn:aws:iam::{ACCOUNT_ID}:role/Task-Role-CAB432-ECS",
    "events": f"arn:aws:iam::{ACCOUNT_ID}:role/CAB432-EventBridge-Rules-Role",
}
TAGS = {"qut-username": QUT_USERNAME, "purpose": PURPOSE, "project": "strobe-assistant"}


class AwsDeployment:
    """Creates and updates the assessment infrastructure in dependency order."""

    def __init__(self, *, build_images: bool = True) -> None:
        self.session = boto3.Session(region_name=REGION)
        self.build_images = build_images
        self.ddb = self.session.client("dynamodb")
        self.s3 = self.session.client("s3")
        self.s3control = self.session.client("s3control")
        self.s3vectors = self.session.client("s3vectors")
        self.sqs = self.session.client("sqs")
        self.lambda_client = self.session.client("lambda")
        self.events = self.session.client("events")
        self.secrets = self.session.client("secretsmanager")
        self.ecr = self.session.client("ecr")
        self.ecs = self.session.client("ecs")
        self.ec2 = self.session.client("ec2")
        self.elb = self.session.client("elbv2")
        self.logs = self.session.client("logs")
        self.discovery = self.session.client("servicediscovery")
        self.cognito = self.session.client("cognito-idp")
        self.resources: list[dict[str, str]] = []

    def deploy(self) -> None:
        self._retag_assessment_one()
        table_arns = {
            "classification": self._ensure_table(f"{PREFIX}-classifications"),
            "agent-run": self._ensure_table(f"{PREFIX}-agent-runs"),
            "idempotency": self._ensure_table(f"{PREFIX}-idempotency", ttl_attribute="expiration"),
        }
        secret_arn, _api_key = self._ensure_secret()
        vector_arn, index_arn = self._ensure_vectors()
        queue_url, queue_arn, dlq_arn = self._ensure_queues()
        lambda_arns = self._ensure_lambdas(queue_url)
        upload_rule_arn, heartbeat_rule_arn = self._ensure_events(queue_arn, dlq_arn, lambda_arns)
        image_uris = self._ensure_images()
        endpoint, ecs_resources = self._ensure_ecs(image_uris, secret_arn)

        self._record(
            "Bedrock model",
            "amazon.titan-embed-text-v2:0",
            "Creates 1024-dimensional semantic-search embeddings.",
        )
        self._record(
            "Bedrock model",
            "apac.amazon.nova-lite-v1:0",
            "Generates grounded chat, photo descriptions, and retrospectives when "
            "account policy permits.",
        )
        self._record(
            "Vector bucket",
            vector_arn,
            "Stores Strobe photo-description embeddings for semantic retrieval.",
        )
        self._record(
            "Vector index",
            index_arn,
            "Runs cosine nearest-neighbour search with per-user metadata filtering.",
        )
        self._record(
            "SQS queue",
            queue_arn,
            "Buffers S3 photo-created events for asynchronous classification.",
        )
        self._record(
            "SQS dead-letter queue",
            dlq_arn,
            "Retains repeatedly failed classification messages for investigation.",
        )
        self._record(
            "EventBridge rule",
            upload_rule_arn,
            "Routes new Strobe media objects to the classification queue.",
        )
        self._record(
            "EventBridge rule",
            heartbeat_rule_arn,
            "Runs the autonomous daily retrospective heartbeat.",
        )
        self._record(
            "Secrets Manager secret",
            secret_arn,
            "Stores the private MCP service authentication key.",
        )
        for name, arn in table_arns.items():
            self._record("DynamoDB table", arn, f"Persists Strobe Assistant {name} records.")
        for name, arn in lambda_arns.items():
            self._record(
                "Lambda function",
                arn,
                f"Runs the {name} workflow with structured CloudWatch logging.",
            )
        self.resources.extend(ecs_resources)
        self._write_manifest(endpoint)
        print(json.dumps({"endpoint": endpoint, "resources": len(self.resources)}, indent=2))

    def _record(self, resource_type: str, arn: str, description: str) -> None:
        self.resources.append({"type": resource_type, "arn": arn, "description": description})

    def _tag_list(self) -> list[dict[str, str]]:
        return [{"Key": key, "Value": value} for key, value in TAGS.items()]

    def _ecs_tag_list(self) -> list[dict[str, str]]:
        return [{"key": key, "value": value} for key, value in TAGS.items()]

    def _retag_assessment_one(self) -> None:
        for bucket in [f"{PREFIX}-media"]:
            self.s3control.tag_resource(
                AccountId=ACCOUNT_ID,
                ResourceArn=f"arn:aws:s3:::{bucket}",
                Tags=self._tag_list(),
            )
            self.s3.put_bucket_notification_configuration(
                Bucket=bucket,
                NotificationConfiguration={"EventBridgeConfiguration": {}},
            )
            self._record(
                "S3 bucket",
                f"arn:aws:s3:::{bucket}",
                "Private media store reused from Strobe Assessment 1.",
            )
        for suffix in ["users", "posts", "comments", "likes", "follows", "moments"]:
            name = f"{PREFIX}-{suffix}"
            response = self.ddb.describe_table(TableName=name)["Table"]
            self.ddb.tag_resource(ResourceArn=response["TableArn"], Tags=self._tag_list())
            self._record(
                "DynamoDB table",
                response["TableArn"],
                f"Assessment 1 Strobe {suffix} data reused by the assistant.",
            )

    def _ensure_table(self, name: str, ttl_attribute: str | None = None) -> str:
        try:
            table = self.ddb.describe_table(TableName=name)["Table"]
        except self.ddb.exceptions.ResourceNotFoundException:
            table = self.ddb.create_table(
                TableName=name,
                AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
                KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
                BillingMode="PAY_PER_REQUEST",
                Tags=self._tag_list(),
                SSESpecification={"Enabled": True},
            )["TableDescription"]
            self.ddb.get_waiter("table_exists").wait(TableName=name)
            table = self.ddb.describe_table(TableName=name)["Table"]
        self.ddb.tag_resource(ResourceArn=table["TableArn"], Tags=self._tag_list())
        if ttl_attribute:
            try:
                self.ddb.update_time_to_live(
                    TableName=name,
                    TimeToLiveSpecification={"Enabled": True, "AttributeName": ttl_attribute},
                )
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "ValidationException":
                    raise
        return table["TableArn"]

    def _ensure_secret(self) -> tuple[str, str]:
        name = f"{PREFIX}/mcp-api-key"
        try:
            metadata = self.secrets.describe_secret(SecretId=name)
            value = json.loads(self.secrets.get_secret_value(SecretId=name)["SecretString"])
            self.secrets.tag_resource(SecretId=name, Tags=self._tag_list())
            return metadata["ARN"], value["apiKey"]
        except self.secrets.exceptions.ResourceNotFoundException:
            api_key = secrets.token_urlsafe(32)
            response = self.secrets.create_secret(
                Name=name,
                Description="Authentication key used only between Strobe ACP agent and MCP service",
                SecretString=json.dumps({"apiKey": api_key}),
                Tags=self._tag_list(),
            )
            return response["ARN"], api_key

    def _ensure_vectors(self) -> tuple[str, str]:
        bucket = f"{PREFIX}-vectors"
        index = "photo-search"
        try:
            bucket_data = self.s3vectors.get_vector_bucket(vectorBucketName=bucket)
        except self.s3vectors.exceptions.NotFoundException:
            self.s3vectors.create_vector_bucket(
                vectorBucketName=bucket,
                encryptionConfiguration={"sseType": "AES256"},
                tags=TAGS,
            )
            bucket_data = self.s3vectors.get_vector_bucket(vectorBucketName=bucket)
        bucket_arn = bucket_data["vectorBucket"]["vectorBucketArn"]
        self.s3vectors.tag_resource(resourceArn=bucket_arn, tags=TAGS)
        try:
            index_data = self.s3vectors.get_index(vectorBucketName=bucket, indexName=index)
        except self.s3vectors.exceptions.NotFoundException:
            self.s3vectors.create_index(
                vectorBucketName=bucket,
                indexName=index,
                dataType="float32",
                dimension=1024,
                distanceMetric="cosine",
                metadataConfiguration={
                    "nonFilterableMetadataKeys": ["description", "labels", "objectKey"]
                },
                tags=TAGS,
            )
            index_data = self.s3vectors.get_index(vectorBucketName=bucket, indexName=index)
        index_arn = index_data["index"]["indexArn"]
        self.s3vectors.tag_resource(resourceArn=index_arn, tags=TAGS)
        return bucket_arn, index_arn

    def _ensure_queues(self) -> tuple[str, str, str]:
        dlq_url = self.sqs.create_queue(
            QueueName=f"{PREFIX}-classification-dlq",
            Attributes={"SqsManagedSseEnabled": "true", "MessageRetentionPeriod": "1209600"},
            tags=TAGS,
        )["QueueUrl"]
        dlq_arn = self.sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])[
            "Attributes"
        ]["QueueArn"]
        queue_url = self.sqs.create_queue(
            QueueName=f"{PREFIX}-classification",
            Attributes={
                "SqsManagedSseEnabled": "true",
                "VisibilityTimeout": "180",
                "RedrivePolicy": json.dumps({"deadLetterTargetArn": dlq_arn, "maxReceiveCount": 3}),
            },
            tags=TAGS,
        )["QueueUrl"]
        queue_arn = self.sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])[
            "Attributes"
        ]["QueueArn"]
        return queue_url, queue_arn, dlq_arn

    def _lambda_zip(self) -> bytes:
        buffer = io.BytesIO()
        package = ROOT / "src" / "strobe_assistant"
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in package.rglob("*.py"):
                if path.name in {"mcp_app.py", "__main__.py"}:
                    continue
                archive.write(path, Path("strobe_assistant") / path.relative_to(package))
        return buffer.getvalue()

    def _ensure_lambdas(self, queue_url: str) -> dict[str, str]:
        code = self._lambda_zip()
        common = {
            "AWS_REGION_NAME": REGION,
            "MEDIA_BUCKET": f"{PREFIX}-media",
            "POSTS_TABLE": f"{PREFIX}-posts",
            "USERS_TABLE": f"{PREFIX}-users",
            "CLASSIFICATIONS_TABLE": f"{PREFIX}-classifications",
            "AGENT_RUNS_TABLE": f"{PREFIX}-agent-runs",
            "IDEMPOTENCY_TABLE": f"{PREFIX}-idempotency",
            "VECTOR_BUCKET_NAME": f"{PREFIX}-vectors",
            "VECTOR_INDEX_NAME": "photo-search",
            "VECTOR_DIMENSION": "1024",
            "EMBEDDING_MODEL_ID": "amazon.titan-embed-text-v2:0",
            "CHAT_MODEL_ID": "apac.amazon.nova-lite-v1:0",
            "CLASSIFICATION_QUEUE_URL": queue_url,
        }
        definitions = {
            "classifier": ("strobe_assistant.handlers.classification_handler", 120, 512),
            "heartbeat": ("strobe_assistant.handlers.heartbeat_handler", 120, 512),
        }
        arns = {}
        for suffix, (handler, timeout, memory) in definitions.items():
            name = f"{PREFIX}-{suffix}"
            try:
                self.lambda_client.get_function(FunctionName=name)
                self.lambda_client.update_function_code(
                    FunctionName=name, ZipFile=code, Publish=False
                )
                self.lambda_client.get_waiter("function_updated").wait(FunctionName=name)
                response = self.lambda_client.update_function_configuration(
                    FunctionName=name,
                    Handler=handler,
                    Runtime="python3.14",
                    Role=ROLE_ARNS["lambda"],
                    Timeout=timeout,
                    MemorySize=memory,
                    Environment={"Variables": common},
                    TracingConfig={"Mode": "Active"},
                )
            except ClientError as exc:
                if exc.response["Error"]["Code"] not in {
                    "ResourceNotFoundException",
                    "AccessDeniedException",
                }:
                    raise
                response = self.lambda_client.create_function(
                    FunctionName=name,
                    Runtime="python3.14",
                    Role=ROLE_ARNS["lambda"],
                    Handler=handler,
                    Code={"ZipFile": code},
                    Timeout=timeout,
                    MemorySize=memory,
                    Environment={"Variables": common},
                    TracingConfig={"Mode": "Active"},
                    Tags=TAGS,
                    Architectures=["x86_64"],
                )
            arns[suffix] = response["FunctionArn"]
            self.lambda_client.tag_resource(Resource=response["FunctionArn"], Tags=TAGS)
            self._ensure_log_group(f"/aws/lambda/{name}")
        mappings = self.lambda_client.list_event_source_mappings(
            EventSourceArn=self._queue_arn(queue_url), FunctionName=arns["classifier"]
        ).get("EventSourceMappings", [])
        if not mappings:
            self.lambda_client.create_event_source_mapping(
                EventSourceArn=self._queue_arn(queue_url),
                FunctionName=arns["classifier"],
                BatchSize=5,
                FunctionResponseTypes=["ReportBatchItemFailures"],
                Enabled=True,
            )
        return arns

    def _queue_arn(self, queue_url: str) -> str:
        return self.sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])[
            "Attributes"
        ]["QueueArn"]

    def _ensure_events(
        self, queue_arn: str, dlq_arn: str, lambda_arns: dict[str, str]
    ) -> tuple[str, str]:
        upload_name = f"{PREFIX}-photo-uploaded"
        upload_rule = self.events.put_rule(
            Name=upload_name,
            EventPattern=json.dumps(
                {
                    "source": ["aws.s3"],
                    "detail-type": ["Object Created"],
                    "detail": {"bucket": {"name": [f"{PREFIX}-media"]}},
                }
            ),
            State="ENABLED",
            Description="Route new Strobe media objects to asynchronous classification",
            Tags=self._tag_list(),
        )["RuleArn"]
        self.events.put_targets(
            Rule=upload_name,
            Targets=[
                {
                    "Id": "classification-queue",
                    "Arn": queue_arn,
                    "DeadLetterConfig": {"Arn": dlq_arn},
                }
            ],
        )
        queue_url = self.sqs.get_queue_url(QueueName=queue_arn.rsplit(":", 1)[-1])["QueueUrl"]
        self.sqs.set_queue_attributes(
            QueueUrl=queue_url,
            Attributes={
                "Policy": json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "events.amazonaws.com"},
                                "Action": "sqs:SendMessage",
                                "Resource": queue_arn,
                                "Condition": {"ArnEquals": {"aws:SourceArn": upload_rule}},
                            }
                        ],
                    }
                )
            },
        )
        heartbeat_name = f"{PREFIX}-daily-heartbeat"
        heartbeat_rule = self.events.put_rule(
            Name=heartbeat_name,
            ScheduleExpression="cron(0 20 * * ? *)",
            State="ENABLED",
            Description=(
                "Generate a daily autonomous Strobe retrospective at 06:00 Australia/Brisbane"
            ),
            Tags=self._tag_list(),
        )["RuleArn"]
        self.events.put_targets(
            Rule=heartbeat_name,
            Targets=[{"Id": "heartbeat-lambda", "Arn": lambda_arns["heartbeat"]}],
        )
        with contextlib.suppress(self.lambda_client.exceptions.ResourceConflictException):
            self.lambda_client.add_permission(
                FunctionName=lambda_arns["heartbeat"],
                StatementId="AllowDailyHeartbeat",
                Action="lambda:InvokeFunction",
                Principal="events.amazonaws.com",
                SourceArn=heartbeat_rule,
            )
        return upload_rule, heartbeat_rule

    def _ensure_images(self) -> dict[str, str]:
        images = {}
        password = None
        docker_auth = tempfile.TemporaryDirectory(prefix="strobe-ecr-")
        docker_env = os.environ | {"DOCKER_CONFIG": docker_auth.name}
        (Path(docker_auth.name) / "config.json").write_text('{"auths":{}}', encoding="utf-8")
        if self.build_images:
            subprocess.run(["npm", "run", "build"], cwd=ROOT, check=True, shell=True)
            subprocess.run(["npm", "run", "build:server"], cwd=ROOT, check=True, shell=True)
            password = self.ecr.get_authorization_token()["authorizationData"][0]
            registry = password["proxyEndpoint"].removeprefix("https://")
            (Path(docker_auth.name) / "config.json").write_text(
                json.dumps(
                    {
                        "auths": {
                            registry: {"auth": password["authorizationToken"]},
                        }
                    }
                ),
                encoding="utf-8",
            )
        for component, dockerfile in {"agent": "Dockerfile.agent", "mcp": "Dockerfile.mcp"}.items():
            repository = f"{PREFIX}-{component}"
            try:
                data = self.ecr.describe_repositories(repositoryNames=[repository])["repositories"][
                    0
                ]
            except self.ecr.exceptions.RepositoryNotFoundException:
                data = self.ecr.create_repository(
                    repositoryName=repository,
                    imageScanningConfiguration={"scanOnPush": True},
                    encryptionConfiguration={"encryptionType": "AES256"},
                    tags=self._tag_list(),
                )["repository"]
                try:
                    self.ecr.put_lifecycle_policy(
                        repositoryName=repository,
                        lifecyclePolicyText=json.dumps(
                            {
                                "rules": [
                                    {
                                        "rulePriority": 1,
                                        "description": "Keep five images",
                                        "selection": {
                                            "tagStatus": "any",
                                            "countType": "imageCountMoreThan",
                                            "countNumber": 5,
                                        },
                                        "action": {"type": "expire"},
                                    }
                                ]
                            }
                        ),
                    )
                except ClientError as error:
                    if error.response["Error"]["Code"] not in {
                        "AccessDenied",
                        "AccessDeniedException",
                    }:
                        raise
            uri = f"{data['repositoryUri']}:latest"
            if self.build_images:
                subprocess.run(
                    ["docker", "build", "-f", dockerfile, "-t", uri, "."],
                    cwd=ROOT,
                    check=True,
                    env=docker_env,
                )
                subprocess.run(
                    ["docker", "--config", docker_auth.name, "push", uri],
                    cwd=ROOT,
                    check=True,
                    env=docker_env,
                )
            images[component] = uri
            self._record(
                "ECR repository",
                data["repositoryArn"],
                f"Stores the Strobe {component} container image.",
            )
        docker_auth.cleanup()
        return images

    def _ensure_ecs(
        self, images: dict[str, str], secret_arn: str
    ) -> tuple[str, list[dict[str, str]]]:
        cluster_name = f"{PREFIX}-cluster"
        cluster = self.ecs.create_cluster(
            clusterName=cluster_name,
            settings=[{"name": "containerInsights", "value": "enabled"}],
            tags=self._ecs_tag_list(),
        )["cluster"]
        network = self._network()
        mcp_alb_arn, mcp_listener_arn, mcp_target_arn, mcp_dns = self._load_balancer(
            network, "mcp", internal=True
        )
        alb_arn, listener_arn, target_arn, dns = self._load_balancer(network, "agent")
        demo_user = self._demo_user_id()
        mcp_task = self._task_definition(
            "mcp",
            images["mcp"],
            [
                *self._application_environment(),
            ],
            secrets_config=[{"name": "MCP_API_KEY", "valueFrom": f"{secret_arn}:apiKey::"}],
        )
        agent_task = self._task_definition(
            "agent",
            images["agent"],
            [
                {"name": "MCP_URL", "value": f"http://{mcp_dns}"},
                {"name": "MCP_API_KEY_SECRET_ARN", "value": secret_arn},
                {"name": "DEMO_USER_ID", "value": demo_user},
                {"name": "CHAT_MODEL_ID", "value": "apac.amazon.nova-lite-v1:0"},
            ],
        )
        self._ecs_service(
            cluster_name,
            "mcp",
            mcp_task,
            network["private"],
            network["mcp_sg"],
            target_group=mcp_target_arn,
        )
        agent_service = self._ecs_service(
            cluster_name,
            "agent",
            agent_task,
            network["public"],
            network["agent_sg"],
            target_group=target_arn,
        )
        resources = [
            {
                "type": "ECS cluster",
                "arn": cluster["clusterArn"],
                "description": "Runs the independently scalable Strobe agent and MCP services.",
            },
            {
                "type": "ECS service",
                "arn": agent_service,
                "description": "Hosts the ACP agent and browser chat client on Fargate.",
            },
            {
                "type": "ECS service",
                "arn": f"arn:aws:ecs:{REGION}:{ACCOUNT_ID}:service/{cluster_name}/{PREFIX}-mcp",
                "description": "Hosts the private dedicated MCP tool server on Fargate.",
            },
            {
                "type": "MCP server",
                "arn": f"http://{mcp_dns}/mcp",
                "description": (
                    "Exposes semantic photo search, posts, and heartbeat records as MCP tools."
                ),
            },
            {
                "type": "Internal Application Load Balancer",
                "arn": mcp_alb_arn,
                "description": "Provides stable private routing from the ACP agent to MCP.",
            },
            {
                "type": "Internal ALB listener",
                "arn": mcp_listener_arn,
                "description": "Routes private MCP tool traffic to its Fargate task.",
            },
            {
                "type": "Application Load Balancer",
                "arn": alb_arn,
                "description": "Provides the public ACP WebSocket and chat frontend endpoint.",
            },
            {
                "type": "ALB listener",
                "arn": listener_arn,
                "description": "Routes browser HTTP and WebSocket traffic to the ACP agent.",
            },
        ]
        return f"http://{dns}", resources

    def _application_environment(self) -> list[dict[str, str]]:
        values = {
            "AWS_REGION_NAME": REGION,
            "MEDIA_BUCKET": f"{PREFIX}-media",
            "POSTS_TABLE": f"{PREFIX}-posts",
            "USERS_TABLE": f"{PREFIX}-users",
            "CLASSIFICATIONS_TABLE": f"{PREFIX}-classifications",
            "AGENT_RUNS_TABLE": f"{PREFIX}-agent-runs",
            "IDEMPOTENCY_TABLE": f"{PREFIX}-idempotency",
            "VECTOR_BUCKET_NAME": f"{PREFIX}-vectors",
            "VECTOR_INDEX_NAME": "photo-search",
            "EMBEDDING_MODEL_ID": "amazon.titan-embed-text-v2:0",
            "CHAT_MODEL_ID": "apac.amazon.nova-lite-v1:0",
        }
        return [{"name": key, "value": value} for key, value in values.items()]

    def _network(self) -> dict[str, Any]:
        vpcs = self.ec2.describe_vpcs(
            Filters=[{"Name": "tag:Name", "Values": ["aws-controltower-VPC"]}]
        )["Vpcs"]
        if not vpcs:
            raise RuntimeError("CAB432 shared VPC was not found")
        vpc = vpcs[0]["VpcId"]
        subnets = self.ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])[
            "Subnets"
        ]
        public = [item["SubnetId"] for item in subnets if item["MapPublicIpOnLaunch"]][:3]
        private = [item["SubnetId"] for item in subnets if not item["MapPublicIpOnLaunch"]][:3]
        # The CAB432 student role explicitly denies security-group creation. The
        # course-provided group permits ports 80 and 8080 and is the supported
        # network boundary in this shared account. MCP remains private because it
        # has no load balancer and runs only in private subnets.
        groups = self.ec2.describe_security_groups(
            Filters=[
                {"Name": "group-name", "Values": ["CAB432SG"]},
                {"Name": "vpc-id", "Values": [vpc]},
            ]
        )["SecurityGroups"]
        if not groups:
            raise RuntimeError("Course-provided CAB432SG security group was not found")
        shared_sg = groups[0]["GroupId"]
        return {
            "vpc": vpc,
            "public": public,
            "private": private,
            "alb_sg": shared_sg,
            "agent_sg": shared_sg,
            "mcp_sg": shared_sg,
        }

    def _security_group(self, name: str, description: str, vpc: str) -> str:
        groups = self.ec2.describe_security_groups(
            Filters=[{"Name": "group-name", "Values": [name]}, {"Name": "vpc-id", "Values": [vpc]}]
        )["SecurityGroups"]
        if groups:
            return groups[0]["GroupId"]
        group_id = self.ec2.create_security_group(
            GroupName=name,
            Description=description,
            VpcId=vpc,
            TagSpecifications=[{"ResourceType": "security-group", "Tags": self._tag_list()}],
        )["GroupId"]
        return group_id

    def _authorize(
        self, group: str, port: int, *, cidr: str | None = None, source_group: str | None = None
    ) -> None:
        pair: dict[str, Any] = {"IpProtocol": "tcp", "FromPort": port, "ToPort": port}
        if cidr:
            pair["IpRanges"] = [{"CidrIp": cidr}]
        if source_group:
            pair["UserIdGroupPairs"] = [{"GroupId": source_group}]
        try:
            self.ec2.authorize_security_group_ingress(GroupId=group, IpPermissions=[pair])
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "InvalidPermission.Duplicate":
                raise

    def _namespace(self, vpc: str) -> str:
        namespaces = self.discovery.list_namespaces(
            Filters=[{"Name": "TYPE", "Values": ["DNS_PRIVATE"], "Condition": "EQ"}]
        )["Namespaces"]
        found = next((item for item in namespaces if item["Name"] == "strobe.local"), None)
        if found:
            return found["Id"]
        operation = self.discovery.create_private_dns_namespace(
            Name="strobe.local", Vpc=vpc, Tags=self._tag_list()
        )
        operation_id = operation["OperationId"]
        while True:
            status = self.discovery.get_operation(OperationId=operation_id)["Operation"]
            if status["Status"] == "SUCCESS":
                return status["Targets"]["NAMESPACE"]
            if status["Status"] == "FAIL":
                raise RuntimeError(status.get("ErrorMessage", "Namespace creation failed"))
            time.sleep(3)

    def _discovery_service(self, namespace_id: str) -> str:
        services = self.discovery.list_services(
            Filters=[{"Name": "NAMESPACE_ID", "Values": [namespace_id], "Condition": "EQ"}]
        )["Services"]
        found = next((item for item in services if item["Name"] == "mcp"), None)
        if found:
            return found["Arn"]
        return self.discovery.create_service(
            Name="mcp",
            NamespaceId=namespace_id,
            DnsConfig={"DnsRecords": [{"Type": "A", "TTL": 10}], "RoutingPolicy": "MULTIVALUE"},
            HealthCheckCustomConfig={"FailureThreshold": 1},
            Tags=self._tag_list(),
        )["Service"]["Arn"]

    def _task_definition(
        self,
        component: str,
        image: str,
        environment: list[dict[str, str]],
        secrets_config: list[dict[str, str]] | None = None,
    ) -> str:
        family = f"{PREFIX}-{component}"
        log_group = f"/ecs/{family}"
        self._ensure_log_group(log_group)
        health_command = (
            ["CMD-SHELL", "wget -qO- http://localhost:8080/healthz || exit 1"]
            if component == "agent"
            else [
                "CMD-SHELL",
                "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')\"",
            ]
        )
        response = self.ecs.register_task_definition(
            family=family,
            taskRoleArn=ROLE_ARNS["ecs_task"],
            executionRoleArn=ROLE_ARNS["ecs_execution"],
            networkMode="awsvpc",
            requiresCompatibilities=["FARGATE"],
            cpu="256",
            memory="512",
            runtimePlatform={"cpuArchitecture": "X86_64", "operatingSystemFamily": "LINUX"},
            containerDefinitions=[
                {
                    "name": component,
                    "image": image,
                    "essential": True,
                    "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
                    "environment": environment,
                    "secrets": secrets_config or [],
                    "healthCheck": {
                        "command": health_command,
                        "interval": 30,
                        "timeout": 5,
                        "retries": 3,
                        "startPeriod": 20,
                    },
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": log_group,
                            "awslogs-region": REGION,
                            "awslogs-stream-prefix": component,
                        },
                    },
                    "readonlyRootFilesystem": False,
                }
            ],
            tags=self._ecs_tag_list(),
        )
        return response["taskDefinition"]["taskDefinitionArn"]

    def _ecs_service(
        self,
        cluster: str,
        component: str,
        task: str,
        subnets: list[str],
        security_group: str,
        *,
        discovery: str | None = None,
        target_group: str | None = None,
    ) -> str:
        name = f"{PREFIX}-{component}"
        services = self.ecs.describe_services(cluster=cluster, services=[name])["services"]
        kwargs: dict[str, Any] = {
            "cluster": cluster,
            "service": name,
            "taskDefinition": task,
            "desiredCount": 1,
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": subnets,
                    "securityGroups": [security_group],
                    "assignPublicIp": "ENABLED",
                }
            },
            "forceNewDeployment": True,
        }
        if services and services[0].get("status") != "INACTIVE":
            response = self.ecs.update_service(**kwargs)["service"]
        else:
            kwargs.pop("forceNewDeployment")
            kwargs.update(
                {
                    "serviceName": kwargs.pop("service"),
                    "launchType": "FARGATE",
                    "enableExecuteCommand": True,
                    "deploymentConfiguration": {
                        "maximumPercent": 200,
                        "minimumHealthyPercent": 50,
                        "deploymentCircuitBreaker": {"enable": True, "rollback": True},
                    },
                    "healthCheckGracePeriodSeconds": 60,
                    "propagateTags": "SERVICE",
                    "tags": self._ecs_tag_list(),
                }
            )
            if discovery:
                kwargs["serviceRegistries"] = [{"registryArn": discovery}]
            if target_group:
                kwargs["loadBalancers"] = [
                    {
                        "targetGroupArn": target_group,
                        "containerName": component,
                        "containerPort": 8080,
                    }
                ]
            response = self.ecs.create_service(**kwargs)["service"]
        return response["serviceArn"]

    def _load_balancer(
        self, network: dict[str, Any], component: str, *, internal: bool = False
    ) -> tuple[str, str, str, str]:
        name = f"{STUDENT_ID}-strobe-{component}"
        existing = (
            self.elb.describe_load_balancers(Names=[name])["LoadBalancers"]
            if self._alb_exists(name)
            else []
        )
        if existing:
            alb = existing[0]
        else:
            alb = self.elb.create_load_balancer(
                Name=name,
                Subnets=network["private"] if internal else network["public"],
                SecurityGroups=[network["alb_sg"]],
                Scheme="internal" if internal else "internet-facing",
                Type="application",
                IpAddressType="ipv4",
                Tags=self._tag_list(),
            )["LoadBalancers"][0]
        tg_name = f"{STUDENT_ID}-{component}-tg"
        groups = (
            self.elb.describe_target_groups(Names=[tg_name])["TargetGroups"]
            if self._tg_exists(tg_name)
            else []
        )
        if groups:
            target = groups[0]
        else:
            target = self.elb.create_target_group(
                Name=tg_name,
                Protocol="HTTP",
                Port=8080,
                VpcId=network["vpc"],
                TargetType="ip",
                HealthCheckPath="/healthz",
                Matcher={"HttpCode": "200"},
                Tags=self._tag_list(),
            )["TargetGroups"][0]
        listeners = self.elb.describe_listeners(LoadBalancerArn=alb["LoadBalancerArn"])["Listeners"]
        listener = next((item for item in listeners if item["Port"] == 80), None)
        if not listener:
            listener = self.elb.create_listener(
                LoadBalancerArn=alb["LoadBalancerArn"],
                Protocol="HTTP",
                Port=80,
                DefaultActions=[{"Type": "forward", "TargetGroupArn": target["TargetGroupArn"]}],
            )["Listeners"][0]
        return (
            alb["LoadBalancerArn"],
            listener["ListenerArn"],
            target["TargetGroupArn"],
            alb["DNSName"],
        )

    def _alb_exists(self, name: str) -> bool:
        try:
            self.elb.describe_load_balancers(Names=[name])
            return True
        except self.elb.exceptions.LoadBalancerNotFoundException:
            return False

    def _tg_exists(self, name: str) -> bool:
        try:
            self.elb.describe_target_groups(Names=[name])
            return True
        except self.elb.exceptions.TargetGroupNotFoundException:
            return False

    def _ensure_log_group(self, name: str) -> None:
        try:
            self.logs.create_log_group(logGroupName=name, tags=TAGS)
        except self.logs.exceptions.ResourceAlreadyExistsException:
            with contextlib.suppress(self.logs.exceptions.AccessDeniedException):
                self.logs.tag_log_group(logGroupName=name, tags=TAGS)
        with contextlib.suppress(self.logs.exceptions.AccessDeniedException):
            self.logs.put_retention_policy(logGroupName=name, retentionInDays=14)

    def _demo_user_id(self) -> str:
        items = (
            self.session.resource("dynamodb")
            .Table(f"{PREFIX}-users")
            .scan(Limit=100)
            .get("Items", [])
        )
        test_email = f"{STUDENT_ID}-strobe-test@example.com"
        user = next(
            (item for item in items if item.get("email") == test_email), items[0] if items else None
        )
        if not user:
            raise RuntimeError("No Strobe user exists for the ACP demo")
        return str(user["id"])

    def _write_manifest(self, endpoint: str) -> None:
        payload = {
            "cloudInfrastructure": self.resources,
            "metaData": {"track": "A", "qutUsernameTag": QUT_USERNAME, "agentEndpoint": endpoint},
        }
        (ROOT / "submission-agent-infra.yml").write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-images", action="store_true", help="Reuse existing latest ECR images"
    )
    args = parser.parse_args()
    AwsDeployment(build_images=not args.skip_images).deploy()


if __name__ == "__main__":
    main()
