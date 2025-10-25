#!/usr/bin/env env/bin/python
"""
Class to count number of questions
"""

import random
import re

from typing import List
import yaml

import tags


def find_questions(structure, questions) -> List:
    """
    find_questions to test
    """
    query = tags.tag_query(structure)

    # print("fake finding", structure)
    # return list(structure)  # TODO: delete this line
    return tags.look_compatible_questions(query, questions)


class Counter:
    """
    Class to measure/control/calculate number of questions in exam

    attributes:
        lemma: text to define questions
        bank: list of questions following lemma
        children: subtree in the structure of the counter
        min: min number of questions can be choosen
        max: max number of questions can be choosen
        taken: final number of questions taken
    """

    def __init__(self, structure, questions):
        self.lemma = ""
        self.bank = []
        self.children = []
        self.min = 0
        self.max = 0
        self.taken = 0

        if isinstance(structure, int):
            self._init_int(structure)
        elif isinstance(structure, str):
            self._init_str(structure, questions)
        elif isinstance(structure, list):
            self._init_list(structure, questions)

        elif isinstance(structure, dict):
            # if the dict have more than one key, each key is
            # processed independly and then trated as an array

            if len(structure) == 1:
                self._init_dict1(structure, questions)
            else:
                self._init_dict(structure, questions)

    def _init_int(self, structure: int):
        """
        Init Counter if the content is a int

        Possible values:
        - structure (input)
            - -2 -> (*,*) Any negative becomes in maximum posible. 
                          Obs: Any number of questions is (0,*), 
                               all questions is (*,*)
            - 1  -> (1,1) Any positive or zero
        - min:
            - zero or positive int (numeric minimun)
            - '*' -> max value possible 
        - max:
            - zero or positive value (bigger than min)
            - * -> max value possible
        """
        if structure > -1:
            self.min = structure
            self.max = structure
        else:
            self.min = "*"
            self.max = "*"

        self.lemma = str(structure)

    def _init_str(self, structure: str, questions: List):
        """
        Init Counter if the content is a str
        Return (min,max),

        Possible values:
        - structure (input)
            - *  -> (0,*)
            - +  -> (1,*)
            - ?  -> (0,1)
            - 2-* -> (2,*)
            - otherwhise -> ("unknown","unknown")
        - min:
            - zero or positive int (numeric minimun)
            - "unknown" -> unknown value(1)
        - max:
            - zero or positive value (bigger than min)
            - "unknown" -> unknown value(1)
            - * -> max value possible
        """
        self.lemma = structure

        structure = structure.strip()

        if structure == "*":
            self.min = 0
            self.max = "*"
            return

        if structure == "+":
            self.min = 1
            self.max = "*"
            return

        if structure == "?":
            self.min = 0
            self.max = 1
            return

        match = re.fullmatch(r"(-?\d+)", structure)
        if match:
            self._init_int(int(match[1]))
            return

        match = re.fullmatch(r"(\d+)-(\d+|\*)", structure)
        if match:
            self.min = int(match[1])
            if match[2] == "*":
                self.max = "*"
            else:
                self.max = int(match[2])
            return

        # tags -> searching for questions
        self.bank = find_questions(structure, questions)
        if self.bank:
            self.min = 1
            self.max = 1
        else:
            print(questions)
            raise ValueError(
                f"""
Lemma: <{self.lemma}> doesn't have any question in question_bank
        """
            )

    def _init_list(self, structure: list, questions):
        """
        Init Counter if the content is a list

        Possible values:
        - structure (input)
            - -2 -> (*,*) Any negative
            - 0  -> (1,1) Any positive or zero
        - min:
            - zero or positive int (numeric minimun)
            - '*' -> max value possible
        - max:
            - zero or positive value (bigger than min)
            - * -> max value possible
        """
        self.min = 0
        self.max = 0
        self.children = []
        for it in structure:
            child = Counter(it, questions)
            self._add_range(child)
            self.children.append(child)

        self.lemma = f"ARRAY[{self.children[0].lemma},...]"

    def _init_dict1(self, structure, questions):
        """
        Init Counter if the content is a one key dict

        """
        (k, v) = structure.popitem()
        self.init_pair(k, v, questions)

    def _init_dict(self, structure, questions):
        """
        Init Counter if the content is a one key dict

        """
        self.children = []
        for k, v in structure.items():
            child = Counter(None, questions)
            child.init_pair(k, v, questions)

            self._add_range(child)
            self.children.append(child)

        self.lemma = f"DICT[{self.children[0].lemma},...]"

    def init_pair(self, key, value, questions):
        """
        Init Counter if the content is a one key dict

        """
        key_counter = Counter(key, questions)
        value_counter = Counter(value, questions)

        if key_counter.bank and value_counter.is_single():
            self.lemma = key_counter.lemma
            self.bank = key_counter.bank
            self.min = 0
            self.max = len(self.bank)

            self._combine_range(value_counter)

            return

        if key_counter.is_single() and value_counter.children:
            self.lemma = value_counter.lemma
            self.children = value_counter.children
            self.min = key_counter.min
            self.max = key_counter.max

            self._combine_range(value_counter)

            return

        raise ValueError(
            f"""
Trying to pair with key:

{key_counter}

and value:
{value_counter}

and I do not know how to do it.
        """
        )

    def _combine_range(self, other):
        """
        Combine two ranges into one
        """
        if other.min == "*":
            other.min = self.max
        if other.max == "*":
            other.max = self.max

        self.min = max(self.min, other.min)
        self.max = min(self.max, other.max)

        self.taken = min(self.taken, other.taken)

        if self.max < self.min:
            raise ValueError(
                f"""
Trying to combine:

{self},
with

{other}
an empty range was obtained
(MAYBE: there isn't enought questions in the bank)
"""
            )

    def _add_range(self, other):
        """
        Calculate the size of ranges.

        Fail if one of elements have '*' in is range
        """

        if self.min == "*" or self.max == "*" or other.min == "*" or other.max == "*":
            raise ValueError(
                f"adding ranges of {self} and {other} and they are not decided yet."
            )

        self.min += other.min
        self.max += other.max

    def __str__(self):
        output = [
            f"Counter: {self.lemma}",
            f"  range: [{self.min}:{self.max}] -> {self.taken}",
        ]
        for child in self.children:
            lines = str(child).split("\n")
            for line in lines:
                output.append(f"  {line}")

        if self.bank:
            output.append(f"  bank_size: {len(self.bank)}")

        return "\n".join(output)

    def have_to_grow(self) -> bool:
        """
        Inform if the counter have to increase its taken value because is less than minimum
        """
        return self.taken < self.min

    def can_grow(self) -> bool:
        """
        Inform if the counter can increase its value
        """
        return self.taken < self.max

    def is_single(self) -> bool:
        """
        Inform if the counter hasn't children or questions in the bank
        (it is only a number or a interval)
        """
        return not (bool(self.children) or bool(self.bank))

    def is_correct(self) -> bool:
        """
        Check the viability of the tree of counters:
        Rule:
            Every node have or children or bank of questions only one.
        """

        if bool(self.children) == bool(self.bank):
            if not self.children:
                print(f"\n{self} don't have children neither bank of questions")
            else:
                print(f"\n{self} have children and bank of questions")
            return False

        if self.children:
            for child in self.children:
                if not child.is_correct():
                    return False

        return True

    # variation of question taken
    def increment_question(self):
        """
        Increment the number of real questions of the counter
        """
        assert self.can_grow()

        self.taken += 1

        if self.bank:
            return

        # locate have to grow
        haveto = [
            pos for (pos, counter) in enumerate(self.children) if counter.have_to_grow()
        ]
        if haveto:
            to_grow = haveto.pop()
            self.children[to_grow].increment_question()
            return

        # locate growable children
        growable = [
            pos for (pos, counter) in enumerate(self.children) if counter.can_grow()
        ]
        to_grow = random.choice(growable)

        self.children[to_grow].increment_question()

    def update_taken_questions(self, amount: int):
        """
        Increment questions until the amount
        """
        while self.taken < amount:
            self.increment_question()


def main():
    """
    main function to test the file
    """

    document = """
    - uno
    - 0-25:
        - tres: 2-3
        - cinco seis &: '*'
        - cinco seis .: +
        - 0-4:
            - uno: 1-2
            - dos: 1-2
            - tres: 1-2
        - 0-4:
            UNO: 1-2
            dos: 1-2
            tres: 1-2
    """

    source = yaml.safe_load(document)
    print(yaml.safe_dump(source))
    print((source))

    questions = []
    c = Counter(source, questions)
    print(c)


if __name__ == "__main__":
    main()
