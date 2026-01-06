import asyncio
from typing import Literal

from aiomqtt.types import PayloadType
from pydantic import BaseModel
from pydantic_core import ValidationError

from mqtt_client.core import core
from mqtt_client.settings import settings
from mqtt_client.util import VerificationError

from .protocol import *

IF_ID = "IF_04"
IF_SYSID = "45BDA-12A3DASD-1231-1E12-3123D3DAZ23"
IF_HOST = "CRKPNTCHAI"
IF_DATE = "20240503152229"

HEADER = {
    "IF_ID": IF_ID,
    "IF_SYSID": IF_SYSID,
    "IF_HOST": IF_HOST,
    "IF_DATE": IF_DATE,
}


class CollectDoorReqData(ReqData):
    door_state: Literal["OPEN", "CLOSE"]


class CollectDoorReqMessage(BaseModel):
    HEADER: Header
    DATA: CollectDoorReqData


class CollectDoorAckData(AckData):
    door_state: Literal["OPEN", "CLOSE"]
    camera_status: str
    deadbolt_status: str
    loadcell_status: str


class CollectDoorAckMessage(BaseModel):
    HEADER: Header
    DATA: CollectDoorAckData


@core.router.register(
    subscribe_topic="chai/device/{DEVICE_ID}/cmd/door/collect",
    publish_topic="chai/device/{DEVICE_ID}/ack/door/collect",
)
async def collect_door_handler(payload: PayloadType):
    if not isinstance(payload, (str, bytes, bytearray)):
        return None

    try:
        req_message = ReqMessage.model_validate_json(payload)
    except ValidationError as e:
        return None
