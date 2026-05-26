# guanli.feijihe.top SSL 与小程序 API

## 现象

微信开发者工具 / 真机报 **`Error: timeout`**，curl 报 `SEC_E_WRONG_PRINCIPAL`。

原因：`guanli.feijihe.top` 解析到 87，但 **HTTPS 证书不含该子域名**（只有 `feijihe.top`），微信请求无法建立 TLS。

## 临时方案（已做）

- 小程序 API 走 **`https://feijihe.top/api/mp/*`**
- 87 上执行 **`bash deploy/install-feijihe-mp-proxy.sh`**，把 `/api/mp/` 反代到 **3003**
- 或 `git pull && bash deploy.sh` 重启 **sanyang-production**（3002 也挂载 mp 路由）

绑定若报 **HTTP 405**：说明 feijihe 尚未反代 /api/mp，按上面脚本修复。

## 账号说明

绑定用的是 **zean.feijihe.top 客服端账号**（MySQL `users` 表），不是 3003 guanli 网页的 admin。

| 账号 | 密码 | 角色 | 能否用报价小程序 |
|------|------|------|------------------|
| admin | admin888 | 超级管理员 | ✅ |
| sushiting 等 | … | 客服 | ✅ |
| manager | … | 管理 | ❌ |

## 正式修复 guanli（小马哥）

在 87 为 `guanli.feijihe.top` 单独配 Nginx + 证书，例如：

```bash
# 若用 certbot（DNS 已指向 87）
sudo certbot certonly --nginx -d guanli.feijihe.top

# /etc/nginx/conf.d/guanli.conf
server {
    listen 443 ssl http2;
    server_name guanli.feijihe.top;

    ssl_certificate     /etc/letsencrypt/live/guanli.feijihe.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/guanli.feijihe.top/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
curl -s https://guanli.feijihe.top/api/health
```

证书正常后，3003 网页后台可继续用 guanli 域名；小程序可继续走 feijihe.top 或改回 guanli。
