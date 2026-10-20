#include "mco/installation_support.hpp"
#include <array>
#include <stdexcept>
namespace mco {
// 0x533f60: sprintf("%c:\\", (index & 255) + 'A'), then DRIVE_CDROM.
bool installation_drive_is_cd(std::uint32_t index,const InstallationDrivePlatform& p) {
    if(!p.query) throw std::invalid_argument("installation drive-type query required");
    const std::array<std::byte,4> path{
        std::byte(((index & 255u)+65u)&255u),std::byte{':'},std::byte{'\\'},std::byte{}};
    return p.query(path,p.user)==5;
}
// 0x530a90 returns a word identity, not a dereferenced host pointer.
std::uint32_t installation_path_address(std::uint32_t index) {
    return 0xa52d48u + index*0x104u;
}
// 0x5354d0 returns the entire flag word rather than Boolean normalization.
std::uint32_t installation_cd_mode(std::uint32_t value) {return value;}
}
