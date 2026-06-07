# deploy/prod — 生产部署配置（版本化源）

生产服务器 `~/software/lmzj-ragflow/` 是首次部署时从仓库 `docker/` 拷贝、**非 git clone、无 git 追踪**,可直接在服务器上编辑。本目录只保存「脱离镜像、又不该随 `.env`/证书外泄」的配置的**可恢复源**——历史上 nginx 的 https 配置因只存在于服务器、被覆盖而丢失,导致 HTTPS 掉线。

## HTTPS 如何启用（官方积木 + 一个 entrypoint 坑）

RAGFlow 官方无 HTTPS 教程,但提供了积木:`docker-compose.yml` 里有(被注释的)nginx 挂载位,仓库自带 `docker/nginx/ragflow.https.conf` 模板。

**坑**:`entrypoint.sh` 每次启动执行 `cp -f /etc/nginx/conf.d/ragflow.conf.python /etc/nginx/conf.d/ragflow.conf`(默认 python 后端)。所以**不能**把 https 配置挂到目标 `ragflow.conf`(会被这条 cp 覆盖回 http-only);要挂到**源** `ragflow.conf.python`,让 entrypoint 反而把我们的 https 配置应用上去,且容器重建后自动生效。

**做法**:直接编辑服务器 `~/software/lmzj-ragflow/docker-compose.yml`,在 `ragflow-cpu` 的 `volumes:` 下加两行(取代官方注释的那行 nginx 挂载):

```yaml
    volumes:
      - ./ragflow-logs:/ragflow/logs
      - ./nginx/ragflow.conf:/etc/nginx/conf.d/ragflow.conf.python   # 挂到 entrypoint 复制的“源”
      - ./nginx/ssl:/etc/nginx/ssl                                    # TLS 证书目录
      - ./service_conf.yaml.template:/ragflow/conf/service_conf.yaml.template
      - ./entrypoint.sh:/ragflow/entrypoint.sh
```

`nginx/ragflow.conf`（本目录）= https 站点配置(基于官方 `ragflow.https.conf`,`server_name edu.lmzjai.com`,80→301→443,证书路径 `/etc/nginx/ssl/{fullchain.pem,privkey.pem}`)。

## 不版本化（仅存服务器）

- `nginx/ssl/{fullchain.pem,privkey.pem}` — TLS 证书/私钥,到期手动续。
- `.env` — 含密钥(DB/MinIO/Redis、`LMZJ_SSO_CLIENT_ID/SECRET`)。
- `service_conf.yaml.template` — 服务器版含 `oauth.lmzj`,密钥用 `${ENV}` 占位(对应 git `docker/service_conf.yaml.template`)。

## 恢复 / 应用 nginx 配置

```bash
# 1. 推 https 配置到服务器（若丢失/更新）
scp deploy/prod/nginx/ragflow.conf ubuntu@<host>:~/software/lmzj-ragflow/nginx/ragflow.conf
# 2. 让运行中的容器生效（重跑 entrypoint 的 cp 源→目标 + reload；或 force-recreate）
ssh ubuntu@<host> 'docker exec lmzj-ragflow-ragflow-cpu-1 cp -f /etc/nginx/conf.d/ragflow.conf.python /etc/nginx/conf.d/ragflow.conf \
  && docker exec lmzj-ragflow-ragflow-cpu-1 nginx -t \
  && docker exec lmzj-ragflow-ragflow-cpu-1 nginx -s reload'
# 3. 验证
ssh ubuntu@<host> 'curl -sk -o /dev/null -w "%{http_code}\n" --resolve edu.lmzjai.com:443:127.0.0.1 https://edu.lmzjai.com/'
```

> 改 `docker-compose.yml` 的 mount 结构后,需 `COMPOSE_PROFILES=infinity,cpu docker compose up -d --force-recreate ragflow-cpu`,并**重建后立即复验 443**。
