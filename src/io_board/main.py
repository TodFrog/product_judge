import asyncio

from .api import serve_api
from .serial import serve_serial

async def main():
    await asyncio.gather(
        serve_serial(device='/dev/ttyUSB0', baudrate=38400),
        serve_api(host='0.0.0.0', port=8000, log_level="info"),
    )

if __name__ == "__main__":
    asyncio.run(main())