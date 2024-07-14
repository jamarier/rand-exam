#!/usr/bin/env env/bin/python

import time
from typing import Dict, List, Optional
import random
import re
from pathlib import Path
import copy

import typer
from typing_extensions import Annotated
import yaml

from macro_engine2 import macro_engine2, load_next_macro
from tags import look_compatible_questions
from counter import Counter

# --------------------------------------------------------------------
# TODO

# --------------------------------------------------------------------
# UTILS


def header(text):
    """
    Create a banner to help to read the logs (open flag)
    """
    print("")
    print("-" * 40)
    print(f"- {text}")
    print(" ")


def label(text):
    """
    Create a banner to help to read the logs (closed banner)
    """
    length = len(text) + 4
    print("*" * length)
    print(f"* {text} *")
    print("*" * length)


# --------------------------------------------------------------------
# QUESTIONS


def check_field(field, question) -> Dict:
    """
    If the field doesn't exist it is marked in debug mesage
    """

    if field not in question or question[field] is None:
        question[field] = f"\n((COUNTER)): No {field} - DEBUG. Metadata: {question}\n\n"

    return question


def check_compulsory(question, keys):
    """
    Check the existence of compulsory keys
    """
    for key in keys:
        if key not in question or question[key] is None:
            print(f' question "{question}" has no key: "{key}"')
            raise typer.Exit(3)


def load_tags(question, filestem):
    """
    Load tags of question and add filestem and all (if it is autotag)
    """

    tags = set()

    if question["autotag"]:
        tags.add(filestem)
        tags.add("all")

    if "tags" in question:
        if isinstance(question["tags"], str):
            tags.add(question["tags"])
        if isinstance(question["tags"], list):
            for tag in question["tags"]:
                tags.add(tag)

    return tags


def inner_load_questions(input_path: Path, accumulated: List) -> List:
    """Load the questions in a directory or file.

    Returns a List.
        the values are a list of the questions
    """
    print(f"loading {input_path}")
    if input_path.is_dir():
        print("is a dir")
        for subinput in input_path.glob("*"):
            accumulated = inner_load_questions(subinput, accumulated)
    elif input_path.suffix in (".yaml", ".yml"):
        with input_path.open("r") as fh:
            questions = yaml.safe_load_all(fh)
            for question in questions:
                # allow to ignore unfinished questions
                if "ignored" in question:
                    print(" question ignored.")
                    continue

                # Temporal warning of old formats
                if question.get("difficulty", -1) == 0:
                    raise ValueError(
                        f"""
 question {question} has difficulty 0. Old format, it has to declare scaffold
 """
                    )

                # scaffold cases
                if "scaffold" in question and question["scaffold"] is not False:
                    print("scaffold")
                    question["scaffold"] = True
                    question["difficulty"] = 0
                    question["autotag"] = False
                else:
                    question["scaffold"] = False

                # default values
                question["difficulty"] = question.get("difficulty", 1)
                question["frequency"] = question.get("frequency", 1)
                question["autotag"] = question.get("autotag", True)

                # tags archiving
                question["tags"] = load_tags(question, input_path.stem)

                accumulated.append(question)

    return accumulated


def load_questions(bank_dir: Path) -> List:
    """Load questions from a bank_dir.
    wrapper of inner_load_questions.
    """
    header("Loading questions")
    questions = inner_load_questions(bank_dir, [])
    assert len(questions) > 0, "No questions in bank"

    return questions


def estimated_difficulty_tag(questions) -> float:
    """
    Estimate difficulty of question list.

    Return weighted difficulty of group of questions:
        sum(difficulty*frequency) / sum(frequency)
    """

    sum_numerator = 0
    sum_frequency = 0

    label("quesions")
    print(questions)

    for question in questions:
        print("question", question)
        if question["difficulty"] is None or question["frequency"] is None:
            print(f"question: {question} has no frequency or difficulty")
            continue

        sum_numerator += question["difficulty"] * question["frequency"]
        sum_frequency += question["frequency"]

    return sum_numerator / sum_frequency


def random_question(questions, num_questions) -> List:
    """
    questions: bank of questions (for certain part)
    num_questions: number of questions to extract
    """

    # in case all questions asked
    if len(questions) == num_questions:
        return questions

    return random_question_more(questions, num_questions)


