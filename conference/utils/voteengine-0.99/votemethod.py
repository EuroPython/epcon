#Votemethod module

"""
Votemethod module by Blake Cretney

This work is distributed AS IS.  It is up to you to 
determine if it is useful and safe.  In particular, 
NO WARRANTY is expressed or implied.

I permanently give everyone the rights to use, modify, 
copy, distribute, re-distribute, and perform this work, 
and all derived works, to the extent that I hold copyright 
in them.  My intent is to have this work treated as 
public domain.

This module provides all the different election methods.
"""

from votelib import *

from string import *
import Numeric
import re
from Numeric import *
import sys
from sys import maxint

def borda(o):
	n=len(o.cand_l)
	row_sum=sum(o.pw_tbl,1)
	print 'Borda'
	print "Cand  Borda Count"
	for i in xrange(n):
		borda=(row_sum[i]+(n-1)*o.n_votes)*.5
		print ljust(o.cand_l[i],4), rjust(`borda`,9)

	winmat=zeros((n,n),Int0)
	for i in xrange(n):
		for j in xrange(n):
			if i!=j and row_sum[i]>row_sum[j]: winmat[i,j]=1
	print
	break_ties(winmat,o.tiebreaker)
	print_ranks(winmat,o.cand_l)

def borda_elim(o):
	n=len(o.cand_l)
	row_sum=sum(o.pw_tbl,1)
	act=ones((n),Int0) #active candidates
	n_act=n

	print 'Borda-elimination'

	while n_act>1:

		print "Cand  Borda count"
		for i in xrange(n):
			if act[i]:
				borda=(row_sum[i]+(n_act-1)*o.n_votes)*.5
				print ljust(o.cand_l[i],4), rjust(`borda`,9)
		print	
		minim=min(take(row_sum,nonzero(act)))
		elim=logical_and(equal(row_sum,minim),act)

		for i in xrange(n):
			if elim[i]:
				print "Eliminate", o.cand_l[i]
				row_sum=row_sum-o.pw_tbl[:,i]
				act[i]=0
				n_act=n_act-1

	if n_act==0:
		if not o.tiebreaker:
			print "Unresolved Tie"
			return
		else: 
			for i in o.tiebreaker:
				if elim[i]: 
					print "Winner", o.cand_l[i]
					return
									
	print "Winner", o.cand_l[nonzero(act)[0]]

def bucklin(o):
	n=len(o.cand_l)
	print 'Bucklin'
	level=n
	vts=zeros((n),Int32)
	while level>0:
		votes=0
		for x in o.ballot_tbl:
			valid=0 # whether the ballot is still a valid vode
			b=x.ballot
			for i in xrange(n):
				if b[i]==level: 
					vts[i]=vts[i]+x.votes
					valid=1
			if valid: votes=votes+x.votes
		print "Valid Votes: ", votes
		print "Cand  Accumulated score"
		for i in xrange(n):
			print ljust(o.cand_l[i],4), rjust(`vts[i]`,9)
		print
		max=-1
		cand=0
		tieprob=0 # tie problem
		for i in xrange(n):
			if vts[i]>max or (vts[i]==max and cmpTie(i,cand,o.tiebreaker)<0):
				max=vts[i]
				cand=i
				tieprob=0
			elif vts[i]==max and cmpTie(cand,i,o.tiebreaker)==0:
				tieprob=1
			
		if max>votes/2:
			if tieprob==1:
				print "Unresolved Tie"
				return
			else:
				print "Winner", o.cand_l[cand]
				return
		level=level-1
		
	print 'Tie'

