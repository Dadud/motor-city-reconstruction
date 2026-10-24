"""Per-vertex object transform used by the native track mesh builders."""
from .matrix_math import dot_3_f32
from .tire_response import f32


def transform_track_vertex(vertex, matrix):
    """Translate the 3x3 point transform in 0x495c00 and 0x495f50.

    The 3x3 matrix is read from object offset 0x44 in row-major memory order;
    each output component is a native x87 dot product stored as binary32.
    """
    vertex, matrix = tuple(f32(value) for value in vertex), tuple(
        f32(value) for value in matrix)
    if len(vertex) != 3 or len(matrix) != 9:
        raise ValueError('track vertex transform requires a 3-vector and 3x3 matrix')
    return tuple(dot_3_f32(vertex, (matrix[column], matrix[column+3],
                                   matrix[column+6]))
                 for column in range(3))