def random_question_more(questions, num_questions) -> List:
    """
    Select num_questions questions from the list of questions
    """

    if num_questions == 1:
        return random_question_one(questions)
    if num_questions == 0:
        return []

    output = []

    one_question = random_question_one(questions)[0]
    output.append(one_question)

    new_possible_questions = [it for it in questions if it is not one_question]

    output.extend(random_question_more(new_possible_questions, num_questions - 1))

    return output


def random_question_one(questions) -> List:
    """
    Extract `num_questions` random question(s) from bank with
    certain tag
    """

    accum = 0.0
    for question in questions:
        accum += question["frequency"]

    cursor = random.random() * accum

    accum = 0.0
    for question in questions:
        accum += question["frequency"]
        if cursor < accum:
            return [question]

    return questions[-1]  # las element


# --------------------------------------------------------------------
# List of Questions


def difficulty_list(questions) -> float:
    """
    Evaluate the accumulated difficulty of a list of questions
    """
    difficulty = 0.0

    for question in questions:
        difficulty += question["difficulty"]

    return difficulty


# --------------------------------------------------------------------
# EXAM


def default_values(exam):
    """
    Define default values for parameters in index file
    Value of exam pased by reference (modified here)
    """
    # bank loading
    if "bank" not in exam:
        exam["bank"] = None
    else:
        exam["bank"] = Path(exam["bank"])

    # other parameters configuration
    # seed
    if "seed" not in exam:
        exam["seed"] = int(time.strftime("%Y%m%d")) * 10  # 10 editions

    if "tries" not in exam:
        exam["tries"] = 1000

    if "tolerance" not in exam:
        exam["tolerance"] = 0.5


def load_macros(exam):
    """
    Load macros from index file
    Value of exam pased by reference (modified here)
    """
    # loading macros
    if "macros" not in exam:
        exam["macros"] = []
    else:
        label("MACROS")

        nmacros = []

        for key, value in exam["macros"].items():
            print(key, "->", value)
            _previous, key, args, _post = load_next_macro(key)
            if args:
                nmacros.append(
                    {"constant": False, "key": key, "args": args, "value": value}
                )
            else:
                nmacros.append({"constant": True, "key": key, "value": value})

        exam["macros"] = nmacros


def load_output_files(exam):
    """
    Load the names of the output files in exam
    Value of exam pased by reference (modified here)
    """

    if "files" not in exam:
        print("files field not in exam")
        raise ValueError(f"files field not in exam: {exam.keys()}")

    # check forbiden names
    forbidden_names = [
        "scaffold",
        "difficulty",
        "autotag",
        "frequency",
        "tags",
    ]

    # Checking valid files and headers and footers of files
    files_id = []
    for file in exam["files"]:
        file_id = Path(file).stem

        if file_id in forbidden_names:
            print(f"file field <{file}> forbidden")
            raise ValueError("field forbidden)")

        files_id.append(file_id)

    exam["files_id"] = files_id


def load_exam(exam_file: Path) -> Dict:
    """
    Load exam description (not the questions)
    """
    header("Loading exam")

    with exam_file.open("r") as fh:
        exam = yaml.safe_load(fh)

    default_values(exam)
    load_macros(exam)
    # load_output_files(exam)

    return exam


def extract_possibly_questions(exam: Dict, questions: List) -> List:
    """
    Read condition for each part in exam and select question that fullfill
    the requirement.
    """

    subsets = []
    for part in exam["parts"]:
        subsets.append(look_compatible_questions(part["tag"], questions))

    return subsets


def check_exam(exam: Dict, selected_questions: List) -> bool:
    """Check integrity of exam (all tags are defined in bank of questions)
    and other possibles checks
    """

    for part, content in zip(exam["parts"], selected_questions):
        tag = part["tag"]
        if not content:
            print(f" tag <{tag}> doesn't have any question")
            return False

    return True


def estimated_difficulty_exam(exam, selected_questions) -> float:
    """Return weighted difficulty of tag sum(difficulty*frequency) / sum(frequency)"""

    difficulty = [0.0, 0.0]

    label("ede")
    print(selected_questions)

    for part, questions in zip(exam["parts"], selected_questions):
        difficulty[0] += estimated_difficulty_tag(questions) * part["num_questions"][0]
        difficulty[1] += estimated_difficulty_tag(questions) * part["num_questions"][1]

    return difficulty


