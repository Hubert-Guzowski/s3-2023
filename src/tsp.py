#!/usr/bin/env python3
#
# Copyright (C) 2023 Alexandre Jesus <https://adbjesus.com>, Carlos M. Fonseca <cmfonsec@dei.uc.pt>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from typing import TextIO, Optional, cast, NewType
from collections.abc import Sequence, Iterable, Hashable

from dataclasses import dataclass
from math import sqrt, isclose
from copy import copy
from itertools import chain
import logging
import sys
import random

from api.utils import or_default, pairwise, sample2

@dataclass
class Component:
    u: int
    v: int
    candle_len: int
    candle_speed: int

    @property
    def cid(self) -> Hashable:
        return self.u, self.v

@dataclass
class LocalMove:
    i: int
    j: int

if sys.version_info < (3, 9):
    Path = NewType('Path', list)
    Used = NewType('Used', set)
    Unused = NewType('Unused', set)
else:
    Path = NewType('Path', list[Component])
    Used = NewType('Used', set[int])
    Unused = NewType('Unused', set[int])

class Solution():
    def __init__(self,
                 problem: Problem,
                 start: int,
                 path: Path,
                 used: Used,
                 unused: Unused,
                 dist: float) -> None:
        self.problem = problem
        self.start = start
        self.path = path
        self.used = used
        self.unused = unused
        self.dist = dist


    def output(self) -> str:
        return "\n".join(map(str, self.path[1:]))

    def copy(self):
        return self.__class__(self.problem,
                              self.start,
                              copy(self.path),
                              copy(self.used),
                              copy(self.unused),
                              self.dist)

    def is_feasible(self) -> bool:
        return True

    def objective(self) -> Optional[float]:
        reward = 0
        if self.path != []:
            current_time = 0 # self.problem.dist[0][self.path[0]]
            for i in range(len(self.path)-1):
                reward += max(0, self.problem.coords[self.path[i]].candle_len - (current_time*self.problem.coords[self.path[i]].candle_speed))
                current_time += self.problem.dist[self.path[i]][self.path[i+1]]
            reward += max(0, self.problem.coords[self.path[-1]].candle_len - (current_time*self.problem.coords[self.path[-1]].candle_speed))
            return -reward  # WE ARE WORKING WITH A MINIMIZATION FRAMEWORK --> flipped to min problem!
        else:
            return 0

    def lower_bound(self) -> Optional[float]:
        return self.dist

    def add_moves(self) -> Iterable[Component]:
        if len(self.path) < self.problem.nnodes:
            u = self.path[-1]
            for v in self.unused:
                yield Component(u, v, self.problem.coords[self.path[-1]].candle_len, self.problem.coords[self.path[-1]].candle_speed)
        # elif len(self.path) == self.problem.nnodes:
        #     u = self.path[-1]
        #     yield Component(u, self.start)

    def local_moves(self) -> Iterable[LocalMove]:
        for i in range(1, len(self.path)):
            for j in range(i+2, len(self.path)):
                yield LocalMove(i, j)

    def random_local_move(self) -> Optional[LocalMove]:
        if len(self.path) >= 4:
            i = random.randrange(1, len(self.path)-2)
            j = random.randrange(i+2, len(self.path))
            return LocalMove(i, j)
        else:
            return None

    def random_local_moves_wor(self) -> Iterable[LocalMove]:
        for i, j in sample2(len(self.path), len(self.path)):
            if i >= 1 and j >= i+2:
                yield LocalMove(i, j)

    def heuristic_add_move(self) -> Optional[Component]:
        # Return the closest
        if len(self.path) < self.problem.nnodes:
            best = None
            bestd = None
            u = self.path[-1]
            for v in self.unused:
                d = self.problem.dist[u][v] 
                if bestd is None or d < bestd:
                    best = Component(u, v, self.problem.coords[self.path[-1]].candle_len, self.problem.coords[self.path[-1]].candle_speed)
                    bestd = d
            return best
        # elif len(self.path) == self.problem.nnodes:
        #     u = self.path[-1]
        #     return Component(u, self.start)
        return None

    def add(self, component: Component) -> None:
        u, v = component.u, component.v
        self.path.append(v)
        if v != self.start:
            self.unused.remove(v)
        self.used.add(v)
        self.dist += self.problem.dist[u][v]

    def step(self, lmove: LocalMove) -> None:
        i, j = lmove.i, lmove.j
        self.dist -= self.problem.dist[self.path[i-1]][self.path[i]]
        self.dist -= self.problem.dist[self.path[j-1]][self.path[j]]
        self.path[i:j] = list(reversed(self.path[i:j]))
        self.dist += self.problem.dist[self.path[i-1]][self.path[i]]
        self.dist += self.problem.dist[self.path[j-1]][self.path[j]]

        # if __debug__:
        #     dist = sum(map(lambda t: self.problem.dist[t[0]][t[1]],
        #                    pairwise(self.path)))
        #     assert isclose(dist, self.dist), (dist, self.dist)
        #     assert self.path[0] == self.start, self.path
        #     assert self.path[-1] == self.start, self.path

    def objective_incr_local(self, lmove: LocalMove) -> Optional[float]:
        i, j = lmove.i, lmove.j
        ndist = self.dist
        ndist -= self.problem.dist[self.path[i-1]][self.path[i]]
        ndist -= self.problem.dist[self.path[j-1]][self.path[j]]
        ndist += self.problem.dist[self.path[i-1]][self.path[j-1]]
        ndist += self.problem.dist[self.path[i]][self.path[j]]
        return ndist - self.dist

    def lower_bound_incr_add(self, component: Component) -> Optional[float]:
        # TODO
        if len(self.path) + 1 <= cast(Problem, self.problem).nnodes:
            u, v = component.u, component.v
            d = self.problem.dist[u][v]
            return d
        else:
            return 0

    def perturb(self, ks: int) -> None:
        for _ in range(ks):
            move = self.random_local_move()
            if move is not None:
                self.step(move)

    def components(self) -> Iterable[Component]:
        for i in range(1, len(self.path)):
            yield Component(self.path[i-1], self.path[i], self.problem.coords[self.path[-1]].candle_len,
                      self.problem.coords[self.path[-1]].candle_speed)



