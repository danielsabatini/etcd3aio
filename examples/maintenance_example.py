from __future__ import annotations

import argparse
import asyncio
import logging

from etcd3aio.client import Etcd3Client
from etcd3aio.maintenance import AlarmType, MaintenanceService

logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s: %(message)s')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Maintenance example against etcd.')
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=['localhost:2379'],
        help='List of etcd endpoints in host:port format.',
    )
    return parser.parse_args()


async def run_maintenance_example(maintenance: MaintenanceService) -> None:
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


async def main() -> None:
    args = parse_args()

    async with Etcd3Client(args.endpoints) as client:
        maintenance = client.maintenance
        if maintenance is None:
            raise RuntimeError('maintenance service is not initialized')

        await run_maintenance_example(maintenance)


if __name__ == '__main__':
    asyncio.run(main())
