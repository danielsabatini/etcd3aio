from __future__ import annotations

from typing import List, Optional

from .connections import ConnectionManager
from .kv import KVService
from .lease import LeaseService
from .watch import WatchService


class Etcd3Client:
    """
    Interface principal para o cluster etcd v3.
    Unifica balanceamento, tratamento de erros e stubs de serviço [3].
    """

    def __init__(self, endpoints: Optional[List[str]] = None, **conn_args):
        self._manager = ConnectionManager(endpoints or ['localhost:2379'])
        self._conn_args = conn_args
        self._channel = None
        self.kv: Optional[KVService] = None
        self.lease: Optional[LeaseService] = None
        self.watch: Optional[WatchService] = None

    async def __aenter__(self) -> Etcd3Client:
        """Inicializa a conexão e os serviços ao entrar no contexto 'async with' [4]."""
        self._channel = await self._manager.get_channel(**self._conn_args)
        self.kv = KVService(self._channel)
        self.lease = LeaseService(self._channel)
        self.watch = WatchService(self._channel)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Garante que o canal gRPC seja fechado adequadamente [5]."""
        if self._channel:
            await self._channel.close()
