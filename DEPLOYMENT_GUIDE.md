# 🚀 OmniBrain Production Deployment & 24/7 Hosting Guide
## 100% Free Forever Cloud Architecture (₹0 / $0 Cost)

This guide provides instructions to run **OmniBrain** 24 hours a day, 7 days a week in the cloud without paying a single rupee.

---

## 🏗️ The 100% Free Stack

| Layer | Provider | Free Tier Specification | Cost |
|---|---|---|---|
| **Compute & Cloud Server** | **Oracle Cloud Always Free** | 4 OCPU (Ampere A1 ARM), 24 GB RAM, 200 GB NVMe | **₹0 / forever** |
| **Primary Intelligence** | **Google Gemini API** | Free tier (Gemini 1.5 Flash / Pro, 15 RPM, 1M TPM) | **₹0 / forever** |
| **Database & Vectors** | **Self-hosted PostgreSQL 16** | Containerized with `pgvector` index | **₹0 / forever** |
| **Cache, Stream & Queue** | **Self-hosted Redis 7** | Containerized Streams & Pub/Sub | **₹0 / forever** |
| **Lady AI Voice Engine** | **Microsoft Neural TTS** | Python `edge-tts` (JennyNeural & SwaraNeural) | **₹0 / forever** |
| **Mobile Automation** | **MacroDroid / Apple Shortcuts** | Webhook calls to OmniBrain Companion Gateway | **₹0 / forever** |
| **Domain & SSL** | **DuckDNS / Cloudflare + Caddy** | Automatic Let's Encrypt HTTPS certificates | **₹0 / forever** |

---

## Part 1: Oracle Cloud Free Tier Instance Setup (5 Minutes)

1. Sign up for an **Oracle Cloud Free Tier** account at [cloud.oracle.com](https://cloud.oracle.com).
2. In the Oracle Console, go to **Compute** → **Instances** → **Create Instance**.
3. Configure the VM:
   - **Image**: Ubuntu 22.04 or 24.04 LTS.
   - **Shape**: Change shape to **Ampere (ARM)** → Select **4 OCPUs** and **24 GB RAM** (Included in Always Free).
   - **Networking**: Assign a public IPv4 address.
   - **SSH Keys**: Download and save your private SSH key (`ssh-key.key`).
4. Click **Create**. Within 60 seconds, your 24GB RAM Cloud Server is active!

---

## Part 2: Cloud Firewall & Ingress Rules

In the Oracle Cloud Console:
1. Go to **Virtual Cloud Networks (VCN)** → Click your Default Security List.
2. Add **Ingress Rules**:
   - `0.0.0.0/0`, TCP Port `80` (HTTP for SSL renewal)
   - `0.0.0.0/0`, TCP Port `443` (HTTPS for Web UI & Mobile Webhooks)
   - `0.0.0.0/0`, TCP Port `22` (SSH)

On the Ubuntu server itself, configure `iptables`:
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

---

## Part 3: Deploy OmniBrain on the Server

SSH into your server:
```bash
ssh -i ssh-key.key ubuntu@<YOUR_SERVER_PUBLIC_IP>
```

Install Docker & Docker Compose:
```bash
sudo apt update && sudo apt install -y docker.io docker-compose git curl
sudo usermod -aG docker ubuntu
newgrp docker
```

Clone your OmniBrain repository:
```bash
git clone <YOUR_GIT_REPO_URL> omnibrain
cd omnibrain
```

Configure your production `.env` file:
```bash
cp .env.example .env
nano .env
```
Ensure your `GEMINI_API_KEY`, `JWT_SECRET_KEY`, and `ENCRYPTION_KEY` are populated.

Start all backend services:
```bash
docker compose up -d
docker compose exec api alembic upgrade head
```

Build and run the Next.js frontend:
```bash
cd apps/web
npm install
npm run build
pm2 start npm --name "omnibrain-web" -- start -- -p 3000
```

---

## Part 4: Automated Free SSL & Domain with Caddy

Install Caddy (Reverse proxy that issues and renews free HTTPS automatically):
```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

Point a free domain (e.g. `yourname.duckdns.org`) or your own domain to your server's Public IP.

Edit `/etc/caddy/Caddyfile`:
```caddy
yourname.duckdns.org {
    # Route API and mobile webhook calls
    handle /v1/* {
        reverse_proxy localhost:8000
    }

    # Route Command Center UI
    handle {
        reverse_proxy localhost:3000
    }
}
```

Restart Caddy:
```bash
sudo systemctl restart caddy
```

Now, visit `https://yourname.duckdns.org` in your browser. You will have:
- Green padlock HTTPS.
- Full Command Center with F.R.I.D.A.Y. Voice & Chat.
- Mobile companion webhook endpoint: `https://yourname.duckdns.org/v1/mobile/webhook`.

---

## Part 5: Smartphone Companion Integration

On your Android phone (via **MacroDroid** or **Tasker**) or iPhone (via **Apple Shortcuts**):

1. **SMS & Bank OTP Forwarding**:
   - Trigger: *SMS Received*
   - Action: *HTTP Request (POST)*
   - URL: `https://yourname.duckdns.org/v1/mobile/webhook`
   - Body: `{"event_type": "sms", "sender": "[sms_number]", "message": "[sms_body]"}`

2. **Low Battery Voice Alert**:
   - Trigger: *Battery < 15%*
   - Action: *HTTP Request (POST)*
   - URL: `https://yourname.duckdns.org/v1/mobile/webhook`
   - Body: `{"event_type": "battery", "level": 12}`

3. **Lockscreen Morning Briefing Widget**:
   - Add a home-screen quick button that sends a `POST` to `https://yourname.duckdns.org/v1/mobile/quick-action` with body `{"action": "morning_briefing"}`.

---

## Part 6: Local Launch (Development on Windows)

When working locally on your PC, simply run:
```powershell
.\start.ps1
```
And to stop cleanly:
```powershell
.\stop.ps1
```

