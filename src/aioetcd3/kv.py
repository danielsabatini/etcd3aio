from typing import Optional, Union

from ._protobuf import DeleteRangeRequest, KVStub, PutRequest, RangeRequest


class KVService:
    """Operações de dados com garantia de serializabilidade estrita [14]."""

    def __init__(self, channel):
        self._stub = KVStub(channel)

    async def put(
        self,
        key: Union[str, bytes],
        value: Union[str, bytes],
        lease: int = 0,
        prev_kv: bool = False,
    ):
        request = PutRequest(
            key=self._to_bytes(key), value=self._to_bytes(value), lease=lease, prev_kv=prev_kv
        )
        return await self._stub.Put(request)

    async def get(
        self,
        key: Union[str, bytes],
        range_end: Optional[Union[str, bytes]] = None,
        serializable: bool = False,
        revision: int = 0,
    ):
        request = RangeRequest(
            key=self._to_bytes(key),
            range_end=self._to_bytes(range_end) if range_end else b'',
            serializable=serializable,
            revision=revision,
        )
        return await self._stub.Range(request)

    async def delete(
        self,
        key: Union[str, bytes],
        range_end: Optional[Union[str, bytes]] = None,
        prev_kv: bool = False,
    ):
        request = DeleteRangeRequest(
            key=self._to_bytes(key),
            range_end=self._to_bytes(range_end) if range_end else b'',
            prev_kv=prev_kv,
        )
        return await self._stub.DeleteRange(request)

    def _to_bytes(self, data: Union[str, bytes]) -> bytes:
        return data.encode('utf-8') if isinstance(data, str) else data
