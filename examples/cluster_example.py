from __future__ import annotations

import argparse
import asyncio
import logging

from etcd3aio.client import Etcd3Client
from etcd3aio.cluster import ClusterService

logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s: %(message)s')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Cluster example against etcd.')
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=['localhost:2379'],
        help='List of etcd endpoints in host:port format.',
    )
    return parser.parse_args()


async def run_cluster_example(cluster: ClusterService) -> None:
    # List all cluster members
    resp = await cluster.member_list()
    print(f'member_list() -> {len(resp.members)} member(s)')
    for m in resp.members:
        learner_tag = ' [learner]' if m.isLearner else ''
        print(
            f'  id={m.ID}  name={m.name!r}  '
            f'peerURLs={list(m.peerURLs)}  '
            f'clientURLs={list(m.clientURLs)}{learner_tag}'
        )

    # Example: add a learner member, then promote and remove it.
    # Uncomment and adapt peer_urls to a real etcd peer endpoint before running.
    #
    # add_resp = await cluster.member_add(['http://10.0.0.4:2380'], is_learner=True)
    # new_id = add_resp.member.ID
    # print(f'member_add(learner) -> new member id={new_id}')
    #
    # # Promote the learner to a voting member (requires the learner to be in sync)
    # await cluster.member_promote(new_id)
    # print(f'member_promote({new_id}) -> ok')
    #
    # # Update peer URLs of the new member
    # await cluster.member_update(new_id, ['http://10.0.0.4:2381'])
    # print(f'member_update({new_id}) -> ok')
    #
    # # Remove the member from the cluster
    # await cluster.member_remove(new_id)
    # print(f'member_remove({new_id}) -> ok')


async def main() -> None:
    args = parse_args()

    async with Etcd3Client(args.endpoints) as client:
        cluster = client.cluster
        if cluster is None:
            raise RuntimeError('cluster service is not initialized')

        await run_cluster_example(cluster)


if __name__ == '__main__':
    asyncio.run(main())
