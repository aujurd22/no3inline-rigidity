// csearch2.cpp — Full edge-swap search for rot4-NTIL
//
// Three move types: YSWAP (swap ys), XSWAP (swap xs), XYSWAP (swap both).
// Each has meas_* and commit_* pair, exactly like csearch1's proven structure.
// Tabu list + ejection chain for local-minima escape.

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <random>
#include <chrono>
#include <algorithm>
#include <fstream>
#include <cctype>
using namespace std;

typedef uint64_t LK; typedef long long LL;
static const int AOFF=200,BOFF=200,COFF=20000,ASPAN=400,BSPAN=400,CSPAN=40000;
struct Pt{int x,y;};
enum MoveType{YSWAP=0,XSWAP=1,XYSWAP=2,NUM_MOVES=3};

int m,n;
vector<int> xs,ys;
vector<Pt> pts;
unordered_map<LK,unordered_set<int>> lpts;
LL total_bad;
mt19937 rng(1);
vector<char> present;
vector<LK> g_touch;
vector<char> tabu;
int tabu_tenure=10,tabu_cnt=0;

Pt c4(int x,int y,int r,int n){
    if(r==0)return{x,y}; if(r==1)return{n-1-y,x};
    if(r==2)return{n-1-x,n-1-y}; return{y,n-1-x};
}
static inline int igcd(int a,int b){a=abs(a);b=abs(b);while(b){int t=a%b;a=b;b=t;}return a;}
static inline LK line_of(Pt p,Pt q){
    int a=-(q.y-p.y),b=(q.x-p.x),c=(q.y-p.y)*p.x-(q.x-p.x)*p.y;
    int g=igcd(abs(a),abs(b));g=igcd(g,abs(c));
    if(g){a/=g;b/=g;c/=g;}
    if(a<0||(a==0&&b<0)||(a==0&&b==0&&c<0)){a=-a;b=-b;c=-c;}
    LK K=(LK)(a+AOFF);K=K*BSPAN+(b+BOFF);K=K*CSPAN+(c+COFF);return K;
}
static inline LL C3(LL t){return(t>=3)?t*(t-1)*(t-2)/6:0;}

void build_points(){
    pts.resize(4*m);
    for(int i=0;i<m;i++) for(int r=0;r<4;r++) pts[4*i+r]=c4(xs[i],ys[i],r,n);
}
void add_point(int i){
    g_touch.clear(); Pt pi=pts[i];
    for(int j=0;j<4*m;j++){
        if(j==i||!present[j])continue;
        if(pts[j].x==pi.x&&pts[j].y==pi.y)continue;
        LK k=line_of(pi,pts[j]); lpts[k].insert(j); g_touch.push_back(k);
    }
    sort(g_touch.begin(),g_touch.end()); g_touch.erase(unique(g_touch.begin(),g_touch.end()),g_touch.end());
    for(LK k:g_touch){auto&S=lpts[k];LL o=(LL)S.size();S.insert(i);total_bad+=C3(o+1)-C3(o);}
    present[i]=1;
}
void remove_point(int i){
    present[i]=0; g_touch.clear(); Pt pi=pts[i];
    for(int j=0;j<4*m;j++){
        if(j==i||!present[j])continue;
        if(pts[j].x==pi.x&&pts[j].y==pi.y)continue;
        g_touch.push_back(line_of(pi,pts[j]));
    }
    sort(g_touch.begin(),g_touch.end()); g_touch.erase(unique(g_touch.begin(),g_touch.end()),g_touch.end());
    for(LK k:g_touch){auto it=lpts.find(k);if(it==lpts.end())continue;auto&S=it->second;
        LL c=(LL)S.size();S.erase(i);total_bad+=C3(c-1)-C3(c);if(S.size()<2)lpts.erase(it);}
}
void build_map(){lpts.clear();total_bad=0; present.assign(4*m,0);for(int i=0;i<4*m;i++)add_point(i);}

