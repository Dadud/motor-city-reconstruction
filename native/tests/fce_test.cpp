#include "mco/fce.hpp"
#include <bit>
#include <iostream>
#include <limits>
#include <stdexcept>
namespace {
void require(bool value) {
  if (!value)
    throw std::runtime_error("FCE test failed");
}
void put(std::vector<std::uint8_t> &b, size_t o, std::uint32_t n) {
  for (size_t i = 0; i < 4; ++i)
    b[o + i] = std::uint8_t(n >> (8 * i));
}
void real(std::vector<std::uint8_t> &b, size_t o, float n) {
  put(b, o, std::bit_cast<std::uint32_t>(n));
}
void rejects(const std::vector<std::uint8_t> &b) {
  bool rejected = false;
  try {
    (void)mco::decode_fce(b);
  } catch (const std::runtime_error &) {
    rejected = true;
  }
  require(rejected);
}
} // namespace
int main() {
  constexpr size_t h = 0x2038;
  std::vector<std::uint8_t> b(h + 72 + 56);
  put(b, 0, 0x101014);
  put(b, 8, 1);
  put(b, 12, 3);
  put(b, 0x18, 36);
  put(b, 0x1c, 72);
  put(b, 0x11c, 1);
  put(b, 0x520, 3);
  put(b, 0x720, 1);
  b[0xe28] = 'A';
  real(b, 0x120, 2);
  real(b, h + 12, 1);
  real(b, h + 28, 1);
  for (size_t i = 0; i < 3; ++i)
    real(b, h + 36 + i * 12 + 8, 1);
  put(b, h + 72 + 8, 1);
  put(b, h + 72 + 12, 2);
  auto m = mco::decode_fce(b);
  require(m.parts.size() == 1 && m.parts[0].name == "A" &&
          m.parts[0].vertices.size() == 3 && m.parts[0].triangles.size() == 1);
  require(m.parts[0].origin[0] == 2 && m.parts[0].vertices[1][0] == 1 &&
          m.parts[0].vertices[2][1] == 1);
  auto broken = b;
  broken.resize(h - 1);
  rejects(broken);
  broken = b;
  put(broken, 0, 7);
  rejects(broken);
  broken = b;
  put(broken, 0x1c, 40);
  rejects(broken);
  broken = b;
  put(broken, 0x14, 0xfffffff0);
  put(broken, 12, 0);
  put(broken, 0x520, 0);
  rejects(broken); // A wrapped offset must fail even for an empty table.
  broken = b;
  put(broken, h + 72 + 4, 3);
  rejects(broken);
  broken = b;
  real(broken, h, std::numeric_limits<float>::infinity());
  rejects(broken);
  broken = b;
  put(broken, 0x520, 4);
  rejects(broken);
  broken = b;
  for (size_t i = 0; i < 64; ++i)
    broken[0xe28 + i] = 'x';
  rejects(broken);
  broken = b;
  put(broken, 12, 1000001);
  rejects(broken);
  broken = b;
  real(broken, h + 36, std::numeric_limits<float>::quiet_NaN());
  auto repaired = mco::decode_fce(broken);
  require(repaired.warnings.size() == 1 &&
          repaired.parts[0].normals[0][2] == 1);
  broken = b;
  put(broken, 0x11c, 2);
  put(broken, 0x524, 3);
  put(broken, 0x724, 1);
  rejects(broken);
  std::cout << "bounded FCE geometry tests passed\n";
}
