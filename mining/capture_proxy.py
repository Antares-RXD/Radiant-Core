#!/usr/bin/env python3
"""
Simple TCP proxy to capture stratum traffic between ASIC and Whalepool
"""
import asyncio
import sys

LISTEN_PORT = 3333
UPSTREAM_HOST = "rxd.us1.whalepool.com"
UPSTREAM_PORT = 12110

async def pipe(reader, writer, label):
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            print(f"{label}: {data.decode().strip()}")
            writer.write(data)
            await writer.drain()
    except Exception as e:
        print(f"{label} error: {e}")
    finally:
        writer.close()

async def handle_client(client_reader, client_writer):
    client_addr = client_writer.get_extra_info('peername')
    print(f"Client connected: {client_addr}")
    
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(
            UPSTREAM_HOST, UPSTREAM_PORT
        )
        print(f"Connected to upstream: {UPSTREAM_HOST}:{UPSTREAM_PORT}")
        
        await asyncio.gather(
            pipe(client_reader, upstream_writer, "ASIC->POOL"),
            pipe(upstream_reader, client_writer, "POOL->ASIC")
        )
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_writer.close()
        print(f"Client disconnected: {client_addr}")

async def main():
    server = await asyncio.start_server(handle_client, '0.0.0.0', LISTEN_PORT)
    print(f"Capture proxy listening on port {LISTEN_PORT}")
    print(f"Forwarding to {UPSTREAM_HOST}:{UPSTREAM_PORT}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
