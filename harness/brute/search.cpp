// search: BFS/exhaustion depuis snapshot dale. 1 orchestrateur + N workers.
// Usage: search <prefix.txt> <candidats.txt> [workers]
// candidats.txt : 1 suffixe/ligne, commandes separees par '|'
// Verdicts: WIN / HALLS / DRAGON / GATE / LOC:<lieu> / DEAD / STALL / SAME / ERR
#include "emu.h"
#include <atomic>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

static std::string clean(const std::string& s){
    std::string o; o.reserve(s.size());
    for(char c:s) if(c!='+') o.push_back(c);
    return o;
}
static bool has(const std::string& t, const char* w){
    return t.find(w)!=std::string::npos;
}
// extrait les lignes "You are ..." (lieux visites pendant le suffixe)
static std::string locs(const std::string& t){
    std::string o; size_t p=0;
    while((p=t.find("You are",p))!=std::string::npos){
        size_t e=t.find('\n',p); if(e==std::string::npos) e=t.size();
        std::string l=t.substr(p,e-p);
        if(o.find(l)==std::string::npos){ if(!o.empty())o+=" // "; o+=l; }
        p=e;
    }
    return o;
}

struct Trial { int idx; std::vector<std::string> cmds; };
struct Result { int idx; std::string verdict; std::string detail; };

static std::vector<uint8_t> SNAP;
static std::vector<Trial> TRIALS;
static std::vector<Result> RESULTS;
static std::atomic<size_t> NEXT{0};
static std::mutex IOM;
#define LOG(...) do{ std::lock_guard<std::mutex> _l(IOM); printf(__VA_ARGS__); fflush(stdout);}while(0)

static Emu BASE; // image chargee une fois, copiee par thread (memcpy 64Ko)

static std::string classify(const std::string& txt){
    std::string t=clean(txt);
    if(has(t,"cheering crowd of dwarves")) return "WIN";
    if(has(t,"dragon is dead")) return "DRAGON";
    if(has(t,"where the dragon sleeps")||has(t,"sleeping dragon")||has(t,"the dragon sleeps")) return "HALLS";
    if(has(t,"Front Gate")||has(t,"front gate")) return "GATE";
    if(has(t,"has killed you")||has(t,"kills you")||has(t,"eats you")||has(t,"you are dead")||has(t,"You are dead")) return "DEAD";
    return "";
}

static void worker(int id){
    Emu e = BASE; // copie image (memcpy)
    e.restore(SNAP);
    const uint64_t CAP=150000000ULL;
    for(;;){
        size_t i=NEXT.fetch_add(1);
        if(i>=TRIALS.size()) break;
        const Trial& t=TRIALS[i];
        e.restore(SNAP);
        std::string txt; bool bad=false; std::string why;
        for(auto& c:t.cmds){
            e.feed(c);
            if(!e.play_turn(CAP)){ bad=true; why = e.stall?"STALL":"ERR:"+e.err; break; }
            txt+=e.out; e.out.clear();
        }
        std::string v = bad?why:classify(txt);
        std::string det;
        if(v.empty()){
            std::string l=locs(clean(txt));
            if(l.empty()){ v="SAME"; }
            else { v="LOC"; det=l.substr(0,160); }
        } else if(v=="GATE"||v=="HALLS"||v=="DRAGON"||v=="WIN"){
            det=locs(clean(txt)).substr(0,160);
        }
        {
            std::lock_guard<std::mutex> _l(IOM);
            RESULTS.push_back({t.idx,v,det});
            std::string s; for(auto& c:t.cmds){ if(!s.empty())s+=" | "; s+=c; }
            printf("#%d [%s] %s %s\n", t.idx, v.c_str(), s.c_str(), det.c_str());
            fflush(stdout);
        }
    }
}

static std::vector<std::string> split(const std::string& s, char d){
    std::vector<std::string> o; std::string c;
    for(char x:s){ if(x==d){ o.push_back(c); c.clear(); } else c.push_back(x); }
    if(!c.empty()) o.push_back(c);
    return o;
}

int main(int argc, char** argv){
    if(argc<3){ fprintf(stderr,"usage: search <prefix.txt> <candidats.txt> [workers]\n"); return 1; }
    int NW = argc>3?atoi(argv[3]):11;
    const char* img = argc>4?argv[4]:"data/hobbit.bin";
    if(!BASE.load(img,"data/basic10.rom")){ fprintf(stderr,"load: %s\n",BASE.err.c_str()); return 1; }
    // rejoue prefixe -> snapshot dale
    std::ifstream pf(argv[1]); std::string line;
    if(BASE.run_until_suspend(400000000ULL)!=Emu::NEED_INPUT){ fprintf(stderr,"boot?\n"); return 1; }
    while(std::getline(pf,line)){
        if(!line.empty()&&line.back()=='\r') line.pop_back();
        if(line.empty()) continue;
        BASE.feed(line);
        if(!BASE.play_turn(400000000ULL)){ fprintf(stderr,"prefix stall @ %s\n",line.c_str()); return 1; }
        BASE.out.clear();
    }
    BASE.snapshot(SNAP);
    fprintf(stderr,"snapshot dale: %llu instr\n",(unsigned long long)BASE.icount);
    // candidats
    std::ifstream cf(argv[2]); int idx=0;
    while(std::getline(cf,line)){
        if(!line.empty()&&line.back()=='\r') line.pop_back();
        if(line.empty()) continue;
        TRIALS.push_back({idx++,split(line,'|')});
    }
    fprintf(stderr,"%zu trials, %d workers\n",TRIALS.size(),NW);
    std::vector<std::thread> th;
    for(int i=0;i<NW;i++) th.emplace_back(worker,i);
    for(auto& t:th) t.join();
    int nw=0,nh=0,nd=0,ng=0,nl=0,ns=0,nst=0,ne=0;
    for(auto& x:RESULTS){
        if(x.verdict=="WIN")nw++; else if(x.verdict=="HALLS")nh++;
        else if(x.verdict=="DRAGON")nd++; else if(x.verdict=="GATE")ng++;
        else if(x.verdict=="LOC")nl++; else if(x.verdict=="SAME")ns++;
        else if(x.verdict=="STALL")nst++; else ne++;
    }
    fprintf(stderr,"RESUME: WIN=%d HALLS=%d DRAGON=%d GATE=%d LOC=%d SAME=%d STALL=%d ERR=%d\n",nw,nh,nd,ng,nl,ns,nst,ne);
    return 0;
}
