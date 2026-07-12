# 🚂 Despliegue en Railway — TeleAgent

Guía para dejar TeleAgent **funcionando 24/7 sin depender de tu PC**. Todo se aloja en Railway:
6 servicios. El despliegue se hace en **dos fases**: primero **el cerebro** (y se verifica que
tiene conocimiento), y solo entonces **las caras** (landing, bot, indexer).

> **Por qué en dos fases:** el conocimiento del bot NO viene pre-cargado. Es documentación
> oficial (ACPs + Builders Hub + Teleporter, ~320+ documentos) que se descarga y se convierte en
> embeddings dentro de ChromaDB en un paso único (el "seed"). Antes de sembrar, ChromaDB está
> **vacío** y el bot respondería "no tengo información" a todo. Por eso se despliega y **verifica
> el cerebro antes** de montar lo visible encima.

**Datos que reusarás:**
- Repo: `zzzbedream/teleagent`
- Contrato Fuji: `0x78cce8C167583bf358B3EA1c9C409e13A7Da691a`
- Necesitas: `DEEPSEEK_API_KEY`, `DISCORD_TOKEN`, y el `DISCORD_INVITE_URL` (Fase B).
- La URL pública del backend (se genera en A3; se reusa en landing y bot).

> 🛑 **Cada servicio que sale del repo** necesita, en **Settings → Config-as-code → Railway
> Config File**, la ruta a su `railway.json` (`backend/railway.json`, `frontend/railway.json`,
> etc.). Sin eso, Railway usa Railpack y **falla**. Deja **Root Directory** vacío / en `/`.

---

# FASE A — El cerebro (desplegar y VERIFICAR)

## A1. PostgreSQL
En el proyecto: **`Ctrl`+`K`** → escribe `Postgres` → **Add PostgreSQL**. Sin más config.
(El botón para bases de datos está en el **lienzo del proyecto**, no dentro de un servicio.)

## A2. ChromaDB
1. **`+ New` → Docker Image** → `chromadb/chroma:latest`.
2. Renómbralo **EXACTAMENTE `chromadb`** (para el hostname `chromadb.railway.internal`).
3. **Settings → Volumes** → volumen en `/chroma/chroma`. Sin dominio público. Escucha en `8000`.

## A3. Backend (RAG)
1. **Config-as-code → Railway Config File** = `backend/railway.json`.
2. **Networking → Generate Domain** → **copia la URL** (ej. `https://backend-xxx.up.railway.app`).
3. **Variables:**
   ```
   DEEPSEEK_API_KEY = tu_api_key_de_deepseek
   DATABASE_URL     = ${{Postgres.DATABASE_URL}}
   CHROMA_HOST      = chromadb.railway.internal
   CHROMA_PORT      = 8000
   ALLOWED_ORIGINS  = *
   ```

> ⚠️ Carga un modelo de embeddings (torch): necesita **≥1–2 GB de RAM**. Si se reinicia por
> memoria (OOM), súbele el plan a este servicio.

## A4. Sembrar el corpus (una sola vez)
Con backend y chromadb arriba, en el servicio **backend** → Terminal/Shell (o CLI de Railway):
```
python scripts/fetch_repos.py && python -m app.ingest
```
Descarga la documentación oficial y la indexa. Tarda varios minutos.

## A5. 🚦 Filtro de verificación (NO sigas si falla)
- Abre `https://TU-BACKEND.up.railway.app/health` → debe decir **`"documents": ~320`** (no `0`).
  - `documents: 0` → el seed (A4) no cargó nada; revísalo antes de continuar.
  - `documents: null` → el backend no alcanza a ChromaDB; revisa `CHROMA_HOST`.
- **Solo si `documents` > 0, pasa a la Fase B.**

---

# FASE B — Las caras (solo tras pasar el filtro A5)

## B0. Link de invitación del bot (Discord Developer Portal)
App → **OAuth2 → URL Generator** → scopes **`bot`** + **`applications.commands`**; permisos
**Send Messages** + **Use Slash Commands**. Copia la URL → es tu `DISCORD_INVITE_URL`.
Ábrela una vez para **invitar el bot a tu servidor**.

## B1. Landing (marketing + demo)
1. **Railway Config File** = `frontend/railway.json`.
2. **Generate Domain** → **esta es la URL para los jueces**.
3. **Variables:**
   ```
   BACKEND_URL        = https://TU-BACKEND.up.railway.app      (SIN /query ni /health)
   DISCORD_INVITE_URL = (el link de B0)
   GITHUB_URL         = https://github.com/zzzbedream/teleagent
   CONTRACT_ADDRESS   = 0x78cce8C167583bf358B3EA1c9C409e13A7Da691a
   ```
4. (Recomendado) Vuelve al **backend** y cambia `ALLOWED_ORIGINS = *` por la URL de la landing.

## B2. Bot (Discord)
1. **Railway Config File** = `bot/railway.json`. Sin dominio.
2. **Variables:**
   ```
   DISCORD_TOKEN = tu_token_del_bot
   DATABASE_URL  = ${{Postgres.DATABASE_URL}}
   FASTAPI_URL   = https://TU-BACKEND.up.railway.app/query     (CON /query al final)
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
2. En **Discord** (bot ya invitado): `/link_wallet 0xTuWallet`.
3. Envía 0.1 AVAX al contrato en Fuji (`cast send $CONTRACT "deposit()" --value 0.1ether ...`).
4. Logs del **indexer** en Railway → aparece `Credited ... wei`.
5. En Discord: `/ask ¿Qué cambió con la actualización Etna?` → respuesta con fuentes y saldo descontado.

Si los 5 pasan: **listo para el grant.** 🎉

## Tabla resumen

| Fase | Servicio | Railway Config File | Dominio | Variables clave |
|---|---|---|---|---|
| A1 | Postgres | — (plugin) | no | — |
| A2 | chromadb | — (Docker image) | no | volumen /chroma/chroma |
| A3 | backend | `backend/railway.json` | **sí** | DEEPSEEK_API_KEY, DATABASE_URL, CHROMA_HOST/PORT, ALLOWED_ORIGINS |
| A4 | (seed) | — | — | `fetch_repos.py` + `app.ingest`, una vez |
| A5 | (verificar) | — | — | `/health` → documents > 0 |
| B1 | landing | `frontend/railway.json` | **sí** | BACKEND_URL, DISCORD_INVITE_URL, GITHUB_URL, CONTRACT_ADDRESS |
| B2 | bot | `bot/railway.json` | no | DISCORD_TOKEN, DATABASE_URL, FASTAPI_URL |
| B3 | indexer | `indexer/railway.json` | no | WSS_URL, DATABASE_URL, CONTRACT_ADDRESS |

## Solución de problemas

- **`Railpack could not determine how to build`:** falta el Railway Config File del servicio (arriba).
- **`{"detail":"Not Found"}` en el backend:** es normal en `/`. Prueba `/health`.
- **`/health` da `documents: 0`:** el corpus no se sembró (repite A4).
- **`/health` da `documents: null`:** el backend no ve a ChromaDB (revisa `CHROMA_HOST`/nombre del servicio).
- **La demo de la landing no responde:** falta `BACKEND_URL`, o CORS (pon la URL de la landing en `ALLOWED_ORIGINS`).
- **Backend se reinicia (OOM):** súbele la RAM.
- **El bot no muestra comandos:** revisa `DISCORD_TOKEN` y que se invitó con `applications.commands`.
