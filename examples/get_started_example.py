from __future__ import annotations

import asyncio

from etcd3aio import Etcd3Client, EtcdConnectionError
from etcd3aio.kv import prefix_range_end


async def main() -> None:
    async with Etcd3Client(['localhost:2379']) as client:
        # Verify cluster is healthy and reachable
        await client.ping()
        print('ping -> cluster is reachable')

        kv = client.kv
        if kv is None:
            raise RuntimeError('kv service is not initialized')

        # Put / Get / Delete
        await kv.put('myapp/greeting', 'hello-etcd')
        resp = await kv.get('myapp/greeting')
        print(f'get -> {resp.kvs[0].value.decode()}')

        await kv.delete('myapp/greeting')
        resp = await kv.get('myapp/greeting')
        print(f'after delete -> exists={bool(resp.kvs)}')

        # Prefix scan
        for i in range(3):
            await kv.put(f'myapp/item/{i}', f'value-{i}')
        resp = await kv.get('myapp/item/', range_end=prefix_range_end('myapp/item/'))
        print(f'prefix scan -> {len(resp.kvs)} keys found')
        await kv.delete('myapp/item/', range_end=prefix_range_end('myapp/item/'))

        # Distributed lock
        async with client.lock('myapp/resource'):
            print('lock -> acquired exclusive section')
        print('lock -> released')

        # Leader election
        async with client.election('myapp/leader', value=b'node-1'):
            print('election -> this node is the leader')
        print('election -> resigned')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except EtcdConnectionError as exc:
        print(f'Error: could not connect to etcd -> {exc}')
        raise SystemExit(1) from None
