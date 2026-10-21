import struct
import unittest

from client.collision_dispatch import (CollisionDispatchServices,
                                       CollisionDispatchWorld,
                                       dispatch_world_collision)


def image(**fields):
    result = bytearray(0x500)
    for name, offset, value in fields.values():
        if name == 'f':
            struct.pack_into('<f', result, offset, value)
        elif name == 'h':
            struct.pack_into('<h', result, offset, value)
        elif name == 'b':
            result[offset] = value
        elif name == 'i':
            struct.pack_into('<i', result, offset, value)
        else:
            struct.pack_into('<I', result, offset, value)
    return result


class CollisionDispatchTests(unittest.TestCase):
    def make_services(self, events, *, terrain=1, correction=0, filters=()):
        filter_values = iter(filters)
        def mark(name, result=None):
            def callback(*args):
                events.append((name, args))
                return result
            return callback
        return CollisionDispatchServices(
            initialize_contact_fields=mark('initialize'),
            terrain_query=mark('terrain', terrain),
            support_correction=mark('support', correction),
            high_speed_action=mark('high_speed'),
            inactive_object_update=mark('inactive'),
            pair_filter=lambda *args: next(filter_values),
            pair_response=mark('pair_response'),
            after_candidates=mark('after_candidates'),
            contact_followup=mark('contact'),
            post_collision=mark('post'),
            final_update=mark('final'))

    def test_inactive_owner_still_resets_and_decrements_countdown(self):
        owner = image(active=('i', 4, 0), countdown=('i', 0x410, 2))
        owner[0x3c4:0x400] = bytes([0xa5]) * 0x3c
        events = []
        world = CollisionDispatchWorld([], (), bytes(0x80), (0, 0, 0))
        result = dispatch_world_collision(owner, world, self.make_services(events))
        self.assertFalse(result['active'])
        self.assertEqual(struct.unpack_from('<i', owner, 0x410)[0], 1)
        self.assertEqual(owner[0x3c4:0x400], bytes(0x3c))
        self.assertEqual([name for name, _ in events], ['initialize'])

    def test_pair_response_uses_ordered_filter_retry_and_normal(self):
        other = image(radius=('f', 0xd8, 2.0))
        owner = image(active=('i', 4, 1), radius=('f', 0xd8, 2.0),
                      speed=('f', 0x350, 0.7), high_speed=('f', 0xc4, 1.0))
        events = []
        world = CollisionDispatchWorld([other, image()], (), bytes(0x80), (0, 3, 4),
                                       impact_count=1)
        services = self.make_services(events, filters=(1, 0))
        result = dispatch_world_collision(owner, world, services)
        self.assertEqual(result['pairs'], ((0, 2, True),))
        self.assertEqual(result['responses'], 1)
        call = next(args for name, args in events if name == 'pair_response')
        self.assertIs(call[0], owner)
        self.assertIs(call[1], other)
        self.assertEqual(call[3], (-0.0, -0.6000000238418579,
                                   -0.800000011920929))
        self.assertEqual(struct.unpack_from('<h', owner, 0x3bc)[0], 2)
        self.assertIs(world.candidates[1], owner)

    def test_first_pair_filter_rejection_does_not_respond(self):
        other = image(radius=('f', 0xd8, 2.0))
        owner = image(active=('i', 4, 1), radius=('f', 0xd8, 2.0),
                      speed=('f', 0x350, 0.7))
        events = []
        world = CollisionDispatchWorld([other], (), bytes(0x80), (1, 0, 0),
                                       impact_count=1)
        result = dispatch_world_collision(
            owner, world, self.make_services(events, filters=(0,)))
        self.assertEqual(result['pairs'], ((0, 1, False),))
        self.assertEqual(result['responses'], 0)
        self.assertFalse(any(name == 'pair_response' for name, _ in events))

    def test_pair_filter_caps_at_original_33_attempts(self):
        other = image(radius=('f', 0xd8, 2.0))
        owner = image(active=('i', 4, 1), radius=('f', 0xd8, 2.0),
                      speed=('f', 0x350, 0.7))
        events = []
        world = CollisionDispatchWorld([other], (), bytes(0x80), (0, 0, 0),
                                       impact_count=1)
        result = dispatch_world_collision(
            owner, world, self.make_services(events, filters=(1,) * 33))
        self.assertEqual(result['pairs'], ((0, 33, True),))
        self.assertEqual(result['responses'], 1)

    def test_contact_followups_filter_invalid_neighbor_indices(self):
        owner = image(active=('i', 4, 1), speed=('f', 0x350, 0.7),
                      contact_index=('I', 0x374, 0))
        owner[0x400] = 0x40
        events = []
        row = (-1, 0, 1, 2, 3, 4, 5, 6)
        world = CollisionDispatchWorld([], (), bytes(0x80), (0, 0, 0),
            contact_neighbor_rows=(row,), contact_index_limit=3)
        result = dispatch_world_collision(owner, world,
                                          self.make_services(events))
        contacts = [args[1] for name, args in events if name == 'contact']
        self.assertEqual(contacts, [0, 0, 1, 2, 3])
        self.assertTrue(result['collision_allowed'])


if __name__ == '__main__':
    unittest.main()
