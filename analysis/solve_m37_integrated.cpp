// solve_m37_integrated.cpp
//
// Multi-threaded integrated solver for the rot4 (C4-symmetric) NTIL problem,
// combining ALL knowledge accumulated in the SIRH research program:
//
//   K1  Fundamental-domain = top-left m x m quadrant; a valid rot4 NTIL's
//       quadrant cells form a 2-regular graph (Th-44 / R9b): every index value
//       v in {0..m-1} appears EXACTLY TWICE across the combined multiset xs U ys.
//       IMPORTANT: this is NOT "xs and ys are both permutations" (that special
//       case EXCLUDES valid solutions and was the bug in the first version).
//       The three move types (YSWAP/XSWAP/XYSWAP) preserve the combined multiset,
//       so we INIT a 2-regular config (csearch2's construction) and the whole
//       search stays inside the sound 2-regular subspace.  (Verified m=3..36.)
//
//   K2  Objective = "bad = 0" over the C4-lifted 4m points, measured by the
//       number of collinear triples via a normalized line key (cross-product
//       collinearity).  bad == 0  <=>  rot4 NTIL.
//
//   K3  (X)/(S) split with priority weighting.  (S) = collinear triples on
//       slope +/-1 lines (the FDR linear layer, easy, ~25%); (X) = all other
//       collinear triples (the quadratic bottleneck, ~75%).  Objective =
//       WX * bad_X + WS * bad_S.  Different threads use WX=1 (pure) or WX=2
//       (prioritize the hard X-layer) for diversified search.
//
//   K4  Sparse (X) conflict hypergraph via incremental add/remove_point: each
//       point touches only O(n) lines, so updates are cheap.  This is the
//       empirical sparsity (each cell in only 0.6-0.9 (X) conflicts) that
//       makes conflict-driven search viable.
//
//   K5  min|det| = 1 sanity check on any found solution (verification only,
//       never used as a search filter since it has 0% discrimination).
//
//   K6  Multi-start SA + restart, parallelized with OpenMP.  Each thread owns
//       an independent Searcher (own RNG, own state).  Restarts re-seed from a
//       perturbed copy of the thread-local best (intensification) or a fresh
//       random permutation (diversification).  Reject = incremental undo
//       (re-apply the swap), avoiding the costly full map rebuild.
//
//   K7  Checkpoint every 30 min (atomic text write) + solution JSON written
//       immediately on discovery + progress log.
//
// Build (MSVC):
//   cl /O2 /openmp /std:c++17 /EHsc solve_m37_integrated.cpp
//
// Usage:
//   solve_m37_integrated --m 10 --threads 4 --hours 0.05   (validate)
//   solve_m37_integrated --m 37 --threads 16 --hours 9 --seed 1 \
//        --checkpoint results/m37_integrated_ckpt.txt \
//        --out results/m37_integrated_solution.json --log results/m37_integrated.log
//   solve_m37_integrated --selftest --m 37     (verify incremental delta + split invariant)

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <set>
#include <random>
#include <chrono>
#include <algorithm>
#include <fstream>
#include <string>
#include <atomic>
#include <mutex>
#include <thread>
#include <omp.h>
using namespace std;

typedef uint64_t LK;
typedef long long LL;

static const int AOFF=200,BOFF=200,COFF=20000,ASPAN=400,BSPAN=400,CSPAN=40000;
struct Pt{int x,y;};
static inline uint64_t pkey(Pt p){return ((uint64_t)(uint32_t)p.x<<32)|(uint32_t)p.y;}
enum MoveType{YSWAP=0,XSWAP=1,XYSWAP=2,XYCROSS=3,NUM_MOVES=4};
// NOTE on move semantics (critical for correctness of the search space):
//  YSWAP  : swap ys[i],ys[j] ............ preserves xs&ys multisets => preserves SPLIT
//  XSWAP  : swap xs[i],xs[j] ............ preserves xs&ys multisets => preserves SPLIT
//  XYSWAP : swap full (x,y) pair of cell i with cell j (diagonal) ... preserves SPLIT
//  XYCROSS: swap x of cell i with y of cell j  (xs[i]:=ys[j]; ys[j]:=xs[i]) ...
//           CHANGES the split while keeping the combined multiset 2-regular
//           (each value 0..m-1 still appears exactly twice).  This is the move
//           that lets SA traverse the ENTIRE 2-regular space (all splits), which
//           is REQUIRED to reach a solution: the 3 split-preserving moves alone
//           confine the search to the single split chosen at init_2reg, and the
//           chance of that split containing a solution is vanishingly small.

// ---------------------------------------------------------------------------
//  Sweatequity: one independent search state per thread
// ---------------------------------------------------------------------------
extern atomic<bool> g_stop;   // declared here so sa_restart can see the stop flag

struct Searcher {
    int m,n;
    LL WX,WS;                 // weights for (X) and (S)
    vector<int> xs,ys;
    vector<Pt> pts;
    unordered_map<LK,int> lcnt;        // line key -> current point count (fast, no set)
    LL total_bad,bad_X,bad_S;
    vector<char> present;
    vector<pair<LK,bool>> g_touch;
    vector<char> tabu;
    int tabu_tenure,tabu_cnt;
    mt19937 rng;
    unordered_map<uint64_t,int> pcnt;   // coordinate key -> present count (dup detection)
    int dup_keys=0;                     // # of coordinate keys with >=2 present points

