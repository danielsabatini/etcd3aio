from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from aioetcd3._protobuf import WatchResponse
from aioetcd3.watch import WatchService


class FakeRpcError(grpc.aio.AioRpcError):
    def __init__(self, status_code: grpc.StatusCode) -> None:
        self._status_code = status_code

    def code(self) -> grpc.StatusCode:
        return self._status_code


class FakeWatchStream:
    def __init__(
        self,
        responses: list[WatchResponse] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._responses = responses or []
        self._error = error
        self.cancelled = False

    def __aiter__(self) -> FakeWatchStream:
        return self

    async def __anext__(self) -> WatchResponse:
        if self._error is not None:
            error = self._error
            self._error = None
            raise error

        if self._responses:
            return self._responses.pop(0)

        raise StopAsyncIteration

    def cancel(self) -> None:
        self.cancelled = True


@pytest.mark.asyncio
async def test_watch_reconnects_on_transient_error() -> None:
    first_stream = FakeWatchStream(error=FakeRpcError(grpc.StatusCode.UNAVAILABLE))

    expected_revision = 7
    second_response = WatchResponse()
    second_response.header.revision = expected_revision
    second_stream = FakeWatchStream(responses=[second_response])

    stub = MagicMock()
    stub.Watch = MagicMock(side_effect=[first_stream, second_stream])

    with (
        patch('aioetcd3.watch.WatchStub', return_value=stub),
        patch('aioetcd3.watch.asyncio.sleep', new=AsyncMock()) as sleep_mock,
    ):
        service = WatchService(channel=MagicMock())
        watch_iterator = cast(
            AsyncGenerator[WatchResponse, None],
            service.watch('my-key', start_revision=3),
        )
        response = await anext(watch_iterator)
        await watch_iterator.aclose()

    assert response.header.revision == expected_revision
    assert stub.Watch.call_count == 2
    sleep_mock.assert_awaited_once()
    assert first_stream.cancelled is True
    assert second_stream.cancelled is True


@pytest.mark.asyncio
async def test_watch_raises_on_non_transient_error() -> None:
    failing_stream = FakeWatchStream(error=FakeRpcError(grpc.StatusCode.PERMISSION_DENIED))

    stub = MagicMock()
    stub.Watch = MagicMock(return_value=failing_stream)

    with patch('aioetcd3.watch.WatchStub', return_value=stub):
        service = WatchService(channel=MagicMock())
        watch_iterator = cast(AsyncGenerator[WatchResponse, None], service.watch('my-key'))
        with pytest.raises(FakeRpcError):
            await anext(watch_iterator)
        await watch_iterator.aclose()
