#!/usr/bin/env .env/bin/python

import typer
from typing import Mapping, List, Tuple, Optional
from typing_extensions import Annotated

import yaml
import random
import re
from pathlib import Path

# --------------------------------------------------------------------
# TODO

# Posibility to create macros in exam file (e.g. to uniform headers)
#   they are processed before VAR operators

# --------------------------------------------------------------------
# UTILS

def header(text):
    print("-"*40)
    print(f"- {text}")
    print(" ")

def label(text):
    length = len(text)+4
    print("*"*length)
    print(f"* {text} *")
    print("*"*length)

# --------------------------------------------------------------------
# QUESTIONS
def inner_load_questions(input: Path, accumulated: Mapping) -> Mapping:
    """Load the questions in a directory or file. """
    print(f'loading {input}')
    if input.is_dir():
        for subinput in input.glob('*'):
            accumulated = inner_load_questions(subinput, accumulated)
    elif input.suffix == '.yaml' or input.suffix == '.yml':

        with input.open("r") as fh:
            questions = yaml.safe_load_all(fh)
            for question in questions:
                if 'description' not in question:
                    print(f' question "{question}" has no key: "description"')
                    raise typer.Exit(3)

                if question['description'] is None:
                    question['description'] = "VARNUM: No description - DEBUG\n"

                if 'ignored' in question:
                    print(" question ignored")
                    continue

                # compulsory keys 
                for key in ['tags', 'description', 'difficulty']:
                    if key not in question or question[key] is None:
                        print(f' question "{question}" has no key: "{key}"')
                        raise typer.Exit(3)
 
                # default values
                question['regex'] = question.get('regex', "auto")
                question['notes'] = question.get('notes', None)
                question['frequency'] = question.get('frequency',1)
                question['title'] = question.get('title', question['description'][0:80])
                            
                # Numbering
                if question['regex'] == 'auto': 
                    if "VAR" in question['description'] or (question['notes'] is not None and "VAR" in question['notes']):
                        question['regex'] = True
                    else:
                        question['regex'] = False



                # tags archiving
                for tag in question['tags']:
                    if tag not in accumulated:
                        accumulated[tag] = []
                    accumulated[tag].append(question)

                if question['regex']:
                    accumulated['all'].append(question)

    return accumulated

def load_questions(bank_dir: Path) -> Mapping:
    """Load questions from a bank_dir. 
    wrapper of inner_load_questions. 
    """
    header("Loading questions")
    questions = inner_load_questions(bank_dir, {'all':[]})

    return questions

def estimated_difficulty_tag(questions,tag) -> float:
    """
    Estimate difficulty of question list.

    Return weighted difficulty of tag sum(difficulty*frequency) / sum(frequency)
    """

    sum_numerator = 0
    sum_frequency = 0

    for question in questions[tag]:
        if question['difficulty'] is None or question['frequency'] is None:
            print(f'question: {question["title"]} has no frequency or difficulty')
            continue

        sum_numerator += question['difficulty']*question['frequency']
        sum_frequency += question['frequency']

    return sum_numerator/sum_frequency

def random_question(questions,tag,num_questions=1) -> List:
    """
    Extract `num_questions` random question(s) from bank with
    certain tag
    """
    questions_tag = questions[tag]
    assert(len(questions_tag)>=num_questions)
    
    if len(questions_tag) == num_questions or num_questions < 0:
        return questions_tag

    if num_questions == 1:
        accum = 0.0
        for question in questions_tag:
            accum += question['frequency']

        cursor = random.random()*accum

        accum = 0.0
        for question in questions_tag:
            accum += question['frequency']
            if cursor < accum:
                return [question]

    if num_questions > 1:
        output = []

        one_question = random_question(questions, tag)[0]
        output.append(one_question)

        new_possible_questions = {tag: [ it for it in questions_tag if it is not one_question]}
        output.extend(random_question(new_possible_questions, tag, num_questions-1))

        return output

    return [] # 0 options

# --------------------------------------------------------------------
# List of Questions

def difficulty_list(questions) -> float:
    """
    Evaluate the accumulated difficulty of a list of questions
    """
    difficulty = 0.0

    for question in questions:
        difficulty += question['difficulty']

    return difficulty

# --------------------------------------------------------------------
# EXAM

