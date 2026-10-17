// Hobbit brute-force emulator: 6502 + paravirt shims natifs.
// Semantique entree = interactive (Session) : file d'octets, les polls
// hors-prompt ne consomment jamais, le prompt suspend si file vide.
#pragma once
#include <cstdint>
#include <deque>
#include <string>
#include <vector>

struct Emu {
    uint8_t A=0,X=0,Y=0,S=0xFF,P=0x24;
    uint16_t PC=0x2C00;
    uint8_t mem[65536];
    // entree clavier (machine press/release du shim)
    std::deque<uint8_t> in;
    bool kbst=false;            // KBSTATE
    // capture ASCII (hooks L75B8/L7694/L7514)
    std::string out;
    bool prompt_seen=false;     // '>' vu depuis le dernier feed
    bool last_eolr=false;
    uint64_t icount=0;
    bool stall=false;
    std::string err;

    enum Run { NEED_INPUT, AT_PROMPT, CAP };
    bool load(const char* binpath, const char* rompath);
    void feed(const std::string& line);   // ajoute octets + CR, reset prompt_seen
    Run run_until_suspend(uint64_t cap);  // tourne jusqu'a suspension clavier (vrai prompt) ou cap
    // joue un tour complet (apres feed) : suspends jusqu'a '>' vu, CR
    // sacrificiels si suspend sans '>' (MORE). true = tour complet.
    bool play_turn(uint64_t cap_per);
    void snapshot(std::vector<uint8_t>& s) const;
    void restore(const std::vector<uint8_t>& s);
    bool step();  // false = erreur (err renseigne)
};