void init_random(){
    xs.assign(m,0);ys.assign(m,0);
    vector<int>type(m,1);int conv=(int)(0.35*m);
    for(int t=0;t<conv;t++){int a=rng()%m,b=(a+1+rng()%(m-1))%m;if(type[a]==1&&type[b]==1){type[a]=2;type[b]=0;}}
    vector<int>X,Y;
    for(int v=0;v<m;v++){if(type[v]>=1)X.push_back(v);if(type[v]==2)X.push_back(v);
        if(type[v]<=1)Y.push_back(v);if(type[v]==0)Y.push_back(v);}
    shuffle(X.begin(),X.end(),rng);shuffle(Y.begin(),Y.end(),rng);xs=X;ys=Y;
    build_points();build_map();
}

// ---- Inline move functions (exact csearch1 structure, 3 types) ----

// YSWAP: swap ys[i],ys[j] (original)
void commit_yswap(int i,int j){
    int oi[4],oj[4]; for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
    for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
    int t=ys[i];ys[i]=ys[j];ys[j]=t;
    for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r,n);pts[oj[r]]=c4(xs[j],ys[j],r,n);}
    for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
}
LL meas_yswap(int i,int j){
    int oi[4],oj[4]; for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
    vector<int>xs0=xs,ys0=ys; LL before=total_bad;
    for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
    int t=ys[i];ys[i]=ys[j];ys[j]=t;
    for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r,n);pts[oj[r]]=c4(xs[j],ys[j],r,n);}
    for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
    LL delta=total_bad-before; xs=xs0;ys=ys0; build_points();build_map(); return delta;
}

// XSWAP: swap xs[i],xs[j] (new — symmetric to YSWAP)
void commit_xswap(int i,int j){
    int oi[4],oj[4]; for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
    for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
    int t=xs[i];xs[i]=xs[j];xs[j]=t;
    for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r,n);pts[oj[r]]=c4(xs[j],ys[j],r,n);}
    for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
}
LL meas_xswap(int i,int j){
    int oi[4],oj[4]; for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
    vector<int>xs0=xs,ys0=ys; LL before=total_bad;
    for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
    int t=xs[i];xs[i]=xs[j];xs[j]=t;
    for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r,n);pts[oj[r]]=c4(xs[j],ys[j],r,n);}
    for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
    LL delta=total_bad-before; xs=xs0;ys=ys0; build_points();build_map(); return delta;
}

// XYSWAP: swap cell i and cell j (both xs+ys — true edge swap)
void commit_xyswap(int i,int j){
    int oi[4],oj[4]; for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
    for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
    int tx=xs[i],ty=ys[i]; xs[i]=xs[j];ys[i]=ys[j]; xs[j]=tx;ys[j]=ty;
    for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r,n);pts[oj[r]]=c4(xs[j],ys[j],r,n);}
    for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
}
LL meas_xyswap(int i,int j){
    int oi[4],oj[4]; for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
    vector<int>xs0=xs,ys0=ys; LL before=total_bad;
    for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
    int tx=xs[i],ty=ys[i]; xs[i]=xs[j];ys[i]=ys[j]; xs[j]=tx;ys[j]=ty;
    for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r,n);pts[oj[r]]=c4(xs[j],ys[j],r,n);}
    for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
    LL delta=total_bad-before; xs=xs0;ys=ys0; build_points();build_map(); return delta;
}

// ---- Dispatcher (for selftest) ----
void commit_move(int i,int j,MoveType t){
    if(t==YSWAP)commit_yswap(i,j);else if(t==XSWAP)commit_xswap(i,j);else commit_xyswap(i,j);
}
LL meas_move(int i,int j,MoveType t){
    if(t==YSWAP)return meas_yswap(i,j);
    if(t==XSWAP)return meas_xswap(i,j); return meas_xyswap(i,j);
}

// ---- Tabu ----
void tabu_add(int i,int j){tabu[i*m+j]=1;tabu[j*m+i]=1;}
bool tabu_chk(int i,int j){return tabu[i*m+j];}
void tabu_decay(){if(++tabu_cnt%tabu_tenure==0)fill(tabu.begin(),tabu.end(),0);}

