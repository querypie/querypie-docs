#!/usr/bin/env python3
"""Delete untagged manifests from a Docker Hub repository.

Usage:
    # Using Docker credential store (local):
    ./dockerhub-cleanup.py

    # Using environment variables (CI/CD):
    DOCKERHUB_USERNAME=user DOCKERHUB_PASSWORD=token ./dockerhub-cleanup.py

    # Dry-run (list only, no delete):
    ./dockerhub-cleanup.py --dry-run

Environment variables:
    DOCKERHUB_USERNAME  Docker Hub username
    DOCKERHUB_PASSWORD  Docker Hub password or Personal Access Token
    DOCKERHUB_REPO      Repository (default: querypie/confluence-mdx)
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error


REPO_DEFAULT = "querypie/confluence-mdx"


def get_credentials():
    """Get Docker Hub credentials from env vars or Docker credential store."""
    username = os.environ.get("DOCKERHUB_USERNAME", "")
    password = os.environ.get("DOCKERHUB_PASSWORD", "")
    if username and password:
        return username, password

    # Try Docker credential store (works on macOS/Linux with Docker Desktop)
    for helper in ["docker-credential-desktop", "docker-credential-osxkeychain"]:
        try:
            result = subprocess.run(
                [helper, "get"],
                input="https://index.docker.io/v1/",
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                creds = json.loads(result.stdout)
                if creds.get("Username") and creds.get("Secret"):
                    return creds["Username"], creds["Secret"]
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            continue

    print("ERROR: No credentials found.", file=sys.stderr)
    print("  Set DOCKERHUB_USERNAME and DOCKERHUB_PASSWORD env vars,", file=sys.stderr)
    print("  or log in via Docker Desktop.", file=sys.stderr)
    sys.exit(1)


def api_request(url, headers=None, method="GET", data=None):
    """Make an HTTP request and return (status_code, parsed_json)."""
    hdrs = headers or {}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode())
        except Exception:
            err_body = {"error": str(e)}
        return e.code, err_body


def authenticate(username, password):
    """Authenticate with Docker Hub and return a Bearer token."""
    status, body = api_request(
        "https://hub.docker.com/v2/users/login",
        headers={"Content-Type": "application/json"},
        data={"username": username, "password": password},
    )
    token = body.get("token", "")
    if status != 200 or not token:
        detail = body.get("detail", body.get("message", str(body)))
        print(f"ERROR: Docker Hub login failed (HTTP {status}): {detail}", file=sys.stderr)
        sys.exit(1)
    return token


def list_manifests(token, namespace, repo):
    """List all manifests in a repository, handling pagination."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_url = f"https://hub.docker.com/v2/namespaces/{namespace}/repositories/{repo}/manifests"
    all_manifests = []
    url = f"{base_url}?page_size=100"

    while url:
        status, body = api_request(url, headers=headers)
        if status != 200:
            msg = body.get("message", body.get("error", str(body)))
            print(f"ERROR: Failed to list manifests (HTTP {status}): {msg}", file=sys.stderr)
            sys.exit(1)

        manifests = body.get("manifests", [])
        all_manifests.extend(manifests)

        # Pagination: use last_evaluated_key if present
        last_key = body.get("last_evaluated_key")
        if last_key and manifests:
            url = f"{base_url}?page_size=100&last_evaluated_key={last_key}"
        else:
            url = None

    return all_manifests


def delete_manifests(token, namespace, repo, digests):
    """Delete manifests by digest."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"https://hub.docker.com/v2/namespaces/{namespace}/repositories/{repo}/manifests"

    status, body = api_request(
        url,
        headers=headers,
        method="DELETE",
        data={"digests": digests, "delete_references": True},
    )

    if status != 200:
        msg = body.get("message", body.get("error", str(body)))
        print(f"ERROR: Failed to delete manifests (HTTP {status}): {msg}", file=sys.stderr)
        return False

    # Check individual results
    results = body.get("status", {})
    success = 0
    failed = 0
    for digest, info in results.items():
        s = info.get("status", {}).get("status", "unknown")
        if s == "success":
            success += 1
        else:
            failed += 1
            print(f"  WARN: {digest[:30]}... status={s}", file=sys.stderr)

    print(f"  Deleted: {success}, Failed: {failed}")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Delete untagged manifests from Docker Hub")
    parser.add_argument("--dry-run", action="store_true", help="List untagged manifests without deleting")
    parser.add_argument("--repo", default=os.environ.get("DOCKERHUB_REPO", REPO_DEFAULT),
                        help=f"Repository (default: {REPO_DEFAULT})")
    args = parser.parse_args()

    parts = args.repo.split("/", 1)
    if len(parts) != 2:
        print(f"ERROR: Invalid repo format '{args.repo}', expected 'namespace/repo'", file=sys.stderr)
        sys.exit(1)
    namespace, repo = parts

    # Authenticate
    username, password = get_credentials()
    token = authenticate(username, password)

    # List all manifests
    manifests = list_manifests(token, namespace, repo)
    tagged = [m for m in manifests if m.get("tags")]
    untagged = [m for m in manifests if not m.get("tags")]

    print(f"Repository: {namespace}/{repo}")
    print(f"Total manifests: {len(manifests)}")
    print(f"  Tagged: {len(tagged)}")
    for m in tagged:
        d = m["manifest_digest"][:30]
        print(f"    {d}... tags={m['tags']}")
    print(f"  Untagged: {len(untagged)}")
    for m in untagged:
        d = m["manifest_digest"][:30]
        pushed = m.get("last_pushed", "?")
        print(f"    {d}... pushed={pushed}")

    if not untagged:
        print("\nNo untagged manifests to clean up.")
        return

    if args.dry_run:
        print(f"\n[DRY RUN] Would delete {len(untagged)} untagged manifest(s).")
        return

    # Delete untagged manifests
    digests = [m["manifest_digest"] for m in untagged]
    print(f"\nDeleting {len(digests)} untagged manifest(s)...")
    ok = delete_manifests(token, namespace, repo, digests)

    # Verify
    manifests_after = list_manifests(token, namespace, repo)
    untagged_after = [m for m in manifests_after if not m.get("tags")]
    print(f"\nVerification: {len(untagged)} -> {len(untagged_after)} untagged manifests")

    if untagged_after:
        print(f"WARNING: {len(untagged_after)} untagged manifest(s) remain", file=sys.stderr)
        sys.exit(1)
    else:
        print("All untagged manifests deleted successfully.")


if __name__ == "__main__":
    main()
