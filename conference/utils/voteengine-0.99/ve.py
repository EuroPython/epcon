#!/usr/bin/python

"""
Vote counter by Blake Cretney 

This work is distributed AS IS.  It is up to you to 
determine if it is useful and safe.  In particular, 
NO WARRANTY is expressed or implied.

I permanently give everyone the rights to use, modify, 
copy, distribute, re-distribute, and perform this work, 
and all derived works, to the extent that I hold copyright 
in them.  My intent is to have this work treated as 
public domain.

This module is used to run the program where a proper console
is not available.  I wrote it for Windows, but maybe it works
on a Mac too.  I have no way of knowing.
"""

import votemain
import sys

sys_stdin=sys.stdin
sys_stdout=sys.stdout
pause=1
try:
	sys.stdin=open("input.txt")
	sys.stdout=open("output.txt","w")
	votemain.vote_main()
	pause=0
except IOError, e:
	sys_stdout.write(str(e) + "\n")
except RuntimeError,e:
	sys_stdout.write(e.args[0] + "\n")
if pause:
	try:
		import msvcrt
		sys_stdout.write("Press any key to continue\n")
		c = msvcrt.getch()
		pause=0
	except: pass

