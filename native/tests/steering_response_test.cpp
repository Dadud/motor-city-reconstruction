#include "mco/steering_response.hpp"
#include <limits>
#include <stdexcept>
namespace {
void check(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
}
int main() {
    check(mco::steering_response(0, 100) == 0, "zero steering failed");
    const float low = mco::steering_response(64, 0), high = mco::steering_response(64, 100);
    check(low > high && high > 0, "speed blend did not shape partial steering");
    check(mco::steering_response(-64, 100) == -high, "signed steering failed");
    check(mco::steering_response(64, -100) == high, "reverse speed blend differs");
    check(mco::steering_response(std::numeric_limits<std::int32_t>::min(), 10) == -1,
          "minimum signed control failed");
    check(mco::steering_response(std::numeric_limits<std::int32_t>::max(), 10) == 1,
          "maximum signed control failed");
    bool rejected = false;
    try { mco::steering_response(0, std::numeric_limits<double>::infinity()); }
    catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid speed accepted at zero steering");
}
