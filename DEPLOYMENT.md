# 🚂 Despliegue en Railway — TeleAgent

Guía para dejar TeleAgent **funcionando 24/7 sin depender de tu PC**. Son **5 servicios**.
El backend es liviano (embeddings ONNX, sin PyTorch) y trae **el cerebro (ChromaDB) HORNEADO
dentro de la imagen**: la documentación se descarga y se convierte en embeddings durante el
build, así que **no necesitas volumen** (que en planes pequeños de Railway no está disponible)
ni un paso manual de carga. El backend arranca ya con conocimiento.

**Datos que reusarás:**
- Repo: `zzzbedream/teleagent`
- Contrato Fuji: `0x78cce8C167583bf358B3EA1c9C409e13A7Da691a`
- Necesitas: `DEEPSEEK_API_KEY`, `DISCORD_TOKEN`, y el `DISCORD_INVITE_URL` (Fase B).
- La URL pública del backend (se genera en A2; se reusa en landing y bot).

> 🛑 **Cada servicio que sale del repo** necesita, en **Settings → Config-as-code → Railway
> Config File**, la ruta a su `railway.json` (`backend/railway.json`, etc.). Sin eso Railway usa
> Railpack y falla. **Root Directory** vacío / en `/`.

---

## Reset (empezar limpio)
Proyecto viejo → **Settings → Danger → Delete Project**. Luego **New Project → Empty Project**.
**Si tenías un servicio `chromadb` aparte, ya no se usa: no lo crees.**

---

# FASE A — El cerebro (backend + Postgres)

## A1. PostgreSQL
En el proyecto: **`Ctrl`+`K`** → `Postgres` → **Add PostgreSQL**. Sin más config.

## A2. Backend (RAG con cerebro horneado)
1. **`+ New` → GitHub Repo** → `teleagent`.
2. **Settings → Config-as-code → Railway Config File** = `backend/railway.json`.
3. **Networking → Generate Domain** → **copia la URL**.
4. **Variables** (NO pongas `CHROMA_PATH`, ni volumen — el cerebro va dentro de la imagen):
   ```
   DEEPSEEK_API_KEY = tu_api_key_de_deepseek
   DATABASE_URL     = ${{Postgres.DATABASE_URL}}
   ALLOWED_ORIGINS  = *
   ```
5. Al desplegar, el **build descarga la documentación y hornea el cerebro (~3-6 min)**. Es normal
   que el build tarde más que antes: está generando los ~2500 embeddings una sola vez.

## A3. 🚦 Verificación
`https://TU-BACKEND.up.railway.app/health` → **`{"status":"ok","documents": ~2500}`**.
- Si `documents` > 0 → el cerebro está cargado. Pasa a la Fase B.
- Si `documents` es `0` o el build falló → mira los **Deploy/Build Logs** del backend (el build
  aborta a propósito si el corpus queda vacío).

---

# FASE B — Las caras (solo tras pasar A3)

## B0. Link de invitación del bot (Discord Developer Portal)
App → **OAuth2 → URL Generator** → scopes **`bot`** + **`applications.commands`**; permisos
**Send Messages** + **Use Slash Commands**. Copia la URL → `DISCORD_INVITE_URL`. Invita el bot a tu server.

## B1. Landing (marketing + demo)
1. **Railway Config File** = `frontend/railway.json`. **Generate Domain** → URL para los jueces.
2. **Variables:**
   ```
   BACKEND_URL        = https://TU-BACKEND.up.railway.app      (SIN /query ni /health)
   DISCORD_INVITE_URL = (el link de B0)
   GITHUB_URL         = https://github.com/zzzbedream/teleagent
   CONTRACT_ADDRESS   = 0x78cce8C167583bf358B3EA1c9C409e13A7Da691a
   ```
3. (Recomendado) En el backend, cambia `ALLOWED_ORIGINS = *` por la URL de la landing.

## B2. Bot (Discord)
1. **Railway Config File** = `bot/railway.json`. Sin dominio.
2. **Variables:**
   ```
   DISCORD_TOKEN = tu_token_del_bot
   DATABASE_URL  = ${{Postgres.DATABASE_URL}}
   FASTAPI_URL   = https://TU-BACKEND.up.railway.app/query     (CON /query)
   ```

## B3. Indexer (eventos on-chain)
1. **Railway Config File** = `indexer/railway.json`. Sin dominio.
2. **Variables:**
   ```
   WSS_URL          = wss://api.avax-test.network/ext/bc/C/ws
   DATABASE_URL     = ${{Postgres.DATABASE_URL}}
   CONTRACT_ADDRESS = 0x78cce8C167583bf358B3EA1c9C409e13A7Da691a
   ```

---

## ✅ Verificación end-to-end final
1. Abre la **URL de la landing** → carga y la demo responde una pregunta.
2. En **Discord**: `/link_wallet 0xTuWallet`.
3. Envía 0.1 AVAX al contrato en Fuji.
4. Logs del **indexer** → `Credited ... wei`.
5. En Discord: `/ask ...` → respuesta con fuentes y saldo descontado.

## Tabla resumen

| Fase | Servicio | Railway Config File | Dominio | Variables clave |
|---|---|---|---|---|
| A1 | Postgres | — (plugin) | no | — |
| A2 | backend | `backend/railway.json` | **sí** | DEEPSEEK_API_KEY, DATABASE_URL, ALLOWED_ORIGINS |
| A3 | (verificar) | — | — | `/health` → documents > 0 |
| B1 | landing | `frontend/railway.json` | **sí** | BACKEND_URL, DISCORD_INVITE_URL, GITHUB_URL, CONTRACT_ADDRESS |
| B2 | bot | `bot/railway.json` | no | DISCORD_TOKEN, DATABASE_URL, FASTAPI_URL |
| B3 | indexer | `indexer/railway.json` | no | WSS_URL, DATABASE_URL, CONTRACT_ADDRESS |

## Solución de problemas
- **`Railpack could not determine how to build`:** falta el Railway Config File del servicio.
- **Build del backend falla en `app.ingest`:** revisa los Build Logs; puede ser red al clonar los
  docs. Reintenta el deploy. El build aborta a propósito si el corpus queda vacío.
- **"Application failed to respond":** el backend se cayó al arrancar (antes era memoria por torch;
  ya no debería pasar). Mira los Deploy Logs.
- **`{"detail":"Not Found"}` en `/`:** normal en el backend. Usa `/health`.
- **`/health` da `documents: 0`:** el horneado del build no cargó docs; revisa los Build Logs.
- **La demo de la landing no responde:** falta `BACKEND_URL`, o CORS (pon la URL de la landing en `ALLOWED_ORIGINS`).
- **El bot no muestra comandos:** revisa `DISCORD_TOKEN` y que se invitó con `applications.commands`.