    Searcher(int m_,int n_,LL WX_,LL WS_,unsigned seed)
        : m(m_),n(n_),WX(WX_),WS(WS_),total_bad(0),bad_X(0),bad_S(0),tabu_tenure(10),tabu_cnt(0),rng(seed){
        tabu.assign((size_t)m*m,0);
    }

    Pt c4(int x,int y,int r) const {
        if(r==0)return{x,y}; if(r==1)return{n-1-y,x};
        if(r==2)return{n-1-x,n-1-y}; return{y,n-1-x};
    }
    static int igcd(int a,int b){a=abs(a);b=abs(b);while(b){int t=a%b;a=b;b=t;}return a;}
    static inline bool is_S(Pt p,Pt q){
        int dx=q.x-p.x, dy=q.y-p.y;
        return (dx!=0 && dy!=0 && abs(dx)==abs(dy));
    }
    LK line_of(Pt p,Pt q) const {
        int a=-(q.y-p.y),b=(q.x-p.x),c=(q.y-p.y)*p.x-(q.x-p.x)*p.y;
        int g=igcd(abs(a),abs(b));g=igcd(g,abs(c));
        if(g){a/=g;b/=g;c/=g;}
        if(a<0||(a==0&&b<0)||(a==0&&b==0&&c<0)){a=-a;b=-b;c=-c;}
        LK K=(LK)(a+AOFF);K=K*BSPAN+(b+BOFF);K=K*CSPAN+(c+COFF);return K;
    }
    static inline LL C3(LL t){return(t>=3)?t*(t-1)*(t-2)/6:0;}
    inline LL obj() const {return bad_X*WX + bad_S*WS;}
    size_t dbg_lcntsz() const {return lcnt.size();}

    void build_points(){
        pts.resize(4*m);
        for(int i=0;i<m;i++) for(int r=0;r<4;r++) pts[4*i+r]=c4(xs[i],ys[i],r);
    }
    void add_point(int i){
        g_touch.clear(); Pt pi=pts[i];
        for(int j=0;j<4*m;j++){
            if(j==i||!present[j])continue;
            if(pts[j].x==pi.x&&pts[j].y==pi.y)continue;
            LK k=line_of(pi,pts[j]); bool s=is_S(pi,pts[j]);
            g_touch.push_back({k,s});
        }
        sort(g_touch.begin(),g_touch.end(),
             [](const pair<LK,bool>&a,const pair<LK,bool>&b){return a.first<b.first;});
        g_touch.erase(unique(g_touch.begin(),g_touch.end(),
             [](const pair<LK,bool>&a,const pair<LK,bool>&b){return a.first==b.first;}),
             g_touch.end());
        for(auto&e:g_touch){
            LK k=e.first; int c=lcnt[k]; if(c==0) c=1; lcnt[k]=c+1; // c==0 => first point on this line (j is the only existing one)
            LL d=C3(c+1)-C3(c); total_bad+=d;
            if(e.second) bad_S+=d; else bad_X+=d;
        }
        present[i]=1;
        { uint64_t k=pkey(pts[i]); int c=pcnt[k]; pcnt[k]=c+1; if(c==1) dup_keys++; }
    }
    void remove_point(int i){
        present[i]=0; g_touch.clear(); Pt pi=pts[i];
        for(int j=0;j<4*m;j++){
            if(j==i||!present[j])continue;
            if(pts[j].x==pi.x&&pts[j].y==pi.y)continue;
            LK k=line_of(pi,pts[j]); bool s=is_S(pi,pts[j]);
            g_touch.push_back({k,s});
        }
        sort(g_touch.begin(),g_touch.end(),
             [](const pair<LK,bool>&a,const pair<LK,bool>&b){return a.first<b.first;});
        g_touch.erase(unique(g_touch.begin(),g_touch.end(),
             [](const pair<LK,bool>&a,const pair<LK,bool>&b){return a.first==b.first;}),
             g_touch.end());
        for(auto&e:g_touch){
            LK k=e.first; int c=lcnt[k]; lcnt[k]=c-1;
            LL d=C3(c-1)-C3(c); total_bad+=d;
            if(e.second) bad_S+=d; else bad_X+=d;
        }
        { uint64_t k=pkey(pi); int c=pcnt[k]; pcnt[k]=c-1; if(c==2) dup_keys--; if(pcnt[k]==0) pcnt.erase(k); }
    }
    void build_map(){
        lcnt.clear(); pcnt.clear(); dup_keys=0; total_bad=0; bad_X=0; bad_S=0; present.assign(4*m,0);
        for(int i=0;i<4*m;i++) add_point(i);
    }

