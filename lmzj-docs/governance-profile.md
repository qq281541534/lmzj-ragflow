# 治理画像（governance-profile）

仓库 `qq281541534/lmzj-ragflow` 为 **public** 仓库，治理级别 **L4（平台强制门禁）**。public 仓库不得只靠补偿护栏，必须由人类在 GitHub UI 配置平台门禁；AI 只生成 workflow 与脚本。

## 治理级别判定

| 维度 | 值 | 结论 |
|---|---|---|
| Project type | `secondary_development` | 决定分支/发布参数，不降低门禁 |
| Visibility | `public` | 治理级别强制 `L4` |
| Governance level | `L4` | platform-enforced + CI 补偿同时存在 |

## 需人类在 GitHub 配置（AI 无法代办）

> 现状提示：截至接入时 `gh api repos/qq281541534/lmzj-ragflow/environments` 返回 `total_count: 0`，repo 级 secrets/variables 为空。下列配置需在 **本 fork** 补齐后，build / deploy 关口方可生效。

### 1. `production` Environment + Required reviewers

- 创建 environment：`production`
- 开启 **Required reviewers**（至少 1 名人类），用于 deploy workflow 的人工部署确认门
- 可选：deployment branch 限制

### 2. Environment secrets（`production`）

| Secret | 用途 |
|---|---|
| `ALIYUN_ACR_USERNAME` | ACR 登录用户名 |
| `ALIYUN_ACR_PASSWORD` | ACR 登录密码 / token |
| `PROD_SSH_HOST` | 生产服务器地址 |
| `PROD_SSH_PORT` | SSH 端口 |
| `PROD_SSH_USER` | SSH 用户 |
| `PROD_SSH_KEY` | SSH 私钥 |
| `PROD_DEPLOY_PATH` | 生产 compose 部署目录 |

### 3. Actions variables（repo 或 `production` environment）

| Variable | 值 |
|---|---|
| `ACR_REGISTRY` | `registry.cn-chengdu.aliyuncs.com` |
| `ACR_NAMESPACE` | `lmzjai` |
| `ACR_REPOSITORY` | `ragflow-lmzj` |

### 4. Branch protection / ruleset（`dev` 与 `main`）

- Require a pull request before merging
- Require status checks to pass：绑定 `pr-check` 的稳定 final check（job 名 `pr-check-result`）
- 禁止直接 push 到 `dev` / `main`
- Prevent self-review（require review from someone other than the author）
- 可选：require linear history

## CI 补偿护栏（AI 已生成）

平台门禁之外，workflow 层补偿（即便平台配置缺失也提供基本保障）：

| 护栏 | 实现 |
|---|---|
| PR process lint | `scripts/pr_process_lint.py` + `pr-check.yml`：校验 `Refs #<issue>`、验证 / 部署影响 / 回滚段落，禁 auto-close 关键词 |
| Change scope 检测 | `scripts/detect_change_scope.py`：分类 docs / process / release-governance / runtime / unknown |
| Image source check | `scripts/check_image_build_source.py`：构建前确认 `dev` HEAD commit 来自已合并 PR |
| Non-runtime skip guard | `build-images.yml`：non-runtime 变更不 login / build / push |
| Deploy input validation | `deploy.yml`：只接受完整 40 位 SHA，拒绝 `latest` / 短 SHA |
| Manual deploy | `deploy.yml` 仅 `workflow_dispatch` + `production` environment 审批 |

## 硬规则映射

- PR 合并 ≠ 部署：合并只触发 build-images，不触发 deploy。
- 部署仅人工 `workflow_dispatch` 指定完整 SHA 后执行。
- 生产服务器只 pull，不 build。
- Issue 不被 PR 自动关闭，验证 + 回滚证据齐全且人类明确指令后关闭。
