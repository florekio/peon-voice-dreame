"""Dreame cloud API client.

Handles authentication and device communication via the Dreame Home cloud,
which is separate from Xiaomi's Mi Home cloud.
"""

import hashlib
import json
import ssl
import urllib.parse
import urllib.request
import urllib.error
from base64 import b64encode

# OAuth credentials (from the Dreame Home app)
CLIENT_ID = "dreame_appv1"
CLIENT_SECRET = "AP^dv@z@SQYVxN88"
PASSWORD_SALT = "RAylYC%fmSKp7%Tq"

REGIONS = {
    "eu": "Europe",
    "us": "United States",
    "cn": "China",
    "sg": "Singapore / Asia-Pacific",
    "ru": "Russia",
    "kr": "South Korea",
}

_basic_auth = b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()


def _ssl_ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_ctx = _ssl_ctx()


def _post(url, data, headers=None, is_json=False):
    """Make an HTTP POST request."""
    hdrs = {"Authorization": f"Basic {_basic_auth}"}
    if headers:
        hdrs.update(headers)

    if is_json:
        body = json.dumps(data).encode()
        hdrs["Content-Type"] = "application/json"
    else:
        body = urllib.parse.urlencode(data).encode()
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(url, data=body, headers=hdrs)
    try:
        with urllib.request.urlopen(req, context=_ctx) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode(errors="replace")
        try:
            error_json = json.loads(error_body)
            raise RuntimeError(f"HTTP {e.code}: {error_json}") from None
        except json.JSONDecodeError:
            raise RuntimeError(f"HTTP {e.code}: {error_body[:500]}") from None


def _base_url(region):
    return f"https://{region}.iot.dreame.tech:13267"


def login(username, password, region="eu"):
    """Authenticate with Dreame cloud. Returns session dict."""
    salted = password + PASSWORD_SALT
    pw_hash = hashlib.md5(salted.encode()).hexdigest()

    url = f"{_base_url(region)}/dreame-auth/oauth/token"
    data = {
        "grant_type": "password",
        "scope": "all",
        "platform": "IOS",
        "type": "account",
        "username": username,
        "password": pw_hash,
    }

    login_headers = {"Tenant-Id": "000000"}
    resp = _post(url, data, headers=login_headers)

    if "access_token" not in resp:
        raise RuntimeError(f"Login failed: {resp}")

    return {
        "access_token": resp["access_token"],
        "refresh_token": resp.get("refresh_token"),
        "uid": resp.get("uid"),
        "tenant_id": resp.get("tenant_id", "000000"),
        "region": region,
    }


def _auth_headers(session):
    return {
        "Dreame-Auth": session["access_token"],
        "Tenant-Id": session.get("tenant_id", "000000"),
    }


def get_devices(session):
    """List all devices on the account. Returns list of device dicts."""
    region = session["region"]
    url = f"{_base_url(region)}/dreame-user-iot/iotuserbind/device/listV2"

    resp = _post(url, {}, headers=_auth_headers(session), is_json=True)

    if not resp.get("success"):
        raise RuntimeError(f"Failed to get devices: {resp}")

    records = resp.get("data", {}).get("page", {}).get("records", [])
    return records


def get_device_info(session, did):
    """Get detailed info for a specific device."""
    region = session["region"]
    url = f"{_base_url(region)}/dreame-user-iot/iotuserbind/device/info"

    resp = _post(url, {"did": did}, headers=_auth_headers(session), is_json=True)
    return resp.get("data", resp)


def send_command(session, did, bind_domain, method, params):
    """Send a command to a device via the Dreame cloud.

    bind_domain: from the device's bindDomain field (e.g. 'mqtts-eu-10000.iot.dreame.tech:13285')
    """
    region = session["region"]

    # Extract host number from bind domain (e.g. "10000" from "mqtts-eu-10000.iot.dreame.tech:13285")
    try:
        host_part = bind_domain.split(".")[0]  # "mqtts-eu-10000"
        host_num = host_part.split("-")[-1]     # "10000"
    except (IndexError, AttributeError):
        host_num = "10000"

    url = f"{_base_url(region)}/dreame-iot-com-{host_num}/device/sendCommand"

    payload = {
        "did": did,
        "id": 1,
        "data": {
            "did": did,
            "id": 1,
            "method": method,
            "params": params,
        },
    }

    resp = _post(url, payload, headers=_auth_headers(session), is_json=True)
    return resp
