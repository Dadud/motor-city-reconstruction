"""Bounded Python port of the original track-surface query 0x42e760."""
from dataclasses import dataclass
import math
import struct

from .tire_response import f32


GRID_ADDRESS = 0x00A559D8
GRID_BYTES = 65536
LEAF_SENTINEL = 0xDEADBEEF


@dataclass(frozen=True)
class TrackSurfaceMemory:
    """Two bounded original-address memory views used by the native port."""
    grid: bytes
    nodes: bytes
    nodes_address: int

    def __post_init__(self):
        if len(self.grid) != GRID_BYTES:
            raise ValueError('spatial grid must be exactly 65536 bytes')
        if type(self.nodes_address) is not int or not 0 <= self.nodes_address <= 0xFFFFFFFF:
            raise ValueError('node memory base must be uint32')

    def word(self, address):
        if GRID_ADDRESS <= address and address + 4 <= GRID_ADDRESS + len(self.grid):
            return struct.unpack_from('<I', self.grid, address - GRID_ADDRESS)[0]
        if self.nodes_address <= address and address + 4 <= self.nodes_address + len(self.nodes):
            return struct.unpack_from('<I', self.nodes, address - self.nodes_address)[0]
        raise ValueError(f'unmapped track-surface word at 0x{address:08x}')

    def half(self, address):
        return self.word(address) & 0xFFFF

    def byte(self, address):
        if GRID_ADDRESS <= address < GRID_ADDRESS + len(self.grid):
            return self.grid[address - GRID_ADDRESS]
        if self.nodes_address <= address < self.nodes_address + len(self.nodes):
            return self.nodes[address - self.nodes_address]
        raise ValueError(f'unmapped track-surface byte at 0x{address:08x}')

    def read(self, address, size):
        if type(size) is not int or size < 0:
            raise ValueError('track-surface read size must be nonnegative')
        if GRID_ADDRESS <= address and address + size <= GRID_ADDRESS + len(self.grid):
            offset = address - GRID_ADDRESS
            return self.grid[offset:offset + size]
        if self.nodes_address <= address and address + size <= self.nodes_address + len(self.nodes):
            offset = address - self.nodes_address
            return self.nodes[offset:offset + size]
        raise ValueError(f'unmapped track-surface range at 0x{address:08x}')

    def signed_half(self, address):
        return struct.unpack('<h', struct.pack('<H', self.half(address)))[0]

    def real(self, address):
        return struct.unpack('<f', struct.pack('<I', self.word(address)))[0]


@dataclass(frozen=True)
class TrackSurfaceWorld:
    memory: TrackSurfaceMemory
    origin: tuple[float, float]
    scale: tuple[float, float]
    blocks_address: int
    paths_address: int
    last_block: int
    path_count: int


