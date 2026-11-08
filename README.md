# workbuddy
自动签到、消息推送、token自动续期

## 功能
- 每天北京时间 06:17（UTC 22:17）自动签到（GitHub Actions 定时任务）
- Access Token 过期时自动用 refresh_token 续期
- **Token 刷新后自动回写 GitHub Secret**（需配置 `PAT_TOKEN`，见下）
- 签到结果推送到微信（Server酱，可选）

## 必需 Secret（Settings → Secrets and variables → Actions）
| 名称 | 说明 |
|---|---|
| `WORKBUDDY_TOKEN_JSON` | token.json 的完整 JSON 内容（用 `script/workbuddy/import_accounts.py` 从本机客户端提取） |

## 可选 Secret
| 名称 | 说明 |
|---|---|
| `SERVERCHAN_KEY` | Server酱推送 key（https://sct.ftqq.com） |
| `PAT_TOKEN` | 细粒度 PAT，用于 token 刷新后自动回写 `WORKBUDDY_TOKEN_JSON` |

### PAT_TOKEN 配置方法（启用 token 自动续期回写）
1. 打开 https://github.com/settings/personal-access-tokens/new
2. Repository access 选 **Only select repositories → 本仓库**
3. Permissions 给 **Actions secrets: Read and write**（仅此一项，最小权限）
4. 生成后把令牌添加为仓库 Secret `PAT_TOKEN`

配置后：每次运行时若 token 被刷新，新 token 会加密写回 `WORKBUDDY_TOKEN_JSON`，
后续运行直接使用新 token，不再依赖旧的 refresh 链。
未配置 `PAT_TOKEN` 时功能自动降级（刷新仅在当次运行内生效），不影响签到本身。

## 手动触发
Actions → WorkBUDDY Daily Sign → Run workflow

## 本地导入账号
```bash
python script/workbuddy/import_accounts.py --list   # 预览
python script/workbuddy/import_accounts.py          # 导入到 config/token.json
```
