#Votelib module

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

This module is for the procedures that don't do I/O or anything like that.
"""

from string import *
import re
import numpy
import sys


# 2 funcs for converting to and from special letter form
# i.e. A-Z AA-ZZ AAA-ZZZ etc.
def alpha_to_int(x):
	c=0
	total=0
	while c<len(x):
		total=total*26+ord(x[c])-64
		c=c+1
	return(total)
	
def int_to_alpha(x):
	alpha=""
	sub=1
	len=0
	while 1:
		sub=sub*26
		len=len+1
		temp=x-sub
		if temp<=0: break
		x=temp
	x=x-1
	while len>0:
		alpha=chr(x%26+65) +alpha
		x=x/26
		len=len-1
	return(alpha)

# change the matrix to a winning-votes matrix
def zero_defeats(x): 
	n=x.shape[0]
	for i in xrange(n):
		for j in xrange(i+1,n):
			if x[i,j]==x[j,i]: x[i,j]=x[j,i]=0
			elif x[i,j]>x[j,i]: x[j,i]=0
			else: x[i,j]=0

# change the matrix to a marginal matrix
def to_margins(x): 
	n=x.shape[0]
	for i in xrange(n):
		for j in xrange(i+1,n):
			m=x[i,j]-x[j,i]
			x[i,j]=m
			x[j,i]=-m

# returns <0 if x is preffered to y, >0 if y is preferred to x, 0 if no preference
def cmpTie(x,y,tiebreaker):
	if tiebreaker==None: return(0)
	xi=tiebreaker.index(x)
	yi=tiebreaker.index(y)
	return(xi-yi)

def break_ties(winmat,tiebreaker):
	if tiebreaker==None: return
	n=winmat.shape[0]
	done=numpy.zeros((n),numpy.int_) # record of which 
	                                    #candidates are already processed
	while 1:
		for i in tiebreaker:
			if done[i]>0: continue
			for j in xrange(n):
				if i==j or done[j]>0: continue
				if winmat[j,i]>0: break
			else: break # if no defeat, use this i
		else: break # no i was undefeated.  Must be done
		done[i]=1
		for j in xrange(n):
			if done[j]==0: winmat[i,j]=1

#winmat - matrix of wins and ties, no contradictions allowed
#candlist - same old list of candidate names

def print_ranks(winmat,candlist):
	n=winmat.shape[0];

	wins=numpy.zeros((n),numpy.int32)

	for i in xrange(n):
		for j in xrange(n):
			if winmat[i,j]>winmat[j,i]: wins[i]=wins[i]+1;

	order=[]
	for i in xrange(n):
		order= order+ [(wins[i],i)]
	order.sort()
	order.reverse()

	ties=0
	
	for i in xrange(n):
		(c_wins,c)=order[i]
		if c_wins<n-1-i:
			ties=1
			if i==0:
				print "Tie for first place."
			else:
				print " ... ties prevent full ranking \n"
			break
		print candlist[c],
		if i<n-1:
			print ">",
	
	if ties:
		print "Some ties exist.  See table."	
		print "      ",
		for j in xrange(n): 
			print rjust(candlist[j],5),
		print
		for i in xrange(n):
			print ljust(candlist[i],3),
			print "  ",
			for j in xrange(n):
				if i==j: print "    X",
				elif winmat[i][j]>winmat[j][i]:
					print "    1",
				elif winmat[j][i]>winmat[i][j]:
					print "    0",
				else:
					print "    ?",
			print 
	print

def print_some_scores(x,candlist,act):
	n=x.shape[0]
	print '      ',
	for j in act:
		print rjust(candlist[j],5),
	print
	for i in act:
		print ljust(candlist[i],3), '  ',
		for j in act:
			if i==j: print '    X',
			else: print rjust(`x[i,j]`,5),
		print
	print

def print_scores(x,candlist,act=None):
	if(act):
		print_some_scores(x,candlist,act)
		return
	n=x.shape[0]
	print '      ',
	for j in xrange(n):
		print rjust(candlist[j],5),
	print
	for i in xrange(n):
		print ljust(candlist[i],3), '  ',
		for j in xrange(n):
			if i==j: print '    X',
			else: print rjust(`x[i,j]`,5),
		print
	print

def candRange(start,end): # translates selected range of candidates into list
	
	if start=="": failure("Missing Range")
	pat=re.compile(r'(?P<alpha>[A-Z]*)(?P<num>\d*)')
	m=pat.match(start)
	if(m==None): failure("Improper range")
	start_alpha_raw=m.group('alpha')
	start_num_raw=m.group('num')
	
	m=pat.match(end)
	if(m==None): failure("Improper range")
	end_alpha_raw=m.group('alpha')
	end_num_raw=m.group('num')
	
	if (start_alpha_raw=="")!=(end_alpha_raw==""):
		failure('alpha mismatch on range')
		
	if (start_num_raw=="")!=(end_num_raw==""):
		failure('Numeric mismatch on range')

	if start_alpha_raw: 
		current_alpha=start_alpha=alpha_to_int(start_alpha_raw)
		end_alpha=alpha_to_int(end_alpha_raw)
		if start_alpha>end_alpha: failure('Alpha bound error on range')
	if start_num_raw: 
		current_num=start_num=int(start_num_raw)
		end_num=int(end_num_raw)
		if start_num>end_num: failure('Numeric bound error on range')
	
	carry=0
	list=[]
	while carry<2:
		carry=0
		c=""
		if start_alpha_raw: c=c+int_to_alpha(current_alpha)
		if start_num_raw: c=c+`current_num`
		list=list+[c]
		if start_num_raw:
			if current_num==end_num:
				carry=1
				current_num=start_num
			else: current_num=current_num+1
		else: carry=1
		if carry==1:
			if start_alpha_raw:
				if current_alpha==end_alpha:
					carry=2
				else: current_alpha=current_alpha+1
			else: carry=2
	return(list)

def floyd(m):
	n=m.shape[0]
	for k in xrange(n):
		for i in xrange(n):
			for j in xrange(n):
				m[i,j]=max(m[i,j],min(m[i,k],m[k,j]))
	
