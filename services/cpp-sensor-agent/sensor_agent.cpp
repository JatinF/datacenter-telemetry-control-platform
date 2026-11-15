#include <iostream>

int main() {
    std::cout
        << "{\"device_id\":\"SYN-SENS-CPP-0001\","
        << "\"metric\":\"intake_temperature_c\","
        << "\"value\":23.0,"
        << "\"unit\":\"C\","
        << "\"quality\":\"good\","
        << "\"source\":\"cpp-sensor-agent\","
        << "\"hardware\":\"not-contacted\"}"
        << std::endl;
    return 0;
}
