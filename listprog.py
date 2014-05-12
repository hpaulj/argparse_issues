import argparse
p = argparse.ArgumentParser(
    #prog=['PROG', '-f FOO', 'XXX', 123],
    prog='PROG',
    formatter_class=argparse.ListProgHelpFormatter)
p.add_argument('-b','--bar',nargs=3)
p.add_argument('yyy',nargs='*', metavar=('YYY1','YYY2'))
#print(p.prog)
#print(type(p.prog))
p.prog = 'PROG'
print(p.format_usage())
p.prog =  '/home/paul/testdir/subdir/A_very_long_program_name.foo.bar'
print(p.format_usage())
p.prog = ['PROG', '-f FOO', 'XXX']
print(p.format_usage())
p.prog = ['A VERY LONG NAME', '-f FOOBAR FOOBAR', 'XXX [XXX [XXX XXX]]', '[ONE TWO THREE FOUR]']
print(p.format_usage())
# puts each p.prog string on new line, no indent
p.prog = 'SHORT'
print(p.parse_args())
