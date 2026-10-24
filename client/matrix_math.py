"""Bit-preserving matrix helpers recovered from the client math library."""
from math import atan2, cos, inf, isfinite, sin, sqrt
import struct

from .tire_response import f32


_F32 = struct.Struct('<f')


def _round_binary32(value):
    return _F32.unpack(_F32.pack(value))[0]


def transpose_3x3_words(values):
    """Translate 0x6f12a0: transpose nine row-major 32-bit matrix words."""
    values = tuple(values)
    if len(values) != 9:
        raise ValueError('3x3 transpose requires exactly nine words')
    if any(type(value) is not int or not 0 <= value <= 0xffffffff for value in values):
        raise ValueError('matrix entries must be uint32 words')
    return (values[0], values[3], values[6],
            values[1], values[4], values[7],
            values[2], values[5], values[8])


def scale_matrix_rows(matrix, scale):
    """Translate 0x6f1240: scale each three-float matrix row by XYZ."""
    matrix, scale = tuple(matrix), tuple(scale)
    if len(matrix) != 9 or len(scale) != 3:
        raise ValueError('row scaling requires a 3x3 matrix and three scales')
    matrix = tuple(f32(value) for value in matrix)
    scale = tuple(f32(value) for value in scale)
    return tuple(f32(matrix[row * 3 + column] * scale[row])
                 for row in range(3) for column in range(3))


def rotation_x_turns(turns):
    """Translate the 0x6f1530 matrix builder's x-axis turn parameter."""
    turns = f32(turns)
    angle_scale = f32(6.2831854820251465)
    sine = f32(sin(turns * angle_scale))
    cosine = f32(cos(turns * angle_scale))
    return (1.0, 0.0, 0.0,
            0.0, cosine, sine,
            0.0, -sine, cosine)


def rotation_y_turns(turns):
    """Translate 0x6f1590's 3x3 Y-axis turn matrix builder."""
    turns = f32(turns)
    angle_scale = f32(6.2831854820251465)
    sine = f32(sin(turns * angle_scale))
    cosine = f32(cos(turns * angle_scale))
    return (cosine, 0.0, -sine,
            0.0, 1.0, 0.0,
            sine, 0.0, cosine)


def rotation_z_turns(turns):
    """Translate 0x6f15f0's 3x3 Z-axis turn matrix builder."""
    turns = f32(turns)
    angle_scale = f32(6.2831854820251465)
    sine = f32(sin(turns * angle_scale))
    cosine = f32(cos(turns * angle_scale))
    return (cosine, sine, 0.0,
            -sine, cosine, 0.0,
            0.0, 0.0, 1.0)


def axis_angle_rotation_matrix(axis, turns):
    """Translate 0x6f1650's normalized-axis Rodrigues matrix builder."""
    axis = tuple(f32(value) for value in axis)
    turns = f32(turns)
    if len(axis) != 3 or any(not isfinite(value) for value in axis) or not isfinite(turns):
        raise ValueError('axis-angle matrix requires finite axis and turn values')
    if turns == 0.0:
        return (1., 0., 0., 0., 1., 0., 0., 0., 1.)
    x, y, z = normalize_vector3(axis)
    angle_scale = f32(6.2831854820251465)
    sine = f32(sin(turns * angle_scale))
    cosine = f32(cos(turns * angle_scale))
    one_minus_cosine = _round_binary32(1.0 - cosine)
    x1, y1, z1 = (_round_binary32(component * one_minus_cosine)
                  for component in (x, y, z))
    return (x * x1 + cosine, y * x1 + z * sine, z * x1 - y * sine,
            x * y1 - z * sine, y * y1 + cosine, z * y1 + x * sine,
            x * z1 + y * sine, y * z1 - x * sine, z * z1 + cosine)


def rotate_matrix_rows_x(matrix, turns):
    """Translate 0x6f1780: rotate matrix rows one and two about X turns."""
    matrix = tuple(f32(value) for value in matrix)
    turns = f32(turns)
    if len(matrix) != 9 or not isfinite(turns):
        raise ValueError('matrix X rotation requires nine values and finite turns')
    angle_scale = f32(6.2831854820251465)
    sine = f32(sin(turns * angle_scale))
    cosine = f32(cos(turns * angle_scale))
    row1, row2 = matrix[3:6], matrix[6:9]
    rotated1 = tuple(f32(row2[i] * sine + row1[i] * cosine) for i in range(3))
    rotated2 = tuple(f32(row2[i] * cosine - row1[i] * sine) for i in range(3))
    return matrix[:3] + rotated1 + rotated2


