import random
import pytest
from chess_analysis import MATE,candidate_subset


def rows(*scores):
    return {"scores":[{"uci":str(i),"score":s} for i,s in enumerate(scores)]}


@pytest.mark.parametrize("scores,expected",[
    ([99999,99997,900],["0"]),
    ([99995,99995,99993],["0","1"]),
    ([-99992,-99996,-99996],["0"]),
    ([-99990,-99990,-99996],["0","1"]),
    ([99900,99899],["0"]),
    ([-99900,-99901],["0"]),
    ([99999]*6,["0","1","2","3"]),
])
def test_mate_distance_uses_exact_best_ties(scores,expected):
    assert candidate_subset(rows(*scores),[str(i) for i in range(len(scores))],tolerance=30,secondary_tolerance=30)==expected


def test_bounds_cannot_supply_or_widen_mate_candidates():
    data={"scores":[{"uci":"bound","score":99999,"score_bound":"upper"},{"uci":"best","score":99997},{"uci":"other","score":99995}]}
    assert candidate_subset(data,["bound","best","other"])==["best"]
    assert candidate_subset({"scores":[data["scores"][0]]},["bound"])==["bound"]


def test_nonmate_policy_matches_old_formula_on_fresh_numeric_inputs():
    rng=random.Random(20261015151)
    for _ in range(200):
        scores=sorted([rng.randrange(-90000,90000) for _ in range(rng.randrange(1,12))],reverse=True)
        data=rows(*scores);legal=[str(i) for i in range(len(scores))]
        for tolerance,secondary in [(0,0),(30,30),(65,120),(0,1000000)]:
            exact=data["scores"];best=exact[0]["score"]
            expected=[x["uci"] for x in exact if x["score"]>=best-tolerance][:4]
            if len(expected)==1 and len(exact)>1 and exact[1]["score"]>=best-secondary:expected.append(exact[1]["uci"])
            assert candidate_subset(data,legal,tolerance=tolerance,secondary_tolerance=secondary)==expected