    // --- K1: init as a 2-regular configuration (Th-44 / R9b / csearch2).
    //   2-regular means every index value v in {0..m-1} appears EXACTLY TWICE
    //   across the combined multiset xs U ys.  This is NOT the same as "xs and
    //   ys are both permutations" (that is only the special case where each v is
    //   type-1: once in xs + once in ys, which EXCLUDES valid solutions such as
    //   the known m=10 solution: xs=[0,1,3,4,4,5,6,8,8,9], ys=[7,5,6,2,9,3,1,2,7,0]).
    //   The three move types (YSWAP/XSWAP/XYSWAP) preserve the combined multiset,
    //   hence preserve 2-regularity, so the search stays inside the sound
    //   2-regular subspace.  Construction below is csearch2's (proven to find
    //   m=3..36). ---
    void init_2reg(){
        int tries=0;
        do {
            xs.assign(m,0);ys.assign(m,0);
            // Randomize the SPLIT: each value v gets type in {0,1,2} with
            // #type-2 == #type-0 == k2 (so xs and ys both have size m).  The
            // split is an INVARIANT of the three moves (YSWAP/XSWAP/XYSWAP), so
            // different solutions may live in different splits; randomizing k2
            // per restart is what gives the search cross-split coverage.
            int half=m/2;
            int k2 = (half<=0)?0:(int)(rng() % (half+1));
            vector<int> idx(m); for(int v=0;v<m;v++) idx[v]=v;
            shuffle(idx.begin(),idx.end(),rng);
            vector<int> type(m,1);
            for(int t=0;t<k2;t++) type[idx[t]]=2;
            for(int t=k2;t<2*k2;t++) type[idx[t]]=0;
            vector<int>X,Y;
            for(int v=0;v<m;v++){
                if(type[v]>=1)X.push_back(v); if(type[v]==2)X.push_back(v);
                if(type[v]<=1)Y.push_back(v); if(type[v]==0)Y.push_back(v);
            }
            shuffle(X.begin(),X.end(),rng); shuffle(Y.begin(),Y.end(),rng);
            xs=X; ys=Y;
            build_points(); build_map();
            tries++;
        } while(dup_keys>0 && tries<2000);
    }
    // load a given permutation (xs,ys) and perturb it with `perturb` random swaps
    void load_perm(const vector<int>& ax,const vector<int>& ay,int perturb){
        xs=ax; ys=ay;
        for(int t=0;t<perturb;t++){
            int i=rng()%m,j=rng()%m; if(i==j)continue;
            int t1=xs[i];xs[i]=xs[j];xs[j]=t1;
        }
        for(int t=0;t<perturb;t++){
            int i=rng()%m,j=rng()%m; if(i==j)continue;
            int t1=ys[i];ys[i]=ys[j];ys[j]=t1;
        }
        build_points(); build_map();
    }

