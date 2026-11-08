# -*- coding: utf-8 -*-
import json
import os
import sys

# 导入同目录的 api 和根目录的 notification
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(project_root)
sys.path.append(current_dir)

import api
try:
    import notification
except ImportError:
    notification = None

def run_account(account):
    """处理单个账号。Returns: (结果消息, token 是否被刷新)"""
    name = account.get("account_name", "默认账号")
    token = account.get("access_token", "")
    refresh_token = account.get("refresh_token", "")
    uid = account.get("uid", "")

    print(f"👉 开始处理账号: {name}")
    token_refreshed = False

    # 尝试检查状态
    code, resp = api.get_checkin_status(token, uid)

    # 如果 Token 失效 (401 或 code 401)，尝试使用 refresh_token 刷新
    if code == 401 or resp.get("code") == 401:
        if refresh_token:
            print("🔄 Access Token 已过期，尝试刷新 Token...")
            ok, ref_data = api.refresh_access_token(refresh_token)
            if ok:
                if ref_data.get("access_token"):
                    account["access_token"] = ref_data["access_token"]
                    token = ref_data["access_token"]
                # 部分实现会同时下发新的 refresh_token（旋转式刷新）
                if ref_data.get("refresh_token"):
                    account["refresh_token"] = ref_data["refresh_token"]
                token_refreshed = True
                print("✅ Token 刷新成功！")
                code, resp = api.get_checkin_status(token, uid)
            else:
                reason = ref_data.get("msg") or ref_data.get("message") or "未知错误"
                return f"❌ 账号 [{name}] Token 刷新失败({reason})，请重新抓取。", False
        else:
            return f"❌ 账号 [{name}] Token 已失效，且未提供 refresh_token。", False

    if code != 200 or resp.get("code") != 0:
        return f"❌ 账号 [{name}] 查询签到状态失败: {resp.get('msg') or resp.get('message')}", token_refreshed

    data = resp.get("data", {})
    # 兼容多种字段命名（实测为 today_checked_in）
    if data.get("today_checked_in") or data.get("today_done") or data.get("todayDone"):
        return f"✅ 账号 [{name}] 今天已经签过到了。", token_refreshed

    # 执行签到
    c_code, c_resp = api.do_daily_checkin(token, uid)
    if c_code == 200 and c_resp.get("code") == 0:
        c_data = c_resp.get("data", {}) or {}
        got = c_data.get("credit", c_data.get("daily_credit", 100))
        return f"🎉 账号 [{name}] 签到成功，获得 {got} 积分！", token_refreshed
    else:
        return f"❌ 账号 [{name}] 签到失败: {c_resp.get('msg') or c_resp.get('message')}", token_refreshed

def persist_config(config):
    """把刷新后的 token 配置回写到 GitHub Actions Secret（需配置 PAT_TOKEN）"""
    try:
        import sync_secret
        ok, msg = sync_secret.update_token_secret(config)
    except Exception as e:
        ok, msg = False, f"回写 Secret 异常: {e}"
    print(("🔐 " if ok else "⚠️  ") + msg)
    return ok

def main():
    token_json_str = os.getenv("WORKBUDDY_TOKEN_JSON")
    if not token_json_str:
        # 兼容单 Token 模式
        single_token = os.getenv("WORKBUDDY_TOKEN")
        if single_token:
            token_json_str = json.dumps({
                "workbuddy": {"accounts": [{"account_name": "单账号", "access_token": single_token}]}
            })
        else:
            print("❌ 错误：未设置 WORKBUDDY_TOKEN_JSON 或 WORKBUDDY_TOKEN 环境变量")
            sys.exit(1)

    try:
        config = json.loads(token_json_str)
        accounts = config.get("workbuddy", {}).get("accounts", [])
    except Exception as e:
        print(f"❌ JSON 配置解析失败: {e}")
        sys.exit(1)

    results = []
    any_refreshed = False
    for acc in accounts:
        msg, refreshed = run_account(acc)
        print(msg)
        results.append(msg)
        any_refreshed = any_refreshed or refreshed

    # 有 token 被刷新过，就把新 token 回写到仓库 Secret，后续运行直接用新 token
    if any_refreshed:
        persist_config(config)
    else:
        print("ℹ️  Token 未发生变化，无需回写")

    summary = "\n".join(results)
    if notification:
        notification.send("WorkBuddy 签到结果", summary)

if __name__ == "__main__":
    main()
