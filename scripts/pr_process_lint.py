#!/usr/bin/env python3
"""PR 正文流程校验（process lint）。

强制：
  1. 必含 `Refs #<issue>`（关联但不自动关闭 Issue）。
  2. 禁用 auto-close 关键词：Closes/Close/Closed、Fixes/Fix/Fixed、Resolves/Resolve/Resolved + #<n>。
  3. 必含验证、部署影响、回滚三个段落标题（大小写不敏感，中英任一）。

PR 正文来源（按优先级）：
  - 环境变量 PR_BODY
  - argv[1] 指定的文件路径

退出码非 0 表示校验失败。
"""
from __future__ import annotations

import os
import re
import sys

AUTO_CLOSE = re.compile(
    r"\b(clos(e|es|ed)|fix(es|ed)?|resolv(e|es|ed))\b\s*:?\s*#\d+",
    re.IGNORECASE,
)
REFS = re.compile(r"\bRefs\s+#\d+", re.IGNORECASE)

# 每组任一关键词命中即视为该段落存在。
REQUIRED_SECTIONS: list[tuple[str, list[str]]] = [
    ("验证 / verification", ["验证", "verification", "verify", "test result", "测试结果"]),
    ("部署影响 / deployment impact", ["部署影响", "部署", "deployment impact", "deploy impact", "deployment"]),
    ("回滚 / rollback", ["回滚", "rollback", "roll back"]),
]


def load_body() -> str:
    body = os.environ.get("PR_BODY")
    if body is not None:
        return body
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as fh:
            return fh.read()
    return sys.stdin.read()


def main() -> int:
    body = load_body()
    errors: list[str] = []

    if not REFS.search(body):
        errors.append("缺少 `Refs #<issue>` 关联（PR 必须引用 Issue，且不得自动关闭）。")

    bad = AUTO_CLOSE.search(body)
    if bad:
        errors.append(
            f"检测到 auto-close 关键词 `{bad.group(0)}`：PR 不得用 Closes/Fixes/Resolves 自动关闭 Issue，请改用 `Refs #<issue>`。"
        )

    low = body.lower()
    for label, keys in REQUIRED_SECTIONS:
        if not any(k.lower() in low for k in keys):
            errors.append(f"缺少必填段落：{label}。")

    if errors:
        print("PR process lint 失败：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("PR process lint 通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
