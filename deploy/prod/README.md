# deploy/prod — 生产部署配置（版本化源）

生产服务器 `~/software/lmzj-ragflow/` 下**脱离镜像的部署配置**的版本化源。这些文件经 `docker-compose.yml` 的 bind mount 注入容器,**不在镜像里**,也**不在 pull-only 部署的自动同步范围**——历史上曾因只存在于服务器而被覆盖丢失,导致 HTTPS 掉线。此目录即为防丢的可恢复源。

> ⚠️ 教训:2026-06-07 服务器上的 `nginx/ragflow.conf` 被退回为镜像默认(仅 80),443 停止监听、HTTPS 打不开。根因是该文件当时只在服务器、未版本化。

## 内容

| 文件 | 对应服务器路径 | 说明 |
|---|---|---|
| `nginx/ragflow.conf` | `~/software/lmzj-ragflow/nginx/ragflow.conf` | HTTPS 站点配置(80→301→443,`server_name edu.lmzjai.com`) |
| `docker-compose.override.yml` | `~/software/lmzj-ragflow/docker-compose.override.yml` | 给 `ragflow-cpu` 追加挂载:上面的 nginx 配置 + `./nginx/ssl`(证书) |

## 不在此目录(不版本化)的内容

- `nginx/ssl/{fullchain.pem,privkey.pem}` — TLS 证书/私钥,仅存服务器,到期手动续。
- `.env` — 含密钥(DB/MinIO/Redis 密码、`LMZJ_SSO_CLIENT_ID/SECRET`),仅存服务器。
- `service_conf.yaml.template` — 由 `docker/service_conf.yaml.template`(git)同步,密钥用 `${ENV}` 占位。

## 同步到服务器(手动,直到部署自动化覆盖配置同步)

```bash
# 从仓库根目录
scp deploy/prod/nginx/ragflow.conf      ubuntu@<host>:~/software/lmzj-ragflow/nginx/ragflow.conf
scp deploy/prod/docker-compose.override.yml ubuntu@<host>:~/software/lmzj-ragflow/docker-compose.override.yml
# 重载 nginx（不重建容器）
ssh ubuntu@<host> 'docker exec lmzj-ragflow-ragflow-cpu-1 nginx -t && docker exec lmzj-ragflow-ragflow-cpu-1 nginx -s reload'
# 验证
ssh ubuntu@<host> 'curl -sk -o /dev/null -w "%{http_code}\n" --resolve edu.lmzjai.com:443:127.0.0.1 https://edu.lmzjai.com/'
```

> 改 compose mount(非仅 nginx 内容)时,需 `docker compose up -d --force-recreate ragflow-cpu`(不带 `-f`,以加载 override),并**重建后立即复验 443**。

## 待办(后续硬化)

- 让治理版 `deploy.yml` / `deploy_pull_only.sh` 在每次部署时从仓库同步 `deploy/prod/*` 与 `docker/service_conf.yaml.template` 到服务器(排除 `.env`、`nginx/ssl/`),彻底消除配置漂移。
