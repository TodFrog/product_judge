from typing import Literal
from fastapi import FastAPI
from pydantic import BaseModel, Field
import uvicorn
from uvicorn.config import Config
from uvicorn.server import Server

from .serial import *

app = FastAPI()

@app.post("/init")
async def handle_init():
    await io_board_init()

class Deadbolt(BaseModel):
    state: Literal["open", "close"]
@app.post("/deadbolt")
async def handle_deadbolt(deadbolt: Deadbolt) -> Deadbolt:
    if deadbolt.state not in ("open", "close"):
        raise ValueError("Invalid deadbolt state")
    if deadbolt.state == "open":
        state = "O"
    else:
        state = "C"
    state = await io_board_set_door(state)
    return Deadbolt(state="open" if state == "O" else "close")

@app.post("/calibrate")
async def handle_calibrate():
    await io_board_calibrate()

class ManufacturingNumber(BaseModel):
    manufacturing_number: str = Field(..., min_length=11, max_length=11)
@app.post("/manufacturing_number")
async def handle_manufacturing_number(manufacturing_number: ManufacturingNumber) -> ManufacturingNumber:
    manufacturing_number_str = manufacturing_number.manufacturing_number
    result = await io_board_set_manufacturing_number(manufacturing_number_str)
    return ManufacturingNumber(manufacturing_number=result)
    

@app.delete("/errors")
async def handle_clear_errors():
    await io_board_clear_errors()

@app.post("/reboot")
async def handle_reboot():
    await io_board_reboot()

class ProductInfo(BaseModel):
    product_id: str
    sw_version: str
@app.get("/product_info")
async def handle_product_info() -> ProductInfo:
    info = await io_board_get_product_info()
    return ProductInfo(
        product_id=info["product_id"],
        sw_version=info["sw_version"],
    )

class LoadCell(BaseModel):
    value: str
@app.get("/loadcells")
async def handle_loadcells() -> list[LoadCell]:
    loadcells = await io_board_get_loadcells()
    return [LoadCell(value=lc) for lc in loadcells]

class Status(BaseModel):
    door: str
    deadbolt: str
@app.get("/status")
async def handle_status() -> Status:
    status = await io_board_get_status()
    return Status(
        door=status["door"],
        deadbolt=status["deadbolt"],
    )

class Error(BaseModel):
    code: str
@app.get("/errors")
async def handle_errors() -> list[Error]:
    errors = await io_board_get_errors()
    return [Error(code=err) for err in errors]

async def serve_api(host, port, log_level="info"):
    config = Config(app=app, host=host, port=port, log_level=log_level)
    server = Server(config=config)
    await server.serve()