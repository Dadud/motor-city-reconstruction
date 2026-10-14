#include "mco/room_join_request.hpp"

#include <algorithm>
#include <iostream>
#include <stdexcept>

int main() {
    int failures = 0;
    const auto check = [&](bool condition) { if (!condition) ++failures; };
    const auto rejects = [&](const auto& action) {
        try { action(); ++failures; } catch (const std::invalid_argument&) {}
    };
    mco::RoomJoinInputs inputs{44,0x42,0x12345678,{'L','O','B','B','Y'},16,{}};
    for (std::size_t i = 0; i < 256; ++i) inputs.opaque_data[i] = static_cast<std::uint8_t>(i);
    const auto empty = mco::build_room_join_argument(inputs);
    check(empty[0] == 44 && empty[4] == 0x42 && empty[0xc] == 2);
    check(empty[8] == 0x78 && empty[11] == 0x12 && empty[0x150] == 16 && empty[0x152] == 2);
    check(std::equal(inputs.opaque_data.begin(),inputs.opaque_data.end(),empty.begin() + 0x50));
    check(std::all_of(empty.begin() + 0x154,empty.end(),[](auto value) { return value == 0; }));
    inputs.name.assign(31,'n');
    std::array<std::uint8_t,16> password;
    password.fill('p');
    const auto waiting = mco::build_room_join_argument(inputs,password,true,true,0x71000000);
    check(waiting[0xc] == 0x21 && waiting[0x152] == 1);
    check(waiting[0x2e] == 'n' && waiting[0x2f] == 0 && waiting[0x43] == 'p' && waiting[0x44] == 0);
    check(waiting[0x154] == 0x40 && waiting[0x155] == 0xd7 && waiting[0x156] == 0x44);
    check(waiting[0x158] == 0 && waiting[0x15b] == 0x71);
    rejects([&] { (void)mco::build_room_join_argument(inputs,{},false,true); });
    rejects([&] { (void)mco::build_room_join_argument(inputs,{},false,false,1); });
    inputs.name.push_back('n');
    rejects([&] { (void)mco::build_room_join_argument(inputs); });
    inputs.name = {'a',0,'b'};
    rejects([&] { (void)mco::build_room_join_argument(inputs); });
    inputs.name.clear();
    rejects([&] { (void)mco::build_room_join_argument(inputs,std::vector<std::uint8_t>(17,'p')); });
    rejects([&] { (void)mco::build_room_join_argument(inputs,std::array<std::uint8_t,1>{0}); });
    std::vector<std::uint8_t> source(0x3b8,0xa5);
    std::fill(source.begin() + 0xa0,source.begin() + 0xc0,0);
    source[0xa0] = 'r'; source[0xa1] = 0;
    source[0x39c] = 44; source[0x39d] = source[0x39e] = source[0x39f] = 0;
    const auto extracted = mco::room_join_inputs_from_image(source);
    check(extracted.server_selector == 44 && extracted.name == std::vector<std::uint8_t>{'r'});
    check(extracted.channel_id == 0xa5a5a5a5 && extracted.protocol == 0xa5a5a5a5 && extracted.max_ready == 0xa5a5);
    std::fill(source.begin() + 0xa0,source.begin() + 0xc0,'x');
    rejects([&] { (void)mco::room_join_inputs_from_image(source); });
    for (auto size : {std::size_t{0},std::size_t{0x39f},std::size_t{65537}})
        rejects([&] { (void)mco::room_join_inputs_from_image(std::vector<std::uint8_t>(size)); });
    if (failures) std::cerr << failures << " room request checks failed\n";
    return failures ? 1 : 0;
}
