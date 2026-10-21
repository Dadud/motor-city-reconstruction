import unittest
from pathlib import Path
from types import SimpleNamespace

from client.fce import Model, Part
from client.assembly import collect_render_group
from client.scene import (_marker_component_prefix, select_component_part,
                          DRIVER_MODEL_BY_VARIANT, split_component_marker,
                          ComponentModelNode, attach_component_from_nodes,
                          attach_component_marker, attach_rear_suspension,
                          collect_component_render_graph,
                          select_component_node, stock_scene)
from client.tire_response import f32


class SceneSelectionTests(unittest.TestCase):
    def test_recursive_generic_component_graph_matches_native_record_shape(self):
        root = Model((Part(':PPLfoo', (20, 30, 40), (), (), ()),), 0)
        foo = Model((Part(':PHfoo', (2, 3, 4), ((8, 10, 12),), (), ()),
                     Part(':PPRfog', (4, 5, 6), ((3, 4, 5),), (), ())), 0)
        fog = Model((Part(':PHfog', (1, 2, 3), ((7, 8, 9),), (), ()),), 0)
        nodes = (ComponentModelNode(5, foo, 0x1000),
                 ComponentModelNode(6, fog, 0x2000),
                 ComponentModelNode(0, root, 0x3000))

        graph = collect_component_render_graph(root, nodes, 0)
        self.assertEqual(tuple((entry.marker_path, entry.node_index,
                                entry.part_index, entry.record.words[1],
                                entry.record.words[4]) for entry in graph.entries),
                         (((':PPLfoo',), 0, 0, 0x1000, 1),
                          ((':PPLfoo', ':PPRfog'), 1, 0, 0x2000, 0x41)))
        self.assertEqual(graph.models[0].parts[0].origin, (20, 30, 40))
        self.assertEqual(graph.models[0].parts[1].origin, (22, 32, 42))
        self.assertEqual(graph.models[0].parts[0].vertices, ((26, 37, 48),))
        self.assertEqual(graph.models[0].parts[1].vertices, ((21, 31, 41),))
        self.assertEqual(graph.models[1].parts[0].origin, (22, 32, 42))
        self.assertEqual(graph.models[1].parts[0].vertices, ((16, 38, 48),))

        lod_one = collect_component_render_graph(root, nodes, 1)
        self.assertEqual(len(lod_one.entries), 1)
        self.assertEqual(lod_one.entries[0].record.words[4], 2)

    def test_recursive_component_graph_emits_native_driver_and_head_records(self):
        body = Model((Part(':PPdriver', (10, 20, 30), (), (), ()),), 0)
        driver = Model((Part(':PHdriver', (1, 2, 3), (), (), ()),
                        Part(':PHdriverhead', (4, 6, 8), (), (), ())), 0)
        graph = collect_component_render_graph(body,
            (ComponentModelNode(0, driver, 0x1234, 0x80e9),), 0)
        self.assertEqual(tuple((entry.part_index, entry.record.words[4],
                                entry.record.words[5]) for entry in graph.entries),
                         ((0, 0x81, 0x11), (1, 0x81, 0x10)))
        self.assertEqual(graph.models[0].parts[0].origin, (10, 20, 30))
        self.assertEqual(graph.models[0].parts[1].origin, (13, 24, 35))

    def test_recursive_component_graph_honors_engine_gate_and_rear_suspension(self):
        engine_body = Model((Part(':PPengine', (3, 4, 5), (), (), ()),), 0)
        engine = Model((Part(':PHengine', (0, 0, 0), (), (), ()),), 0)
        node = ComponentModelNode(0, engine, 0x1234)
        self.assertEqual(collect_component_render_graph(
            engine_body, (node,), 0).entries, ())
        enabled = collect_component_render_graph(engine_body, (node,), 0, 0x10000)
        self.assertEqual(len(enabled.entries), 1)
        self.assertEqual(enabled.entries[0].record.words[4:6], (1, 0))
        self.assertEqual(collect_component_render_graph(
            engine_body, (node,), 3, 0x10000).entries, ())

        rear_body = Model((Part(':PPrearsusp', (2.5, -3, 4.25), (), (), ()),), 0)
        suspension = Model((Part(':PHrearsusp', (9, 8, 7), (), (), ()),), 0)
        rear = collect_component_render_graph(
            rear_body, (ComponentModelNode(0, suspension, 0x5678),), 0)
        self.assertEqual(len(rear.entries), 1)
        self.assertEqual(rear.entries[0].record.words[4:6], (0x81, 0x0f))
        self.assertEqual(rear.models[0].parts[0].origin, rear_body.parts[0].origin)

    def test_recursive_component_graph_emits_both_corner_wheel_records(self):
        body = Model((Part(':PPRRwheel', (12, -7, 3), (), (), ()),), 0)
        wheel = Model((Part(':PHtire', (1, 2, 3), (), (), ()),
                       Part(':PHhubcap', (-4, 5, 6), (), (), ())), 0)
        graph = collect_component_render_graph(
            body, (ComponentModelNode(4, wheel, 0x1234),), 0)
        self.assertEqual(tuple((entry.part_index, entry.record.words[4],
                                entry.record.words[5]) for entry in graph.entries),
                         ((0, 0xc1, 10), (1, 0x41, 6)))
        self.assertEqual(tuple(part.origin for part in graph.models[0].parts),
                         (body.parts[0].origin, body.parts[0].origin))

    def test_component_node_lookup_uses_native_class_table_and_lod_priority(self):
        low = Model((Part(':PHtire', (0, 0, 0), (), (), ()),), 0)
        high = Model((Part(':PTtire', (0, 0, 0), (), (), ()),), 0)
        nodes = (ComponentModelNode(6, low, 0x1000),
                 ComponentModelNode(11, high, 0x2000))
        selected = select_component_node(nodes, 'R', 'tire', 3)
        self.assertEqual((selected.node_index, selected.part_index), (1, 0))
        self.assertEqual((selected.record.words[1], selected.record.words[4]),
                         (0x2000, 0x48))
        self.assertEqual(select_component_node(nodes, 'R', 'tire', 0).node_index, 0)
        self.assertIsNone(select_component_node(nodes, 'LF', 'tire', 3))

    def test_component_node_lookup_flows_into_generic_attachment(self):
        component = Model((Part(':PHfog', (2, 3, 4), ((8, 10, 12),), (), ()),), 0)
        nodes = (ComponentModelNode(6, component, 0x1234),)
        attached = attach_component_from_nodes(
            Part(':PPRfog', (20, 30, 40), (), (), ()), nodes)
        model, node_index, part_index, record = attached
        self.assertEqual((node_index, part_index), (0, 0))
        self.assertEqual(model.parts[0].vertices, ((14, 37, 48),))
        self.assertEqual((record.words[1], record.words[4]), (0x1234, 0x41))

    def test_generic_component_attachment_rebases_geometry_and_nested_marker(self):
        marker = Part(':PPRfog', (20, 30, 40), (), (), ())
        model = Model((Part(':PHfog', (2, 3, 4), ((8, 10, 12),), (), ()),
                       Part(':PPRchild', (4, 5, 6), (), (), ())), 0)
        transformed, index, record = attach_component_marker(
            marker, model, lod=0, model_handle=0x1234)
        self.assertEqual(index, 0)
        self.assertEqual(transformed.parts[0].origin, marker.origin)
        self.assertEqual(transformed.parts[0].vertices, ((14, 37, 48),))
        self.assertEqual(transformed.parts[1].origin, (18, 32, 42))
        self.assertEqual(record.words[1], 0x1234)
        self.assertEqual(record.words[4], 0x41)

    def test_generic_component_attachment_selects_lod_without_transform_at_lod3(self):
        marker = Part(':PPLfog', (20, 30, 40), (), (), ())
        model = Model((Part(':PHfog', (2, 3, 4), ((8, 10, 12),), (), ()),
                       Part(':PTfog', (5, 6, 7), ((9, 11, 13),), (), ())), 0)
        transformed, index, record = attach_component_marker(marker, model, lod=3)
        self.assertEqual(index, 1)
        self.assertEqual(transformed.parts[1].origin, marker.origin)
        self.assertEqual(transformed.parts[1].vertices, ((9, 11, 13),))
        self.assertEqual(record.words[4], 8)

    def test_rear_suspension_attachment_builds_native_record_and_places_marker(self):
        marker = Part(':PPrearsusp', (2.5, -3, 4.25), (), (), ())
        model = Model((Part(':PHrearsusp', (9, 8, 7), ((1, 2, 3),), (), ()),
                       Part(':PTrearsusp', (6, 5, 4), ((1, 2, 3),), (), ())), 0)
        placed, record = attach_rear_suspension(marker, model, lod=3,
                                                model_handle=0x1234)
        self.assertEqual(placed.origin, marker.origin)
        self.assertEqual(placed.vertices, ((1, 2, 3),))
        self.assertEqual(record.words[1], 0x1234)
        self.assertEqual(record.words[3], 1)
        self.assertEqual(record.words[4], 0x88)
        self.assertEqual(record.words[5], 0x0f)
        self.assertIsNone(attach_rear_suspension(
            marker, Model((Part(':PHother', (0, 0, 0), (), (), ()),), 0)))

    def test_render_group_lookup_uses_native_lod_then_model_order(self):
        first = Model((Part(':Hdoor', (0, 0, 0), (), (), ()),
                       Part(':Mdoor', (0, 0, 0), (), (), ())), 0)
        second = Model((Part(':Hdoor', (0, 0, 0), (), (), ()),), 0)
        selected = collect_render_group((first, second), 'door', 1,
                                       extra_flags=0x100, mesh_type=7)
        self.assertEqual(selected.words[1], 0)
        self.assertEqual(selected.words[3], 1)
        self.assertEqual(selected.words[4], 0x102)
        self.assertEqual(selected.words[5], 7)

    def test_render_group_lookup_falls_back_by_lod_before_next_model(self):
        first = Model((Part(':Hdoor', (0, 0, 0), (), (), ()),), 0)
        second = Model((Part(':Mdoor', (0, 0, 0), (), (), ()),), 0)
        selected = collect_render_group((first, second), 'door', 1)
        self.assertEqual((selected.words[1], selected.words[3], selected.words[4]),
                         (1, 0, 2))
        fallback = collect_render_group((first,), 'door', 3)
        self.assertEqual(fallback.words[4], 8)
        self.assertIsNone(collect_render_group((first,), 'missing', 3))

    def test_attachment_prefix_matches_native_corner_keys(self):
        expected = {'LF': 'LF', 'RF': 'RF', 'LR': 'LR', 'RR': 'RR'}
        for key, prefix in expected.items():
            self.assertEqual(_marker_component_prefix(f':PP{key}wheel', 0x1adb1), prefix)
        self.assertIsNone(_marker_component_prefix(':PPengine', 0x1adb1))
        self.assertIsNone(_marker_component_prefix(':PPRFwheel', 0x186a1))

    def test_native_marker_class_prefix_family(self):
        self.assertEqual(split_component_marker(':PPLFwheel'), ('LF', 'wheel'))
        self.assertEqual(split_component_marker(':PPLfog'), ('L', 'fog'))
        self.assertEqual(split_component_marker(':PPAdash'), ('A', 'dash'))
        self.assertEqual(split_component_marker(':PPengine'), ('', 'engine'))
        self.assertEqual(split_component_marker(':PHbody'), (None, None))
        self.assertEqual(len(DRIVER_MODEL_BY_VARIANT), 33)
        self.assertEqual((DRIVER_MODEL_BY_VARIANT[0], DRIVER_MODEL_BY_VARIANT[-1]),
                         ('driver18', 'driver13'))

    def test_native_component_option_search_is_exact_and_descending(self):
        low = Part(':PHtire', (0, 0, 0), (), (), ())
        high = Part(':PTtire', (0, 0, 0), (), (), ())
        model = Model((low, high, Part(':PHhubcap-extra', (0, 0, 0), (), (), ())), 0)
        self.assertIs(select_component_part(model, 'tire', 0), low)
        self.assertIs(select_component_part(model, 'tire', 3), high)
        self.assertIsNone(select_component_part(model, 'hubcap', 3))
        self.assertIs(select_component_part(model, 'tire', 4), high)
        self.assertIsNone(select_component_part(model, 'tire', -1))

    def test_stock_scene_places_main_engine_at_body_marker(self):
        body = Model((Part(':PPengine', (2, 3, 4), (), (), ()),
                       Part(':PPdriver', (2, 3, 4), (), (), ())), 0)
        engine = Model((Part(':PHengine', (0, 1, 0), ((1, 0, 0),), (), ()),
                        Part(':PPmanifold', (0, 2, 0), (), (), ()),
                        Part(':PPvalve', (0, 0, 0), (), (), ())), 0)
        manifold = Model((Part(':PHmanifold', (0, 0, 0), (), (), ()),
                          Part(':PPcarb', (0, 1, 0), (), (), ())), 0)
        carb = Model((Part(':PHcarb', (0, 0, 0), (), (), ()),
                      Part(':PPaircleaner', (0, 1, 0), (), (), ())), 0)
        cleaner = Model((Part(':PHaircleaner', (0, 0, 0), (), (), ()),), 0)
        valve = Model((Part(':PHvalve', (0, 0, 0), (), (), ()),), 0)
        driver_origin = (0.1, -0.2, 0.3)
        head_origin = (16777216.0, 0.1, -0.4)
        driver = Model((Part(':PHdriver', driver_origin, (), (), ()),
                         Part(':PHdriverhead', head_origin, (), (), ())), 0)

        class FakeAssets:
            paths = {'data/models/body.viv': Path('body.viv'),
                     'data/models/engine.viv': Path('engine.viv'),
                     'data/models/manifold.viv': Path('manifold.viv'),
                     'data/models/carb.viv': Path('carb.viv'),
                     'data/models/cleaner.viv': Path('cleaner.viv'),
                     'data/models/valve.viv': Path('valve.viv'),
                     'data/models/driver18.viv': Path('driver18.viv')}

            def load_vehicle(self, path):
                return {'body.viv': body, 'engine.viv': engine,
                        'manifold.viv': manifold, 'carb.viv': carb,
                        'cleaner.viv': cleaner, 'valve.viv': valve,
                        'driver18.viv': driver}[path.name]

            def load_textures(self, path, skin=None):
                return ()

        vehicle = SimpleNamespace(parts=tuple(SimpleNamespace(
            abstract_type_id=kind, attachment_id=0, filename=filename)
            for kind, filename in ((160001, 'engine'), (320001, 'manifold'),
                                   (330001, 'carb'), (340001, 'cleaner'),
                                   (1500001, 'valve'))))
        model, _, _, notes = stock_scene(FakeAssets(), Path('body.viv'), vehicle)
        placed = next(part for part in model.parts if part.name == 'engine')
        self.assertEqual(placed.origin, (2, 3, 4))
        self.assertEqual(placed.vertices, ((3, 2, 4),))
        self.assertEqual(next(part.origin for part in model.parts
                              if part.name == 'engine:manifold'), (2, 4, 4))
        self.assertEqual(next(part.origin for part in model.parts
                              if part.name == 'engine:manifold:carb'), (2, 5, 4))
        self.assertEqual(next(part.origin for part in model.parts
                              if part.name == 'engine:manifold:carb:aircleaner'), (2, 6, 4))
        self.assertEqual(next(part.name for part in model.parts
                              if part.name == 'engine:valve'), 'engine:valve')
        expected_head = tuple(f32(f32(head-driver)+marker)
            for marker, head, driver in zip((2, 3, 4), head_origin, driver_origin))
        observed_head = next(part.origin for part in model.parts
                             if part.name == 'driverhead')
        self.assertEqual(observed_head, expected_head)
        self.assertNotEqual(observed_head, tuple(
            marker+head-driver for marker, head, driver in
            zip((2, 3, 4), head_origin, driver_origin)))
        self.assertFalse(any('Missing component' in note for note in notes))


if __name__ == '__main__':
    unittest.main()
