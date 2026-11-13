"""End-to-end smoke test against a running Docker Compose stack (no dependencies).

    docker compose up --build --detach --wait
    python3 scripts/e2e_smoke.py

Walks the main chain from the requirements: register → write and publish →
subscribe by email → confirm with the link from Mailpit → the worker emails
the next essay → unsubscribe → recommendations explain themselves. Exits
non-zero on the first failed step.
"""

# All URLs below are fixed http://127.0.0.1 addresses, so urlopen's scheme warning
# (file:// and friends) does not apply.
# ruff: noqa: S310

import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.request

WEB = "http://127.0.0.1:8080"
API = f"{WEB}/api/v1"
MAILPIT = "http://127.0.0.1:8025/api/v1"
RUN = str(int(time.time()))  # unique names, so the script can run repeatedly


class Browser:
    """A cookie-keeping client that sends the Origin header a browser would."""

    def __init__(self) -> None:
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def call(self, method: str, path: str, body: object = None) -> tuple[int, object]:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(API + path, data=data, method=method)
        request.add_header("Origin", WEB)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(request, timeout=10) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"null")


def check(condition: bool, step: str, detail: object = "") -> None:
    if not condition:
        print(f"FAILED: {step} {detail}")
        sys.exit(1)
    print(f"ok  {step}")


def mailpit_messages() -> list[dict]:
    with urllib.request.urlopen(f"{MAILPIT}/messages", timeout=10) as response:
        return json.loads(response.read())["messages"] or []


def wait_for_mail(to: str, subject_start: str, timeout: float = 40) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for message in mailpit_messages():
            addresses = [a["Address"] for a in message["To"]]
            if to in addresses and message["Subject"].startswith(subject_start):
                url = f"{MAILPIT}/message/{message['ID']}"
                with urllib.request.urlopen(url, timeout=10) as response:
                    return json.loads(response.read())["Text"]
        time.sleep(1)
    check(False, f"email '{subject_start}' to {to} arrived")
    return ""


def token(text: str, kind: str) -> str:
    match = re.search(rf"/newsletter/{kind}#token=([\w-]+)", text)
    check(match is not None, f"{kind} link in email")
    return match.group(1)  # type: ignore[union-attr]


def main() -> None:
    status, health = Browser().call("GET", "/health")
    check(status == 200 and health == {"status": "ok", "database": "ok"}, "API and database up")

    author = Browser()
    handle = f"author_{RUN}"
    status, me = author.call(
        "POST",
        "/auth/register",
        {
            "email": f"{handle}@example.com",
            "password": "correct horse battery staple",
            "handle": handle,
            "display_name": "Smoke Author",
        },
    )
    check(status == 201, "author registers", me)

    def publish(title: str, tags: list[str]) -> dict:
        status, draft = author.call(
            "POST",
            "/articles",
            {"title": title, "summary": "Smoke test.", "body_markdown": "Text.", "tags": tags},
        )
        check(status == 201, f"draft '{title}' created", draft)
        status, article = author.call("POST", f"/articles/{draft['id']}/publish")  # type: ignore[index]
        check(status == 200, f"'{title}' published", article)
        return article  # type: ignore[return-value]

    first = publish(f"First essay {RUN}", ["ethics"])

    fan = f"fan_{RUN}@example.com"
    status, _ = Browser().call(
        "POST",
        f"/authors/{me['id']}/newsletter-subscriptions",
        {"email": fan},  # type: ignore[index]
    )
    check(status == 202, "guest subscribes by email")
    confirm = token(wait_for_mail(fan, "Confirm your Aporia subscription"), "confirm")
    status, confirmed = Browser().call("POST", "/newsletter/confirm", {"token": confirm})
    check(status == 200, "subscription confirmed with the emailed link", confirmed)

    second = publish(f"Second essay {RUN}", ["logic"])
    news = wait_for_mail(fan, "New essay by Smoke Author")
    check(second["slug"] in news, "worker emailed the new essay")
    stop = token(news, "unsubscribe")
    status, _ = Browser().call("POST", "/newsletter/unsubscribe", {"token": stop})
    check(status == 204, "unsubscribed with the link from the email")

    reader = Browser()
    status, _ = reader.call(
        "POST",
        "/auth/register",
        {
            "email": f"reader_{RUN}@example.com",
            "password": "correct horse battery staple",
            "handle": f"reader_{RUN}",
            "display_name": "Smoke Reader",
        },
    )
    check(status == 201, "reader registers")
    reader.call("PUT", "/me/interests", {"tags": ["ethics"]})
    status, feed = reader.call("GET", "/feed/recommended?page_size=50")
    reasons = {i["article"]["id"]: i["reason"] for i in feed["items"]}  # type: ignore[index]
    check(status == 200 and feed["cold_start"] is False, "reader gets a personal feed")  # type: ignore[index]
    check(
        reasons.get(first["id"]) == "You are interested in Ethics",
        "recommendation explains itself",
        reasons.get(first["id"]),
    )
    print("e2e smoke test passed")


if __name__ == "__main__":
    main()
