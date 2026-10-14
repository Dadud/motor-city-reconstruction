#pragma once
#include <cstdint>
namespace mco {
// Bounded 0x541930 shaping; control producer and wheel geometry are external.
float steering_response(std::int32_t raw_control, double speed);
}
