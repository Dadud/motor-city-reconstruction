import struct
import unittest
from unittest.mock import patch
from client.mechanical_assembly import assemble_mechanical_components,assembly_report
from client.mechanical_loaders import MECHANICAL_LOADERS
from tools.body_accessory_oracle import base_component


def part(kind):
    image=base_component(kind);struct.pack_into('<I',image,0x338,kind)
    return bytes(image)


class MechanicalAssemblyTests(unittest.TestCase):
    def test_preflight_failure_preserves_all_inputs(self):
        initial=bytes([73])*0x820;component=part(23001)
        result=assemble_mechanical_components((component,),{},tire_templates=None,initial_configuration=initial)
        self.assertEqual(result.status,0)
        self.assertEqual(result.configuration,initial)
        self.assertEqual(result.components,(component,))
        self.assertFalse(result.loader_calls)
        self.assertTrue(result.missing)

    def test_rejected_then_valid_duplicate_still_fails(self):
        valid=part(23001);bad=bytearray(valid);struct.pack_into('<I',bad,0x14,99)
        with patch('client.mechanical_assembly.DISPATCH',((23001,0,1,1,True),)):
            result=assemble_mechanical_components((bytes(bad),valid),{},tire_templates=None)
        self.assertEqual(result.status,0)
        self.assertEqual(result.loader_calls,((23001,0,1),(23001,1,0)))
        self.assertEqual(struct.unpack_from('<f',result.configuration,0x20)[0],10.)
        self.assertEqual(struct.unpack_from('<f',result.components[0],0x1c)[0],1.)

    def test_success_cap_leaves_extra_component_unchanged(self):
        first=part(23001);extra=bytearray(first);struct.pack_into('<f',extra,0x1c,123.)
        with patch('client.mechanical_assembly.DISPATCH',((23001,0,1,1,True),)), \
             patch('client.mechanical_assembly.finalize_loaded_configuration',side_effect=lambda image,**kw:image), \
             patch('client.mechanical_assembly.finalize_engine_configuration',side_effect=lambda image,*args,**kw:image):
            result=assemble_mechanical_components((first,bytes(extra)),{},tire_templates=None)
        self.assertEqual(result.status,1)
        self.assertEqual(len(result.loader_calls),1)
        self.assertEqual(result.components[1],bytes(extra))

    def test_unsupported_present_dispatcher_is_explicit(self):
        component=bytearray(part(23001));struct.pack_into('<I',component,0x338,350001)
        with patch('client.mechanical_assembly.DISPATCH',((350001,0,0,1,True),)):
            result=assemble_mechanical_components((bytes(component),),{},tire_templates=None)
        self.assertEqual(result.unsupported,(350001,))
        self.assertFalse(assembly_report(result)['mechanical_assembly_complete'])

    def test_zero_required_mass_resets_quality_without_calling_loader(self):
        image=bytearray(part(23001));struct.pack_into('<f',image,0x30,0.)
        with patch('client.mechanical_assembly.DISPATCH',((23001,0,1,1,True),)):
            result=assemble_mechanical_components((bytes(image),),{},tire_templates=None)
        self.assertEqual(result.status,0)
        self.assertEqual(result.loader_calls,((23001,0,'zero_mass'),))
        self.assertEqual(struct.unpack_from('<f',result.components[0],0x1c)[0],1.)

    def test_body_height_exception_uses_truncation(self):
        body=base_component(20001);struct.pack_into('<f',body,0x4c,.28)
        self.assertEqual(MECHANICAL_LOADERS[20001](bytes(0x820),body).status,2)
        struct.pack_into('<f',body,0x54,6.9)
        self.assertEqual(MECHANICAL_LOADERS[20001](bytes(0x820),body).status,0)

    def test_unknown_bar_attachment_succeeds_without_mass_or_quality_writes(self):
        bar=base_component(13001);struct.pack_into('<I',bar,0x18,5)
        result=MECHANICAL_LOADERS[13001](bytes(0x820),bar)
        self.assertEqual((result.status,result.configuration,result.component),(0,bytes(0x820),bytes(bar)))

    def test_image_bounds_are_checked(self):
        with self.assertRaises(ValueError):assemble_mechanical_components((bytes(5),),{},tire_templates=None)
