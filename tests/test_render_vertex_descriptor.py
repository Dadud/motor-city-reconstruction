import unittest

from client.render_vertex_descriptor import query_render_vertex_descriptor


class RenderVertexDescriptorTests(unittest.TestCase):
    def test_default_query_dispatches_mode_eight_and_writes_selected_outputs(self):
        mode=[0x1234]; calls=[]
        def set_mode(value):
            old=mode[0]; mode[0]=value; return old
        def dispatch(*args):
            calls.append(args[:3]); args[3][:]=[10,20,30,40]
        values,writes,render_mode=query_render_vertex_descriptor(0x4000,0,0b0101,
            set_mode=set_mode,dispatch=dispatch)
        self.assertEqual((values,writes,render_mode),((10,20,30,40),((0,10),(2,30)),8))
        self.assertEqual(mode,[0x1234])
        self.assertEqual(calls,[(8,1,0x4000)])

    def test_temporary_mode_uses_extended_dispatch_and_restores_nonzero_previous(self):
        mode=[0x55]; calls=[]
        def set_mode(value):
            old=mode[0]; mode[0]=value; return old
        def dispatch(target,count,source,scratch):
            calls.append((target,count,source)); scratch[:]=[1,2,3,4]
        result=query_render_vertex_descriptor(0x9000,0x20,0b1111,
            set_mode=set_mode,dispatch=dispatch)
        self.assertEqual(result,((1,2,3,4),((0,1),(1,2),(2,3),(3,4)),0x10008))
        self.assertEqual(mode,[0x55])
        self.assertEqual(calls,[(0x10008,1,0x9000)])

    def test_zero_previous_mode_is_not_restored(self):
        mode=[0]; calls=[]
        def set_mode(value):
            old=mode[0]; mode[0]=value; return old
        def dispatch(target,count,source,scratch):
            mode[0]=target; scratch[:]=[5,6,7,8]
        query_render_vertex_descriptor(1,0x10,0,set_mode=set_mode,dispatch=dispatch)
        self.assertEqual(mode,[0x10008])

    def test_rejects_invalid_inputs_and_unfilled_dispatch_result(self):
        noop=lambda *_:None
        for values in ((-1,0,0),(1,0,16),(1,0,0x10000)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                query_render_vertex_descriptor(*values,set_mode=lambda _:0,dispatch=noop)
        with self.assertRaises(ValueError):
            query_render_vertex_descriptor(1,0,0,set_mode=lambda _:0,dispatch=noop)


if __name__ == '__main__':
    unittest.main()
