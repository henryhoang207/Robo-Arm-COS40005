#include "../../robo-arm/sketch/controller.h"
#include <iostream>
#include <sstream>
#include <string>
// Test transport only: real C++ controller, simulated time, no Arduino hardware.
int main() {
  Controller core;
  std::string line;
  while(std::getline(std::cin,line)) {
    std::istringstream in(line); uint32_t now; in>>now;
    std::vector<int32_t> packet; int32_t value;
    while(in>>value) packet.push_back(value);
    auto response=core.dispatch(packet,now);
    for(auto item:response) std::cout<<item<<' ';
    std::cout<<std::endl;
  }
}