// ---- SA restart (3 move types) ----
bool sa_restart(LL max_moves,double T0,double Tend,LL& best_out,vector<int>& bxs,vector<int>& bys,bool keep_init=false){
    if(!keep_init)init_random();
    LL cur=total_bad;best_out=cur;bxs=xs;bys=ys;
    double T=T0,Tdec=pow(Tend/T0,1.0/max_moves);
    uniform_real_distribution<double>ur(0.0,1.0);int stale=0;
    for(LL mv=0;mv<max_moves;mv++){
        int i=rng()%m,j=rng()%m;if(i==j)continue;
        MoveType mt=(MoveType)(rng()%NUM_MOVES);
        if(tabu_chk(i,j)&&mt!=XYSWAP)continue;
        LL before=total_bad;
        // Snapshot for possible revert
        vector<int> xs0=xs,ys0=ys;
        commit_move(i,j,mt); LL newbad=total_bad;
        if(newbad<=before||ur(rng)<exp(-(double)(newbad-before)/T)){
            cur=newbad; if(cur<best_out){best_out=cur;bxs=xs;bys=ys;stale=0;}
            if(cur==0)return true;
            if(newbad<before)tabu_add(i,j);
        }else{
            // Revert from snapshot (reliable restore)
            xs=xs0;ys=ys0;build_points();build_map(); cur=total_bad;
        }
        T*=Tdec; tabu_decay();
        if(++stale>max_moves/10){T=max(T,T0*0.3);stale=0;}
    }
    best_out=cur; return false;
}

// ---- Greedy restart (scans all 3 move types) ----
bool greedy_restart(LL max_steps,LL& best_out,vector<int>& bxs,vector<int>& bys,bool keep_init=false){
    if(!keep_init)init_random();
    LL cur=total_bad;best_out=cur;bxs=xs;bys=ys;
    for(LL step=0;step<max_steps&&cur>0;step++){
        bool found=false;
        for(int ii=0;ii<m&&!found;ii++)for(int jj=ii+1;jj<m&&!found;jj++)
            for(int tt=0;tt<NUM_MOVES&&!found;tt++)
                if(meas_move(ii,jj,(MoveType)tt)<0){
                    commit_move(ii,jj,(MoveType)tt);cur=total_bad;found=true;
                    if(cur<best_out){best_out=cur;bxs=xs;bys=ys;}
                    if(cur==0)return true;
                }
        if(!found){// Possibly state drift vs theory mismatch. Rebuild to verify.
            LL vfy=0;unordered_map<LK,unordered_set<int>>lp;
            for(int a=0;a<4*m;a++)for(int b=a+1;b<4*m;b++){
                if(pts[a].x==pts[b].x&&pts[a].y==pts[b].y)continue;
                LK k=line_of(pts[a],pts[b]);lp[k].insert(a);lp[k].insert(b);
            }
            for(auto&kv:lp){LL c=kv.second.size();if(c>=3)vfy+=c*(c-1)*(c-2)/6;}
            if(vfy!=total_bad){// state drift — rebuild and retry
                build_map();cur=total_bad;if(cur<best_out){best_out=cur;bxs=xs;bys=ys;}
                if(cur==0)return true;step--;continue;
            }else break;// genuinely stuck
        } // stuck (should not happen per Theorem 1 for m>=14)
    }
    best_out=cur;return false;
}

static bool load_init(const string&path, vector<int>& oxs, vector<int>& oys, int m){
    ifstream f(path); if(!f) return false;
    oxs.assign(m,0); oys.assign(m,0); int cnt=0; string line;
    while(getline(f,line)){
        size_t p=line.find("cells:"); if(p!=string::npos) line=line.substr(p+6);
        vector<int> nums; size_t i=0;
        while(i<line.size()){
            if(isdigit((unsigned char)line[i])||line[i]=='-'){
                long v=strtol(line.c_str()+i,nullptr,10); nums.push_back((int)v);
                while(i<line.size()&&(isdigit((unsigned char)line[i])||line[i]=='-')) i++;
            } else i++;
        }
        if(nums.size()>=2){ oxs[cnt]=nums[0]; oys[cnt]=nums[1]; cnt++; if(cnt>=m) break; }
    }
    return cnt==m;
}

