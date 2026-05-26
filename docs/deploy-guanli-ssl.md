# guanli.feijihe.top SSL 与小程序 API

## 现象

微信开发者工具 / 真机报 **`Error: timeout`**，curl 报 `SEC_E_WRONG_PRINCIPAL`。

原因：`guanli.feijihe.top` 解析到 87，但 **HTTPS 证书不含该子域名**（只有 `feijihe.top`），微信请求无法建立 TLS。

## 临时方案（已做）

- 小程序 API 同时注册在 **3002** → `https://feijihe.top/api/mp/*`
- quote-weapp / customer-order 的 API 地址改为 **`https://feijihe.top`**
- 微信后台 request 合法域名只需 **`https://feijihe.top`**（报价小程序本来就有）

部署：`git pull && bash deploy.sh` 后重启 **sanyang-production** 与 **sanyang-customer-order**。

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
