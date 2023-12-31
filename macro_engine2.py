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
    else:
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


def range(min, max, step) -> List:
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
def op_SAVE(args, vars: Mapping) -> Tuple[str, Mapping]:
    varname = args.pop(0)
    key = args.pop(0)
    value, vars = run_function(key, *args, vars=vars)
    vars[varname] = value

    return ("", vars)


@register_op("VAR")
def op_VAR(args, vars: Mapping) -> Tuple[str, Mapping]:
    varname = args.pop(0)
    key = args.pop(0)
    _, vars = run_function("SAVE", varname, key, *args, vars=vars)

    return (f"(({varname}))", vars)


# random generators


@register_op("INT")
def op_INT(args, vars: Mapping) -> Tuple[str, Mapping]:
    """
    The third arg is the step or 1 if doesn't exist
    """
    args = to_int(args)
    if len(args) == 2:
        return str(gen_int(*args)), vars
    else:
        return str(gen_op(range(*args))), vars


@register_op("FLOAT")
def op_FLOAT(args, vars: Mapping) -> Tuple[str, Mapping]:
    """
    FLOAT(min,max,decimals?)
    """
    args = to_float(args)

    return str(gen_float(*args)), vars


@register_op("FLOATRANGE")
def op_FLOATRANGE(args, vars: Mapping) -> Tuple[str, Mapping]:
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

    return f"{gen_op(range(*args)):.{int(decimals)}f}", vars


@register_op("OP")
def op_OP(args, vars: Mapping) -> Tuple[str, Mapping]:
    return gen_op(args), vars


# format content


@register_op("DATE")
def op_DATE(args, vars: Mapping) -> Tuple[str, Mapping]:
    return time.strftime("%Y-%m-%d"), vars


@register_op("FOR")
def op_FOR(args, vars: Mapping) -> Tuple[str, Mapping]:
    torepeat = args.pop(0)
    times = int(args.pop(0))

    return torepeat * times, vars


@register_op("CASES")
def op_CASES(args, vars: Mapping) -> Tuple[str, Mapping]:
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
            return match_clause, vars

        value = args.pop(0)

        if tomatch == match_clause:
            return value, vars

    return "", vars


@register_op("ID")
def op_ID(args, vars: Mapping) -> Tuple[str, Mapping]:
    return args.pop(0), vars


# mathematical operations


@register_op("CALC")
def op_CALC(args, vars) -> Tuple[str, Mapping]:
    stack = []

    while args:
        key = args.pop(0).strip()

        # Variable substitution
        if key in vars["metadata"]:
            key = vars["metadata"][key]
        elif key in vars:
            key = vars[key]

        # Remove empty operator
        if key == "":
            continue

        # Operators
        if key == "INT":
            value = stack.pop()
            stack.append(int(round(value)))  # round to even, then cast
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

    if len(stack) > 1:
        raise ValueError(f"To much depth in stack: <{stack}>")

    return str(stack[0]), vars


print("Internal Operations:")
for name in internal_operations:
    print(" ", name)


# --------------------------------------------------------------------
# Macro engine
def run_function(key, *args, vars, macros={}) -> Tuple[str, Mapping]:
    """
    Execute function "key" with arguments
    """

    print("RUN_FUNCTION:", key, ",".join(args), end=" --> ")
    text = None

    # metadata
    if key in vars["metadata"]:
        text = str(vars["metadata"][key])

    # vars
    elif key in vars:
        text = vars[key]

    # macros
    elif key in macros:
        text = apply_macro_user(macros[key], args)

    # internal functions
    elif key in internal_operations:
        text, vars = internal_operations[key](list(args), vars)

    print(text)

    return text, vars


def load_next_macro(text: str) -> Tuple:
    """
    Load next macro and return a tuple with all elements to process

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
    key = args.pop(0)

    return (previous, key, args, post)


def macro_engine2_single(macros, vars, text) -> str:
    """
     In this engine, the activation of a macro is always in the shape:
         ((name,args,args,...))

     Double parenteses and a list split with commas.

     They are processes from begining to end from inside to outside, so
     ((1,((2)),((3)),)) ((4,((5))))

    The order to resolve: 2, 3, 1, 5, 4

     (To avoid to parse)

    """
    previous, key, args, post = load_next_macro(text)
    if not key:
        return previous

    # DNL, remove from macro invocation to newline inclusive
    if key == "DNL":
        post = remove_to_nl(post)
        text = previous + post
        return macro_engine2_single(macros, vars, text)

    # execute function in key
    result, vars = run_function(key, *args, vars=vars, macros=macros)
    if result is not None:
        text = previous + result + post
        return macro_engine2_single(macros, vars, text)

    raise ValueError("~~~~~~~~Unknown function", key, args)


def macro_engine2(counter, macros, vars, text_d, text_n) -> Tuple[str, str]:
    """
    Second version of the macro engine.

    Inputs:
    * counter: current counter
    * macros: macro definitions
    * Vars defined

    look for macro_engine2_single for information about the working of the
    engine

    First is procesed text_d and then text_n

    """

    # updating data to engine2
    vars2 = {k: v for k, v in vars.items()}
    vars2["metadata"]["COUNTER"] = counter

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
    output1 = macro_engine2_single(macros2, vars2, text_d)
    output2 = macro_engine2_single(macros2, vars2, text_n)

    if "STOP" in output1 or "STOP" in output2:
        print("----")
        print(output1)
        print("---")
        print(output2)
        # 0 / 0

    return (output1, output2)
