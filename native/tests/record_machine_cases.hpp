#pragma once
#include "cell_io.hpp"
#include "mco/record_machine.hpp"
#include "mco/record_machine_initialize.hpp"
#include "mco/record_transition.hpp"
#include "mco/record_should_retain.hpp"
#include "mco/record_handler.hpp"
#include "mco/record_pair_match.hpp"
#include "mco/record_activate.hpp"
#include "mco/record_cursor_pop.hpp"
#include "mco/record_stack_contains.hpp"
#include <vector>
#include <utility>
#include <initializer_list>

namespace record_cases {
struct Fixture {
    std::array<std::byte,0x780> bytes{};
    std::uint32_t count{}, index{}, pending{};
    std::uint32_t redirect3{0xffffffffu}, redirect0{0xffffffffu}, mask{}, value{};
    std::vector<std::vector<std::uint32_t>> logs;

    static Fixture read(std::istream& input) {
        Fixture result;
        result.count = cell_io::read(input);
        result.index = cell_io::read(input);
        result.pending = cell_io::read(input);
        result.redirect3 = cell_io::read(input);
        result.redirect0 = cell_io::read(input);
        result.mask = cell_io::read(input);
        result.value = cell_io::read(input);
        result.bytes = cell_io::image<0x780>(input);
        return result;
    }
    static void callback(mco::RecordMachine& machine, std::uint32_t handler,
                         std::uint32_t event, void* user) {
        auto& fixture = *static_cast<Fixture*>(user);
        std::vector<std::uint32_t> observation{handler,event,machine.selection_presets[0],
            machine.selection_index,machine.selection_slot};
        for (auto byte : machine.bytes) observation.push_back(std::to_integer<std::uint32_t>(byte));
        fixture.logs.push_back(std::move(observation));
        const auto redirect = event == 3 ? fixture.redirect3 : fixture.redirect0;
        if (redirect != 0xffffffffu) machine.store(record_machine_image::current_record, redirect);
        if (fixture.mask & 1) {
            auto record = machine.record(machine.load(record_machine_image::current_record));
            mco::detail::write_word(record, state_record::flags, fixture.value);
            mco::detail::write_word(record, state_record::parameter, fixture.value ^ event);
        }
        if (fixture.mask & 2) {
            for (unsigned k = 0; k < 3; ++k)
                machine.store(record_machine_image::inherited_word0+k*4, fixture.value+k);
        }
        if (fixture.mask & 4) {
            machine.selection_presets[0] = fixture.value;
            machine.selection_index = fixture.value ^ 0x55aa55aau;
            machine.selection_slot = fixture.value+1u;
        }
        if (fixture.mask & 8) {
            for (auto offset : {record_machine_image::rollover,record_machine_image::rollover0,
                 record_machine_image::rollover1,record_machine_image::rollover2,
                 record_machine_image::after_stack_flag,record_machine_image::state_flag,
                 record_machine_image::request_flag})
                machine.store(offset, fixture.value ^ static_cast<std::uint32_t>(offset));
        }
    }
    mco::RecordMachine machine() {
        return {bytes,{count,0,0,0},index,pending,&callback,this};
    }
    void emit(const mco::RecordMachine& machine) const {
        cell_io::emit(machine.selection_presets[0]);
        cell_io::emit(machine.selection_index);
        cell_io::emit(machine.selection_slot);
        cell_io::emit(bytes);
        cell_io::emit(static_cast<std::uint32_t>(logs.size()));
        for (const auto& log : logs) for (auto word : log) cell_io::emit(word);
    }
};

inline std::array<std::uint32_t,5> lifecycle(mco::RecordMachine& machine) {
    mco::record_machine_initialize(machine);
    auto current = machine.load(record_machine_image::current_record);
    mco::detail::write_word(machine.record(current), state_record::retain_until, 4);
    std::array<std::byte,16> request{};
    mco::detail::write_word(request, record_request::identifier, 14);
    mco::detail::write_word(request, record_request::parameter, 0x1234);
    const auto retained = mco::record_should_retain(machine.record(current), request, 5);
    if (retained) throw std::logic_error("lifecycle fixture requires expired retention");
    const auto handler = mco::record_handler(14);
    std::array<std::byte,64> pairs{};
    mco::detail::write_word(pairs, 0, 24);
    mco::detail::write_word(pairs, 4, 14);
    mco::detail::write_word(pairs, 8, 0xffffffffu);
    const auto matched = mco::record_pair_match(pairs, 24, 14);
    mco::record_transition(machine, pairs, 14, handler, 1, 0x1234);
    mco::record_activate(machine);
    current = mco::record_cursor_pop(machine.load(record_machine_image::current_record),
                                   machine.load(record_machine_image::base_record));
    machine.store(record_machine_image::current_record, current);
    const auto base = machine.load(record_machine_image::base_record);
    auto records = machine.bytes.subspan(record_machine_image::records, 6*state_record::size);
    return {retained, handler, matched,
            mco::record_stack_contains(records, base, current, 24),
            mco::record_stack_contains(records, base, current, 14)};
}
}  // namespace record_cases
