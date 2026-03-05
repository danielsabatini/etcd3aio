"""mTLS connection example for etcd3aio.

Demonstrates how to connect to an etcd cluster over mutual TLS (mTLS) using
a CA certificate, a client certificate, and a client private key.

Run against the local TLS cluster from docker/compose.yaml:

    bash docker/gen-certs.sh          # generate certificates once
    docker compose -f docker/compose.yaml up -d etcdtls1 etcdtls2 etcdtls3
    uv run python examples/tls_example.py

Use a custom certificate directory:

    uv run python examples/tls_example.py --certs-dir /path/to/certs
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from etcd3aio import Etcd3Client

logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s: %(message)s')

TLS_ENDPOINTS = ['localhost:5379', 'localhost:6379', 'localhost:7379']


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Connect to etcd over mTLS.')
    parser.add_argument(
        '--certs-dir',
        default='docker',
        help='Directory with server-ca.crt, client-cert.crt, client-key.key (default: docker/)',
    )
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=TLS_ENDPOINTS,
        help='TLS endpoints (default: localhost:5379 localhost:6379 localhost:7379)',
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    certs = Path(args.certs_dir)

    ca_cert = (certs / 'server-ca.crt').read_bytes()
    cert_chain = (certs / 'client-cert.crt').read_bytes()
    cert_key = (certs / 'client-key.key').read_bytes()

    async with Etcd3Client(
        args.endpoints,
        ca_cert=ca_cert,
        cert_chain=cert_chain,
        cert_key=cert_key,
        # Required for multi-endpoint TLS: gRPC encodes all addresses as a
        # comma-separated list and cannot derive a server name from it.
        # Set this to a DNS name present in the server certificate's SANs.
        tls_server_name='localhost',
    ) as client:
        # Connectivity check
        await client.ping()
        print(f'ping -> mTLS connection established ({len(args.endpoints)} endpoint(s))')

        # Basic KV round-trip
        key, value = 'tls-example/greeting', 'hello-over-tls'
        await client.kv.put(key, value)
        resp = await client.kv.get(key)
        print(f'put/get -> {resp.kvs[0].value.decode()}')
        await client.kv.delete(key)
        print('delete -> ok')

        # Cluster membership
        members = await client.cluster.member_list()
        print(f'member_list -> {len(members.members)} member(s)')
        for m in members.members:
            tag = ' [learner]' if m.isLearner else ''
            print(f'  id={m.ID}  name={m.name!r}{tag}')

        # Maintenance status
        status = await client.maintenance.status()
        print(f'maintenance.status -> version={status.version}  dbSize={status.dbSize}')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except FileNotFoundError as exc:
        print(f'Certificate file not found: {exc}')
        print('Run  bash docker/gen-certs.sh  to generate the certificates.')
        raise SystemExit(1) from None
    except Exception as exc:
        print(f'Error: {exc}')
        raise SystemExit(1) from None
