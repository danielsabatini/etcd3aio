from __future__ import annotations

import asyncio

from aioetcd3.client import Etcd3Client


async def main() -> None:
    async with Etcd3Client(['localhost:2379']) as client:
        await client.kv.put('demo:key', 'demo:value')
        get_response = await client.kv.get('demo:key')

        if get_response.kvs:
            print(get_response.kvs[0].value.decode('utf-8'))


if __name__ == '__main__':
    asyncio.run(main())
