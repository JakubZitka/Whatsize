# Testovací prostředí zdarma

Kompletní testovací nasazení WhatSize za 0 Kč, bez platební karty, vše v EU.
Slouží k ladění před ostrým deploymentem na Hetzner (viz `deployment-plan.md`);
produkční Terraform a compose zůstávají nedotčené — přechod na ostrý provoz je
jen změna API URL.

| Složka | Služba | Free tier limity |
|---|---|---|
| API | Render (Frankfurt) | usne po 15 min nečinnosti, probuzení ~30–60 s |
| PostgreSQL | Neon (Frankfurt) | 0,5 GB — seed data zaberou pár MB |
| Flutter web | GitHub Pages | bez praktických limitů |
| Android APK | GitHub Actions artefakty | artefakty drží 90 dní |
| iOS | — | bez Apple Developer účtu (99 $/rok) nejde distribuovat; testujte web build, na vlastní iPhone lze appku nahrát přes Xcode (podpis platí 7 dní) |

## 1. Databáze — Neon (~5 minut)

1. Účet na [neon.tech](https://neon.tech) (přihlášení GitHubem), **Create project**,
   region **Frankfurt (eu-central-1)**, jméno `whatsize-test`.
2. Zkopírujte connection string a upravte schéma pro psycopg:
   `postgres://uzivatel:heslo@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`
   → `postgresql+psycopg://uzivatel:heslo@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`
3. Migrace se na free tieru pouštějí ručně z lokálu (Render free nemá
   pre-deploy krok):
   ```bash
   cd backend
   WHATSIZE_DATABASE_URL='postgresql+psycopg://…' alembic upgrade head
   ```

## 2. API — Render (~5 minut)

1. Účet na [render.com](https://render.com) (přihlášení GitHubem).
2. **New → Blueprint**, vyberte repo `JakubZitka/Whatsize` — Render načte
   `render.yaml` z kořene repa (Frankfurt, free plán, health check `/healthz`).
3. Při dotazu na `WHATSIZE_DATABASE_URL` vložte upravený Neon connection
   string z kroku 1.
4. Po nasazení dostanete URL typu `https://whatsize-api.onrender.com` —
   ověřte `https://…/healthz` a `https://…/docs`. Auto-deploy z `main`
   je zapnutý v blueprintu.

První request po probuzení ze spánku trvá až minutu — to je vlastnost free
tieru, ne chyba. (Mobilní appka s tím počítá delším timeoutem.)

## 3. Flutter web — GitHub Pages (~3 minuty)

1. V repu: **Settings → Pages → Source: „GitHub Actions"**.
2. **Settings → Secrets and variables → Actions → Variables** → nová
   proměnná `WHATSIZE_API_URL` = URL z Renderu (bez lomítka na konci).
3. Merge do `main` dotýkající se `mobile/` spustí workflow `mobile`,
   který web build nasadí na `https://jakubzitka.github.io/Whatsize/`.
   Odkaz funguje komukoli, i na telefonu.

CORS: `render.yaml` už povoluje origin `https://jakubzitka.github.io`.
Kdyby se změnil účet/doména, upravte `WHATSIZE_CORS_ORIGINS` v Renderu.

## 4. Android APK

Každý běh workflow `mobile` přikládá artefakt **whatsize-apk**
(Actions → běh workflow → Artifacts). Testeři si `app-release.apk`
nainstalují přímo (je podepsaný debug klíčem — jen pro testování, do
Play Store půjde build z Codemagicu).

Pohodlnější distribuce větší skupině: [Firebase App Distribution]
(https://firebase.google.com/docs/app-distribution) — zdarma, testeři
dostávají e-mail s odkazem na novou verzi. Zapojíme, až bude potřeba.

## Až testování skončí

Ostrý deployment podle `deployment-plan.md`: Terraform na Hetzner, přepnout
`WHATSIZE_API_URL` na produkční doménu a Render/Neon prostředí smazat nebo
ponechat jako trvalé testovací prostředí — nic to nestojí.
