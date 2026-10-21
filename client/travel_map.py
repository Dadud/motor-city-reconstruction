"""Bounded travel-map bitset used by path-reset notifications (0x406a50)."""
from dataclasses import dataclass


TRAVEL_MAP_RESOURCE = 0x00886B08


@dataclass
class TravelMapCache:
    """Process-global table state corresponding to DAT_008e3abc/3ac0."""
    data: bytearray | None = None
    capacity: int = 0

    def __post_init__(self):
        if self.data is not None and not isinstance(self.data, bytearray):
            raise ValueError('travel-map data must be a mutable bytearray')
        if type(self.capacity) is not int or self.capacity < 0:
            raise ValueError('travel-map capacity must be nonnegative')
        if self.data is not None and self.capacity == 0:
            self.capacity = len(self.data)
        if self.data is not None and len(self.data) < self.capacity:
            raise ValueError('travel-map view is smaller than its capacity')


def mark_travel_map(cache, row_index, step_index, *, path_count,
                    step_threshold, allocate):
    """Port 0x406a50 over explicit bounded storage and an allocator bridge.

    The original allocates ``path_count // 20 + 1`` zeroed bytes the first time
    its global table is null, then sets one low-byte bit at row ``row//20``.
    The caller supplies the allocator because it owns the engine resource
    manager and its failure behavior.
    """
    if not isinstance(cache, TravelMapCache):
        raise ValueError('TravelMapCache is required')
    if any(type(value) is not int for value in
           (row_index, step_index, path_count, step_threshold)):
        raise ValueError('travel-map indices and bounds must be integers')
    if path_count < 0 or step_threshold < 0:
        raise ValueError('travel-map bounds must be nonnegative')
    if not callable(allocate):
        raise ValueError('the engine resource allocator must be supplied')

    if cache.data is None:
        size = path_count // 0x14 + 1
        cache.capacity = size
        allocated = allocate(TRAVEL_MAP_RESOURCE, size, 0)
        if allocated is None:
            return False
        if not isinstance(allocated, bytearray) or len(allocated) < size:
            raise ValueError('allocator must return a mutable buffer of requested size')
        cache.data = allocated
        cache.data[:size] = bytes(size)

    if row_index < path_count and step_index < step_threshold:
        if row_index < 0:
            raise ValueError('negative row would address before the bounded travel-map view')
        offset = row_index // 0x14
        if offset >= cache.capacity:
            raise ValueError('travel-map row exceeds the allocated table')
        bit = (1 << (step_index & 0x1f)) & 0xff
        cache.data[offset] |= bit
        return bool(bit)
    return False
