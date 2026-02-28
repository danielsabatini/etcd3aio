from unittest.mock import patch
import pytest
from aioetcd3.connections import ConnectionManager

@pytest.fixture
def endpoints():
    return ['localhost:2379', 'localhost:3379', 'localhost:4379']

@pytest.mark.asyncio
async def test_target_formatting(endpoints):
    manager = ConnectionManager(endpoints)
    assert manager.target == 'ipv4:127.0.0.1:2379,127.0.0.1:3379,127.0.0.1:4379'

@pytest.mark.asyncio
async def test_grpc_options(endpoints):
    manager = ConnectionManager(endpoints)
    with patch('grpc.aio.insecure_channel') as mock:
        await manager.get_channel()
        _, kwargs = mock.call_args
        opts = kwargs['options']
        assert ('grpc.lb_policy_name', 'round_robin') in opts
        assert any(k == 'grpc.keepalive_time_ms' for k, v in o