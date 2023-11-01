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

Usage: gen-exlab.py [OPTIONS] INDEX\_FILE BANK\_DIR

Arguments:

*  INDEX\_FILE  Structure of exam  [required]
*  BANK\_DIR    Questions to choose  [required]

Options:

* -e, --edition INTEGER  Force edition. If None, look for first empty

    It is possible to generate different versions of the exam (with same
    INDEX\_FILE (different questions but same difficulty and categories)

* -s, --seed INTEGER     Seed used

    To force the rebuild an exam with same questions and values. BE CAREFUL, 
    the same random generator is used to select questions and random values, if
    the BANK\_DIR is altered (i.e. adding a random var in a question). 
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

## INDEX\_FILE

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
seed: <number>
```

Description of attributes:

* **comment** comment to describe the exam. (Year, subject, ....)
* **difficulty** desired difficulty of the exam
* **file\_descriptions** File to generate with the questions
* **file\_notes** File to generate answers or corrector
* **macros** List of user defined macros. Described in Macros sections. String
  to search and substitution.
* **description** Preamble to put at the beggining of file\_description. Macros
  are substituted.
* **notes** Preamble to put at the begginning of file\_notes. Macros are
  substituted.
* **parts** The exam is a list of blocks and each block is defined with a tags
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

  There is a special predefined tag: `all` that means all questions available.

  If `num_questions`<0, that means all questions with that tag.

  The combination of {tag: 'all', num\_questions: -1} dumps all questions in
  BANK\_DIR (except ignored and with no regex, described in BANK\_DIR) 
* **seed** Seed to generate the tests. 
  * Seed used is (this parameter + edition number)
  * Default value of seed is today date in iso format yyyymmdd
  * If command line cli argument seed is provided, the seed is overrided.

### MACROS

Macros is a string substitution with almost no syntax in a similar way to m4
macro languaje (simpler than m4). Each macro has a trigger (an string), optional
arguments and a content. The only real requirement is do not use '(' in the
trigger string or ',' in the list of arguments. You can use any other caracter
(space too) but for your sanity, follow this recomendations:

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
  - HEADER_NOTES: "text"
  - HEADER: |+
      YAML allows multiline text. We use here
      HEADER_NOTES
```

##### Macros with arguments in INDEX\_FILE

```yaml
  - HEADER(@a,@b): "print('***** @a ----- @b')"
  - HEADER2(@a,$b): "print('***** @a ----- @b $b')"
```

You can use any string to define argument and they are always substituted
(there is no escape) or protection inside a string.

In `HEADER2` the second arg changed the sigil to be able to write @b without
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
  `- HEADER(@a,@b): "print('***** @a ----- @b')"`
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

* Any variable is substitute by its value. The value have to be valid number or
  operations.

* You can use functions. The output of the functions have to be valid numbers
  or operations.

* You can use numbers (ints or float) directly. All are converted to float. 

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

### BANK\_DIR
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

