# Exam generator

Exam generator chooses from a bank of questions/problems a set of items based
on a set of constraints. 

Possible constraints are the global difficult of the selected set and the
amount of questions in each section (it can be an exact number of questions or a
range).

Additionally, a macro engine allows defining global parameters (e.g. header
texts, header of each question, date, ...) and increase the variety of questions
using random parameters in exercises.

The bank of questions is composed as a series of YAML files with the questions and
metadata as subject, difficulty, likelihood to be used, and random value generation.

The general configuration of the set to be generated is in the index\_file,
which has information about desired difficulty, general macros and structure of
questions. The use of convenient index\_files allow generating different
exams but also the ability of create a catalog of all problems in database.

There are no restrictions about the format of the questions, except they are
any text format (text, Markdown, LaTeX, typst, python, octave, whatever) and
all questions have to share the same formats. Also, each question can use any
amount of "versions": a question can have an English version, a Spanish one, a
Solution, notes about the problem, sources, implementation in several
programing languages etc. 

**The rest of the README.md file is from an older version. So, the information 
maybe is not very updated. Work in progress**

## Options

Usage: rand-exam.py [OPTIONS] INDEX\_FILE BANK\_DIR

Arguments:

*  INDEX\_FILE Structure of exam [required]

Options:

* -b, --bank DIR. Directory with bank of questions.

    This parameter can be defined also in INDEX\_FILE

* -e, --edition INTEGER Force edition. If None, look for first empty

    It is possible to generate different versions of the exam (with same
    INDEX\_FILE). That is, different questions but same difficulty and categories.

* -s, --seed INTEGER Seed used

    To force the rebuild an exam with same questions and values. BE CAREFUL, 
    the same random generator is used to select questions and random values, if
    the BANK\_DIR is altered (i.e. adding a random var in a question). 
    Can alter the questions (TODO: CHECK)

    This parameter can be defined also in INDEX\_FILE

    The real seed used is this seed parameter added with edition. It is a good strategy
    use the date (numeric) of the exam as seed multiplied by 10 or 100. So 
    edition 1 of date 20231011 will use a different seed (202310111) than edition 0 of 
    date 20231012 (202310120). 

* -a, --tries INTEGER Number of tries to generate exam [default: 1000]

    The exam is generate trying random posibilities. This parameter says how
    many tries do.

    If the target is not achieved, inform of the best result, the maximum
    difficulty generated and the minimum.

    This parameter can be defined also in INDEX\_FILE

* -t, --tolerance FLOAT  Tolerance to select exam  [default: 0.5]

    Sets the range of values to stop searching an exam. if target difficulty is
    11 and tolerance is 1, it stop if calculated difficulty value is in
    [11-1,11+1]

    This parameter can be defined also in INDEX\_FILE

* --help                 Show this message and exit.

## INDEX\_FILE

Description of the exam in a yaml file. 

Structure:
```yaml
---
comment: <text>
bank: <dir>
seed: <int>
tolerance: <float>
tries: <int>
difficulty: <number>
file_descriptions: <filename1>
file_notes: <filename2>
macros:
    - ...
description: <text>
notes: <text>
parts:
    - ...
seed: <number>
```

Description of attributes:

* **comment** comment to describe the exam. (Year, subject, ....)
* **bank** same as command line parameter
* **seed** same as command line parameter
* **tolerance** same as command line parameter
* **tries** same as command line parameter
* **difficulty** desired difficulty of the exam
* **file\_descriptions** File to generate with the questions
* **file\_notes** File to generate answers or corrector
* **macros** List of user defined macros. Described in Macros sections. String
  to search and substitution.
* **description** Preamble to put at the beggining of file\_description. Macros
  are substituted.
* **notes** Preamble to put at the begginning of file\_notes. Macros are
  substituted.
