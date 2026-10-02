from __future__ import annotations

import json
from pathlib import Path

import boto3
import requests
import yaml


ROOT = Path(__file__).resolve().parents[1]
infra = yaml.safe_load((ROOT / "submission-infra.yml").read_text(encoding="utf-8"))["cloudInfrastructure"]
endpoint = infra["apiRoute53Record"].rstrip("/")
if not endpoint.startswith("http"):
    endpoint = f"https://{endpoint}"
test_username = infra["metaData"]["testUsername"]
test_password = infra["metaData"]["testPassword"]

dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-2")


def call(method: str, path: str, token: str | None = None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(method, f"{endpoint}{path}", headers=headers, timeout=30, **kwargs)
    try:
        body = response.json()
    except Exception:
        body = response.text
    printable = redact(body)
    print(method, path, response.status_code, printable)
    response.raise_for_status()
    return body


def redact(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if key.lower() in {"token", "accesstoken", "idtoken", "refreshtoken", "uploadurl", "imageurl", "images"}:
                redacted[key] = "<redacted-url-or-token>"
            else:
                redacted[key] = redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def count_table(entity: str) -> int:
    arn = next(item["arn"] for item in infra["dynamoDBTableARNs"] if item["entity"] == entity)
    name = arn.rsplit("/", 1)[-1]
    return dynamodb.Table(name).scan(Select="COUNT")["Count"]


def main() -> None:
    before = {entity: count_table(entity) for entity in ["user", "post", "comment", "like", "follow", "moment"]}
    login = call("POST", "/v1/auth/login", json={"email": test_username, "password": test_password})
    token = login["token"]
    user = login["user"]
    unique = f"verify-{__import__('uuid').uuid4().hex[:10]}@example.com"
    regular = call("POST", "/v1/auth/register", json={"email": unique, "password": "Regular123!", "role": "user"})
    regular_token = regular["token"]
    duplicate = requests.post(f"{endpoint}/v1/auth/register", json={"email": unique, "password": "Regular123!", "role": "user"}, timeout=30)
    print("POST", "/v1/auth/register duplicate", duplicate.status_code, redact(duplicate.json()))
    assert duplicate.status_code == 409
    post = call("POST", "/v1/posts", token, json={"title": "Verification post", "description": "Created by deployment verifier", "images": []})["post"]
    call("GET", f"/v1/posts/{post['id']}", token)
    call("POST", f"/v1/posts/{post['id']}/comments", token, json={"text": "Verification comment"})
    call("POST", f"/v1/posts/{post['id']}/like", token)
    forbidden = requests.post(f"{endpoint}/v1/posts/{post['id']}/hide", headers={"Authorization": f"Bearer {regular_token}"}, timeout=30)
    print("POST", "/v1/posts/{id}/hide regular", forbidden.status_code, redact(forbidden.json()))
    assert forbidden.status_code == 403
    call("POST", f"/v1/posts/{post['id']}/hide", token)
    upload = call("POST", "/v1/uploads/url", token, json={"postId": post["id"]})
    assert "X-Amz-Algorithm" in upload["uploadUrl"]
    uploaded = requests.put(upload["uploadUrl"], data=b"verification-image", headers={"Content-Type": "image/jpeg"}, timeout=30)
    print("PUT", "presigned S3 URL", uploaded.status_code, "<empty>")
    uploaded.raise_for_status()
    object_url = upload["uploadUrl"].split("?", 1)[0]
    call("PUT", f"/v1/posts/{post['id']}", token, json={"images": [object_url]})
    call("GET", f"/v1/posts/{post['id']}", token)
    call("POST", f"/v1/users/{user['id']}/follow", regular_token)
    call("POST", "/v1/moments", token, json={"imageUrl": object_url, "caption": "Verification moment"})
    call("GET", "/v1/users", token)
    call("GET", "/v1/feed", regular_token)
    after = {entity: count_table(entity) for entity in before}
    print(json.dumps({"endpoint": endpoint, "before": before, "after": after, "testUserId": user["id"]}, indent=2))


if __name__ == "__main__":
    main()
