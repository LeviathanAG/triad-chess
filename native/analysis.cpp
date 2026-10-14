// Team-written algorithmic analysis, created during the 2026 event with Codex.
// Only board operations/legal moves come from the attributed MIT rules library.
// Evaluation ports our own Python formula; no engine search/evaluation is copied.
#include "vendor/chess.hpp"
#include <algorithm>
#include <chrono>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace chess;
using Clock = std::chrono::steady_clock;
constexpr int MATE = 100000;
constexpr int VALUE[7] = {100,320,330,500,900,0,0};
struct Expired {};
struct Result { int score; std::vector<Move> line; };
struct Row { Move move; int score; bool upper; std::vector<Move> line; };

int evaluate(const Board& b) {
    int nonpawn=0,score=0;
    for(int s=0;s<64;++s) {
        Piece p=b.at(Square(s));
        if(p!=Piece::NONE && p.type()!=PieceType::PAWN && p.type()!=PieceType::KING)
            nonpawn+=VALUE[int(p.type())];
    }
    for(Color colour : {Color::WHITE,Color::BLACK}) {
        int subtotal=0,bishops=0;
        for(int s=0;s<64;++s) {
            Piece p=b.at(Square(s));
            if(p==Piece::NONE || p.color()!=colour) continue;
            int kind=p.type(),file=s%8,rank=s/8;
            int advance=colour==Color::WHITE ? rank : 7-rank;
            int center=7-std::abs(2*file-7)-std::abs(2*rank-7);
            subtotal+=VALUE[kind];
            if(kind==int(PieceType::PAWN)) {
                subtotal+=advance*(nonpawn<2500?6:3);
                if(file==3 || file==4) subtotal+=advance*3;
            } else if(kind==int(PieceType::KNIGHT)) subtotal+=center*6;
            else if(kind==int(PieceType::BISHOP)) {++bishops;subtotal+=center*3;}
            else if(kind==int(PieceType::ROOK)) {
                bool any=false,own=false;
                for(int r=0;r<8;++r) {
                    Piece q=b.at(Square(r*8+file));
                    if(q.type()==PieceType::PAWN) {any=true;own|=q.color()==colour;}
                }
                if(!any) subtotal+=18;else if(!own) subtotal+=9;
                if(advance==6) subtotal+=15;
            } else if(kind==int(PieceType::QUEEN)) {
                subtotal+=center;
                if(b.fullMoveNumber()<=10) subtotal-=advance*5;
            } else {
                if(nonpawn>=2500) {
                    subtotal-=advance*25;
                    if((file==2 || file==6) && advance==0) subtotal+=35;
                    int r=rank+(colour==Color::WHITE?1:-1);
                    if(r>=0 && r<8) for(int f=std::max(0,file-1);f<=std::min(7,file+1);++f)
                        if(b.at(Square(r*8+f))==Piece(PieceType::PAWN,colour)) subtotal+=8;
                } else subtotal+=center*6;
            }
        }
        if(bishops>=2) subtotal+=20;
        score+=colour==Color::WHITE ? subtotal : -subtotal;
    }
    return b.sideToMove()==Color::WHITE ? score : -score;
}

bool insufficient(const Board& b) {
    // Match the rules library used by the official evaluator, including any
    // number of bishops confined to one square colour after underpromotion.
    if(b.pieces(PieceType::PAWN) || b.pieces(PieceType::ROOK) || b.pieces(PieceType::QUEEN)) return false;
    if(b.pieces(PieceType::KNIGHT)) return b.occ().count()==3;
    bool dark=false,light=false;
    for(int s=0;s<64;++s) if(b.at(Square(s)).type()==PieceType::BISHOP)
        ((s%8+s/8)%2 ? dark : light)=true;
    return !(dark && light);
}

bool draw(const Board& b) {return b.halfMoveClock()>=100 || b.isRepetition(2) || insufficient(b);}
std::vector<Move> legal(const Board& b) {
    Movelist list;movegen::legalmoves(list,b);
    return std::vector<Move>(list.begin(),list.end());
}
std::vector<std::string> split(const std::string& s,char delimiter) {
    std::vector<std::string> out;std::stringstream in(s);std::string item;
    while(std::getline(in,item,delimiter)) if(!item.empty()) out.push_back(item);
    return out;
}
Move parsed_legal(const Board& b,const std::string& s) {
    auto moves=legal(b);
    for(Move m:moves) if(uci::moveToUci(m,false)==s) return m;
    throw std::invalid_argument("illegal input move");
}

