from typing import Mapping, List, Tuple, Optional
from typing_extensions import Annotated
import time

import random
import re

# --------------------------------------------------------------------
# MACROS


def apply_macro(macros: Mapping, text: str, vars) -> Tuple[str, Mapping]:
    for macro in macros:
        if macro["constant"]:
            text = text.replace(macro["key"], macro["value"])
            continue

        # macro with arguments (we are going to build a "special const macro")
        pattern = re.compile(f'{macro["key"]}\\(([^()]+)\\)')
        match = pattern.search(text)

        if match:
            source = match.group(0)
            args = [it for it in match.group(1).split(",")]

            target = macro["value"]
            if len(args) != len(macro["args"]):
                print(f"Wrong invocation of macro: {macro}, in text: {text}")
                raise typer.Exit(5)

            for it, arg in enumerate(args):
                target = target.replace(macro["args"][it], arg)

            text = text.replace(source, target)

    return (text, vars)


def op_VARFLOAT(text: str, vars) -> Tuple[str, Mapping]:
    pattern = re.compile(r"VARFLOAT\(([^()]+)\)")
    match = pattern.search(text)
    while match:
        args = [it for it in match.group(1).split(",")]
        varname = args.pop(0)
        vars[varname] = gen_float(*[float(it) for it in args])
        text = pattern.sub(lambda _: f"{vars[varname]}", text, count=1)
        match = pattern.search(text)

    return (text, vars)


def op_VARFLOATRANGE(text: str, vars) -> Tuple[str, Mapping]:
    pattern = re.compile(r"VARFLOATRANGE\(([^()]+)\)")
    match = pattern.search(text)
    while match:
        args = [it for it in match.group(1).split(",")]
        varname = args.pop(0)
        options = []
        current = float(args[0])
        end = float(args[1])
        step = float(args[2])
        decimals = 2
        if len(args) > 3:
            decimals = int(args[3])
        while current < end:
            options.append(f"{current:.{decimals}f}")
            current += step
        vars[varname] = gen_op(options)
        text = pattern.sub(lambda _: f"{vars[varname]}", text, count=1)
        match = pattern.search(text)

    return (text, vars)


def op_VARINT(text: str, vars) -> Tuple[str, Mapping]:
    pattern = re.compile(r"VARINT\(([^()]+)\)")
    match = pattern.search(text)
    while match:
        args = [it for it in match.group(1).split(",")]
        varname = args.pop(0)
        vars[varname] = gen_int(*[int(it) for it in args])
        text = pattern.sub(lambda _: f"{vars[varname]}", text, count=1)
        match = pattern.search(text)

    return (text, vars)


def op_VARINTRANGE(text: str, vars) -> Tuple[str, Mapping]:
    pattern = re.compile(r"VARINTRANGE\(([^()]+)\)")
    match = pattern.search(text)
    while match:
        args = [it for it in match.group(1).split(",")]
        varname = args.pop(0)
        options = []
        current = int(args[0])
        end = int(args[1])
        step = int(args[2])
        while current < end:
            options.append(f"{current}")
            current += step
        vars[varname] = gen_op(options)
        text = pattern.sub(lambda _: f"{vars[varname]}", text, count=1)
        match = pattern.search(text)

    return (text, vars)


def op_VAROP(text: str, vars) -> Tuple[str, Mapping]:
    pattern = re.compile(r"VAROP\(([^()]+)\)")
    match = pattern.search(text)
    while match:
        args = [it for it in match.group(1).split(",")]
        varname = args.pop(0)
        vars[varname] = gen_op(args)
        text = pattern.sub(lambda _: f"{vars[varname]}", text, count=1)
        match = pattern.search(text)

    return (text, vars)


def op_VARM(text: str, vars: Mapping) -> Tuple[str, Mapping]:
    pattern = re.compile(r"VARM\(([^()]+)\)")
    print("metadata:")
    print(vars)
    text = pattern.sub(lambda m: f'{vars["metadata"][m.group(1)]}', text)

    return (text, vars)


def op_VARDATE(text: str, vars: Mapping) -> Tuple[str, Mapping]:
    text = re.sub(r"VARDATE", time.strftime("%Y-%m-%d"), text)

    return (text, vars)


def op_VARV(text: str, vars: Mapping) -> Tuple[str, Mapping]:
    pattern = re.compile(r"VARV\(([^()]+)\)")
    text = pattern.sub(lambda m: f"{vars[m.group(1)]}", text, count=1)

    return (text, vars)


def op_VARQ(text: str, vars: Mapping) -> Tuple[str, Mapping]:
    text = re.sub(r"VARQ\(([^()]+)\)", r"tVARNUM_\1", text)

    return (text, vars)


def op_VARFOR(text: str, vars: Mapping) -> Tuple[str, Mapping]:
    pattern = re.compile(r"VARFOR\(([^()]+)\)")
    match = pattern.search(text)
    if match:
        args = [it for it in match.group(1).split(",")]
        torepeat = args.pop(0)
        times = int(args.pop(0))
        if times <= 0:
            return (text, vars)

        text = re.sub(pattern, torepeat * times, text)

    return (text, vars)


def apply_varnum(counter, text: str, vars: Mapping) -> Tuple[str, Mapping]:
    text = text.replace("VARNUM", f"{counter}")

    return (text, vars)


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
# MACRO ENGINE


def macro_step(text, vars, function):
    """
    Apply a macro to a string
    """
    previous = text
    text, vars = function(text, vars)
    return (previous != text, text, vars)


def macro_step2(text1, text2, vars, function):
    """
    Apply same macro to two string (description and notes)
    """
    run1, text1, vars = macro_step(text1, vars, function)
    run2, text2, vars = macro_step(text2, vars, function)

    return (run1 or run2, text1, text2, vars)


def macro_engine(counter, macros, vars, text_d, text_n) -> Tuple[str, str]:
    """
    This macro process text_d and text_n with the state of:
    * counter: current counter
    * macros: macro definitions
    * Vars defined

    and the texts
    """
    run = True

    while run:
        run, text_d, text_n, vars = macro_step2(
            text_d, text_n, vars, lambda t, v: apply_macro(macros, t, v)
        )
        if run:
            continue

        # metadata
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, op_VARM)
        if run:
            continue

        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, op_VARDATE)
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
        run, text_d, text_n, vars = macro_step2(
            text_d, text_n, vars, lambda t, v: apply_varnum(counter, t, v)
        )
        if run:
            continue
        run, text_d, text_n, vars = macro_step2(text_d, text_n, vars, op_VARFOR)
        if run:
            continue

    return (text_d, text_n)
