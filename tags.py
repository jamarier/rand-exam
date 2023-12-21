"""
Tags processing and search for questions in tags
"""

from typing import Dict, List


def tag_query(tag_str: str) -> List:
    """
    Preprocess tag query from a string
    """
    query = []
    for word in tag_str.split():
        if word == ".":
            b = query.pop()
            a = query.pop()
            query.append(f"{a} {b}")
        else:
            query.append(word)

    return query


def look_compatible_questions(tag_description: List, questions: List) -> List:
    """
    Look for questions with the conditions in tag_description.

    status is a stack of boolean values
    """

    compatible_subset = []
    for question in questions:
        tags = question["tags"]
        status = []
        for word in tag_description:
            if word == "!":
                a = status.pop()
                status.append(not a)
            elif word == "&":
                a = status.pop()
                b = status.pop()
                status.append(a and b)
            elif word == "|":
                a = status.pop()
                b = status.pop()
                status.append(a or b)
            else:
                status.append(word in tags)

        assert len(status) == 1
        if status.pop():
            compatible_subset.append(question)

    return compatible_subset
