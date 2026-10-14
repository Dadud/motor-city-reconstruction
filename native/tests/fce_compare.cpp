#include "mco/fce.hpp"
#include <iomanip>
#include <iostream>
int main(int argc, char **argv) {
  try {
    if (argc != 3)
      return 2;
    auto m = mco::load_vehicle(argv[1], argv[2]);
    std::cout << std::setprecision(9) << m.version << ' ' << m.parts.size()
              << '\n';
    for (auto &p : m.parts) {
      std::cout << p.name << ' ' << p.vertices.size() << ' '
                << p.triangles.size();
      for (float x : p.origin)
        std::cout << ' ' << x;
      std::cout << '\n';
      for (auto &v : p.vertices) {
        for (float x : v)
          std::cout << x << ' ';
        std::cout << '\n';
      }
    }
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
