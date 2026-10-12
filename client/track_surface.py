"""Native spatial leaf references to track surface quads (0x42e760/0x42eed0).

This identifies surfaces; vehicle collision response is a separate subsystem.
"""
from dataclasses import dataclass
import math
from .track_mesh import decode_mesh
from .track_spatial import decode_spatial


@dataclass(frozen=True)
class SurfaceHit:
    block: int
    descriptor: int
    vertices: tuple
    raw_descriptor: tuple

    def sample(self, x, z):
        """Return height and unit normal using native 0x42dc50/0x4b71a0."""
        if not math.isfinite(x) or not math.isfinite(z):
            raise ValueError('non-finite surface sample')
        a,b,c,d = self.vertices
        triangle=(a,b,d)
        first=all((p[0]-q[0])*(z-q[2]) <= (x-q[0])*(p[2]-q[2])
                  for p,q in zip(triangle,triangle[1:]+triangle[:1]))
        def cross(u,v):
            return (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        def delta(p,q):
            return tuple(p[i]-q[i] for i in range(3))
        normal=cross(delta(a,b),delta(d,b)) if first else (0,0,0)
        if not any(normal):
            normal=cross(delta(c,d),delta(b,d))
        length=math.sqrt(sum(v*v for v in normal))
        if length == 0 or abs(normal[1]) <= length*1e-12:
            raise ValueError('degenerate or vertical surface plane')
        normal=tuple(v/length for v in normal)
        height=b[1]-((x-b[0])*normal[0]+(z-b[2])*normal[2])/normal[1]
        return height,normal


@dataclass(frozen=True)
class TrackSurface:
    spatial: object
    blocks: tuple

    def lookup(self, x, z, upward_only=True, reference_height=None, tolerance=0):
        """Query surfaces, optionally select the height nearest wheel contact.

        Default behavior preserves native candidate order and exact containment.
        Height selection and edge tolerance are authored compatibility behavior.
        Tolerance is a distance in track units, not an unscaled cross-product.
        """
        if not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError('invalid surface edge tolerance')
        if reference_height is not None and not math.isfinite(reference_height):
            raise ValueError('non-finite surface reference height')
        best=None
        best_distance=math.inf
        for identifier in self.spatial.candidates(x,z):
            block, record = identifier & 0xffff, identifier >> 16
            vertices,quads,descriptors = self.blocks[block]
            descriptor = descriptors[record]
            if upward_only and descriptor[5] <= 0:
                continue
            quad = tuple(vertices[i] for i in quads[descriptor[3] & 0xffff])
            if all((a[0]-b[0])*(z-b[2]) <= (x-b[0])*(a[2]-b[2]) + tolerance*math.hypot(a[0]-b[0],a[2]-b[2])
                   for a,b in zip(quad,quad[1:]+quad[:1])):
                hit=SurfaceHit(block,record,quad,descriptor)
                if reference_height is None:
                    return hit
                try:
                    height,_=hit.sample(x,z)
                except ValueError:
                    continue
                distance=abs(height-reference_height)
                if distance < best_distance:
                    best,best_distance=hit,distance
        return best


def decode_surface(data):
    blocks=[]
    _,offset=decode_mesh(data,materials=True,surface_records=blocks)
    spatial,end=decode_spatial(data,offset)
    if end != len(data):
        raise ValueError('unexpected FRD trailing spatial data')
    def validate(node):
        if node.identifiers is not None:
            for identifier in node.identifiers:
                block,record=identifier & 0xffff,identifier >> 16
                if block >= len(blocks) or record >= len(blocks[block][2]):
                    raise ValueError('FRD spatial surface reference outside block')
        else:
            for child in node.children:
                if child is not None:
                    validate(child)
    for cell in spatial.cells:
        validate(cell)
    return TrackSurface(spatial,tuple(blocks))