class Analysis {
public:
    Clock::time_point deadline;
    uint64_t nodes=0;
    explicit Analysis(double seconds):deadline(Clock::now()+std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds))) {}
    void check(bool force=false) {
        if((force || nodes%256==0) && Clock::now()>=deadline) throw Expired{};
    }
    int order(const Board& b,Move m) {
        int result=0;
        if(b.isCapture(m)) result+=2000+VALUE[int(b.getCapturing<PieceType>(m))]*10-VALUE[int(b.at(m.from()).type())];
        if(m.typeOf()==Move::PROMOTION) result+=1500+VALUE[int(m.promotionType())];
        return result;
    }
    Result node(Board& b,int depth,int alpha,int beta,int ply,int qleft=4) {
        ++nodes;check();auto moves=legal(b);
        if(moves.empty()) return {b.inCheck()?-MATE+ply:0,{}};
        if(draw(b)) return {0,{}};
        bool checked=b.inCheck();int best=-2*MATE;
        if(depth<=0) {
            int stand=evaluate(b);
            if(qleft<=0) return {stand,{}};
            if(!checked) {
                if(stand>=beta) return {stand,{}};
                alpha=std::max(alpha,stand);best=stand;
                moves.erase(std::remove_if(moves.begin(),moves.end(),[&](Move m){return !b.isCapture(m) && m.typeOf()!=Move::PROMOTION;}),moves.end());
                if(moves.empty()) return {stand,{}};
            }
        }
        std::stable_sort(moves.begin(),moves.end(),[&](Move x,Move y){return order(b,x)>order(b,y);});
        std::vector<Move> line;
        for(Move m:moves) {
            b.makeMove<true>(m);Result child;
            try {child=node(b,depth-1,-beta,-alpha,ply+1,depth<=0?qleft-1:qleft);}
            catch(...) {b.unmakeMove(m);throw;}
            b.unmakeMove(m);int score=-child.score;
            if(score>best) {best=score;line=std::move(child.line);line.insert(line.begin(),m);}
            alpha=std::max(alpha,score);
            if(alpha>=beta) break;
        }
        return {best,std::move(line)};
    }
};

int main(int argc,char** argv) {
    try {
        if(argc!=8) throw std::invalid_argument("usage: analysis seconds maxdepth initial-fen history-csv current-fen choices-csv prune");
        double seconds=std::stod(argv[1]);int maxdepth=std::stoi(argv[2]);
        if(seconds<0 || seconds>10 || maxdepth<0 || maxdepth>12) throw std::invalid_argument("invalid search budget");
        Board b;if(!b.setFen(argv[3])) throw std::invalid_argument("invalid initial FEN");
        if(b.pieces(PieceType::KING,Color::WHITE).count()!=1 || b.pieces(PieceType::KING,Color::BLACK).count()!=1) throw std::invalid_argument("missing kings");
        for(const auto& s:split(argv[4],',')) b.makeMove<true>(parsed_legal(b,s));
        if(b.getFen()!=argv[5]) throw std::invalid_argument("history/current FEN mismatch");
        std::vector<Move> choices;for(const auto& s:split(argv[6],',')) choices.push_back(parsed_legal(b,s));
        bool prune=std::stoi(argv[7])!=0;
        Analysis search(seconds);auto start=Clock::now();std::vector<Row> rows;
        for(Move m:choices) {
            b.makeMove<true>(m);auto replies=legal(b);
            int score=replies.empty()?(b.inCheck()?MATE-1:0):(draw(b)?0:-evaluate(b));
            b.unmakeMove(m);rows.push_back({m,score,false,{m}});
        }
        auto sort=[](std::vector<Row>& r){std::stable_sort(r.begin(),r.end(),[](const Row& a,const Row& b){return a.score>b.score;});};
        sort(rows);int completed=0;
        for(int depth=1;depth<=maxdepth;++depth) {
            std::vector<Row> trial;int best=-2*MATE;
            try {
                for(const Row& previous:rows) {
                    search.check(true);Move m=previous.move;b.makeMove<true>(m);Result child;
                    int limit=prune && !trial.empty() ? -best+65 : 2*MATE;
                    try {child=search.node(b,depth-1,-2*MATE,limit,1);} catch(...) {b.unmakeMove(m);throw;}
                    b.unmakeMove(m);int score=-child.score;bool upper=prune && !trial.empty() && score<=best-65;
                    if(!upper) best=std::max(best,score);
                    child.line.insert(child.line.begin(),m);trial.push_back({m,score,upper,std::move(child.line)});
                }
            } catch(Expired&) {break;}
            rows=std::move(trial);sort(rows);completed=depth;
            if(!rows.empty() && rows.front().score>=MATE-10) break;
        }
        std::cout<<"{\"completed_depth\":"<<completed<<",\"nodes\":"<<search.nodes<<",\"seconds\":"<<std::chrono::duration<double>(Clock::now()-start).count()<<",\"static_score\":"<<evaluate(b)<<",\"legal_moves\":[";
        bool legal_comma=false;
        for(Move m:legal(b)) {if(legal_comma) std::cout<<',';legal_comma=true;std::cout<<'"'<<uci::moveToUci(m,false)<<'"';}
        std::cout<<"],\"scores\":[";
        bool comma=false;
        for(const auto& row:rows) {
            if(comma) std::cout<<',';comma=true;
            std::cout<<"{\"uci\":\""<<uci::moveToUci(row.move,false)<<"\",\"score\":"<<row.score;
            if(row.upper) std::cout<<",\"score_bound\":\"upper\"";
            std::cout<<",\"line\":[";bool inner=false;
            for(Move m:row.line) {if(inner) std::cout<<',';inner=true;std::cout<<'"'<<uci::moveToUci(m,false)<<'"';}
            std::cout<<"]}";
        }
        std::cout<<"]}\n";
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 2;}
}
