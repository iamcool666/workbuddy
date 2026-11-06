# -*- coding: utf-8 -*-
"""
将刷新后的 token 配置回写到 GitHub Actions Secret（WORKBUDDY_TOKEN_JSON）。

原理（GitHub 官方要求的加密方式）：
1. GET /repos/{repo}/actions/secrets/public-key  获取仓库公钥
2. 用 PyNaCl SealedBox（libsodium sealed box）加密 Secret 明文
3. PUT /repos/{repo}/actions/secrets/{name}  写入加密结果

仅在以下环境变量齐备时生效（均在 GitHub Actions 运行器上自动可用）：
- GITHUB_REPOSITORY: "owner/repo"（Actions 默认环境变量）
- PAT_TOKEN:          具有 Actions secrets 写权限的细粒度 PAT（作为仓库 Secret 配置）
"""
import base64
import json
import os
import urllib.request
import urllib.error

API_BASE = "https://api.github.com"


def _request(url, method="GET", headers=None, payload=None, timeout=15):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.getcode(), json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"message": f"HTTP {e.code}"}
    except Exception as e:
        return 500, {"message": str(e)}


def update_token_secret(config: dict, secret_name: str = "WORKBUDDY_TOKEN_JSON"):
    """
    把 config（完整 token.json 结构）加密后写入仓库 Secret。

    Returns:
        (ok: bool, message: str)
    """
    repo = os.getenv("GITHUB_REPOSITORY")
    pat = os.getenv("PAT_TOKEN")
    if not repo:
        return False, "未设置 GITHUB_REPOSITORY，跳过回写"
    if not pat:
        return False, "未设置 PAT_TOKEN Secret，无法回写新 token（详见 README）"

    try:
        from nacl.public import PublicKey, SealedBox
    except ImportError:
        return False, "缺少 pynacl（pip install pynacl），无法回写新 token"

    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }

    # 1. 获取仓库公钥
    code, key_data = _request(f"{API_BASE}/repos/{repo}/actions/secrets/public-key", headers=headers)
    if code != 200 or "key" not in key_data or "key_id" not in key_data:
        return False, f"获取仓库公钥失败({code}): {key_data.get('message')}"

    # 2. SealedBox 加密
    plain = json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")
    sealed = SealedBox(PublicKey(base64.b64decode(key_data["key"]))).encrypt(plain)
    encrypted_value = base64.b64encode(sealed).decode("ascii")

    # 3. 写入 Secret
    code, resp = _request(
        f"{API_BASE}/repos/{repo}/actions/secrets/{secret_name}",
        method="PUT",
        headers=headers,
        payload={"encrypted_value": encrypted_value, "key_id": key_data["key_id"]},
    )
    if code in (201, 204):
        return True, f"✅ 新 token 已回写到 Secret {secret_name}"
    return False, f"写入 Secret 失败({code}): {resp.get('message')}"
