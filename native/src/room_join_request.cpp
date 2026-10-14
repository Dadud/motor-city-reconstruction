#include "mco/room_join_request.hpp"

#include <algorithm>
#include <stdexcept>

namespace mco {
namespace {
std::uint32_t read_little(std::span<const std::uint8_t> image, std::size_t offset,
                          std::size_t width) {
    std::uint32_t value = 0;
    for (std::size_t index = 0; index < width; ++index)
        value |= static_cast<std::uint32_t>(image[offset + index]) << (8 * index);
    return value;
}
void put(std::span<std::uint8_t> output,std::size_t offset,std::size_t width,std::uint32_t value) {
    for (std::size_t index = 0; index < width; ++index)
        output[offset + index] = static_cast<std::uint8_t>(value >> (8 * index));
}
bool has_nul(std::span<const std::uint8_t> value) {
    return std::find(value.begin(),value.end(),0) != value.end();
}
} // namespace

RoomJoinInputs room_join_inputs_from_image(std::span<const std::uint8_t> image) {
    if (image.size() < 0x3a0 || image.size() > 65536)
        throw std::invalid_argument("expected bounded room image covering offset 0x39f");
    const auto name = image.subspan(0xa0,32);
    const auto end = std::find(name.begin(),name.end(),0);
    if (end == name.end())
        throw std::invalid_argument("room image name requires NUL within its 32-byte field");
    RoomJoinInputs inputs{read_little(image,0x39c,4),read_little(image,0xcc,4),
        read_little(image,0xc0,4),{name.begin(),end},
        static_cast<std::uint16_t>(read_little(image,0xe6,2)),{}};
    std::copy_n(image.begin() + 0xf4,256,inputs.opaque_data.begin());
    return inputs;
}

std::array<std::uint8_t,channel_argument_size> build_room_join_argument(
    const RoomJoinInputs& inputs,std::span<const std::uint8_t> password,
    bool flag_0x20,bool wait_for_completion,std::optional<std::uint32_t> owner_token) {
    if (inputs.name.size() > 31 || has_nul(inputs.name))
        throw std::invalid_argument("room name must contain at most 31 bytes without NUL");
    if (password.size() > 16 || has_nul(password))
        throw std::invalid_argument("password must contain at most 16 bytes without NUL");
    if (wait_for_completion != owner_token.has_value())
        throw std::invalid_argument("explicit owner token is required only for waiting branch");
    std::array<std::uint8_t,channel_argument_size> output{};
    const std::uint32_t mode = password.empty() ? 2 : 1;
    put(output,0,4,inputs.server_selector);
    put(output,4,4,inputs.protocol);
    put(output,8,4,inputs.channel_id);
    put(output,0xc,4,mode | (flag_0x20 ? 0x20 : 0));
    std::copy(inputs.name.begin(),inputs.name.end(),output.begin() + 0x10);
    std::copy(password.begin(),password.end(),output.begin() + 0x34);
    std::copy(inputs.opaque_data.begin(),inputs.opaque_data.end(),output.begin() + 0x50);
    put(output,0x150,2,inputs.max_ready);
    put(output,0x152,2,mode);
    if (wait_for_completion) {
        put(output,0x154,4,0x44d740);
        put(output,0x158,4,*owner_token);
    }
    return output;
}

} // namespace mco
