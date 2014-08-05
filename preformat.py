import re
from argparse import ArgumentParser, Normal, Pre, NoWrap, PreWrap, \
    PreLine, Py3FormatHelpFormatter, WSList
import textwrap

"""
adapted from ParaformatterML in issue12806
Takes a text with paragraphs (defined by blank line) and preformatted
indented items, and turns it into WSList which
is a mix of Normal and Pre text blocks
In effect a 2 stage formatting

keepline - if True, blank line between paragraphs will be ' ', ensuring
that if is preserved in wrap.
Pre('') is inconsistent between wrap and fill (actually all are)
Not sure if it is better to fix it here, or in Pre

"""

def preformat(text, multiline=True, keepblank=True, para_style=Normal, indent_style=Pre):
    text = textwrap.dedent(text)
    _whitespace_matcher = re.compile(r'\s+')
    new_lines = list()
    main_indent = len(re.match(r'( *)',text).group(1))
    if main_indent: print('indent', main_indent)
    def blocker (text):
        '''On each call yields 2-tuple consisting of a boolean
        and the next block of text from 'text'.  A block is
        either a single line, or a group of contiguous lines.
        The former is returned when not in multiline mode, the
        text in the line was indented beyond the indentation
        of the first line, or it was a blank line (the latter
        two jointly referred to as "no-wrap" lines).
        A block of concatenated text lines up to the next no-
        wrap line is returned when in multiline mode.  The
        boolean value indicates whether text wrapping should
        be done on the returned text.'''

        block = list()
        for line in text.splitlines():
            line_indent = len(re.match(r'( *)',line).group(1))
            isindented = line_indent - main_indent > 0
            isblank = re.match(r'\s*$', line)
            if isblank or isindented:       # A no-wrap line.
                if block:                       # Yield previously accumulated block .
                    yield True, ' '.join(block)  #  of text if any, for wrapping.
                    block = list()
                yield False, line               # And now yield our no-wrap line.
            else:                           # We have a regular text line.
                if multiline:                   # In multiline mode accumulate it.
                    block.append(line)
                else:                       # Not in multiline mode, yield it
                    yield True, line            #  for wrapping.
        if block:                           # Yield any text block left over.
            yield (True, ' '.join(block))

    for wrap, line in blocker(text):
        if wrap:
            new_lines.append(para_style(line))
        else:
            # The line was a no-wrap one so leave the formatting alone.
            line = line[main_indent:]
            if len(line)==0:
                if keepblank:
                    line = ' ' # ' ' preserves a blank line between paragraphs
                    new_lines.append(Pre(line))
                # else - don't append anything
            else:
                new_lines.append(indent_style(line))

    return WSList(new_lines)

from argparse import WhitespaceStyle

class Hanging(WhitespaceStyle):
    """Hanging indent - wrap the string with a hanging indent
    intended to format list items.  Ideally the indent accounts for
    header, e.g. '1. ', '- '.
    Indent may also be given as a initial parameter
    Extra code here to preserve that Indent across functions
    """

    def __new__(cls, data='', header_indent=None):
        astr =  str.__new__(cls, data)
        astr.header_indent = header_indent
        return astr

    _whitespace_matcher = re.compile(r'\s+')
    header_matcher = re.compile(r'\s*([\w\-*\.\)\]]{1,2} )')

    def _deduce_indent(self):
        # run as part of __new__?
        if self.header_indent is None:
            m = self.header_matcher.match(self)
            if m:
                indent = len(m.group(1))
            else:
                indent = 4
            return ' '*indent
        else:
            return ' '* self.header_indent

    def copy_class(self, text):
        """modified to handle the extra attribute
        """
        Fn = type(self)
        if isinstance(text, str):
            return Fn(text, header_indent=self.header_indent)
        else:
            # this may not be of any value since a list like this normally joined
            return WSList([Fn(line, self.header_indent) for line in text])

    def __getattribute__(self, name):
        """modified to handle the extra attribute
        """
        att = super(WhitespaceStyle, self).__getattribute__(name)

        if not callable(att):
            return att

        def wrapped_fn(*args, **kwargs):
            value = att(*args, **kwargs)
            if isinstance(value, str):
                return type(self)(value, self.header_indent)
            return value
        return wrapped_fn

    def _split_lines(self, width):
        text = self._fill_text(width, '')
        lines = text.splitlines()
        return self.copy_class(lines)

    def _fill_text(self, width, indent):
        text = self
        in_indent = len(re.match(r'( *)',text).group(1))
        indent = indent + ' '*in_indent
        added_indent = self._deduce_indent()
        text = self._whitespace_matcher.sub(' ', text).strip()
        text = textwrap.fill(text, width, initial_indent=indent,
                                           subsequent_indent=indent+added_indent)
        return self.copy_class(text)

if __name__ == "__main__":
    text = Hanging('1- one two three four {five} %(six)s seven')
    print(text)
    print(text._fill_text(20,''))
    text = text.format(five=5)._str_format(dict(six=6))
    print(text._fill_text(20,''))

    print('\n')
    N = 6
    text = Hanging('1- One two three four {five} %(six)s seven', N)
    print(text)
    assert text.header_indent == N
    print(text._fill_text(20,''))
    assert text.header_indent == N
    #print(text.upper().header_indent)
    text1 = text.copy_class(str(text))
    print('after copy', text1.header_indent, type(text1))
    print(text1)
    text = text.format(five=5)._str_format(dict(six=6))
    print(text.header_indent)
    print(text._fill_text(20,''))
