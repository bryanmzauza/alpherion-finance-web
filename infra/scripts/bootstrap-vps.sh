#!/usr/bin/env bash
# Prepara uma VPS Ubuntu 24.04 do zero (site.md §7.6). Roda UMA vez, como root.
#
#   ssh root@IP 'bash -s' < infra/scripts/bootstrap-vps.sh
#   # ou, já na VPS:  bash bootstrap-vps.sh
#
# O que faz: usuário de deploy, SSH só por chave, ufw (SSH + Cloudflare), fail2ban,
# Docker, unattended-upgrades, volume/tablespace do schema `market`, logrotate de 6 meses
# (Marco Civil art. 15) e o cron do update-cloudflare-ips.
# O que NÃO faz: clonar o repo, criar o .env, subir o compose — isso é o deploy.sh.
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-deploy}"
APP_DIR="${APP_DIR:-/opt/alpherion}"
MARKET_DIR="${MARKET_DIR:-/srv/alpherion/market}"
SSH_PORT="${SSH_PORT:-22}"

[ "$(id -u)" -eq 0 ] || { echo "rode como root" >&2; exit 1; }

echo "==> pacotes"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg ufw fail2ban unattended-upgrades \
  age postgresql-client-16 logrotate cron jq

echo "==> usuário $DEPLOY_USER"
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" "$DEPLOY_USER"
fi
install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
if [ -f /root/.ssh/authorized_keys ]; then
  cp /root/.ssh/authorized_keys "/home/$DEPLOY_USER/.ssh/authorized_keys"
  chown "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh/authorized_keys"
  chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
fi
# Sem sudo interativo (§7.6): só os comandos do deploy.
cat > /etc/sudoers.d/alpherion-deploy <<EOF
$DEPLOY_USER ALL=(root) NOPASSWD: /usr/bin/docker, /usr/bin/docker compose, $APP_DIR/infra/scripts/update-cloudflare-ips.sh
EOF
chmod 440 /etc/sudoers.d/alpherion-deploy

echo "==> SSH: sem senha, sem root"
sed -i -E 's/^#?PermitRootLogin.*/PermitRootLogin no/; s/^#?PasswordAuthentication.*/PasswordAuthentication no/; s/^#?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config
systemctl reload ssh || systemctl reload sshd

echo "==> Docker"
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
usermod -aG docker "$DEPLOY_USER"
cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "5" },
  "live-restore": true,
  "userland-proxy": false
}
EOF
systemctl restart docker

echo "==> firewall (SSH + Cloudflare)"
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow "$SSH_PORT"/tcp comment 'ssh'
ufw --force enable
# As faixas da Cloudflare entram aqui (o script também recarrega o nginx quando mudam).
if [ -x "$APP_DIR/infra/scripts/update-cloudflare-ips.sh" ]; then
  "$APP_DIR/infra/scripts/update-cloudflare-ips.sh" --no-reload
else
  echo "    (rode update-cloudflare-ips.sh depois de clonar o repo em $APP_DIR)"
fi

echo "==> fail2ban (sshd + nginx)"
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
backend  = systemd

[sshd]
enabled = true

[nginx-http-auth]
enabled  = true
logpath  = /var/log/nginx/error.log

[nginx-limit-req]
enabled  = true
logpath  = /var/log/nginx/error.log
maxretry = 20
findtime = 1m
bantime  = 10m
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban

echo "==> atualizações de segurança automáticas"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
cat > /etc/apt/apt.conf.d/52unattended-upgrades-local <<'EOF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:30";
EOF

echo "==> diretórios"
install -d -m 755 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$APP_DIR"
# Volume separado para o schema `market` (§7.6). Se houver disco dedicado, monte-o aqui
# ANTES de rodar este script (fstab) — o Postgres cria a tablespace neste caminho.
install -d -m 700 -o 999 -g 999 "$MARKET_DIR" # uid/gid do postgres na imagem alpine
install -d -m 755 -o "$DEPLOY_USER" -g "$DEPLOY_USER" /var/log/alpherion

echo "==> logrotate: registros de acesso por 6 meses (Marco Civil art. 15)"
cat > /etc/logrotate.d/alpherion-nginx <<'EOF'
/var/lib/docker/volumes/alpherion_nginx-logs/_data/*.log {
    daily
    rotate 180
    missingok
    notifempty
    compress
    delaycompress
    sharedscripts
    postrotate
        docker compose -f /opt/alpherion/infra/compose.yml exec -T nginx nginx -s reopen 2>/dev/null || true
    endscript
}
EOF

echo "==> cron"
cat > /etc/cron.d/alpherion <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
# faixas da Cloudflare (semanal)
0 4 * * 1 root $APP_DIR/infra/scripts/update-cloudflare-ips.sh >> /var/log/alpherion/cf-ips.log 2>&1
# backup diário (app, listmonk, umami) e semanal (market)
30 3 * * * $DEPLOY_USER $APP_DIR/infra/scripts/backup.sh >> /var/log/alpherion/backup.log 2>&1
30 2 * * 0 $DEPLOY_USER $APP_DIR/infra/scripts/backup.sh --market >> /var/log/alpherion/backup.log 2>&1
EOF
chmod 644 /etc/cron.d/alpherion

cat <<EOF

==> pronto. Próximos passos (manuais):
  1. Como $DEPLOY_USER: git clone <repo> $APP_DIR && cd $APP_DIR
  2. cp infra/env/.env.example .env && chmod 600 .env && preencher
  3. Colocar o certificado de origem da Cloudflare nos caminhos de CLOUDFLARE_ORIGIN_*
     e baixar o CA do Authenticated Origin Pulls em infra/nginx/tls/cloudflare-origin-pull-ca.pem:
       curl -fsSL https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem \\
         -o infra/nginx/tls/cloudflare-origin-pull-ca.pem
  4. infra/scripts/update-cloudflare-ips.sh
  5. infra/scripts/deploy.sh <tag>
EOF