def load_exam(exam_file: Path) -> Mapping:
    header("Loading exam")

    with exam_file.open("r") as fh:
        exam = yaml.safe_load(fh)


    # loading elements o parts
    new_parts = []

    for part in exam['parts']:
        # default values
        npart = {'num_questions':1}

        # loading data
        if isinstance(part, str):
            npart['tag'] = part
        else: 
            npart.update(part)

        new_parts.append(npart)

    exam['parts'] = new_parts

    # loading macros
    if 'macros' not in exam:
        exam['macros'] = []
    else:
        label('MACROS')

        nmacros = []

        for macro in exam['macros']:
            for key,value in macro.items(): # there is only one macro per entry, but the for is easy to extract that element
                print(key,'->', value)
                if '(' in key:
                    nmacro = {'constant':False, 'value':value} 

                    pattern = re.compile(r'([^()]+)\(([^()]+)\)')
                    match = pattern.search(key)
                    if match:
                        macroname = match.group(1)
                        args = [it for it in match.group(2).split(',')]

                        nmacro['key'] = macroname
                        nmacro['args'] = args
                    else:
                        print("Illegal macro in exam description:",macro)
                        raise typer.Exit(4)

                    nmacros.append(nmacro)
                else:
                    # constant macro
                    nmacros.append({'constant':True,'key':key, 'value':value})


        exam['macros'] = nmacros

    return exam

def check_exam(exam: Mapping, questions: Mapping) -> bool:
    """Check integrity of exam (all tags are deffined in bank of questions)
    and other possibles checks
    """
    
    for part in exam['parts']:
        if part['tag'] not in questions:
            print("Checking exam:")
            print(f"  Part: {part} has invalid tag")
            return False

    return True

def estimated_difficulty_exam(exam,questions) -> float:
    """Return weighted difficulty of tag sum(difficulty*frequency) / sum(frequency)"""

    difficulty = 0.0

    for question in exam['parts']:
        difficulty += estimated_difficulty_tag(questions, question['tag'])*question['num_questions']

    return difficulty 


def random_exam_item(exam,questions):
    possible_exam = []

    for part in exam['parts']:
        possible_exam.extend(random_question(questions, part['tag'], part['num_questions']))

    difficulty = difficulty_list(possible_exam)

    return (difficulty, possible_exam)


def random_exam(exam, questions, tries, tolerance):
    header("Random Exam")

    best_difficulty,best_attempt = random_exam_item(exam, questions)
    min_difficulty = best_difficulty
    max_difficulty = best_difficulty
    tries -= 1

    if abs(exam['difficulty']- best_difficulty) < tolerance:
        return best_attempt

    for _ in range(tries):
        new_difficulty, new_attempt = random_exam_item(exam, questions)

        min_difficulty = new_difficulty if new_difficulty < min_difficulty else min_difficulty
        max_difficulty = new_difficulty if max_difficulty < new_difficulty else max_difficulty

        if abs(exam['difficulty']- new_difficulty) < abs(exam['difficulty']- best_difficulty):
            best_difficulty = new_difficulty
            best_attempt = new_attempt

        if abs(exam['difficulty']- best_difficulty) < tolerance:
            return best_attempt

         
    print(f"Not found, range measured ({min_difficulty},{max_difficulty}) best_difficulty: {best_difficulty}")
    return None
    


# --------------------------------------------------------------------
# MACROS 

def apply_macro(macros: Mapping, text:str, vars) -> Tuple[str,Mapping]:
    for macro in macros:
        if macro['constant']:
            text = text.replace(macro['key'], macro['value'])
            continue

        # macro with arguments (we are going to build a "special const macro")
        pattern = re.compile(f'{macro["key"]}\\(([^()]+)\\)')
        match = pattern.search(text)

        if match:
            source = match.group(0)
            args = [it for it in match.group(1).split(',')]
            
            target = macro['value']
            if len(args) != len(macro['args']):
                print(f"Wrong invocation of macro: {macro}, in text: {text}")
                raise typer.Exit(5)

            for it,arg in enumerate(args):
                target = target.replace(macro['args'][it],arg)

            text = text.replace(source,target)

    return (text,vars)

def apply_macro_old(macros: Mapping, text:str, vars) -> Tuple[str,Mapping]:
    for key,value in macros.items():
        text = text.replace(key, value)

    return (text,vars)

