from __future__ import annotations

import io
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import boto3
import yaml
from botocore.exceptions import ClientError


REGION = "ap-southeast-2"
ACCOUNT_ID = "901444280953"
STUDENT_ID = "n11553758"
FIRST_NAME = "Mesh"
LAST_NAME = "Alsulami"
QUT_USERNAME = f"{STUDENT_ID}@qut.edu.au"
PURPOSE = "assessment 1"
PREFIX = f"{STUDENT_ID}-strobe"
ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/CAB432-Lambda-Role"
RUNTIME = "python3.14"
HANDLER = "lambda_app.lambda_handler"
TEST_USERNAME = f"{STUDENT_ID}-strobe-test@example.com"
TEST_PASSWORD = "StrobeTest123!"
ROOT_DOMAIN = "cab432.com"
CUSTOM_DOMAIN = f"{STUDENT_ID}.{ROOT_DOMAIN}"

ROOT = Path(__file__).resolve().parent
LAMBDA_SOURCE = ROOT / "lambda_app.py"

session = boto3.Session(region_name=REGION)
dynamodb = session.client("dynamodb")
s3 = session.client("s3")
s3control = session.client("s3control")
lambda_client = session.client("lambda")
apigw = session.client("apigatewayv2")
cognito = session.client("cognito-idp")
tagging = session.client("resourcegroupstaggingapi")
route53 = session.client("route53")
acm = session.client("acm")

TAGS = {"qut-username": QUT_USERNAME, "qut username": QUT_USERNAME, "purpose": PURPOSE}
TABLES = {
    "user": f"{PREFIX}-users",
    "post": f"{PREFIX}-posts",
    "comment": f"{PREFIX}-comments",
    "like": f"{PREFIX}-likes",
    "follow": f"{PREFIX}-follows",
    "moment": f"{PREFIX}-moments",
}
CONTROLLERS = ["auth", "feed", "moment", "post", "user", "upload"]
ROUTES = [
    ("/v1/auth/register", "POST", "auth", "user", []),
    ("/v1/auth/login", "POST", "auth", "user", []),
    ("/v1/posts", "POST", "post", "post", []),
    ("/v1/posts/user/{userId}", "GET", "post", "post", [{"entity": "user", "arn": ""}, {"entity": "like", "arn": ""}, {"entity": "comment", "arn": ""}]),
    ("/v1/posts/{id}", "GET", "post", "post", [{"entity": "user", "arn": ""}, {"entity": "like", "arn": ""}, {"entity": "comment", "arn": ""}]),
    ("/v1/posts/{id}", "PUT", "post", "post", []),
    ("/v1/posts/{id}", "DELETE", "post", "post", [{"entity": "comment", "arn": ""}, {"entity": "like", "arn": ""}]),
    ("/v1/posts/{id}/like", "POST", "post", "like", [{"entity": "post", "arn": ""}]),
    ("/v1/posts/{id}/like", "DELETE", "post", "like", [{"entity": "post", "arn": ""}]),
    ("/v1/posts/{id}/hide", "POST", "post", "post", []),
    ("/v1/posts/{postId}/comments", "POST", "post", "comment", [{"entity": "post", "arn": ""}, {"entity": "user", "arn": ""}]),
    ("/v1/posts/{postId}/comments", "GET", "post", "comment", [{"entity": "post", "arn": ""}, {"entity": "user", "arn": ""}]),
    ("/v1/posts/{postId}/comments/{commentId}", "DELETE", "post", "comment", []),
    ("/v1/feed", "GET", "feed", "post", [{"entity": "follow", "arn": ""}, {"entity": "like", "arn": ""}, {"entity": "comment", "arn": ""}]),
    ("/v1/users", "GET", "user", "user", [{"entity": "follow", "arn": ""}, {"entity": "post", "arn": ""}]),
    ("/v1/users/{id}", "GET", "user", "user", [{"entity": "follow", "arn": ""}, {"entity": "post", "arn": ""}]),
    ("/v1/users/{id}", "DELETE", "user", "user", [{"entity": "post", "arn": ""}, {"entity": "comment", "arn": ""}, {"entity": "like", "arn": ""}, {"entity": "follow", "arn": ""}, {"entity": "moment", "arn": ""}]),
    ("/v1/users/{userId}/follow", "POST", "user", "follow", [{"entity": "user", "arn": ""}]),
    ("/v1/users/{userId}/follow", "DELETE", "user", "follow", [{"entity": "user", "arn": ""}]),
    ("/v1/users/{userId}/followers", "GET", "user", "follow", [{"entity": "user", "arn": ""}]),
    ("/v1/users/{userId}/following", "GET", "user", "follow", [{"entity": "user", "arn": ""}]),
    ("/v1/uploads/url", "POST", "upload", "media", []),
    ("/v1/moments", "POST", "moment", "moment", []),
    ("/v1/moments/feed", "GET", "moment", "moment", [{"entity": "follow", "arn": ""}]),
    ("/v1/moments/archive", "GET", "moment", "moment", [{"entity": "follow", "arn": ""}]),
    ("/v1/moments/{id}/hide", "POST", "moment", "moment", []),
    ("/v1/moments/{id}", "DELETE", "moment", "moment", []),
]


