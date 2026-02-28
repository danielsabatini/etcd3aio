Architecture

aioetcd3 is a native asynchronous etcd v3 client.

The library follows a facade pattern to isolate gRPC complexity.

Core Principles

Python 3.13+

asyncio native

strict typing

grpc.aio transport

round-robin endpoint balancing

HTTP/2 keepalive

etcd Guarantees

Default operations are linearizable.

Cluster revision acts as logical clock.

Writes increment the global revision.

Modules

client.py

High level facade that exposes services.

connections.py

Connection manager that builds grpc channels.

Features:

round robin

keepalive

retry support

kv.py

Implements

Put
Range
Delete

lease.py

Lease lifecycle management

Grant
Revoke
KeepAlive

watch.py

Async iterator interface over Watch API.

_protobuf.py

Loads descriptors and exposes TypeAlias for grpc stubs.

Error handling

Transient gRPC errors must be retried:

Unavailable
DeadlineExceeded

Event loop rule

No blocking operations allowed.