def op_VARFLOAT(text: str, vars) -> Tuple[str, Mapping]:
    pattern = re.compile(r'VARFLOAT\(([^()]+)\)')
    match = pattern.search(text)
    while(match):
        args = [it for it in match.group(1).split(',')]
        varname = args.pop(0)
        vars[varname] = gen_float(*[float(it) for it in args])
        text = pattern.sub(lambda _: f'{vars[varname]}',text, count=1)
        match = pattern.search(text)

    return (text,vars)

def op_VARFLOATRANGE(text: str, vars) -> Tuple[str, Mapping]:
    pattern = re.compile(r'VARFLOATRANGE\(([^()]+)\)')
    match = pattern.search(text)
    while(match):
        args = [it for it in match.group(1).split(',')]
        varname = args.pop(0)
        options = []
        current = float(args[0])
        end = float(args[1])
        step = float(args[2])
        decimals = 2
        if len(args)>3:
            decimals = int(args[3])
        while ( current < end):
            options.append(f"{current:.{decimals}f}")
            current += step
        vars[varname] = gen_op(options)
        text = pattern.sub(lambda _: f'{vars[varname]}',text, count=1)
        match = pattern.search(text)

    return (text,vars)

def op_VARINT(text: str, vars) -> Tuple[str, Mapping]:
    pattern = re.compile(r'VARINT\(([^()]+)\)')
    match = pattern.search(text)
    while(match):
        args = [it for it in match.group(1).split(',')]
        varname = args.pop(0)
        vars[varname] = gen_int(*[int(it) for it in args])
        text = pattern.sub(lambda _: f'{vars[varname]}',text, count=1)
        match = pattern.search(text)

    return (text,vars)

def op_VARINTRANGE(text: str, vars) -> Tuple[str, Mapping]:
    pattern = re.compile(r'VARINTRANGE\(([^()]+)\)')
    match = pattern.search(text)
    while(match):
        args = [it for it in match.group(1).split(',')]
        varname = args.pop(0)
        options = []
        current = int(args[0])
        end = int(args[1])
        step = int(args[2])
        while ( current < end):
            options.append(f"{current}")
            current += step
        vars[varname] = gen_op(options)
        text = pattern.sub(lambda _: f'{vars[varname]}',text, count=1)
        match = pattern.search(text)

    return (text,vars)

def op_VAROP(text:str, vars) -> Tuple[str, Mapping]:
    pattern = re.compile(r'VAROP\(([^()]+)\)')
    match = pattern.search(text)
    while(match):
        args = [it for it in match.group(1).split(',')]
        varname = args.pop(0)
        vars[varname] = gen_op(args)
        text = pattern.sub(lambda _: f'{vars[varname]}',text, count=1)
        match = pattern.search(text)

    return (text,vars)

def op_VARM(text:str, vars: Mapping) -> Tuple[str, Mapping]:
    pattern = re.compile(r'VARM\(([^()]+)\)')
    text = pattern.sub(lambda m: f'{vars["metadata"][m.group(1)]}',text)

    return (text,vars)
def op_VARV(text:str, vars: Mapping) -> Tuple[str, Mapping]:
    pattern = re.compile(r'VARV\(([^()]+)\)')
    text = pattern.sub(lambda m: f'{vars[m.group(1)]}',text, count=1)

    return (text,vars)

def op_VARQ(text:str, vars: Mapping) -> Tuple[str, Mapping]:
    text = re.sub(r'VARQ\(([^()]+)\)',r'tVARNUM_\1',text) 

    return (text,vars)

def apply_varnum(counter, text:str, vars: Mapping) -> Tuple[str, Mapping]:
    text = text.replace("VARNUM",f"{counter}")

    return (text,vars)

# --------------------------------------------------------------------
# Random Generators


def gen_op(values) -> str:
    output = random.choice(values)

    return output

def gen_float(min,max,decimals=2) -> str:
    output = random.uniform(min,max)
    output = f"{output:.{int(decimals)}f}"

    return output

def gen_int(min,max) -> str:
    """ min <= generated <= max """
    output = random.randint(min,max)
    output = f"{output}"

    return output

# --------------------------------------------------------------------
# MACRO ENGINE