def rotate_matrix_rows_y(matrix, turns):
    """Translate 0x6f1850: rotate matrix rows zero and two about Y turns."""
    matrix = tuple(f32(value) for value in matrix)
    turns = f32(turns)
    if len(matrix) != 9 or not isfinite(turns):
        raise ValueError('matrix Y rotation requires nine values and finite turns')
    angle_scale = f32(6.2831854820251465)
    sine = f32(sin(turns * angle_scale))
    cosine = f32(cos(turns * angle_scale))
    row0, row2 = matrix[:3], matrix[6:9]
    rotated0 = tuple(f32(row0[i] * cosine - row2[i] * sine) for i in range(3))
    rotated2 = tuple(f32(row2[i] * cosine + row0[i] * sine) for i in range(3))
    return rotated0 + matrix[3:6] + rotated2


def dot_3_f32(left, right):
    """Translate 0x6f1140/0x6f3b51 and round the x87 result on float storage."""
    left, right = tuple(left), tuple(right)
    if len(left) != 3 or len(right) != 3:
        raise ValueError('three-component vectors required')
    left = tuple(f32(value) for value in left)
    right = tuple(f32(value) for value in right)
    return f32(left[0] * right[0] + left[1] * right[1] + left[2] * right[2])


def dot_product_batch(vectors, direction):
    """Translate 0x6f1160: dot each consecutive 3-vector with direction."""
    vectors = tuple(tuple(vector) for vector in vectors)
    direction = tuple(direction)
    if len(direction) != 3 or any(len(vector) != 3 for vector in vectors):
        raise ValueError('dot batch requires three-component vectors')
    if any(not isfinite(value) for vector in vectors + (direction,)
           for value in vector):
        raise ValueError('dot batch vectors must be finite')
    return tuple(dot_3_f32(vector, direction) for vector in vectors)


def vector_length3(values):
    """Translate 0x6f1210's x87 three-component Euclidean magnitude."""
    values = tuple(f32(value) for value in values)
    if len(values) != 3:
        raise ValueError('three-component vector required')
    x, y, z = values
    return sqrt((z*z + y*y) + x*x)


def normalize_vector3(values):
    """Translate 0x6f1100: scale a 3D vector by reciprocal x87 magnitude."""
    values = tuple(f32(value) for value in values)
    if len(values) != 3:
        raise ValueError('three-component vector required')
    length = vector_length3(values)
    inverse = inf if length == 0.0 else 1.0 / length
    return tuple(_round_binary32(component * inverse) for component in values)


def atan2_turns(y, x):
    """Translate 0x6f1430: x87 FPATAN scaled by the native turns constant."""
    y, x = f32(y), f32(x)
    return atan2(y, x) * 0.15915493667125702


def normalized_cross3(left, right):
    """Translate 0x6f10d0's cross product and x87 length normalization."""
    left, right = tuple(f32(v) for v in left), tuple(f32(v) for v in right)
    if len(left) != 3 or len(right) != 3:
        raise ValueError('cross product requires two three-component vectors')
    cross = (f32(left[1] * right[2] - left[2] * right[1]),
             f32(left[2] * right[0] - left[0] * right[2]),
             f32(left[0] * right[1] - left[1] * right[0]))
    return normalize_vector3(cross)


def cross_product3(left, right):
    """Translate 0x6f3b75's three-component cross product."""
    left, right = tuple(left), tuple(right)
    if len(left) != 3 or len(right) != 3:
        raise ValueError('cross product requires two three-component vectors')
    left, right = tuple(f32(v) for v in left), tuple(f32(v) for v in right)
    return (f32(left[1] * right[2] - left[2] * right[1]),
            f32(left[2] * right[0] - left[0] * right[2]),
            f32(left[0] * right[1] - left[1] * right[0]))


