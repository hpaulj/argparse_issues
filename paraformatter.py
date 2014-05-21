# http://bugs.python.org/issue12806, http://bugs.python.org/file22977/argparse_formatter.py

import argparse
import re
import textwrap

class ParagraphFormatter(argparse.HelpFormatter):

    def _split_lines(self, text, width):
        return _para_reformat(self, text, width, multiline=False)

    def _fill_text(self, text, width, indent):
        lines =_para_reformat(self, text, width, indent, False)
        return '\n'.join(lines)

class ParagraphFormatterML(argparse.HelpFormatter):

    def _split_lines(self, text, width):
        return _para_reformat(self, text, width, multiline=True)

    def _fill_text(self, text, width, indent):
        lines = _para_reformat(self, text, width, indent, True)
        return '\n'.join(lines)

class ParagraphFormatter1(argparse.HelpFormatter):
    def __init__(self,
                 prog,
                 multiline=False,
                 **kwargs):
        self.multiline = multiline
        super(ParagraphFormatter1, self).__init__(prog, **kwargs)
    def _split_lines(self, text, width):
        return _para_reformat(self, text, width, multiline=self.multiline)

    def _fill_text(self, text, width, indent):
        lines = _para_reformat(self, text, width, indent,  multiline=self.multiline)
        return '\n'.join(lines)

def format_wrapper(**kwargs):
    # class 'factory' used to give extra parameters
    def fnc(prog):
        cls = ParagraphFormatter1
        return cls(prog, **kwargs)
    return fnc

ParagraphFormatter = format_wrapper(multiline=False)
ParagraphFormatterML = format_wrapper(multiline=True)

def _para_reformat(self, text, width, indent='', multiline=False):
        new_lines = list()
        main_indent = len(re.match(r'( *)',text).group(1))

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
                        yield True, ''.join(block)  #  of text if any, for wrapping.
                        block = list()
                    yield False, line               # And now yield our no-wrap line.
                else:                           # We have a regular text line.
                    if multiline:                   # In multiline mode accumulate it.
                        block.append(line)
                    else:                           # Not in multiline mode, yield it
                        yield True, line            #  for wrapping.
            if block:                           # Yield any text block left over.
                yield (True, ''.join(block))

        for wrap, line in blocker(text):
            if wrap:
                # We have either a single line or a group of concatented
                # lines.  Either way, we treat them as a block of text and
                # wrap them (after reducing multiple whitespace to just
                # single space characters).
                line = self._whitespace_matcher.sub(' ', line).strip()
                # Textwrap will do all the hard work for us.
                new_lines.extend(textwrap.wrap(text=line, width=width,
                                               initial_indent=indent,
                                               subsequent_indent=indent))
            else:
                # The line was a no-wrap one so leave the formatting alone.
                new_lines.append(line[main_indent:])

        return new_lines

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=ParagraphFormatter,
                                     description='''\
        This description help text will have this first long line wrapped to\
        fit the target window size so that your text remains flexible.

            1. But lines such as
            2. this that that are indented beyond the first line's indent,
            3. are reproduced verbatim, with no wrapping.
               or other formatting applied.

        You must use backslashes at the end of lines to indicate that you\
        want the text to wrap instead of preserving the newline. '''
        'Alternatively you can avoid using backslashes by using the '
        'fact that Python concatenates adjacent string literals as '
        'we are doing now.\n\n'
        ''
        'As with docstrings, the leading space to the text block is ignored.')
    parser.add_argument('--example', help='''\
        This argument's help text will have this first long line wrapped to\
        fit the target window size so that your text remains flexible.

            1. But lines such as
            2. this that that are indented beyond the first line's indent,
            3. are reproduced verbatim, with no wrapping.
               or other formatting applied.

        You must use backslashes at the end of lines to indicate that you\
        want the text to wrap instead of preserving the newline. '''
        'Alternatively you can avoid using backslashes by using the '
        'fact that Python concatenates adjacent string literals as '
        'we are doing now.\n\n'
        ''
        'As with docstrings, the leading space to the text block is ignored.')
    parser.print_help()

    parser = argparse.ArgumentParser(formatter_class=ParagraphFormatterML,
                                     description='''\
        This description help text will have this first long line wrapped to
        fit the target window size so that your text remains flexible.

            1. But lines such as
            2. this that that are indented beyond the first line's indent,
            3. are reproduced verbatim, with no wrapping.
               or other formatting applied.

        The ParagraphFormatterML class will treat consecutive lines of
        text as a single block to rewrap.  So there is no need to end lines
        with backslashes to create a single long logical line.

        As with docstrings, the leading space to the text block is ignored.''')

    parser.add_argument('--example', help='''\
        This argument's help text will have this first long line wrapped to
        fit the target window size so that your text remains flexible.

            1. But lines such as
            2. this that that are indented beyond the first line's indent,
            3. are reproduced verbatim, with no wrapping.
               or other formatting applied.

        The ParagraphFormatterML class will treat consecutive lines of
        text as a single block to rewrap.  So there is no need to end lines
        with backslashes to create a single long logical line.

        As with docstrings, the leading space to the text block is ignored.''')
    parser.print_help()
