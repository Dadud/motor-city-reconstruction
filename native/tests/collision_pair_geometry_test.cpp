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
}
