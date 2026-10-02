from __future__ import annotations

import base64
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config


REGION = os.getenv("AWS_REGION", "ap-southeast-2")
CONTROLLER = os.getenv("CONTROLLER", "app")
USER_POOL_ID = os.environ["USER_POOL_ID"]
USER_POOL_CLIENT_ID = os.environ["USER_POOL_CLIENT_ID"]
MEDIA_BUCKET = os.environ["MEDIA_BUCKET"]
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

TABLES = {
    "user": os.environ["USERS_TABLE"],
    "post": os.environ["POSTS_TABLE"],
    "comment": os.environ["COMMENTS_TABLE"],
    "like": os.environ["LIKES_TABLE"],
    "follow": os.environ["FOLLOWS_TABLE"],
    "moment": os.environ["MOMENTS_TABLE"],
}

dynamodb = boto3.resource("dynamodb", region_name=REGION)
cognito = boto3.client("cognito-idp", region_name=REGION)
s3 = boto3.client(
    "s3",
    region_name=REGION,
    endpoint_url=f"https://s3.{REGION}.amazonaws.com",
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)


class ApiError(Exception):
    def __init__(self, status_code: int, error: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.error = error
        self.message = message


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_id() -> str:
    return str(uuid.uuid4())


def table(entity: str):
    return dynamodb.Table(TABLES[entity])


def response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, default=str),
    }


def read_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise ApiError(400, "ValidationError", "Invalid JSON request body")


