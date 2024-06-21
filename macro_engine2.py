from typing import Tuple, Mapping, List
import time
import random
import re


def locate_macro(text: str) -> Tuple[str, str, str]:
    """
    Locate first invocation of macro can be resolve (when there is not nested macro)
    return the text in 3 parts: previous, macro invocation, rest

    """
    start_pattern = re.compile(r"\(\((?!\()", re.DOTALL)
    end_pattern = re.compile(r"\)\)", re.DOTALL)

    start1 = start_pattern.search(text)
    if start1 is None:
        return (text, "", "")

    previous = text[: start1.start()]
    following = text[start1.end() :]

    start2 = start_pattern.search(following)
    end2 = end_pattern.search(following)

    if end2 is None:
        raise ValueError(f"Opened macro, never closed: <{following}>")

    if start2 and start2.start() < end2.start():
        p2, m2, po2 = locate_macro(following)
        return (previous + "((" + p2, m2, po2)

    # end2.start() < start2.start()
    # or start2 is None
    macro = following[: end2.start()]
    post = following[end2.end() :]
    return (previous, macro, post)


def remove_to_nl(text: str) -> str:
    """
    Remove all text until end or newline
    """
    pos = text.find("\n")

    if pos < 0:
        return ""

    return text[pos + 1 :]


def apply_macro_user(macro, args) -> str:
    """
    Take a macro user defined and calculate the output2
    """

    if macro["constant"]:
        return macro["value"]

    target = macro["value"]
    if len(args) != len(macro["args"]):
        raise ValueError(
            f"args in macro definition <{macro['args']}> and in invocation <{args}> haven't same arity"
        )

    for it, arg in enumerate(args):
        target = target.replace(macro["args"][it], arg)

    return target


# --------------------------------------------------------------------
# arg formatters


def to_int(args: List[str]) -> List[int]:
    """
    Convert all arguments into ints
    """
    return [int(it) for it in args]


def to_float(args: List[str]) -> List[float]:
    """
    Convert all arguments into floats
    """
    return [float(it) for it in args]


# --------------------------------------------------------------------
# Random Generators


def gen_op(values) -> str:
    output = random.choice(values)

    return output


def gen_float(min, max, decimals=2) -> str:
    output = random.uniform(min, max)
    output = f"{output:.{int(decimals)}f}"

    return output


def gen_int(min, max) -> str:
    """min <= generated <= max"""
    output = random.randint(min, max)
    output = f"{output}"

    return output


def gen_range(min, max, step) -> List:
    """min <= generated << max
    step"""
    options = []
    current = min
    while current <= max:
        options.append(current)
        current += step

    return options


# --------------------------------------------------------------------
# Internal operators


# register of builders
internal_operations = {}


def register_op(name):
    """
    Decorator to register internal operations
    """

    def inner_decorator(func):
        internal_operations[name] = func
        return func

    return inner_decorator


# variable generation


