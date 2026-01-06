import asyncio
import aiomqtt

from settings import settings
from core import core

async def main():
    kwargs = {
        "hostname": settings.mqtt_broker_host,
        "port": settings.mqtt_broker_port,
        "username": settings.mqtt_client_username,
        "password": settings.mqtt_client_password,
    }

    async with aiomqtt.Client(**kwargs) as client:
        await core.run(client)

if __name__ == "__main__":
    asyncio.run(main())
