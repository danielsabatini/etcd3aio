from __future__ import annotations

from typing import Any, cast
from unittest.mock import patch

import pytest

from etcd3aio.connections import ConnectionManager


@pytest.fixture
def endpoints() -> list[str]:
    return ['localhost:2379', 'localhost:3379', 'localhost:4379']


@pytest.mark.asyncio
async def test_target_formatting(endpoints: list[str]) -> None:
    manager = ConnectionManager(endpoints)
    assert manager.target == 'ipv4:127.0.0.1:2379,127.0.0.1:3379,127.0.0.1:4379'


@pytest.mark.asyncio
async def test_grpc_options(endpoints: list[str]) -> None:
    manager = ConnectionManager(endpoints)

    with patch('grpc.aio.insecure_channel') as insecure_channel_mock:
        await manager.get_channel()

    call_args = insecure_channel_mock.call_args
    assert call_args is not None

    kwargs = cast(dict[str, Any], call_args.kwargs)
    options = cast(list[tuple[str, object]], kwargs['options'])

    assert ('grpc.lb_policy_name', 'round_robin') in options
    assert any(key == 'grpc.keepalive_time_ms' for key, _ in options)


@pytest.mark.asyncio
async def test_tls_requires_ca_cert(endpoints: list[str]) -> None:
    manager = ConnectionManager(endpoints)

    with pytest.raises(ValueError, match='ca_cert is required'):
        await manager.get_channel(cert_key=b'key')
