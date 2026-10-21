#include "mco/world_object_damping.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using mco::WorldObjectMotion;
    auto result = mco::update_world_object_motion({1, {0.1f,-0.2f,0.3f}, {1.0f,-2.0f,3.0f}});
    assert(result.linear_velocity[0] == 0.1f && result.linear_velocity[1] == -0.2f);
    assert(result.angular_velocity[0] == 1.0f*0.9f && result.angular_velocity[1] == -2.0f*0.9f && result.angular_velocity[2] == 3.0f*0.9f);
    result = mco::update_world_object_motion({0, {0.49f,-0.5f,0.6f}, {0.2f,0.08f,-0.1f}});
    assert(result.linear_velocity[0] == 0.0f && result.linear_velocity[1] == -0.5f);
    assert(result.angular_velocity[0] == 0.2f && result.angular_velocity[1] == 0.08f);
    for (const auto angles : {std::array<float,3>{0.049f,0.4f,0.4f},
                              std::array<float,3>{0.4f,0.049f,0.4f},
                              std::array<float,3>{0.4f,0.4f,0.049f}}) {
        result = mco::update_world_object_motion({0, {1,2,3}, angles});
        assert(result.angular_velocity[1] == 0.0f);
    }
    result = mco::update_world_object_motion({0, {0.5f,0,0}, {0.05f,0.05f,0.05f}});
    assert(result.linear_velocity[0] == 0.5f && result.angular_velocity[0] == 0.05f && result.angular_velocity[1] == 0.05f);
}
