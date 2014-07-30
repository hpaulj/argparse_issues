import sys
from argparse import ArgumentParser, Normal, Pre, NoWrap, PreWrap, \
    PreLine, Py3FormatHelpFormatter, WSList

longtxt="""\
Body of the text.
1 - point one
2 - second point with
    contination
3 - third line

"""

description = '%(prog)s description'
description = PreLine('  %(prog)s Indented<br>\n\t<tab>more line<br>\n    with white    space')
epilog = Pre('Epilog: No wrap line %(prog)s<br>\n\tNext line\n \n')
usage = None

parser = ArgumentParser(prog='PROG', usage=usage,
    description=description, epilog=epilog,
    formatter_class=Py3FormatHelpFormatter
    )

parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.0.1')
parser.add_argument('-t', '--test', action='count', help='test the white-space styles. counter')

grp = parser.add_argument_group(title='Test Group',
    description=Pre('Group for testing<br>\n  the Pre indent')
    )

grp.add_argument('-l','--longversion', action='version', version=Pre(longtxt),
    help=Pre('writes to {prog:_^10} stderr,\n\tredirect with `2> temp.txt`'))
grp.add_argument('positional', help='short help line;\nignored nl, default: {default}', nargs='?',
    default=100)
grp.add_argument('--foo', default='DEFAULT', help='default: {%(default)s}')
grp.add_argument('--bar', default='DEFAULT', help='default: {{{default}}}')
grp.add_argument('--choice', choices=['one','two','three'],
    help='with choices: {%(choices)s}, default:%(default)s')
grp.add_argument('--prewrap', help=PreWrap("""\
This one very long line xxxxxxxxxxxxx xxxxxxxxxxxxxx xxxxxxxxxx  xxxxxxxx xxxxxxxx
Second line
"""))
parser.add_argument('-L', '--list', action='store_true', help='test WSList class')
parser.add_argument('-H', '--hanging', action='store_true', help='test Hanging class')


formatter = parser._get_formatter()
formatter.add_text(Pre('test text'))
txt = formatter._root_section.format_help()
print(repr(txt))

args = parser.parse_args()

print(args)

text1 = ("""\
    Normal long line that should be wrapped.  It can contain more than one sentence.
    This is a line       -this is after spaces.
    Second line\t-after tab.
    Indented items follow

      1 - two
      2 - three %(numb)s
      3 - a format test {}

""")
text = text1

if args.test==1:
    print('\n')
    print(repr(text))
    for fn in [Normal, Pre, NoWrap, PreWrap, PreLine]:
        print('\n')
        text = fn(text).dedent().format('DATA')._str_format(dict(numb=300))
        print(type(text))
        print(fn.__name__, ':', Normal(fn.__doc__)._fill_text(80, ''))
        print(text._split_lines(width=30))
        newtext = text._fill_text(width=30, indent='....')
        print(type(newtext))
        print(newtext)

text2 = """\
    one two three four five six
    four five six seven eight nine
      seven eight nine ten
        eight nine ten
    """
text = text
if args.test==2:
    print(text)
    for fn in [Normal, Pre, NoWrap, PreWrap, PreLine]:
        print(fn.__name__)
        print(fn(text)._split_lines(20))
        print(fn(text).dedent()._split_lines(20))
        print('\n')

if args.test==3:
    text = """\
    One two three four
    Five six

    Seven eight nine

        - point one
          two three four

        - point two

    """
    text = Pre(text)
    print(text.block())
    print(text.dedent().block())
    print(PreWrap(text.dedent().block())._fill_text(20,''))
    print('\n___ separate blocks with blank line __\n')
    #print(text.block(keepblank=True))
    print(text.dedent().block(keepblank=True))
    print(PreWrap(text.dedent().block(keepblank=True))._fill_text(20,''))
    """
    print(text.by_paragraph(multiline=False))
    print(text.by_paragraph(multiline=True))
    text = text.dedent()
    print(text.by_paragraph(multiline=False))
    print(text.by_paragraph(multiline=True))
    """

if args.hanging:
    from preformat import preformat, Hanging
    ptext = preformat(text1, keepblank=False)._str_format({'numb':1234})
    print(ptext)
    print(ptext._fill_text(30, '\t'))
    print('\n'.join(ptext._split_lines(30)))
    print([type(p) for p in ptext])

    txt = Hanging('1 - This is an line with need for wrapping', header_indent=4)
    print(txt)
    print(txt._fill_text(30, '...'))
    from functools import partial
    fn = partial(Hanging, header_indent=6)
    txt = fn('1 - this is a line with a extra indent')
    print(txt)
    print(txt._fill_text(30, '...'))

"""
print(repr(Pre(' ')._fill_text(30,'')))
print(Pre(' ')._split_lines(30))
print(Pre('')._split_lines(30))
print(NoWrap('')._split_lines(30))
print(Normal('')._split_lines(30))
"""

if args.list:
    # test a list structure that lets us define a text block with a mix
    # of formatting styles

    tlist = WSList([
        Pre('EPILOG\n------'),
        Normal('this is a test normal string {test}'),
        Pre('and a Pre string {test}'),
        PreLine('and a Preline string {test}\n'),
        PreWrap('PreWrap list\n  1 - point one %(prog)s\n  2 - point two\n      continued')

    ])
    print('\n')
    print(tlist)
    print(tlist.format(test='TEST STRING')._str_format(dict(prog=parser.prog)))
    print(tlist.format(test='  BOO     ')._split_lines(20))
    print(tlist.format(test='One tab\tTwo')._fill_text(30,'...'))

    parser.epilog = tlist.format(test='[TEST]')
    parser.print_help()

"""
http://bugs.python.org/issue12284 - examples in epilog, a good use for Pre
http://bugs.python.org/issue13023 - epilog w/br and add-defaults
     can do with subclass that inherits from 2 formatters
     zbybz: Yeah, adding a formatter instance seems overkill for the usual case of wanting to preserver formatting of the epilog.
http://bugs.python.org/issue9399 - 'write' license
     eg use version with a Pre text
http://bugs.python.org/issue13923
     It would be really nice to have a formatter for argparse that would respect explicit new lines while still wrapping lines otherwise.
     like white-space:pre-wrap?
http://bugs.python.org/issue12806 - hybrid formatter - i.e. apply wrap to lines
     but keep 'paragraph' breaks
"""