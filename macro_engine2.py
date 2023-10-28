from typing import Tuple, Mapping
import time
import random
import re


def locate_macro(text) -> Tuple[str, str, str]:
    start_pattern = re.compile(r"\(\(", re.DOTALL)
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


@register_op("VAR")
def op_VAR(args, vars) -> Tuple[str, Mapping]:
    varname = args.pop(0)
    key = args.pop(0)
    value, vars = run_function(key, *args, vars=vars)
    vars[varname] = value

    return (value, vars)


@register_op("INT")
def op_INT(args, vars) -> Tuple[str, Mapping]:
    args = [int(it) for it in args]
    return str(gen_int(*args)), vars


@register_op("VARINT")
def op_VARINT(args, vars) -> Tuple[str, Mapping]:
    varname = args.pop(0)
    return run_function("VAR", varname, "INT", *args, vars=vars)


@register_op("FLOAT")
def op_FLOAT(args, vars) -> Tuple[str, Mapping]:
    args = [float(it) for it in args]
    return str(gen_float(*args)), vars


@register_op("VARFLOAT")
def op_VARFLOAT(args, vars) -> Tuple[str, Mapping]:
    varname = args.pop(0)
    return run_function("VAR", varname, "FLOAT", *args, vars=vars)


@register_op("QUOTE")
def op_QUOTE(args, vars) -> Tuple[str, Mapping]:
    varname = args.pop(0)
    return f"t((COUNTER))_{varname}", vars


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
    previous, macro, post = locate_macro(text)

    if not macro:
        return previous

    args = macro.split(",")
    key = args.pop(0)

    # execute function in key
    result, vars = run_function(key, *args, vars=vars, macros=macros)
    if result is not None:
        text = previous + result + post
        return macro_engine2_single(macros, vars, text)

    print("~~~~~~~~Unknown function", key, args)
    10 / 0
    return text


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
        0 / 0

    return (output1, output2)
