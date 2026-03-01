from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

import grpc
import grpc.aio

ChannelOptionValue: TypeAlias = str | int | bool
ChannelOption: TypeAlias = tuple[str, ChannelOptionValue]


class ConnectionManager:
    """Builds asyncio gRPC channels with round-robin load balancing."""

    def __init__(
        self,
        endpoints: Sequence[str],
        *,
        keepalive_time_ms: int = 10_000,
        keepalive_timeout_ms: int = 5_000,
    ) -> None:
        if not endpoints:
            raise ValueError('endpoints cannot be empty')

        formatted_endpoints = [endpoint.replace('localhost', '127.0.0.1') for endpoint in endpoints]
        self.target = f'ipv4:{",".join(formatted_endpoints)}'
        self.grpc_options: list[ChannelOption] = [
            ('grpc.lb_policy_name', 'round_robin'),
            ('grpc.keepalive_time_ms', keepalive_time_ms),
            ('grpc.keepalive_timeout_ms', keepalive_timeout_ms),
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.enable_retries', 1),
        ]

    async def get_channel(
        self,
        ca_cert: bytes | None = None,
        cert_key: bytes | None = None,
        cert_chain: bytes | None = None,
    ) -> grpc.aio.Channel:
        if ca_cert is None and (cert_key is not None or cert_chain is not None):
            raise ValueError('ca_cert is required when cert_key or cert_chain is provided')

        if ca_cert is not None:
            credentials = grpc.ssl_channel_credentials(
                root_certificates=ca_cert,
                private_key=cert_key,
                certificate_chain=cert_chain,
            )
            return grpc.aio.secure_channel(self.target, credentials, options=self.grpc_options)

        return grpc.aio.insecure_channel(self.target, options=self.grpc_options)
