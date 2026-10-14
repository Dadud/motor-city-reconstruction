#include "mco/fce.hpp"
#include "mco/viv.hpp"
#include <algorithm>
#include <bit>
#include <cctype>
#include <cmath>
#include <fstream>
#include <stdexcept>
namespace mco {
namespace {
constexpr size_t header = 0x2038;
using Range = std::pair<size_t, size_t>;
void disjoint(std::vector<Range> ranges) {
  std::sort(ranges.begin(), ranges.end());
  for (size_t i = 1; i < ranges.size(); ++i)
    if (ranges[i].first < ranges[i - 1].second)
      throw std::runtime_error("overlapping FCE tables or parts");
}
std::string lower(std::string s) {
  for (char &c : s)
    if (c >= 'A' && c <= 'Z')
      c = char(c - 'A' + 'a');
  return s;
}
} // namespace
FceModel decode_fce(std::span<const std::uint8_t> b) {
  if (b.size() < header)
    throw std::runtime_error("FCE header truncated");
  auto u = [&](size_t o) -> std::uint32_t {
    if (o > b.size() || b.size() - o < 4)
      throw std::runtime_error("FCE read outside file");
    return std::uint32_t(b[o]) | (std::uint32_t(b[o + 1]) << 8) |
           (std::uint32_t(b[o + 2]) << 16) | (std::uint32_t(b[o + 3]) << 24);
  };
  auto f = [&](size_t o, bool finite = true) {
    float v = std::bit_cast<float>(u(o));
    if (finite && !std::isfinite(v))
      throw std::runtime_error("non-finite FCE geometry");
    return v;
  };
  auto v3 = [&](size_t o, bool finite = true) {
    return Vec3{f(o, finite), f(o + 4, finite), f(o + 8, finite)};
  };
  FceModel result{u(0), {}, {}};
  if (result.version != 0x101014 && result.version != 0x101015)
    throw std::runtime_error("unsupported FCE version");
  const size_t nt = u(8), nv = u(12), np = u(0x11c);
  if (np < 1 || np > 64)
    throw std::runtime_error("invalid FCE part count");
  if (nv > 1000000 || nt > 2000000)
    throw std::runtime_error("FCE geometry budget exceeded");
  auto table_offset = [&](size_t field) {
    const size_t relative = u(field);
    // Check before adding: size_t may be 32 bits in a Windows build.
    if (relative > b.size() - header)
      throw std::runtime_error("FCE table offset extends past EOF");
    return header + relative;
  };
  std::array<size_t, 3> offsets{table_offset(0x14), table_offset(0x18),
                              table_offset(0x1c)};
  std::array<size_t, 3> counts{nv, nv, nt}, strides{12, 12, 56};
  std::vector<Range> tables, vr, tr;
  for (size_t i = 0; i < 3; ++i) {
    if (offsets[i] > b.size() ||
        counts[i] > (b.size() - offsets[i]) / strides[i])
      throw std::runtime_error("FCE table extends past EOF");
    if (counts[i])
      tables.emplace_back(offsets[i], offsets[i] + counts[i] * strides[i]);
  }
  disjoint(tables);
  for (size_t p = 0; p < np; ++p) {
    const size_t firstv = u(0x420 + 4 * p), nvp = u(0x520 + 4 * p),
                 firstt = u(0x620 + 4 * p), ntp = u(0x720 + 4 * p);
    if (firstv > nv || nvp > nv - firstv || firstt > nt || ntp > nt - firstt)
      throw std::runtime_error("FCE part outside global table");
    if (nvp)
      vr.emplace_back(firstv, firstv + nvp);
    if (ntp)
      tr.emplace_back(firstt, firstt + ntp);
    FcePart part;
    part.origin = v3(0x120 + 12 * p);
    size_t name = 0xe28 + 64 * p, end = name;
    while (end < name + 64 && b[end])
      ++end;
    if (end == name + 64)
      throw std::runtime_error("unterminated FCE part name");
    for (size_t i = name; i < end; ++i) {
      auto c = b[i];
      if (c < 128)
        part.name += char(c);
      else {
        part.name += char(0xc0 | (c >> 6));
        part.name += char(0x80 | (c & 63));
      }
    }
    for (size_t i = 0; i < nvp; ++i) {
      part.vertices.push_back(v3(offsets[0] + 12 * (firstv + i)));
      part.normals.push_back(v3(offsets[1] + 12 * (firstv + i), false));
    }
    for (size_t i = 0; i < ntp; ++i) {
      size_t o = offsets[2] + 56 * (firstt + i);
      FceTriangle t{{u(o + 4), u(o + 8), u(o + 12)}, {}, u(o), u(o + 28)};
      for (auto index : t.indices)
        if (index >= nvp)
          throw std::runtime_error("FCE triangle index outside part");
      for (size_t j = 0; j < 6; ++j)
        t.uv[j] = f(o + 32 + 4 * j);
      part.triangles.push_back(t);
    }
    std::vector<Vec3> sums(nvp, Vec3{});
    size_t repaired = 0;
    for (auto &n : part.normals)
      if (!std::isfinite(n[0]) || !std::isfinite(n[1]) || !std::isfinite(n[2]))
        ++repaired;
    if (repaired) {
      for (auto &t : part.triangles) {
        auto a = part.vertices[t.indices[0]], bb = part.vertices[t.indices[1]],
             c = part.vertices[t.indices[2]];
        Vec3 x, y;
        for (size_t j = 0; j < 3; ++j) {
          x[j] = bb[j] - a[j];
          y[j] = c[j] - a[j];
        }
        Vec3 n{x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2],
               x[0] * y[1] - x[1] * y[0]};
        for (auto index : t.indices)
          for (size_t j = 0; j < 3; ++j)
            sums[index][j] += n[j];
      }
      for (size_t i = 0; i < nvp; ++i) {
        auto &n = part.normals[i];
        if (!std::isfinite(n[0]) || !std::isfinite(n[1]) ||
            !std::isfinite(n[2])) {
          auto s = sums[i];
          double length = std::hypot(double(s[0]), double(s[1]), double(s[2]));
          n = length && std::isfinite(length)
                  ? Vec3{float(s[0] / length), float(s[1] / length),
                         float(s[2] / length)}
                  : Vec3{0, 1, 0};
        }
      }
      result.warnings.push_back(part.name + ": rebuilt " +
                                std::to_string(repaired) +
                                " non-finite normals");
    }
    result.parts.push_back(std::move(part));
  }
  disjoint(vr);
  disjoint(tr);
  return result;
}
FceModel load_vehicle(const std::filesystem::path &root,
                      const std::filesystem::path &model) {
  namespace fs = std::filesystem;
  auto base = fs::canonical(root);
  if (model.empty() || model.is_absolute() || model.has_root_name())
    throw std::runtime_error("model must be a relative path inside data root");
  auto path = base;
  for (const auto &component : model) {
    if (component == "." || component == "..")
      throw std::runtime_error("model path traversal rejected");
    auto wanted = lower(component.string());
    fs::path found;
    for (auto &e : fs::directory_iterator(path))
      if (lower(e.path().filename().string()) == wanted) {
        if (!found.empty())
          throw std::runtime_error("case-ambiguous asset path");
        found = e.path();
      }
    if (found.empty())
      throw std::runtime_error("model path not found: " + model.string());
    path = fs::canonical(found);
    auto rel = path.lexically_relative(base);
    if (rel.empty() || *rel.begin() == "..")
      throw std::runtime_error("asset symlink leaves data root");
  }
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file)
    throw std::runtime_error("cannot read model");
  auto size = file.tellg();
  if (size < 0 || size > 256 * 1024 * 1024)
    throw std::runtime_error("archive read budget exceeded");
  std::vector<std::uint8_t> bytes(static_cast<size_t>(size));
  file.seekg(0);
  if (!file.read(reinterpret_cast<char *>(bytes.data()), size))
    throw std::runtime_error("truncated archive read");
  auto entries = parse_viv_directory(bytes);
  const VivEntry *found = nullptr;
  for (auto &e : entries)
    if (lower(e.name) == "part.fce") {
      if (found)
        throw std::runtime_error("case-ambiguous part.fce");
      found = &e;
    }
  if (!found)
    throw std::runtime_error("archive has no part.fce");
  if (found->size > 64 * 1024 * 1024)
    throw std::runtime_error("FCE member budget exceeded");
  return decode_fce(std::span(bytes).subspan(found->offset, found->size));
}
} // namespace mco
