# 发布手册（release-runbook）

把一次变更从 Issue 推进到可验证、可回滚的生产发布。每个关口产出证据。

## 发布状态机

```text
issue_open
  -> branch_ready                      # 从 dev 创建工作分支
  -> pr_open                           # PR target dev，Refs #<issue>
  -> pr_merged                         # 人工合并，记录 merge SHA
  -> image_build_resolved             # build-images 完成，记录完整 SHA 镜像 tag
  -> pre_deploy_artifact_reviewed     # 镜像体积 / digest / 磁盘 / 依赖 profile 审查
  -> production_manifest_reviewed     # 生产 compose 使用不可变镜像 + 正确 secrets/volumes/ports/health
  -> deploy_approved                  # 人类明确确认具体完整 SHA
  -> deploy_run_completed             # deploy workflow 拿到 final conclusion
  -> deployed
  -> verified                         # 生产 health + public URL 验证
  -> rollback_ready                   # 上一版不可变 SHA 镜像可回滚
  -> issue_closed_after_verified_release  # 人类明确指令后关闭
  -> ai_short_lived_branch_cleaned    # 清理 AI 短期工作分支
```

**AI 不得把 `pr_merged` 当作 done。**

## 日常交付步骤

### 1. 创建 / 复用 Issue
中文标题描述业务意图。

### 2. 从 dev 创建工作分支
```bash
git fetch origin dev
git switch -c <feat|fix|docs|chore>/<slug> origin/dev
```

### 3. 实现与验证
- 变更范围最小化，复用既有模式。
- 跑相关检查：`ruff check`、`ruff format`、`uv run pytest`（按改动范围）、前端 `npm run lint` / `npm run test`。

### 4. PR
- target `dev`，正文用 `Refs #<issue>`（禁 `Closes/Fixes/Resolves`）。
- 必含：摘要、变更范围、验证命令与结果、部署影响、新增 secrets/vars、迁移影响、回滚方案。
- 等待 `pr-check` 通过。

### 5. 人工合并后
```bash
git fetch origin dev
git switch dev
git pull --ff-only origin dev
git status --short --branch   # 确认本地 HEAD 含 merge commit
git log -1 --oneline
```
- 观察该 merge SHA 的 `build-images` run，记录完整 40 位 SHA 镜像 tag。

### 6. 部署前审查
- 镜像 size 与 digest。
- 生产机磁盘余量是否够 pull / 解压 / 启动。
- dependency profile 是否误带 `all` / `full` / `gpu` / `cuda`。
- 生产 compose 是否用不可变镜像、正确 secrets / volumes / ports / health。

### 7. 人工确认部署
- 人类明确给出要部署的完整 40 位 SHA。
- 触发 `deploy` workflow（`workflow_dispatch`），输入该 SHA。
- `production` environment required reviewer 审批后执行。

### 8. 部署执行（pull-only）
deploy workflow 通过 SSH 在生产执行：
- ACR 登录、`docker pull` 指定完整 SHA 镜像。
- 更新生产 compose 的 `RAGFLOW_IMAGE` 为该镜像。
- `docker compose up -d`，等待 health。
- 生产服务器**不构建**镜像。

### 9. 验证与回滚准备
- 验证 health 接口 + public URL。
- 记录实际 deployed image tag。
- 记录上一版不可变 SHA 镜像的回滚方式。
- 部署后镜像清理只作用于本项目旧镜像，**不**清理 volume 或其他项目镜像。

### 10. 关闭 Issue
- 生产验证 + 回滚准备证据齐全后保持 open。
- 收到人类明确关闭指令后，AI 关闭 Issue 并附证据摘要。

### 11. 清理 AI 短期分支
- 仅在 PR 已合并、`dev` 已同步、工作区干净后。
- 本地：`git branch -d <branch>`（安全删除）。
- 远端 PR 分支默认删除；若 GitHub 已自动删除记为 already gone。
- **禁删** `main` / `dev` / `release/*` / `hotfix/*` / `upstream/*` / 未合并 / 仍有 open PR / 归属不清 / 人类要求保留的分支。

## 回滚

```bash
# 在生产 compose 目录
export RAGFLOW_IMAGE=registry.cn-chengdu.aliyuncs.com/lmzjai/ragflow-lmzj:<上一版完整SHA>
docker pull "$RAGFLOW_IMAGE"
docker compose up -d
```
回滚源永远是 registry 中的不可变完整 SHA 镜像，不依赖生产本地历史镜像。不要用 `docker system prune -a --volumes` 清理。

## 发布证据包模板

```markdown
## 发布证据 — Issue #<n>

- Issue: #<n>
- PR: #<m>（merged，merge SHA `<40-sha>`）
- 镜像: registry.cn-chengdu.aliyuncs.com/lmzjai/ragflow-lmzj:<40-sha>
- 镜像 digest / size: <...>
- build-images run: <url>（conclusion success）
- 部署前审查: 磁盘 <剩余>，dependency profile <...>，compose 审查通过
- 部署确认人: <人类>，部署 SHA: <40-sha>
- deploy run: <url>（conclusion success）
- 验证: health <ok>，public URL <ok>
- 回滚: 上一版镜像 :<prev-40-sha>
- Issue 关闭指令: <人类原话/链接>
```

