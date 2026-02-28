import logging
from typing import List, Optional

import grpc.aio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gerencia canais gRPC assíncronos com failover automático [8]."""

    def __init__(
        self, endpoints: List[str], keepalive_time_ms: int = 10000, keepalive_timeout_ms: int = 5000
    ):
        # O gRPC v3.4+ requer o prefixo ipv4: para múltiplos alvos [9]
        formatted = [e.replace('localhost', '127.0.0.1') for e in endpoints]
        self.target = f'ipv4:{",".join(formatted)}'

        self.grpc_options = [
            ('grpc.lb_policy_name', 'round_robin'),
            ('grpc.keepalive_time_ms', keepalive_time_ms),
            ('grpc.keepalive_timeout_ms', keepalive_timeout_ms),
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.enable_retries', 1),
        ]

    async def get_channel(
        self,
        ca_cert: Optional[bytes] = None,
        cert_key: Optional[bytes] = None,
        cert_chain: Optional[bytes] = None,
    ) -> grpc.aio.Channel:
        """Cria um canal seguro ou inseguro integrado ao Event Loop [10, 11]."""
        try:
            if ca_cert:
                credentials = grpc.ssl_channel_credentials(
                    root_certificates=ca_cert, private_key=cert_key, certificate_chain=cert_chain
                )
                return grpc.aio.secure_channel(self.target, credentials, options=self.grpc_options)
            return grpc.aio.insecure_channel(self.target, options=self.grpc_options)
        except Exception as e:
            logger.error(f'Erro ao inicializar canal: {e}')
            raise
