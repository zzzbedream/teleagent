import os
import re
import sys
import logging

import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.models import User, normalize_async_db_url

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = normalize_async_db_url(os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/teleagent"))
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8001/query")

COST_PER_QUERY_WEI = 100_000_000_000_000_000  # 0.1 AVAX
# Cortesía: cada cuenta nueva recibe consultas gratis al vincular su wallet.
# Elimina la fricción para jueces/nuevos usuarios sin romper el modelo de pago (free trial → pago).
FREE_TRIAL_QUERIES = 5
FREE_TRIAL_CREDITS = FREE_TRIAL_QUERIES * COST_PER_QUERY_WEI
DISCORD_MESSAGE_LIMIT = 1950

def is_valid_evm_address(address: str) -> bool:
    return bool(re.match(r"^0x[a-fA-F0-9]{40}$", address))

class TeleAgentBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

        self.engine = create_async_engine(DATABASE_URL, echo=False)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def setup_hook(self):
        await self.tree.sync()
        logging.info("Bot is ready and slash commands synced.")

bot = TeleAgentBot()

async def charge_user(discord_id: str) -> bool:
    """Descuenta el costo de una consulta de forma atómica; False si el saldo no alcanza."""
    async with bot.async_session() as session:
        stmt = (
            update(User)
            .where(User.discord_id == discord_id, User.api_credits >= COST_PER_QUERY_WEI)
            .values(api_credits=User.api_credits - COST_PER_QUERY_WEI)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

async def refund_user(discord_id: str):
    """Devuelve el costo de la consulta cuando el RAG no pudo responder."""
    async with bot.async_session() as session:
        stmt = (
            update(User)
            .where(User.discord_id == discord_id)
            .values(api_credits=func.coalesce(User.api_credits, 0) + COST_PER_QUERY_WEI)
        )
        await session.execute(stmt)
        await session.commit()

@bot.tree.command(name="link_wallet", description="Vincular tu billetera EVM para recibir créditos.")
@app_commands.describe(address="Tu dirección EVM (0x...)")
async def link_wallet(interaction: discord.Interaction, address: str):
    if not is_valid_evm_address(address):
        await interaction.response.send_message("Dirección EVM inválida. Asegúrate de que empiece con 0x y tenga 42 caracteres.", ephemeral=True)
        return

    discord_id = str(interaction.user.id)

    try:
        async with bot.async_session() as session:
            stmt = select(User).where(User.discord_id == discord_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                user.wallet_address = address
                await session.commit()
                await interaction.response.send_message(f"✅ Billetera actualizada a: `{address}`", ephemeral=True)
            else:
                new_user = User(discord_id=discord_id, wallet_address=address, api_credits=FREE_TRIAL_CREDITS)
                session.add(new_user)
                await session.commit()
                await interaction.response.send_message(
                    f"✅ Cuenta vinculada con la billetera: `{address}`\n"
                    f"🎁 Te regalamos **{FREE_TRIAL_QUERIES} consultas gratis** para que pruebes ahora mismo con `/ask`.\n"
                    f"Cuando se acaben, envía AVAX al contrato para recargar.",
                    ephemeral=True,
                )
    except IntegrityError:
        await interaction.response.send_message("❌ Esa billetera ya está vinculada a otra cuenta de Discord.", ephemeral=True)

@bot.tree.command(name="ask", description="Pregúntale a TeleAgent sobre Avalanche9000.")
@app_commands.describe(pregunta="Tu consulta técnica")
async def ask(interaction: discord.Interaction, pregunta: str):
    await interaction.response.defer(thinking=True)

    discord_id = str(interaction.user.id)

    if not await charge_user(discord_id):
        await interaction.followup.send(
            "❌ Saldo insuficiente o cuenta no vinculada.\n"
            "• ¿Primera vez? Usa `/link_wallet 0xTuDireccion` y recibes **5 consultas gratis**.\n"
            "• ¿Ya las usaste? Recarga enviando 0.1 AVAX al contrato "
            "(consíguelo gratis en el faucet de Fuji: https://core.app/tools/testnet-faucet/)."
        )
        return

    error_message = None
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(FASTAPI_URL, json={"prompt": pregunta}) as response:
                if response.status == 200:
                    data = await response.json()
                    answer = data.get("answer") or "No obtuve contenido de la documentación para esta consulta."

                    if len(answer) > DISCORD_MESSAGE_LIMIT:
                        answer = answer[:DISCORD_MESSAGE_LIMIT] + "..."

                    await interaction.followup.send(answer)
                    return
                if response.status == 503:
                    error_message = "⚠️ Error: La base de datos vectorial está caída (HTTP 503). Intenta más tarde."
                else:
                    error_message = f"⚠️ Error del servidor: HTTP {response.status}"
    except Exception as e:
        logging.error(f"Error querying FastAPI: {e}")
        error_message = "⚠️ Error interno de conexión con el RAG Engine."

    await refund_user(discord_id)
    await interaction.followup.send(f"{error_message} Tu crédito fue reembolsado.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logging.error("DISCORD_TOKEN no está configurado.")
    else:
        bot.run(DISCORD_TOKEN)