def arn(service: str, resource: str) -> str:
    return f"arn:aws:{service}:{REGION}:{ACCOUNT_ID}:{resource}"


def tag_list() -> list[dict[str, str]]:
    return [{"Key": key, "Value": value} for key, value in TAGS.items()]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_table(name: str) -> str:
    try:
        dynamodb.describe_table(TableName=name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        dynamodb.create_table(
            TableName=name,
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
            Tags=tag_list(),
        )
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=name)
    table_arn = dynamodb.describe_table(TableName=name)["Table"]["TableArn"]
    for attempt in range(6):
        try:
            dynamodb.update_continuous_backups(
                TableName=name,
                PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True, "RecoveryPeriodInDays": 7},
            )
            break
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ContinuousBackupsUnavailableException" and attempt < 5:
                time.sleep(10)
                continue
            try:
                dynamodb.update_continuous_backups(
                    TableName=name,
                    PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
                )
                break
            except ClientError as fallback_exc:
                if fallback_exc.response["Error"]["Code"] == "ContinuousBackupsUnavailableException" and attempt < 5:
                    time.sleep(10)
                    continue
                raise
    try:
        dynamodb.tag_resource(ResourceArn=table_arn, Tags=tag_list())
    except ClientError:
        pass
    return table_arn


def ensure_bucket(name: str) -> str:
    try:
        s3.head_bucket(Bucket=name)
    except ClientError:
        s3.create_bucket(Bucket=name, CreateBucketConfiguration={"LocationConstraint": REGION})
    s3.put_public_access_block(
        Bucket=name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    try:
        s3.put_bucket_encryption(
            Bucket=name,
            ServerSideEncryptionConfiguration={
                "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
            },
        )
    except ClientError:
        pass
    s3.put_bucket_cors(
        Bucket=name,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
                    "AllowedOrigins": ["*"],
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 300,
                }
            ]
        },
    )
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCab432LambdaRoleMediaAccess",
                "Effect": "Allow",
                "Principal": {"AWS": ROLE_ARN},
                "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                "Resource": f"arn:aws:s3:::{name}/*",
            },
            {
                "Sid": "AllowCab432LambdaRoleBucketList",
                "Effect": "Allow",
                "Principal": {"AWS": ROLE_ARN},
                "Action": ["s3:ListBucket"],
                "Resource": f"arn:aws:s3:::{name}",
            },
        ],
    }
    try:
        s3.put_bucket_policy(Bucket=name, Policy=json.dumps(policy))
    except ClientError:
        pass
    try:
        s3.put_bucket_tagging(Bucket=name, Tagging={"TagSet": tag_list()})
    except ClientError:
        try:
            s3control.tag_resource(AccountId=ACCOUNT_ID, ResourceArn=f"arn:aws:s3:::{name}", Tags=tag_list())
        except ClientError:
            try:
                tagging.tag_resources(ResourceARNList=[f"arn:aws:s3:::{name}"], Tags=TAGS)
            except ClientError:
                pass
            existing = s3.get_bucket_tagging(Bucket=name).get("TagSet", [])
            expected = {(tag["Key"], tag["Value"]) for tag in existing}
            if ("qut-username", QUT_USERNAME) not in expected or ("purpose", PURPOSE) not in expected:
                raise
    return f"arn:aws:s3:::{name}"


def find_user_pool() -> dict | None:
    token = None
    while True:
        kwargs = {"MaxResults": 60}
        if token:
            kwargs["NextToken"] = token
        result = cognito.list_user_pools(**kwargs)
        for pool in result.get("UserPools", []):
            if pool["Name"] == f"{PREFIX}-users":
                return pool
        token = result.get("NextToken")
        if not token:
            return None


def ensure_user_pool() -> tuple[str, str, str]:
    pool = find_user_pool()
    if pool:
        pool_id = pool["Id"]
    else:
        result = cognito.create_user_pool(
            PoolName=f"{PREFIX}-users",
            UsernameAttributes=["email"],
            AutoVerifiedAttributes=["email"],
            Policies={"PasswordPolicy": {"MinimumLength": 8, "RequireUppercase": True, "RequireLowercase": True, "RequireNumbers": True, "RequireSymbols": False}},
            EmailConfiguration={
                "SourceArn": f"arn:aws:ses:{REGION}:{ACCOUNT_ID}:identity/noreply@cab432.com",
                "EmailSendingAccount": "DEVELOPER",
                "From": "CAB432 Strobe <noreply@cab432.com>",
            },
            UserPoolTags=TAGS,
        )
        pool_id = result["UserPool"]["Id"]
    for group in ("user", "moderator"):
        try:
            cognito.create_group(UserPoolId=pool_id, GroupName=group)
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "GroupExistsException":
                raise
    clients = cognito.list_user_pool_clients(UserPoolId=pool_id, MaxResults=60).get("UserPoolClients", [])
    client = next((item for item in clients if item["ClientName"] == f"{PREFIX}-client"), None)
    if client:
        client_id = client["ClientId"]
        cognito.update_user_pool_client(
            UserPoolId=pool_id,
            ClientId=client_id,
            ClientName=f"{PREFIX}-client",
            AccessTokenValidity=24,
            IdTokenValidity=24,
            RefreshTokenValidity=1,
            TokenValidityUnits={"AccessToken": "hours", "IdToken": "hours", "RefreshToken": "days"},
            ExplicitAuthFlows=[
                "ALLOW_USER_PASSWORD_AUTH",
                "ALLOW_ADMIN_USER_PASSWORD_AUTH",
                "ALLOW_REFRESH_TOKEN_AUTH",
                "ALLOW_USER_SRP_AUTH",
            ],
            PreventUserExistenceErrors="ENABLED",
        )
    else:
        client_id = cognito.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName=f"{PREFIX}-client",
            GenerateSecret=False,
            AccessTokenValidity=24,
            IdTokenValidity=24,
            RefreshTokenValidity=1,
            TokenValidityUnits={"AccessToken": "hours", "IdToken": "hours", "RefreshToken": "days"},
            ExplicitAuthFlows=[
                "ALLOW_USER_PASSWORD_AUTH",
                "ALLOW_ADMIN_USER_PASSWORD_AUTH",
                "ALLOW_REFRESH_TOKEN_AUTH",
                "ALLOW_USER_SRP_AUTH",
            ],
            PreventUserExistenceErrors="ENABLED",
        )["UserPoolClient"]["ClientId"]
    return pool_id, client_id, arn("cognito-idp", f"userpool/{pool_id}")


def zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(LAMBDA_SOURCE, "lambda_app.py")
    return buffer.getvalue()


def ensure_lambda(controller: str, env: dict[str, str]) -> str:
    name = f"{PREFIX}-{controller}"
    code = zip_bytes()
    try:
        result = lambda_client.create_function(
            FunctionName=name,
            Runtime=RUNTIME,
            Role=ROLE_ARN,
            Handler=HANDLER,
            Code={"ZipFile": code},
            Timeout=20,
            MemorySize=256,
            Environment={"Variables": env},
            Tags=TAGS,
        )
        function_arn = result["FunctionArn"]
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceConflictException":
            raise
        lambda_client.update_function_code(FunctionName=name, ZipFile=code)
        waiter = lambda_client.get_waiter("function_updated")
        waiter.wait(FunctionName=name)
        lambda_client.update_function_configuration(FunctionName=name, Environment={"Variables": env}, Runtime=RUNTIME, Handler=HANDLER, Timeout=20, MemorySize=256)
        function_arn = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{name}"
    waiter = lambda_client.get_waiter("function_active")
    waiter.wait(FunctionName=name)
    return function_arn


def find_api() -> dict | None:
    token = None
    while True:
        kwargs = {}
        if token:
            kwargs["NextToken"] = token
        result = apigw.get_apis(**kwargs)
        for api in result.get("Items", []):
            if api["Name"] == f"{PREFIX}-api":
                return api
        token = result.get("NextToken")
        if not token:
            return None


def ensure_api(lambda_arns: dict[str, str]) -> tuple[str, str, str]:
    api = find_api()
    if api:
        api_id = api["ApiId"]
        endpoint = api["ApiEndpoint"]
    else:
        api = apigw.create_api(Name=f"{PREFIX}-api", ProtocolType="HTTP", CorsConfiguration={"AllowOrigins": ["*"], "AllowMethods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "AllowHeaders": ["Content-Type", "Authorization"]}, Tags=TAGS)
        api_id = api["ApiId"]
        endpoint = api["ApiEndpoint"]
    integrations = {}
    existing_integrations = apigw.get_integrations(ApiId=api_id).get("Items", [])
    for controller, function_arn in lambda_arns.items():
        name = f"{controller}-integration"
        existing = next((item for item in existing_integrations if item.get("Description") == name), None)
        if existing:
            integrations[controller] = existing["IntegrationId"]
        else:
            result = apigw.create_integration(
                ApiId=api_id,
                IntegrationType="AWS_PROXY",
                IntegrationUri=function_arn,
                PayloadFormatVersion="2.0",
                Description=name,
            )
            integrations[controller] = result["IntegrationId"]
        try:
            lambda_client.add_permission(
                FunctionName=function_arn,
                StatementId=f"{api_id}-{controller}-invoke",
                Action="lambda:InvokeFunction",
                Principal="apigateway.amazonaws.com",
                SourceArn=f"arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*/*/*",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ResourceConflictException":
                raise
    routes = []
    next_token = None
    while True:
        kwargs = {"ApiId": api_id}
        if next_token:
            kwargs["NextToken"] = next_token
        page = apigw.get_routes(**kwargs)
        routes.extend(page.get("Items", []))
        next_token = page.get("NextToken")
        if not next_token:
            break
    for route, method, controller, _storage, _additional in ROUTES:
        route_key = f"{method} {route}"
        target = f"integrations/{integrations[controller]}"
        existing = next((item for item in routes if item["RouteKey"] == route_key), None)
        if existing:
            apigw.update_route(ApiId=api_id, RouteId=existing["RouteId"], Target=target)
        else:
            try:
                created = apigw.create_route(ApiId=api_id, RouteKey=route_key, Target=target)
                routes.append({"RouteKey": route_key, "RouteId": created["RouteId"]})
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "ConflictException":
                    raise
                refreshed = apigw.get_routes(ApiId=api_id).get("Items", [])
                existing = next((item for item in refreshed if item["RouteKey"] == route_key), None)
                if not existing:
                    raise
                apigw.update_route(ApiId=api_id, RouteId=existing["RouteId"], Target=target)
                routes.append(existing)
    stages = apigw.get_stages(ApiId=api_id).get("Items", [])
    if not any(stage["StageName"] == "$default" for stage in stages):
        apigw.create_stage(ApiId=api_id, StageName="$default", AutoDeploy=True, Tags=TAGS)
    else:
        stage = next(stage for stage in stages if stage["StageName"] == "$default")
        apigw.update_stage(ApiId=api_id, StageName="$default", AutoDeploy=True)
    return api_id, endpoint, f"arn:aws:apigateway:{REGION}::/apis/{api_id}/stages/$default"


def route53_zone_id() -> str:
    zones = route53.list_hosted_zones_by_name(DNSName=ROOT_DOMAIN).get("HostedZones", [])
    zone = next((item for item in zones if item["Name"].rstrip(".") == ROOT_DOMAIN), None)
    if not zone:
        raise RuntimeError(f"Hosted zone {ROOT_DOMAIN} was not found")
    return zone["Id"].rsplit("/", 1)[-1]


def find_certificate(domain_name: str) -> str | None:
    paginator = acm.get_paginator("list_certificates")
    for page in paginator.paginate(CertificateStatuses=["ISSUED", "PENDING_VALIDATION"]):
        for cert in page.get("CertificateSummaryList", []):
            if cert.get("DomainName") == domain_name:
                return cert["CertificateArn"]
    return None


def ensure_certificate(domain_name: str) -> str:
    cert_arn = find_certificate(domain_name)
    if not cert_arn:
        result = acm.request_certificate(
            DomainName=domain_name,
            ValidationMethod="DNS",
            IdempotencyToken=STUDENT_ID.replace("-", "")[:32],
            Options={"CertificateTransparencyLoggingPreference": "DISABLED"},
            Tags=tag_list(),
        )
        cert_arn = result["CertificateArn"]
    zone_id = route53_zone_id()
    resource_record = None
    for _attempt in range(20):
        cert = acm.describe_certificate(CertificateArn=cert_arn)["Certificate"]
        if cert.get("Status") == "ISSUED":
            return cert_arn
        for option in cert.get("DomainValidationOptions", []):
            if option.get("DomainName") == domain_name and option.get("ResourceRecord"):
                resource_record = option["ResourceRecord"]
                break
        if resource_record:
            break
        time.sleep(6)
    if not resource_record:
        raise RuntimeError(f"ACM did not provide a DNS validation record for {domain_name}")
    route53.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": resource_record["Name"],
                        "Type": resource_record["Type"],
                        "TTL": 60,
                        "ResourceRecords": [{"Value": resource_record["Value"]}],
                    },
                }
            ]
        },
    )
    acm.get_waiter("certificate_validated").wait(CertificateArn=cert_arn, WaiterConfig={"Delay": 30, "MaxAttempts": 30})
    return cert_arn


def ensure_custom_domain(api_id: str, certificate_arn: str, domain_name: str) -> str:
    try:
        domain = apigw.get_domain_name(DomainName=domain_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "NotFoundException":
            raise
        domain = apigw.create_domain_name(
            DomainName=domain_name,
            DomainNameConfigurations=[
                {
                    "CertificateArn": certificate_arn,
                    "EndpointType": "REGIONAL",
                    "SecurityPolicy": "TLS_1_2",
                }
            ],
            Tags=TAGS,
        )
    mappings = apigw.get_api_mappings(DomainName=domain_name).get("Items", [])
    mapping = next((item for item in mappings if item.get("ApiMappingKey", "") == ""), None)
    if mapping:
        if mapping.get("ApiId") != api_id or mapping.get("Stage") != "$default":
            apigw.update_api_mapping(DomainName=domain_name, ApiMappingId=mapping["ApiMappingId"], ApiId=api_id, Stage="$default")
    else:
        apigw.create_api_mapping(DomainName=domain_name, ApiId=api_id, Stage="$default")

    zone_id = route53_zone_id()
    config = None
    for _attempt in range(20):
        domain = apigw.get_domain_name(DomainName=domain_name)
        configs = domain.get("DomainNameConfigurations") or []
        config = next((item for item in configs if item.get("ApiGatewayDomainName") and item.get("HostedZoneId")), None)
        if config:
            break
        time.sleep(6)
    if not config:
        raise RuntimeError(f"API Gateway custom domain target was not ready for {domain_name}")
    route53.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": domain_name,
                        "Type": "A",
                        "AliasTarget": {
                            "HostedZoneId": config["HostedZoneId"],
                            "DNSName": config["ApiGatewayDomainName"],
                            "EvaluateTargetHealth": False,
                        },
                    },
                }
            ]
        },
    )
    return domain_name


def ensure_test_user(pool_id: str, _client_id: str, user_table: str) -> None:
    existing = None
    try:
        cognito.admin_get_user(UserPoolId=pool_id, Username=TEST_USERNAME)
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "UserNotFoundException":
            raise
    else:
        existing = True
    if not existing:
        cognito.admin_create_user(
            UserPoolId=pool_id,
            Username=TEST_USERNAME,
            UserAttributes=[{"Name": "email", "Value": TEST_USERNAME}, {"Name": "email_verified", "Value": "true"}],
            MessageAction="SUPPRESS",
        )
    else:
        cognito.admin_update_user_attributes(
            UserPoolId=pool_id,
            Username=TEST_USERNAME,
            UserAttributes=[{"Name": "email_verified", "Value": "true"}],
        )
    cognito.admin_set_user_password(UserPoolId=pool_id, Username=TEST_USERNAME, Password=TEST_PASSWORD, Permanent=True)
    cognito.admin_add_user_to_group(UserPoolId=pool_id, Username=TEST_USERNAME, GroupName="moderator")
    user = cognito.admin_get_user(UserPoolId=pool_id, Username=TEST_USERNAME)
    attrs = {a["Name"]: a["Value"] for a in user["UserAttributes"]}
    item = {
        "id": attrs["sub"],
        "username": TEST_USERNAME,
        "email": TEST_USERNAME,
        "role": "moderator",
        "cognitoUsername": TEST_USERNAME,
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }
    session.resource("dynamodb").Table(user_table).put_item(Item=item)


def fill_additional(additional: list[dict[str, str]], table_arns: dict[str, str], bucket_arn: str) -> list[dict[str, str]]:
    output = []
    for item in additional:
        entity = item["entity"]
        output.append({"entity": entity, "arn": bucket_arn if entity == "media" else table_arns[entity]})
    return output


def write_manifests(api_id: str, api_base: str, certificate_arn: str, stage_arn: str, pool_arn: str, table_arns: dict[str, str], bucket_arn: str, lambda_arns: dict[str, str]) -> None:
    infra = {
        "cloudInfrastructure": {
            "apiGatewayExecutionARN": f"arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}",
            "apiGatewayStageARN": stage_arn,
            "apiRoute53Record": api_base,
            "certificateARN": certificate_arn,
            "cognitoARN": pool_arn,
            "dynamoDBPostsTableARN": table_arns["post"],
            "s3MediaStoreARN": bucket_arn,
            "dynamoDBTableARNs": [{"entity": entity, "arn": table_arns[entity]} for entity in ("user", "post", "comment", "like", "follow", "moment")],
            "lambdaARN": [{"controller": controller, "arn": lambda_arns[controller]} for controller in CONTROLLERS],
            "metaData": {
                "qutUsernameTag": QUT_USERNAME,
                "testUsername": TEST_USERNAME,
                "testPassword": TEST_PASSWORD,
                "studentDetail": {"studentID": STUDENT_ID, "studentFirstName": FIRST_NAME, "studentLastName": LAST_NAME},
            },
        }
    }
    routing = []
    for route, method, controller, storage, additional in ROUTES:
        storage_arn = bucket_arn if storage == "media" else table_arns[storage]
        routing.append(
            {
                "route": route,
                "method": method,
                "controller": controller,
                "apiGatewayRoute": f"{method} {route}",
                "lambdaARN": lambda_arns[controller],
                "storage": {"entity": storage, "arn": storage_arn},
                "additionalStorage": fill_additional(additional, table_arns, bucket_arn),
            }
        )
    (ROOT.parent / "submission-infra.yml").write_text(yaml.safe_dump(infra, sort_keys=False), encoding="utf-8")
    (ROOT.parent / "submission-routes.yml").write_text(yaml.safe_dump({"routing": routing}, sort_keys=False), encoding="utf-8")
    (ROOT.parent / "deployment-summary.json").write_text(json.dumps({"apiEndpoint": f"https://{api_base}", "testUsername": TEST_USERNAME}, indent=2), encoding="utf-8")


def main() -> None:
    table_arns = {entity: ensure_table(name) for entity, name in TABLES.items()}
    bucket_name = f"{PREFIX}-media"
    bucket_arn = ensure_bucket(bucket_name)
    pool_id, client_id, pool_arn = ensure_user_pool()
    env_base = {
        "USER_POOL_ID": pool_id,
        "USER_POOL_CLIENT_ID": client_id,
        "MEDIA_BUCKET": bucket_name,
        "PUBLIC_BASE_URL": "",
        "USERS_TABLE": TABLES["user"],
        "POSTS_TABLE": TABLES["post"],
        "COMMENTS_TABLE": TABLES["comment"],
        "LIKES_TABLE": TABLES["like"],
        "FOLLOWS_TABLE": TABLES["follow"],
        "MOMENTS_TABLE": TABLES["moment"],
    }
    lambda_arns = {}
    for controller in CONTROLLERS:
        env = dict(env_base)
        env["CONTROLLER"] = controller
        lambda_arns[controller] = ensure_lambda(controller, env)
    api_id, endpoint, stage_arn = ensure_api(lambda_arns)
    certificate_arn = ensure_certificate(CUSTOM_DOMAIN)
    api_base = ensure_custom_domain(api_id, certificate_arn, CUSTOM_DOMAIN)
    ensure_test_user(pool_id, client_id, TABLES["user"])
    write_manifests(api_id, api_base, certificate_arn, stage_arn, pool_arn, table_arns, bucket_arn, lambda_arns)
    print(json.dumps({"apiEndpoint": f"https://{api_base}", "rawApiEndpoint": endpoint, "submissionInfra": "submission-infra.yml", "submissionRoutes": "submission-routes.yml"}, indent=2))


if __name__ == "__main__":
    main()
