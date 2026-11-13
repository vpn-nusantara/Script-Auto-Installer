#!/usr/bin/env python3
# VPN NUSANTARA - jembatan SSH over WebSocket (nginx -> proxy ini -> OpenSSH)
import asyncio, os

LISTEN = int(os.environ.get("NUS_WS_PORT", "10015"))
TARGET = int(os.environ.get("NUS_SSH_PORT", "22"))
REPLY = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n"


async def pipe(r, w):
    try:
        while True:
            data = await r.read(65536)
            if not data:
                break
            w.write(data)
            await w.drain()
    except Exception:
        pass
    finally:
        try:
            w.close()
        except Exception:
            pass


async def handle(cr, cw):
    try:
        head = b""
        while b"\r\n\r\n" not in head and len(head) < 16384:
            chunk = await asyncio.wait_for(cr.read(4096), 15)
            if not chunk:
                cw.close()
                return
            head += chunk
        rest = head.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in head else b""
        sr, sw = await asyncio.open_connection("127.0.0.1", TARGET)
        cw.write(REPLY)
        await cw.drain()
        if rest:
            sw.write(rest)
            await sw.drain()
        await asyncio.gather(pipe(cr, sw), pipe(sr, cw))
    except Exception:
        try:
            cw.close()
        except Exception:
            pass


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.start_server(handle, "127.0.0.1", LISTEN))
    loop.run_forever()


if __name__ == "__main__":
    main()
