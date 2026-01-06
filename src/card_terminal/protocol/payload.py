from construct import (
    Bytes,
    Const,
    GreedyString,
    If,
    NullTerminated,
    Optional,
    PaddedString,
    Struct,
)

from .const import ResponseCode, AuthorizationType, StatusCode

Notification = Struct(
    "response_code" / ResponseCode,
    Const(b"\x1e"),
    "message" / GreedyString("euc-kr"),
)

Error = Struct(
    "status" / Const(b"N"),
    Const(b"\x1c"),
    "notification" / NullTerminated(Notification, term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

CardInfo = Struct(
    "serial_number"
    / NullTerminated(GreedyString("ascii"), term=b"\x1e", consume=False),
    Const(b"\x1e"),
    "acquirer_id" / PaddedString(3, "ascii"),
    Const(b"\x1e"),
    "acquirer_name"
    / NullTerminated(GreedyString("euc-kr"), term=b"\x1e", consume=False),
    Const(b"\x1e"),
    "issuer_id" / PaddedString(3, "ascii"),
    Const(b"\x1e"),
    "issuer_name" / NullTerminated(GreedyString("euc-kr"), term=b"\x1e", consume=False),
    Const(b"\x1e"),
    "merchant_id" / GreedyString("ascii"),
)

PPRequest = Struct(
    Const(b"\x1c"),
)

PPResponse = Struct(
    Const(b"\x1c"),
    "message" / NullTerminated(GreedyString("euc-kr"), term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

PSRequest = Struct(
    Const(b"\x1c"),
)

PSResponse = Struct(
    Const(b"\x1c"),
    "message" / NullTerminated(GreedyString("euc-kr"), term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

TQRequest = Struct(
    "data" / NullTerminated(GreedyString("euc-kr"), term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

TQResponse = Struct(
    "status" / StatusCode,
    Const(b"\x1c"),
    "VANKEYHASH" / If(lambda ctx: ctx.status == 'Y', Bytes(24)),
    Const(b"\x1c"),
    "card_info"
    / If(
        lambda ctx: ctx.status == 'Y',
        NullTerminated(CardInfo, term=b"\x1c", consume=False),
    ),
    Const(b"\x1c"),
    "notification" / NullTerminated(Notification, term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

D8Request = Struct(
    "amount" / NullTerminated(GreedyString("ascii"), term=b"\x1c", consume=False),
    Const(b"\x1c"),
    "VANKEYHASH" / Optional(Bytes(24)),
    Const(b"\x1c"),
)

D8Response = Struct(
    "status" / StatusCode,
    Const(b"\x1c"),
    "transaction_id" / If(lambda ctx: ctx.status == 'Y', Bytes(8)),
    Const(b"\x1c"),
    "card_info"
    / If(
        lambda ctx: ctx.status == 'Y',
        NullTerminated(CardInfo, term=b"\x1c", consume=False),
    ),
    Const(b"\x1c"),
    "VANKEY" / If(lambda ctx: ctx.status == 'Y', Bytes(16)),
    Const(b"\x1c"),
    "notification" / NullTerminated(Notification, term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

D9Request = Struct(
    "amount" / NullTerminated(GreedyString("ascii"), term=b"\x1c", consume=False),
    Const(b"\x1c"),
    "original_transaction_id" / Bytes(8),
    Const(b"\x1c"),
    "original_transaction_date" / Bytes(6),
    Const(b"\x1c"),
    "VANKEYHASH" / Optional(Bytes(24)),
    Const(b"\x1c"),
)

D9Response = Struct(
    "status" / StatusCode,
    Const(b"\x1c"),
    "card_info"
    / If(
        lambda ctx: ctx.status == 'Y',
        NullTerminated(CardInfo, term=b"\x1c", consume=False),
    ),
    Const(b"\x1c"),
    "VANKEY" / If(lambda ctx: ctx.status == 'Y', Bytes(16)),
    Const(b"\x1c"),
    "notification" / NullTerminated(Notification, term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

PARequest = Struct(
    Const(b"\x1c"),
)

PAResponse = Struct(
    Const(b"\x1c"),
    "message" / NullTerminated(GreedyString("euc-kr"), term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

D1Request = Struct(
    "amount" / NullTerminated(GreedyString("ascii"), term=b"\x1c", consume=False),
    Const(b"\x1c"),
    "authorization_type" / AuthorizationType,
    Const(b"\x1c"),
)

D1Response = Struct(
    "status" / StatusCode,
    Const(b"\x1c"),
    "transaction_id" / If(lambda ctx: ctx.status == 'Y', Bytes(8)),
    Const(b"\x1c"),
    "VANKEY" / If(lambda ctx: ctx.status == 'Y', Bytes(16)),
    Const(b"\x1c"),
    "card_info"
    / If(
        lambda ctx: ctx.status == 'Y',
        NullTerminated(CardInfo, term=b"\x1c", consume=False),
    ),
    Const(b"\x1c"),
    "notification" / NullTerminated(Notification, term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

D7Request = Struct(
    "amount" / NullTerminated(GreedyString("ascii"), term=b"\x1c", consume=False),
    Const(b"\x1c"),
    "original_transaction_id" / Bytes(8),
    Const(b"\x1c"),
    "original_transaction_date" / Bytes(6),
    Const(b"\x1c"),
    "VANKEY" / Bytes(16),
    Const(b"\x1c"),
)

D7Response = Struct(
    "status" / StatusCode,
    Const(b"\x1c"),
    "card_info"
    / If(
        lambda ctx: ctx.status == 'Y',
        NullTerminated(CardInfo, term=b"\x1c", consume=False),
    ),
    Const(b"\x1c"),
    "VANKEY" / If(lambda ctx: ctx.status == 'Y', Bytes(16)),
    Const(b"\x1c"),
    "notification" / NullTerminated(Notification, term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

PCRequest = Struct(
    "message" / NullTerminated(GreedyString("euc-kr"), term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

PCResponse = Struct(
    "notification" / NullTerminated(Notification, term=b"\x1c", consume=False),
    Const(b"\x1c"),
)

PayloadDict = {
    (b"PP", b"10"): PPRequest,
    (b"PP", b"20"): PPResponse,
    (b"PS", b"10"): PSRequest,
    (b"PS", b"20"): PSResponse,
    (b"TQ", b"10"): TQRequest,
    (b"TQ", b"20"): TQResponse,
    (b"D8", b"10"): D8Request,
    (b"D8", b"20"): D8Response,
    (b"D9", b"10"): D9Request,
    (b"D9", b"20"): D9Response,
    (b"PA", b"10"): PARequest,
    (b"PA", b"20"): PAResponse,
    (b"D1", b"10"): D1Request,
    (b"D1", b"20"): D1Response,
    (b"D7", b"10"): D7Request,
    (b"D7", b"20"): D7Response,
    (b"PC", b"10"): PCRequest,
    (b"PC", b"20"): PCResponse,
}

ErrorPayload = Error
