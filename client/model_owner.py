"""Owner component-node construction and render-list selection primitives."""
from dataclasses import dataclass
import struct

_PART_INFO_SIZE = 0x984
_PART_INFO_CLASS = 0x338
_PART_INFO_ATTACHMENT = 0x18


@dataclass(frozen=True)
class ComponentNodeImage:
    address: int
    image: bytes


@dataclass(frozen=True)
class ComponentNodeList:
    head: int
    nodes: tuple[ComponentNodeImage, ...]

    @property
    def count(self):
        return len(self.nodes)


@dataclass(frozen=True)
class StockComponentNodeList:
    mechanical_parts: tuple
    component_nodes: ComponentNodeList

    @property
    def head(self):
        return self.component_nodes.head

    @property
    def count(self):
        return self.component_nodes.count


@dataclass(frozen=True)
class DefaultDriverNodeInsertion:
    node: ComponentNodeImage
    head: int
    count: int


@dataclass(frozen=True)
class StockOwnerWorkerResult:
    owner_image: bytes
    component_nodes: ComponentNodeList
    source_vehicle_index: int


@dataclass(frozen=True)
class OwnerJobPollResult:
    state: int
    ready_result: bool
    waits: int
    pumps: int


@dataclass(frozen=True)
class StockOwnerAdmission:
    admitted: bool
    release_completion: bool
    reason: str


def admit_stock_owner_job(completion_status, source_slot_count, buffer_allocated):
    """Translate the pre-expansion gates in stock-owner worker `0x52c790`.

    A non-success completion status and an empty slot count return zero without
    releasing the completion. A failed scratch-buffer allocation releases the
    completion first, then returns zero. Successful admission proceeds into
    the ready-result translation.
    """
    if type(completion_status) is not int or not 0 <= completion_status <= 0xffffffff:
        raise ValueError('completion status must be an unsigned 32-bit value')
    if type(source_slot_count) is not int or not 0 <= source_slot_count <= 0xffffffff:
        raise ValueError('source slot count must be an unsigned 32-bit value')
    if type(buffer_allocated) is not bool:
        raise TypeError('buffer_allocated must be boolean')
    if completion_status != 1:
        return StockOwnerAdmission(False, False, 'completion status is not success')
    if source_slot_count == 0:
        return StockOwnerAdmission(False, False, 'no source slots')
    if not buffer_allocated:
        return StockOwnerAdmission(False, True, 'scratch allocation failed')
    return StockOwnerAdmission(True, False, 'ready')


def poll_owner_job_result(initial_state, read_state, current_thread_id,
                          pumping_thread_id, pump, sleep, *, max_waits=10000):
    """Translate `0x52c790`'s pending-state poll before ready-result handling.

    State 2 waits in 10 ms intervals. On each pass it pumps the callback queue
    with argument zero only when running on the designated pump thread. States
    0 through 98 return the worker function's ordinary not-ready/failure value;
    other signed 32-bit states are treated as the ready result pointer gate.
    """
    def state_value(value, label):
        if type(value) is not int or not -0x80000000 <= value <= 0x7fffffff:
            raise ValueError(f'{label} must be a signed 32-bit state')
        return value

    state = state_value(initial_state, 'initial state')
    for value, label in ((current_thread_id, 'current thread ID'),
                         (pumping_thread_id, 'pumping thread ID')):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError(f'{label} must be an unsigned 32-bit value')
    if type(max_waits) is not int or not 0 <= max_waits <= 1_000_000:
        raise ValueError('max_waits must be a bounded nonnegative integer')
    if state == 2 and (not callable(read_state) or not callable(sleep)):
        raise TypeError('pending state requires read_state and sleep callbacks')
    if state == 2 and current_thread_id == pumping_thread_id and not callable(pump):
        raise TypeError('the pump thread requires a pump callback')

    waits = pumps = 0
    while state == 2:
        if waits >= max_waits:
            raise TimeoutError('owner worker remained pending beyond max_waits')
        if current_thread_id == pumping_thread_id:
            pump(0)
            pumps += 1
        sleep(10)
        waits += 1
        state = state_value(read_state(), 'polled state')
    return OwnerJobPollResult(state, not (-1 < state < 99), waits, pumps)


