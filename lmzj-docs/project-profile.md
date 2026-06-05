# 项目画像（project-profile）

机器与人共同的事实源。workflow 与脚本中的参数必须与本表一致。

## 基本画像

| 字段 | 值 |
|---|---|
| Project type | `secondary_development` |
| Upstream | `infiniflow/ragflow`（`main` 作上游基线） |
| Repository | `qq281541534/lmzj-ragflow` |
| Visibility | `public` |
| Governance level | `L4`（平台强制门禁，详见 [governance-profile.md](governance-profile.md)） |
| Release source branch | `dev` |
| PR target branch | `dev` |
| Image build branch | `dev` |
| Default branch | `main` |

## 镜像与 registry

| 字段 | 值 |
|---|---|
| Registry | `registry.cn-chengdu.aliyuncs.com`（阿里云 ACR，华为成都） |
| Namespace | `lmzjai` |
| Repository（镜像名） | `ragflow-lmzj`（上游 `ragflow` + `-lmzj` 后缀） |
| 完整镜像引用 | `registry.cn-chengdu.aliyuncs.com/lmzjai/ragflow-lmzj:<full-40-sha>` |
| Tag 规则 | 完整 40 位 commit SHA；**禁** `latest` / 短 SHA |

> registry / namespace / repository 在 GitHub 以 Actions Variables 提供：`ACR_REGISTRY`、`ACR_NAMESPACE`、`ACR_REPOSITORY`。workflow 不硬编码这些值，全部从 vars 读取。

## 分支模型

```text
infiniflow/ragflow  (upstream)
        │  定期同步（独立关口，不与功能开发混合）
        ▼
main  (上游基线镜像，不直接开发)
        │  公司集成基线
        ▼
dev   (公司发布源 = PR target = 镜像构建源)
        ▲
        │  PR（feature/* | fix/* | docs/* | chore/*）
        └── 工作分支从 dev 创建
```

- 功能分支 base：`dev`
- PR target：`dev`
- 生产镜像来源：`dev`（合并后由 build-images workflow 构建完整 SHA 镜像）
- 上游同步：单独关口，把 `infiniflow/ragflow` 同步进 `main`，再按需并入 `dev`，不与功能 PR 混合。

## 验证与回滚参数

| 字段 | 值 / 来源 |
|---|---|
| 生产部署路径 | secret `PROD_DEPLOY_PATH`（生产服务器上的 compose 目录） |
| 生产镜像变量 | compose 通过 `RAGFLOW_IMAGE` 指定完整 SHA 镜像 |
| 健康检查 | 部署后验证生产 health 接口与 public URL（部署时按实际域名填写） |
| 回滚方式 | 把生产 compose 的 `RAGFLOW_IMAGE` 切回 registry 中**上一版完整 SHA 不可变镜像**后重启；回滚源是 registry，不是生产本地历史镜像 |

## 变更分类（决定是否构建镜像）

| Change scope | 示例 | 镜像行为 |
|---|---|---|
| `docs-only` | `*.md`、`docs/**`、`lmzj-docs/**` | 不构建 |
| `process-only` | `AGENTS.md`、`CLAUDE.md`、`.github/**`（模板/workflow 元）、`scripts/**` 流程脚本 | 不构建 |
| `release-governance` | build/deploy workflow、runbook、pull-only 脚本 | 单独变化不构建应用镜像，但严格 review |
| `runtime` | `api/**`、`rag/**`、`deepdoc/**`、`agent/**`、`web/**`、`Dockerfile`、`docker/**` compose、`pyproject.toml`、`uv.lock` 等 | 构建受影响镜像 |
| `unknown` | 分类器无法识别的路径 | 保守构建 |

> 分类逻辑实现见 `scripts/detect_change_scope.py`，pr-check 与 build-images 共用。
