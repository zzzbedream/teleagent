import os
import sys
import asyncio
import logging

from dotenv import load_dotenv
from web3 import AsyncWeb3, WebSocketProvider
from sqlalchemy import update, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.models import User

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

WSS_URL = os.getenv("WSS_URL", "wss://api.avax-test.network/ext/bc/C/ws")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/teleagent")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
EVENT_SIGNATURE = "CreditsPurchased(address,uint256)"
INITIAL_RETRY_DELAY_SECONDS = 1
MAX_RETRY_DELAY_SECONDS = 60

ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "CreditsPurchased",
        "type": "event"
    }
]

# Dedupe de eventos ya acreditados (MVP en memoria; en producción, tabla processed_events).
_processed_events: set = set()

async def process_event(event, async_session):
    try:
        event_key = (event['transactionHash'].hex(), event['logIndex'])
        if event_key in _processed_events:
            logging.info(f"Event {event_key} already processed. Skipping.")
            return

        user_address = event['args']['user']
        amount = int(event['args']['amount'])

        logging.info(f"Detected payment of {amount} wei from {user_address}")

        async with async_session() as session:
            stmt = (
                update(User)
                .where(User.wallet_address.ilike(user_address))
                .values(api_credits=func.coalesce(User.api_credits, 0) + amount)
            )
            result = await session.execute(stmt)
            await session.commit()

            if result.rowcount > 0:
                logging.info(f"Credited {amount} wei to wallet {user_address}.")
            else:
                logging.warning(f"Wallet {user_address} not linked to any Discord account. Ignoring.")

        _processed_events.add(event_key)
    except Exception as e:
        logging.error(f"Error processing event: {e}")

async def listen_for_events():
    if not CONTRACT_ADDRESS or CONTRACT_ADDRESS.lower() == ZERO_ADDRESS:
        logging.error("CONTRACT_ADDRESS is not set. Configure it in .env before running the indexer.")
        return

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    retry_delay = INITIAL_RETRY_DELAY_SECONDS

    while True:
        try:
            logging.info(f"Connecting to WSS: {WSS_URL}")
            async with AsyncWeb3(WebSocketProvider(WSS_URL)) as w3:
                logging.info("Connected to WebSocket. Subscribing to contract events...")
                retry_delay = INITIAL_RETRY_DELAY_SECONDS

                contract_address_checksum = w3.to_checksum_address(CONTRACT_ADDRESS)
                contract = w3.eth.contract(address=contract_address_checksum, abi=ABI)
                event_topic = w3.keccak(text=EVENT_SIGNATURE).to_0x_hex()

                await w3.eth.subscribe("logs", {
                    "address": contract_address_checksum,
                    "topics": [event_topic]
                })

                logging.info("Listening for CreditsPurchased events...")

                async for payload in w3.socket.process_subscriptions():
                    event = contract.events.CreditsPurchased().process_log(payload["result"])
                    await process_event(event, async_session)

        except Exception as e:
            logging.error(f"WebSocket connection lost or error occurred: {e}")
            logging.info(f"Reconnecting in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY_SECONDS)  # Exponential backoff

if __name__ == "__main__":
    asyncio.run(listen_for_events())
