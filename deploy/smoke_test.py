"""
Smoke test for a running deployment (issue #20). Standard library only.

Usage:
  SMOKE_USERNAME=<admin username> SMOKE_PASSWORD=<password> python deploy/smoke_test.py https://example.org
  python deploy/smoke_test.py https://localhost --insecure    (local test: Caddy's own certificate)

Checks the app and a deep link, the session cookie flags, /api/health, /api/me before and after signing in,
the latest detection run, signing out, the login rate limit (the 6th failed attempt in a minute returns 429)
and that a foreign origin gets no CORS header. The password is read from the environment and never printed.
The rate limit check waits one minute first, so the earlier sign in does not count towards it.
"""

import argparse
import http.cookiejar
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

FOREIGN_ORIGIN = "https://foreign.example"
RATE_LIMIT = 5
RATE_WINDOW_SECONDS = 61


class Client:
    def __init__(self, base, insecure):
        self.base = base.rstrip("/")
        context = ssl._create_unverified_context() if insecure else ssl.create_default_context()
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context),
                                                  urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, method, path, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method, headers={
            "Accept": "application/json, text/html", **({"Content-Type": "application/json"} if data else {}),
            **(headers or {})})
        try:
            with self.opener.open(request, timeout=30) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers, error.read()


class Report:
    def __init__(self):
        self.failures = 0

    def check(self, name, ok, detail=""):
        print(f"{'PASS' if ok else 'FAIL'}  {name}{f' ({detail})' if detail and not ok else ''}")
        self.failures += 0 if ok else 1
        return ok


def is_app(status, body):
    return status == 200 and b'<div id="root"></div>' in body


def main(argv=None):
    parser = argparse.ArgumentParser(description="Smoke test a running SalesMesh deployment.")
    parser.add_argument("base_url", help="for example https://example.org")
    parser.add_argument("--insecure", action="store_true", help="skip certificate checks (local tests only)")
    args = parser.parse_args(argv)
    username, password = os.environ.get("SMOKE_USERNAME"), os.environ.get("SMOKE_PASSWORD")
    if not username or not password:
        sys.exit("Set SMOKE_USERNAME and SMOKE_PASSWORD (an existing account) in the environment")

    client, report = Client(args.base_url, args.insecure), Report()

    status, _, body = client.request("GET", "/")
    report.check("GET / returns the app", is_app(status, body), f"status {status}")
    status, _, body = client.request("GET", "/threat-intelligence")
    report.check("a deep link returns the app", is_app(status, body), f"status {status}")

    status, _, body = client.request("GET", "/api/health")
    report.check("GET /api/health returns ok", status == 200 and json.loads(body or b"{}").get("status") == "ok",
                 f"status {status}")
    status, _, _ = client.request("GET", "/api/me")
    report.check("GET /api/me without a session returns 401", status == 401, f"status {status}")

    status, headers, _ = client.request("POST", "/api/login", {"username": username, "password": password})
    report.check("sign in works", status == 200, f"status {status}")
    cookie = next((c for c in headers.get_all("Set-Cookie") or [] if c.startswith("session=")), "")
    flags = {part.strip().lower() for part in cookie.split(";")[1:]}
    report.check("the session cookie is Secure and HttpOnly", "secure" in flags and "httponly" in flags,
                 "flags " + ", ".join(sorted(f.split("=")[0] for f in flags)))
    status, _, body = client.request("GET", "/api/me")
    report.check("GET /api/me with the session returns 200", status == 200, f"status {status}")
    status, _, body = client.request("GET", "/api/detection-runs/latest")
    run = json.loads(body or b"{}").get("run") if status == 200 else None
    report.check("GET /api/detection-runs/latest returns a run", bool(run),
                 f"status {status}" if status != 200 else "no run yet")
    status, _, _ = client.request("POST", "/api/logout")
    report.check("sign out works", status == 200, f"status {status}")
    status, _, _ = client.request("GET", "/api/me")
    report.check("GET /api/me after signing out returns 401", status == 401, f"status {status}")

    for method in ("GET", "OPTIONS"):
        _, headers, _ = client.request(method, "/api/health", headers={
            "Origin": FOREIGN_ORIGIN, "Access-Control-Request-Method": "GET"})
        report.check(f"{method} from a foreign origin gets no Access-Control-Allow-Origin",
                     "Access-Control-Allow-Origin" not in headers, headers.get("Access-Control-Allow-Origin", ""))

    print(f"Waiting {RATE_WINDOW_SECONDS} seconds so the sign in above leaves the rate limit window...")
    time.sleep(RATE_WINDOW_SECONDS)
    wrong = {"username": "smoke_test_unknown_user", "password": "not the password"}
    statuses = [client.request("POST", "/api/login", wrong)[0] for _ in range(RATE_LIMIT + 1)]
    report.check("the 6th failed sign in within a minute returns 429",
                 statuses[:RATE_LIMIT] == [401] * RATE_LIMIT and statuses[RATE_LIMIT] == 429,
                 "statuses " + ", ".join(map(str, statuses)))

    print(f"{'All checks passed' if not report.failures else f'{report.failures} checks failed'}.")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
