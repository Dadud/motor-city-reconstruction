#include "mco/entity_clear.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto target = image<0x124>(input);
        mco::entity_clear(target);
        emit(target);
    });
}