// ---- Main ----
int main(int argc,char**argv){
    m=10;int restarts=100;LL max_moves=5000000LL;int seed=1;bool greedy=false,selftest=false;int pos=0;string init_path;
    for(int a=1;a<argc;a++){
        string s=argv[a];
        if(s=="--m"&&a+1<argc)m=atoi(argv[++a]);
        else if(s=="--restarts"&&a+1<argc)restarts=atoi(argv[++a]);
        else if(s=="--moves"&&a+1<argc)max_moves=atoll(argv[++a]);
        else if(s=="--seed"&&a+1<argc)seed=atoi(argv[++a]);
        else if(s=="--init"&&a+1<argc)init_path=argv[++a];
        else if(s=="--greedy")greedy=true;
        else if(s=="--selftest")selftest=true;
        else if(!s.empty()&&s[0]!='-'){if(pos==0)m=atoi(s.c_str());else if(pos==1)restarts=atoi(s.c_str());
            else if(pos==2)max_moves=atoll(s.c_str());else if(pos==3)seed=atoi(s.c_str());pos++;}
    }
    n=2*m;rng=mt19937(seed);tabu.assign(m*m,0);

    // ---- Selftest ----
    if(selftest){
        init_random();int leaks=0,mism=0;
        for(int t=0;t<3000;t++){
            int i=rng()%m,j=rng()%m;if(i==j)continue;MoveType mt=(MoveType)(rng()%NUM_MOVES);
            LL b0=total_bad; LL d=meas_move(i,j,mt); LL b1=total_bad;
            if(b1!=b0){printf("LEAK t=%d mt=%d: %lld -> %lld\n",t,mt,b0,b1);if(++leaks>3)break;continue;}
            // Snapshot for reliable undo
            vector<int> xs0=xs,ys0=ys;
            commit_move(i,j,mt); LL d_true=total_bad-b0;
            if(d!=d_true){printf("MISMATCH t=%d mt=%d: measure=%lld true=%lld\n",t,mt,d,d_true);if(++mism>3)break;}
            // Restore from snapshot
            xs=xs0;ys=ys0;build_points();build_map();
        }
        printf("SELFTEST: leaks=%d mismatches=%d (total_bad=%lld)\n",leaks,mism,total_bad); return 0;
    }

    // ---- Search ----
    auto t0=chrono::high_resolution_clock::now(); bool found=false; LL best_overall=1e18;
    vector<int>bxs,bys;
    // progress log: flushed every step so a timeout-kill (SIGTERM) does not lose it
    FILE* pf=fopen("csearch2_progress.log","w");
    if(pf){fprintf(pf,"start m=%d restarts=%d\n",m,restarts); fflush(pf);}
    if(!init_path.empty()){
        vector<int> ixs,iys;
        if(!load_init(init_path,ixs,iys,m)){ fprintf(stderr,"INIT LOAD FAILED: %s\n",init_path.c_str()); return 2; }
        xs=ixs; ys=iys; build_points(); build_map();
        LL best=0; vector<int>rsx,rsy; bool ok=sa_restart(max_moves,3.0,0.005,best,rsx,rsy,true);
        best_overall=best; bxs=rsx;bys=rsy; found=ok;
    } else {
        for(int rs=0;rs<restarts&&!found;rs++){
            LL best=0;vector<int>rsx,rsy;bool ok;
            if(greedy)ok=greedy_restart(max_moves,best,rsx,rsy);
            else ok=sa_restart(max_moves,3.0,0.005,best,rsx,rsy);
            if(best<best_overall){best_overall=best;bxs=rsx;bys=rsy;}
            if(ok){found=true;break;}
            if(rs%10==0){fprintf(stderr,"rs=%d best=%lld\n",rs,best); if(pf){fprintf(pf,"rs=%d best=%lld\n",rs,best); fflush(pf);}}
        }
    }
    auto t1=chrono::high_resolution_clock::now();double secs=chrono::duration<double>(t1-t0).count();
    if(pf){fprintf(pf,"DONE best_overall=%lld found=%d time=%.2f\n",best_overall,(int)found,secs); fflush(pf); fclose(pf);}
    if(found){
        xs=bxs;ys=bys;build_points();build_map();
        printf("verify_bad=%lld\n",total_bad);
        if(total_bad==0){printf("FOUND m=%d time=%.2fs\n",m,secs);printf("cells:");for(int i=0;i<m;i++)printf(" (%d,%d)",bxs[i],bys[i]);printf("\n");}
        else found=false;
    }
    if(!found)printf("NOTFOUND m=%d best_bad=%lld time=%.2fs restarts=%d\n",m,best_overall,secs,restarts);
    return 0;
}
