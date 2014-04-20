argparse_issues
===============

Compilation of argparse patches from bugs.python.org

Notes:

--------------------
composite - merger of following branches:

master
9334
(skip 16142 dashku)
(13922 - argparse ok, conflict in test_argparse)
9253
15125
9338
(11354 conflict in argparse, prob over range already added to 9338)
(14191 conflict in argparse - over adding nargs SUPPRESS)
(9849 conflict over the mnrep lines in _check_argument)
(16468 numerous conflicts in argparse and test_argparse)
14074
15112
14365
(9694 merge fail)
18943
17218


-----------------
* 9334    argparse does not accept options taking arguments beginning with dash (regression from optparse)
=> default_to_positional; argcoffee (args_default_to_positional) 2013/04/26
(important)

? 16142  daskku -  ArgumentParser inconsistent with parse_known_args
dashku.patch; argcoffee (-ku) 2013/04/29 (incomplete)

* 13922  ddash -  argparse handling multiple "--" in args improperly
=> ddash; argcoffee (--) 2013/04/28
(closed, should be reopened)
* 14364 - Argparse incorrectly handles '--'
=> 13922 ddash solves this
(rather than reopen 13922, apply the patch here)

15427  remainder - Describe use of args parameter of argparse.ArgumentParser.parse_args
=> remainder; doc change

* 9253  required -  argparse: optional subparsers
=> required; argcoffee (required) 2013/04/30
(important)

* 15125 - argparse: positional arguments containing - in name not handled well
17965 identifier (just text) -_ replacement issue (closed)

9338 greedyopt,  - argparse optionals with nargs='?', '*' or '+' can't be followed by positionals
(complex)

greedyrange - join nargs range and 9338
(11354 - nargsrange is newer, may be need to backport change)
(add feature, can delay)

* 14191 - argparse doesn't allow optionals within positionals
=> intermixed, mixed
(valuable, new feature, adds method, minimal change elsewhere)

13966   Add disable_interspersed_args() to argparse.ArgumentParser
(not my patch; implements the other optparse behavior)

* 9849 - Argparse needs better error handling for nargs
=> nargswarn; argcoffee
16970 - argparse: bad nargs value raises misleading message
=> nargswarn; argcoffee (allinone) 2013/04/28
(I discuss this, prefer my solution in 9849; also reference 14191)


16878   argparse: positional args with nargs='*' defaults to []
doc patch 1/2013; comment by me
(i mention 18943 as possibly related)
(has doc patch, plus a test case, by chris.jerdonek)

* 14074 - argparse allows nargs>1 for positional arguments but doesn't allow metavar to be a tuple
small change to argparse.py; join metavars with |

* 15112 - argparse: nargs='*' positional argument doesn't accept any items if preceded by an option and another positional
don't consume a possibly zero length positional if there still are optionals to proceess
(related to 'mixed')

14365 - subparsers, argument abbreviations and ambiguous option
(related to 9253 - subparsers required/not)
include subparsers in the argument ambiguity testing
(merged fine)

14910 - disable abreviations
(patch by bethard; I suggest a quick work around)

9694 - argparse required arguments displayed under "optional arguments"
Issue regarding the awkwardness of the name 'optionals' when arguments
may be required or not.
Proposal is a 'help_groups' parameters, defining 0,1,2,3 base groups
(merge failed)

* 18943 - argparse: default args in mutually exclusive groups
PyPy and Cpython behave different in how small v large ints satisfy 'is'
In modifying seen_nondefault_actions (used in MXG testing) argparse uses
'if argument_values is not action.default' (wrong use of 'is')
Patch changes how this is determined - by generating a flag in
_get_values() when it is actually using the default
(important - this corrects a discrepency between PyPy and Cpython)
11588 - uses seen_nondefault_actions (and changes it from set to list)

17218 - support title and description in argparse add_mutually_exclusive_group
In add_mutually_exclusive_group, if 'title' given
first create an argument_group, then nest the MXG in that
there's a test_argparse case that does just this.
So this patch just makes it more convenient; it does not add functionality
MXG nesting may have been designed for this purpose
(merged)

--------------------

issues related mutually exclusive groups
(overlap with usage formatting)
10984 - argparse add_mutually_exclusive_group should accept existing arguments to register conflicts
adding existing argument to a MXG is easy; not problem testing it
formatting usage requires format_usage rewrite
and custom formatter
=> multigroup
do_once (add self to group)
11588 (inclusive) - alt way of testing groups
mutex_title (add title to MXG - propose nesting MXG in argGroup)

issues related to FileType
13824 - FileContext
14156 - (-rb files)

issues related to help formatting
14074

issues related to nargs
9338 - greedyopt
- greedyrange
11354 - nargsrange
9849 - nargswarn

----------------------
issues related to usage formatting

issues related to AssertionError in usage formatting
14046 - argparse: assertion failure if optional argument has square/round brackets in metavar
16360 - argparse: comma in metavar causes assertion failure when formatting long usage message
17890 - argparse: mutually exclusive groups full of suppressed args can cause AssertionErrors
    text = _re.sub( '\s+', ' ', text ).strip()
18349 - argparse usage should preserve () in metavars such as range(20)
11874 - argparse assertion failure with brackets in metavars (solution)
10984 - argparse add_mutually_exclusive_group should accept existing arguments to register conflicts

7/16/2013 - rewrite _format_actions_usage()
    issue 11874 has this change
    issues 18349, 17890 are solved by this change
    issue 16468 is simplified by this change (freeer metavar content)
    issue 10984 builds on this change (new formatter class)

18349 argparse usage should preserve () in metavars such as range(20)
=> metaparen

11874   argparse assertion failure with brackets in metavars
=> inner_bracket

11708 - also best uses formatter from 11874 (chg '[x] [y]' to [x [y]])
-----------------

issues related to choices:
9625    argparse: Problem with defaults for variable nargs when using choices
=> starchoices

16468   argparse only supports iterable choices
=> customchoice

16418   argparse with many choices can generate absurdly long usage message
=> customchoice  (issue 16468)

16977   argparse: mismatch between choices parsing and usage/error message

=> customchoice (issue 16468)