def linear_vector_sequence(first, second, count):
    """Translate 0x4954c0's fixed-step 3D point sequence producer."""
    first, second = tuple(f32(v) for v in first), tuple(f32(v) for v in second)
    if len(first) != 3 or len(second) != 3:
        raise ValueError('two three-component points are required')
    if type(count) is not int or not 2 <= count <= 65536:
        raise ValueError('point count must be within [2, 65536]')
    delta = tuple(f32(second[i] - first[i]) for i in range(3))
    points = [first, second]
    for _ in range(count - 2):
        points.append(tuple(f32(points[-1][i] + delta[i]) for i in range(3)))
    return tuple(points)


def _multiply_3x3(left, right):
    return tuple(f32(sum(left[row * 3 + k] * right[k * 3 + col]
                         for k in range(3)))
                 for row in range(3) for col in range(3))


def multiply_3x3(matrix_a, matrix_b):
    """Translate the alias-safe matrix product used by 0x6f2a60."""
    a, b = tuple(f32(x) for x in matrix_a), tuple(f32(x) for x in matrix_b)
    if len(a) != 9 or len(b) != 9:
        raise ValueError('matrix multiplication requires two 3x3 matrices')
    orders = ((0, 2, 1), (0, 1, 2), (0, 1, 2),
              (0, 1, 2), (0, 1, 2), (0, 1, 2),
              (0, 1, 2), (0, 1, 2), (0, 1, 2))
    result = []
    for index, order in enumerate(orders):
        row, col = divmod(index, 3)
        terms = [a[row * 3 + k] * b[k * 3 + col] for k in order]
        result.append(f32(terms[0] + terms[1] + terms[2]))
    return tuple(result)


_MATRIX_REPAIR_COEFFICIENTS = (
    -0.5, 0.375, -0.3125, 0.2734375, -0.24609375,
    0.2255859375, -0.20947265625, 0.196380615234375,
    -0.1854705810546875,
)


def repair_rotation_matrix(matrix, iterations=10):
    """Translate 0x5538a0's ten-term inverse-square-root correction."""
    matrix = tuple(f32(value) for value in matrix)
    if len(matrix) != 9:
        raise ValueError('matrix repair requires a 3x3 matrix')
    if type(iterations) is not int or iterations != 10:
        raise ValueError('the recovered repair path supports its observed 10 iterations')
    transpose = transpose_3x3_words(tuple(float_to_word(v) for v in matrix))
    gram = multiply_3x3(tuple(word_to_float(v) for v in transpose), matrix)
    error = tuple(f32(gram[i] - (1.0 if i in (0, 4, 8) else 0.0))
                  for i in range(9))
    power = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    correction = list(power)
    for coefficient in _MATRIX_REPAIR_COEFFICIENTS:
        power = multiply_3x3(power, error)
        scaled = tuple(f32(value * coefficient) for value in power)
        correction = [f32(correction[i] + scaled[i]) for i in range(9)]
    return multiply_3x3(matrix, correction)


def float_to_word(value):
    import struct
    return struct.unpack('<I', struct.pack('<f', value))[0]


def word_to_float(value):
    import struct
    return struct.unpack('<f', struct.pack('<I', value))[0]


def integrate_rotation_matrix(matrix, delta_turns):
    """Translate 0x4b7430: compose X/Y/Z increments expressed in turns."""
    matrix = tuple(f32(value) for value in matrix)
    turns = tuple(f32(value) for value in delta_turns)
    if len(matrix) != 9 or len(turns) != 3:
        raise ValueError('rotation update requires a 3x3 matrix and three increments')
    tau = f32(6.2831854820251465)
    rotations = []
    for value in turns:
        radians = value * tau
        s, c = f32(sin(radians)), f32(cos(radians))
        rotations.append((s, c))
    (sx,cx),(sy,cy),(sz,cz)=rotations
    rx=(1.0,0.0,0.0, 0.0,cx,sx, 0.0,-sx,cx)
    ry=(cy,0.0,-sy, 0.0,1.0,0.0, sy,0.0,cy)
    rz=(cz,sz,0.0, -sz,cz,0.0, 0.0,0.0,1.0)
    increment=_multiply_3x3(_multiply_3x3(rx,ry),rz)
    return _multiply_3x3(matrix,increment)