def path_and_method(event: dict[str, Any]) -> tuple[str, str]:
    path = event.get("rawPath") or event.get("path") or "/"
    path = path.rstrip("/") or "/"
    method = (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod") or "").upper()
    return path, method


def query_params(event: dict[str, Any]) -> dict[str, str]:
    return event.get("queryStringParameters") or {}


def scan(entity: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {}
    t = table(entity)
    while True:
        result = t.scan(**kwargs)
        items.extend(result.get("Items", []))
        if "LastEvaluatedKey" not in result:
            return items
        kwargs["ExclusiveStartKey"] = result["LastEvaluatedKey"]


def get_item(entity: str, item_id: str) -> dict[str, Any] | None:
    result = table(entity).get_item(Key={"id": item_id})
    return result.get("Item")


def put_item(entity: str, item: dict[str, Any]) -> dict[str, Any]:
    table(entity).put_item(Item=item)
    return item


def delete_item(entity: str, item_id: str) -> None:
    table(entity).delete_item(Key={"id": item_id})


def update_item(entity: str, item_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    existing = get_item(entity, item_id)
    if not existing:
        raise ApiError(404, "NotFound", f"{entity.title()} not found")
    existing.update({k: v for k, v in updates.items() if v is not None and k != "id"})
    existing["updatedAt"] = now_iso()
    put_item(entity, existing)
    return existing


def validate_email(email: str | None) -> None:
    if not email or not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        raise ApiError(400, "ValidationError", "Email is invalid")


def validate_password(password: str | None) -> None:
    if not password:
        raise ApiError(400, "ValidationError", "Password is required")
    if len(password) < 6:
        raise ApiError(400, "ValidationError", "Password must be at least 6 characters")


def validate_role(role: str | None) -> str:
    role = role or "user"
    if role not in {"user", "moderator"}:
        raise ApiError(400, "ValidationError", "Role must be either user or moderator")
    return role


def safe_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user:
        return None
    result = dict(user)
    result.pop("password", None)
    result.pop("cognitoUsername", None)
    return result


def find_user_by_email(email: str) -> dict[str, Any] | None:
    lowered = email.lower()
    return next((u for u in scan("user") if u.get("email", "").lower() == lowered), None)


def find_user_by_id(user_id: str) -> dict[str, Any] | None:
    return get_item("user", user_id)


def auth_identifier(body: dict[str, Any]) -> str:
    return (body.get("email") or body.get("username") or "").strip().lower()


def token_response(tokens: dict[str, Any]) -> dict[str, Any]:
    result = {
        "token": tokens["AccessToken"],
        "accessToken": tokens["AccessToken"],
        "tokenType": tokens.get("TokenType", "Bearer"),
        "expiresIn": tokens.get("ExpiresIn"),
    }
    if tokens.get("IdToken"):
        result["idToken"] = tokens["IdToken"]
    if tokens.get("RefreshToken"):
        result["refreshToken"] = tokens["RefreshToken"]
    return result


def decode_jwt_payload(token: str) -> dict[str, Any]:
    try:
        _header, payload, _signature = token.split(".", 2)
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode()).decode("utf-8"))
    except Exception:
        return {}


def get_cognito_tokens(email: str, password: str) -> dict[str, str]:
    try:
        auth = cognito.initiate_auth(
            ClientId=USER_POOL_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )
        return auth["AuthenticationResult"]
    except ClientError:
        raise ApiError(401, "Unauthorised", "Invalid email or password")


def user_role_from_cognito(username: str, fallback: str = "user") -> str:
    try:
        groups = cognito.admin_list_groups_for_user(UserPoolId=USER_POOL_ID, Username=username).get("Groups", [])
    except ClientError:
        return fallback
    names = {group["GroupName"] for group in groups}
    return "moderator" if "moderator" in names else fallback


def require_auth(event: dict[str, Any]) -> dict[str, str]:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    auth = headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise ApiError(401, "Unauthorised", "Missing bearer token")
    token = auth.removeprefix("Bearer ").strip()
    try:
        data = cognito.get_user(AccessToken=token)
    except ClientError:
        payload = decode_jwt_payload(token)
        user_id = payload.get("sub")
        user = find_user_by_id(user_id) if user_id else None
        if not user:
            raise ApiError(401, "Unauthorised", "Invalid or expired token")
        groups = set(payload.get("cognito:groups") or [])
        role = "moderator" if "moderator" in groups else user.get("role", "user")
        return {"userId": user["id"], "userRole": role, "username": user["username"], "email": user["email"]}
    attrs = {a["Name"]: a["Value"] for a in data.get("UserAttributes", [])}
    user_id = attrs.get("sub")
    user = find_user_by_id(user_id) if user_id else None
    if not user:
        raise ApiError(401, "Unauthorised", "Invalid token user")
    username = data["Username"]
    role = user_role_from_cognito(username, user.get("role", "user"))
    return {"userId": user["id"], "userRole": role, "username": user["username"], "email": user["email"]}


def optional_auth(event: dict[str, Any]) -> dict[str, str] | None:
    try:
        return require_auth(event)
    except ApiError:
        return None


def require_moderator(event: dict[str, Any]) -> dict[str, str]:
    current = require_auth(event)
    if current["userRole"] != "moderator":
        raise ApiError(403, "Forbidden", "Moderator access required")
    return current


def get_following_ids(user_id: str) -> list[str]:
    return [f["followeeId"] for f in scan("follow") if f.get("followerId") == user_id]


def get_follower_ids(user_id: str) -> list[str]:
    return [f["followerId"] for f in scan("follow") if f.get("followeeId") == user_id]


def post_count(user_id: str) -> int:
    return sum(1 for p in scan("post") if p.get("userId") == user_id)


def like_count(post_id: str) -> int:
    return sum(1 for l in scan("like") if l.get("postId") == post_id)


def comment_count(post_id: str) -> int:
    return sum(1 for c in scan("comment") if c.get("postId") == post_id)


def is_following(follower_id: str | None, followee_id: str) -> bool:
    return bool(follower_id) and any(f.get("followerId") == follower_id and f.get("followeeId") == followee_id for f in scan("follow"))


def has_liked(post_id: str, user_id: str | None) -> bool:
    return bool(user_id) and any(l.get("postId") == post_id and l.get("userId") == user_id for l in scan("like"))


def enrich_user(user: dict[str, Any], current_user_id: str | None = None) -> dict[str, Any]:
    result = safe_user(user) or {}
    result["stats"] = {
        "followers": len(get_follower_ids(user["id"])),
        "following": len(get_following_ids(user["id"])),
        "posts": post_count(user["id"]),
    }
    result["currentUserFollows"] = is_following(current_user_id, user["id"]) if current_user_id else False
    return result


def enrich_post(post: dict[str, Any], current_user_id: str | None = None) -> dict[str, Any]:
    result = dict(post)
    author = safe_user(find_user_by_id(post["userId"]))
    result["author"] = {"id": post["userId"], "username": author.get("username") if author else None}
    result["stats"] = {"likes": like_count(post["id"]), "comments": comment_count(post["id"])}
    result["currentUserLiked"] = has_liked(post["id"], current_user_id)
    result["images"] = [sign_media_url(value) for value in result.get("images", [])]
    return result


def sign_media_url(value: str) -> str:
    if not value:
        return value
    key = media_key_from_url(value)
    if not key:
        return value
    return s3.generate_presigned_url("get_object", Params={"Bucket": MEDIA_BUCKET, "Key": key}, ExpiresIn=300)


def media_key_from_url(value: str) -> str | None:
    marker = f"/{MEDIA_BUCKET}/"
    if marker in value:
        return value.split(marker, 1)[1]
    if ".amazonaws.com/" in value:
        return value.split(".amazonaws.com/", 1)[1]
    if value.startswith("s3://"):
        parts = value.removeprefix("s3://").split("/", 1)
        return parts[1] if len(parts) == 2 and parts[0] == MEDIA_BUCKET else None
    if value.startswith("/uploads/"):
        return value.removeprefix("/uploads/")
    if value.startswith("uploads/"):
        return value.removeprefix("uploads/")
    if re.fullmatch(r"[^/\s]+/[^/\s]+/[^/\s]+", value):
        return value
    return None


def list_sorted(entity: str, predicate=lambda item: True, reverse: bool = True) -> list[dict[str, Any]]:
    items = [item for item in scan(entity) if predicate(item)]
    items.sort(key=lambda item: item.get("createdAt", ""), reverse=reverse)
    return items


def handle_auth(path: str, method: str, event: dict[str, Any]) -> dict[str, Any]:
    body = read_body(event)
    if path == "/v1/auth/register" and method == "POST":
        email = auth_identifier(body)
        password = body.get("password")
        role = validate_role(body.get("role", "user"))
        validate_email(email)
        validate_password(password)
        if find_user_by_email(email):
            raise ApiError(409, "Conflict", "Email already exists")
        try:
            created = cognito.sign_up(ClientId=USER_POOL_CLIENT_ID, Username=email, Password=password, UserAttributes=[{"Name": "email", "Value": email}])
            user_id = created["UserSub"]
            cognito.admin_confirm_sign_up(UserPoolId=USER_POOL_ID, Username=email)
            cognito.admin_update_user_attributes(
                UserPoolId=USER_POOL_ID,
                Username=email,
                UserAttributes=[{"Name": "email_verified", "Value": "true"}],
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"UsernameExistsException", "AliasExistsException"}:
                raise ApiError(409, "Conflict", "Email already exists")
            raise
        if role == "moderator":
            cognito.admin_add_user_to_group(UserPoolId=USER_POOL_ID, Username=email, GroupName="moderator")
        else:
            cognito.admin_add_user_to_group(UserPoolId=USER_POOL_ID, Username=email, GroupName="user")
        user = {
            "id": user_id,
            "username": email,
            "email": email,
            "role": role,
            "cognitoUsername": email,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
        }
        put_item("user", user)
        tokens = get_cognito_tokens(email, password)
        return response(201, {"message": "User registered successfully", "user": safe_user(user), **token_response(tokens)})
    if path == "/v1/auth/login" and method == "POST":
        email = auth_identifier(body)
        password = body.get("password") or ""
        tokens = get_cognito_tokens(email, password)
        user = find_user_by_email(email)
        if not user:
            raise ApiError(401, "Unauthorised", "Invalid email or password")
        return response(200, {"message": "Login successful", "user": safe_user(user), **token_response(tokens)})
    raise ApiError(404, "NotFound", "Route not found")


def handle_posts(path: str, method: str, event: dict[str, Any]) -> dict[str, Any]:
    body = read_body(event) if method in {"POST", "PUT"} else {}
    current = optional_auth(event)
    if path == "/v1/posts" and method == "POST":
        current = require_auth(event)
        title = body.get("title")
        description = body.get("description", "")
        images = body.get("images") or []
        if not title:
            raise ApiError(400, "ValidationError", "Title is required")
        if len(str(title)) > 500 or len(str(description)) > 5000 or len(images) > 5:
            raise ApiError(400, "ValidationError", "Post payload is invalid")
        post = {
            "id": new_id(),
            "userId": current["userId"],
            "title": title,
            "description": description,
            "images": images,
            "status": "active",
            "hiddenBy": None,
            "hiddenAt": None,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
        }
        put_item("post", post)
        return response(201, {"message": "Post created successfully", "post": enrich_post(post, current["userId"])})
    match = re.fullmatch(r"/v1/posts/user/([^/]+)", path)
    if match and method == "GET":
        user_id = match.group(1)
        if not find_user_by_id(user_id):
            raise ApiError(404, "NotFound", "User not found")
        qp = query_params(event)
        limit = max(1, min(int(qp.get("limit", 20)), 100))
        offset = max(0, int(qp.get("offset", 0)))
        role = current["userRole"] if current else None
        viewer = current["userId"] if current else None
        posts = list_sorted("post", lambda p: p.get("userId") == user_id)
        posts = [p for p in posts if p.get("status") != "hidden" or role == "moderator" or viewer == p.get("userId")]
        return response(200, {"message": "Posts retrieved successfully", "posts": [enrich_post(p, viewer) for p in posts[offset:offset + limit]]})
    match = re.fullmatch(r"/v1/posts/([^/]+)(?:/(like|hide))?", path)
    if not match:
        raise ApiError(404, "NotFound", "Route not found")
    post_id, action = match.group(1), match.group(2)
    post = get_item("post", post_id)
    if not post:
        raise ApiError(404, "NotFound", "Post not found")
    if action == "like" and method == "POST":
        current = require_auth(event)
        if any(l.get("postId") == post_id and l.get("userId") == current["userId"] for l in scan("like")):
            raise ApiError(409, "Conflict", "Post already liked")
        like = {"id": new_id(), "postId": post_id, "userId": current["userId"], "createdAt": now_iso()}
        put_item("like", like)
        return response(201, {"message": "Post liked successfully", "like": like})
    if action == "like" and method == "DELETE":
        current = require_auth(event)
        like = next((l for l in scan("like") if l.get("postId") == post_id and l.get("userId") == current["userId"]), None)
        if not like:
            raise ApiError(404, "NotFound", "Like not found")
        delete_item("like", like["id"])
        return response(200, {"message": "Post unliked successfully"})
    if action == "hide" and method == "POST":
        current = require_moderator(event)
        post = update_item("post", post_id, {"status": "hidden", "hiddenBy": current["userId"], "hiddenAt": now_iso()})
        return response(200, {"message": "Post hidden successfully", "post": enrich_post(post, current["userId"])})
    if action:
        raise ApiError(404, "NotFound", "Route not found")
    if method == "GET":
        viewer = current["userId"] if current else None
        role = current["userRole"] if current else None
        if post.get("status") == "hidden" and role != "moderator" and viewer != post.get("userId"):
            raise ApiError(403, "Forbidden", "You cannot view this post")
        return response(200, {"message": "Post retrieved successfully", "post": enrich_post(post, viewer)})
    if method == "PUT":
        current = require_auth(event)
        if post["userId"] != current["userId"]:
            raise ApiError(403, "Forbidden", "You can only update your own post")
        updates = {k: body[k] for k in ("title", "description", "images") if k in body}
        updated = update_item("post", post_id, updates)
        return response(200, {"message": "Post updated successfully", "post": enrich_post(updated, current["userId"])})
    if method == "DELETE":
        current = require_auth(event)
        if post["userId"] != current["userId"]:
            raise ApiError(403, "Forbidden", "You can only delete your own post")
        for entity in ("comment", "like"):
            for item in scan(entity):
                if item.get("postId") == post_id:
                    delete_item(entity, item["id"])
        delete_item("post", post_id)
        return response(200, {"message": "Post deleted successfully"})
    raise ApiError(404, "NotFound", "Route not found")


def handle_comments(path: str, method: str, event: dict[str, Any]) -> dict[str, Any]:
    match = re.fullmatch(r"/v1/posts/([^/]+)/comments(?:/([^/]+))?", path)
    if not match:
        return handle_posts(path, method, event)
    post_id, comment_id = match.group(1), match.group(2)
    if not get_item("post", post_id):
        raise ApiError(404, "NotFound", "Post not found")
    if method == "GET" and not comment_id:
        comments = list_sorted("comment", lambda c: c.get("postId") == post_id, reverse=False)
        for comment in comments:
            author = safe_user(find_user_by_id(comment["userId"]))
            comment["author"] = {"id": comment["userId"], "username": author.get("username") if author else None}
        return response(200, {"message": "Comments retrieved successfully", "comments": comments})
    if method == "POST" and not comment_id:
        current = require_auth(event)
        text = (read_body(event).get("text") or "").strip()
        if not text:
            raise ApiError(400, "ValidationError", "Comment text is required")
        comment = {"id": new_id(), "postId": post_id, "userId": current["userId"], "text": text, "createdAt": now_iso(), "updatedAt": now_iso()}
        put_item("comment", comment)
        author = safe_user(find_user_by_id(current["userId"]))
        comment["author"] = {"id": current["userId"], "username": author.get("username") if author else None}
        return response(201, {"message": "Comment created successfully", "comment": comment})
    if method == "DELETE" and comment_id:
        current = require_auth(event)
        comment = get_item("comment", comment_id)
        if not comment:
            raise ApiError(404, "NotFound", "Comment not found")
        if comment["userId"] != current["userId"]:
            raise ApiError(403, "Forbidden", "You can only delete your own comments")
        delete_item("comment", comment_id)
        return response(200, {"message": "Comment deleted successfully"})
    raise ApiError(404, "NotFound", "Route not found")


def handle_users(path: str, method: str, event: dict[str, Any]) -> dict[str, Any]:
    current = optional_auth(event)
    if path == "/v1/users" and method == "GET":
        qp = query_params(event)
        q = (qp.get("q") or "").lower()
        limit = max(1, min(int(qp.get("limit", 20)), 100))
        users = [u for u in scan("user") if not q or q in u.get("username", "").lower()]
        return response(200, {"message": "Users retrieved successfully", "users": [enrich_user(u, current["userId"] if current else None) for u in users[:limit]]})
    match = re.fullmatch(r"/v1/users/([^/]+)(?:/(follow|followers|following))?", path)
    if not match:
        raise ApiError(404, "NotFound", "Route not found")
    user_id, action = match.group(1), match.group(2)
    user = find_user_by_id(user_id)
    if not user:
        raise ApiError(404, "NotFound", "User not found")
    if not action and method == "GET":
        return response(200, {"message": "User profile retrieved successfully", "user": enrich_user(user, current["userId"] if current else None)})
    if not action and method == "DELETE":
        current = require_auth(event)
        if current["userId"] != user_id:
            raise ApiError(403, "Forbidden", "You can only delete your own account")
        for entity in ("post", "comment", "like", "follow", "moment"):
            for item in scan(entity):
                if user_id in {item.get("userId"), item.get("followerId"), item.get("followeeId")}:
                    delete_item(entity, item["id"])
        cognito.admin_delete_user(UserPoolId=USER_POOL_ID, Username=user.get("cognitoUsername") or user["email"])
        delete_item("user", user_id)
        return response(200, {"message": "Account deleted successfully"})
    if action == "follow" and method == "POST":
        current = require_auth(event)
        if current["userId"] == user_id:
            raise ApiError(403, "Forbidden", "You cannot follow yourself")
        if is_following(current["userId"], user_id):
            raise ApiError(409, "Conflict", "Already following this user")
        follow = {"id": new_id(), "followerId": current["userId"], "followeeId": user_id, "createdAt": now_iso()}
        put_item("follow", follow)
        return response(201, {"message": "User followed successfully", "follow": follow})
    if action == "follow" and method == "DELETE":
        current = require_auth(event)
        follow = next((f for f in scan("follow") if f.get("followerId") == current["userId"] and f.get("followeeId") == user_id), None)
        if not follow:
            raise ApiError(404, "NotFound", "Follow relationship not found")
        delete_item("follow", follow["id"])
        return response(200, {"message": "User unfollowed successfully"})
    if action == "followers" and method == "GET":
        users = [find_user_by_id(uid) for uid in get_follower_ids(user_id)]
        enriched = [enrich_user(u, current["userId"] if current else None) for u in users if u]
        return response(200, {"message": "Followers retrieved successfully", "users": enriched, "followers": enriched})
    if action == "following" and method == "GET":
        users = [find_user_by_id(uid) for uid in get_following_ids(user_id)]
        enriched = [enrich_user(u, current["userId"] if current else None) for u in users if u]
        return response(200, {"message": "Following retrieved successfully", "users": enriched, "following": enriched})
    raise ApiError(404, "NotFound", "Route not found")


def handle_feed(path: str, method: str, event: dict[str, Any]) -> dict[str, Any]:
    if path != "/v1/feed" or method != "GET":
        raise ApiError(404, "NotFound", "Route not found")
    current = require_auth(event)
    qp = query_params(event)
    limit = max(1, min(int(qp.get("limit", 20)), 100))
    offset = max(0, int(qp.get("offset", 0)))
    visible_authors = {current["userId"], *get_following_ids(current["userId"])}
    posts = list_sorted("post", lambda p: p.get("userId") in visible_authors and (p.get("status") != "hidden" or current["userRole"] == "moderator"))
    return response(200, {"message": "Feed retrieved successfully", "posts": [enrich_post(p, current["userId"]) for p in posts[offset:offset + limit]]})


def handle_upload(path: str, method: str, event: dict[str, Any]) -> dict[str, Any]:
    if path == "/v1/uploads/url" and method == "POST":
        current = require_auth(event)
        post_id = read_body(event).get("postId")
        if not post_id:
            raise ApiError(400, "ValidationError", "Post ID is required")
        file_id = uuid.uuid4().hex[:8]
        key = f"{current['userId']}/{post_id}/{file_id}"
        upload_url = s3.generate_presigned_url("put_object", Params={"Bucket": MEDIA_BUCKET, "Key": key}, ExpiresIn=300)
        return response(200, {"message": "Upload URL generated", "uploadUrl": upload_url, "fileId": file_id})
    match = re.fullmatch(r"/v1/uploads/([^/]+)/([^/]+)/([^/]+)", path)
    if match and method == "PUT":
        current = require_auth(event)
        user_id, post_id, file_id = match.groups()
        if current["userId"] != user_id:
            raise ApiError(403, "Forbidden", "You can only upload files for your own user ID")
        data = event.get("body") or ""
        raw = base64.b64decode(data) if event.get("isBase64Encoded") else data.encode()
        key = f"{user_id}/{post_id}/{file_id}"
        s3.put_object(Bucket=MEDIA_BUCKET, Key=key, Body=raw, ContentType=(event.get("headers") or {}).get("content-type", "application/octet-stream"))
        return response(200, {"message": "File uploaded successfully", "file": {"fileId": file_id, "url": f"/uploads/{key}", "size": len(raw), "mimetype": "application/octet-stream"}})
    raise ApiError(404, "NotFound", "Route not found")


def handle_moments(path: str, method: str, event: dict[str, Any]) -> dict[str, Any]:
    current = require_auth(event)
    if path == "/v1/moments" and method == "POST":
        body = read_body(event)
        if not body.get("imageUrl"):
            raise ApiError(400, "ValidationError", "Image URL is required")
        moment = {
            "id": new_id(),
            "userId": current["userId"],
            "imageUrl": body["imageUrl"],
            "caption": body.get("caption", ""),
            "status": "active",
            "createdAt": now_iso(),
            "expiresAt": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat().replace("+00:00", "Z"),
            "updatedAt": now_iso(),
        }
        put_item("moment", moment)
        return response(201, {"message": "Moment created successfully", "moment": sign_moment(moment)})
    if path in {"/v1/moments/feed", "/v1/moments/archive"} and method == "GET":
        users = {current["userId"], *get_following_ids(current["userId"])}
        target_status = "active" if path.endswith("/feed") else "archived"
        moments = []
        for moment in list_sorted("moment", lambda m: m.get("userId") in users):
            moment = archive_if_expired(moment)
            if moment.get("status") == target_status:
                moments.append(sign_moment(moment))
        label = "Moment feed" if target_status == "active" else "Moment archive"
        return response(200, {"message": f"{label} retrieved successfully", "moments": moments})
    match = re.fullmatch(r"/v1/moments/([^/]+)(?:/(hide))?", path)
    if not match:
        raise ApiError(404, "NotFound", "Route not found")
    moment_id, action = match.group(1), match.group(2)
    moment = get_item("moment", moment_id)
    if not moment:
        raise ApiError(404, "NotFound", "Moment not found")
    if action == "hide" and method == "POST":
        current = require_moderator(event)
        updated = update_item("moment", moment_id, {"status": "hidden", "hiddenBy": current["userId"], "hiddenAt": now_iso()})
        return response(200, {"message": "Moment hidden successfully", "moment": sign_moment(updated)})
    if not action and method == "DELETE":
        if current["userRole"] != "moderator" and moment["userId"] != current["userId"]:
            raise ApiError(403, "Forbidden", "You cannot delete this moment")
        delete_item("moment", moment_id)
        return response(200, {"message": "Moment deleted successfully"})
    raise ApiError(404, "NotFound", "Route not found")


def archive_if_expired(moment: dict[str, Any]) -> dict[str, Any]:
    if moment.get("status") == "active" and moment.get("expiresAt"):
        expires = datetime.fromisoformat(moment["expiresAt"].replace("Z", "+00:00"))
        if expires <= datetime.now(timezone.utc):
            return update_item("moment", moment["id"], {"status": "archived", "archivedAt": now_iso()})
    return moment


def sign_moment(moment: dict[str, Any]) -> dict[str, Any]:
    result = dict(moment)
    result["imageUrl"] = sign_media_url(result.get("imageUrl", ""))
    return result


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    path, method = path_and_method(event)
    if method == "OPTIONS":
        return response(204, {})
    try:
        if path == "/health":
            return response(200, {"status": "ok", "timestamp": now_iso()})
        if CONTROLLER == "auth":
            return handle_auth(path, method, event)
        if CONTROLLER == "post":
            return handle_comments(path, method, event)
        if CONTROLLER == "feed":
            return handle_feed(path, method, event)
        if CONTROLLER == "user":
            return handle_users(path, method, event)
        if CONTROLLER == "upload":
            return handle_upload(path, method, event)
        if CONTROLLER == "moment":
            return handle_moments(path, method, event)
        raise ApiError(404, "NotFound", "Route not found")
    except ApiError as exc:
        return response(exc.status_code, {"error": exc.error, "message": exc.message})
    except Exception as exc:
        print(f"Unhandled error: {exc}")
        return response(500, {"error": "InternalServerError", "message": "An unexpected error occurred"})
