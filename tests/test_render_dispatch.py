import unittest

from client.render_dispatch import RenderDispatchState, dispatch_object_geometry


class RenderDispatchTests(unittest.TestCase):
    def test_mode_six_handoff_and_state_restore(self):
        old_matrix, old_position = object(), object()
        matrix, position, destination, points = object(), object(), object(), object()
        state = RenderDispatchState(old_matrix, old_position, 7)
        calls = []
        dispatch_object_geometry(
            state, vertex_count=22, local_vertices=points, world_vertices=destination,
            matrix=matrix, position=position, output_stride_bytes=12,
            draw=lambda *args: calls.append(args))
        self.assertEqual(calls, [(6, 22, points, destination, matrix, position, 12)])
        self.assertIs(state.matrix_source, old_matrix)
        self.assertIs(state.position_source, old_position)
        self.assertEqual(state.output_stride_bytes, 7)
        self.assertTrue(state.matrix_dirty and state.position_dirty)
        self.assertTrue(state.dispatch_cache_valid)

    def test_zero_state_invalidates_cache_and_restore_occurs_on_error(self):
        state = RenderDispatchState(object(), object(), 7)
        def fail(*args):
            self.assertIsNone(state.position_source)
            raise RuntimeError('graphics backend failure')
        old_matrix, old_position = state.matrix_source, state.position_source
        with self.assertRaises(RuntimeError):
            dispatch_object_geometry(
                state, vertex_count=22, local_vertices=object(), world_vertices=object(),
                matrix=object(), position=None, output_stride_bytes=0, draw=fail)
        self.assertIs(state.matrix_source, old_matrix)
        self.assertIs(state.position_source, old_position)
        self.assertEqual(state.output_stride_bytes, 7)
        self.assertFalse(state.dispatch_cache_valid)


if __name__ == '__main__':
    unittest.main()
