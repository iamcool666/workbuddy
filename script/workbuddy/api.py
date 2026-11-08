# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.error

CHECKIN_STATUS_URL = "https://www.codebuddy.cn/v2/billing/meter/checkin-activity-status"
DAILY_CHECKIN_URL = "https://www.codebuddy.cn/v2/billing/meter/daily-checkin"
REFRESH_TOKEN_URL = "https://www.codebuddy.cn/v2/plugin/auth/token/refresh"

def http_post(url, headers, payload=None):
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.getcode(), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except:
            return e.code, {"code": e.code, "message": "HTTP Error"}
    except Exception as e:
        return 500, {"code": 500, "message": str(e)}

def refresh_access_token(refresh_token):
    """刷新 access token。

    实测该接口的 refresh token 通过请求头 X-Refresh-Token 传递（body 为空），
    返回字段为 camelCase：accessToken / refreshToken / expiresIn / refreshExpiresIn。
    这里统一转成 snake_case 交给上层使用。
    """
    headers = {
        "Content-Type": "application/json",
        "X-Refresh-Token": refresh_token,
        "X-Auth-Refresh-Source": "plugin",
    }
    code, resp = http_post(REFRESH_TOKEN_URL, headers, {})
    if code == 200 and resp.get("code") == 0:
        data = resp.get("data") or {}
        return True, {
            "access_token": data.get("accessToken") or data.get("access_token"),
            "refresh_token": data.get("refreshToken") or data.get("refresh_token"),
            "expires_in": data.get("expiresIn"),
            "refresh_expires_in": data.get("refreshExpiresIn"),
        }
    return False, resp

def get_checkin_status(access_token, uid=""):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    if uid:
        headers["X-User-Id"] = str(uid)
    return http_post(CHECKIN_STATUS_URL, headers)

def do_daily_checkin(access_token, uid=""):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    if uid:
        headers["X-User-Id"] = str(uid)
    return http_post(DAILY_CHECKIN_URL, headers)
