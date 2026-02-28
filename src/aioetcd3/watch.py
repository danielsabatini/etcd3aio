import asyncio
from typing import AsyncIterator, Optional, Union

from ._protobuf import WatchCreateRequest, WatchRequest, WatchResponse, WatchStub


class WatchService:
    """Notificações de eventos PUT/DELETE via streams [18, 19]."""

    def __init__(self, channel):
        self._stub = WatchStub(channel)

    async def watch(
        self,
        key: Union[str, bytes],
        range_end: Optional[Union[str, bytes]] = None,
        start_revision: int = 0,
        prev_kv: bool = False,
    ) -> AsyncIterator['WatchResponse']:
        """Cria um watcher que cede controle ao Event Loop enquanto aguarda [20, 21]."""

        async def request_generator():
            create_request = WatchCreateRequest(
                key=self._to_bytes(key),
                range_end=self._to_bytes(range_end) if range_end else b'',
                start_revision=start_revision,
                prev_kv=prev_kv,
            )
            yield WatchRequest(create_request=create_request)
            while True:
                await asyncio.sleep(3600)  # Mantém o stream aberto [22]

        responses = self._stub.Watch(request_generator())
        async for response in responses:
            yield response

    def _to_bytes(self, data: Union[str, bytes]) -> bytes:
        return data.encode('utf-8') if isinstance(data, str) else data
