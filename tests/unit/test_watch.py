from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from etcd3aio._protobuf import WatchResponse
from etcd3aio.watch import WatchFilter, WatchService


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
        patch('etcd3aio.watch.WatchStub', return_value=stub),
        patch('etcd3aio.watch.asyncio.sleep', new=AsyncMock()) as sleep_mock,
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

    with patch('etcd3aio.watch.WatchStub', return_value=stub):
        service = WatchService(channel=MagicMock())
        watch_iterator = cast(AsyncGenerator[WatchResponse, None], service.watch('my-key'))
        with pytest.raises(FakeRpcError):
            await anext(watch_iterator)
        await watch_iterator.aclose()


# ---------------------------------------------------------------------------
# filters and progress_notify
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_passes_filters_to_create_request() -> None:
    """filters= is forwarded to WatchCreateRequest server-side."""
    response = WatchResponse()
    response.header.revision = 1
    stream = FakeWatchStream(responses=[response])

    captured_gen: AsyncGenerator | None = None

    def _watch_side_effect(gen: object, *, metadata: object = None) -> FakeWatchStream:
        nonlocal captured_gen
        captured_gen = cast(AsyncGenerator, gen)
        return stream

    stub = MagicMock()
    stub.Watch.side_effect = _watch_side_effect

    with patch('etcd3aio.watch.WatchStub', return_value=stub):
        service = WatchService(channel=MagicMock())
        watch_iterator = cast(
            AsyncGenerator[WatchResponse, None],
            service.watch('key', filters=[WatchFilter.NOPUT, WatchFilter.NODELETE]),
        )
        await anext(watch_iterator)
        await watch_iterator.aclose()

    assert captured_gen is not None
    first_msg = await captured_gen.__anext__()
    assert list(first_msg.create_request.filters) == [
        int(WatchFilter.NOPUT),
        int(WatchFilter.NODELETE),
    ]


@pytest.mark.asyncio
async def test_watch_passes_progress_notify_to_create_request() -> None:
    """progress_notify=True is forwarded to WatchCreateRequest."""
    response = WatchResponse()
    response.header.revision = 1
    stream = FakeWatchStream(responses=[response])

    captured_gen: AsyncGenerator | None = None

    def _watch_side_effect(gen: object, *, metadata: object = None) -> FakeWatchStream:
        nonlocal captured_gen
        captured_gen = cast(AsyncGenerator, gen)
        return stream

    stub = MagicMock()
    stub.Watch.side_effect = _watch_side_effect

    with patch('etcd3aio.watch.WatchStub', return_value=stub):
        service = WatchService(channel=MagicMock())
        watch_iterator = cast(
            AsyncGenerator[WatchResponse, None],
            service.watch('key', progress_notify=True),
        )
        await anext(watch_iterator)
        await watch_iterator.aclose()

    assert captured_gen is not None
    first_msg = await captured_gen.__anext__()
    assert first_msg.create_request.progress_notify is True


def test_watch_filter_enum_values() -> None:
    assert int(WatchFilter.NOPUT) == 0
    assert int(WatchFilter.NODELETE) == 1
