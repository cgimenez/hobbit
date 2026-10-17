CXX = g++
CXXFLAGS = -O2 -std=c++17 -Wall
BRUTE = brute search

all: $(BRUTE)

brute: emu.cpp main.cpp emu.h
	$(CXX) $(CXXFLAGS) -o brute emu.cpp main.cpp

search: emu.cpp search.cpp emu.h
	$(CXX) $(CXXFLAGS) -pthread -o search emu.cpp search.cpp

clean:
	rm -f $(BRUTE)
