"""Authored wheel/terrain contact queries for the portable driving simulation.

FCE wheel centers are recovered markers. Tire radius must be supplied by the
vehicle configuration; no mesh-derived sizing or suspension response is implied.
"""
from dataclasses import dataclass
import math

WHEELS=('LF','RF','LR','RR')


@dataclass(frozen=True)
class Pose:
    position: tuple
    rotation: tuple = ((1,0,0),(0,1,0),(0,0,1))

    def __post_init__(self):
        if len(self.position)!=3 or len(self.rotation)!=3 or any(len(row)!=3 for row in self.rotation):
            raise ValueError('invalid vehicle pose dimensions')
        if not all(math.isfinite(v) for v in (*self.position,*(v for row in self.rotation for v in row))):
            raise ValueError('non-finite vehicle pose')
        for i in range(3):
            for j in range(3):
                dot=sum(self.rotation[i][k]*self.rotation[j][k] for k in range(3))
                if abs(dot-(i==j))>1e-6:
                    raise ValueError('vehicle pose rotation is not orthonormal')
        a,b,c=self.rotation
        determinant=a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
        if determinant<0:
            raise ValueError('vehicle pose rotation contains reflection')

    @classmethod
    def yaw(cls,position,angle):
        if not math.isfinite(angle):
            raise ValueError('non-finite vehicle heading')
        c,s=math.cos(angle),math.sin(angle)
        return cls(tuple(position),((c,0,s),(0,1,0),(-s,0,c)))

    def transform(self,point):
        return tuple(self.position[i]+sum(self.rotation[i][j]*point[j] for j in range(3)) for i in range(3))


@dataclass(frozen=True)
class WheelContact:
    wheel: str
    center: tuple
    surface: object | None
    height: float | None
    normal: tuple | None
    gap: float | None


@dataclass(frozen=True)
class WheelRig:
    centers: tuple

    @classmethod
    def from_model(cls,model):
        centers=[]
        for key in WHEELS:
            matches=[p.origin for p in model.parts if p.name==f':PP{key}wheel']
            if len(matches)!=1:
                raise ValueError(f'vehicle requires one {key} wheel marker')
            point=tuple(matches[0])
            if len(point)!=3 or not all(math.isfinite(v) for v in point):
                raise ValueError('non-finite wheel center')
            centers.append(point)
        return cls(tuple(centers))

    def contacts(self,terrain,pose,radii,tolerance=0.001):
        """Query each wheel independently; missing terrain stays explicit.

        Gap is vertical clearance of the tire bottom, not spring compression.
        """
        if set(radii)!=set(WHEELS) or any(not math.isfinite(radii[k]) or radii[k]<=0 for k in WHEELS):
            raise ValueError('four positive finite tire radii are required')
        results=[]
        for key,local in zip(WHEELS,self.centers):
            center=pose.transform(local)
            bottom=center[1]-radii[key]
            hit=terrain.lookup(center[0],center[2],reference_height=bottom,tolerance=tolerance)
            height=normal=gap=None
            if hit is not None:
                height,normal=hit.sample(center[0],center[2])
                gap=bottom-height
            results.append(WheelContact(key,center,hit,height,normal,gap))
        return tuple(results)

    def spawn_pose(self,terrain,pose,radii,clearance=0.02):
        """Authored conservative placement with every tire above its surface.

        Preserve heading/bank and raise the body to clear the highest wheel
        support. This initializes a simulation; it does not settle suspension.
        """
        if not math.isfinite(clearance) or clearance<0:
            raise ValueError('invalid spawn clearance')
        contacts=self.contacts(terrain,pose,radii)
        if any(c.gap is None for c in contacts):
            raise ValueError('spawn requires terrain beneath all four wheels')
        shift=clearance-min(c.gap for c in contacts)
        placed=Pose((pose.position[0],pose.position[1]+shift,pose.position[2]),pose.rotation)
        final=self.contacts(terrain,placed,radii)
        if any(c.gap is None or c.gap<clearance-1e-6 for c in final):
            raise ValueError('spawn surface changed during placement')
        return placed,final

    def velocities(self,pose,linear,angular,center_of_mass=(0,0,0)):
        """World wheel velocities: v + omega cross rotated lever arm.

        Angular velocity is world radians/second. Native contact code performs
        the same cross product after converting its turns/second by 2*pi.
        Center of mass is supplied in the body's local coordinates.
        """
        vectors=(linear,angular,center_of_mass)
        if any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in vectors):
            raise ValueError('finite three-component motion vectors are required')
        com=pose.transform(center_of_mass)
        results={}
        for key,local in zip(WHEELS,self.centers):
            world=pose.transform(local)
            r=tuple(world[i]-com[i] for i in range(3))
            wx,wy,wz=angular
            spin=(wy*r[2]-wz*r[1],wz*r[0]-wx*r[2],wx*r[1]-wy*r[0])
            results[key]=tuple(linear[i]+spin[i] for i in range(3))
        return results
