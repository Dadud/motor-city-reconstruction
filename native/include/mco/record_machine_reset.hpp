#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/record_machine.hpp"
namespace mco {
// Original 0x434ef0; Initialize six record slots and the original callback/reset ordering.
void record_machine_reset(RecordMachine &machine);
}
