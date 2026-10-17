// 6502 complet (opcodes officiels + BCD) + interceptions paravirt Hobbit.
#include "emu.h"
#include <cstdio>
#include <cstring>

// Flags 6502
enum { FC=1, FZ=2, FI=4, FD=8, FB=16, FV=64, FN=128 };

uint16_t ringbuf[64]; int ringidx=0;   // ring d'execution (diag stall)

static inline void setZN(Emu& e, uint8_t v){ e.P=(e.P&~(FZ|FN))|(!v?FZ:0)|(v&FN); }

bool Emu::load(const char* binpath, const char* rompath) {
    FILE* f=fopen(binpath,"rb"); if(!f){err="bin?";return false;}
    fseek(f,0,SEEK_END); long n=ftell(f); fseek(f,0,SEEK_SET);
    std::vector<uint8_t> img(n); if(fread(img.data(),1,n,f)!=(size_t)n){fclose(f);err="read";return false;}
    fclose(f);
    memset(mem,0xFF,sizeof mem);   // sim65 remplit la RAM de $FF
    uint32_t BASE=0x0400; uint8_t* body=img.data(); long blen=n;
    if(n>12 && !memcmp(img.data(),"sim65",5)){
        BASE=img[8]|(img[9]<<8);   // image .sim : header 12 o
        body=img.data()+12; blen=n-12;
        if(BASE+blen>65536){err="sim trop gros";return false;}
    }
    memcpy(mem+BASE,body,blen);
    bool is_sim = (n>12 && !memcmp(img.data(),"sim65",5));
    if(!is_sim){
    // zero-fill comme sim_pack : BSS ($91B2-$C000), zone shim, $C760-$F700
    memset(mem+BASE+blen,0,0xC000-(BASE+blen));
    memset(mem+0xC000,0,0x02F0);
    memset(mem+0xC300,0xFF,0x0460);       // miroir texte shim ($FF)
    memset(mem+0xC760,0,0xF700-0xC760);
    memset(mem+0xF700,0,0xFC70-0xF700);
    // curseurs cassette RD/WR := $E804 (sim_pack, mode non-snapshot)
    mem[0xE800]=0x04; mem[0xE801]=0xE8; mem[0xE802]=0x04; mem[0xE803]=0xE8;
    // patch --fast : $2C4A 01 -> 00 ($56=0, sans images)
    if(mem[0x2C4A]!=0x01){err="patch fast refuse";return false;}
    mem[0x2C4A]=0x00;
    // patch pause solver : $7628 `JSR $7353` -> `LDA #$00 ; NOP`
    if(!(mem[0x7628]==0x20&&mem[0x7629]==0x53&&mem[0x762A]==0x73)){err="patch pause refuse";return false;}
    mem[0x7628]=0xA9; mem[0x7629]=0x00; mem[0x762A]=0xEA;
    }
    // verifie read_key (lecteur de ligne : `JSR vec_11` en $406D)
    if(!(mem[0x406D]==0x20&&mem[0x406E]==0x26&&mem[0x406F]==0x2C)){err="read_key introuvable";return false;}
    // verifie le shim clavier ($7353 = JMP $C000, pose par sim_pack)
    if(!(mem[0x7353]==0x4C&&mem[0x7354]==0x00&&mem[0x7355]==0xC0)){err="shim kb absent ($7353)";return false;}
    if(!is_sim){
    FILE* r=fopen(rompath,"rb");
    if(r){ fseek(r,0,SEEK_END); long rn=ftell(r); fseek(r,0,SEEK_SET);
        std::vector<uint8_t> rom(rn); fread(rom.data(),1,rn,r); fclose(r);
        // basic10.rom = image $C000-$FFFF ?
        if(rn>=0x4000) memcpy(mem+0xFC70,rom.data()+(0xFC70-0xC000),0xFFC0-0xFC70);
    }
    }
    A=0;X=0;Y=0;S=0x00;P=0x24;PC=0x2C00; // S=$00 comme sim65 (mesure) : le 1er JSR
    // (boot_copy) pousse en $0100, residu lu par le RNG (noise=$0100)
    in.clear();kbst=false;out.clear();prompt_seen=false;last_eolr=false;icount=0;stall=false;
    return true;
}

void Emu::feed(const std::string& line){
    for(char c:line) in.push_back((uint8_t)c);
    in.push_back(0x0D);
    prompt_seen=false;
}