## 首次生产部署实录（2026-06-06，手动 provision）

首次部署是**手动 SSH provision**（合理：全新国内服务器、本地带宽仅 2M 不适合 self-hosted runner）。部署的镜像仍是受治理的 ACR 不可变构建。后续镜像更新走治理版 `deploy.yml`（`workflow_dispatch` + `production` 审批 + pull-only）。

### 服务器与部署坐标

| 项 | 值 |
|---|---|
| 主机 | `ubuntu@118.145.161.32`（4 vCPU / 8GB / 40G；SSH 端口非 22，已自定义） |
| 部署目录 | `~/software/lmzj-ragflow`（= `PROD_DEPLOY_PATH`，需与 secret 一致） |
| 域名 | `edu.lmzjai.com` → `118.145.161.32` |
| 应用镜像 | `registry.cn-chengdu.aliyuncs.com/lmzjai/ragflow-lmzj:a3a9cac419df89f25a1c881c04abcfe20e21d555` |
| 文档引擎 | **infinity**（8GB 内存选轻量引擎，非默认 ES） |

### 关键决策与配置（写入服务器 `.env`，原始备份 `.env.orig`）

- `DOC_ENGINE=infinity`、`DEVICE=cpu` → `COMPOSE_PROFILES` 自解析为 `infinity,cpu`。
- `MEM_LIMIT=2147483648`（2G，给 infinity）。
- `RAGFLOW_IMAGE=` 上述 ACR 完整 SHA 镜像。
- `REGISTER_ENABLED=0`（建好管理员后关闭公开注册）。
- 安全端口绑定：`mysql/minio/redis/infinity/9380/9381` 全部 host 段写 `127.0.0.1:`，公网仅 `80/443`。已从服务器自测公网 IP 验证基础设施端口不可达。
- `MYSQL_PASSWORD/MINIO_PASSWORD/REDIS_PASSWORD` 改为强随机（存服务器 `.env`）。

### 国内拉镜像方案（重要）

- 阿里云**个人版加速器对 Docker Hub 返回 403**（已停服）；公共加速源大 blob TLS 抖动 → 均不可靠。
- 最终方案：用 `.github/workflows/mirror-base-images.yml`（GitHub 托管 runner 直连 Docker Hub）把 4 个基础镜像搬到自有 ACR：
  - `lmzjai/mysql:8.0.39`、`lmzjai/valkey:8`、`lmzjai/minio:RELEASE.2026-03-25T00-00-00Z`、`lmzjai/infinity:v0.7.0`
- 服务器从 ACR 拉取后 **retag 回原始名**（`docker tag <acr>/mysql:8.0.39 mysql:8.0.39` …），vanilla compose 无需改动即可使用。**生产零外部镜像依赖。**

> ⚠️ **base 镜像版本升级时必须先 mirror**（已知坑）：日常 `deploy.yml` 只拉应用镜像（ragflow-lmzj）；base 镜像（mysql/valkey/minio/infinity）沿用服务器本地副本。当 RAGFlow 升级带来**新的 base 镜像版本**（如 `mysql:8.0.40`、`infinity:vX`）时，`docker compose up -d` 会尝试从 **Docker Hub** 拉新 base → **国内拉不动 → 部署卡住/失败**。
>
> 处理流程：升级前先 (1) 更新 `mirror-base-images.yml` 里的版本并手动触发，把新 base 搬到 ACR；(2) 在服务器 `docker pull <acr>/<name>:<newtag> && docker tag` 回原始名；(3) 再走治理版 `deploy.yml` 部署应用镜像。判断是否涉及 base 升级：对比新版 `docker/docker-compose-base.yml` 的 `image:` 行与服务器本地已有 tag。

### TLS（HTTPS）

- 证书（Nginx 格式）：`fullchain.pem` + `privkey.pem` 放 `~/software/lmzj-ragflow/nginx/ssl/`。
- `nginx/ragflow.conf` 用 RAGFlow 自带 https 模板（80→301→443，证书路径 `/etc/nginx/ssl/`，`server_name edu.lmzjai.com`）。
- 通过 `docker-compose.override.yml` 追加挂载（不改原 compose，治理 deploy 自动继承）：
  ```yaml
  services:
    ragflow-cpu:
      volumes:
        - ./nginx/ragflow.conf:/etc/nginx/conf.d/ragflow.conf
        - ./nginx/ssl:/etc/nginx/ssl
  ```
- 注意：`docker compose` 命令**不要带 `-f docker-compose.yml`**，否则忽略 override；用 `docker compose up -d`（与 `deploy_pull_only.sh` 一致）。

### 运维注意

- 内存固定 8GB（不可扩），已加 4G swap（`vm.swappiness=10`）作 OOM 安全垫；重负载需监控。
- 云安全组仅放 `80/443` + 自定义 SSH 端口。
- 证书有效期至 `2026-09-04`，到期前需续期并替换 `nginx/ssl/` 后 `nginx -s reload`。
- 待办：HTTP/2、HSTS 等可后续在 nginx 加强。
