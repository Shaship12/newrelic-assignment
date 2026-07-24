"""
URL Shortener - AWS Lambda handler

Two operations, both served through a single Lambda behind an
API Gateway HTTP API (payload format 2.0):

  POST /urls          body: {"url": "https://example.com/very/long/link"}
                       -> 201 {"short_code": "aZ3xQ1", "short_url": ".../aZ3xQ1"}

  GET  /{code}         -> 302 redirect to the original URL
                          (or 404 JSON if the code doesn't exist)

Storage: a single DynamoDB table, hash key `short_code`.

This is intentionally small: no auth, no custom domain, no
collision-retry loop, no analytics. Those are called out as
explicit trade-offs in README.md - the point of the exercise is
the pipeline and the infra decisions, not the app logic.
"""

import json
import os
import secrets
import string
from urllib.parse import urlparse

import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)

CODE_ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 7


def _response(status_code, body_dict, extra_headers=None):
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body_dict),
    }


def _generate_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def _is_valid_url(candidate):
    try:
        parsed = urlparse(candidate)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def _create_short_url(event):
    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Request body must be valid JSON"})

    long_url = payload.get("url")
    if not long_url or not _is_valid_url(long_url):
        return _response(400, {"error": "Provide a valid 'url' (http/https)"})

    # Note: no collision-retry loop here - see README trade-offs.
    # With a 7-char base62 code the collision odds are low enough
    # for a take-home, not for a real production launch.
    code = _generate_code()

    table.put_item(
        Item={
            "short_code": code,
            "original_url": long_url,
        }
    )

    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"].get("stage", "")
    prefix = f"https://{domain}/{stage}" if stage and stage != "$default" else f"https://{domain}"

    return _response(
        201,
        {"short_code": code, "short_url": f"{prefix}/{code}"},
    )


def _redirect(event, code):
    result = table.get_item(Key={"short_code": code})
    item = result.get("Item")
    if not item:
        return _response(404, {"error": f"No URL found for code '{code}'"})

    return {
        "statusCode": 302,
        "headers": {"Location": item["original_url"]},
        "body": "",
    }


def handler(event, context):
    method = event["requestContext"]["http"]["method"]
    raw_path = event["rawPath"]
    stage = event["requestContext"].get("stage", "")
    path = raw_path
    if stage and stage != "$default" and path.startswith(f"/{stage}"):
        path = path[len(stage) + 1 :] or "/"

    if method == "POST" and path == "/urls":
        return _create_short_url(event)

    if method == "GET" and path not in ("", "/", "/urls"):
        code = path.lstrip("/")
        return _redirect(event, code)

    return _response(404, {"error": "Not found"})