void Emu::snapshot(std::vector<uint8_t>& s) const {
    s.resize(65536+8+in.size()+4);
    uint8_t* p=s.data();
    memcpy(p,mem,65536); p+=65536;
    *p++=A;*p++=X;*p++=Y;*p++=S;*p++=P;*p++=PC&255;*p++=PC>>8;*p++=kbst?1:0;
    uint32_t q=(uint32_t)in.size(); memcpy(p,&q,4); p+=4;
    int i=0; for(uint8_t b:in) p[i++]=b;
}
void Emu::restore(const std::vector<uint8_t>& s){
    const uint8_t* p=s.data();
    memcpy(mem,p,65536); p+=65536;
    A=p[0];X=p[1];Y=p[2];S=p[3];P=p[4];PC=p[5]|(p[6]<<8);kbst=p[7];p+=8;
    uint32_t q; memcpy(&q,p,4); p+=4;
    in.clear(); for(uint32_t i=0;i<q;i++) in.push_back(p[i]);
    out.clear();prompt_seen=true;last_eolr=false;stall=false;err.clear(); // snapshots pris au prompt
}

// ---- paravirt : le vrai shim_kb ($C000) s'execute ; seuls PV_READ ($FFF6)
// et PV_WRITE ($FFF7) sont emules en natif. Suspension au prompt : si le
// shim est appele depuis read_key ($406D-$40B0) avec KBSTATE=0 et file vide,
// on suspend (NEED_INPUT) au lieu de laisser le shim bloquer.
static inline bool in_readkey(uint16_t ret){ return (ret>=0x406D && ret<=0x40B0) || (ret>=0x7481 && ret<=0x7486); }
static long kb_in=0, kb_out=0, kb_cons=0;
static FILE* kblog(){
    static FILE* f = getenv("KBLOG") ? fopen("/tmp/kb.log","w") : nullptr;
    return f;
}
// Vrai prompt et file vide -> suspend. Retourne true si suspendu.
static bool kb_maysuspend(Emu& e){
    uint8_t lo=e.mem[0x100|((e.S+1)&0xFF)], hi=e.mem[0x100|((e.S+2)&0xFF)];
    uint16_t ret=lo|(hi<<8);
    FILE* L0=kblog(); if(L0){fprintf(L0,"kb7353 ret=$%04X q=%zu kbst=%02X\n",ret,e.in.size(),e.mem[0xC2F1]);
        static int nst=0; if(nst<3){ nst++; fprintf(L0,"  stack S=$%02X:",e.S);
            for(int i=1;i<=8;i++)fprintf(L0," %02X",e.mem[0x100|((e.S+i)&0xFF)]); fprintf(L0,"\n"); } fflush(L0);}
    if(e.mem[0xC2F1]!=0) return false;   // KBSTATE=1 : release imminent, pas de blocage
    if(!in_readkey(ret)||!e.in.empty()) return false;
    FILE* L=kblog(); if(L){fprintf(L,"SUSPEND\n");fflush(L);}
    e.S+=2; e.PC=ret+1;
    return true;
}
// Traps PV (atteints via JSR $FFFn : pop ret, I/O, A=resultat, PC=ret+1).
static void pv_read(Emu& e){
    uint8_t lo=e.mem[0x100|((e.S+1)&0xFF)], hi=e.mem[0x100|((e.S+2)&0xFF)];
    e.S+=2; uint16_t ret=lo|(hi<<8);
    uint16_t sp=e.mem[0x02]|(e.mem[0x03]<<8);
    uint16_t buf=e.mem[sp]|(e.mem[sp+1]<<8);
    uint16_t fd=e.mem[sp+2]|(e.mem[sp+3]<<8);
    uint16_t cnt=e.A|(e.X<<8);
    uint16_t n=0;
    if(fd==0){
        while(n<cnt && !e.in.empty()){ e.mem[(buf+n)&0xFFFF]=e.in.front(); e.in.pop_front(); n++; }
        FILE* L=kblog();
        if(L&&n){ if(kb_cons<200){ for(uint16_t i=0;i<n;i++)fprintf(L,"consume $%02X\n",e.mem[(buf+i)&0xFFFF]); kb_cons+=n; } fflush(L); }
    } else { e.err="PV_READ fd!=0"; }
    { FILE* L=kblog(); if(L){fprintf(L,"pv_read fd=%u cnt=%u -> n=%u q=%zu\n",fd,cnt,n,e.in.size());fflush(L);} }
    e.A=n&0xFF; setZN(e,e.A); e.PC=ret+1;
}
static void pv_write(Emu& e){
    uint8_t lo=e.mem[0x100|((e.S+1)&0xFF)], hi=e.mem[0x100|((e.S+2)&0xFF)];
    e.S+=2; uint16_t ret=lo|(hi<<8);
    // dumps shim (@@FRAME/@@MEM/...) : jetes (capture via hooks natifs)
    e.A&=0xFF; setZN(e,e.A); e.PC=ret+1;
}