def build_default_driver_node(address, previous_head, previous_count, part_lookup):
    """Translate the successful default-driver insertion in original `0x52c190`.

    Owner allocation is external. This builds the node image and resulting
    owner-list metadata after the allocator and class/attachment lookup return.
    """
    for value, label in ((address, 'node address'), (previous_head, 'previous head')):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError(f'{label} must be an unsigned 32-bit value')
    if address == 0:
        raise ValueError('node address must be nonzero')
    if type(previous_count) is not int or not 0 <= previous_count < 0xffffffff:
        raise ValueError('owner count must be a bounded unsigned 32-bit value')
    if not callable(part_lookup):
        raise TypeError('part_lookup must be callable')
    handle = part_lookup(0x80e9, 0)
    if type(handle) is not int or not 0 <= handle <= 0xffffffff:
        raise ValueError('part_lookup must return an unsigned 32-bit value')

    image = bytearray(_PART_INFO_SIZE)
    struct.pack_into('<I', image, 0x00, previous_head)
    struct.pack_into('<I', image, 0x18, 0)
    struct.pack_into('<I', image, 0x1c, 0x3f800000)
    struct.pack_into('<I', image, 0x24, 0x4700e900)
    struct.pack_into('<I', image, 0x28, 0x3f800000)
    struct.pack_into('<I', image, 0x2c, 0x3f800000)
    struct.pack_into('<I', image, 0x30, 0x42960000)
    struct.pack_into('<I', image, 0x34, 0x3f800000)
    struct.pack_into('<I', image, 0x38, 0x46ea6000)
    struct.pack_into('<I', image, 0x11c, handle)
    struct.pack_into('<I', image, 0x338, 0x80e9)
    image[0x53f:0x546] = b'Driver\0'
    struct.pack_into('<I', image, 0x980, 0x42960000)
    node = ComponentNodeImage(address, bytes(image))
    return DefaultDriverNodeInsertion(node, address, previous_count + 1)


def build_component_node_list(template_images, node_addresses, part_lookup):
    """Translate `0x52add0` for an existing empty owner component list.

    The caller supplies allocator addresses and the result of the original
    `(class_id, attachment_id)` lookup. Original insertion prepends each tPartInfo record,
    so the final head is the last allocated record. The complete 0x984-byte
    source image is copied before the original field overrides are applied.
    Owner allocation, resource loading and failure cleanup are separate.
    """
    templates = tuple(template_images)
    addresses = tuple(node_addresses)
    if len(templates) != len(addresses):
        raise ValueError('template and allocated-node counts differ')
    if not callable(part_lookup):
        raise TypeError('part_lookup must be callable')
    for index, (template, address) in enumerate(zip(templates, addresses)):
        if not isinstance(template, bytes) or len(template) != _PART_INFO_SIZE:
            raise ValueError(f'template {index} must be a 0x984-byte image')
        if type(address) is not int or not 0 < address <= 0xffffffff:
            raise ValueError(f'node address {index} must be a nonzero 32-bit value')
    if len(set(addresses)) != len(addresses):
        raise ValueError('allocated node addresses must be unique')

    head = 0
    nodes = []
    for template, address in zip(templates, addresses):
        image = bytearray(template)
        class_id, = struct.unpack_from('<I', image, _PART_INFO_CLASS)
        attachment_id, = struct.unpack_from('<I', image, _PART_INFO_ATTACHMENT)
        part_handle = part_lookup(class_id, attachment_id)
        if type(part_handle) is not int or not 0 <= part_handle <= 0xffffffff:
            raise ValueError('part_lookup must return an unsigned 32-bit value')
        first_bounds, second_bounds = struct.unpack_from('<II', image, 0x104)
        struct.pack_into('<I', image, 0x00, head)
        struct.pack_into('<I', image, 0x04, 0)
        struct.pack_into('<I', image, 0x1c, 0x3f800000)
        struct.pack_into('<IIII', image, 0x10c, first_bounds, second_bounds,
                         first_bounds, second_bounds)
        struct.pack_into('<I', image, 0x11c, part_handle)
        head = address
        nodes.append(ComponentNodeImage(address, bytes(image)))
    return ComponentNodeList(head, tuple(nodes))