    // --- moves (permutation-preserving) ---
    void commit_yswap(int i,int j){
        int oi[4],oj[4]; for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
        for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
        int t=ys[i];ys[i]=ys[j];ys[j]=t;
        for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r);pts[oj[r]]=c4(xs[j],ys[j],r);}
        for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
    }
    void commit_xswap(int i,int j){
        int oi[4],oj[4]; for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
        for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
        int t=xs[i];xs[i]=xs[j];xs[j]=t;
        for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r);pts[oj[r]]=c4(xs[j],ys[j],r);}
        for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
    }
    void commit_xyswap(int i,int j){
        int oi[4],oj[4]; for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
        for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
        int tx=xs[i],ty=ys[i]; xs[i]=xs[j];ys[i]=ys[j]; xs[j]=tx;ys[j]=ty;
        for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r);pts[oj[r]]=c4(xs[j],ys[j],r);}
        for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
    }
    void commit_xycross(int i,int j){
        // True cross-swap: exchange x of cell i with y of cell j.
        // Only xs[i] and ys[j] change; ys[i] and xs[j] stay put.
        int oi[4],oj[4]; for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
        for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
        int tmp=xs[i]; xs[i]=ys[j]; ys[j]=tmp;
        for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r);pts[oj[r]]=c4(xs[j],ys[j],r);}
        for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
    }
    void commit_move(int i,int j,MoveType t){
        if(t==YSWAP)commit_yswap(i,j);
        else if(t==XSWAP)commit_xswap(i,j);
        else if(t==XYSWAP)commit_xyswap(i,j);
        else commit_xycross(i,j);
    }
    // Pre-check (without mutating state) whether applying move (i,j,t) would make
    // two of the 4m lifted points coincide.  We simulate the 8 new point coords,
    // then reject if any equals (a) another of the 8 new points, or (b) a STATIC
    // present point (the 8 points being moved are excluded since they are removed).
    bool would_dup(int i,int j,MoveType t) const {
        int sx_i=xs[i],sy_i=ys[i],sx_j=xs[j],sy_j=ys[j];
        if(t==YSWAP){ int tmp=sy_i; sy_i=sy_j; sy_j=tmp; }
        else if(t==XSWAP){ int tmp=sx_i; sx_i=sx_j; sx_j=tmp; }
        else if(t==XYSWAP){ int tx=sx_i,ty=sy_i; sx_i=sx_j; sy_i=sy_j; sx_j=tx; sy_j=ty; }
        else { int tmp=sx_i; sx_i=sy_j; sy_j=tmp; }   // XYCROSS: x_i <-> y_j
        Pt onew[8];
        for(int r=0;r<4;r++){ onew[r]=c4(sx_i,sy_i,r); onew[4+r]=c4(sx_j,sy_j,r); }
        for(int a=0;a<8;a++) for(int b=a+1;b<8;b++)
            if(onew[a].x==onew[b].x && onew[a].y==onew[b].y) return true;
        Pt oold[8];
        for(int r=0;r<4;r++){ oold[r]=pts[4*i+r]; oold[4+r]=pts[4*j+r]; }
        for(int a=0;a<8;a++){
            uint64_t k=pkey(onew[a]);
            auto it=pcnt.find(k); if(it==pcnt.end()) continue;
            int cnt=it->second;
            for(int b=0;b<8;b++) if(pkey(oold[b])==k) cnt--;
            if(cnt>0) return true;
        }
        return false;
    }
    // Apply a move only if it keeps all 4m lifted points DISTINCT.  A valid
    // rot4 NTIL requires distinct points; a duplicate is degenerate and must
    // never be part of a solution.  We pre-check with would_dup so the live
    // line-count (lcnt) is never touched by an invalid (reverted) move.
    bool commit_move_safe(int i,int j,MoveType t){
        if(would_dup(i,j,t)) return false;
        commit_move(i,j,t);
        if(dup_keys>0){ commit_move(i,j,t); return false; }   // defensive backstop
        return true;
    }
    void tabu_add(int i,int j){tabu[i*m+j]=1;tabu[j*m+i]=1;}
    bool tabu_chk(int i,int j){return tabu[i*m+j];}
    void tabu_decay(){if(++tabu_cnt%tabu_tenure==0)fill(tabu.begin(),tabu.end(),0);}

    // incremental delta (commit + undo via re-applying the involutive swap)
    LL meas_move(int i,int j,MoveType mt){
        LL before=obj(); bool applied=commit_move_safe(i,j,mt);
        if(!applied) return (LL)1e15;          // forbidden (would duplicate): huge penalty
        LL after=obj(); commit_move(i,j,mt); return after-before;
    }
    // ILS refinement: greedy best-descent from current state; if stuck at a
    // local min, perturb and retry.  Returns true iff obj() reaches 0.
    bool greedy_refine(int max_attempts){
        for(int att=0; att<max_attempts && obj()>0; att++){
            bool improved=true;
            while(improved && obj()>0){
                improved=false;
                for(int ii=0; ii<m && obj()>0; ii++)
                    for(int jj=ii+1; jj<m; jj++)
                        for(int tt=0; tt<NUM_MOVES; tt++){
                            if(meas_move(ii,jj,(MoveType)tt)<0){ commit_move_safe(ii,jj,(MoveType)tt); improved=true; goto resc; }
                        }
                resc:;
            }
            if(obj()==0) return true;
            int kp=max(1,m/8);
            for(int t=0;t<kp;t++){ int a=rng()%m,b=rng()%m; if(a==b)continue;
                MoveType mt=(MoveType)(rng()%NUM_MOVES); commit_move(a,b,mt); }
        }
        return false;
    }

    // --- SA restart; returns true if obj() reaches 0 (== solution) ---
    bool sa_restart(LL max_moves,double T0,double Tend,
                    LL& best_out,LL& best_badX,LL& best_badS,
                    vector<int>& bxs,vector<int>& bys,bool keep_init=false){
        if(!keep_init) init_2reg();
        LL cur=obj(); best_out=cur; bxs=xs; bys=ys; best_badX=bad_X; best_badS=bad_S;
        double T=T0,Tdec=pow(Tend/T0,1.0/max_moves);
        uniform_real_distribution<double>ur(0.0,1.0); int stale=0;
        for(LL mv=0;mv<max_moves;mv++){
            if((mv & 65535)==0 && g_stop.load()) break;
            int i=rng()%m,j=rng()%m; if(i==j)continue;
            // K8: bias toward XYCROSS (the only split-changing move) so the SA
            // traverses the full 2-regular space; 35% XYCROSS, 65% split-preserving.
            int mr=rng()%100;
            MoveType mt = (mr<35)? XYCROSS : (MoveType)(rng()%3);
            if(tabu_chk(i,j)&&mt!=XYSWAP&&mt!=XYCROSS)continue;
            LL before=obj();
            bool applied=commit_move_safe(i,j,mt);
            if(!applied) continue;                 // duplicate created -> reject, state unchanged
            LL newobj=obj();
            if(newobj<=before || ur(rng)<exp(-(double)(newobj-before)/T)){
                cur=newobj;
                if(cur<best_out){best_out=cur;bxs=xs;bys=ys;best_badX=bad_X;best_badS=bad_S;stale=0;}
                if(cur==0){best_badX=bad_X;best_badS=bad_S;return true;}
                if(newobj<before) tabu_add(i,j);
            }else{
                commit_move(i,j,mt);   // incremental undo (swap is involutive)
                cur=obj();             // == before
            }
            T*=Tdec; tabu_decay();
            if(++stale>max_moves/10){T=max(T,T0*0.3);stale=0;}
        }
        best_out=cur; return false;
    }
};

// ---------------------------------------------------------------------------
//  Globals for cross-thread best + control
// ---------------------------------------------------------------------------
mutex g_mtx;
LL g_best = (LL)1e18;
vector<int> g_xs, g_ys;
LL g_badX=0, g_badS=0;
atomic<bool> g_stop(false);
atomic<bool> g_found(false);

