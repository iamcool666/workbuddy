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
    name = account.get("account_name", "默认账号")
    token = account.get("access_token", "")
    refresh_token = account.get("refresh_token", "")
    uid = account.get("uid", "")
    
    print(f"👉 开始处理账号: {name}")
    
    # 尝试检查状态
    code, resp = api.get_checkin_status(token, uid)
    
    # 如果 Token 失效 (401 或 code 401)，尝试使用 refresh_token 刷新
    if code == 401 or resp.get("code") == 401:
        if refresh_token:
            print("🔄 Access Token 已过期，尝试刷新 Token...")
            ok, ref_data = api.refresh_access_token(refresh_token)
            if ok:
                token = ref_data.get("access_token", token)
                account["access_token"] = token
                print("✅ Token 刷新成功！")
                code, resp = api.get_checkin_status(token, uid)
            else:
                return f"❌ 账号 [{name}] Token 刷新失败，请重新抓取。"
        else:
            return f"❌ 账号 [{name}] Token 已失效，且未提供 refresh_token。"
            
    if code != 200 or resp.get("code") != 0:
        return f"❌ 账号 [{name}] 查询签到状态失败: {resp.get('message')}"
        
    data = resp.get("data", {})
    if data.get("today_done") or data.get("todayDone"):
        return f"✅ 账号 [{name}] 今天已经签过到了。"
        
    # 执行签到
    c_code, c_resp = api.do_daily_checkin(token, uid)
    if c_code == 200 and c_resp.get("code") == 0:
        got = c_resp.get("data", {}).get("credit", 100)
        return f"🎉 账号 [{name}] 签到成功，获得 {got} 积分！"
    else:
        return f"❌ 账号 [{name}] 签到失败: {c_resp.get('message')}"

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
    for acc in accounts:
        msg = run_account(acc)
        print(msg)
        results.append(msg)
        
    summary = "\n".join(results)
    if notification:
        notification.send("WorkBuddy 签到结果", summary)

if __name__ == "__main__":
    main()
