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
