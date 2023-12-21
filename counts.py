#!/usr/bin/env env/bin/python
"""
Class to count number of questions
"""

import random
import re
import copy

from typing import List
import yaml

import tags


def find_questions(structure, questions) -> List:
    """
    fake find_questions to test
    """
    print("finding", structure)
    query = tags.tag_query(structure)

    return tags.look_compatible_questions(query, questions)


class Counter:
    """
    Class to measure/control/calculate number of questions in exam
    """

    def __init__(self, structure, questions):
        if isinstance(structure, int):
            self._copy({"lemma": str(structure), "min": structure})
        elif isinstance(structure, str):
            # Detect interval
            match = re.fullmatch(r"(-?\d+)(-(\d+))?", structure)
            if match:
                mn = int(match[1])
                if match[2]:
                    mx = int(match[3])
                    self._copy({"lemma": structure, "min": mn, "max": mx})
                else:
                    self._copy({"lemma": structure, "min": mn})
            else:
                # it is a tag filter
                selected_questions = find_questions(structure, questions)
                self._copy(
                    {
                        "lemma": structure,
                        "min": 0,
                        "max": len(selected_questions),
                        "bank": selected_questions,
                    }
                )
        elif isinstance(structure, list):
            mn = 0
            mx = 0
            children = []
            for it in structure:
                child = Counter(it, questions)
                mn += child.min
                mx += child.max
                children.append(child)
            self._copy(
                {
                    "lemma": f"ARRAY[{children[0].lemma},...]",
                    "min": mn,
                    "max": mx,
                    "children": children,
                }
            )
        elif isinstance(structure, dict):
            # if the dict have more than one key, each key is
            # processed independly and then trated as an array

            if len(structure) == 1:
                (k, v) = structure.popitem()
                key_counter = Counter(k, questions)
                value_counter = Counter(v, questions)
                combined_counter = combine(key_counter, value_counter)

                self._copy(combined_counter)
            else:
                mn = 0
                mx = 0
                children = []
                for k, v in structure.items():
                    key_counter = Counter(k, questions)
                    value_counter = Counter(v, questions)
                    combined_counter = combine(key_counter, value_counter)

                    mn += combined_counter.min
                    mx += combined_counter.max
                    children.append(combined_counter)
                self._copy(
                    {
                        "lemma": f"DICT[{children[0].lemma},...]",
                        "min": mn,
                        "max": mx,
                        "children": children,
                    }
                )

    def __str__(self):
        output = [
            f"Counter: {self.lemma}",
            f"  range: {self.min}-{self.max}: {self.real}",
        ]
        for child in self.children:
            lines = str(child).split("\n")
            for line in lines:
                output.append(f"  {line}")

        if self.bank:
            output.append(f"  bank_size: {len(self.bank)}")

        return "\n".join(output)

    def can_grow(self) -> bool:
        """
        Inform if the counter can increase its value
        """
        return self.real < self.max

    def is_single(self) -> bool:
        """
        Inform if the counter hasn't children or questions in the bank
        (it is only a number or a interval)
        """
        return not (bool(self.children) or bool(self.bank))

    def _copy(self, other):
        """
        A kind of shallow copy constructor without allocation
        """
        if isinstance(other, Counter):
            self.lemma = copy.deepcopy(other.lemma)
            self.min = other.min
            self.max = other.max
            self.real = other.min
            self.bank = copy.deepcopy(other.bank)
            self.children = copy.deepcopy(other.children)
        else:
            self.lemma = other["lemma"]
            self.min = other["min"]

            if "max" in other:
                self.max = other["max"]
            else:
                self.max = self.min

            self.real = other["min"]

            if "bank" in other:
                self.bank = other["bank"]
            else:
                self.bank = []

            if "children" in other:
                self.children = other["children"]
            else:
                self.children = []

    def is_correct(self) -> bool:
        """
        Check the viability of the tree of counters:
        Rule:
            Every node have or children or bank of questions only one.
        """

        if bool(self.children) == bool(self.bank):
            return False

        if self.children:
            for child in self.children:
                if not child.is_correct():
                    return False

        return True

    def increment_question(self):
        """
        Increment the number of real questions of the counter
        """
        assert self.can_grow()

        self.real += 1

        if self.bank:
            return

        # locate growable children
        growable = [
            pos for (pos, counter) in enumerate(self.children) if counter.can_grow()
        ]
        to_grow = random.choice(growable)

        self.children[to_grow].increment_question()

    def update_real_questions(self, amount: int):
        """
        Increment questions until the amount
        """
        while self.real < amount:
            self.increment_question()


def combine(a_counter, b_counter):
    """
    Combine two counters into one
    """
    if not a_counter.is_single() and not b_counter.is_single():
        raise ValueError(
            f"Cannot combine <{a_counter}> with <{b_counter}>"
            " There is not any single"
        )

    if a_counter.min == -1:
        a_counter.min = b_counter.max
        a_counter.max = b_counter.max
    elif b_counter.min == -1:
        a_counter.min = a_counter.max
    else:
        if a_counter.min < b_counter.min:
            a_counter.min = b_counter.min

        if b_counter.max < a_counter.max:
            a_counter.max = b_counter.max

    if a_counter.max < a_counter.min:
        raise ValueError(
            f"Cannot combine <{a_counter.lemma}> with <{b_counter.lemma}>\n"
            f"Incorrect Range: {a_counter}\n"
            f"{b_counter}\n"
            "Non compatible counters. Cannot combine them"
        )

    a_counter.lemma = a_counter.lemma + ":" + b_counter.lemma
    a_counter.children.extend(b_counter.children)
    a_counter.bank.extend(b_counter.bank)
    a_counter.real = a_counter.min

    return a_counter