* **parts** TODO: OBSOLETE
  
  The exam is a list of blocks and each block is defined with a tags
  or question type. In parts array, there is a list of these blocks with
  information about the tag to be used and the amount of questions to use in
  that block.

  The general form is {tag:<string>,num\_questions:<int>}, if a item is only a
  string, that will be the tag and num\_questions is defaulted to 1. This format
  is useful to create headers and fixes texts:

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

  There is a special predefined tag: `all` that means all questions available. (In fact, 
  `all` tag is all questions with regex activated.)

  If `num_questions`<0, that means all questions with that tag.

  The combination of {tag: 'all', num\_questions: -1} dumps all questions in
  BANK\_DIR (except ignored and with no regex, described in BANK\_DIR) 
* **seed** Seed to generate the tests. 
  * Seed used is (this parameter + edition number)
  * Default value of seed is today date in iso format yyyymmdd
  * If command line cli argument seed is provided, the seed is overrided.

### MACROS

Macros is a string substitution with almost no syntax in a similar way to m4
macro languaje (simpler than m4). Each macro has two possible structures:

    '((' trigger '))'

or 
    '((' trigger , list_of_arguments_separated_with_commas '))'

The declaration and the invocation has same structure: double parentheses,
trigger string, and an optional list of arguments separated by commas. The
triggers and the arguments are treated as strings without stripping of spaces.
So if you use "(( trigger))" the trigger string will be " trigger" with the
space. 

Macros can be nested, in the invocation (inside of macro invocation, in the
argument) or in the contents. The use of nested macros inside of macro
definition is a undefined behaviour. 

You can use any other caracter (space too) in trigger text and argument names
but for your sanity, follow this recomendations in definition of macros:

* For triggers use only UPPERCASE and '\_'.
* The arguments is a list of strings between parentheses with comma (',') as
  separation. Prepend each argument with a sigil like '$' or '@' and do not use
  space.
* In the content, when the macro is called, each argument is substituted by its
  value in the call.

All the inputs values and the results are strings and they are converted if it
is needed.

Macro are the same for all questions. 

##### Constant macros in INDEX\_FILE

Examples:
```yaml
  ((HEADER_NOTES)): "text"
  ((HEADER)): |+
    YAML allows multiline text. We use here
    ((HEADER_NOTES))
```

A macro can call another macro. In the example, the second "((HEADER_NOTES))" is a invocation, not a definition.

##### Macros with arguments in INDEX\_FILE

```yaml
  ((HEADER,@a,@b)): "print('***** @a ----- @b')"
  ((HEADER2,@a,$b)): "print('***** @a ----- @b $b')"
```

You can use any string to define argument and they are always substituted
(there is no escape) or protection inside a string.

In `HEADER2` the second arg changed the sigil to protect the @b and avoid
substitution.

## Macro engine 2

Second version of the macro engine. In the same namespace, there are four kind of 
substitutions.

* Metadata. Specific information of the question: Level of difficulty,
  frequency, title, ...Metadata is accesible in descriptions and notes of the
  question.

* Vars. Specific from question. Any variable defined with "SAVE" or "VAR"
  commands. Vars are accesible since the creation until the end of the question
  (descriptions and notes).

* Macros. Defined in INDEX\_FILE. Common values and function for all exam.

* Internal Operations. Defined in code.

The look-up order is the same of above list: Metadata, Vars, Macros and
Internal. That allows to override internal operations with specific operations.

### Invocation

The macro engine is activated with sequence of double parenteses. Inside of the
parentheses there is a list of elements marked with commas. The first token is
the variable, macro or function to execute and the rest of the elements are the
arguments of that function.

All arguments are strings, but certains functions can convert to a number if it
is needed. Extra arguments are ignored. 

A macro defined as: 
  `((HEADER,@a,@b)): "print('***** @a ----- @b')"`
is invoqued: ((HEADER,one,two))

To get the value of a variable put the name in double parentheses: ((myvariable))

### Order of macro execution.

The order is from begining to end. From inside to outside.

In expression:
```
((1,((2)),3,((4))))((5))((6,((7))))
```
The order of execution of substitutions is 2,4,1,5,7,6

### Internal Functions 

#### Variable Generation
##### SAVE

Asign to "varname", the result of the function and args. 

```
((SAVE,varname,function,args))
```
save doesn't produce any output.