@dataclass
class Point:
    x: float
    y: float

if sys.version_info < (3, 9):
    CoordList = Sequence
    DistMatrix = tuple
else:
    CoordList = Sequence[Point]
    DistMatrix = tuple[tuple[float, ...], ...]

def manhattan_distance(a: Point, b: Point) -> float:
    dx = a.u - b.u
    dy = a.v - b.v
    return abs(dx) + abs(dy)

def distance_matrix(coords: CoordList) -> DistMatrix:
    mat = []
    for a in coords:
        row = []
        for b in coords:
            row.append(manhattan_distance(a, b))
        mat.append(tuple(row))
    return tuple(mat)

class Problem():
    def __init__(self, coords: CoordList, start: Component) -> None:
        self.nnodes = len(coords)
        self.coords = coords
        self.dist = distance_matrix(coords)
        self.start = start

    @classmethod
    def from_textio(cls, f: TextIO) -> Problem:
        """
        Create a problem from a text I/O source `f`
        """
        n = int(f.readline())

        villages = []

        start_u, start_v = map(int, f.readline().split())
        start = Component(start_u, start_v, 0, 0)
        villages.append(start)
        for _ in range(n-1):
            u, v, h, s = map(int, f.readline().split())
            villages.append(Component(u, v, h, s))
        return cls(villages, start)

    def empty_solution(self) -> Solution:
        return Solution(self, 0, [0], {0}, set(range(1, self.nnodes)), 0)

    def empty_solution_with_start(self, start: int) -> Solution:
        return Solution(self, start, [start], {start}, set(range(self.nnodes))-{start}, 0)


if __name__ == '__main__':
    from api.solvers import *
    from time import perf_counter
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('--log-level',
                        choices=['critical', 'error', 'warning', 'info', 'debug'],
                        default='warning')
    parser.add_argument('--log-file', type=argparse.FileType('w'), default=sys.stderr)
    parser.add_argument('--csearch',
                        choices=['beam', 'grasp', 'greedy', 'heuristic', 'as', 'mmas', 'none'],
                        default='none')
    parser.add_argument('--cbudget', type=float, default=5.0)
    parser.add_argument('--lsearch',
                        choices=['bi', 'fi', 'ils', 'rls', 'sa', 'none'],
                        default='none')
    parser.add_argument('--lbudget', type=float, default=5.0)
    parser.add_argument('--input-file', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('--output-file', type=argparse.FileType('w'), default=sys.stdout)
    args = parser.parse_args()

    logging.basicConfig(stream=args.log_file,
                        level=args.log_level.upper(),
                        format="%(levelname)s;%(asctime)s;%(message)s")

    p = Problem.from_textio(args.input_file)
    s: Optional[Solution] = p.empty_solution()

    start = perf_counter()

    if s is not None:
        if args.csearch == 'beam':
            s = beam_search(s, 10)
        elif args.csearch == 'grasp':
            # s = grasp(s, args.cbudget, alpha = 0.01)
            s = grasp(s, args.cbudget, alpha = 0.01, local_search = lambda s: first_improvement(s, 0.1))
        elif args.csearch == 'greedy':
            s = greedy_construction(s)
        elif args.csearch == 'heuristic':
            s = heuristic_construction(s)
        elif args.csearch == 'as':
            ants = [p.empty_solution_with_start(i) for i in range(p.nnodes)]
            # s = aco(ants, 30.0, beta = 5.0, rho = 0.5, tau0 = 1 / 3000.0)
            lbudget = 1.0 / len(ants)
            s = ant_system(ants, args.cbudget, beta = 5.0, rho = 0.5, tau0 = 1 / 3000.0,
                           local_search = lambda s: first_improvement(s, lbudget))
        elif args.csearch == 'mmas':
            ants = [p.empty_solution_with_start(i) for i in range(p.nnodes)]
            # s = mmas(ants, 30.0, beta = 5.0, rho = 0.02, taumax = 1 / 3000.0, ants = 0.1)
            lbudget = 1.0 / len(ants)
            s = mmas(ants, args.cbudget, beta = 5.0, rho = 0.05, taumax = 1 / 3000.0, globalratio = 0.1,
                     local_search = lambda s: first_improvement(s, lbudget))
    print('done csearch!')

    if s is not None:
        if args.lsearch == 'bi':
            s = best_improvement(s, args.lbudget)
        elif args.lsearch == 'fi':
            s = first_improvement(s, args.lbudget)
        elif args.lsearch == 'ils':
            s = ils(s, args.lbudget)
        elif args.lsearch == 'rls':
            s = rls(s, args.lbudget)
        elif args.lsearch == 'sa':
            s = sa(s, args.lbudget, 10)

    end = perf_counter()

    if s is not None:
        print(s.output(), file=args.output_file)
        if s.objective() is not None:
            logging.info(f"Objective: {s.objective():.3f}")
        else:
            logging.info(f"Objective: None")
    else:
        logging.info(f"Objective: no solution found")

    logging.info(f"Elapsed solving time: {end-start:.4f}")
