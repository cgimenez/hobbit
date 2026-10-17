// Driver replay : lit des commandes (stdin, 1/ligne), joue, imprime transcript.
// Usage: brute <cmds.txt   (chaque tour separe par "@@@TURN@@@" sur stdout)
#include "emu.h"
#include <cstdio>
#include <iostream>
#include <string>

extern uint16_t ringbuf[64]; extern int ringidx;

int main(int argc, char** argv){
    const char* root = (argc>1)?argv[1]:".";
    std::string bin = (argc>2)?argv[2]:(std::string(root)+"/data/hobbit.bin");
    std::string rom = std::string(root)+"/data/basic10.rom";
    Emu e;
    if(!e.load(bin.c_str(),rom.c_str())){ fprintf(stderr,"load: %s\n",e.err.c_str()); return 1; }
    const uint64_t CAP = 400000000ULL;
    std::string line;
    // boot -> premiere suspension (= vrai prompt)
    if(getenv("DUMPINIT")){
        FILE* f=fopen("/tmp/emu_init.bin","wb"); fwrite(e.mem,1,65536,f); fclose(f);
    }
    if(e.run_until_suspend(CAP)!=Emu::NEED_INPUT){ fprintf(stderr,"boot? %s\n",e.err.c_str()); return 1; }
    printf("%s@@@TURN@@@\n", e.out.c_str()); e.out.clear();
    while(std::getline(std::cin,line)){
        if(!line.empty()&&line.back()=='\r') line.pop_back();
        if(line.rfind("@RAW ",0)==0 && line.size()==6){
            e.in.push_back((uint8_t)line[5]); // octet brut sans CR (echo seul)
            if(e.run_until_suspend(CAP)!=Emu::NEED_INPUT){ printf("@@@STALL@@@ %s\n", e.err.c_str()); break; }
            printf("%s@@@TURN@@@\n", e.out.c_str()); e.out.clear();
            continue;
        }
        e.feed(line);
        if(!e.play_turn(CAP)){ printf("@@@STALL@@@ %s\n", e.err.c_str());
            if(getenv("RINGDUMP")){ for(int i=0;i<64;i++) printf("RING %04X\n", ringbuf[(ringidx+i)&63]); }
            if(getenv("LOOPDUMP")){ printf("PC=%04X A=%02X X=%02X Y=%02X S=%02X P=%02X scriptPC=%02X%02X\n",
                e.PC,e.A,e.X,e.Y,e.S,e.P,e.mem[0x8D],e.mem[0x8C]);
                printf("ZP80:"); for(int i=0x80;i<0xA0;i++) printf(" %02X",e.mem[i]); printf("\n"); }
            break; }
        printf("%s@@@TURN@@@ lieu=$%02X\n", e.out.c_str(), e.mem[0x1B2A]); e.out.clear();
    }
    if(getenv("MEMDUMP")){
        char fn[64];
        const int regs[5][2]={{0x00BE,0x18},{0x1B1A,0x556},{0x28CC,0x2F1},{0x211A,0x5C8},{0x0000,0x100}};
        for(int i=0;i<5;i++){ snprintf(fn,64,"/tmp/emu_%04X.bin",regs[i][0]);
            FILE* f=fopen(fn,"wb"); fwrite(e.mem+regs[i][0],1,regs[i][1],f); fclose(f); }
    }
    fprintf(stderr,"instr: %llu\n",(unsigned long long)e.icount);
    return 0;
}