##### VAR

Asign to "varname", the result of the function and args. 

```
((VAR,varname,function,args))
```
The output is the value of the created variable.

#### Random generators
##### INT

Random Int with $min<=value<=max$. If step is specified, the values have to
fullfill: $value = min+k\cdot{}step$.

```
((INT,min,max))
```
or
```
((INT,min,max,step))
```

##### FLOAT 

Random FLOAT with $min<=value<=max$. The output is shown with the number of
decimals.

```
((FLOAT,min,max))
```
or
```
((FLOAT,min,max,decimals))
```

##### FLOATRANGE 

Random FLOAT with $min<=value<=max$. Limited by steps. The output is shown with the number of
decimals (same decimals than step or defined).

$value = min+k\cdot{}step$.

```
((FLOATRANGE,min,max,step))
```
or
```
((FLOATRANGE,min,max,step,decimals))
```
##### OP
Random option. Take one random arg.

```
((OP,one,two,three))
```

#### Calculations
Function to calculate. 

##### Calc

Function CALC is a little RPN calculator with basic functions: +,-,*,/.

```
((CALC,a,((FLOAT,1,3)),+,2,/,INT))
```
Remarks:

* All operations are done with FLOAT. The INT command convert value in top of
  stack into int.

* Any variable is substituted by its value. The value have to be valid number  or
  operations.

* You can use functions. The output of the functions have to be valid numbers
  or operations.

* You can use numbers (ints or float) directly. All are converted to float. 

* All arguments are striped (removed spaces before and after the content), if
  you have a variable name with a space at the begining or the end (very bad
  idea), you can escape using double parentheses: (( A long variable name with
  spaces at the beggining)).

#### Format functions

##### DATE
Current date en ISO8601 format (i.e. "2023-10-23")

```
((DATE))
```

##### DNL

Ignore the rest of the line until "\n". Same idea from dnl macro of m4. It
allows to reduce lines in the output.

```
((DNL))
```
E.g.:
```
Text and more text
((SAVE,a,INT,1,10))((DNL))
more text. The above line is omited. 
```

##### FOR
Repeat a string several times:

```
((FOR,*,((difficulty))))
```

Take the value of difficulty and repeat (a difficulty of 3 will generate '***')

##### ID
Return the first argument of the function.

```
((ID,12))
```

Allow to use a literal when a function is required. 

E.g.:
```
((SAVE,a,ID,12))
```

## BANK\_DIR

A directory with yaml files. In each file can be several yaml documents. Each
document is a question.

Structure of question:
```yaml
title: <string>
scaffold: <boolean (Default False)>
tags: <string or array of strings>  
difficulty: <number>                #compulsory
frequency: <number>
description: <text of question>     #compulsory
notes: <text of answer/autocorrect>
ignored: <bool>
regex: <auto or bool>
autotag: <bool (default True)>
```

* **title** A title only for document the question. Maybe an example of
  question or a small description. Optional
* **scaffold** This is not a real question. Its a piece of text to add to 
  an exam. Like title of exam, name of section, header. Useful, for instance to 
  create he header and end of LaTeX document. The tags of this no-question have to be 
  unique to select this exact element. A scaffold imply no autotags, and difficult = 0
  
  ```yaml
  scaffold: true
  scaffold:
  ```
  Any value except "false" will be considered as "true"

  The state variable ((COUNTER)) is incremented always except in questions 
  with scaffold active.
* **tags** A string with a tag or a list of strings. 
* **autotag** If True, add two tags automagically to tags list:
  * the filename (without the yaml extension) and,
  * `all` 
* **difficulty** difficulty asigned. Compulsory except if scaffold key is present and 
  with value not false. 
* **frequency** Bigger value implies more probability to be selected. Default
  value=1.
* **description** Text of the question. Compulsory
* **notes** Text of the answer/autocorrection file
* **ignored** question ignored.
* **regex** Says if the macro engine is going to be used.
  * true: yes with macros. 
  * false: without macros. 
  * auto: look for any "((" operator in the description and notes text. If
    there is any, the macro engine is used, otherwise the macros are not used.
    Default value. 

