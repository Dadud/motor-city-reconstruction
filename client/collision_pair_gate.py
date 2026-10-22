"""Object-identity and vertical candidate gates used by 0x45c3e0."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PairCandidateRecord:
    """Fields consumed by 0x45cd80 after 0x45c3e0 copies its 0x44-byte row."""
    object_id: int
    material_flags: int
    gate_value: int
    vertices: tuple
    height_limit: float

    def __post_init__(self):
        for value, name in ((self.object_id, 'object id'),
                            (self.material_flags, 'material flags'),
                            (self.gate_value, 'gate value')):
            if type(value) is not int or not 0 <= value <= 0xffffffff:
                raise ValueError(f'{name} must be a uint32')
        if len(self.vertices) != 4 or any(len(point) != 3 for point in self.vertices):
            raise ValueError('four 3D candidate vertices are required')
        if not all(math.isfinite(float(value))
                   for point in self.vertices for value in point):
            raise ValueError('candidate vertices must be finite')
        if not math.isfinite(float(self.height_limit)):
            raise ValueError('height limit must be finite')


def objects_share_contact_table(contact_links, first_id, second_id):
    """Translate 0x42d890: self or one of eight direct contact links."""
    if len(contact_links) != 8:
        raise ValueError('exactly eight contact-link entries are required')
    if any(type(value) is not int or not 0 <= value <= 0xffffffff
           for value in (*contact_links, first_id, second_id)):
        raise ValueError('object identities and links must be uint32 values')
    return first_id == second_id or second_id in contact_links


def accepts_pair_candidate(owner_id, contact_links, record):
    """Translate 0x45cd80's identity/material and vertical-span rejection."""
    if not isinstance(record, PairCandidateRecord):
        raise ValueError('a pair candidate record is required')
    if type(owner_id) is not int or not 0 <= owner_id <= 0xffffffff:
        raise ValueError('owner identity must be uint32')
    conditional = (record.object_id != 0 and record.gate_value == 0 and
                   objects_share_contact_table(contact_links, owner_id,
                                               record.object_id) and
                   (record.material_flags & 0x1f) not in (0, 0x0e))
    if conditional:
        if max(float(vertex[1]) for vertex in record.vertices) <= record.height_limit:
            return False
    return True