def c_irv(o):
	n=len(o.cand_l)
	print 'Condorcet//IRV'

	cws=nonzero(equal(maximum.reduce(o.pw_tbl),0))
		#note that the diagonal contains 0's

	for x in cws:
		print "CW", o.cand_l[x]
	if len(cws): return
	
	print
	print 'No Condorcet Winner'
	act=range(n) # active / non-eliminated candidates
	while len(act)>1:
		vts=zeros((n),Int32)
		for x in o.ballot_tbl:
			b=x.ballot
			max=-1
			cand=0
			for i in act:
				if b[i]>max:
					max=b[i]
					cand=i
			if max==0: continue
			vts[cand]=vts[cand]+x.votes
		print "Cand  Plurality score"
		for i in act:
			print ljust(o.cand_l[i],4), rjust(`vts[i]`,9)
		print
		min=sys.maxint
		cand=0
		tieprob=0 # tie problem
		for i in act:
			if vts[i]<min or (vts[i]==min and cmpTie(i,cand,o.tiebreaker)>0):
				min=vts[i]
				cand=i
				tieprob=0
			elif vts[i]==min and cmpTie(cand,i,o.tiebreaker)==0:
				tieprob=1
		if tieprob==1:
			print "Unresolved Tie"
			return
		act.remove(cand)		
	print "Winner", o.cand_l[act[0]]

def copeland(o):
	n=len(o.cand_l)
	print 'Copeland'
	sc=zeros((n),Int32) # two points for win, 1 for tie
	for i in xrange(n):
		for j in xrange(n):
			if o.pw_tbl[i,j]>o.pw_tbl[j,i]: sc[i]=sc[i]+2
			elif o.pw_tbl[i,j]==o.pw_tbl[j,i]: sc[i]=sc[i]+1
	
	print "Cand  Wins"
	for i in xrange(n):
		print ljust(o.cand_l[i],4), rjust(`0.5*(sc[i]-1)`,9)
	#since a candidate ties itself, I have to subtract that tie
	winmat=zeros((n,n),Int0)
	for i in xrange(n):
		for j in xrange(n):
			if i!=j and sc[i]>sc[j]: winmat[i,j]=1
	print
	break_ties(winmat,o.tiebreaker)
	print_ranks(winmat,o.cand_l)

def irv(o):
	n=len(o.cand_l)
	print 'IRV'
	act=range(n) # active / non-eliminated candidates
	while len(act)>1:
		vts=zeros((n),Int32)
		for x in o.ballot_tbl:
			b=x.ballot
			max=-1
			cand=0
			for i in act:
				if b[i]>max:
					max=b[i]
					cand=i
			if max==0: continue
			vts[cand]=vts[cand]+x.votes
		print "Cand  Plurality score"
		for i in act:
			print ljust(o.cand_l[i],4), rjust(`vts[i]`,9)
		print
		min=sys.maxint
		cand=0
		tieprob=0 # tie problem
		for i in act:
			if vts[i]<min or (vts[i]==min and cmpTie(i,cand,o.tiebreaker)>0):
				min=vts[i]
				cand=i
				tieprob=0
			elif vts[i]==min and cmpTie(cand,i,o.tiebreaker)==0:
				tieprob=1
		if tieprob==1:
			print "Unresolved Tie"
			return
		act.remove(cand)		
	print "Winner", o.cand_l[act[0]]

def minmax(o):
	n=len(o.cand_l)
	print 'Minmax'

	sc=maximum.reduce(o.pw_tbl)
	print "Cand  Max Loss"
	for x in xrange(n):
		print ljust(o.cand_l[x],4), rjust(`sc[x]`,9)
	winmat=zeros((n,n),Int0)
	for i in xrange(n):
		for j in xrange(n):
			if i!=j and sc[i]<sc[j]: winmat[i,j]=1
	print
	break_ties(winmat,o.tiebreaker)
	print_ranks(winmat,o.cand_l)

def nanson(o):
	n=len(o.cand_l)

	row_sum=sum(o.pw_tbl,1)
	act=ones((n),Int0) #active candidates
	n_act=n

	print 'Nanson (original)'

	while n_act>1:

		print "Cand  Borda count"
		for i in xrange(n):
			if act[i]:
				borda=(row_sum[i]+(n_act-1)*o.n_votes)*.5
				print ljust(o.cand_l[i],4), rjust(`borda`,9)
		print "Average",(n_act-1)*o.n_votes*.5
		print

		elim=logical_and(less_equal(row_sum,0),act)
		print "Eliminate:",
		for i in xrange(n):
			if elim[i]:
				print o.cand_l[i],
				row_sum=row_sum-o.pw_tbl[:,i]
				act[i]=0
				n_act=n_act-1
		print

	if n_act==0:
		if not o.tiebreaker:
			print "Unresolved Tie"
			return
		else: 
			for i in o.tiebreaker:
				if elim[i]: 
					print "Winner", o.cand_l[i]
					return						
	print "Winner", o.cand_l[nonzero(act)[0]]

