#include <cstdio>
#include <cstdlib>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <random>
#include <algorithm>
using namespace std;

int m=10,n=20;
vector<int> xs,ys;
struct Pt{int x,y;};
vector<Pt> pts;
unordered_map<uint64_t,unordered_set<int>> lpts;
long long total_bad;
vector<char> present;
vector<uint64_t> g_touch;
mt19937 rng(1);

uint64_t line_of(Pt p,Pt q){
    int a=-(q.y-p.y),b=(q.x-p.x),c=(q.y-p.y)*p.x-(q.x-p.x)*p.y;
    auto igcd=[](int a,int b){a=abs(a);b=abs(b);while(b){int t=a%b;a=b;b=t;}return a;};
    int g=igcd(abs(a),abs(b));g=igcd(g,abs(c));
    if(g){a/=g;b/=g;c/=g;}
    if(a<0||(a==0&&b<0)||(a==0&&b==0&&c<0)){a=-a;b=-b;c=-c;}
    uint64_t K=(uint64_t)(a+200);K=K*400+(b+200);K=K*40000+(c+20000);return K;
}
long long C3(long long t){return(t>=3)?t*(t-1)*(t-2)/6:0;}

Pt c4(int x,int y,int r){if(r==0)return{x,y};if(r==1)return{n-1-y,x};if(r==2)return{n-1-x,n-1-y};return{y,n-1-x};}

void build_points(){
    pts.resize(4*m);
    for(int i=0;i<m;i++)for(int r=0;r<4;r++)pts[4*i+r]=c4(xs[i],ys[i],r);
}

void add_point(int i){
    g_touch.clear();Pt pi=pts[i];
    for(int j=0;j<4*m;j++){
        if(j==i||!present[j])continue;
        if(pts[j].x==pi.x&&pts[j].y==pi.y)continue;
        uint64_t k=line_of(pi,pts[j]);lpts[k].insert(j);g_touch.push_back(k);
    }
    sort(g_touch.begin(),g_touch.end());g_touch.erase(unique(g_touch.begin(),g_touch.end()),g_touch.end());
    for(uint64_t k:g_touch){auto&s=lpts[k];long long o=(long long)s.size();s.insert(i);total_bad+=C3(o+1)-C3(o);}
    present[i]=1;
}

void remove_point(int i){
    present[i]=0;g_touch.clear();Pt pi=pts[i];
    for(int j=0;j<4*m;j++){
        if(j==i||!present[j])continue;
        if(pts[j].x==pi.x&&pts[j].y==pi.y)continue;
        g_touch.push_back(line_of(pi,pts[j]));
    }
    sort(g_touch.begin(),g_touch.end());g_touch.erase(unique(g_touch.begin(),g_touch.end()),g_touch.end());
    for(uint64_t k:g_touch){auto it=lpts.find(k);if(it==lpts.end())continue;auto&s=it->second;
        long long c=(long long)s.size();s.erase(i);total_bad+=C3(c-1)-C3(c);if(s.size()<2)lpts.erase(it);}
}

void build_map(){lpts.clear();total_bad=0;present.assign(4*m,0);for(int i=0;i<4*m;i++)add_point(i);}

void init_random(){
    xs.assign(m,0);ys.assign(m,0);
    vector<int>type(m,1);int conv=m*0.35;
    for(int t=0;t<conv;t++){int a=rng()%m,b=rng()%m;if(type[a]==1&&type[b]==1){type[a]=2;type[b]=0;}}
    vector<int>X,Y;
    for(int v=0;v<m;v++){if(type[v]>=1)X.push_back(v);if(type[v]==2)X.push_back(v);if(type[v]<=1)Y.push_back(v);if(type[v]==0)Y.push_back(v);}
    shuffle(X.begin(),X.end(),rng);shuffle(Y.begin(),Y.end(),rng);xs=X;ys=Y;
    build_points();build_map();
    printf("init: xs=%d ys=%d pts=%d present=%d total_bad=%lld\n",(int)xs.size(),(int)ys.size(),(int)pts.size(),(int)present.size(),total_bad);
}

// YSWAP only
void commit_yswap(int i,int j){
    int oi[4],oj[4];for(int r=0;r<4;r++){oi[r]=4*i+r;oj[r]=4*j+r;}
    printf("commit_yswap i=%d j=%d oi0=%d oj0=%d (max=%d)\n",i,j,oi[0],oj[0],4*m-1);
    fflush(stdout);
    for(int r=0;r<4;r++){remove_point(oi[r]);remove_point(oj[r]);}
    int t=ys[i];ys[i]=ys[j];ys[j]=t;
    for(int r=0;r<4;r++){pts[oi[r]]=c4(xs[i],ys[i],r);pts[oj[r]]=c4(xs[j],ys[j],r);}
    for(int r=0;r<4;r++){add_point(oi[r]);add_point(oj[r]);}
}

int main(){
    n=2*m;
    init_random();
    for(int t=0;t<5;t++){
        int i=rng()%m,j=rng()%m;if(i==j)continue;
        printf("--- iter %d i=%d j=%d ---\n",t,i,j);
        commit_yswap(i,j);
        printf("total_bad=%lld\n",total_bad);
        // undo
        commit_yswap(i,j);
        printf("total_bad after undo=%lld\n",total_bad);
    }
    printf("done\n");
    return 0;
}
