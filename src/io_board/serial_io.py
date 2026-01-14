import asyncio
import serial
import serial_asyncio

from protocol import RequestProtocol, ResponseProtocol

serial_mutex = asyncio.Lock()

configuration = {
    "url": "/dev/ttyUSB0",
    "baudrate": 38400,
}

reader: asyncio.StreamReader | None = None
writer: asyncio.StreamWriter | None = None


def configure_serial(url: str, baudrate: int):
    configuration["url"] = url
    configuration["baudrate"] = baudrate


async def _fetch(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, message: bytes
) -> bytes:
    writer.write(message)
    await writer.drain()
    response = b""
    response += await asyncio.wait_for(
        reader.readexactly(1), timeout=0.2
    )  # Read Start of Text
    response += await asyncio.wait_for(
        reader.readuntil(b"\x03"), timeout=1.0
    )  # Read until End of Text
    response += await asyncio.wait_for(
        reader.readexactly(1), timeout=0.2
    )  # Read Checksum
    return response


async def fetch(message: bytes) -> bytes:
    async with serial_mutex:
        try:
            reader, writer = await serial_asyncio.open_serial_connection(
                url=configuration["url"],
                baudrate=configuration["baudrate"],
            )
        except serial.SerialException as e:
            raise RuntimeError(f"Failed to open serial port: {e}") from e
        try:
            retry = 0
            while retry < 3:
                try:
                    response = await _fetch(reader, writer, message)
                    return response
                except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                    if retry >= 3:
                        raise
                    retry += 1
                    await asyncio.sleep(0.1)
        finally:
            writer.close()
            await writer.wait_closed()
    return b""  # This line should never be reached


async def io_board_init():
    req_message = RequestProtocol.build(dict(COMMAND="MC", SUBCOMMAND="PD", DATA={}))
    resp_message = await fetch(req_message)
    resp = ResponseProtocol.parse(resp_message)


async def io_board_set_door(state: str):
    req_message = RequestProtocol.build(
        dict(COMMAND="MC", SUBCOMMAND="DC", DATA=dict(DOOR=state))
    )
    resp_message = await fetch(req_message)
    resp = ResponseProtocol.parse(resp_message)
    return resp.DATA.DOOR


async def io_board_calibrate():
    req_message = RequestProtocol.build(dict(COMMAND="MC", SUBCOMMAND="LZ", DATA={}))
    resp_message = await fetch(req_message)
    resp = ResponseProtocol.parse(resp_message)


async def io_board_set_manufacturing_number(manufacturing_number: str):
    req_message = RequestProtocol.build(
        dict(COMMAND="MC", SUBCOMMAND="WP", DATA=dict(PRODUCT_ID=manufacturing_number))
    )
    resp_message = await fetch(req_message)
    resp = ResponseProtocol.parse(resp_message)
    return resp.DATA.PRODUCT_ID


async def io_board_clear_errors():
    req_message = RequestProtocol.build(dict(COMMAND="MC", SUBCOMMAND="EZ", DATA={}))
    resp_message = await fetch(req_message)
    resp = ResponseProtocol.parse(resp_message)


async def io_board_reboot():
    req_message = RequestProtocol.build(dict(COMMAND="MC", SUBCOMMAND="RT", DATA={}))
    resp_message = await fetch(req_message)
    resp = ResponseProtocol.parse(resp_message)


async def io_board_get_product_info():
    req_message = RequestProtocol.build(dict(COMMAND="RQ", SUBCOMMAND="MI", DATA={}))
    resp_message = await fetch(req_message)
    resp = ResponseProtocol.parse(resp_message)
    return dict(
        product_id=resp.DATA.PRODUCT_ID,
        sw_version=resp.DATA.SW_VERSION,
    )


async def io_board_get_loadcells():
    req_message = RequestProtocol.build(dict(COMMAND="RQ", SUBCOMMAND="IW", DATA={}))
    resp_message = await fetch(req_message)
    resp = ResponseProtocol.parse(resp_message)
    return list(resp.DATA.LOADCELLS)


async def io_board_get_status():
    req_message = RequestProtocol.build(dict(COMMAND="RQ", SUBCOMMAND="ID", DATA={}))
    resp_message = await fetch(req_message)
    resp = ResponseProtocol.parse(resp_message)
    return dict(
        door=resp.DATA.DOOR,
        deadbolt=resp.DATA.DEADBOLT,
    )


async def io_board_get_errors():
    req_message = RequestProtocol.build(dict(COMMAND="RQ", SUBCOMMAND="ER", DATA={}))
    resp_message = await fetch(req_message)
    resp = ResponseProtocol.parse(resp_message)
    return list(resp.DATA.ERRORS)
