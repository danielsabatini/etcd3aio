from __future__ import annotations

import argparse
import asyncio
import logging

from etcd3aio.client import Etcd3Client
from etcd3aio.maintenance import AlarmType, DowngradeAction, MaintenanceService

logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s: %(message)s')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Maintenance example against etcd.')
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=['localhost:2379'],
        help='List of etcd endpoints in host:port format.',
    )
    parser.add_argument(
        '--snapshot',
        action='store_true',
        help='Stream a snapshot from the cluster and print its total size.',
    )
    return parser.parse_args()


async def run_maintenance_example(maintenance: MaintenanceService, *, snapshot: bool) -> None:
    # Cluster member status
    status = await maintenance.status()
    print(
        f'Status -> leader={status.leader}, version={status.version}, db_size={status.dbSize} bytes'
    )

    # List active alarms
    alarms_resp = await maintenance.alarms()
    if alarms_resp.alarms:
        for alarm in alarms_resp.alarms:
            print(f'Alarm -> memberID={alarm.memberID}, type={AlarmType(alarm.alarm).name}')
    else:
        print('Alarms -> none active')

    # Deactivate all NOSPACE alarms (no-op if none exist)
    await maintenance.alarm_deactivate(AlarmType.NOSPACE)
    print('alarm_deactivate(NOSPACE) -> ok')

    # Defragment the backend database of the connected member
    await maintenance.defragment()
    print('defragment() -> ok')

    # Hash the KV store at the latest revision for consistency checks
    hkv = await maintenance.hash_kv()
    print(
        f'hash_kv() -> hash={hkv.hash:#010x}, '
        f'compact_revision={hkv.compact_revision}, '
        f'hash_revision={hkv.hash_revision}'
    )

    # Full-store hash (testing / cross-member consistency verification)
    h = await maintenance.hash()
    print(f'hash() -> hash={h.hash:#010x}')

    # Validate whether the cluster is eligible for a version downgrade
    # (VALIDATE does not change cluster state — safe to run anytime)
    try:
        dg = await maintenance.downgrade(DowngradeAction.VALIDATE, '3.5.0')
        print(f'downgrade(VALIDATE, "3.5.0") -> version={dg.version}')
    except Exception as exc:
        print(f'downgrade(VALIDATE) -> not eligible: {exc}')

    # Stream a binary snapshot (optional — large clusters can produce large snapshots)
    if snapshot:
        total = 0
        async for chunk in maintenance.snapshot():
            total += len(chunk)
        print(f'snapshot() -> received {total} bytes')


async def main() -> None:
    args = parse_args()

    async with Etcd3Client(args.endpoints) as client:
        maintenance = client.maintenance
        if maintenance is None:
            raise RuntimeError('maintenance service is not initialized')

        await run_maintenance_example(maintenance, snapshot=args.snapshot)


if __name__ == '__main__':
    asyncio.run(main())
