from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

import grpc
import grpc.aio

ChannelOptionValue: TypeAlias = str | int | bool
ChannelOption: TypeAlias = tuple[str, ChannelOptionValue]


class ConnectionManager:
    """Builds asyncio gRPC channels with round-robin load balancing.

    Args:
        endpoints: One or more ``host:port`` strings.  ``localhost`` is
            automatically replaced with ``127.0.0.1`` to force IPv4 and
            avoid gRPC resolver ambiguity.
        keepalive_time_ms: Interval between gRPC keepalive pings in
            milliseconds (default 10 s).
        keepalive_timeout_ms: Time to wait for a keepalive ping ACK before
            treating the connection as dead (default 5 s).
    """

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

    def get_channel(
        self,
        ca_cert: bytes | None = None,
        cert_key: bytes | None = None,
        cert_chain: bytes | None = None,
        tls_server_name: str | None = None,
    ) -> grpc.aio.Channel:
        """Create and return a gRPC async channel.

        Returns an insecure channel when *ca_cert* is ``None``, or a
        TLS-secured channel otherwise.

        Args:
            ca_cert: PEM-encoded CA certificate bytes for server verification.
                Required to enable TLS.
            cert_key: PEM-encoded client private key bytes for mutual TLS (mTLS).
                Requires *ca_cert*.
            cert_chain: PEM-encoded client certificate chain bytes for mTLS.
                Requires *ca_cert*.
            tls_server_name: Override the server name used for TLS hostname
                verification.  Required when using multiple endpoints with the
                ``ipv4:`` target scheme and TLS, because gRPC cannot derive a
                single hostname from a comma-separated address list.  The value
                must match a DNS SAN in the server certificate (e.g.
                ``'localhost'`` or a shared cluster hostname).  Ignored when
                *ca_cert* is ``None``.

        Returns:
            :class:`grpc.aio.Channel` configured with round-robin load
            balancing and gRPC keepalives.

        Raises:
            ValueError: if *cert_key* or *cert_chain* is provided without *ca_cert*.
        """
        if ca_cert is None and (cert_key is not None or cert_chain is not None):
            raise ValueError('ca_cert is required when cert_key or cert_chain is provided')

        if ca_cert is not None:
            credentials = grpc.ssl_channel_credentials(
                root_certificates=ca_cert,
                private_key=cert_key,
                certificate_chain=cert_chain,
            )
            options = self.grpc_options
            if tls_server_name is not None:
                options = [*options, ('grpc.ssl_target_name_override', tls_server_name)]
            return grpc.aio.secure_channel(self.target, credentials, options=options)

        return grpc.aio.insecure_channel(self.target, options=self.grpc_options)
