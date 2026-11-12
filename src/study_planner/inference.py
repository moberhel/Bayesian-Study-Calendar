"""Exact inference: factor-based variable elimination (plus brute-force enumeration for testing)."""
from __future__ import annotations
import itertools
from dataclasses import dataclass
import numpy as np
from .model import STATES, PARENTS, ORDER, build_cpts

# =====================================================================
# 2. INFERENCE: factor-based exact Variable Elimination
# =====================================================================
@dataclass
class Factor:
    vars: list[str]
    table: np.ndarray

    def restrict(self, ev: dict[str, str]) -> "Factor":
        idx, keep = [], []
        for v in self.vars:
            if v in ev: idx.append(STATES[v].index(ev[v]))
            else: idx.append(slice(None)); keep.append(v)
        return Factor(keep, self.table[tuple(idx)])

    def multiply(self, o: "Factor") -> "Factor":
        allv = list(dict.fromkeys(self.vars + o.vars))
        def expand(f):
            shape = [len(STATES[v]) if v in f.vars else 1 for v in allv]
            order = [f.vars.index(v) for v in allv if v in f.vars]
            return np.transpose(f.table, order).reshape(shape)
        return Factor(allv, expand(self) * expand(o))

    def marginalize(self, v: str) -> "Factor":
        ax = self.vars.index(v)
        return Factor([x for x in self.vars if x != v], self.table.sum(axis=ax))


class BayesNet:
    def __init__(self):
        self.cpt = build_cpts()

    def factors(self):
        return [Factor(PARENTS[v] + [v], self.cpt[v]) for v in ORDER]

    def query(self, targets: list[str], evidence: dict[str, str]) -> Factor:
        """P(targets | evidence) via variable elimination (min-size heuristic)."""
        facs = [f.restrict(evidence) for f in self.factors()]
        hidden = [v for v in ORDER if v not in targets and v not in evidence]
        while hidden:
            def cost(v):  # size of the product factor created by eliminating v
                vs = set().union(*[set(f.vars) for f in facs if v in f.vars])
                return np.prod([len(STATES[x]) for x in vs])
            v = min(hidden, key=cost); hidden.remove(v)
            rel = [f for f in facs if v in f.vars]
            facs = [f for f in facs if v not in f.vars]
            prod = rel[0]
            for f in rel[1:]: prod = prod.multiply(f)
            facs.append(prod.marginalize(v))
        res = facs[0]
        for f in facs[1:]: res = res.multiply(f)
        order = [res.vars.index(t) for t in targets]
        t = np.transpose(res.table, order)
        return Factor(targets, t / t.sum())

    def query_bruteforce(self, target: str, evidence: dict[str, str]) -> np.ndarray:
        """Full-joint enumeration; used only to unit-test the VE implementation."""
        out = np.zeros(len(STATES[target]))
        for combo in itertools.product(*[range(len(STATES[v])) for v in ORDER]):
            a = dict(zip(ORDER, combo))
            if any(STATES[v].index(s) != a[v] for v, s in evidence.items()): continue
            p = 1.0
            for v in ORDER:
                p *= self.cpt[v][tuple(a[x] for x in PARENTS[v]) + (a[v],)]
            out[a[target]] += p
        return out / out.sum()
