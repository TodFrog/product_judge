import asyncio

from api import serve_api
from serial_io import configure_serial


async def main():
    await asyncio.gather(
        serve_api(host="0.0.0.0", port=8000, log_level="info"),
    )


if __name__ == "__main__":
    configure_serial(url="COM3", baudrate=38400)
    asyncio.run(main())
