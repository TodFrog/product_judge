import asyncio

from protocol import Protocol, PayloadDict, ErrorPayload

queue = asyncio.Queue()

async def handle_reading(reader: asyncio.StreamReader):
    try:
        while True:
            raw_request = await reader.readuntil(b'\x03') + await reader.readexactly(1)  # Read until ETX and checksum
            request = Protocol.parse(raw_request)
            print("Received message:", request)
            queue.put_nowait(request)
    except asyncio.CancelledError:
        pass
    finally:
        print("Closing reading task")

async def handle_writing(writer: asyncio.StreamWriter):
    try:
        while True:
            request = await queue.get()
            
            try:
                req_payload = PayloadDict[(request.service_code, request.message_type)].parse(request.payload)
                print("Parsed payload:", req_payload)
            except:
                req_payload = ErrorPayload.parse(request.payload)
                print("Parsed error payload:", req_payload)

            if request.service_code == b'PS' and request.message_type == b'10':
                resp_payload = PayloadDict[(b'TQ', b'10')].build({'data': ''})
                raw_request = Protocol.build({'service_code': b'TQ', 'message_type': b'10', 'payload': resp_payload})
                writer.write(raw_request)

            elif request.service_code == b'PA' and request.message_type == b'10':
                resp_payload = PayloadDict[(b'D1', b'10')].build({'amount': '5000', 'authorization_type': 'PRE_AUTH'})
                pay_accept_reqeust = Protocol.build({'service_code': b'D1', 'message_type': b'10', 'payload': resp_payload})
                writer.write(pay_accept_reqeust)
            
            await writer.drain()
    except asyncio.CancelledError:
        pass
    finally:
        print("Closing writing task")
        writer.close()

async def handle_payment(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    reading_task = asyncio.create_task(handle_reading(reader))
    writing_task = asyncio.create_task(handle_writing(writer))
    try:
        await asyncio.gather(reading_task, writing_task)
    except Exception as e:
        print("Error in handle_payment:", e)
    finally:
        reading_task.cancel()
        writing_task.cancel()
        await asyncio.gather(reading_task, writing_task, return_exceptions=True)
        writer.close()

async def main():
    server = await asyncio.start_server(handle_payment, "0.0.0.0", 5000)
    print("Server started on port 5000...")
    async with server:
        await server.serve_forever()
    
if __name__ == "__main__":
    asyncio.run(main())
