#include "mco/collision_pair_geometry.hpp"
#include <cassert>

int main() {
    using namespace mco;
    const OrientedCollisionBox owner{{0, 0, 0},
        {{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}}, {2, 2, 2}};
    const OrientedCollisionBox target{{0, 0, 0},
        {{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}}, {1, 1, 1}};
    const auto hit = oriented_box_point_test(owner, target, {1, -1, 0.5});
    assert(hit.inside);
    assert(hit.owner_local_point == (std::array<float, 3>{1, -1, 0.5f}));
    assert(hit.target_world_point == (std::array<float, 3>{1, -1, 0.5f}));
    const auto miss = oriented_box_point_test(owner, target, {3, 0, 0});
    assert(!miss.inside);
    assert(miss.owner_local_point[0] == 3);

    const OrientedCollisionBox small_owner{{0, 0, 0},
        {{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}}, {1, 1, 1}};
    const OrientedCollisionBox large_target{{0, 0, 0},
        {{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}}, {2, 2, 2}};
    const auto reversed_hit = owner_point_direction_test(
        small_owner, large_target, {1, -1, 0.5});
    assert(reversed_hit.inside);
    assert(reversed_hit.target_local_point == (std::array<float, 3>{1, -1, 0.5f}));
    assert(reversed_hit.owner_world_point == (std::array<float, 3>{1, -1, 0.5f}));
    assert(reversed_hit.owner_direction[0] < 0);
    const auto contact_hit = owner_point_contact_test(
        small_owner, large_target, {1, -1, 0.5});
    assert(contact_hit.inside);
    assert(contact_hit.owner_world_point == reversed_hit.owner_world_point);
    const auto reversed_miss = owner_point_contact_test(
        small_owner, large_target, {3, 0, 0});
    assert(!reversed_miss.inside);
}
