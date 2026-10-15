import struct
import unittest
from client.mechanical_loaders import MECHANICAL_LOADERS
from tools.engine_auxiliary_oracle import base_component
from tools.engine_component_loaders_oracle import configuration


class EngineAuxiliaryTests(unittest.TestCase):
    def test_pipe_mutates_contribution_before_rejecting_invalid_mass(self):
        part=base_component(290001);struct.pack_into('<f',part,0x30,0.)
        struct.pack_into('<ff',part,0x40,1.,5.)
        image=configuration();result=MECHANICAL_LOADERS[290001](image,part)
        self.assertEqual((result.status,result.configuration),(2,image))
        self.assertEqual(struct.unpack_from('<f',result.component,0x44)[0],0.)
        struct.pack_into('<I',part,0x14,99)
        result=MECHANICAL_LOADERS[290001](image,part)
        self.assertEqual((result.status,result.component),(1,bytes(part)))

    def test_carburetor_quality_uses_truncated_duty(self):
        part=base_component(330001);struct.pack_into('<f',part,0x34,2.9)
        result=MECHANICAL_LOADERS[330001](configuration(),part)
        self.assertEqual(result.status,0)
        self.assertEqual(struct.unpack_from('<i',result.configuration,0x3c4)[0],2)
        self.assertEqual(struct.unpack_from('<f',result.component,0x1c)[0],2.)

    def test_air_cleaner_installation_override_requires_all_flags(self):
        part=base_component(340001)
        for offset in (0x96c,0x930,0x51b,0x527,0x94c):struct.pack_into('<I',part,offset,1)
        installed=MECHANICAL_LOADERS[340001](configuration(),part)
        self.assertEqual(installed.status,0)
        self.assertEqual(struct.unpack_from('<f',installed.configuration,0x3f4)[0],0.)
        struct.pack_into('<I',part,0x930,0)
        ordinary=MECHANICAL_LOADERS[340001](configuration(),part)
        self.assertGreater(struct.unpack_from('<f',ordinary.configuration,0x3f4)[0],0.)

    def test_muffler_uses_previously_loaded_manifold(self):
        outputs=[]
        for manifold in range(4):
            image=bytearray(configuration());struct.pack_into('<i',image,0x57c,manifold)
            result=MECHANICAL_LOADERS[300001](image,base_component(300001))
            self.assertEqual(result.status,0)
            outputs.append(struct.unpack_from('<f',result.configuration,0x5b0)[0])
        self.assertEqual(len(set(outputs)),4)
        self.assertGreater(outputs[2],outputs[3])
