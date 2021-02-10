#!/usr/bin/python

from tqdm.auto import tqdm
import pandas as pd
from collections import OrderedDict
import os
from multiprocessing import current_process
from setcover.set import ExclusionSet
import logging
import concurrent.futures
from typing import List, Dict, Set, Iterable
from tests.test_sets import exclusion_sets
from itertools import repeat

logging.basicConfig()
log = logging.getLogger(__name__)

# TODO: Use additional logging handlers from standard library https://docs.python.org/3/library/logging.handlers.html
# TODO: Implement better logging from cookbook https://docs.python.org/3/howto/logging-cookbook.html
# TODO: logging to file that is written as the module executes
# TODO: Cloudwatch on logging file

# TODO: Lazy data type checking on __init__
# TODO: Figure out why  __init__  `obj = obj = None` fails -- is it a pointer issue?


class ExclusionSetCoverProblem:
    def __init__(self, input_sets=None):
        self.subsets_include = OrderedDict()
        self.subsets_exclude = OrderedDict()
        self.include_covered = set()
        self.exclude_covered = set()
        self.elements_include = set()
        self.elements_exclude = set()
        self.cover_solution = []

        if input_sets:
            log.info("Building data set with included data")
            (
                self.elements_include,
                self.elements_exclude,
                self.subsets_include,
                self.subsets_exclude,
            ) = self._make_data(input_sets)

    @staticmethod
    def _make_data(
        sets: List[ExclusionSet],
    ) -> object:
        """

        :param sets: List of Named Tuples
        :return:
        """
        elements_include = set({})
        elements_exclude = set({})
        subsets_include = OrderedDict()
        subsets_exclude = OrderedDict()
        for set_ in sets:
            subset_id, subset_include, subset_exclude = set_
            subsets_include[subset_id] = set(subset_include)
            subsets_exclude[subset_id] = set(subset_exclude)
            elements_include |= set(subset_include)
            elements_exclude |= set(subset_exclude)
        return elements_include, elements_exclude, subsets_include, subsets_exclude

    def _define_data(self, sets: List[ExclusionSet]):
        (
            self.elements_include,
            self.elements_exclude,
            self.subsets_include,
            self.subsets_exclude,
        ) = self._make_data(sets)

    @staticmethod
    def _rows_to_sets(rows: Iterable) -> List[ExclusionSet]:
        return [ExclusionSet(r[0], r[1], r[2]) for r in rows]

    def from_lists(
        self, ids: List[str], sets_include: List[Set[str]], sets_exclude: List[Set[str]]
    ):
        """
        Used to import Python Lists
        :param ids:
        :param sets_include:
        :param sets_exclude:
        :return:
        """
        rows = list(zip(ids, sets_include, sets_exclude))
        sets = self._rows_to_sets(rows)
        self._define_data(sets)

    def from_dataframe(self, df: pd.DataFrame):
        """
        Used to import Pandas DataFrames
        :param df:
        :return:
        """
        rows = list(df.itertuples(name="Row", index=False))
        sets = self._rows_to_sets(rows)
        self._define_data(sets)

    @staticmethod
    def _calculate_set_cost(subsets_data, include_covered, exclude_covered):
        """
        Calculate the cost of adding the set to the problem solution
        :param subsets_data:
        :param include_covered:
        :param exclude_covered:
        :return:
        """
        (set_id, include_elements, exclude_elements) = subsets_data
        process_id, process_name = (
            os.getpid(),
            current_process().name,
        )
        log.info(f"Process ID: {process_id}")
        log.info(f"Process Name: {process_name}")
        new_include_elements = len(include_elements - include_covered)
        new_exclude_elements = len(exclude_elements - exclude_covered)
        # set may have same elements as already covered -> Check to avoid division by 0 error
        if new_include_elements != 0:
            cost_elem_ratio = new_exclude_elements / new_include_elements
        else:
            cost_elem_ratio = float("inf")
        return set_id, round(cost_elem_ratio, 4)

    def solve(self, limit=float("inf")):
        log.info("Solving set coverage problem")
        # If elements don't cover problem -> invalid inputs for set cover problem
        set_ids = set(self.subsets_include.keys()) # TODO Move this out of solve
        log.info(f"Sets IDs: {set_ids}")
        all_elements = set(
            e for s in self.subsets_include.keys() for e in self.subsets_include[s]
        )
        if all_elements != self.elements_include:
            log.error(f"All Elements: {all_elements}")
            log.error(f"Universe: {self.elements_include} self.elements_exclude,")
            raise Exception("Universe is incomplete")

        # track elements of problem covered
        # coverage_goal = set(
        #     [item for sublist in self.subsets_include.values() for item in sublist]
        # )
        log.info(f"Number of Sets: {len(set_ids)}")
        with tqdm(total=len(set_ids), desc="Sets Used in Solution") as tqdm_sets, tqdm(
            total=len(self.elements_include),
            desc="Set Coverage of Include Set",
        ) as tqdm_include, tqdm(
            total=len(self.elements_exclude),
            desc="Set Coverage of Exclude Set",
        ) as tqdm_exclude:
            log.debug(f"Include Elements: {self.elements_include}")
            log.debug(f"Include Covered: {self.include_covered}")
            while (len(self.include_covered) < len(self.elements_include)) & (len(self.cover_solution) < limit):
                skip_set_ids = [set_id for set_id, cost in self.cover_solution]
                log.info(
                    f"Skipping over {len(skip_set_ids)} sets already in solution"
                )
                set_zip = zip(
                    self.subsets_include.keys(),
                    self.subsets_include.values(),
                    self.subsets_exclude.values(),
                )
                set_data = [
                    (set_id, incl, excl)
                    for set_id, incl, excl in set_zip
                    if set_id not in skip_set_ids
                ]
                n = len(set_data)
                if n == 0:
                    log.error("Available sets have been exhausted")
                    break
                log.info(f"Calculating cost for {n} sets")
                # Iterator repeats for multiprocessing
                ic, ec = repeat(self.include_covered), repeat(self.exclude_covered)
                # Find set with minimum cost:elements_added ratio
                with concurrent.futures.ProcessPoolExecutor() as executor:
                    results = list(
                        tqdm(
                            executor.map(self._calculate_set_cost, set_data, ic, ec),
                            total=n,
                            desc="Calculating Set Costs",
                            leave=False,
                        )
                    )
                # Select the set with the lowest cost
                log.debug(results)
                min_set_id, min_set_cost = min(results, key=lambda t: t[1])
                min_set_include, min_set_exclude = (
                    self.subsets_include[min_set_id],
                    self.subsets_exclude[min_set_id],
                )
                # Find the new elements we covered
                new_covered_inclusive = min_set_include.difference(self.include_covered)
                new_covered_exclusive = min_set_exclude.difference(self.exclude_covered)
                tqdm_include.update(len(new_covered_inclusive))
                tqdm_exclude.update(len(new_covered_exclusive))
                # Add newly covered to tracking variables
                self.include_covered |= new_covered_inclusive
                self.exclude_covered |= new_covered_exclusive
                # Append to our solution
                self.cover_solution.append((min_set_id, min_set_cost))
                tqdm_sets.update(1)
                log.info(
                    f"""Set found: {min_set_id}
                Cost: {min_set_cost}
                Added Coverage: {len(new_covered_inclusive)}
                """
                )
                log.debug(self.include_covered)
                log.debug(self.exclude_covered)
                log.debug(self.cover_solution)
        log.info(f"Final cover Solution: {self.cover_solution}")


if __name__ == "__main__":
    problem = ExclusionSetCoverProblem(exclusion_sets)
    problem.solve()
    log.info(problem.cover_solution)
