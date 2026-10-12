import math
import unittest
from client.contact import Pose, WheelRig, WHEELS
from client.fce import Model, Part
from client.track_surface import SurfaceHit


class Terrain:
    def lookup(self,x,z,**kwargs):
        if x>10:return None
        return SurfaceHit(0,0,((-10,0,-10),(10,0,-10),(10,0,10),(-10,0,10)),())


def model():
    return Model(tuple(Part(f':PP{k}wheel',p,(),(),()) for k,p in
                       zip(WHEELS,((-1,0,2),(1,0,2),(-1,0,-2),(1,0,-2)))),0)


class ContactTests(unittest.TestCase):
    def test_wheel_velocity_includes_pitch_yaw_and_center_of_mass(self):
        rig=WheelRig.from_model(model())
        velocity=rig.velocities(Pose((50,20,-10)),(1,2,3),(1,0,0))
        self.assertEqual(velocity['LF'],(1,0,3))
        self.assertEqual(velocity['LR'],(1,4,3))
        velocity=rig.velocities(Pose((0,0,0)),(0,0,0),(0,1,0),center_of_mass=(0,0,1))
        self.assertEqual(velocity['LF'],(1,0,1))
        with self.assertRaisesRegex(ValueError,'motion vectors'):
            rig.velocities(Pose((0,0,0)),(0,0,0),(0,float('nan'),0))

    def test_spawn_uses_wheel_bottoms_and_requires_four_supports(self):
        rig=WheelRig.from_model(model());radii=dict.fromkeys(WHEELS,0.4)
        pose,contacts=rig.spawn_pose(Terrain(),Pose.yaw((0,-2,0),0.3),radii)
        self.assertAlmostEqual(pose.position[1],0.42)
        self.assertTrue(all(abs(c.gap-0.02)<1e-8 for c in contacts))
        self.assertEqual(pose.rotation,Pose.yaw((0,0,0),0.3).rotation)
        with self.assertRaisesRegex(ValueError,'all four'):
            rig.spawn_pose(Terrain(),Pose((10,0,0)),radii)
        with self.assertRaisesRegex(ValueError,'clearance'):
            rig.spawn_pose(Terrain(),Pose((0,0,0)),radii,clearance=-1)

    def test_four_wheels_transform_clearance_and_missing_terrain(self):
        rig=WheelRig.from_model(model())
        contacts=rig.contacts(Terrain(),Pose.yaw((0,1,0),math.pi/2),dict.fromkeys(WHEELS,0.4))
        self.assertEqual(tuple(c.wheel for c in contacts),WHEELS)
        self.assertAlmostEqual(contacts[0].center[0],2)
        self.assertAlmostEqual(contacts[0].center[2],1)
        self.assertTrue(all(abs(c.gap-0.6)<1e-8 for c in contacts))
        contacts=rig.contacts(Terrain(),Pose((10,1,0)),dict.fromkeys(WHEELS,0.4))
        self.assertIsNone(contacts[1].gap)
        self.assertIsNotNone(contacts[0].gap)

    def test_invalid_markers_radii_and_pose(self):
        with self.assertRaisesRegex(ValueError,'wheel marker'):
            WheelRig.from_model(Model((),0))
        for radii in ({},dict.fromkeys(WHEELS,0),dict.fromkeys(WHEELS,float('nan'))):
            with self.assertRaisesRegex(ValueError,'radii'):
                WheelRig.from_model(model()).contacts(Terrain(),Pose((0,0,0)),radii)
        with self.assertRaisesRegex(ValueError,'orthonormal'):
            Pose((0,0,0),((2,0,0),(0,1,0),(0,0,1)))
        with self.assertRaisesRegex(ValueError,'reflection'):
            Pose((0,0,0),((-1,0,0),(0,1,0),(0,0,1)))
        with self.assertRaisesRegex(ValueError,'non-finite'):
            Pose((0,float('inf'),0))
