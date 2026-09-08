#!/usr/bin/env python3
"""Small standard-library CLI for exercising R2D2 local authentication."""

import argparse
import getpass
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

API_URL = os.getenv("R2D2_API_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN_FILE = Path(
    os.getenv("R2D2_TOKEN_FILE", str(Path.home() / ".config/r2d2/tokens.json"))
)


def request(method: str, path: str, payload=None, access_token: str | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    try:
        with urllib.request.urlopen(
            urllib.request.Request(
                f"{API_URL}{path}", data=data, headers=headers, method=method
            )
        ) as response:
            body = response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise SystemExit(f"API returned {exc.code}: {detail}") from exc


def load_tokens() -> dict:
    if not TOKEN_FILE.exists():
        raise SystemExit("Not logged in. Run `r2d2_cli.py login` first.")
    return json.loads(TOKEN_FILE.read_text())


def save_tokens(tokens: dict) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens))
    TOKEN_FILE.chmod(0o600)


def register(args) -> None:
    result = request(
        "POST",
        "/auth/register",
        {
            "username": args.username,
            "email": args.email,
            "password": getpass.getpass("Password: "),
        },
    )
    print(f"Registered {result['email']}")


def login(args) -> None:
    tokens = request(
        "POST",
        "/auth/login",
        {
            "email": args.email,
            "password": getpass.getpass("Password: "),
            "client_type": "cli",
        },
    )
    save_tokens(tokens)
    print(f"Logged in as {args.email}")


def me(_args) -> None:
    tokens = load_tokens()
    print(
        json.dumps(
            request("GET", "/auth/me", access_token=tokens["access_token"]), indent=2
        )
    )


def refresh(_args) -> None:
    tokens = load_tokens()
    replacement = request(
        "POST", "/auth/refresh", {"refresh_token": tokens["refresh_token"]}
    )
    save_tokens(replacement)
    print("Session refreshed")


def logout(_args) -> None:
    tokens = load_tokens()
    request("POST", "/auth/logout", {"refresh_token": tokens["refresh_token"]})
    TOKEN_FILE.unlink(missing_ok=True)
    print("Logged out")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(required=True)
    register_command = commands.add_parser("register")
    register_command.add_argument("--username", required=True)
    register_command.add_argument("--email", required=True)
    register_command.set_defaults(handler=register)
    login_command = commands.add_parser("login")
    login_command.add_argument("--email", required=True)
    login_command.set_defaults(handler=login)
    commands.add_parser("me").set_defaults(handler=me)
    commands.add_parser("refresh").set_defaults(handler=refresh)
    commands.add_parser("logout").set_defaults(handler=logout)
    return result


if __name__ == "__main__":
    arguments = parser().parse_args()
    arguments.handler(arguments)