def pw_elim(o):
	n=len(o.cand_l)
	act=range(n) # active / non-eliminated candidates
	print 'Pairwise Elimination'
	
	while len(act)>1:
		sc=zeros((n),Int32)
		for i in act:
			sc[i]=maximum.reduce(take(o.pw_tbl[:,i],act))
			
		print "Cand  Max Loss"
		for i in act:
			print ljust(o.cand_l[i],4), rjust(`sc[i]`,9)

		max=-1
		cand=0
		tieprob=0
		for i in act:
			if sc[i]>max or (sc[i]==max and cmpTie(i,cand,o.tiebreaker)>0):
				max=sc[i]
				cand=i
				tieprob=0
			elif sc[i]==max and cmpTie(cand,i,o.tiebreaker)==0:
				tieprob=1
		if tieprob==1:
			print "Unresolved Tie"
			return
		print "Drop", o.cand_l[cand]
		act.remove(cand)		
	print "Winner", o.cand_l[act[0]]

def s_irv(o):
	n=len(o.cand_l)
	act=range(n) # non-eliminated candidates
	print 'Smith//IRV'

	path=array(o.pw_tbl,Int32)
	floyd(path)
	path=greater_equal(path,0)
	
	for i in xrange(n):
		for j in xrange(n):
				if path[i,j]>path[j,i] and j in act: act.remove(j)			
	
	print 'Smith Set: ',
	for i in act:
		print o.cand_l[i],
	print
	
	while len(act)>1:
		vts=zeros((n),Int32)
		for x in o.ballot_tbl:
			b=x.ballot
			max=-1
			cand=0
			for i in act:
				if b[i]>max:
					max=b[i]
					cand=i
			if max==0: continue
			vts[cand]=vts[cand]+x.votes
		print "Cand  Plurality score"
		for i in act:
			print ljust(o.cand_l[i],4), rjust(`vts[i]`,9)
		print
		min=sys.maxint
		cand=0
		tieprob=0 # tie problem
		for i in act:
			if vts[i]<min or (vts[i]==min and cmpTie(i,cand,o.tiebreaker)>0):
				min=vts[i]
				cand=i
				tieprob=0
			elif vts[i]==min and cmpTie(cand,i,o.tiebreaker)==0:
				tieprob=1
		if tieprob==1:
			print "Unresolved Tie"
			return
		act.remove(cand)		
	print "Winner", o.cand_l[act[0]]

def s_minmax(o):
	n=len(o.cand_l)
	path=array(o.pw_tbl,Int32)

	floyd(path)

	smith=greater(minimum.reduce(path,1),0)

	print 'Smith//Minmax','(',o.opts,')'

	print 'Smith Set'
	print_scores(o.pw_tbl, o.cand_l, nonzero(smith))
	
	maximum.reduce(o.pw_tbl)
	
	sc=zeros((n),Int32)
	for i in xrange(n):
		if smith[i]:
			sc[i]=maximum.reduce(compress(smith,o.pw_tbl[:,i]))
		else:
			sc[i]=sys.maxint
	winmat=zeros((n,n),Int0)
	for i in xrange(n):
		for j in xrange(n):
			if i!=j and sc[i]<sc[j]: winmat[i,j]=1
	print
	break_ties(winmat,o.tiebreaker)
	print_ranks(winmat,o.cand_l)

def schulze(o):
	n=len(o.cand_l)
	print 'Schulze'

	floyd(o.pw_tbl)

	print 'Path matrix'
	print_scores(o.pw_tbl, o.cand_l)
	winmat=zeros((n,n),Int0)
	for i in xrange(n):
		for j in xrange(n):
			if i!=j and o.pw_tbl[i,j]>o.pw_tbl[j,i]: winmat[i,j]=1
	print
	break_ties(winmat,o.tiebreaker)
	print_ranks(winmat,o.cand_l)