static void plot_intercept(Emu& e){
    uint8_t c=e.A;
    if(c==0x3E){ e.out.push_back('>'); e.prompt_seen=true; }
    else e.out.push_back((char)c);
    e.last_eolr=false;
    e.mem[0x75E0]=e.X; e.mem[0x75E1]=e.Y;   // rejoue stx/sty
    e.PC=0x75BE;
}
static void eol_intercept(Emu& e){   // L7694
    if(e.last_eolr){ e.last_eolr=false; }   // EOLR suivi d'EOL = un seul saut
    else e.out.push_back('\n');
    // rejoue pha + lda #$00
    e.mem[0x100|e.S]=e.A; e.S--; e.A=0; setZN(e,0);
    e.PC=0x7697;
}
static void eolr_intercept(Emu& e){  // L7514 (echo RAW)
    e.out.push_back('\n'); e.last_eolr=true;
    e.mem[0x100|e.S]=e.A; e.S--; e.A=0; setZN(e,0);
    e.PC=0x7517;
}
// stubs cassette $0405-$0414 (jamais appeles hors SAVE/LOAD, au cas ou)
static void tape_intercept(Emu& e){
    uint8_t lo=e.mem[0x100|((e.S+1)&0xFF)], hi=e.mem[0x100|((e.S+2)&0xFF)];
    e.S+=2; uint16_t ret=lo|(hi<<8), pc=e.PC;
    uint16_t RD=e.mem[0xE800]|(e.mem[0xE801]<<8), WR=e.mem[0xE802]|(e.mem[0xE803]<<8);
    if(pc==0x0405){ RD=0xE804; e.mem[0xE800]=RD&255; e.mem[0xE801]=RD>>8; }
    else if(pc==0x0408){ if(RD<WR){e.A=e.mem[RD++]; e.P&=~FC;} else {e.A=0; e.P|=FC;}
        e.mem[0xE800]=RD&255; e.mem[0xE801]=RD>>8; setZN(e,e.A); }
    else if(pc==0x040E){ if(WR<0xF700){e.mem[WR++]=e.A;} e.mem[0xE802]=WR&255; e.mem[0xE803]=WR>>8; }
    e.PC=ret+1;
}

bool Emu::play_turn(uint64_t cap_per){
    for(int sac=0;sac<6;sac++){
        Run r=run_until_suspend(cap_per);
        if(r==CAP) return false;
        if(prompt_seen) return true;
        in.push_back(0x0D); // suspend sans '>' (MORE) : CR sacrificiel = touche
    }
    return false;
}
Emu::Run Emu::run_until_suspend(uint64_t cap){
    uint64_t start=icount;
    for(;;){
        if(icount-start>=cap){ stall=true;
            if(getenv("DUMP")){ for(int i=0;i<64;i++){ uint16_t rpc=ringbuf[(ringidx+i)&63]; fprintf(stderr,"  $%04X: %02X\n",rpc,mem[rpc]); } }
            return CAP; }
        // interceptions avant fetch
        if(PC==0x7353){ if(kb_maysuspend(*this)) return NEED_INPUT; } // sinon execute le JMP $C000 (vrai shim)
        if(PC==0xFFF6){ pv_read(*this); icount++; continue; }
        if(PC==0xFFF7){ pv_write(*this); icount++; continue; }
        if(PC==0x75B8){ plot_intercept(*this); icount++; continue; }
        if(PC==0x7694){ eol_intercept(*this); icount++; continue; }
        if(PC==0x7514){ eolr_intercept(*this); icount++; continue; }
        if(PC>=0x0405&&PC<=0x0414&&(PC==0x0405||PC==0x0408||PC==0x040B||PC==0x040E||PC==0x0411||PC==0x0414)){ tape_intercept(*this); icount++; continue; }
        if(!step()) return CAP;
    }
}

// ================= CPU 6502 =================
long pctrace=0;
static uint16_t wp[8]; static int nwp=0;
static void wp_init(){ if(nwp||!getenv("WP"))return; char* s=getenv("WP"); char* p=s;
    while(*p&&nwp<8){ wp[nwp++]=(uint16_t)strtoul(p,nullptr,16); while(*p&&*p!=',')p++; if(*p)p++; } }
