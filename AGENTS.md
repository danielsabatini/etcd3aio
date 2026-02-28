Agent Instructions

This repository implements aioetcd3.

Guidelines for modifications:

Python 3.13+

Strict typing required

Use TypeAlias where appropriate

Do not block asyncio event loop

Always prefer async APIs

All grpc calls must be awaited

Code quality:

Ruff must pass

Pyright must pass

Design rules:

Keep facade pattern

gRPC logic must stay isolated

Client object must remain lightweight

File modification rules:

Always output full file when modifying

Do not modify protobuf generated files

Maintain backwards compatibility

Documentation references:

etcd API
https://etcd.io/docs/v3.6/dev-guide/api_reference_v3/

Asyncio
https://docs.python.org/3/howto/asyncio.html