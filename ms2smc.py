#!/usr/bin/python
# Aylwyn Scally 2012

import sys
import getopt
import optparse
import os.path
import numpy as np
import logging
from logging import error, warning, info, debug, critical

#os.umask(0002)
loglevel = logging.WARNING
logging.basicConfig(format = '%(module)s:%(lineno)d:%(levelname)s: %(message)s', level = loglevel)

#indivs = 2
binsize = 100

#def usage():
##	print '''usage: %s [-l loci] [-i individuals_per_population] [-o output] ms_cmd
#	print '''usage: %s [ms_outfile] [-L length] [-o output]
#	output		  'summary', 'full' (summary)''' % os.path.basename(sys.argv[0])

p = optparse.OptionParser()
p.add_option('-l', '--length', default = '10e3', help = 'seqlen for converting ms coords (within each rep)')
p.add_option('--output', action='store', type = 'choice', choices = ['segsep', 'psmcfa'], default = 'segsep', help = 'output format (segsep, psmcfa)')
p.add_option('--onechr', action='store', help = 'output sites on one chromosome')
p.add_option('--chrlen', default = '0', help = 'output sites on multiple chromosomes of length CHRLEN (split using awk \'{print > $1".segsep"}\')')
p.add_option('--phasecombs', action='store_true', default = False, help = 'output all diploid phase combinations (assume unphased input)')
p.add_option('--unphased', action='store_true', default = False, help = 'output diploid genotypes')
p.add_option('--hetcount', action='store_true', default = False, help = 'count hets in each individual')
p.add_option('--indivsep', default = '', help = 'separator between individuals')
opt, args = p.parse_args()

opt.length = eval(opt.length)
opt.chrlen = eval(opt.chrlen)

#for (oflag, oarg) in opts:
#	if oflag == '-b':
#		binsize = int(eval(oarg))
#	if oflag == '-L':
#		L = int(eval(oarg))
#	elif oflag == '-o':
#		output = {'summary': 1, 'full': 2}[oarg]

def genotype(al1, al2):
	return(''.join(sorted([al1, al2])))

def het(al1, al2):
	return(al1 != al2)

def hapsitetypes(n):
# haploid allele combinations
	for gt in ['0', '1']:
		if n > 1:
			for cc in hapsitetypes(n-1):
				yield(''.join((gt, cc)))
		else:
			yield(gt)


def dipsitetypes(n):
# diploid genotype combinations
# to get segregating sites drop first and last elements of returned vals
	for gt in ['00', '01', '11']:
		if n > 1:
			for cc in dipsitetypes(n-1):
				yield('-'.join((gt, cc)))
		else:
			yield(gt)

def phases(gt):
# diploid allele combinations
	yield(gt)
	if gt[0] != gt[1]:
		yield(gt[::-1])

def phasecombs(gts, sep = ''):
# different phase combinations of diploid genotypes in gts 
	if len(gts) > 1:
		for cc in phasecombs(gts[1:], sep):
			for ph in phases(gts[0]):
				yield(sep.join((ph + cc)))
	else:
		for ph in phases(gts[0]):
			yield(ph)

tgt = ['AB', 'CD', 'EF']
assert ','.join(phasecombs(tgt)) == 'ABCDEF,BACDEF,ABDCEF,BADCEF,ABCDFE,BACDFE,ABDCFE,BADCFE'


def lout(*args):
	sys.stdout.write('\t'.join([str(x) for x in args]) + '\n')

class FastaStream(object):
	def __init__(self, fh):
		self.fh = fh
		self.ccount = 0

	def write(self, c):
		self.fh.write(c)
		self.ccount += len(c)
		if self.ccount >= 60:
			self.fh.write('\n')
			self.ccount = 0

	def newrec(self, name):
		self.fh.write('\n>%s\n' % str(name))
		self.ccount = 0


if len(args) < 1:
   inputf = sys.stdin
else:
   inputf = open(args[0])

j = 0
chrseq = []
nchrs = int(inputf.next().split()[1])
indivs = nchrs/2
if nchrs % 2:
	error('odd number of input chrs')
	sys.exit(2)
#sitetypes = list(hapsitetypes(indivs))
#gtcount = dict([(x, 0) for x in sitetypes])
#zerotype = '0' * indivs
snum = 0
lastpos = 0
nextpos = binsize
chrnum = 1

if opt.output == 'psmcfa':
	faout = FastaStream(sys.stdout)
	faout.newrec(chrnum)

for line in inputf:
#	lout('ITERATION', ii)
#		treestr = str(itree)
#		tree=newick.parse_tree(treestr)

	if line.startswith('segsites'):
		nsites = int(line.split()[1])
		snum += 1

	if line.startswith('positions'):
		sitepos = [int(opt.length * float(x)) for x in line.split()[1:]]

		for indiv in range(nchrs):
			chrseq.append(inputf.next().strip())
		nsites = len(chrseq[0])

		if opt.phasecombs:
			siteseq = [','.join(phasecombs([genotype(chrseq[x][s], chrseq[x+1][s]) for x in range(0, nchrs, 2)], sep=opt.indivsep)) for s in range(nsites)]
		else:
			if opt.unphased:
				siteseq = [opt.indivsep.join([genotype(chrseq[x][s], chrseq[x+1][s]) for x in range(0, nchrs, 2)]) for s in range(nsites)]
			else:
				siteseq = [opt.indivsep.join([''.join([chrseq[x][s], chrseq[x+1][s]]) for x in range(0, nchrs, 2)]) for s in range(nsites)]
			if opt.hetcount:
#				hetsr = [[het(chrseq[x][s], chrseq[x+1][s]) for x in range(0, nchrs, 2)] for s in range(nsites)]
#				hets = np.array(hetsr)
				hets = np.array([[het(chrseq[x][s], chrseq[x+1][s]) for x in range(0, nchrs, 2)] for s in range(nsites)])
				hetcount = [sum(hets[:, i]) for i in range(indivs)]

#			print([opt.chrname, opt.chrlen, lastpos, opt.length, lastpos + opt.length])
		if opt.output == 'segsep':
			if opt.chrlen and lastpos + opt.length > opt.chrlen:
				if snum == 1:
					error('chrlen too short')
					sys.exit(2)
				chrnum += 1
				snum = 1
				lastpos = 0
			for i in range(nsites):
				pos = sitepos[i] + int((snum - 1) * opt.length)
				if pos > lastpos:
					lout(chrnum, pos, pos - lastpos, siteseq[i])
				lastpos = pos

		elif opt.output == 'psmcfa':
			if opt.chrlen and lastpos + opt.length > opt.chrlen:
				if snum == 1:
					error('chrlen too short')
					sys.exit(2)
				chrnum += 1
				snum = 1
				nextpos = binsize
				faout.newrec(chrnum)
			for i in range(nsites):
				pos = sitepos[i] + int((snum - 1) * opt.length)
				while pos > nextpos:
					faout.write('T')
					nextpos += binsize
				if pos > nextpos - binsize:
					faout.write('K')
					nextpos += binsize
				lastpos = nextpos

		chrseq = []
		if opt.hetcount:
			print('hetcounts: ' + ' '.join([str(x) for x in hetcount]))
			print('mean: %f' % np.average(hetcount))
