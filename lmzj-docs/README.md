# lmzj-docs

公司二开（secondary_development）专属流程与运维文档。**与上游 Docusaurus 站点 `docs/` 完全隔离，禁止把公司流程文档写入 `docs/`。**

本目录承载 RAGFlow fork（`qq281541534/lmzj-ragflow`）的 AI Issue-to-Production 交付链路文档。

## 索引

- [project-profile.md](project-profile.md) — 项目画像：项目类型、发布源、PR target、registry、镜像命名、验证、回滚参数。
- [governance-profile.md](governance-profile.md) — 治理画像：仓库可见性、L4 平台门禁、需人类配置的 environment / secrets / variables / branch protection 清单。
- [release-runbook.md](release-runbook.md) — 发布手册：发布状态机、构建 / 部署 / 验证 / 回滚步骤、发布证据模板。

## 交付链路（概览）

```text
Issue
  -> 从 dev 创建分支
  -> AI 实现与验证
  -> PR（Refs #<issue>，target dev）
  -> CI（pr-check）
  -> 人工合并
  -> ACR 不可变镜像（完整 40 位 SHA）
  -> 人工明确确认生产部署
  -> 生产服务器 pull-only
  -> 生产验证与回滚准备
  -> 人类明确指令后关闭 Issue
```

## 硬规则（摘要）

1. 不直接提交 `dev` / `main`，一律走 PR。
2. PR 合并 ≠ 生产部署；无人类明确确认不触发部署。
3. 生产镜像必须用完整 40 位 commit SHA，禁 `latest` / 短 SHA。
4. 生产服务器只拉取镜像，不在生产构建。
5. non-runtime 变更（docs / process / 流程脚本）不构建或 push 生产镜像。
6. PR 用 `Refs #<issue>`，禁 `Closes` / `Fixes` / `Resolves` 自动关闭关键词。
7. Issue 仅在生产验证 + 回滚准备证据齐全、且收到人类明确指令后关闭。
