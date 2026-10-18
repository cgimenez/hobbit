# The project

## Why?

In 1984 I discovered the book "The Hobbit" sold together with the eponymous game for the Oric Atmos.
I never managed to finish the game but I still keep today,
42 years later, an unforgettable memory of this game, absolutely avant-garde for its time.

Talking to characters? Autonomous characters?
Software capable of understanding complex sentences?
A chaotic little world in which every game was different.
None of that existed at the time, and yet they did it.

Around 2004, then in 2014, I had the chance to exchange
emails with Veronika Megler (co-developer with Philip Mitchell), in which I expressed
my gratitude for this fabulous game, the only one she ever developed, the rest of her career
being spent at IBM.

This is the original version of the Oric Atmos port (made around 1983 by Gregg Barnett), whose inner workings have been analysed
to allow real-time visualisation of the game's internal logic.

What you have here is the execution of the original code, without any modification.
The code does not run in an Oric emulator
but in the sim65 simulator from the cc65 suite, thanks to sim65's
"paravirtualization" mechanisms.

## How?

70% of the reverse engineering was done by a pair of AIs.

As finalising the documentation was relatively
laborious, I then included in the AI analysis loop the projects "Wilderland" (Valerio Messina)
and "The Hobbit ZX Spectrum disassembly" (Paul Maddern)
as complementary sources (missing variables, correlation
of locations, etc).

## Graphics

The illustrations were converted to SVG from the vector data encoded
in the game binary.

## Notes

The OFFSTAGE panel data is partially buggy.
