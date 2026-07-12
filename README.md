# TeleAgent 🤖⛰️

**Asistente RAG autónomo para desarrolladores de Avalanche9000, con acceso pagado en AVAX nativo.**

Los devs de Avalanche pierden horas buscando en ACPs, docs y contratos de Teleporter — y los LLMs genéricos alucinan reglas pre-Etna (como el viejo requisito de 2,000 AVAX para Subnets, eliminado por la actualización Etna). TeleAgent responde **solo con documentación oficial indexada** (ACPs, Builders Hub, Teleporter/ICM) desde Discord, y se monetiza on-chain: cada consulta cuesta 0.1 AVAX pagados a un contrato en Fuji, sin pasarelas de pago ni tarjetas.

## Arquitectura

```
Discord (/ask, /link_wallet)
   │ defer + REST
   ▼
FastAPI  ──►  LangChain (DeepSeek) ──► ChromaDB (corpus Avalanche9000)
   ▲                                        ▲
   │ créditos                               │ ingesta (ACPs + Builders Hub + Teleporter)
   ▼                                        │
PostgreSQL ◄── Indexer (WSS + eth_subscribe, backoff exponencial)
                  ▲
                  │ evento CreditsPurchased
        TeleAgentAccess.sol (Fuji C-Chain)
```

- **Contrato:** `TeleAgentAccess.sol` en Avalanche Fuji — [`0x78cce8C167583bf358B3EA1c9C409e13A7Da691a`](https://testnet.snowtrace.io/address/0x78cce8C167583bf358B3EA1c9C409e13A7Da691a)
- **Stack:** Python 3.11+ · FastAPI · LangChain + DeepSeek · ChromaDB · PostgreSQL · discord.py · web3.py v7 · Foundry

## Quickstart (5 pasos)

Requisitos: Docker, Python 3.11+, [Foundry](https://book.getfoundry.sh/), una wallet con AVAX de [Fuji Faucet](https://core.app/tools/testnet-faucet/).

```bash
# 0. Configuración
cp .env.example .env   # completa DISCORD_TOKEN, DEEPSEEK_API_KEY, CONTRACT_ADDRESS
pip install -r backend/requirements.txt

# 1. Infraestructura + base de datos
docker compose up -d
python scripts/init_db.py

# 2. Corpus de conocimiento (ACPs + Builders Hub + Teleporter)
python scripts/fetch_repos.py
python backend/app/ingest.py

# 3. Contrato en Fuji (una sola vez; copia la dirección a .env de la raíz)
#    Antes: pon tu clave de testnet en contracts/.env (DEPLOYER_PRIVATE_KEY).
cd contracts && forge test && forge script script/Deploy.s.sol:DeployScript \
  --rpc-url https://api.avax-test.network/ext/bc/C/rpc --broadcast && cd ..

# 4. Servicios (tres terminales)
uvicorn app.main:app --port 8001 --app-dir backend
python indexer/indexer.py
python bot/bot.py
```

> ⚠️ El backend corre en el puerto **8001** (ChromaDB ocupa el 8000).

## Cómo probarlo (jueces del grant 👋)

1. En Discord: `/link_wallet 0xTuDireccion` — vincula tu billetera EVM.
2. Compra créditos: `cast send $CONTRACT_ADDRESS "deposit()" --value 0.1ether --rpc-url https://api.avax-test.network/ext/bc/C/rpc --private-key $PK`
3. El indexer acredita el pago en segundos (evento `CreditsPurchased`).
4. Pregunta: `/ask ¿Qué cambió con la actualización Etna?` — la respuesta cita fuentes oficiales y descuenta exactamente 0.1 AVAX de tu saldo.
5. Si el motor RAG falla, el crédito se reembolsa automáticamente.

¿Sin entorno local? Escríbenos y te invitamos al servidor demo de Discord con el bot ya desplegado.

## Estructura del repositorio

| Ruta | Descripción |
|---|---|
| `backend/` | API FastAPI + cadena RAG (LangChain → DeepSeek) + ingesta a ChromaDB |
| `bot/` | Bot de Discord (slash commands asíncronos con `defer`) |
| `indexer/` | Listener WSS de eventos on-chain con reconexión y backoff exponencial |
| `contracts/` | Contrato `TeleAgentAccess` + tests Foundry + script de deploy a Fuji |
| `database/` | Modelos SQLAlchemy (usuarios, créditos en wei) |
| `scripts/` | Fetch del corpus oficial y creación de tablas |

## Licencia

MIT
