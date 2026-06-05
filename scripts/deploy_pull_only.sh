#!/usr/bin/env bash
# 生产 pull-only 部署：只拉取指定不可变镜像并重启，生产服务器绝不构建镜像。
# 由 deploy workflow 通过 SSH 在生产执行，所需变量经环境注入：
#   ACR_REGISTRY ACR_USERNAME ACR_PASSWORD RAGFLOW_IMAGE DEPLOY_PATH
set -euo pipefail

: "${ACR_REGISTRY:?缺少 ACR_REGISTRY}"
: "${ACR_USERNAME:?缺少 ACR_USERNAME}"
: "${ACR_PASSWORD:?缺少 ACR_PASSWORD}"
: "${RAGFLOW_IMAGE:?缺少 RAGFLOW_IMAGE}"
: "${DEPLOY_PATH:?缺少 DEPLOY_PATH}"

# 镜像必须是完整 40 位 SHA tag，禁 latest / 短 SHA。
TAG="${RAGFLOW_IMAGE##*:}"
if ! echo "${TAG}" | grep -Eq '^[0-9a-f]{40}$'; then
  echo "拒绝部署：镜像 tag 必须是完整 40 位 SHA，收到 '${TAG}'" >&2
  exit 1
fi

cd "${DEPLOY_PATH}"

echo "[1/5] 登录 ACR ${ACR_REGISTRY}"
echo "${ACR_PASSWORD}" | docker login "${ACR_REGISTRY}" --username "${ACR_USERNAME}" --password-stdin

echo "[2/5] 拉取镜像 ${RAGFLOW_IMAGE}"
docker pull "${RAGFLOW_IMAGE}"

echo "[3/5] 写入 RAGFLOW_IMAGE 到 .env（compose 引用）"
# 更新或追加 RAGFLOW_IMAGE，保留其余 .env 内容。
touch .env
if grep -q '^RAGFLOW_IMAGE=' .env; then
  sed -i.bak "s|^RAGFLOW_IMAGE=.*|RAGFLOW_IMAGE=${RAGFLOW_IMAGE}|" .env && rm -f .env.bak
else
  printf 'RAGFLOW_IMAGE=%s\n' "${RAGFLOW_IMAGE}" >> .env
fi

echo "[4/5] 启动服务（pull-only，不 build）"
docker compose up -d --no-build

echo "[5/5] 当前运行镜像"
docker compose images 2>/dev/null || docker ps --format '{{.Image}}'

echo "部署完成：${RAGFLOW_IMAGE}"
echo "回滚：将 .env 中 RAGFLOW_IMAGE 改回上一版完整 SHA 镜像后再次执行本脚本或 docker compose up -d。"
