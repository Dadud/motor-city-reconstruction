#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/record_machine.hpp"
namespace mco {
// Original 0x436230; Mark the current record active and call its optional handler.
void record_activate(RecordMachine &machine);
}