@register_op("SAVE")
def op_SAVE(args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    varname = args.pop(0)
    key = args.pop(0)
    value, vars_storage = run_function(key, *args, vars_storage=vars_storage)
    vars_storage[varname] = value

    return ("", vars_storage)


@register_op("VAR")
def op_VAR(args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    varname = args.pop(0)
    key = args.pop(0)
    _, vars_storage = run_function(
        "SAVE", varname, key, *args, vars_storage=vars_storage
    )

    return (f"(({varname}))", vars_storage)


# random generators


@register_op("INT")
def op_INT(args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    """
    The third arg is the step or 1 if doesn't exist
    """
    args = to_int(args)
    if len(args) == 2:
        return str(gen_int(*args)), vars_storage
    else:
        return str(gen_op(gen_range(*args))), vars_storage


@register_op("FLOAT")
def op_FLOAT(args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    """
    FLOAT(min,max,decimals?)
    """
    args = to_float(args)

    return str(gen_float(*args)), vars_storage


@register_op("FLOATRANGE")
def op_FLOATRANGE(args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    """
    FLOATRANGE(min,max,step,decimals?)
    """
    args = to_float(args)

    # count decimals on step var
    if len(args) == 3:
        last = args[-1]
        decimals = len(str(last - int(last))) - 2
    if len(args) == 4:
        decimals = args.pop()

    return f"{gen_op(gen_range(*args)):.{int(decimals)}f}", vars_storage


@register_op("OP")
def op_OP(args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    return gen_op(args), vars_storage


@register_op("OPEXCEPT")
def op_OPEXCEPT(args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    num_except = int(args.pop(0))
    excepts = []

    print("\nnum_except", num_except)
    print("type", type(num_except))

    for _it in range(num_except):
        excepts.append(args.pop(0))

    args = [it for it in args if it not in excepts]

    return gen_op(args), vars_storage


# format content


@register_op("DATE")
def op_DATE(_args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    return time.strftime("%Y-%m-%d"), vars_storage


@register_op("FOR")
def op_FOR(args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    torepeat = args.pop(0)
    times = int(args.pop(0))

    return torepeat * times, vars_storage


@register_op("CASES")
def op_CASES(args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    """
    ((CASES,input,match1,value1,match2,value2,...,default))

    Take input and compare with match*, take value if input is equal to match.
    The last value is the default if no match is found.
        (if you do not have default, the output is empty)
    """
    tomatch = args.pop(0)
    while args:
        match_clause = args.pop(0)
        if not args:
            return match_clause, vars_storage

        value = args.pop(0)

        if tomatch == match_clause:
            return value, vars_storage

    return "", vars_storage


@register_op("ID")
def op_ID(args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    """
    Return the first argument without modification.

    Usefull when a operator requires a macro (SAVE, VAR) but you
    want to insert a literal
    """
    return args.pop(0), vars_storage


@register_op("QUOTECOMMA")
def op_QUOTECOMMA(args, vars_storage: Mapping) -> Tuple[str, Mapping]:
    r"""
    Look for all the commas inside the arg and escape them.
    ((QUOTECOMMA,1,2,3,4)) -> "1\,2\,3\,4"

    In reality, join all the arguments with "\," as separator
    """

    return r"\,".join(args), vars_storage

    # mathematical operations


@register_op("CALC")
def op_CALC(args, vars_storage) -> Tuple[str, Mapping]:
    full_calculation = " ".join(args)
    stack = []

    try:
        while args:
            print(f"CALC args: {args}")
            key = args.pop(0).strip()

            # Variable substitution
            if key in vars_storage["metadata"]:
                key = vars_storage["metadata"][key]
            elif key in vars_storage:
                key = vars_storage[key]

            # Remove empty operator
            if key == "":
                continue

            # Operators
            if key == "INT":
                value = stack.pop()
                stack.append(int(round(value)))  # round to even, then cast
            elif key == "ROUND":
                decimals = int(stack.pop())
                value = stack.pop()
                stack.append(round(value, decimals))
            elif key == "+":
                value_b = stack.pop()
                value_a = stack.pop()
                stack.append(value_a + value_b)
            elif key == "-":
                value_b = stack.pop()
                value_a = stack.pop()
                stack.append(value_a - value_b)
            elif key == "*":
                value_b = stack.pop()
                value_a = stack.pop()
                stack.append(value_a * value_b)
            elif key == "/":
                value_b = stack.pop()
                value_a = stack.pop()
                stack.append(value_a / value_b)
            else:
                stack.append(float(key))
    except IndexError as exc:
        print(f"\nERROR in CALC -> Args: {full_calculation}")
        raise IndexError from exc

    if len(stack) > 1:
        raise ValueError(f"To much depth in stack: <{stack}>")

    return str(stack[0]), vars_storage


def print_operations():
    """
    Print defined operations
    """
    print("Internal Operations:")
    for it in internal_operations:
        print(" ", it)


print_operations()


# --------------------------------------------------------------------
# Macro engine
def run_function(key, *args, vars_storage, macros={}) -> Tuple[str, Mapping]:
    """
    Execute function "key" with arguments
    """

    print("RUN_FUNCTION:", key, ",".join(args), end=" --> ")
    text = None

    # metadata
    if key in vars_storage["metadata"]:
        text = str(vars_storage["metadata"][key])

    # vars_storage
    elif key in vars_storage:
        text = vars_storage[key]

    # macros
    elif key in macros:
        text = apply_macro_user(macros[key], args)

    # internal functions
    elif key in internal_operations:
        text, vars_storage = internal_operations[key](list(args), vars_storage)

    print(text)

    return text, vars_storage


def load_next_macro(text: str) -> Tuple:
    """
    Load next macro and return a tuple with all elements to process

    if the text has "\\,", the comma isn't used as split of args

    Return values: (previous, macro_name, args, post)
    where:
        previous: all the text before de macro
        macro_name: the name of the macro
        args: array of args or [] if there is no args
        post: text after macro call
    """
    previous, macro, post = locate_macro(text)

    if not macro:
        return (previous, "", [], "")

    args = macro.split(",")

    # escape of comma
    nargs = []
    escaped_comma = False
    for arg in args:
        if escaped_comma:
            nargs[-1] = nargs[-1][0:-1] + ","
            nargs[-1] += arg
        else:
            nargs.append(arg)

        escaped_comma = arg[-1] == "\\"
    args = nargs

    key = args.pop(0)

    return (previous, key, args, post)


def macro_engine2_single(macros, vars_storage, text) -> str:
    r"""
     In this engine, the activation of a macro is always in the shape:
         ((name,args,args,...))

     Double parentheses and a list split with commas.

     They are processes from begining to end from inside to outside, so
     ((1,((2)),((3)),)) ((4,((5))))

    The order to resolve: 2, 3, 1, 5, 4

     (To avoid to parse it is possible to escape some chars:
      "\\" -> "\" two bars -> one bar
      "\(" -> "(" bar + open parentheses -> open parentheses
      "\)" -> ")" bar + close parentheses -> close parentheses

      So "(\(DATE)\)" -> "((DATE))" without calling the function

      the close parentheses is not always required. depend on the context

    """
    previous, key, args, post = load_next_macro(text)
    if not key:
        # unscaping
        output = ""
        scape = False
        for char in previous:
            if scape:
                if char in "\\(),":
                    output += char
                else:
                    output += f"\\{char}"
                scape = False
            else:
                if char == "\\":
                    scape = True
                else:
                    output += char

        return output

    # DNL, remove from macro invocation to newline inclusive
    if key == "DNL":
        post = remove_to_nl(post)
        text = previous + post
        return macro_engine2_single(macros, vars_storage, text)

    # execute function in key
    result, vars_storage = run_function(
        key, *args, vars_storage=vars_storage, macros=macros
    )
    if result is not None:
        text = previous + result + post
        return macro_engine2_single(macros, vars_storage, text)

    raise ValueError("~~~~~~~~Unknown function", key, args)


def macro_engine2(counter, macros, vars_storage, files_id, texts) -> List[str]:
    """
    Second version of the macro engine.

    Inputs:
    * counter: current counter
    * macros: macro definitions
    * vars_storage defined

    * list of texts to process with same macro and vars definitions

    look for macro_engine2_single for information about the working of the
    engine

    """

    output_texts = []
    # updating data to engine2
    # copy to avoid the manipulation of original data in macro_engine2
    vars_storage2 = dict(vars_storage.items())
    vars_storage2["metadata"]["COUNTER"] = counter

    macros2 = {}
    for it in macros:
        output = {}
        key = it["key"]
        output["constant"] = it["constant"]
        output["value"] = it["value"]
        if "args" in it:
            output["args"] = it["args"]

        macros2[key] = output

    # calling for each part
    for file_id, text in zip(files_id, texts):
        vars_storage2["metadata"]["FILE"] = file_id
        # cache of the original text un processed
        if file_id in vars_storage2["metadata"]:
            vars_storage2["metadata"][f"{file_id}_raw"] = vars_storage2["metadata"][
                file_id
            ]
        # cache of processed text
        vars_storage2["metadata"][file_id] = macro_engine2_single(
            macros2, vars_storage2, text
        )
        output_texts.append(vars_storage2["metadata"][file_id])

    return output_texts
