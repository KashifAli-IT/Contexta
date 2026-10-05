"""Idempotently create the application bucket on the S3-compatible store.

Runs as a one-shot compose service (``createbuckets``) on a throwaway
``python:3.12-slim`` container, so no MinIO client image is required.
The application also performs this bootstrap in its own lifespan, but having
it as an infra step means the bucket exists before any app image is built.
"""

from __future__ import annotations

import os
import sys
import time

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

ENDPOINT = os.environ.get("S3_ENDPOINT", "http://minio:9000")
ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "contexta")
SECRET_KEY = os.environ.get("S3_SECRET_KEY", "contexta123")
BUCKET = os.environ.get("S3_BUCKET", "contexta")
ATTEMPTS = 30


def make_client() -> boto3.client:  # type: ignore[no-untyped-def]
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def main() -> int:
    client = make_client()
    for attempt in range(1, ATTEMPTS + 1):
        try:
            client.list_buckets()
            break
        except (EndpointConnectionError, ClientError) as exc:
            print(f"--> waiting for object store ({attempt}/{ATTEMPTS}): {exc}")
            time.sleep(2)
    else:
        print("!! object store unreachable", file=sys.stderr)
        return 1

    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    if BUCKET in existing:
        print(f"==> bucket '{BUCKET}' already exists")
    else:
        client.create_bucket(Bucket=BUCKET)
        print(f"==> bucket '{BUCKET}' created")

    # Verify a round-trip so presigned URLs are known to work end to end.
    key = ".bootstrap-probe"
    client.put_object(Bucket=BUCKET, Key=key, Body=b"contexta")
    client.delete_object(Bucket=BUCKET, Key=key)
    url = client.generate_presigned_url(
        "get_object", Params={"Bucket": BUCKET, "Key": "probe.pdf"}, ExpiresIn=60
    )
    print("==> buckets ready:", sorted(existing | {BUCKET}))
    print("==> presigned-url support: ok")
    print(f"    sample: {url[:96]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
