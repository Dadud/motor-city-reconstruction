import unittest
import struct

from client.model_owner import (build_component_node_list,
                                admit_stock_owner_job,
                                build_default_driver_node,
                                complete_ready_stock_owner_job,
                                poll_owner_job_result,
                                build_stock_component_node_list,
                                selected_render_head)


def tpart_image(class_id, attachment_id, marker, bounds):
    image = bytearray([marker]) * 0x984
    struct.pack_into('<I', image, 0x18, attachment_id)
    struct.pack_into('<II', image, 0x104, *bounds)
    struct.pack_into('<I', image, 0x338, class_id)
    return bytes(image)


class SelectedRenderHeadTests(unittest.TestCase):
    def test_selects_highest_populated_slot_at_or_below_limit(self):
        heads = (0x1000, 0, 0x3000, 0x4000)
        self.assertEqual(selected_render_head(heads, 3), 0x4000)
        self.assertEqual(selected_render_head(heads, 2), 0x3000)
        self.assertEqual(selected_render_head(heads, 1), 0x1000)
        self.assertEqual(selected_render_head(heads, 0), 0x1000)

    def test_empty_prefix_returns_null(self):
        self.assertEqual(selected_render_head((0, 0, 0x3000, 0x4000), 1), 0)

    def test_rejects_invalid_slot_count_and_index(self):
        with self.assertRaises(ValueError):
            selected_render_head((1, 2, 3), 2)
        for index in (-1, 4, True):
            with self.subTest(index=index), self.assertRaises(ValueError):
                selected_render_head((0, 0, 0, 0), index)

    def test_rejects_non_pointer_values(self):
        for value in (-1, 0x100000000, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                selected_render_head((value, 0, 0, 0), 0)


class ComponentNodeListTests(unittest.TestCase):
    def test_stock_owner_admission_matches_failure_cleanup_order(self):
        cases=((0,1,True,False,False,'completion status is not success'),
               (1,0,True,False,False,'no source slots'),
               (1,1,False,False,True,'scratch allocation failed'),
               (1,1,True,True,False,'ready'))
        for status,count,allocated,admitted,release,reason in cases:
            with self.subTest(status=status,count=count,allocated=allocated):
                result=admit_stock_owner_job(status,count,allocated)
                self.assertEqual((result.admitted,result.release_completion,result.reason),
                                 (admitted,release,reason))

    def test_owner_worker_pending_poll_pumps_only_the_designated_thread(self):
        events=[]
        states=iter((2,0))
        result=poll_owner_job_result(
            2,lambda:events.append(('read',)) or next(states),4,4,
            lambda value:events.append(('pump',value)),
            lambda milliseconds:events.append(('sleep',milliseconds)))
        self.assertEqual(result.state,0)
        self.assertFalse(result.ready_result)
        self.assertEqual((result.waits,result.pumps),(2,2))
        self.assertEqual(events,[('pump',0),('sleep',10),('read',),
                                 ('pump',0),('sleep',10),('read',)])

        events=[]
        result=poll_owner_job_result(
            2,lambda:events.append(('read',)) or 3,7,8,None,
            lambda ms:events.append(('sleep',ms)))
        self.assertEqual((result.state,result.waits,result.pumps),(3,1,0))
        self.assertEqual(events,[('sleep',10),('read',)])

    def test_owner_worker_status_gate_distinguishes_terminal_and_ready_states(self):
        for state,ready in ((0,False),(1,False),(98,False),(99,True),(-1,True)):
            with self.subTest(state=state):
                result=poll_owner_job_result(state,None,1,2,None,None)
                self.assertEqual(result.ready_result,ready)
                self.assertEqual((result.waits,result.pumps),(0,0))
        with self.assertRaises(TimeoutError):
            poll_owner_job_result(2,lambda:2,1,2,None,lambda _:None,max_waits=1)

    def test_completes_ready_stock_job_owner_fields_and_selected_vehicle_name(self):
        slot=bytearray(0x63c)
        struct.pack_into('<I',slot,0,0x65)
        struct.pack_into('<I',slot,0x1e3,1)
        struct.pack_into('<I',slot,0x1e7,0xDEADBEEF)
        struct.pack_into('<I',slot,0x338,20001)
        slot[0x2c7:0x2cc]=b'Ford\0'
        slot[0x307:0x310]=b'32 Coupe\0'
        job=bytearray(0xbb4)
        struct.pack_into('<I',job,0x5c,0x12345678)
        for index in range(12):
            struct.pack_into('<I',job,0x68+index*4,0xA5000000+index)
        job[0x1d7:0x1de]=b'loaded\0'
        struct.pack_into('<I',job,0xbb0,0x87654321)
        owner=bytearray(0x878)
        result=complete_ready_stock_owner_job(
            bytes(owner),(bytes(slot),),bytes(job),(0x3000,),0x4000,
            lambda kind,attachment:0x70000000+kind+attachment,
            model_prefix='C:\\MCO\\Data\\Models\\',
            driver_model_key='driver18',driver_size=75)
        self.assertEqual(result.source_vehicle_index,0)
        self.assertEqual(result.owner_image[:14],b'Ford 32 Coupe\0')
        self.assertEqual(struct.unpack_from('<I',result.owner_image,0x198)[0],
                         0xDEADBEEF)
        self.assertEqual(struct.unpack_from('<I',result.owner_image,0x238)[0],
                         0x87654321)
        self.assertEqual(struct.unpack_from('<I',result.owner_image,0x178)[0],
                         0x12345678)
        self.assertEqual(struct.unpack_from('<I',result.owner_image,0x40)[0],2)
        self.assertEqual(struct.unpack_from('<I',result.owner_image,0x19c)[0],0x4000)
        self.assertEqual(result.owner_image[0x1ad:0x1b1],
                         struct.pack('<I',0xA5000000))

    def test_default_driver_node_initializes_original_fields_and_prepends(self):
        calls=[]
        result=build_default_driver_node(
            0x3000,0x2000,7,
            lambda kind,attachment: calls.append((kind,attachment)) or 0x70123456)
        self.assertEqual(calls,[(0x80e9,0)])
        self.assertEqual((result.head,result.count),(0x3000,8))
        self.assertEqual(result.node.address,0x3000)
        image=result.node.image
        self.assertEqual(len(image),0x984)
        self.assertEqual(struct.unpack_from('<I',image)[0],0x2000)
        self.assertEqual(struct.unpack_from('<I',image,0x11c)[0],0x70123456)
        self.assertEqual(struct.unpack_from('<I',image,0x338)[0],0x80e9)
        self.assertEqual(image[0x53f:0x546],b'Driver\0')
        self.assertEqual([struct.unpack_from('<I',image,offset)[0]
                          for offset in (0x1c,0x24,0x28,0x2c,0x30,0x34,0x38,0x980)],
                         [0x3f800000,0x4700e900,0x3f800000,0x3f800000,
                          0x42960000,0x3f800000,0x46ea6000,0x42960000])

    def test_copies_templates_and_prepends_with_original_field_overrides(self):
        templates = (tpart_image(20001, 10, 0xA1, (0x11, 0x22)),
                     tpart_image(34001, 11, 0xB2, (0x33, 0x44)))
        lookups = []

        def model_lookup(class_id, attachment_id):
            lookups.append((class_id, attachment_id))
            return 0x70000000 + class_id + attachment_id

        result = build_component_node_list(templates, (0x1000, 0x2000), model_lookup)
        self.assertEqual(result.count, 2)
        self.assertEqual(result.head, 0x2000)
        self.assertEqual([node.address for node in result.nodes], [0x1000, 0x2000])
        self.assertEqual(lookups, [(20001, 10), (34001, 11)])
        first, second = (node.image for node in result.nodes)
        self.assertEqual(struct.unpack_from('<II', first), (0, 0))
        self.assertEqual(struct.unpack_from('<II', second), (0x1000, 0))
        self.assertEqual(struct.unpack_from('<I', first, 0x1c), (0x3f800000,))
        self.assertEqual(struct.unpack_from('<IIII', first, 0x10c),
                         (0x11, 0x22, 0x11, 0x22))
        self.assertEqual(struct.unpack_from('<I', first, 0x11c),
                         (0x70000000 + 20001 + 10,))
        self.assertEqual(first[0x200:0x338], templates[0][0x200:0x338])

    def test_rejects_malformed_templates_addresses_and_model_handles(self):
        template = tpart_image(20001, 0, 0xA1, (1, 2))
        with self.assertRaises(ValueError):
            build_component_node_list((template,), (), lambda *_: 1)
        with self.assertRaises(ValueError):
            build_component_node_list((b'bad',), (0x1000,), lambda *_: 1)
        with self.assertRaises(ValueError):
            build_component_node_list((template,), (0,), lambda *_: 1)
        with self.assertRaises(ValueError):
            build_component_node_list((template,), (0x1000,), lambda *_: -1)

    def test_composes_paired_stock_slot_through_owner_nodes(self):
        slot = bytearray(0x63c)
        struct.pack_into('<I', slot, 0, 20001)
        struct.pack_into('<i', slot, 0x10, 1)
        struct.pack_into('<I', slot, 0x1e3, 1)
        struct.pack_into('<i', slot, 0x61c, 10)
        slot[0x387:0x38d] = b'32ford'
        slot[0x390:0x394] = b'FORD'
        slot[0x2c7:0x2cb] = b'Ford'
        slot[0x307:0x30f] = b'32 Coupe'
        result = build_stock_component_node_list(
            (bytes(slot),), (0x1000, 0x2000),
            lambda kind, attachment: 0x70000000 + kind + attachment,
            model_prefix='C:\\MCO\\Data\\Models\\')
        self.assertEqual(result.count, 2)
        self.assertEqual([part.attachment for part in result.mechanical_parts],
                         [1, 2])
        self.assertEqual(result.head, 0x2000)
        first, second = (node.image for node in result.component_nodes.nodes)
        self.assertEqual(struct.unpack_from('<I', first, 0x11c)[0],
                         0x70000000 + 20001 + 1)
        self.assertEqual(struct.unpack_from('<I', second)[0], 0x1000)
        self.assertIn(b'C:\\MCO\\Data\\Models\\32ford.viv', first)

        with_driver = build_stock_component_node_list(
            (bytes(slot),), (0x1000, 0x2000),
            lambda kind, attachment: 0x70000000 + kind + attachment,
            model_prefix='C:\\MCO\\Data\\Models\\',
            driver_node_address=0x3000)
        self.assertEqual(with_driver.count, 3)
        self.assertEqual(with_driver.head, 0x3000)
        self.assertEqual(with_driver.component_nodes.nodes[-1].image[0x53f:0x546],
                         b'Driver\0')
        self.assertEqual(struct.unpack_from('<I',
                         with_driver.component_nodes.nodes[-1].image)[0],0x2000)


if __name__ == '__main__':
    unittest.main()
