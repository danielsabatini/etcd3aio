from typing import List, Optional

from .connections import ConnectionManager
from .kv import KVService
from .lease import LeaseService
from .watch import WatchService


class Etcd3Client:
    """Interface de alto nível que abstrai a complexidade gRPC [8]."""

    def __init__(self, endpoints: Optional[List[str]] = None, **conn_args):
        self._manager = ConnectionManager(endpoints or ['localhost:2379'])
        self._conn_args = conn_args
        self._channel = None
        self.kv: Optional[KVService] = None
        self.lease: Optional[LeaseService] = None
        self.watch: Optional[WatchService] = None

    async def __aenter__(self):
        """Inicializa a 'worker bee' gRPC ao entrar no contexto [20, 25]."""
        self._channel = await self._manager.get_channel(**self._conn_args)
        self.kv = KVService(self._channel)
        self.lease = LeaseService(self._channel)
        self.watch = WatchService(self._channel)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Garante o encerramento gracioso dos recursos [25, 26]."""
        if self._channel:
            await self._channel.close()
