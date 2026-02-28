from unittest.mock import patch

import pytest

from aioetcd3.connections import ConnectionManager


@pytest.fixture
def endpoints():
    """Retorna endpoints padrão para testes de conexão [2]."""
    return ['localhost:2379', 'localhost:3379', 'localhost:4379']


@pytest.mark.asyncio
async def test_target_formatting(endpoints):
    """Valida se o target é formatado corretamente com prefixo
    ipv4 e substituição de localhost [3]."""
    manager = ConnectionManager(endpoints)
    assert manager.target == 'ipv4:127.0.0.1:2379,127.0.0.1:3379,127.0.0.1:4379'


@pytest.mark.asyncio
async def test_grpc_options(endpoints):
    """Verifica se as opções de Round-robin e KeepAlive são injetadas no canal [1, 3]."""
    manager = ConnectionManager(endpoints)
    with patch('grpc.aio.insecure_channel') as mock:
        await manager.get_channel()
        _, kwargs = mock.call_args
        opts = kwargs['options']

        # Valida balanceamento Round-robin exigido pelo design moderno do etcd [4]
        assert ('grpc.lb_policy_name', 'round_robin') in opts

        # CORREÇÃO: Linha completa validando a chave do KeepAlive nas tuplas de opções [1]
        assert any(k == 'grpc.keepalive_time_ms' for k, v in opts)
