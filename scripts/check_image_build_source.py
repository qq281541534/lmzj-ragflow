#!/usr/bin/env python3
"""镜像构建源校验：确认待构建 commit 来自合并进发布源分支的 PR。

防止有人绕过 PR 直接 push 到 dev 触发生产镜像构建。

用法：
    python scripts/check_image_build_source.py <commit-sha>

环境：
    GITHUB_REPOSITORY  owner/repo（Actions 自动注入）
    RELEASE_SOURCE     发布源分支，默认 dev
    GH_TOKEN / GITHUB_TOKEN  gh CLI 鉴权

判定通过的条件（任一）：
    - 该 commit 关联到 base 为发布源、且 merged 的 PR；或
    - 该 commit 是把某 PR 合并进发布源的 merge commit。

退出码非 0 表示校验失败（不应构建镜像）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys


def gh_api(path: str) -> object:
    proc = subprocess.run(
        ["gh", "api", "-H", "Accept: application/vnd.github+json", path],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh api {path} 失败: {proc.stderr.strip()}")
    return json.loads(proc.stdout or "null")


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: check_image_build_source.py <commit-sha>", file=sys.stderr)
        return 2

    sha = sys.argv[1].strip()
    repo = os.environ["GITHUB_REPOSITORY"]
    release_source = os.environ.get("RELEASE_SOURCE", "dev")

    pulls = gh_api(f"repos/{repo}/commits/{sha}/pulls")
    if not isinstance(pulls, list):
        pulls = []

    for pr in pulls:
        merged = pr.get("merged_at") is not None
        base_ref = (pr.get("base") or {}).get("ref")
        if merged and base_ref == release_source:
            print(
                f"OK: commit {sha[:12]} 来自已合并 PR #{pr.get('number')} (base={base_ref})。"
            )
            return 0

    print(
        f"拒绝构建：commit {sha[:12]} 未关联到合并进 `{release_source}` 的 PR。"
        f" 生产镜像只能从经 PR 合并的提交构建。",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
