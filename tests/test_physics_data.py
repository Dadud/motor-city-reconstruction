import unittest
from client.physics_data import decode_physics_table


def fixture():
    columns=dict(PartTypeID=[110001],Ordinal=[1],Mass=[10.0])
    columns.update({f'Val{i}':[None] for i in range(1,51)})
    columns['Val1']=[150.0];columns['Val2']=[82.0];columns['Val3']=[18.0]
    columns['Val5']=[99.0]
    return columns


class PhysicsDataTests(unittest.TestCase):
    def test_native_prefix_stops_at_null_preserves_ordinal(self):
        record=decode_physics_table(fixture())[(110001,1)]
        self.assertEqual(record.values,(150,82,18))
        self.assertEqual(record.mass,10)
        columns=fixture();columns['Mass']=[None]
        self.assertIsNone(decode_physics_table(columns)[(110001,1)].mass)

    def test_column_lengths_identity_and_numeric_validation(self):
        columns=fixture();columns['Mass']=[]
        with self.assertRaisesRegex(ValueError,'lengths'):decode_physics_table(columns)
        columns=fixture();columns['Val1']=[float('nan')]
        with self.assertRaisesRegex(ValueError,'non-finite'):decode_physics_table(columns)
        columns=fixture();columns['Ordinal']=[-1]
        with self.assertRaisesRegex(ValueError,'identity'):decode_physics_table(columns)