def _spatial_leaf(world, position):
    def coordinate(value, minimum, factor):
        scaled = f32((float(value) - float(minimum)) * float(factor))
        if not math.isfinite(scaled):
            return -0x80000000
        rounded = round(scaled)
        if rounded < -0x80000000 or rounded > 0x7FFFFFFF:
            return -0x80000000
        return rounded

    x = coordinate(position[0], world.origin[0], world.scale[0])
    z = coordinate(position[2], world.origin[1], world.scale[1])
    if x < 0 or z < 0 or x >= 65536 or z >= 65536:
        return 0
    node = GRID_ADDRESS + ((x // 1024) * 64 + (z // 1024)) * 16
    marker = world.memory.word(node)
    if marker == LEAF_SENTINEL:
        return node
    for depth in range(2):
        bit = 9 - depth
        child = ((x >> bit) & 1) + 2 * ((z >> bit) & 1)
        node = world.memory.word(node + child * 4)
        if node == 0 or world.memory.word(node) == LEAF_SENTINEL:
            return node
    raise ValueError('spatial query exceeds the native two-level tree depth')


def _nearest_path(world, position, group):
    start = group * 8
    block_count = world.memory.word(world.blocks_address + group * 0x6C4 + 0x680)
    block_count = struct.unpack('<i', struct.pack('<I', block_count))[0]
    length = block_count if block_count > 1 else 1
    if world.path_count <= 0 or world.path_count > 1_000_000:
        raise ValueError('unsupported track path count')
    if start >= world.path_count or start + length > world.path_count:
        raise ValueError('track path group exceeds the supplied path table')

    def point(index):
        address = world.paths_address + index * 0x54
        return tuple(world.memory.real(address + component * 4) for component in range(3))

    def distance(index):
        path = point(index)
        dz = f32(float(position[2]) - path[2])
        dx = float(position[0]) - path[0]
        return dx * dx + float(dz) * float(dz)

    best = start
    minimum = f32(distance(start))
    for index in range(start + 1, start + length):
        candidate = distance(index)
        if candidate < minimum:
            best = index
            minimum = f32(candidate)
    return best


def _path_side(world, position, index):
    if index >= world.path_count:
        raise ValueError('path side index outside the supplied path table')
    following = 0 if index + 1 >= world.path_count else index + 1

    def point(item):
        address = world.paths_address + item * 0x54
        return tuple(world.memory.real(address + component * 4) for component in range(3))

    current, nxt = point(index), point(following)
    left = (float(current[2]) - nxt[2]) * (float(position[0]) - nxt[0])
    right = (float(current[0]) - nxt[0]) * (float(position[2]) - nxt[2])
    return 8 if left < right else 2


def track_surface_lookup(world, position, record):
    """Update the source 0x44-byte surface query and return its int result."""
    if not isinstance(world, TrackSurfaceWorld):
        raise TypeError('a bounded TrackSurfaceWorld is required')
    if not isinstance(record, bytearray) or len(record) < 68:
        raise ValueError('a mutable 0x44-byte surface query record is required')
    position = tuple(map(f32, position))
    if len(position) != 3:
        raise ValueError('surface query position must have three components')
    memory = world.memory

    def load(offset):
        return struct.unpack_from('<I', record, offset)[0]

    def store(offset, value):
        struct.pack_into('<I', record, offset, value & 0xFFFFFFFF)

    def save_position():
        struct.pack_into('<3f', record, 32, *position)

    previous_block = load(4)

    def contains(vertices):
        for index in range(4):
            a = vertices[index]
            b = vertices[(index + 1) % 4]
            ax, az = memory.real(a), memory.real(a + 8)
            bx, bz = memory.real(b), memory.real(b + 8)
            if not ((ax - bx) * (float(position[2]) - bz) <=
                    (az - bz) * (float(position[0]) - bx)):
                return False
        return True

    cached_vertices = tuple(load(16 + i * 4) for i in range(4))
    if load(12) != 0 and contains(cached_vertices):
        save_position()
        return 1

    leaf = _spatial_leaf(world, position)
    found = False
    if leaf and memory.word(leaf) == LEAF_SENTINEL:
        count = struct.unpack('<i', struct.pack('<I', memory.word(leaf + 4)))[0]
        identifiers = memory.word(leaf + 8)
        for item_index in range(count):
            identifier = identifiers + item_index * 4
            block = memory.half(identifier)
            base = world.blocks_address + block * 0x6C4
            descriptor = memory.word(base + 0x67C) + memory.half(identifier + 2) * 20
            vertices_base = memory.word(base + 0x14C)
            quad = memory.word(base + 0x3C) + memory.half(descriptor + 6) * 30
            vertices = tuple(vertices_base + memory.half(quad + j * 2) * 12
                             for j in range(4))
            if not contains(vertices) or memory.signed_half(descriptor + 10) <= 0:
                continue

            store(4, block)
            store(0, _nearest_path(world, position, block))
            store(12, descriptor)
            save_position()
            store(8, 0)
            for j in range(6):
                coefficient = f32(memory.signed_half(descriptor + 8 + j * 2) *
                                  2.0 * (1.0 / 65536.0))
                struct.pack_into('<f', record, 44 + j * 4, coefficient)
            for j, address in enumerate(vertices):
                store(16 + j * 4, address)
            if block == previous_block:
                return 1
            if any(memory.word(base + 0x6A4 + j * 4) == previous_block
                   for j in range(8)):
                return 1
            found = True
        if found:
            return 1

    def center_distance(block):
        base = world.blocks_address + block * 0x6C4
        x = float(position[0]) - (memory.real(base + 0x670) + memory.real(base + 0x664)) * 0.5
        z = float(position[2]) - (memory.real(base + 0x678) + memory.real(base + 0x66C)) * 0.5
        return z * z + x * x

    block = 0
    minimum = f32(center_distance(0))
    for index in range(1, world.last_block + 1):
        candidate = center_distance(index)
        if candidate < minimum:
            block = index
            minimum = f32(candidate)
    path_index = _nearest_path(world, position, block)
    store(4, path_index >> 3)
    store(12, 0)
    for j in range(4):
        store(16 + j * 4, 0)
    store(8, 0)
    save_position()
    store(0, path_index)
    store(8, _path_side(world, position, path_index))
    return 0
