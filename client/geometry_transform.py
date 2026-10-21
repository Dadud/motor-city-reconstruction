"""Mode-6 3D vertex transformation used by the client's geometry dispatcher."""
from .track_plane import float32_ieee


def transform_vertices(vertices, matrix, position, *, count=22,
                       input_stride=3, output_stride=3):
    """Transform row-vector points into the owner's 22-vertex world buffer.

    The observed call uses twelve-byte input and output strides (three floats)
    and the 22-count mode value. Strides here are expressed in float elements.
    """
    vertices = tuple(float32_ieee(value) for value in vertices)
    matrix = tuple(float32_ieee(value) for value in matrix)
    position = tuple(float32_ieee(value) for value in position)
    if len(matrix) != 9 or len(position) != 3:
        raise ValueError('a 3x3 matrix and 3D position are required')
    if type(count) is not int or count != 22:
        raise ValueError('the observed mode-6 geometry path transforms 22 vertices')
    if type(input_stride) is not int or input_stride < 3 or type(output_stride) is not int or output_stride < 3:
        raise ValueError('vertex strides must fit three float components')
    if len(vertices) < (count - 1) * input_stride + 3:
        raise ValueError('input vertex buffer is shorter than the requested count')
    output = [0.0] * ((count - 1) * output_stride + 3)
    for index in range(count):
        offset = index * input_stride
        x, y, z = vertices[offset:offset + 3]
        transformed_components = []
        for first, second, third, translation in (
                (matrix[0], matrix[3], matrix[6], position[0]),
                (matrix[1], matrix[4], matrix[7], position[1]),
                (matrix[2], matrix[5], matrix[8], position[2])):
            value = float32_ieee(x * first)
            value = float32_ieee(value + float32_ieee(y * second))
            value = float32_ieee(value + float32_ieee(z * third))
            transformed_components.append(float32_ieee(value + translation))
        transformed = tuple(transformed_components)
        target = index * output_stride
        output[target:target + 3] = transformed
    return tuple(output)


def add_vector_to_points(points, vector, *, count=22):
    """Translate contiguous 3-float points as done by the helper at 0x6f1450.

    The original routine permits overlapping source and destination buffers;
    this value-oriented API returns the translated point sequence.
    """
    points = tuple(float32_ieee(value) for value in points)
    vector = tuple(float32_ieee(value) for value in vector)
    if len(vector) != 3:
        raise ValueError('translation requires three components')
    if type(count) is not int or count < 0:
        raise ValueError('point count must be a nonnegative integer')
    if len(points) < count * 3:
        raise ValueError('point buffer is shorter than the requested count')
    output = list(points)
    for index in range(count):
        offset = index * 3
        for axis in range(3):
            output[offset + axis] = float32_ieee(points[offset + axis] + vector[axis])
    return tuple(output)
