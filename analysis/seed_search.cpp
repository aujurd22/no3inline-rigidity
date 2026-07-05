#include <iostream>
#include <vector>
#include <set>
#include <algorithm>
#include <random>
#include <chrono>
#include <unordered_set>

using namespace std;

struct Point { int x,y; };
struct Phash { size_t operator()(const Point& p) const { return p.x*3137+p.y; } };
bool operator==(const Point& a, const Point& b) { return a.x==b.x && a.y==b.y; }

int N;
bool collinear(const Point& a, const Point& b, const Point& c) {
    return (b.x-a.x)*(c.y-a.y) == (c.x-a.x)*(b.y-a.y);
}
bool is_no3(const vector<Point>& pts) {
    for (size_t i=0;i<pts.size();i++)
        for (size_t j=i+1;j<pts.size();j++)
            for (size_t k=j+1;k<pts.size();k++)
                if (collinear(pts[i],pts[j],pts[k])) return false;
    return true;
}
bool is_maximal(const vector<Point>& pts) {
    unordered_set<Point,Phash> ps(pts.begin(),pts.end());
    for (int i=0;i<N;i++) for (int j=0;j<N;j++) {
        Point p{i,j};
        if (ps.count(p)) continue;
        bool ok=false;
        for (size_t a=0;a<pts.size()&&!ok;a++)
            for (size_t b=a+1;b<pts.size()&&!ok;b++)
                if (collinear(pts[a],pts[b],p)) ok=true;
        if (!ok) return false;
    }
    return true;
}
int dom_score(const vector<Point>& pts) {
    unordered_set<Point,Phash> ps(pts.begin(),pts.end());
    int s=0;
    for (int i=0;i<N;i++) for (int j=0;j<N;j++) {
        Point p{i,j};
        if (ps.count(p)) continue;
        for (size_t a=0;a<pts.size();a++) {
            for (size_t b=a+1;b<pts.size();b++)
                if (collinear(pts[a],pts[b],p)) { s++; goto next; }
        } next:;
    }
    return s;
}

int main(int argc, char* argv[]) {
    N=atoi(argv[1]); int k=atoi(argv[2]); int trials=atoi(argv[3]); int seed=atoi(argv[4]);
    
    // Seed solutions for n=13
    vector<vector<Point>> seeds;
    seeds.push_back({{6,3},{4,4},{9,8},{6,9},{0,5},{4,8},{7,9},{5,6},{9,3},{5,5},{0,1},{2,4},{7,6}});
    seeds.push_back({{6,4},{3,7},{12,7},{12,1},{6,10},{0,11},{3,1},{9,10},{9,4},{10,11},{7,0},{0,0},{1,3}});
    
    mt19937 rng(seed);
    vector<Point> all_pts;
    for (int i=0;i<N;i++) for (int j=0;j<N;j++) all_pts.push_back({i,j});
    
    int total_ext = N*N - k;
    int found=0, found_missing=0;
    auto start = chrono::steady_clock::now();
    
    for (int trial=0; trial<trials; trial++) {
        if (trial%1000==0&&trial>0) {
            auto now=chrono::steady_clock::now();
            cerr << "  trial " << trial << "/" << trials << " found=" << found << " " 
                 << chrono::duration<double>(now-start).count() << "s" << endl;
        }
        
        // Start from a seed solution, remove 1 point
        vector<Point> cand = seeds[trial % seeds.size()];
        Point removed = cand[rng() % cand.size()];
        cand.erase(find(cand.begin(),cand.end(),removed));
        
        // Now k should be 12... but we removed 1 from 13, so cand.size() = 12
        if ((int)cand.size() != k) continue;
        
        // Hill-climb on the 12-point set
        int best = dom_score(cand);
        for (int iter=0; iter<200; iter++) {
            bool imp=false;
            for (int pi=0; pi<k && !imp; pi++) {
                for (int ri=0; ri<100; ri++) {
                    Point p_in = all_pts[rng()%all_pts.size()];
                    if (find(cand.begin(),cand.end(),p_in)!=cand.end()) continue;
                    Point old=cand[pi]; cand[pi]=p_in;
                    if (!is_no3(cand)) { cand[pi]=old; continue; }
                    int sc=dom_score(cand);
                    if (sc>best) { best=sc; imp=true; break; }
                    else cand[pi]=old;
                }
            }
            if (!imp) break;
        }
        
        if (best>=total_ext && is_maximal(cand)) {
            found++;
            double cx=(N-1)/2.0,cy=(N-1)/2.0;
            vector<int> d2s;
            for (auto& p:cand) d2s.push_back((int)round((p.x-cx)*(p.x-cx)+(p.y-cy)*(p.y-cy)));
            sort(d2s.begin(),d2s.end());
            int mp=0,i=0;
            while(i<(int)d2s.size()){int j=i;while(j<(int)d2s.size()&&d2s[j]==d2s[i])j++;mp=max(mp,j-i);i=j;}
            bool miss=(mp<3);
            if(miss) found_missing++;
            cout<<"FOUND "<<found<<": {";
            for(auto& p:cand) cout<<"("<<p.x<<","<<p.y<<")";
            cout<<"} missing="<<(miss?"YES":"NO")<<endl;
        }
    }
    
    cout<<"\nRESULTS n="<<N<<" k="<<k<<" trials="<<trials<<": found="<<found;
    if(found) cout<<" missing="<<found_missing<<"/"<<found<<"="<<100.0*found_missing/found<<"%";
    cout<<" time="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"s"<<endl;
}