def gen_filenames(exam,counter):
    filename1 = Path(exam['file_descriptions'])
    filename2 = Path(exam['file_notes'])

    if counter:
        file1 = filename1.parent / (filename1.stem + f"_{counter}" + filename1.suffix)
        file2 = filename2.parent / (filename2.stem + f"_{counter}" + filename2.suffix)
        return(file1,file2)
    else:
        # counter == 0
        return (filename1,filename2)

def locate_empty_filename(exam):
    counter = 0

    file1,file2 = gen_filenames(exam,counter)

    print("testing", file1, file2)
    while ( file1.exists() or file2.exists()):
        counter += 1
        file1,file2 = gen_filenames(exam,counter)
        print("testing", file1, file2)

    return (file1,file2)
 
def macro_step(text, vars, function):
    """
    Apply a macro to a string
    """
    previous = text
    text,vars = function(text,vars)
    return (previous!=text,text,vars)

def macro_step2(text1,text2, vars, function):
    """
    Apply same macro to two string (description and notes)
    """
    run1, text1, vars = macro_step(text1, vars, function)
    run2, text2, vars = macro_step(text2, vars, function)

    return (run1 or run2, text1, text2, vars)

def macro_engine(counter, macros, vars, text_d, text_n) -> Tuple[str,str]:
    run = True

    while(run):
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, lambda t,v: apply_macro(macros,t,v))
        if run:
            continue


        # metadata
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, op_VARM)
        if run:
            continue

        # macros with variable definitions
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, op_VARFLOAT)
        if run:
            continue
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, op_VARFLOATRANGE)
        if run:
            continue
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, op_VARINT)
        if run:
            continue
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, op_VARINTRANGE)
        if run:
            continue
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, op_VAROP)
        if run:
            continue

        # macros with variables names 
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, op_VARV)
        if run:
            continue
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, op_VARQ)
        if run:
            continue
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, lambda t,v: apply_varnum(counter,t,v))
        if run:
            continue

    return (text_d, text_n)

# --------------------------------------------------------------------
# Render

def render_exam(exam, filenames, exam_instance):
    header("Rendering")

    filename_description, filename_notes = filenames 

    counter = 1

    with filename_description.open("w") as fh_d, filename_notes.open("w") as fh_n:
        if 'description' in exam:
            text_d = exam['description']
            fh_d.write(text_d+'\n')

        if 'notes' in exam:
            text_n = exam['notes']
            fh_n.write(text_n+'\n')

        for question in exam_instance:
            header("question")
            print(question['title'])

            text_d = question['description']
            text_n = question['notes'] if question['notes'] else ''

            # functions
            if question['regex']:
                text_d,text_n = macro_engine(counter, exam['macros'], 
                                             {'metadata': question}, text_d, text_n)

                counter += 1

            fh_d.write(text_d+'\n')
            fh_n.write(text_n+'\n')

    label(f"Generated {filename_description} and {filename_notes}")

# --------------------------------------------------------------------


def main(index_file: Annotated[Path,typer.Argument(help='Structure of exam')],
         bank_dir: Annotated[Path, typer.Argument(help='Questions to choose')],
         edition: Annotated[Optional[int], typer.Option('--edition','-e',help="Force edition. If None, look for first empty")]=None,
         seed: Annotated[Optional[int], typer.Option('--seed','-s',help="Seed used")]=None,
         tries: Annotated[int, typer.Option('--tries','-a',help='Number of tries to generate exam')]=1000,
         tolerance: Annotated[float, typer.Option('--tolerance','-t',help='Tolerance to select exam')]=0.5,
         ):
    print("index_file", index_file)
    print("bank_dir", bank_dir)

    random.seed(seed)

    questions = load_questions(bank_dir)

    exam = load_exam(index_file)
    if not check_exam(exam,questions):
        print('Dying')
        raise typer.Exit(1)

    # output filename construction
    if edition is None:
        filenames = locate_empty_filename(exam)
    else:
        filenames = gen_filenames(exam,edition)

    exam_instance = random_exam(exam, questions, tries, tolerance)
    if not exam_instance:
        raise typer.Exit(2)

    print("exam wished difficulty", exam['difficulty'])
    print('exam average difficulty:', estimated_difficulty_exam(exam,questions))
    print('real difficulty', difficulty_list(exam_instance))

    render_exam(exam, filenames, exam_instance)

if __name__ == "__main__":
    typer.run(main)