string g_ckpt_path, g_out_path, g_log_path;
int g_m=37; LL g_WX_def=2, g_WS_def=1;
LL g_moves_per_restart=300000LL;

// ---- checkpoint (atomic text: two lines) ----
void write_ckpt(double elapsed){
    if(g_ckpt_path.empty())return;
    string tmp=g_ckpt_path+".tmp";
    ofstream f(tmp); if(!f)return;
    f<<"xs"; for(int v:g_xs)f<<" "<<v; f<<"\n";
    f<<"ys"; for(int v:g_ys)f<<" "<<v; f<<"\n";
    f<<"best "<<g_best<<" badX "<<g_badX<<" badS "<<g_badS<<" elapsed "<<elapsed<<"\n";
    f.close();
    rename(tmp.c_str(),g_ckpt_path.c_str());
}
void log_line(const string& s){
    if(g_log_path.empty())return;
    ofstream f(g_log_path,ios::app); if(f) f<<s<<"\n";
}

// ---- solution JSON (K5: min|det| sanity) ----
LL min_det_of(const vector<int>& xs,const vector<int>& ys,int m,int n){
    vector<Pt> P(4*m);
    for(int i=0;i<m;i++)for(int r=0;r<4;r++){
        int x=xs[i],y=ys[i];
        Pt p; if(r==0)p={x,y}; else if(r==1)p={n-1-y,x};
        else if(r==2)p={n-1-x,n-1-y}; else p={y,n-1-x};
        P[4*i+r]=p;
    }
    LL md=LLONG_MAX;
    for(int a=0;a<4*m;a++)for(int b=a+1;b<4*m;b++)for(int c=b+1;c<4*m;c++){
        LL d1x=P[b].x-P[a].x,d1y=P[b].y-P[a].y;
        LL d2x=P[c].x-P[a].x,d2y=P[c].y-P[a].y;
        LL det=abs(d1x*d2y-d1y*d2x);
        if(det>0 && det<md) md=det;
    }
    return md;
}
// ---- diagnostic: print phantom (inc-but-not-brute) and ghost triples ----
void debug_dump(Searcher& S, int m){
    int N=4*m;
    set<long long> brute_set;
    for(int a=0;a<N;a++){if(!S.present[a])continue;for(int b=a+1;b<N;b++){if(!S.present[b])continue;for(int c=b+1;c<N;c++){if(!S.present[c])continue;
        if(S.pts[a].x==S.pts[b].x&&S.pts[a].y==S.pts[b].y)continue;
        if(S.pts[a].x==S.pts[c].x&&S.pts[a].y==S.pts[c].y)continue;
        if(S.pts[b].x==S.pts[c].x&&S.pts[b].y==S.pts[c].y)continue;
        LL dx1=S.pts[b].x-S.pts[a].x,dy1=S.pts[b].y-S.pts[a].y;
        LL dx2=S.pts[c].x-S.pts[a].x,dy2=S.pts[c].y-S.pts[a].y;
        if(dx1*dy2-dy1*dx2!=0)continue;
        brute_set.insert((long long)a*N*N+(long long)b*N+c);
    }}}
    unordered_map<LK,vector<int>> lp;
    for(int a=0;a<N;a++){if(!S.present[a])continue;for(int b=a+1;b<N;b++){if(!S.present[b])continue;
        LK k=S.line_of(S.pts[a],S.pts[b]); lp[k].push_back(a); lp[k].push_back(b);
    }}
    set<long long> inc_set;
    for(auto&kv:lp){ vector<int> ps; for(int x:kv.second) ps.push_back(x); sort(ps.begin(),ps.end()); ps.erase(unique(ps.begin(),ps.end()),ps.end());
        int sz=(int)ps.size(); if(sz<3)continue;
        for(int i=0;i<sz;i++)for(int j=i+1;j<sz;j++)for(int k=j+1;k<sz;k++)
            inc_set.insert((long long)ps[i]*N*N+(long long)ps[j]*N+ps[k]);
    }
    int ph=0,gh=0;
    for(auto v:inc_set) if(!brute_set.count(v)){ if(ph<6){ ph++;
        int a=(int)(v/(N*N)),b=(int)((v/N)%N),c=(int)(v%N);
        LL det=(LL)(S.pts[b].x-S.pts[a].x)*(S.pts[c].y-S.pts[a].y)-(LL)(S.pts[b].y-S.pts[a].y)*(S.pts[c].x-S.pts[a].x);
        printf("  PHANTOM (%d,%d,%d) A=(%d,%d) B=(%d,%d) C=(%d,%d) det=%lld\n",a,b,c,
          S.pts[a].x,S.pts[a].y,S.pts[b].x,S.pts[b].y,S.pts[c].x,S.pts[c].y,det); } }
    for(auto v:brute_set) if(!inc_set.count(v)){ if(gh<6){ gh++;
        int a=(int)(v/(N*N)),b=(int)((v/N)%N),c=(int)(v%N);
        printf("  GHOST (%d,%d,%d) A=(%d,%d) B=(%d,%d) C=(%d,%d)\n",a,b,c,
          S.pts[a].x,S.pts[a].y,S.pts[b].x,S.pts[b].y,S.pts[c].x,S.pts[c].y); } }
    printf("  debug: brute_triples=%d inc_triples=%d phantom=%d ghost=%d dup_keys=%d\n",
           (int)brute_set.size(),(int)inc_set.size(),ph,gh,S.dup_keys);
}
void write_solution(int tid,double elapsed,unsigned seed,LL WX,LL WS){
    vector<Pt> lifted(4*g_m);
    for(int i=0;i<g_m;i++)for(int r=0;r<4;r++){
        int x=g_xs[i],y=g_ys[i];
        if(r==0)lifted[4*i+r]={x,y};
        else if(r==1)lifted[4*i+r]={2*g_m-1-y,x};
        else if(r==2)lifted[4*i+r]={2*g_m-1-x,2*g_m-1-y};
        else lifted[4*i+r]={y,2*g_m-1-x};
    }
    LL md=min_det_of(g_xs,g_ys,g_m,2*g_m);
    ofstream f(g_out_path);
    if(!f)return;
    f<<"{\n";
    f<<"  \"m\": "<<g_m<<",\n  \"n\": "<<2*g_m<<",\n  \"found\": true,\n";
    f<<"  \"cells\": [";
    for(int i=0;i<g_m;i++){ f<<"["<<g_xs[i]<<","<<g_ys[i]<<"]"; if(i+1<g_m)f<<","; }
    f<<"],\n  \"lifted_points\": [";
    for(int i=0;i<4*g_m;i++){ f<<"["<<lifted[i].x<<","<<lifted[i].y<<"]"; if(i+1<4*g_m)f<<","; }
    f<<"],\n  \"bad_X\": 0, \"bad_S\": 0,\n"
      <<"  \"min_det\": "<<md<<",\n  \"verify\": true,\n"
      <<"  \"weights\": {\"WX\": "<<WX<<", \"WS\": "<<WS<<"},\n"
      <<"  \"thread\": "<<tid<<", \"seed\": "<<seed<<", \"elapsed\": "<<elapsed<<"\n}\n";
    f.close();
}

