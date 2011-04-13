#Votemain module

"""
Votelib module by Blake Cretney

This work is distributed AS IS.  It is up to you to 
determine if it is useful and safe.  In particular, 
NO WARRANTY is expressed or implied.

I permanently give everyone the rights to use, modify, 
copy, distribute, re-distribute, and perform this work, 
and all derived works, to the extent that I hold copyright 
in them.  My intent is to have this work treated as 
public domain.

This module contains the heart of the program.
"""

from string import *
import re
import Numeric
import sys
from sys import maxint
from votelib import *
import votemethod

class Options:
	cand_l = None # list of candidate names
	zero_def=0 # zero out the defeats
	method_nm=None # selected method
	n_votes=0
	record_pw=0 # do I have to record pairwise information
	pw_tbl=None
	record_ballots=0 # do I have to record complete ballots 
	ballot_tbl=None
	tiebreaker=None 
		# order of candidates used by some methods to break ties

class Ballot:
	votes=0
	ballot=None

lineno=0 # current line being read (for error information)

def failure(x):
	raise RuntimeError, "Failure: %s\nLine %d" % (x,lineno)

def bug(x):
	raise RuntimeError, "Internal Error: %s\nLine %d" % (x,lineno)

def input_line():
	global lineno
	while 1:
		rawline = raw_input()
		lineno=lineno+1
		comment=find(rawline, '#') # filter out comments
		if comment!=-1: 
			rawline=rawline[:comment]
		rawline=lstrip(rawline)
		while rawline and rawline[0]==">":
			rawline=rawline[1:]
			rawline=lstrip(rawline)
		if rawline!="": break	
	return(rawline)
	
def read_table(x): # reads a directly entered table
	n=x.shape[0]
	try:
		for i in xrange(n):
			rawline=input_line()

			sline=split(rawline)[-n:]
			for j in xrange(n):
				if i!=j: x[i,j]=x[i,j]+int(sline[j])
	except ValueError: failure('Bad Table Value')
	except IndexError: failure('Malformed Table')
	except EOFError: failure('EOF during table')

def get_options(list,o): # gets command line options
	for x in list:
		x=split(x,None,1)
		opt= lower(x[0])
		
		if len(x)>1: 
			param= x[1]
		else:
			param= None

		if opt != 'm' and o.method_nm==None:
			failure('-m must be first option')

		if opt == 'cands':
			if param==None:
				failure('Missing parameter')
			if o.cand_l!=None:
				failure('Redefinition of candidate list')

			o.cand_l=[]
			for cand in split(param):
				if find(cand,'-')==-1:
					o.cand_l = o.cand_l + [cand]
				else: 
					range=split(cand,'-',1)
					o.cand_l=o.cand_l + candRange(range[0],range[1])
			n=len(o.cand_l)
			if o.record_pw:
				o.pw_tbl=Numeric.zeros((n,n),Numeric.Int32) # pairwise table
			if o.record_ballots:
				 o.ballot_tbl=[] # storage for ballots	
			
		elif opt=='m':
			if o.method_nm!=None:
				failure('Multiple methods selected')
			if param==None:
				failure('Missing parameter')
			if o.n_votes>0: failure('-m must precede ballots')
			o.method_nm=lower(param)

			if o.method_nm=="borda":
				o.record_pw=1
			
			elif o.method_nm=="bucklin":
				o.record_ballots=1
			
			elif o.method_nm=="c//irv":
				o.method_nm="c_irv"
				o.record_pw=1
				o.record_ballots=1
			
			elif o.method_nm=="copeland":
				o.record_pw=1

			elif o.method_nm=="irv":
				o.record_ballots=1

			elif o.method_nm=="minmax":
				o.record_pw=1

			elif o.method_nm=="borda-elim":
				o.method_nm="borda_elim"
				o.record_pw=1

			elif o.method_nm=="nanson":
				o.record_pw=1
				
			elif o.method_nm=="pw-elim":
				o.method_nm="pw_elim"
				o.record_pw=1

			elif o.method_nm=="s//irv":
				o.method_nm="s_irv"
				o.record_pw=1
				o.record_ballots=1

			elif o.method_nm=="s//minmax":
				o.method_nm="s_minmax"
				o.record_pw=1

			elif o.method_nm=="schulze":
				o.record_pw=1

			elif o.method_nm=="smith":
				o.record_pw=1

			elif o.method_nm=="table":
				o.record_pw=1
				
			elif o.method_nm=="rp":
				o.record_pw=1
				
			elif o.method_nm=="ukvt":
				o.record_pw=1
	
			elif o.method_nm=="nrp":
				o.record_pw=1
	
			else: failure('unknown method: ' + o.method_nm)

		elif opt== 'table':
			if o.cand_l==None: 
				failure('-cands must precede -table')
			if o.record_pw==0: failure('-table needs pairwise method')
			if o.record_ballots!=0: failure('-table requires purely pairwise method')
			if o.n_votes>0: failure('Tables must precede ballots')

			read_table(o.pw_tbl)
			
		elif opt=='tie':
			if o.cand_l==None: 
				failure('-cands must precede -tie')
			if param==None:
				failure('Missing parameter')
			if o.n_votes>0: failure('-tie must precede ballots')
			if o.tiebreaker!=None:
				failure('Multiple tiebreaker selected')

			tb=split(param)
			o.tiebreaker=[]
			try:
				for cand in tb:
					o.tiebreaker=o.tiebreaker + [o.cand_l.index(cand)]
			except ValueError: failure('Unknown candidate used in -tie')
			if(len(o.tiebreaker)!=n):
				failure("Tiebreaker must list all candidates")

		elif opt=='zd':
			if not o.record_pw:
				failure('zero-defeats only works on pairwise')
			o.zero_def=1
		else:
			failure('Unable to process option:' + `opt`)
			
			
