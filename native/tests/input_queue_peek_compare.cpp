#include "mco/input_queue_peek.hpp"
#include "input_consumer_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        input_consumer_cases::compare(input,false);
    });
}