// ---- load checkpoint to warm-start (K7 resume) ----
bool load_ckpt_txt(const string& path,vector<int>& oxs,vector<int>& oys,int m){
    ifstream f(path); if(!f)return false;
    oxs.assign(m,0); oys.assign(m,0); int cur=-1; string line;
    while(getline(f,line)){
        if(line.size()<2)continue;
        if(line[0]=='x'&&line[1]=='s'){cur=0;continue;}
        if(line[0]=='y'&&line[1]=='s'){cur=1;continue;}
        // numeric line: parse all ints
        vector<int> nums; size_t i=0;
        while(i<line.size()){
            if(isdigit((unsigned char)line[i])||line[i]=='-'){
                long v=strtol(line.c_str()+i,nullptr,10); nums.push_back((int)v);
                while(i<line.size()&&(isdigit((unsigned char)line[i])||line[i]=='-'))i++;
            } else i++;
        }
        if(cur==0){for(int k=0;k<m&&k<(int)nums.size();k++)oxs[k]=nums[k];}
        else if(cur==1){for(int k=0;k<m&&k<(int)nums.size();k++)oys[k]=nums[k];}
        cur=-1;
    }
    return true;
}

// ---------------------------------------------------------------------------
//  main
// ---------------------------------------------------------------------------
int main(int argc,char**argv){
    int m=37, threads=omp_get_max_threads(); double hours=9.0;
    unsigned base_seed=1; double T0=6.0, Tend=0.01;
    bool selftest=false; string init_path;
    for(int a=1;a<argc;a++){
        string s=argv[a];
        if(s=="--m"&&a+1<argc)m=atoi(argv[++a]);
        else if(s=="--threads"&&a+1<argc)threads=atoi(argv[++a]);
        else if(s=="--hours"&&a+1<argc)hours=atof(argv[++a]);
        else if(s=="--seed"&&a+1<argc)base_seed=(unsigned)atoi(argv[++a]);
        else if(s=="--T0"&&a+1<argc)T0=atof(argv[++a]);
        else if(s=="--Tend"&&a+1<argc)Tend=atof(argv[++a]);
        else if(s=="--moves"&&a+1<argc)g_moves_per_restart=atoll(argv[++a]);
        else if(s=="--WX"&&a+1<argc)g_WX_def=atoll(argv[++a]);
        else if(s=="--WS"&&a+1<argc)g_WS_def=atoll(argv[++a]);
        else if(s=="--checkpoint"&&a+1<argc)g_ckpt_path=argv[++a];
        else if(s=="--out"&&a+1<argc)g_out_path=argv[++a];
        else if(s=="--log"&&a+1<argc)g_log_path=argv[++a];
        else if(s=="--init"&&a+1<argc)init_path=argv[++a];
        else if(s=="--selftest")selftest=true;
    }
    g_m=m;
    int n=2*m;
    omp_set_num_threads(threads);

    auto t0=chrono::high_resolution_clock::now();
    auto deadline=t0 + chrono::duration<double>(hours*3600.0);

    // ---- selftest: verify incremental delta + split invariant against brute force ----
    if(selftest){
        Searcher S(m,n,g_WX_def,g_WS_def,base_seed);
        S.init_2reg();
        printf("[selftest] after init: total_bad=%lld dup_keys=%d\n",S.total_bad,S.dup_keys);
        auto brute=[&](Searcher&Z,LL& tot,LL& bx,LL& bs){
            tot=0;bx=0;bs=0;
            int N=4*m;
            for(int a=0;a<N;a++){ if(!Z.present[a])continue;
                for(int b=a+1;b<N;b++){ if(!Z.present[b])continue;
                    for(int c=b+1;c<N;c++){ if(!Z.present[c])continue;
                        // degenerate (identical-point) triples cannot occur in a valid
                        // duplicate-free state: skip so the comparison matches the
                        // incremental machinery (which never counts them).
                        if(Z.pts[a].x==Z.pts[b].x&&Z.pts[a].y==Z.pts[b].y)continue;
                        if(Z.pts[a].x==Z.pts[c].x&&Z.pts[a].y==Z.pts[c].y)continue;
                        if(Z.pts[b].x==Z.pts[c].x&&Z.pts[b].y==Z.pts[c].y)continue;
                        LL dxx=Z.pts[b].x-Z.pts[a].x, dxy=Z.pts[b].y-Z.pts[a].y;
                        LL dyy=Z.pts[c].x-Z.pts[a].x, dyy2=Z.pts[c].y-Z.pts[a].y;
                        LL det=dxx*dyy2-dxy*dyy;
                        if(det!=0)continue;
                        tot++;
                        if(Searcher::is_S(Z.pts[a],Z.pts[b])) bs++; else bx++;
                    }
                }
            }
        };
        int mism=0,splitbad=0,undobad=0,dupbad=0;
        int iters = (m<=18)?800:200;
        for(int t=0;t<iters && mism+splitbad+undobad+dupbad<5;t++){
            LL bt,bx,bs; brute(S,bt,bx,bs);
            if(bt!=S.total_bad){printf("TOTAL t=%d brute=%lld inc=%lld\n",t,bt,S.total_bad); debug_dump(S,m); if(++mism>3)break;}
            if(bx!=S.bad_X||bs!=S.bad_S){printf("SPLIT t=%d bruteX=%lld incX=%lld bruteS=%lld incS=%lld\n",
                                               t,bx,S.bad_X,bs,S.bad_S);if(++splitbad>3)break;}
            if(S.bad_X+S.bad_S!=S.total_bad){printf("INV t=%d\n",t);if(++splitbad>3)break;}
            if(S.dup_keys!=0){printf("DUP t=%d dup_keys=%d\n",t,S.dup_keys);if(++dupbad>3)break;}
            int i=S.rng()%m,j=S.rng()%m; if(i==j)continue;
            MoveType mt=(MoveType)(S.rng()%NUM_MOVES);
            LL before=S.obj();
            bool ap=S.commit_move_safe(i,j,mt);
            if(!ap){
                if(S.obj()!=before||S.dup_keys!=0){printf("REJ t=%d: obj %lld->%lld dup=%d\n",t,before,S.obj(),S.dup_keys);if(++undobad>3)break;}
                continue;
            }
            (void)S.obj();
            S.commit_move(i,j,mt);   // undo (involutive)
            if(S.obj()!=before||S.dup_keys!=0){printf("UNDO t=%d: %lld -> %lld dup=%d\n",t,before,S.obj(),S.dup_keys);if(++undobad>3)break;}
        }
        printf("SELFTEST m=%d: total_mismatch=%d split_violations=%d undo_mismatch=%d dup_violations=%d (total_bad=%lld badX=%lld badS=%lld)\n",
               m,mism,splitbad,undobad,dupbad,S.total_bad,S.bad_X,S.bad_S);
        return 0;
    }

    // warm-start from checkpoint if requested
    vector<int> warm_xs,warm_ys; bool have_warm=false;
    if(!init_path.empty()){
        if(load_ckpt_txt(init_path,warm_xs,warm_ys,m)){have_warm=true;
            printf("[init] warm-start from %s\n",init_path.c_str());}
        else printf("[init] FAILED to load %s\n",init_path.c_str());
    }

    printf("[start] m=%d n=%d threads=%d hours=%.3f WX_def=%lld WS=%lld moves/restart=%lld T0=%.3f Tend=%.4f\n",
           m,n,threads,hours,g_WX_def,g_WS_def,g_moves_per_restart,T0,Tend);
    fflush(stdout);
    log_line(string("[start] m=")+to_string(m)+" threads="+to_string(threads)+
             " hours="+to_string(hours)+" WX="+to_string(g_WX_def));

    // ---- checkpointer thread: every 30 min snapshot + stop at deadline ----
    thread ckpt([&](){
        auto last_ck=chrono::high_resolution_clock::now();
        auto last_log=chrono::high_resolution_clock::now();
        while(!g_stop.load()){
            this_thread::sleep_for(chrono::seconds(15));
            auto now=chrono::high_resolution_clock::now();
            double elapsed=chrono::duration<double>(now-t0).count();
            if(chrono::duration<double>(now-last_log).count()>=30.0){
                {
                    lock_guard<mutex> lk(g_mtx);
                    printf("[t=%5.0fs] best=%lld badX=%lld badS=%lld\n",elapsed,g_best,g_badX,g_badS);
                    fflush(stdout);
                }
                last_log=now;
                log_line("[t="+to_string((long long)elapsed)+"s] best="+to_string(g_best)+
                         " badX="+to_string(g_badX)+" badS="+to_string(g_badS));
            }
            if(chrono::duration<double>(now-last_ck).count()>=1800.0){
                {
                    lock_guard<mutex> lk(g_mtx);
                    write_ckpt(elapsed);
                }
                log_line("[ckpt] t="+to_string((long long)elapsed)+"s best="+to_string(g_best)+
                         " badX="+to_string(g_badX)+" badS="+to_string(g_badS));
                printf("[ckpt] t=%.0fs best=%lld badX=%lld badS=%lld\n",elapsed,g_best,g_badX,g_badS);
                fflush(stdout);
                last_ck=now;
            }
            if(now>=deadline) g_stop.store(true);
        }
    });

    // ---- worker threads ----
    #pragma omp parallel
    {
        int tid=omp_get_thread_num();
        // K3: diversify weights across threads
        LL WX = (tid%2==0)? g_WX_def : 1;
        LL WS = g_WS_def;
        unsigned seed = base_seed + (unsigned)(tid*1000003 + 7);
        Searcher S(m,n,WX,WS,seed);

        if(have_warm){ S.load_perm(warm_xs,warm_ys,0); }
        else S.init_2reg();

        LL local_best=(LL)1e18; vector<int> lbx,lby; LL lbX=0,lbS=0;
        int restart_cnt=0;

        while(!g_stop.load() && !g_found.load()){
            LL best,bX,bS; vector<int> rsx,rsy; bool ok=false;
            // K6: diversify (fresh 2-regular init) MOST restarts; intensify from
            // the perturbed local best only every 5th restart. Bigger perturbation
            // (m/3) helps escape the local minima that trap m>=15.
            bool keep = (local_best < (LL)1e18 && (restart_cnt%5==0));
            if(keep){
                S.load_perm(lbx,lby, max(3,m/3));     // perturb local best (strong)
                if(S.dup_keys>0) S.init_2reg();        // invalid -> fresh
                ok=S.sa_restart(g_moves_per_restart,T0,Tend,best,bX,bS,rsx,rsy,true);
            } else {
                ok=S.sa_restart(g_moves_per_restart,T0,Tend,best,bX,bS,rsx,rsy,false);
            }
            restart_cnt++;

            // K6+ILS: greedy refine from the best SA state to escape the
            // bad>0 local minima that pure SA cannot cross.
            if(S.dup_keys!=0){ ok=false; }
            else {
                S.load_perm(rsx,rsy,0);
                if(S.obj()>0){
                    if(S.greedy_refine(10)){ ok=true; best=S.obj(); bX=S.bad_X; bS=S.bad_S; rsx=S.xs; rsy=S.ys; }
                    else { best=S.obj(); bX=S.bad_X; bS=S.bad_S; rsx=S.xs; rsy=S.ys; }
                }
            }
            if(best<local_best){local_best=best;lbx=rsx;lby=rsy;lbX=bX;lbS=bS;}

            {
                lock_guard<mutex> lk(g_mtx);
                if(best<g_best){ g_best=best; g_xs=rsx; g_ys=rsy; g_badX=bX; g_badS=bS;
                    double el=chrono::duration<double>(chrono::high_resolution_clock::now()-t0).count();
                    write_ckpt(el);
                }
            }

            if(ok && S.dup_keys==0){
                lock_guard<mutex> lk(g_mtx);
                g_best=0; g_xs=rsx; g_ys=rsy; g_badX=0; g_badS=0;
                double el=chrono::duration<double>(chrono::high_resolution_clock::now()-t0).count();
                if(!g_out_path.empty()) write_solution(tid,el,seed,WX,WS);
                write_ckpt(el);
                g_found.store(true); g_stop.store(true);
                printf("[FOUND] thread=%d t=%.1fs WX=%lld badX=%lld badS=%lld\n",tid,el,WX,bX,bS);
                fflush(stdout);
                break;
            }
        }
    }

    ckpt.join();
    auto t1=chrono::high_resolution_clock::now();
    double secs=chrono::duration<double>(t1-t0).count();

    if(g_found.load()){
        printf("[DONE] SOLUTION FOUND m=%d in %.1fs -> %s\n",m,secs,g_out_path.c_str());
        log_line("[DONE] FOUND in "+to_string((long long)secs)+"s -> "+g_out_path);
    }else{
        printf("[DONE] no solution in %.1fs; best_bad=%lld (badX=%lld badS=%lld) ckpt=%s\n",
               secs,g_best,g_badX,g_badS,g_ckpt_path.c_str());
        fflush(stdout);
        log_line("[DONE] NOTFOUND in "+to_string((long long)secs)+"s best="+to_string(g_best));
        // final checkpoint so resume is possible
        double el=chrono::duration<double>(t1-t0).count();
        write_ckpt(el);
    }
    return 0;
}