def random_exam_item(exam):
    """
    Loop around parts to create a possible exam.
    """

    # extract amount of questions
    parts = copy.deepcopy(exam["parts"])

    num_of_questions = random.randint(parts.min, parts.max)
    parts.update_taken_questions(num_of_questions)
    print(label("after count finished"))
    print(parts)

    possible_exam = random_exam_item_recurse(parts)

    difficulty = difficulty_list(possible_exam)

    return (difficulty, possible_exam)


def random_exam_item_recurse(part):
    """
    runs recursively part to extracts all the questions
    """
    output = []

    if part.children:
        for child in part.children:
            output.extend(random_exam_item_recurse(child))
    else:  # part.bank
        output.extend(random_question(part.bank, part.taken))

    return output


def random_exam(exam):
    """
    Look for a exam, from questions, with difficulty (from exam)
    and with a limit of tries and tolerance.

    Select by random until tries, and provides the best attempt

    If the requirement are not fullfill, returns a small stats
    about the attemps done.

    """
    header(f"Random Exam. Difficulty: {exam['difficulty']}")

    best_difficulty, best_attempt = random_exam_item(exam)

    min_difficulty = best_difficulty
    max_difficulty = best_difficulty
    exam["tries"] -= 1

    if abs(exam["difficulty"] - best_difficulty) < exam["tolerance"]:
        return best_attempt

    for _ in range(exam["tries"]):
        new_difficulty, new_attempt = random_exam_item(exam)

        min_difficulty = (
            new_difficulty if new_difficulty < min_difficulty else min_difficulty
        )
        max_difficulty = (
            new_difficulty if max_difficulty < new_difficulty else max_difficulty
        )

        if abs(exam["difficulty"] - new_difficulty) < abs(
            exam["difficulty"] - best_difficulty
        ):
            best_difficulty = new_difficulty
            best_attempt = new_attempt

        if abs(exam["difficulty"] - best_difficulty) < exam["tolerance"]:
            return best_attempt

    print(
        f"Exam not found, range measured ({min_difficulty},{max_difficulty}) best_difficulty: {best_difficulty}"
    )
    return None


# --------------------------------------------------------------------
# MACRO ENGINE


def gen_fileid(exam):
    """
    Extract file_id from files key of exam

    return list with same order than files
    """

    return [Path(it).stem for it in exam["files"]]


def gen_filenames(index_file, exam, counter):
    """
    Generate a list of filenames in function of index_file, exam["files"] and counter
    """
    filenames = []
    base_filename = index_file.parent / index_file.stem

    for file_output in exam["files"]:
        name = Path(file_output)
        suffix = name.suffix
        name = name.stem

        if counter:
            filenames.append(
                base_filename.parent
                / (base_filename.stem + f"_{name}_{counter}" + suffix)
            )
        else:
            filenames.append(
                base_filename.parent / (base_filename.stem + f"_{name}" + suffix)
            )

    return filenames


def locate_empty_filename(index_file, exam):
    """
    Look for the first edition not generated yet.

    Return available output filenames and the edition number
    """
    counter = 0

    searching = True
    while searching:
        searching = False

        files = gen_filenames(index_file, exam, counter)
        print("Testing existence of:", files)

        for file in files:
            if file.exists():
                searching = True
                break

        if not searching:
            break

        counter += 1

    return files, counter


# --------------------------------------------------------------------
# Render


def render_exam(exam, exam_instance):
    """
    Create the output filename of description and notes.

    Apply macro engine to substitute macros and update question counter
    """
    header("Rendering")

    counter = 1
    print(exam.keys())
    print(exam["files_id"])
    print(exam["filenames"])

    output_texts = {it: "" for it in exam["files_id"]}

    # headers
    inputs = []
    for fid in exam["files_id"]:
        if f"begin_{fid}" in exam:
            inputs.append(exam[f"begin_{fid}"])
        else:
            inputs.append("")
    outputs = macro_engine2(
        0, exam["macros"], {"metadata": {}}, exam["files_id"], inputs
    )
    for index, content in zip(exam["files_id"], outputs):
        output_texts[index] += content

    # questions
    for question in exam_instance:
        label("question")
        print(question)
        inputs = []
        for fid in exam["files_id"]:
            question = check_field(fid, question)
            inputs.append(question[fid])

        outputs = macro_engine2(
            counter, exam["macros"], {"metadata": question}, exam["files_id"], inputs
        )
        for index, content in zip(exam["files_id"], outputs):
            output_texts[index] += content

        print("question", question)
        if not question["scaffold"]:
            counter += 1

    # footer
    inputs = []
    for fid in exam["files_id"]:
        if f"end_{fid}" in exam:
            inputs.append(exam[f"end_{fid}"])
        else:
            inputs.append("")
    outputs = macro_engine2(
        0, exam["macros"], {"metadata": {}}, exam["files_id"], inputs
    )
    for index, content in zip(exam["files_id"], outputs):
        output_texts[index] += content

    # writing to the files
    header("Writing the files")
    for file_id, filename in zip(exam["files_id"], exam["filenames"]):
        print("Save of", filename)
        with filename.open("w") as fh:
            fh.write(output_texts[file_id] + "\n")


