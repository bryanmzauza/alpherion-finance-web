#!/usr/bin/env python3
"""Configura um Listmonk recém-instalado para a lista do Alpherion (idempotente).

O que faz, via API (sessão do admin):
  1. Lista "Leitura de Mercado" (double opt-in, privada)            → LISTMONK_LIST_ID
  2. Usuário de API "web" (papel Super Admin)                        → LISTMONK_API_USER / LISTMONK_API_TOKEN (impresso 1x)
  3. Template transacional "optin" com link para SITE_URL/lista/confirmar?t=<uuid>
                                                                     → LISTMONK_OPTIN_TEMPLATE_ID
  4. Template de campanha padrão com descadastro em SITE_URL/lista/sair?t=<uuid>
  5. Settings: nome do site, root_url, from, opt-in nativo DESLIGADO (o web envia pelo tx),
     página pública de inscrição desligada; com --smtp-mailpit, SMTP → mailpit:1025 (dev)

Uso (da raiz do repo, com o .env carregado):
  python infra/scripts/listmonk-setup.py --smtp-mailpit          # dev
  python infra/scripts/listmonk-setup.py                         # prod (SMTP configurado no painel)

Variáveis: LISTMONK_URL, LISTMONK_ADMIN_USER, LISTMONK_ADMIN_PASSWORD, SITE_URL, EMAIL_FROM_TRANSACTIONAL.
Só stdlib: roda em qualquer máquina com Python 3.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LIST_NAME = "Leitura de Mercado"
API_USER = "web"
OPTIN_TEMPLATE_NAME = "Alpherion — confirmação de inscrição"


def load_dotenv() -> None:
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.split(" #")[0].strip()
        os.environ.setdefault(key.strip(), value)


class Listmonk:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def _req(self, method: str, path: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> tuple[int, bytes]:
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers or {})
        try:
            with self.opener.open(req, timeout=15) as res:
                return res.status, res.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def login(self, user: str, password: str) -> None:
        self._req("GET", "/admin/login")
        nonce = next((c.value for c in self.jar if c.name == "nonce"), "")
        form = urllib.parse.urlencode({"username": user, "password": password, "nonce": nonce}).encode()
        status, _ = self._req("POST", "/admin/login", form, {"Content-Type": "application/x-www-form-urlencoded"})
        if status not in (200, 302):
            sys.exit(f"login falhou ({status}) — confira LISTMONK_ADMIN_USER/PASSWORD")
        status, _ = self._req("GET", "/api/settings")
        if status != 200:
            sys.exit(f"sessão inválida após login ({status})")

    def api(self, method: str, path: str, body: dict | None = None) -> dict | list | None:
        data = json.dumps(body).encode() if body is not None else None
        status, raw = self._req(method, "/api" + path, data, {"Content-Type": "application/json"} if data else {})
        payload = json.loads(raw) if raw else {}
        if status >= 400:
            sys.exit(f"{method} {path} → {status}: {payload.get('message', raw[:200])}")
        return payload.get("data")


def ensure_list(lm: Listmonk) -> int:
    lists = lm.api("GET", "/lists?per_page=all")["results"]
    for lst in lists:
        if lst["name"] == LIST_NAME:
            print(f"lista já existe: id={lst['id']}")
            return lst["id"]
    created = lm.api(
        "POST",
        "/lists",
        {"name": LIST_NAME, "type": "private", "optin": "double", "tags": ["alpherion"], "description": "Leitura de Mercado semanal e avisos do Alpherion"},
    )
    print(f"lista criada: id={created['id']}")
    return created["id"]


def ensure_api_user(lm: Listmonk) -> str | None:
    users = lm.api("GET", "/users")
    if any(u["username"] == API_USER for u in users):
        print(f"usuário de API '{API_USER}' já existe (token só é mostrado na criação)")
        return None
    roles = lm.api("GET", "/roles/users")
    role_id = next(r["id"] for r in roles if r["name"] == "Super Admin")
    created = lm.api(
        "POST",
        "/users",
        {"username": API_USER, "name": "web (apps/web)", "type": "api", "status": "enabled", "user_role_id": role_id, "list_role_id": None},
    )
    return created.get("password")


OPTIN_BODY = """<!doctype html>
<html lang="pt-BR"><body style="margin:0;background:#0B192C;color:#F8F9FA;font-family:Inter,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0B192C;padding:32px 16px;">
<tr><td align="center">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;background:#11213A;border:1px solid #1A2E4C;border-radius:8px;padding:32px;">
<tr><td>
<p style="margin:0 0 8px;font-size:12px;color:rgba(248,249,250,.7);">Alpherion Finance</p>
<h1 style="margin:0 0 16px;font-family:'Playfair Display',Georgia,serif;font-size:28px;line-height:36px;font-weight:600;">Confirme sua <span style="color:#C5A059;">inscrição</span></h1>
<p style="margin:0 0 24px;font-size:16px;line-height:26px;color:rgba(248,249,250,.85);">Você pediu para receber a Leitura de Mercado e avisos do Alpherion. Para confirmar, clique no botão. Sem isso, não enviamos nada.</p>
<p style="margin:0 0 24px;"><a href="{{ .Tx.Data.confirm_url }}" style="display:inline-block;background:#C5A059;color:#0B192C;text-decoration:none;font-weight:600;padding:12px 20px;border-radius:6px;">Confirmar inscrição</a></p>
<p style="margin:0 0 8px;font-size:13px;line-height:20px;color:rgba(248,249,250,.7);">Se o botão não funcionar, copie este endereço no navegador:<br><a href="{{ .Tx.Data.confirm_url }}" style="color:#C5A059;">{{ .Tx.Data.confirm_url }}</a></p>
<p style="margin:24px 0 0;font-size:12px;line-height:18px;color:rgba(248,249,250,.6);">Se você não pediu isso, ignore este e-mail: nenhum outro será enviado. {{ .Tx.Data.legal_entity }}</p>
</td></tr></table>
</td></tr></table>
</body></html>"""


def ensure_optin_template(lm: Listmonk) -> int:
    templates = lm.api("GET", "/templates")
    body = {"name": OPTIN_TEMPLATE_NAME, "type": "tx", "subject": "Confirme sua inscrição no Alpherion Finance", "body": OPTIN_BODY}
    for t in templates:
        if t["name"] == OPTIN_TEMPLATE_NAME:
            lm.api("PUT", f"/templates/{t['id']}", body)
            print(f"template de opt-in atualizado: id={t['id']}")
            return t["id"]
    created = lm.api("POST", "/templates", body)
    print(f"template de opt-in criado: id={created['id']}")
    return created["id"]


def patch_campaign_template(lm: Listmonk, site_url: str) -> None:
    """Troca o link de descadastro do template padrão pelo /lista/sair do site."""
    templates = lm.api("GET", "/templates")
    default = next((t for t in templates if t["type"] == "campaign" and t.get("is_default")), None)
    if not default:
        print("template de campanha padrão não encontrado; pulei")
        return
    full = lm.api("GET", f"/templates/{default['id']}")
    body: str = full["body"]
    ours = f"{site_url}/lista/sair?t={{{{ .Subscriber.UUID }}}}"
    if ours in body:
        print("template de campanha já aponta para /lista/sair")
        return
    body = body.replace("{{ UnsubscribeURL }}", ours)
    lm.api("PUT", f"/templates/{default['id']}", {"name": full["name"], "type": "campaign", "subject": full.get("subject", ""), "body": body})
    print("template de campanha: descadastro -> /lista/sair")


def patch_settings(lm: Listmonk, site_url: str, root_url: str, from_email: str, smtp_mailpit: bool) -> None:
    settings = lm.api("GET", "/settings")
    settings["app.site_name"] = "Alpherion Finance"
    settings["app.root_url"] = root_url
    settings["app.from_email"] = f"Alpherion Finance <{from_email}>"
    settings["app.send_optin_confirmation"] = False  # o web envia pelo tx com link para SITE_URL/lista/confirmar
    settings["app.enable_public_subscription_page"] = False
    settings["app.enable_public_archive"] = False
    settings["app.check_updates"] = False
    settings["app.lang"] = "pt-BR"
    settings["privacy.allow_blocklist"] = True
    settings["privacy.allow_export"] = True
    settings["privacy.allow_wipe"] = True
    settings["privacy.unsubscribe_header"] = True  # List-Unsubscribe one-click
    if smtp_mailpit:
        settings["smtp"] = [
            {
                "enabled": True,
                "host": "mailpit",
                "hello_hostname": "",
                "port": 1025,
                "auth_protocol": "none",
                "username": "",
                "password": "",
                "email_headers": [],
                "max_conns": 5,
                "max_msg_retries": 2,
                "idle_timeout": "15s",
                "wait_timeout": "5s",
                "tls_type": "none",
                "tls_skip_verify": True,
            }
        ]
    lm.api("PUT", "/settings", settings)
    print("settings atualizadas (o Listmonk reinicia sozinho)")
    _ = site_url


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows: console cp1252
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smtp-mailpit", action="store_true", help="dev: SMTP → mailpit:1025")
    args = parser.parse_args()
    load_dotenv()

    url = os.environ.get("LISTMONK_URL", "http://127.0.0.1:9000")
    admin = os.environ.get("LISTMONK_ADMIN_USER", "admin")
    password = os.environ.get("LISTMONK_ADMIN_PASSWORD") or sys.exit("LISTMONK_ADMIN_PASSWORD não definido")
    site_url = os.environ.get("SITE_URL", "http://localhost:3000").rstrip("/")
    from_email = os.environ.get("EMAIL_FROM_TRANSACTIONAL") or "no-reply@alpherion.com.br"

    lm = Listmonk(url)
    lm.login(admin, password)
    list_id = ensure_list(lm)
    token = ensure_api_user(lm)
    template_id = ensure_optin_template(lm)
    patch_campaign_template(lm, site_url)
    patch_settings(lm, site_url, url, from_email, args.smtp_mailpit)

    print("\nCole no .env:")
    print(f"LISTMONK_LIST_ID={list_id}")
    print(f"LISTMONK_OPTIN_TEMPLATE_ID={template_id}")
    print(f"LISTMONK_API_USER={API_USER}")
    if token:
        print(f"LISTMONK_API_TOKEN={token}")
    else:
        print("LISTMONK_API_TOKEN=<já criado; para gerar outro, apague o usuário 'web' no painel e rode de novo>")


if __name__ == "__main__":
    main()
