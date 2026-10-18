#pragma once
#include "mco/layouts.hpp"
#include "mco/detail/byte_words.hpp"
namespace mco {
struct InputConsoleState {
    const std::span<std::byte,console_input_image::size> image;
    std::uint32_t load(std::size_t offset) const {return detail::read_word(image,offset);}
    void store(std::size_t offset,std::uint32_t value){detail::write_word(image,offset,value);}
};
struct InputConsoleOpenOptions {
    const char* name;
    std::uint32_t access,share,security,creation,flags,template_handle;
};
using ConsoleLock=void (*)(InputConsoleState&,bool entering,std::uint32_t identity,void* user);
using ConsoleOpen=std::uint32_t (*)(InputConsoleState&,const InputConsoleOpenOptions&,void* user);
using ConsoleCount=std::uint32_t (*)(InputConsoleState&,std::uint32_t handle,std::uint32_t& count,void* user);
using ConsolePeek=std::uint32_t (*)(InputConsoleState&,std::uint32_t handle,std::span<std::byte> records,std::uint32_t capacity,std::uint32_t& count,void* user);
using ConsoleGetMode=std::uint32_t (*)(InputConsoleState&,std::uint32_t handle,std::uint32_t& mode,void* user);
using ConsoleSetMode=std::uint32_t (*)(InputConsoleState&,std::uint32_t handle,std::uint32_t mode,void* user);
using ConsoleRead=std::uint32_t (*)(InputConsoleState&,std::uint32_t handle,std::span<std::byte,console_event_record::size> record,std::uint32_t& count,void* user);
struct InputConsolePlatform {ConsoleLock lock{};ConsoleOpen open{};ConsoleCount count{};ConsolePeek peek{};ConsoleGetMode get_mode{};ConsoleSetMode set_mode{};ConsoleRead read{};void* user{};};
std::uint32_t input_console_available(InputConsoleState&,const InputConsolePlatform&);
std::uint32_t input_console_read_unlocked(InputConsoleState&,const InputConsolePlatform&);
std::uint32_t input_console_available_unlocked(InputConsoleState&,const InputConsolePlatform&);
std::span<const std::byte> input_console_decode(InputConsoleState&,std::span<const std::byte,console_key_record::size>);
std::uint32_t input_console_open(InputConsoleState&,const InputConsolePlatform&);
}