def build_stock_component_node_list(slots, node_addresses, part_lookup, *,
                                    model_prefix, driver_node_address=None):
    """Compose stock slot pairing, tPartInfo fields and owner-node creation.

    The input is the already-loaded 0x63c DBAPT slot sequence. This joins the
    translated `0x52c550` pairing and `0x52c2e0` record transfers with the
    successful `0x52add0` list builder. Supplying ``driver_node_address`` also
    models the missing-driver fallback in `0x52c790` via `0x52c190`. Asset
    acquisition, installation-table setup and actual model loading remain
    caller-provided services.
    """
    from .mechanical_parts import expand_mechanical_parts
    parts = expand_mechanical_parts(slots, model_prefix=model_prefix)
    nodes = build_component_node_list(
        tuple(part.image for part in parts), node_addresses, part_lookup)
    if driver_node_address is not None:
        driver = build_default_driver_node(
            driver_node_address, nodes.head, nodes.count, part_lookup)
        nodes = ComponentNodeList(driver.head, nodes.nodes + (driver.node,))
    return StockComponentNodeList(parts, nodes)


def complete_ready_stock_owner_job(owner_image, slots, job_image, node_addresses,
                                   driver_node_address, part_lookup, *,
                                   model_prefix, driver_model_key, driver_size):
    """Translate the successful ready-result tail of stock worker `0x52c790`.

    The asynchronous query/wait, resource handles and pool allocator are
    external. The caller supplies their ready worker image, DBAPT slot images,
    returned node addresses and driver-table values. Mechanical node creation,
    default-driver fallback and the owner's deterministic result fields are
    composed here.
    """
    from .mechanical_parts import expand_mechanical_parts

    if not isinstance(owner_image, bytes) or len(owner_image) < 0x264:
        raise ValueError('owner image must include the recovered 0x264-byte prefix')
    if not isinstance(job_image, bytes) or len(job_image) < 0xbb4:
        raise ValueError('ready job image must include fields through +0xbb3')
    if struct.unpack_from('<I', owner_image, 0x19c)[0] != 0:
        raise ValueError('stock worker integration requires an empty component-list head')
    if isinstance(driver_model_key, str):
        try:
            driver_model_key = driver_model_key.encode('ascii')
        except UnicodeEncodeError as error:
            raise ValueError('driver model key must be ASCII') from error
    if not isinstance(driver_model_key, bytes) or not driver_model_key or b'\0' in driver_model_key:
        raise ValueError('driver model key must be a nonempty NUL-free byte string')
    if type(driver_size) is not int or not 0 <= driver_size <= 0x7fffffff:
        raise ValueError('driver size must be a nonnegative signed 32-bit integer')

    parts = expand_mechanical_parts(slots, model_prefix=model_prefix)
    addresses = tuple(node_addresses)
    if len(addresses) != len(parts):
        raise ValueError('one allocated address is required per mechanical record')
    has_driver = any(struct.unpack_from('<I', part.image, _PART_INFO_CLASS)[0] == 0x80e9
                     for part in parts)
    nodes = build_stock_component_node_list(
        slots, addresses, part_lookup, model_prefix=model_prefix,
        driver_node_address=None if has_driver else driver_node_address)
    driver_index = next((i for i, node in enumerate(nodes.component_nodes.nodes)
                         if struct.unpack_from('<I', node.image, _PART_INFO_CLASS)[0] == 0x80e9),
                        None)
    if driver_index is None:
        raise ValueError('stock owner list must include its default driver node')

    key = driver_model_key.split(b'\0', 1)[0]
    if len(key) >= 9:
        raise ValueError('driver model key does not fit the native 9-byte key area')
    try:
        prefix = model_prefix.encode('ascii') if isinstance(model_prefix, str) else model_prefix
    except UnicodeEncodeError as error:
        raise ValueError('model prefix must be ASCII') from error
    if not isinstance(prefix, bytes) or b'\0' in prefix:
        raise ValueError('model prefix must be NUL-free bytes or ASCII text')
    path = prefix + key + b'.viv'
    if 0x22c + len(path) >= _PART_INFO_SIZE:
        raise ValueError('driver model path exceeds tPartInfo image')

    component_images = list(nodes.component_nodes.nodes)
    driver = component_images[driver_index]
    driver_image = bytearray(driver.image)
    driver_image[0x220:0x229] = key + b'\0' * (9 - len(key))
    driver_image[0x22c:0x22c + len(path) + 1] = path + b'\0'
    size_bits = struct.unpack('<I', struct.pack('<f', float(driver_size)))[0]
    struct.pack_into('<I', driver_image, 0x30, size_bits)
    struct.pack_into('<I', driver_image, 0x980, size_bits)
    component_images[driver_index] = ComponentNodeImage(driver.address, bytes(driver_image))
    component_nodes = ComponentNodeList(nodes.head, tuple(component_images))

    selected = next((index for index, slot in enumerate(slots)
                     if struct.unpack_from('<I', slot, 0x1e3)[0] != 0 and
                     struct.unpack_from('<I', slot, 0)[0] == 0x65), -1)
    out = bytearray(owner_image)
    prior_count, = struct.unpack_from('<I', out, 0x40)
    if prior_count + component_nodes.count > 0xffffffff:
        raise ValueError('owner component count overflows uint32')
    struct.pack_into('<I', out, 0x40, prior_count + component_nodes.count)
    struct.pack_into('<I', out, 0x19c, component_nodes.head)
    struct.pack_into('<I', out, 0x238, struct.unpack_from('<I', job_image, 0xbb0)[0])
    if selected < 0:
        label = b'-DBAPT_kVehicle not found-\0'
    else:
        slot = slots[selected]
        brand = slot[0x2c7:0x307].split(b'\0', 1)[0]
        name = slot[0x307:0x387].split(b'\0', 1)[0]
        label = (brand + b' ' + name)[:0x41] + b'\0'
        struct.pack_into('<I', out, 0x198, struct.unpack_from('<I', slot, 0x1e7)[0])
    if len(label) > 0x42:
        raise ValueError('owner display label exceeds its native 66-byte field')
    out[:len(label)] = label

    # Original 0x52ca30 returns zero while the stock job is still attached;
    # 0x52c790 then copies its status text/words and resource handle.
    status = job_image[0x1d7:].split(b'\0', 1)[0]
    status_end = 0x1a4 + len(status) + 1
    if status_end > len(out):
        raise ValueError('worker status text exceeds owner image')
    out[0x1a4:status_end] = status + b'\0'
    out[0x1ad:0x1ad + 0x30] = job_image[0x68:0x68 + 0x30]
    struct.pack_into('<I', out, 0x178, struct.unpack_from('<I', job_image, 0x5c)[0])
    return StockOwnerWorkerResult(bytes(out), component_nodes, selected)


def selected_render_head(heads, maximum_index):
    """Return the first nonzero render-list head from `maximum_index` down to 0.

    This is the bounded selection performed by original `0x52d070`. It does not
    allocate or construct list nodes; owner slot production remains separate.
    """
    heads = tuple(heads)
    if len(heads) != 4:
        raise ValueError('owner must expose exactly four render-list slots')
    if type(maximum_index) is not int or not 0 <= maximum_index < len(heads):
        raise ValueError('maximum render-list index must be between 0 and 3')
    for index, head in enumerate(heads):
        if type(head) is not int or not 0 <= head <= 0xffffffff:
            raise ValueError(f'render-list head {index} must be an unsigned 32-bit value')
    for index in range(maximum_index, -1, -1):
        if heads[index] != 0:
            return heads[index]
    return 0
