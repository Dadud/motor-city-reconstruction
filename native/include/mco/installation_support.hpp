#pragma once
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
using InstallationDriveQuery=std::uint32_t (*)(std::span<const std::byte,4>,void*);
struct InstallationDrivePlatform {InstallationDriveQuery query{};void* user{};};
bool installation_drive_is_cd(std::uint32_t index,const InstallationDrivePlatform& platform);
std::uint32_t installation_path_address(std::uint32_t index);
std::uint32_t installation_cd_mode(std::uint32_t value);
}
