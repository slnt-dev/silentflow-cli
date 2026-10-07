# silentflow-cli

[SilentFlow](https://slnt.dev) 图床的命令行客户端：上传图片、列出文件、查看用量、管理给 AI Agent 用的受限 Key。

- **零依赖**：单个 Python 文件，只用标准库，Python 3.9+ 即可运行；
- **输出 JSON**：方便脚本、CI 和 AI 编程助手（Claude Code、Cursor、Codex 等）直接解析；
- **默认安全**：Key 只从环境变量或配置文件读取，不接受命令行参数；默认校验 TLS；删除需要显式确认。

> 还没有 Key？在 <https://slnt.dev/free> 免费领取（500 MB 存储，每月 1 GB 流量，不用付款）。

## 安装

```bash
git clone https://github.com/slnt-dev/silentflow-cli.git
cd silentflow-cli
python3 scripts/silentflow.py --version
```

可以给它起个别名：

```bash
alias silentflow="python3 $PWD/scripts/silentflow.py"
```

## 配置 Key

二选一（环境变量优先）：

```bash
export SILENTFLOW_API_KEY='sk_...'
```

或写入 `~/.config/silentflow/config.json`，并把权限设成只有自己可读：

```json
{ "api_key": "sk_..." }
```

```bash
chmod 600 ~/.config/silentflow/config.json
```

不要把 Key 写进命令行参数、提交到仓库或贴到聊天里。

## 用法

```bash
# 上传一张本地图片，返回公开链接
silentflow upload ./screenshot.png

# 列出文件 / 查看用量 / 查看账号
silentflow list --limit 20
silentflow usage
silentflow me

# 删除：先 dry-run 确认目标，再加 --yes 执行
silentflow delete '2026/10/07/abc.png' --dry-run
silentflow delete '2026/10/07/abc.png' --yes
```

上传成功后请使用返回结果里的 `url`，不要根据 API 域名自己拼接链接。

### 给 AI Agent 或 CI 用的受限 Key

用账号主密钥（`sk_...`）签发只有部分权限的 `sf_agent_...` Key，比如只能上传、不能删除：

```bash
silentflow keys create --name ci-uploader --scope files:write
silentflow keys list
silentflow keys revoke 12
```

可用权限：`files:read`、`files:write`、`files:delete`。新 Key 只在创建时显示一次。

## 作为 AI Agent Skill 使用

仓库根目录的 [`SKILL.md`](SKILL.md) 是给 AI 编程助手看的使用说明。把整个目录放进你的 Agent 的 skills 目录即可，例如：

```bash
git clone https://github.com/slnt-dev/silentflow-cli.git ~/.claude/skills/silentflow-client
```

## 其他选项

| 选项 / 变量 | 说明 |
| --- | --- |
| `--api-url` / `SILENTFLOW_API_URL` | 自定义 API 地址，默认 `https://slnt.dev` |
| `--config` | 指定配置文件路径 |
| `--pretty` | 格式化输出 JSON |
| `--insecure` | 跳过 TLS 校验，仅在你明确接受风险时使用 |

完整 API 文档：<https://slnt.dev/developers> · OpenAPI：<https://slnt.dev/openapi.json>

## 开发

```bash
python3 -m pytest tests
```

## 相关项目

- [picgo-plugin-silentflow](https://github.com/slnt-dev/picgo-plugin-silentflow)：PicGo 插件，配合 Typora / Obsidian 粘贴即传

## License

MIT
