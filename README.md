# Examen generator

From a bank of questions, it generates two text files one with questions ("exam
description") and the other with answers ("exam answers"). 

The exam is generated in any text format: markdown, LaTeX, python, octave,
whatever.

The answers are generated in any text format. In my case, the alumns write an
octave script and the answers section of the questions are code to verify the
values of the answer of the alumn. But, you can put the literal answers. 

Each question has a difficulty metadata and a frequency metadata. 

The exam is build to fullfill a total difficulty requirement. And each question
has a probability to appear in function of the frequency metadata.

A simple, but powerfull, macro system is defined. You can generate random
values in several ways, use later, define common headers, and functions (all
using string substitution)

## Options

Usage: gen-exlab.py [OPTIONS] INDEX_FILE BANK_DIR

Arguments:

*  INDEX_FILE  Structure of exam  [required]
*  BANK_DIR    Questions to choose  [required]

Options:

* -e, --edition INTEGER  Force edition. If None, look for first empty

    It is possible to generate different versions of the exam (with same
    INDEX_FILE (different questions but same difficulty and categories)

* -s, --seed INTEGER     Seed used

    To force the rebuild an exam with same questions and values. BE CAREFUL, 
    the same random generator is used to select questions and random values, if
    the BANK_DIR is altered (i.e. adding a random var in a question). 
    Can alter the questions (CHECK)

* -a, --tries INTEGER    Number of tries to generate exam  [default: 1000]

    The exam is generate trying random posibilities. This parameter says how
    many tries do.

    If the target is not achieved, inform of the best result, the maximum
    difficulty generated and the minimum.

* -t, --tolerance FLOAT  Tolerance to select exam  [default: 0.5]

    Sets the range of values to stop searching an exam. if target difficulty is
    11 and tolerance is 1, it stop if calculated difficulty value is in
    [11-1,11+1]

* --help                 Show this message and exit.

## INDEX_FILE

Description of the exam in a yaml file. 

Structure:
```yaml
---
comment: <text>
difficulty: <number>
file_descriptions: <filename1>
file_notes: <filename2>
macros:
    - ...
description: <text>
notes: <text>
parts:
    - ...
```

Description of attributes:

* **comment** comment to describe the exam. (Year, subject, ....)
* **difficulty** desired difficulty of the exam
* **file_descriptions** File to generate with the questions
* **file_notes** File to generate answers or corrector
* **macros** List of user defined macros. Described in Macros sections. String
  to search and substitution.
* **description** Preamble to put at the beggining of file_description
* **notes** Preamble to put at the begginning of file_notes
* **parts** The exam is a list of blocks and each block is defined with a tags
  or question type. In parts array, there is a list of these blocks with
  information about the tag to be used and the amount of questions to use in
  that block.

  The general form is {tag:<string>,num_questions:<int>}, if a item is only a
  string, that will be the tag and num_questions is defaulted to 1. This format is useful to 
  create headers and fixes texts:

  ```yaml
  parts:
    - Instructions
    - Theory
    - {tag: 'lesson 1', num_questions: 1}
    - {tag: 'lesson 2', num_questions: 1}
    - Exercises
    - {tag: 'exercises 1', num_questions: 3}
  ```

  Here, there is only one question with tag "Instructions", and it has
  difficulty=0. (Same for "Theory" or "Exercises"). In this format it is easy to 
  overview the structure of the exam.

  There is a special predefined tag: `all` that means all questions available.

  If `num_questions`<0, that means all questions with that tag.

  The combination of {tag: 'all', num_questions: -1} dumps all questions in
  BANK_DIR (except ignored and with no regex, described in BANK_DIR) 

### MACROS

Macros is a string substitution with almost no syntax in a similar way to M4
macro languaje (simpler). Each macro has a trigger (an string), optional
arguments and a content. The only real requirement is do not use '(' in the
trigger string or ',' in the list of arguments. You can use any other caracter
(space too) but for your sanity, follow this recomendations:

* For triggers use only UPPERCASE and '\_'.
* The arguments is a list of strings between parentheses with comma (',') as
  separation. Prepend with a sigil like '$' or '@' and do not use space.
* In the content, when the macro is called, each argument is substituted by its
  value in the call.

All the inputs values and the results are strings and they are converted if it
is needed.

Each macro has an order of preference. Until no macro of superior order is
processed, do no start the substitutions of macros of the next level. So, each
transformation requires to restart the macro engine.

#### Definitions 
Described by order of precedence. All macros can call another macros. 

##### Constant macros in INDEX_FILE

Examples:
```yaml
  - HEADER_NOTES: "text"
  - HEADER: |+
      YAML allows multiline text. We use here
      HEADER_NOTES
```

##### Macros with arguments in INDEX_FILE

```yaml
  - HEADER(@a,@b): "print('***** @a ----- @b')"
  - HEADER2(@a,$b): "print('***** @a ----- @b $b')"
```

You can use any string to define argument and they are always substituted
(there is no escape) or protection inside a string.

In `HEADER2` the second arg changed the sigil to be able to write @b without
substitution.

##### VARM - Metadata

Sustituyed by metadata variable.

Ex: `VARM(file_notes)` 

it is changed by file_notes metadata.

##### VARFLOAT - Define variable with Random Float

Select a random float number between `min` and `max` and keep `decimals` decimals
(default 2). 

`VARFLOAT(name,min,max,decimals=2)`

The macro result is inserted instead the macro call and the result is stored in
variable `name` to possible later reuse.

##### VARFLOATRANGE - Define variable from list of floats

Create a list of floats from `start`, `end` and `step`. And choose one.

`VARFLOATRANGE(name,start,end,step,decimals=2)`

The macro result is inserted instead the macro call and the result is stored in
variable `name` to possible later reuse.


##### VARINT - Define variable with random int
Select a random int in range `min <= generated <= max`.

`VARINT(name,min,max)`

##### VARINTRANGE - Define variable from list of ints

Create a list of ints from `start`, `end` and `step`. And choose one.

`VARINTRANGE(name,start,end,step)`

The macro result is inserted instead the macro call and the result is stored in
variable `name` to possible later reuse.

##### VAROP - Define a value from list of values
Take a list of values and choose one. 

`VAROP(name,opc1,opc2,opc3)`

Example: `Define operator VAROP(operador,+,addition,in this expresion: 1+2).`

The macro result is inserted instead the macro call and the result is stored in
variable `name` to possible later reuse.

##### VARV - Use previous value

Put the content of a previously defined variable.

`VARV(name)`

A variable is not a macro. So it is only substituted by its value if the name of the variable is inside `VARV` macro.

##### VARQ - Create unique name

Create a unique name based on the current question and a name. 

`VARQ(name)`

The name create is `t<num exercise>_<name>`. if the output format doesn't allow
that name, you can create a macro with arguments in INDEX_FILE. It has more
precedence than this predefined function so the macro will call yours.

##### VARNUM - Current exercise

The number of current exercise.

`VARNUM`

## BANK_DIR

A directory with yaml files. In each file can be several yaml documents. Each
document is a question.

Structure of question:
```yaml
title: <string>
tags: <string or array of strings>  #compulsory
difficulty: <number>                #compulsory
frequency: <number>
description: <text of question>     #compulsory
notes: <text of answer/autocorrect>
ignored: <bool>
regex: <auto or bool>
```

* **title** A title only for document the question. Maybe an example of
  question or a small description. Optional
* **tags** A string with a tags or a list of strings. It is compulsory.
* **difficulty** difficulty asigned. Compulsory. It is possible to assign
  difficulty=0. To headers and other parts.
* **frequency** Bigger value implies more probability to be selected. Default
  value=1.
* **description** Text of the question.
* **notes** Text of the answer/autocorrection file
* **ignored** question ignored.
* **regex** Says if the macro engine is going to be used and if it is a real
  question or not.
  * true: yes with macros. Real question.
  * false: without macros. Header.
  * auto: look for any "VAR" operator in the description and notes text. If
    there is any, the macro engine is used, otherwise the macros are not used.
    Default value. 

  When macro engine is disconected, the var `VARNUM` is not incremented. This
  allow to create labels, without loose the number of the question.

## Example

### INDEX_FILE
```yaml
---
comment: 1st Part. 2023-03
difficulty: 2
file_descriptions: exam.md
file_notes: exam.m
macros:
  - HEADER: |+
    ## Task VARNUM
  - HEADER_NOTES: "\n% Task VARNUM\n"
  - RESULT_NOTES: "disp('Result for task VARNUM:')"
  - VERIFY_VARIABLE(@a): |+
      RESULT_NOTES
      diff = COMPARE_ARRAYS(@a,VARQ(@a))
  - COMPARE_ARRAYS(@a,@b): sum(abs(@a-@b))(:))
description: |+
  # EXAM 1
  Name: 

  Create a script with the values of the solutions, following the instructions
  of each task.

notes: |+ 
  % EXAM 1
parts:
  - addition header
  - {tag: 'addition', num_questions: 1}
  - product header
  - {tag: 'product', num_questions: 1} 
``` 

### BANK_DIR
```
---
tags:
  - addition header
difficulty: 0
description: |+
  ## Additions

---
tags:
  - addition
difficulty: 1
description: |+
  HEADER

  Calculate the addition of VARINT(a,1,9) and VARINTRANGE(b,1,9,2) and store in
  VARQ(c).

notes: |+
  HEADER_NOTES

  c = VARV(a)+VARV(b)
  VERIFY_VARIABLE(c)

---
tags:
  - product header
difficulty: 0
description: |+
  ## Products
---
tags:
  - product
difficulty: 1
description: |+
  HEADER

  Calculate the product VARFLOATRANGE(a,1,5,0.5) and VAROP(b,2.0,5.0,10.0) and store in
  VARQ(c).

notes: |+
  HEADER_NOTES

  c = VARV(a)*VARV(b)
  VERIFY_VARIABLE(c)

```

## TODO

* Select questions by tag (done) or by file (TODO). Actually you
  can put several tags to each question. So it is possible to
  define a tag of type of exercise and other tag the name of the
  file. And use one or other to select.
* Avoid the repetition of same question (CHECK). No sure.
  Sometimes is interesting generate the same questions (with
  different values) several times to make drillout exercises (to
  practice).
* Be able to use macros in description and notes (in INDEX_FILE)
  without increment VARNUM

