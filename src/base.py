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

from typing import TextIO, Optional, Any, List
from collections.abc import Iterable, Hashable
from dataclasses import dataclass

import logging

Objective = Any

@dataclass
class Component:
    x: int
    y: int
    candle_len: int
    candle_speed: int

    @property
    def cid(self) -> Hashable:
        return self.x, self.y

class LocalMove:
    ...

class Solution:
    def output(self) -> str:
        """
        Generate the output string for this solution
        """
        raise NotImplementedError

    def copy(self) -> Solution:
        """
        Return a copy of this solution.

        Note: changes to the copy must not affect the original
        solution. However, this does not need to be a deepcopy.
        """
        raise NotImplementedError

    def is_feasible(self) -> bool:
        """
        Return whether the solution is feasible or not
        """
        raise NotImplementedError

    def objective(self) -> Optional[Objective]:
        """
        Return the objective value for this solution if defined, otherwise
        should return None
        """
        raise NotImplementedError

    def lower_bound(self) -> Optional[Objective]:
        """
        Return the lower bound value for this solution if defined,
        otherwise return None
        """
        raise NotImplementedError

    def add_moves(self) -> Iterable[Component]:
        """
        Return an iterable (generator, iterator, or iterable object)
        over all components that can be added to the solution
        """
        raise NotImplementedError

    def local_moves(self) -> Iterable[LocalMove]:
        """
        Return an iterable (generator, iterator, or iterable object)
        over all local moves that can be applied to the solution
        """
        raise NotImplementedError

    def random_local_move(self) -> Optional[LocalMove]:
        """
        Return a random local move that can be applied to the solution.

        Note: repeated calls to this method may return the same
        local move.
        """
        raise NotImplementedError

    def random_local_moves_wor(self) -> Iterable[LocalMove]:
        """
        Return an iterable (generator, iterator, or iterable object)
        over all local moves (in random order) that can be applied to
        the solution.
        """
        raise NotImplementedError
            
    def heuristic_add_move(self) -> Optional[Component]:
        """
        Return the next component to be added based on some heuristic
        rule.
        """
        raise NotImplementedError

    def add(self, component: Component) -> None:
        """
        Add a component to the solution.

        Note: this invalidates any previously generated components and
        local moves.
        """
        raise NotImplementedError

    def step(self, lmove: LocalMove) -> None:
        """
        Apply a local move to the solution.

        Note: this invalidates any previously generated components and
        local moves.
        """
        raise NotImplementedError

    def objective_incr_local(self, lmove: LocalMove) -> Optional[Objective]:
        """
        Return the objective value increment resulting from applying a
        local move. If the objective value is not defined after
        applying the local move return None.
        """
        raise NotImplementedError

    def lower_bound_incr_add(self, component: Component) -> Optional[Objective]:
        """
        Return the lower bound increment resulting from adding a
        component. If the lower bound is not defined after adding the
        component return None.
        """
        raise NotImplementedError

    def perturb(self, ks: int) -> None:
        """
        Perturb the solution in place. The amount of perturbation is
        controlled by the parameter ks (kick strength)
        """
        raise NotImplementedError

    def components(self) -> Iterable[Component]:
        """
        Returns an iterable to the components of a solution
        """
        raise NotImplementedError

class Problem:

    def __init__(self, villages: List[Component]) -> None:
        self.nnodes = len(villages)
        self.villages = villages

    @classmethod
    def from_textio(cls, f: TextIO) -> Problem:
        """
        Create a problem from a text I/O source `f`
        """
        n = int(f.readline())

        villages = []

        start_x, start_y = map(int, f.readline().split())
        start = Component(start_x, start_y, 0, 0)
        villages.append(start)

        for _ in range(n-1):
            x, y, h, s = map(int, f.readline().split())
            villages.append(Component(x, y, h, s))
        return cls(villages)

    def empty_solution(self) -> Solution:
        """
        Create an empty solution (i.e. with no components).
        """
        return []


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
        if args.csearch == 'heuristic':
            s = heuristic_construction(s)
        elif args.csearch == 'greedy':
            s = greedy_construction(s)
        elif args.csearch == 'beam':
            s = beam_search(s, 10)
        elif args.csearch == 'grasp':
            s = grasp(s, args.cbudget, alpha = 0.01)
        elif args.csearch == 'as':
            ants = [s]*100
            s = ant_system(ants, args.cbudget, beta = 5.0, rho = 0.5, tau0 = 1 / 3000.0)
        elif args.csearch == 'mmas':
            ants = [s]*100
            s = mmas(ants, args.cbudget, beta = 5.0, rho = 0.02, taumax = 1 / 3000.0, globalratio = 0.5)

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
            s = sa(s, args.lbudget, 30)

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

