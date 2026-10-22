#include "mco/collision_pair_response.hpp"
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace {
void check(bool value) {
    if (!value) throw std::runtime_error("collision pair response check failed");
}
}

int main() {
    const std::array<double, 9> identity{1,0,0,0,1,0,0,0,1};
    mco::CollisionImpactBody owner{}, target{};
    owner.address = 0x1000;
    owner.linear_velocity = {1,0,0};
    owner.mass = 1;
    owner.inertia = {1,{1,1,1},identity,identity};
    target.address = 0x2000;
    target.position = {1,0,0};
    target.mass = 1;
    target.inertia = {1,{1,1,1},identity,identity};

    const auto impact = mco::resolve_pair_impulse(owner, target, {.5f,0,0},
                                                  {-1,0,0}, .45f, .2f);
    check(impact.collided && impact.samples == 25 && impact.impact_status == 2);
    check(impact.effective_mass == .5f);
    check(impact.owner.linear_velocity == std::array<float,3>{.5f,0,0});
    check(impact.target.linear_velocity == std::array<float,3>{.5f,0,0});
    check(impact.owner.contact_record[0x3c4] == 0 &&
          impact.owner.contact_record[0x3c5] == 0x20);
    check(impact.target.contact_record[0x3c4] == 0 &&
          impact.target.contact_record[0x3c5] == 0x10);
    check(impact.owner.contact_record[0x3e4] == 2);
    check(impact.owner.contact_record[0x3f4] == 4 &&
          impact.owner.contact_record[0x3f8] == 6);

    mco::CollisionImpactBody support{};
    support.address = 0x3000;
    support.linear_velocity = {1,0,0};
    support.mass = 1;
    support.inertia = {1,{1,1,1},identity,identity};
    support.embedded_contact_pointer = 0x12345678;
    const auto surface = mco::resolve_surface_impulse(support, {.5f,0,0},
                                                      {-1.f,0,0}, .45f, .2f);
    check(surface.collided && surface.samples == 28 && surface.impact_status == 2);
    check(std::abs(surface.body.linear_velocity[0]) < 1e-6f &&
          surface.body.linear_velocity[1] == 0.f && surface.body.linear_velocity[2] == 0.f);
    check(surface.body.contact_record[0x3e4] == 2 &&
          surface.body.contact_record[0x3f4] == 2 &&
          surface.body.contact_record[0x3f8] == 0x78 &&
          surface.body.contact_record[0x3f9] == 0x56 &&
          surface.body.contact_record[0x3fa] == 0x34 &&
          surface.body.contact_record[0x3fb] == 0x12);

    owner.linear_velocity = {-1,0,0};
    owner.contact_record.fill(0xa5);
    target.contact_record.fill(0xa5);
    const auto separating = mco::resolve_pair_impulse(owner, target, {.5f,0,0},
                                                       {-1,0,0}, .45f, .2f);
    check(!separating.collided && separating.samples == 0);
    check(separating.owner.linear_velocity == owner.linear_velocity);
    check(separating.owner.contact_record == owner.contact_record);
    check(separating.target.contact_record == target.contact_record);

    mco::CollisionImpactBody zero_proxy_owner{}, zero_proxy_target{};
    zero_proxy_owner.address = 0x3000;
    zero_proxy_owner.linear_velocity = {1,0,0};
    zero_proxy_owner.mass = 1000;
    zero_proxy_owner.inertia = {1.0/1000.0,{1,1,1},identity,identity};
    zero_proxy_target.address = 0x4000;
    zero_proxy_target.position = {.1f,0,0};
    zero_proxy_target.mass = 25;
    zero_proxy_target.inertia = {1.0/25.0,
        {1.0/75.0,std::numeric_limits<double>::infinity(),1.0/75.0},
        identity,identity};
    const auto singular = mco::resolve_pair_impulse(
        zero_proxy_owner, zero_proxy_target, {.1f,0,0}, {-1,0,0}, .8f, .7f);
    check(singular.collided && singular.samples == 32);
    check(singular.owner.linear_velocity == std::array<float,3>{1,0,0});
    check(std::isnan(singular.owner.angular_turn_velocity[0]) &&
          std::isnan(singular.owner.angular_turn_velocity[1]) &&
          std::isnan(singular.owner.angular_turn_velocity[2]));
}