static inline void wp_chk(Emu&e,uint16_t a,uint8_t v){ wp_init(); for(int i=0;i<nwp;i++) if(wp[i]==a){
    FILE* L=kblog(); if(!L)L=stderr;
    fprintf(L,"W $%04X=$%02X @ $%04X\n",a,v,e.PC-1); } }
bool Emu::step(){
    uint8_t op=mem[PC++];
    icount++;
    FILE* PL=kblog();
    if(PL && pctrace>0){ pctrace--; fprintf(PL,"$%04X %02X A=%02X X=%02X Y=%02X S=%02X\n",PC-1,op,A,X,Y,S); if(pctrace==0)fflush(PL); }
    static bool tr = getenv("TRACE")!=nullptr;
    ringbuf[ringidx]=PC-1; ringidx=(ringidx+1)&63;
    if(tr && icount<200) fprintf(stderr, "$%04X: %02X  A=%02X X=%02X Y=%02X S=%02X P=%02X\n", PC-1, op, A,X,Y,S,P);
    auto rd=[&]()->uint8_t{return mem[PC++];};
    uint16_t a; uint8_t v; int8_t off;
    switch(op){
    case 0x00: err="BRK"; return false;
    // LDA
    case 0xA9: A=rd(); setZN(*this,A); break;
    case 0xA5: A=mem[rd()]; setZN(*this,A); break;
    case 0xB5: A=mem[(rd()+X)&0xFF]; setZN(*this,A); break;
    case 0xAD: {a=rd();a|=rd()<<8;A=mem[a];setZN(*this,A);} break;
    case 0xBD: {a=rd();a|=rd()<<8;A=mem[(a+X)&0xFFFF];setZN(*this,A);} break;
    case 0xB9: {a=rd();a|=rd()<<8;A=mem[(a+Y)&0xFFFF];setZN(*this,A);} break;
    case 0xA1: {uint8_t z=(rd()+X)&0xFF;a=mem[z]|(mem[(z+1)&0xFF]<<8);A=mem[a];setZN(*this,A);} break;
    case 0xB1: {uint8_t z=rd();a=(mem[z]|(mem[(z+1)&0xFF]<<8))+Y;A=mem[a&0xFFFF];setZN(*this,A);} break;
    // LDX
    case 0xA2: X=rd(); setZN(*this,X); break;
    case 0xA6: X=mem[rd()]; setZN(*this,X); break;
    case 0xB6: X=mem[(rd()+Y)&0xFF]; setZN(*this,X); break;
    case 0xAE: {a=rd();a|=rd()<<8;X=mem[a];setZN(*this,X);} break;
    case 0xBE: {a=rd();a|=rd()<<8;X=mem[(a+Y)&0xFFFF];setZN(*this,X);} break;
    // LDY
    case 0xA0: Y=rd(); setZN(*this,Y); break;
    case 0xA4: Y=mem[rd()]; setZN(*this,Y); break;
    case 0xB4: Y=mem[(rd()+X)&0xFF]; setZN(*this,Y); break;
    case 0xAC: {a=rd();a|=rd()<<8;Y=mem[a];setZN(*this,Y);} break;
    case 0xBC: {a=rd();a|=rd()<<8;Y=mem[(a+X)&0xFFFF];setZN(*this,Y);} break;
    // STA
    case 0x85: {uint8_t z=rd(); mem[z]=A; wp_chk(*this,z,A);} break;
    case 0x95: {uint8_t z=(rd()+X)&0xFF; mem[z]=A; wp_chk(*this,z,A);} break;
    case 0x8D: {a=rd();a|=rd()<<8;mem[a]=(A); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(A));} break;
    case 0x9D: {a=rd();a|=rd()<<8;mem[(a+X)&0xFFFF]=(A); wp_chk(*this,(uint16_t)(&(mem[(a+X)&0xFFFF])-mem),(uint8_t)(A));} break;
    case 0x99: {a=rd();a|=rd()<<8;mem[(a+Y)&0xFFFF]=(A); wp_chk(*this,(uint16_t)(&(mem[(a+Y)&0xFFFF])-mem),(uint8_t)(A));} break;
    case 0x81: {uint8_t z=(rd()+X)&0xFF;a=mem[z]|(mem[(z+1)&0xFF]<<8);mem[a]=(A); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(A));} break;
    case 0x91: {uint8_t z=rd();a=(mem[z]|(mem[(z+1)&0xFF]<<8))+Y;mem[a&0xFFFF]=(A); wp_chk(*this,(uint16_t)(&(mem[a&0xFFFF])-mem),(uint8_t)(A));} break;
    // STX/STY
    case 0x86: {uint8_t z=rd(); mem[z]=X; wp_chk(*this,z,X);} break;
    case 0x96: {uint8_t z=(rd()+Y)&0xFF; mem[z]=X; wp_chk(*this,z,X);} break;
    case 0x8E: {a=rd();a|=rd()<<8;mem[a]=(X); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(X));} break;
    case 0x84: {uint8_t z=rd(); mem[z]=Y; wp_chk(*this,z,Y);} break;
    case 0x94: {uint8_t z=(rd()+X)&0xFF; mem[z]=Y; wp_chk(*this,z,Y);} break;
    case 0x8C: {a=rd();a|=rd()<<8;mem[a]=(Y); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(Y));} break;
    // transferts
    case 0xAA: X=A; setZN(*this,X); break;
    case 0xA8: Y=A; setZN(*this,Y); break;
    case 0xBA: X=S; setZN(*this,X); break;
    case 0x8A: A=X; setZN(*this,A); break;
    case 0x9A: S=X; break;
    case 0x98: A=Y; setZN(*this,A); break;
    // pile
    case 0x48: mem[0x100|S]=A; S--; break;
    case 0x68: S++; A=mem[0x100|S]; setZN(*this,A); break;
    case 0x08: mem[0x100|S]=P|0x30; S--; break;
    case 0x28: S++; P=(mem[0x100|S]&0xEF)|0x20; break;
    // ADC
    case 0x69: v=rd(); goto adc;
    case 0x65: v=mem[rd()]; goto adc;
    case 0x75: v=mem[(rd()+X)&0xFF]; goto adc;
    case 0x6D: {a=rd();a|=rd()<<8;v=mem[a]; goto adc;}
    case 0x7D: {a=rd();a|=rd()<<8;v=mem[(a+X)&0xFFFF]; goto adc;}
    case 0x79: {a=rd();a|=rd()<<8;v=mem[(a+Y)&0xFFFF]; goto adc;}
    case 0x61: {uint8_t z=(rd()+X)&0xFF;a=mem[z]|(mem[(z+1)&0xFF]<<8);v=mem[a]; goto adc;}
    case 0x71: {uint8_t z=rd();a=(mem[z]|(mem[(z+1)&0xFF]<<8))+Y;v=mem[a&0xFFFF]; goto adc;}
    adc: {
        uint8_t c=(P&FC)?1:0;
        uint16_t b=A+v+c;
        uint8_t V=((~(A^v))&(A^(b&255))&0x80)?FV:0;
        if(P&FD){ // BCD exact
            uint16_t t=b;
            if(((A&15)+(v&15)+c)>9) t+=6;
            uint8_t Cout=(t>0x99)?1:0;
            if(Cout) t+=0x60;
            P=(P&~(FC|FV|FZ|FN))|(Cout?FC:0)|V;
            A=t&255; setZN(*this,A);
        } else {
            P=(P&~(FC|FV|FZ|FN))|((b>0xFF)?FC:0)|V;
            A=b&255; setZN(*this,A);
        }
        break; }
    // SBC
    case 0xE9: v=rd(); goto sbc;
    case 0xE5: v=mem[rd()]; goto sbc;
    case 0xF5: v=mem[(rd()+X)&0xFF]; goto sbc;
    case 0xED: {a=rd();a|=rd()<<8;v=mem[a]; goto sbc;}
    case 0xFD: {a=rd();a|=rd()<<8;v=mem[(a+X)&0xFFFF]; goto sbc;}
    case 0xF9: {a=rd();a|=rd()<<8;v=mem[(a+Y)&0xFFFF]; goto sbc;}
    case 0xE1: {uint8_t z=(rd()+X)&0xFF;a=mem[z]|(mem[(z+1)&0xFF]<<8);v=mem[a]; goto sbc;}
    case 0xF1: {uint8_t z=rd();a=(mem[z]|(mem[(z+1)&0xFF]<<8))+Y;v=mem[a&0xFFFF]; goto sbc;}
    sbc: {
        uint8_t c=(P&FC)?1:0;
        uint16_t d=A-v-(1-c);
        uint8_t V=(((A^v))&(A^(d&255))&0x80)?FV:0;
        if(P&FD){ // BCD exact
            int16_t t=(int16_t)A-(int16_t)v-(1-c);
            if(((int16_t)(A&15)-(int16_t)(v&15)-(1-c))<0) t-=6;
            uint8_t Cout=(t>=0)?1:0;
            if(!Cout) t-=0x60;
            P=(P&~(FC|FV|FZ|FN))|(Cout?FC:0)|V;
            A=t&255; setZN(*this,A);
        } else {
            P=(P&~(FC|FV|FZ|FN))|(((d&0xFF00)==0)?FC:0)|V;
            A=d&255; setZN(*this,A);
        }
        break; }
    // AND/EOR/ORA
    case 0x29: A&=rd(); setZN(*this,A); break;
    case 0x25: A&=mem[rd()]; setZN(*this,A); break;
    case 0x35: A&=mem[(rd()+X)&0xFF]; setZN(*this,A); break;
    case 0x2D: {a=rd();a|=rd()<<8;A&=mem[a];setZN(*this,A);} break;
    case 0x3D: {a=rd();a|=rd()<<8;A&=mem[(a+X)&0xFFFF];setZN(*this,A);} break;
    case 0x39: {a=rd();a|=rd()<<8;A&=mem[(a+Y)&0xFFFF];setZN(*this,A);} break;
    case 0x21: {uint8_t z=(rd()+X)&0xFF;a=mem[z]|(mem[(z+1)&0xFF]<<8);A&=mem[a];setZN(*this,A);} break;
    case 0x31: {uint8_t z=rd();a=(mem[z]|(mem[(z+1)&0xFF]<<8))+Y;A&=mem[a&0xFFFF];setZN(*this,A);} break;
    case 0x49: A^=rd(); setZN(*this,A); break;
    case 0x45: A^=mem[rd()]; setZN(*this,A); break;
    case 0x55: A^=mem[(rd()+X)&0xFF]; setZN(*this,A); break;
    case 0x4D: {a=rd();a|=rd()<<8;A^=mem[a];setZN(*this,A);} break;
    case 0x5D: {a=rd();a|=rd()<<8;A^=mem[(a+X)&0xFFFF];setZN(*this,A);} break;
    case 0x59: {a=rd();a|=rd()<<8;A^=mem[(a+Y)&0xFFFF];setZN(*this,A);} break;
    case 0x41: {uint8_t z=(rd()+X)&0xFF;a=mem[z]|(mem[(z+1)&0xFF]<<8);A^=mem[a];setZN(*this,A);} break;
    case 0x51: {uint8_t z=rd();a=(mem[z]|(mem[(z+1)&0xFF]<<8))+Y;A^=mem[a&0xFFFF];setZN(*this,A);} break;
    case 0x09: A|=rd(); setZN(*this,A); break;
    case 0x05: A|=mem[rd()]; setZN(*this,A); break;
    case 0x15: A|=mem[(rd()+X)&0xFF]; setZN(*this,A); break;
    case 0x0D: {a=rd();a|=rd()<<8;A|=mem[a];setZN(*this,A);} break;
    case 0x1D: {a=rd();a|=rd()<<8;A|=mem[(a+X)&0xFFFF];setZN(*this,A);} break;
    case 0x19: {a=rd();a|=rd()<<8;A|=mem[(a+Y)&0xFFFF];setZN(*this,A);} break;
    case 0x01: {uint8_t z=(rd()+X)&0xFF;a=mem[z]|(mem[(z+1)&0xFF]<<8);A|=mem[a];setZN(*this,A);} break;
    case 0x11: {uint8_t z=rd();a=(mem[z]|(mem[(z+1)&0xFF]<<8))+Y;A|=mem[a&0xFFFF];setZN(*this,A);} break;
    // BIT
    case 0x24: v=mem[rd()]; P=(P&~(FV|FZ|FN))|((v&(A))?0:FZ)|(v&(FV|FN)); break;
    case 0x2C: {a=rd();a|=rd()<<8;v=mem[a];P=(P&~(FV|FZ|FN))|((v&(A))?0:FZ)|(v&(FV|FN));} break;
    // CMP/CPX/CPY
    case 0xC9: v=rd(); goto cmp;
    case 0xC5: v=mem[rd()]; goto cmp;
    case 0xD5: v=mem[(rd()+X)&0xFF]; goto cmp;
    case 0xCD: {a=rd();a|=rd()<<8;v=mem[a]; goto cmp;}
    case 0xDD: {a=rd();a|=rd()<<8;v=mem[(a+X)&0xFFFF]; goto cmp;}
    case 0xD9: {a=rd();a|=rd()<<8;v=mem[(a+Y)&0xFFFF]; goto cmp;}
    case 0xC1: {uint8_t z=(rd()+X)&0xFF;a=mem[z]|(mem[(z+1)&0xFF]<<8);v=mem[a]; goto cmp;}
    case 0xD1: {uint8_t z=rd();a=(mem[z]|(mem[(z+1)&0xFF]<<8))+Y;v=mem[a&0xFFFF]; goto cmp;}
    cmp: P=(P&~(FC|FZ|FN))|(A>=v?FC:0)|((A==v)?FZ:0)|(((A-v)&0x80)?FN:0); break;
    case 0xE0: v=rd(); goto cpx;
    case 0xE4: v=mem[rd()]; goto cpx;
    case 0xEC: {a=rd();a|=rd()<<8;v=mem[a]; goto cpx;}
    cpx: P=(P&~(FC|FZ|FN))|(X>=v?FC:0)|((X==v)?FZ:0)|(((X-v)&0x80)?FN:0); break;
    case 0xC0: v=rd(); goto cpy;
    case 0xC4: v=mem[rd()]; goto cpy;
    case 0xCC: {a=rd();a|=rd()<<8;v=mem[a]; goto cpy;}
    cpy: P=(P&~(FC|FZ|FN))|(Y>=v?FC:0)|((Y==v)?FZ:0)|(((Y-v)&0x80)?FN:0); break;
    // INC/DEC
    case 0xE6: a=rd(); v=mem[a]+1; mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v)); setZN(*this,v); break;
    case 0xF6: a=(rd()+X)&0xFF; v=mem[a]+1; mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v)); setZN(*this,v); break;
    case 0xEE: {a=rd();a|=rd()<<8;v=mem[a]+1;mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0xFE: {a=rd();a|=rd()<<8;v=mem[(a+X)&0xFFFF]+1;mem[(a+X)&0xFFFF]=(v); wp_chk(*this,(uint16_t)(&(mem[(a+X)&0xFFFF])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0xC6: a=rd(); v=mem[a]-1; mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v)); setZN(*this,v); break;
    case 0xD6: a=(rd()+X)&0xFF; v=mem[a]-1; mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v)); setZN(*this,v); break;
    case 0xCE: {a=rd();a|=rd()<<8;v=mem[a]-1;mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0xDE: {a=rd();a|=rd()<<8;v=mem[(a+X)&0xFFFF]-1;mem[(a+X)&0xFFFF]=(v); wp_chk(*this,(uint16_t)(&(mem[(a+X)&0xFFFF])-mem),(uint8_t)(v));setZN(*this,v);} break;
    // INX/DEX/INY/DEY
    case 0xE8: X++; setZN(*this,X); break;
    case 0xCA: X--; setZN(*this,X); break;
    case 0xC8: Y++; setZN(*this,Y); break;
    case 0x88: Y--; setZN(*this,Y); break;
    // ASL/LSR/ROL/ROR
    case 0x0A: P=(P&~FC)|((A>>7)&1); A<<=1; setZN(*this,A); break;
    case 0x06: a=rd(); v=mem[a]; P=(P&~FC)|((v>>7)&1); v<<=1; mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v)); setZN(*this,v); break;
    case 0x16: a=(rd()+X)&0xFF; v=mem[a]; P=(P&~FC)|((v>>7)&1); v<<=1; mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v)); setZN(*this,v); break;
    case 0x0E: {a=rd();a|=rd()<<8;v=mem[a];P=(P&~FC)|((v>>7)&1);v<<=1;mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0x1E: {a=rd();a|=rd()<<8;a=(a+X)&0xFFFF;v=mem[a];P=(P&~FC)|((v>>7)&1);v<<=1;mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0x4A: P=(P&~FC)|(A&1); A>>=1; setZN(*this,A); break;
    case 0x46: a=rd(); v=mem[a]; P=(P&~FC)|(v&1); v>>=1; mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v)); setZN(*this,v); break;
    case 0x56: a=(rd()+X)&0xFF; v=mem[a]; P=(P&~FC)|(v&1); v>>=1; mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v)); setZN(*this,v); break;
    case 0x4E: {a=rd();a|=rd()<<8;v=mem[a];P=(P&~FC)|(v&1);v>>=1;mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0x5E: {a=rd();a|=rd()<<8;a=(a+X)&0xFFFF;v=mem[a];P=(P&~FC)|(v&1);v>>=1;mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0x2A: {uint8_t c=P&FC; P=(P&~FC)|((A>>7)&1); A=(A<<1)|c; setZN(*this,A);} break;
    case 0x26: {a=rd();uint8_t c=P&FC;v=mem[a];P=(P&~FC)|((v>>7)&1);v=(v<<1)|c;mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0x36: {a=(rd()+X)&0xFF;uint8_t c=P&FC;v=mem[a];P=(P&~FC)|((v>>7)&1);v=(v<<1)|c;mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0x2E: {a=rd();a|=rd()<<8;uint8_t c=P&FC;v=mem[a];P=(P&~FC)|((v>>7)&1);v=(v<<1)|c;mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0x3E: {a=rd();a|=rd()<<8;a=(a+X)&0xFFFF;uint8_t c=P&FC;v=mem[a];P=(P&~FC)|((v>>7)&1);v=(v<<1)|c;mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0x6A: {uint8_t c=P&FC; P=(P&~FC)|(A&1); A=(A>>1)|(c<<7); setZN(*this,A);} break;
    case 0x66: {a=rd();uint8_t c=P&FC;v=mem[a];P=(P&~FC)|(v&1);v=(v>>1)|(c<<7);mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0x76: {a=(rd()+X)&0xFF;uint8_t c=P&FC;v=mem[a];P=(P&~FC)|(v&1);v=(v>>1)|(c<<7);mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0x6E: {a=rd();a|=rd()<<8;uint8_t c=P&FC;v=mem[a];P=(P&~FC)|(v&1);v=(v>>1)|(c<<7);mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    case 0x7E: {a=rd();a|=rd()<<8;a=(a+X)&0xFFFF;uint8_t c=P&FC;v=mem[a];P=(P&~FC)|(v&1);v=(v>>1)|(c<<7);mem[a]=(v); wp_chk(*this,(uint16_t)(&(mem[a])-mem),(uint8_t)(v));setZN(*this,v);} break;
    // branches
    case 0x10: off=rd(); if(!(P&FN)) PC+=off; break;
    case 0x30: off=rd(); if(P&FN) PC+=off; break;
    case 0x50: off=rd(); if(!(P&FV)) PC+=off; break;
    case 0x70: off=rd(); if(P&FV) PC+=off; break;
    case 0x90: off=rd(); if(!(P&FC)) PC+=off; break;
    case 0xB0: off=rd(); if(P&FC) PC+=off; break;
    case 0xD0: off=rd(); if(!(P&FZ)) PC+=off; break;
    case 0xF0: off=rd(); if(P&FZ) PC+=off; break;
    // sauts
    case 0x4C: {a=rd();a|=rd()<<8;PC=a;} break;
    case 0x6C: {a=rd();a|=rd()<<8;uint16_t lo=mem[a],hi=mem[(a&0xFF00)|((a+1)&0xFF)];PC=lo|(hi<<8);} break; // bug JMP indirect replique
    case 0x20: {a=rd();a|=rd()<<8;uint16_t r=PC-1;mem[0x100|S]=(r>>8);S--;mem[0x100|S]=(r&255);S--;PC=a;} break;
    case 0x60: {S++;uint8_t lo2=mem[0x100|S];S++;uint8_t hi2=mem[0x100|S];PC=(lo2|(hi2<<8))+1;} break;
    case 0x40: {S++;P=(mem[0x100|S]&0xEF)|0x20;S++;uint8_t lo2=mem[0x100|S];S++;uint8_t hi2=mem[0x100|S];PC=lo2|(hi2<<8);} break;
    // flags
    case 0x18: P&=~FC; break;
    case 0x38: P|=FC; break;
    case 0x58: P&=~FI; break;
    case 0x78: P|=FI; break;
    case 0xB8: P&=~FV; break;
    case 0xD8: P&=~FD; break;
    case 0xF8: P|=FD; break;
    // divers
    case 0xEA: break;
    case 0x9C: case 0x9E: case 0x89: case 0x80: case 0x82: case 0xC2: case 0xE2: // NOPs 65C02 (au cas ou)
        rd(); break;
    case 0xA7: case 0xB7: case 0xAF: case 0xBF: case 0xA3: case 0xB3: // LAX illégaux (au cas ou)
        rd(); if(op==0xAF||op==0xBF){rd();} A=X=mem[0]; setZN(*this,A); err="LAX?"; return false;
    default: { char b[64]; snprintf(b,64,"opcode $%02X @ $%04X",op,PC-1); err=b;
        if(getenv("DUMP")){ for(int i=0;i<64;i++){ uint16_t rpc=ringbuf[(ringidx+i)&63]; fprintf(stderr,"  $%04X: %02X\n",rpc,mem[rpc]); } }
        return false; }
    }
    return true;
}