# --------------------------------------------------------------------
# creación de una plantilla de index_file si esta no existe


def create_index_file(index_file: Path):
    output = """
---
comment: Catalogue of questions
difficulty: 0
file_descriptions: catalogue.md
file_notes: catalogue.m
macros:
  - ((HEADER)): |+
      ((COUNTER)) Dif. ((FOR,*,((difficulty)))) Frec. ((frequency))
  - ((HEADER_NOTES)): "((COUNTER))\n"
description: |+
  ---
  geometry: margin=4cm
  output: pdf_document
  ---
  ((comment))
notes: |+
  ((comment))
parts:
  - instrucciones
  - Parte Señal .
  - Sesión 1 . 
  - sesion1: -1
  - Sesión 2 .
  - sesion2: -1
"""

    if index_file.exists():
        raise ValueError(f"File <{index_file}> exists, cannot write over it.")
    with index_file.open("w") as fh:
        fh.write(output)


# --------------------------------------------------------------------


def main(
    index_file: Annotated[
        Path,
        typer.Argument(
            help="Structure of exam. "
            "if the file doesn't exist, I'll create one with a template for you."
        ),
    ],
    bank_dir: Annotated[
        Optional[Path], typer.Option("--bank", "-b", help="Questions to choose from")
    ] = None,
    edition: Annotated[
        Optional[int],
        typer.Option(
            "--edition", "-e", help="Force edition. If None, look for first empty"
        ),
    ] = None,
    seed: Annotated[
        Optional[int], typer.Option("--seed", "-s", help="Seed used")
    ] = None,
    tries: Annotated[
        int, typer.Option("--tries", "-a", help="Number of tries to generate exam")
    ] = None,
    tolerance: Annotated[
        float, typer.Option("--tolerance", "-t", help="Tolerance to select exam")
    ] = None,
):
    print("index_file", index_file)
    if not index_file.exists():
        create_index_file(index_file)
        print("index file created: but it is obsolete. You have to retouch")
        return

    exam = load_exam(index_file)

    # Loading options
    for parameter, cli_parameter in [
        ("bank", bank_dir),
        ("seed", seed),
        ("tries", tries),
        ("tolerance", tolerance),
    ]:
        if cli_parameter:
            exam[parameter] = cli_parameter

    # Especific options configuration
    if exam["bank"] is None:
        raise ValueError("No bank dir in index_file or CLI options")

    # Filenames + Edition
    header("Output filenames")
    if edition is None:
        filenames, edition = locate_empty_filename(index_file, exam)
    else:
        filenames = gen_filenames(index_file, exam, edition)
    print("  filenames", filenames)
    exam["filenames"] = filenames
    exam["files_id"] = gen_fileid(exam)

    exam["edition"] = edition

    random.seed(exam["seed"] + exam["edition"])

    # reading questions
    questions = load_questions(exam["bank"])

    # count bank of questions
    header("Counting questions")
    exam["parts"] = Counter(exam["parts"], questions)
    print(exam["parts"])
    if not exam["parts"].is_correct():
        print("Dying, parts description is not correct")
        raise typer.Exit(1)
    print(exam["parts"])

    # selected_questions = extract_possibly_questions(exam, questions)

    exam_instance = random_exam(exam)
    if not exam_instance:
        raise typer.Exit(2)

    print("exam wished difficulty", exam["difficulty"])
    print("real difficulty", difficulty_list(exam_instance))

    render_exam(exam, exam_instance)


if __name__ == "__main__":
    typer.run(main)
