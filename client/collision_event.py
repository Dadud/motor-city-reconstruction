"""World-contact event handler lookup and state transitions."""
import struct

from client.matrix_math import transpose_3x3_words
from client.tire_response import f32


HANDLER_COUNT = 12
HANDLER_TABLE = 0x0098F38C
EVENT_HEIGHT_LIMIT = f32(2.23515)
SAMPLE_EVENT_HEIGHT_LIMIT = f32(11.17575)


def lookup_collision_event_handler(body_image, handlers):
    """Translate the indexed global handler lookup at original 0x43b550."""
    image = bytes(body_image)
    table = tuple(handlers)
    if len(image) < 0x468:
        raise ValueError('body image must contain the handler index at +0x464')
    if len(table) != HANDLER_COUNT or any(
            type(value) is not int or not 0 <= value <= 0xffffffff
            for value in table):
        raise ValueError('handler table must contain twelve uint32 pointers')
    index = struct.unpack_from('<i', image, 0x464)[0]
    return table[index] if 0 <= index < HANDLER_COUNT else 0


def apply_collision_contact_event(body_image, global_event_value=0):
    """Translate the shared handler method at 0x4658f0 and its leaf writes.

    The handler is invoked by its caller only after an object and contact are
    selected. This function still applies the method's own flag and magnitude
    gates so it is also useful as a direct method translation.
    """
    image = bytes(body_image)
    if len(image) < 0x1060:
        raise ValueError('body image must span the collision-event state fields')
    if type(global_event_value) is not int or not 0 <= global_event_value <= 0xffffffff:
        raise ValueError('event clock value must be a uint32')
    if (struct.unpack_from('<I', image, 0x474)[0] & 2) == 0:
        return image
    if struct.unpack_from('<f', image, 0x3c8)[0] == 0.0:
        return image

    matrix = struct.unpack_from('<9I', image, 0x78)
    transposed = tuple(struct.unpack('<f', struct.pack('<I', word))[0]
                       for word in transpose_3x3_words(matrix))
    impulse = struct.unpack_from('<3f', image, 0x3cc)
    vertical = f32((impulse[2] * transposed[8] +
                    impulse[1] * transposed[5]) +
                   impulse[0] * transposed[2])
    state = struct.unpack_from('<I', image, 0xe00)[0]
    result = bytearray(image)
    if (state == 0 and
            struct.unpack_from('<f', image, 0x105c)[0] < EVENT_HEIGHT_LIMIT and
            vertical < 0.0):
        struct.pack_into('<I', result, 0xe04,
                         (global_event_value + 300) & 0xffffffff)
        struct.pack_into('<I', result, 0xe00, 1)
        flags = struct.unpack_from('<I', image, 0xdf4)[0]
        struct.pack_into('<I', result, 0xdf4, flags | 0x40)
    elif state == 1 and vertical > 0.0:
        struct.pack_into('<I', result, 0xe00, 0)
        flags = struct.unpack_from('<I', image, 0xdf4)[0]
        struct.pack_into('<I', result, 0xdf4, flags & 0xffffffbf)
    return bytes(result)


def apply_sampled_world_event_callback(body_image, handler_image,
                                       sample_values, global_event_value=0):
    """Translate the sampled-world virtual callback at 0x465a00.

    The callback asks its handler's +0x24 virtual method (0x4658c0) to toggle
    the body's contact-event state. An activated state queues the sample data
    in the body and increments the handler's +0x28 callback count.
    """
    image = bytes(body_image)
    handler = bytes(handler_image)
    values = tuple(f32(value) for value in sample_values)
    if len(image) < 0x1060:
        raise ValueError('body image must span the sampled-event state fields')
    if len(handler) < 0x2c:
        raise ValueError('handler image must include its callback count at +0x28')
    if len(values) != 4:
        raise ValueError('sample event requires X, Y, Z and vertical values')
    if type(global_event_value) is not int or not 0 <= global_event_value <= 0xffffffff:
        raise ValueError('event clock value must be a uint32')

    contact = struct.unpack_from('<f', image, 0x3c8)[0]
    height = struct.unpack_from('<f', image, 0x105c)[0]
    if not (contact != 0.0 and height < SAMPLE_EVENT_HEIGHT_LIMIT):
        return image, handler, False

    result = bytearray(image)
    state = struct.unpack_from('<I', image, 0xe00)[0]
    flags = struct.unpack_from('<I', image, 0xdf4)[0]
    if state == 0:
        struct.pack_into('<I', result, 0xe04,
                         (global_event_value + 300) & 0xffffffff)
        struct.pack_into('<I', result, 0xe00, 1)
        struct.pack_into('<I', result, 0xdf4, flags | 0x40)
    else:
        struct.pack_into('<I', result, 0xe00, 0)
        struct.pack_into('<I', result, 0xdf4, flags & 0xffffffbf)

    queued = struct.unpack_from('<I', result, 0xe00)[0] == 1
    updated_handler = bytearray(handler)
    if queued:
        struct.pack_into('<I', result, 0xe14,
                         struct.unpack_from('<I', image, 0xe14)[0] | 0x80)
        struct.pack_into('<I', result, 0xe80,
                         struct.unpack_from('<I', image, 0x370)[0])
        struct.pack_into('<4f', result, 0xe84, *values)
        count = struct.unpack_from('<I', handler, 0x28)[0]
        struct.pack_into('<I', updated_handler, 0x28,
                         (count + 1) & 0xffffffff)
    return bytes(result), bytes(updated_handler), queued
