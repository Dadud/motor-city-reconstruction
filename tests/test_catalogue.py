import unittest
from client.catalogue import Catalogue, validated_rows
from client.physics_data import PhysicsRecord
from types import SimpleNamespace


def fixture():
    return {
        'BrandedPart': [dict(BrandedPartID=1, ModelID=10, MfgDate='1932-01-01'),
                        dict(BrandedPartID=2, ModelID=20, PartTypeID=200)],
        'PartType': [dict(PartTypeID=200, AbstractPartTypeID=20001,
                          PartFilename='testcar', PartType='body')],
        'AbstractPartType': [dict(AbstractPartTypeID=20001, PartFilename='fallback')],
        'Model': [dict(ModelID=10, Debug_String='Test car', EModel='Coupe'),
                  dict(ModelID=20, EModel='Stock body')],
        'AttachmentPoint': [dict(AttachmentPointID=0, AttachmentPoint='default')],
        'StockVehicleAttributes': [dict(BrandedPartID=1, RetailPrice=123)],
        'StockAssembly': [dict(ParentBrandedPartID=1, ChildBrandedPartID=2,
                               AttachmentPointID=0, ConfigDefault=0, PhysicsDefault=0)]}


class CatalogueTests(unittest.TestCase):
    def test_owned_metadata_joins_actual_instance_brand_without_stock_substitution(self):
        import struct
        from client.owned_parts import OwnedPart
        catalogue = Catalogue(fixture())
        catalogue.branded[2].update(RetailPrice=500,MaxItemWear=1000,
            MfgDate='1955-01-01',EngineBlockFamilyID=None)
        catalogue.types[200]['PartGradeID'] = 3
        catalogue.models[20].update(BrandID=7,EShortModel='Body',EExtraInfo='details')
        owned = OwnedPart(42,2,17,25,99,50,75)
        metadata = catalogue.owned_part_metadata(owned)
        self.assertEqual((metadata.part_type_id,metadata.abstract_type_id,metadata.retail_price,
            metadata.max_item_wear,metadata.manufacture_year,metadata.engine_block_family_id),
            (200,20001,500,1000,1955,0))
        slot = metadata.apply_numeric_fields(owned)
        self.assertEqual(struct.unpack_from('<I',slot,0x5f8)[0],42)
        self.assertEqual(struct.unpack_from('<i',slot,0x610)[0],17)
        self.assertEqual(struct.unpack_from('<i',slot,0x614)[0],25)
        self.assertEqual(struct.unpack_from('<i',slot,0x1eb)[0],500)
        self.assertEqual(metadata.model_name,'Stock body')
        with self.assertRaises(ValueError):
            catalogue.owned_part_metadata(OwnedPart(43,999,0,0,0,0,0))

    def test_stock_dyno_record_uses_duty_rating_and_rejects_special_carb(self):
        import struct
        from client.dyno import FlowTemplate
        catalogue = Catalogue(fixture())
        catalogue.branded[2]['EngineBlockFamilyID'] = 10
        values = {
            1: (75, (.07779, .09525, 3.6213, 8)),
            2: (30, (0, 0, 0, 1, 6.15, 40.64, 40.64)),
            3: (10, (0, 1, 1, 6.64, 6.31, 12, 62, 66, 10)),
            4: (18, (0, 1)), 5: (25.6, (1, 0, 1)),
            6: (2, (0, 1, 100)), 7: (18, (0, 0, 1)),
            8: (5, ()), 9: (10, (0, 0))}
        catalogue.physics = {(key, 1): PhysicsRecord(key, 1, mass, fields)
                             for key, (mass, fields) in values.items()}
        catalogue.physics_duty = {(8, 1): 0}
        parts = tuple(SimpleNamespace(abstract_type_id=apt, part_type_id=key, branded_id=2)
                      for key, apt in enumerate((160001, 1000001, 1100001, 1200001,
                          320001, 330001, 280001, 340001, 300001), 1))
        vehicle = SimpleNamespace(branded_id=9, parts=parts)
        templates = {1: FlowTemplate(1, (2, 1.6, 25, 25),
                                    ((2,)*8, (.2,)*8, (4,)*8, (.3,)*8))}
        data = catalogue.stock_dyno_record(vehicle, templates)
        self.assertEqual(struct.unpack_from('<h', data, 0x6e)[0], 2)
        self.assertEqual(struct.unpack_from('<h', data, 0x7a)[0], 1)
        self.assertEqual(struct.unpack_from('<h', data, 0xa4)[0], 300)
        self.assertEqual(struct.unpack_from('<h', data, 0xa6)[0], 2)
        self.assertAlmostEqual(struct.unpack_from('<f', data, 0x324)[0], 3.99)
        catalogue.physics[(6, 1)] = PhysicsRecord(6, 1, 2, (0, .95, 400))
        data = catalogue.stock_dyno_record(vehicle, templates)
        # Stored float32 .95 is slightly below .95; __ftol truncates the
        # product, producing 379 rather than a rounded 380.
        self.assertEqual(struct.unpack_from('<h', data, 0xa4)[0], 379)
        catalogue.physics[(6, 1)] = PhysicsRecord(6, 1, 2, (6, 1, 100))
        with self.assertRaisesRegex(ValueError, 'unsupported stock dyno'):
            catalogue.stock_dyno_record(vehicle, templates)

    def test_stock_family_uses_branded_metadata_instead_of_physics_value(self):
        catalogue = Catalogue(fixture())
        catalogue.branded[2]['EngineBlockFamilyID'] = 10
        catalogue.physics = {
            (1, 1): PhysicsRecord(1, 1, 75, (.07779, .09525, 3.6213, 8, 1)),
            (2, 1): PhysicsRecord(2, 1, 30, (0, 0, 0, 1, 6.15, 40.64, 40.64))}
        vehicle = SimpleNamespace(branded_id=9, parts=(
            SimpleNamespace(abstract_type_id=160001, part_type_id=1, branded_id=2),
            SimpleNamespace(abstract_type_id=1000001, part_type_id=2, branded_id=3)))
        self.assertEqual(catalogue.engine_family(vehicle), 10)
        self.assertEqual(catalogue.engine_flow_template_id(vehicle), 1)
        catalogue.branded[2]['EngineBlockFamilyID'] = 1
        self.assertEqual(catalogue.engine_flow_template_id(vehicle), 3)
        for family in (None, True, 27):
            catalogue.branded[2]['EngineBlockFamilyID'] = family
            with self.assertRaises(ValueError):
                catalogue.engine_family(vehicle)

    def test_engine_block_selection_rejects_missing_and_ambiguous_records(self):
        catalogue = Catalogue(fixture())
        catalogue.physics = {(1, 1): PhysicsRecord(1, 1, 70, (.1, .1, 6.28, 8))}
        part = SimpleNamespace(abstract_type_id=160001, part_type_id=1, physics_default=0)
        vehicle = SimpleNamespace(branded_id=9, parts=(part,))
        self.assertEqual(catalogue.engine_block(vehicle).displacement_l, 6.28)
        catalogue.physics[(1, 2)] = catalogue.physics[(1, 1)]
        with self.assertRaisesRegex(ValueError, 'ambiguous.*physics'):
            catalogue.engine_block(vehicle)
        vehicle.parts = ()
        with self.assertRaisesRegex(ValueError, 'missing engine block'):
            catalogue.engine_block(vehicle)

    def test_stock_springs_and_shocks_are_resolved_independently(self):
        catalogue=Catalogue(fixture())
        catalogue.physics={(1,1):PhysicsRecord(1,1,5,(12250,0)),
                           (2,1):PhysicsRecord(2,1,3,(0.2,0.2032))}
        parts=tuple(SimpleNamespace(abstract_type_id=kind,part_type_id=identifier,attachment_id=axle)
                    for kind,identifier in ((12001,1),(11001,2)) for axle in (10,11))
        vehicle=SimpleNamespace(branded_id=9,parts=parts)
        result=catalogue.suspension(vehicle)
        self.assertEqual(set(result),{'LF','RF','LR','RR'})
        self.assertEqual(result['LF'][0].rate,12250)
        self.assertEqual(result['RR'][1].length,0.2032)
        vehicle.parts=parts[:2]
        with self.assertRaisesRegex(ValueError,'shock'):
            catalogue.suspension(vehicle)

    def test_tire_attachment_precedence_and_ordinal_ambiguity(self):
        catalogue=Catalogue(fixture())
        catalogue.physics={(1,1):PhysicsRecord(1,1,10,(150,82,18)),
                           (2,1):PhysicsRecord(2,1,10,(225,60,15))}
        part=lambda kind,attachment:SimpleNamespace(abstract_type_id=110001,part_type_id=kind,attachment_id=attachment,physics_default=0)
        vehicle=SimpleNamespace(branded_id=9,parts=(part(1,10),part(1,11),part(2,1)))
        tires=catalogue.tire_dimensions(vehicle)
        self.assertAlmostEqual(tires['LF'].radius,0.3255)
        self.assertAlmostEqual(tires['RF'].radius,0.3516)
        catalogue.physics[(2,2)]=PhysicsRecord(2,2,10,(200,60,15))
        with self.assertRaisesRegex(ValueError,'ambiguous.*physics'):
            catalogue.tire_dimensions(vehicle)

    def test_rows_reject_incomplete_columns_and_duplicate_keys(self):
        for columns, declared in (({'id': [1], 'name': []}, 1), ({'id': [1]}, 2),
                                  ({'id': [1, 1]}, 2), ({'id': [None]}, 1)):
            with self.assertRaises(ValueError):
                validated_rows('test', columns, declared, 'id')

    def test_join_retains_zero_configuration_flags(self):
        vehicle = Catalogue(fixture()).vehicle(1)
        self.assertEqual((vehicle.name, vehicle.year, vehicle.body_filename),
                         ('Test car', 1932, 'testcar'))
        self.assertEqual(vehicle.parts[0].config_default, 0)
        self.assertEqual(len(vehicle.parts), 1)

    def test_broken_reference_is_rejected(self):
        tables = fixture()
        tables['StockAssembly'][0]['ChildBrandedPartID'] = 999
        with self.assertRaisesRegex(ValueError, 'missing database reference'):
            Catalogue(tables).vehicle(1)

    def test_missing_stock_body_and_duplicate_identity_are_rejected(self):
        tables = fixture()
        tables['StockAssembly'] = []
        with self.assertRaisesRegex(ValueError, 'one stock body'):
            Catalogue(tables).vehicle(1).body_filename
        tables = fixture()
        tables['BrandedPart'].append(tables['BrandedPart'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            Catalogue(tables)
