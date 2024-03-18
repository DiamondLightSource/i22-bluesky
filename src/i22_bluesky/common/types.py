from typing import Protocol, runtime_checkable

from bluesky.protocols import Collectable, Flyable


@runtime_checkable
class CollectableFlyable(Collectable, Flyable, Protocol):
    """
    A Device which implements both the Collectable and Flyable protocols.
    i.e., a device which can be set off, then polled repeatedly to construct documents
    with the data it has collected so far. A typical pattern for "hardware" scans
    """
