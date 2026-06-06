#!/usr/bin/env python3
"""把一组变更文件分类为 docs-only / process-only / release-governance / runtime / unknown。

pr-check 与 build-images 共用本分类器，保证「是否构建镜像」判断一致。

聚合规则（取最保守者）：
    runtime / unknown  > release-governance > process-only > docs-only

用法：
    git diff --name-only <base>...<head> | python scripts/detect_change_scope.py
    python scripts/detect_change_scope.py file1 file2 ...

输出：
    stdout: 单个聚合 scope（docs-only|process-only|release-governance|runtime|unknown）
    若存在 $GITHUB_OUTPUT，则追加 scope=<...> 与 build_needed=<true|false>
"""
from __future__ import annotations

import fnmatch
import os
import sys

# 顺序敏感：自上而下第一个命中的规则决定该文件的 scope。
RULES: list[tuple[str, str]] = [
    # release-governance：发布/部署治理资产（先于 process，避免被 .github/** 笼统吃掉）
    ("release-governance", ".github/workflows/build-images.yml"),
    ("release-governance", ".github/workflows/deploy.yml"),
    ("release-governance", "scripts/check_image_build_source.py"),
    ("release-governance", "scripts/deploy_pull_only.sh"),
    ("release-governance", "lmzj-docs/release-runbook.md"),
    ("release-governance", "lmzj-docs/governance-profile.md"),
    ("release-governance", "lmzj-docs/project-profile.md"),
    # process-only：agent 规则、CI 元、流程脚本（精确文件先于 docs 通配，避免 *.md 误吞）
    ("process-only", "AGENTS.md"),
    ("process-only", "CLAUDE.md"),
    ("process-only", ".claude/*"),
    ("process-only", ".trae/*"),
    ("process-only", ".cursor/*"),
    ("process-only", ".github/ISSUE_TEMPLATE/*"),
    ("process-only", ".github/pull_request_template.md"),
    ("process-only", ".github/copilot-instructions.md"),
    ("process-only", ".github/labeler.yml"),
    ("process-only", ".github/workflows/pr-check.yml"),
    ("process-only", "scripts/pr_process_lint.py"),
    ("process-only", "scripts/detect_change_scope.py"),
    # 兜底：其余 .github/** 均为 CI/process（build/deploy workflow 已在前面优先匹配 release-governance）
    ("process-only", ".github/*"),
    # docs-only
    ("docs-only", "docs/*"),
    ("docs-only", "lmzj-docs/*"),
    ("docs-only", "*.md"),
    ("docs-only", "*.mdx"),
    ("docs-only", "**/*.md"),
    ("docs-only", "**/*.mdx"),
    # runtime：应用源码 / 构建 / 依赖 / 部署清单
    ("runtime", "api/*"),
    ("runtime", "rag/*"),
    ("runtime", "deepdoc/*"),
    ("runtime", "agent/*"),
    ("runtime", "web/*"),
    ("runtime", "sdk/*"),
    ("runtime", "admin/*"),
    ("runtime", "graphrag/*"),
    ("runtime", "mcp/*"),
    ("runtime", "Dockerfile*"),
    ("runtime", "docker/*"),
    ("runtime", "pyproject.toml"),
    ("runtime", "uv.lock"),
    ("runtime", "*.txt"),  # requirements*.txt
    ("runtime", "conf/*"),
]

PRIORITY = {
    "docs-only": 0,
    "process-only": 1,
    "release-governance": 2,
    "runtime": 3,
    "unknown": 4,
}


def classify(path: str) -> str:
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
    if not p:
        return "docs-only"
    for scope, pattern in RULES:
        if fnmatch.fnmatch(p, pattern):
            return scope
        # 目录前缀匹配："api/*" 也覆盖 "api/db/x.py"
        if pattern.endswith("/*") and p.startswith(pattern[:-1]):
            return scope
    return "unknown"


def aggregate(paths: list[str]) -> str:
    if not paths:
        return "docs-only"
    return max((classify(p) for p in paths), key=lambda s: PRIORITY[s])


def main() -> int:
    if len(sys.argv) > 1:
        paths = sys.argv[1:]
    else:
        paths = [line for line in sys.stdin.read().splitlines() if line.strip()]

    scope = aggregate(paths)
    build_needed = scope in ("runtime", "unknown")

    print(scope)

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"scope={scope}\n")
            fh.write(f"build_needed={'true' if build_needed else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
