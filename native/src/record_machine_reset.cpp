#include "mco/record_machine_reset.hpp"
#include <bit>
#include <stdexcept>
#include "mco/detail/byte_words.hpp"
#include "mco/layouts.hpp"
#include "mco/record_machine_initialize.hpp"

namespace mco {
void record_machine_reset(RecordMachine& machine) {
    record_machine_initialize(machine);
}
}