def smith(o):
	n=len(o.cand_l)
	print 'Smith'

	floyd(o.pw_tbl)

	print
	print_ranks(greater_equal(o.pw_tbl,0),o.cand_l)

def rp_fix(path,i,j,m,n):
	if path[j,i]==maxint: return 

	for o_i in xrange(n):
		if path[o_i,i]<m: continue
		if path[o_i,j]>=m: continue
		for o_j in xrange(n):
			if path[j,o_j]<m: continue
			if path[o_i,o_j]>=m: continue
			path[o_i,o_j]=m

def rp(o):
	n=len(o.cand_l)
	pw=o.pw_tbl

	print 'Ranked Pairs'

	for i in xrange(n): pw[i,i]=maxint
	path=zeros((n,n),Int32)
	for i in xrange(n): path[i,i]=maxint

	pairs=[]
	if o.tiebreaker:
		tb=o.tiebreaker
		for i in xrange(n): 
			for j in xrange(n):
				m=0+pw[tb[i],tb[j]]
				if m>=0 and m<maxint:
					if m==0: 
						if i<j: 
							pairs = pairs + [(-m,i,j)]
# remember, higher ranked means lower number
					else:
						pairs = pairs + [(-m,min(i,j),max(i,j))]

		pairs.sort()

		for pair in pairs: 
			if pw[tb[pair[1]],tb[pair[2]]]<0:
				i=tb[pair[2]]
				j=tb[pair[1]]
			else:
				i=tb[pair[1]]
				j=tb[pair[2]]
			rp_fix(path,i,j,maxint,n);
	
	else:
		for j in xrange(n):
			for i in xrange(n):
				if pw[i,j]>0 and i!=j:
					pairs = pairs + [(0+pw[i,j],i,j)]
		
		pairs.sort()
		pairs.reverse()
		
		s=0
		e=0
		while s<len(pairs):
			while e<len(pairs) and pairs[e][0]==pairs[s][0]: e=e+1

			for p in xrange(s,e): 
				rp_fix(path,pairs[p][1],pairs[p][2],pairs[p][0],n)
			for p in xrange(s,e):
				if path[pairs[p][2],pairs[p][1]]==0:
					rp_fix(path,pairs[p][1],pairs[p][2],maxint,n)
			s=e

		for i in xrange(n):
			for j in xrange(n):
				if path[i,j]!=maxint: path[i,j]=0	
	print
	print_ranks(path,o.cand_l)

def ukvt(o):
	n=len(o.cand_l)
	act=range(n) # non-eliminated candidates
	try:
		candSQ=o.cand_l.index('SQ')
	except ValueError: candSQ=-1
	try:
		candRO=o.cand_l.index('RO')
	except ValueError: candRO=-1
	print 'uk.* voting'
	if candSQ!=-1:
		for i in xrange(n): # note that candSQ is always removed from act
			if o.pw_tbl[i,candSQ]<12: 
				act.remove(i)
				continue

	if candSQ!=-1:
		print 'Candidates that beat SQ by 12 or more: ', 
		if act==[]:
			print "None.  SQ wins"
			return
		for i in act:
			print o.cand_l[i],
		print	
		print_scores(o.pw_tbl, o.cand_l, act)
	
	sc=zeros((n),Int32)

	for i in xrange(n):
		if i in act:
			sc[i]=maximum.reduce(take(o.pw_tbl[:,i],act))
		else:
			sc[i]=sys.maxint

	for j in xrange(n):
		for i in xrange(n):
			if i!=j and sc[i]==0 and sc[j]==0:
				if cmpTie(i,j,o.tiebreaker)<0: 
					sc[j]=sys.maxint
					break

	for i in xrange(n):
		if sc[i]!=0 and i in act: act.remove(i)
			
	if len(act)==0:
		print 'No Condorcet winner.  Re-open discussion wins by default'
		return

	# must be at least one Condorcet winner.
	if len(act)==1:
		print 'Condorcet winner: ', o.cand_l[act[0]]
		return
	
	print 'Tied Winners: ',
	for i in act:
		print o.cand_l[i],
	print
	