def vote_main():
	o=Options() 
		
	if len(sys.argv)>1: # process the command line for options
		command=join(sys.argv[1:])
		command=strip(command)
		if command:
			if command[0]!='-': failure('option must use hyphen')
			get_options(re.split(r'\s+-',command[1:]),o)
	
	try:
		while o.cand_l==None:
			rawline=input_line()
			if rawline[0]=='-': # process argument lines
				get_options(re.split(r'\s+-',rawline[1:]),o)
			else: 
				failure('Some options must precede data')
	
		n=len(o.cand_l)
		
		while 1:
			rawline = input_line()
	
			if rawline[0]=='-': # process argument lines
				get_options(re.split(r'\s+-',rawline[1:]),o)
				continue
				

			bltsvote=split(rawline,":",1)
			if len(bltsvote)==1: #check for number of ballots
				ballots=1
				rawline=bltsvote[0]
			else:
				try:
					ballots=int(bltsvote[0])
					rawline=bltsvote[1]
				except ValueError: failure('illegal number of ballots')
			
			rawline=strip(rawline)
			if len(rawline)==0: failure('missing ballot')
	
			if ballots<=0: failure('Number of ballots must be positive')			
			o.n_votes=o.n_votes+ballots
			rawline=strip(rawline)
			rawline=re.sub(r'\s*=\s*','=',rawline) # remove whitespace around '='
	
			line=re.split(r'[\s>]+',rawline) # '>' and/or any remaing whitespace means '>'
	
			#give each candidate a score based on where it appears on the ballot. n is best, 0 worst
			working=Numeric.zeros((n),Numeric.Int32)
			level=n
	
			for eqcands in line:
				cands= split(eqcands,"=")
				for cand in cands:
					try:
						x=o.cand_l.index(cand)
					except ValueError: failure('Unknown candidate: ' + cand)	
					working[x]=level
				level=level-1
				
			if o.record_pw:
				for i in xrange(n):
					for j in xrange(n):
						if working[i]>working[j]: 
							o.pw_tbl[i,j]=o.pw_tbl[i,j]+ballots
			if o.record_ballots:
				b=Ballot()
				b.votes=ballots
				b.ballot=working
				o.ballot_tbl=o.ballot_tbl+[b]
	
	except EOFError:
		if o.cand_l==None:
			print "Empty File.  Nothing to do."
			return
	global lineno
	lineno=-1
	
	print 'VOTES  ' , o.n_votes
	if o.record_pw:
		if o.zero_def: 
			zero_defeats(o.pw_tbl)
			print "Defeats Zero'd out"

		else:
			to_margins(o.pw_tbl)
			print "Margins"
		print_scores(o.pw_tbl,o.cand_l)

	if o.method_nm=="table":
		return
	
	# choose which method to use on the data
	
	eval('votemethod.'+o.method_nm+'(o)')

def vote_engine(fin=None,fout=None,opts=None):
	old_in=sys.stdin
	old_out=sys.stdout
	old_argv=sys.argv
	if fin: sys.stdin=fin
	if fout: sys.stdout=fout
	if opts: sys.argv=opts
	try:
		vote_main()
	except RuntimeError,e:
		print e.args[0]
	sys.stdin=old_in
	sys.stdout=old_out
	sys.argv=old_argv