## FAQ - other questions

### Markdown 
The files of descriptions and notes can be in any text format. 
A typical system is use markdown and later convert to pdf with `pandoc`.

Here are some problems who required some intervention.

#### Margins

Default margins in pandoc are too wide. You can add a header inside description
and notes preambles (in INDEX\_FILE) to specify the margin. 

```yaml
description: |+
  ---
  geometry: margin=4cm
  output: pdf_document
  ---
  (And rest of preamble)

```
The header can contain metadata about different aspects of the pdf generation,
like the margins, or language, or templates, ...

#### New Page

I am not sure about the mecanism of pandoc and markdown. But it seems it is
intelligent enought to understand if a '\' is escaping a character or not. 

The pandoc process to convert markdown to pdf have a intermediate representation 
in LaTeX. So any LaTeX command in the markdown is copied verbatim to the LaTeX
representation without requirement of escape the '\' char.

So, to force a new page, use LaTeX command `\newpage` directly.

## Example

### INDEX\_FILE
```yaml
---
comment: 1st Part. 2023-03
difficulty: 2
file_descriptions: exam.md
file_notes: exam.m
macros:
  ((HEADER)): |+
    ## Task ((COUNTER))
  ((HEADER_NOTES)): "\n% Task ((COUNTER))\n"
  ((RESULT_NOTES)): "disp('Result for task ((COUNTER)):')"
  ((VERIFY_VARIABLE,@a)): |+
      ((RESULT_NOTES))
      diff = ((COMPARE_ARRAYS,@a,((VARQ,@a))))
  ((COMPARE_ARRAYS,@a,@b)): sum(abs(@a-@b))(:))
description: |+
  # EXAM 1
  Name: 

  Create a script with the values of the solutions, following the instructions
  of each task.

notes: |+ 
  % EXAM 1
parts:
  addition header .:
  addition: 1
  product header .:
  product: 1 
``` 

### BANK\_DIR
```
---
tags: addition header
scaffold:
description: |+
  ## Additions

---
tags:
  - addition
difficulty: 1
description: |+
  ((HEADER))

  Calculate the addition of ((VAR,a,INT,1,9)) and ((VAR,b,INT,1,9,2)) and store in
  ((VARQ,c)).

notes: |+
  ((HEADER_NOTES))

  c = ((a))+((b))
  ((VERIFY_VARIABLE,c))

---
tags:product header
scaffold:
description: |+
  ## Products
---
tags:
  - product
difficulty: 1
description: |+
  ((HEADER))

  Calculate the product ((VAR,a,FLOATRANGE,1,5,0.5) and ((VAR,b,OP,2.0,5.0,10.0)) and store in
  ((VARQ,c)).

notes: |+
  ((HEADER_NOTES))

  c = ((a))*((b))
  ((VERIFY_VARIABLE,c))

```

## TODO

* Avoid the repetition of same question (CHECK). No sure.
  Sometimes is interesting generate the same questions (with
  different values) several times to make drillout exercises (to
  practice).

* content of files are cache: unprocessed (f"{file_id}_raw") and processed(f"{file_id}").
  This solve: 
    * Include of the content of other file:
          one: |+
            ((VAR,F,INT,1,1000))
          two: |+
            ((one)). ((F)) is a great number

        in one appear a random int, and in two appear another random, because ((one)) is included in two before one is processed
        Maybe, when processed one: substitute one by the processed values, but keep created variables to keep the value of F: 
    * recursive calls if a command is created with different values per file_id:
        ((BEGIN)): ((BEGIN_((FILE))))
        ((BEGIN_one)): one
        ((BEGIN_two)): ((one))
        one is processed and cached, so if a ((BEGIN)) is in one, the result is the call to ((BEGIN_one)). 
        in two, the one is the processed and cache valued, so isn't recalculated. 

* Document:
    * ESCAPE OF PARENTHESES (\(DATE)) and COMMA
    * QUOTECOMMA

    * question[regex] is deleted

    * multiple files

    * command FILE to identify current file
