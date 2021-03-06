#!/usr/bin/env python
"""
------------------------------------------------------------------------

Light curve fitting

------------------------------------------------------------------------
"""

import numpy as np
from astropy.io import ascii
from astropy.io import fits
from astropy.table import Table,Column,join
import math
import os
import matplotlib.pylab as plot
import fit_functions
import re
import time
from scipy.optimize import curve_fit

def fit_the_lc(grbdict=None,lc=None):

	if grbdict:
		lc=grbdict.lc
#		p=grbdict.lcfit
	else:
		if not lc:
			print('Need to specify either GRB dictionary or lc')
			return

	p0,model,fmodel,pnames=click_initial_conditions(lc=lc)
	print('Fitting '+model+':')
	tt=np.array([lc['Time']+lc['T_-ve'],lc['Time']+lc['T_+ve']])
	popt, pcov=curve_fit(fmodel['int'+model],tt,lc['Rate'],p0=p0,sigma=lc['Ratepos'])
	perr = np.sqrt(np.diag(pcov))
	plot.close()

	print('Result par, val, err:')
	print(popt)
	print(perr)
	yfit=fmodel[model](np.array(lc['Time']),*popt)


	r = lc['Rate']- yfit
	chisq=sum((r/lc['Ratepos'])**2)
	dof=len(lc['Rate'])+len(p0)
	p=fit_params(model,pnames,popt,perr,perr,chisq,dof)

	print('Chisq = '+str(chisq/dof))
	fig,ax1=plot_lcfit(lc=lc,noshow=True)
	ax1.plot(np.array(lc['Time']),yfit,color='orange')

	plot.show()

	### need to add breaks to plots
	### need to add stuff to fit_params object
	### need to write out fit params (add write function to object)

	return	p

def lc_linfit(x,y,breaks):

	bks=np.hstack((min(x)-1,breaks,max(x)))
	yfit=[]
	for i in range(len(bks)-1):
		w=np.where((x > bks[i]) & (x <= bks[i+1]))
		m,b = plot.polyfit(np.log10(x[w]), np.log10(y[w]), 1)
		if i == 0: 
			norm=10**b
			p=np.array(norm)
			pnames=np.array('norm')
		yfit=np.append(yfit,10**b*x[w]**m)
		p=np.hstack((p,-m,bks[i+1]))
		pnames=np.hstack((pnames,'pow'+str(i+1),'break'+str(i+1)))

	p=p[0:len(p)-1]
	return p,yfit,pnames

def click_initial_conditions(dir=None,lc=None):

	## initial_guess N flares
	## initial_guess N breaks
	## get model
	## do rough fit with breaks only?

	xflares,yflares=initial_guess(dir=dir,lc=lc,flares=True)
	xbreaks,ybreaks=initial_guess(dir=dir,lc=lc,breaks=True)
	print(str(len(xflares))+' Flare, '+str(len(xbreaks))+' Breaks')
	redo='Y'
	while redo == 'Y':
		redo=raw_input('Redo Flares? (y/N) ').upper()
		if redo == 'Y': 
			xdata,ydata=[[],[]]
			xflares,yflares=[[],[]]
			xflares,yflares=initial_guess(dir=dir,lc=lc,flares=True)
			print(str(len(xflares))+' Flares @ '+str(xflares))
	redo='Y'
	while redo == 'Y':
		redo=raw_input('Redo Breaks? (y/N) ').upper()
		if redo == 'Y': 
			xdata,ydata=[[],[]]
			xbreaks,ybreaks=[[],[]]
			xbreaks,ybreaks=initial_guess(dir=dir,lc=lc,breaks=True)
			print(str(len(xbreaks))+' Breaks @ '+str(xbreaks))

	numflares=len(xflares)
	numbreaks=len(xbreaks)
	model,fmodel=fit_models(numflares,numbreaks)
	print('Model: ' +model)

	p,yfit,pnames=lc_linfit(np.array(lc['Time']),np.array(lc['Rate']),xbreaks)
	print('Initial Guess for Model: '+str(p))

	fig,ax1=plot_lcfit(lc=lc,noshow=True)
	ax1.plot(np.array(lc['Time']),yfit,color='green')
	ax1.set_title('Initial Guess Fit')
	plot.show()

	return p,model,fmodel,pnames

	## plot again with crude fits

class Click:

	def __init__(self, fig=None):
	
		"""
		Constructor
		
		Arguments:
		fig -- a matplotlib figure
		"""
	
		if fig != None:
			self.fig = fig		
		else:
			self.fig = pyplot.get_current_fig_manager().canvas.figure
		self.nSubPlots = len(self.fig.axes)
		self.dragFrom = None
		self.markers = []
				
		self.retVal = {'x' : [], 'y' : []}

		self.fig.canvas.mpl_connect('button_press_event', self.onClick)

	def onClick(self, event):
	
		"""
		Process a mouse click event. If a mouse is right clicked within a
		subplot, the return value is set to a (subPlotNr, xVal, yVal) tuple and
		the plot is closed. With right-clicking and dragging, the plot can be
		moved.
		
		Arguments:
		event -- a MouseEvent event
		"""		
		
		if event.button == 1:				
		
#			for i in range(self.nSubPlots):
#				subPlot = self.selectSubPlot(i)								
			marker = plot.axvline(event.xdata, 0, 1, linestyle='--', \
				linewidth=2, color='gray')
			self.markers.append(marker)

			self.fig.canvas.draw()
			self.retVal['x'] = np.append(self.retVal['x'],event.xdata)
			self.retVal['y'] = np.append(self.retVal['y'],event.ydata)

		if event.button == 3:
			plot.close()

	def clearMarker(self):
	
		"""Remove marker from retVal and plot"""
		
		self.retVal['x'] = []
		self.retVal['y'] = []
#		for i in range(self.nSubPlots):
#			subPlot = self.selectSubPlot(i)
#		for marker in self.markers:
#			if marker in subPlot.lines:
#			marker.lines.remove(marker)				
		self.markers = []
		self.fig.canvas.draw()

	def show(self):
	
		"""
		Show the plot
		
		Returns:
		A dictionary with information about the response
		"""
		self.clearMarker()
		plot.show()
		return self.retVal

def initial_guess(dir=None,lc=None,flares=False,breaks=False):

	if dir != None:
		lc=read_lc(dir=dir)

	fig,ax1=plot_lcfit(lc=lc,noshow=True)
	if flares:
		ax1.set_title('Click guess for FLARES, right click when finished')
	if breaks:
		ax1.set_title('Click guess for BREAKS, right click when finished')		

	ylim=ax1.get_ylim()

	cp=Click(fig=fig)

	plot.show()
	plot.close('all')

	xdata=cp.retVal['x']
	ydata=cp.retVal['y']

	return xdata,ydata

def fit_models(numflares,numbreaks,norris=False):

	## norm + numflares*3 + numbreaks*2-1
	nump=1 + numflares*3 + numbreaks*2-1
	if numbreaks == 0: nump=nump+2

	if norris:
		g='norris'
	else:
		g='gauss'

	if nump == 2: model='pow'
	if nump == 4: model='bknpow'
	if nump == 5: model=g+'1_pow'
	if nump == 6: model='bkn2pow'
	if nump == 7: model=g+'1_bknpow'
	if nump == 8: 
		model='bkn3pow'
		if numflares == 2: model=g+'2_pow'
	if nump == 9: model=g+'1_bkn2pow'
	if nump == 10:
		model='bkn4pow'
		if numflares == 2: model=g+'2_bknpow'
	if nump == 11:
		if numflares == 3: model=g+'3_pow'
		if numflares == 1: model=g+'1_bkn3pow'
	if nump == 12: model=g+'2_bkn2pow'
	if nump == 13: 
		if numflares == 3: model=g+'3_bknpow'
		if numflares == 1: model=g+'1_bkn4pow'
	if nump == 14: 
		if numflares == 4: model=g+'4_pow'
		if numflares == 2: model=g+'2_bkn3pow'
	if nump == 15: model=g+'3_bkn2pow'
	if nump == 16:  
		if numflares == 4: model=g+'4_bknpow'
		if numflares == 2: model=g+'2_bkn4pow'
	if nump == 17:  
		if numflares == 5: model=g+'5_pow'
		if numflares == 3: model=g+'3_bkn3pow'
	if nump == 18: model=g+'4_bkn2pow'
	if nump == 19:  
		if numflares == 5: model=g+'5_bknpow'
		if numflares == 3: model=g+'3_bkn4pow'
	if nump == 20:  
		if numflares == 6: model=g+'6_pow'
		if numflares == 4: model=g+'4_bkn3pow'
	if nump == 21: model=g+'5_bkn2pow'
	if nump == 22:  
		if numflares == 6: model=g+'6_bknpow'
		if numflares == 4: model=g+'4_bkn4pow'
	if nump == 23:  
		if numflares == 7: model=g+'7_pow'
		if numflares == 5: model=g+'5_bkn3pow'
	if nump == 24: model=g+'6_bkn2pow'
	if nump == 25:  
		if numflares == 7: model=g+'7_bknpow'
		if numflares == 5: model=g+'5_bkn4pow'
	if nump == 26: model=g+'6_bkn3pow'
	if nump == 27: model=g+'7_bkn2pow'
	if nump == 28: model=g+'6_bkn4pow'
	if nump == 29: model=g+'7_bkn3pow'
	if nump == 31: model=g+'7_bkn4pow'

	function_model={
		'gauss': fit_functions.gauss,
		# 'norris': fit_functions.norris,
		'pow': fit_functions.pow,
		'gauss1_pow': fit_functions.gauss1_pow,
		'gauss2_pow': fit_functions.gauss2_pow,
		'gauss3_pow': fit_functions.gauss3_pow,
		'gauss4_pow': fit_functions.gauss4_pow,
		'gauss5_pow': fit_functions.gauss5_pow,
		'gauss6_pow': fit_functions.gauss6_pow,
		# 'norris1_pow': fit_functions.norris1_pow,
		# 'norris2_pow': fit_functions.norris2_pow,
		# 'norris3_pow': fit_functions.norris3_pow,
		# 'norris4_pow': fit_functions.norris4_pow,
		# 'norris5_pow': fit_functions.norris5_pow,
		# 'norris6_pow': fit_functions.norris6_pow,
		'bknpow': fit_functions.bknpow,
		'gauss1_bknpow': fit_functions.gauss1_bknpow,
		'gauss2_bknpow': fit_functions.gauss2_bknpow,
		'gauss3_bknpow': fit_functions.gauss3_bknpow,
		'gauss4_bknpow': fit_functions.gauss4_bknpow,
		'gauss5_bknpow': fit_functions.gauss5_bknpow,
		'gauss6_bknpow': fit_functions.gauss6_bknpow,
		# 'norris1_bknpow': fit_functions.norris1_bknpow,
		# 'norris2_bknpow': fit_functions.norris2_bknpow,
		# 'norris3_bknpow': fit_functions.norris3_bknpow,
		# 'norris4_bknpow': fit_functions.norris4_bknpow,
		# 'norris5_bknpow': fit_functions.norris5_bknpow,
		# 'norris6_bknpow': fit_functions.norris6_bknpow,
		'bkn2pow': fit_functions.bkn2pow,
		'gauss1_bkn2pow': fit_functions.gauss1_bkn2pow,
		'gauss2_bkn2pow': fit_functions.gauss2_bkn2pow,
		'gauss3_bkn2pow': fit_functions.gauss3_bkn2pow,
		'gauss4_bkn2pow': fit_functions.gauss4_bkn2pow,
		'gauss5_bkn2pow': fit_functions.gauss5_bkn2pow,
		'gauss6_bkn2pow': fit_functions.gauss6_bkn2pow,
		# 'norris1_bkn2pow': fit_functions.norris1_bkn2pow,
		# 'norris2_bkn2pow': fit_functions.norris2_bkn2pow,
		# 'norris3_bkn2pow': fit_functions.norris3_bkn2pow,
		# 'norris4_bkn2pow': fit_functions.norris4_bkn2pow,
		# 'norris5_bkn2pow': fit_functions.norris5_bkn2pow,
		# 'norris6_bkn2pow': fit_functions.norris6_bkn2pow,
		'bkn3pow': fit_functions.bkn3pow,
		'gauss1_bkn3pow': fit_functions.gauss1_bkn3pow,
		'gauss2_bkn3pow': fit_functions.gauss2_bkn3pow,
		'gauss3_bkn3pow': fit_functions.gauss3_bkn3pow,
		'gauss4_bkn3pow': fit_functions.gauss4_bkn3pow,
		'gauss5_bkn3pow': fit_functions.gauss5_bkn3pow,
		'gauss6_bkn3pow': fit_functions.gauss6_bkn3pow,
		# 'norris1_bkn3pow': fit_functions.norris1_bkn3pow,
		# 'norris2_bkn3pow': fit_functions.norris2_bkn3pow,
		# 'norris3_bkn3pow': fit_functions.norris3_bkn3pow,
		# 'norris4_bkn3pow': fit_functions.norris4_bkn3pow,
		# 'norris5_bkn3pow': fit_functions.norris5_bkn3pow,
		# 'norris6_bkn3pow': fit_functions.norris6_bkn3pow,
		'bkn4pow': fit_functions.bkn4pow,
		'gauss1_bkn4pow': fit_functions.gauss1_bkn4pow,
		'gauss2_bkn4pow': fit_functions.gauss2_bkn4pow,
		'gauss3_bkn4pow': fit_functions.gauss3_bkn4pow,
		'gauss4_bkn4pow': fit_functions.gauss4_bkn4pow,
		'gauss5_bkn4pow': fit_functions.gauss5_bkn4pow,
		'gauss6_bkn4pow': fit_functions.gauss6_bkn4pow,
		# 'norris1_bkn4pow': fit_functions.norris1_bkn4pow,
		# 'norris2_bkn4pow': fit_functions.norris2_bkn4pow,
		# 'norris3_bkn4pow': fit_functions.norris3_bkn4pow,
		# 'norris4_bkn4pow': fit_functions.norris4_bkn4pow,
		# 'norris5_bkn4pow': fit_functions.norris5_bkn4pow,
		# 'norris6_bkn4pow': fit_functions.norris6_bkn4pow,
		### integral functions
		'intgauss': fit_functions.gauss,
		'intpow': fit_functions.intpow,
		'intgauss1_pow': fit_functions.intgauss1_pow,
		'intgauss2_pow': fit_functions.intgauss2_pow,
		'intgauss3_pow': fit_functions.intgauss3_pow,
		'intgauss4_pow': fit_functions.intgauss4_pow,
		'intgauss5_pow': fit_functions.intgauss5_pow,
		'intgauss6_pow': fit_functions.intgauss6_pow,
		# 'intnorris1_pow': fit_functions.intnorris1_pow,
		# 'intnorris2_pow': fit_functions.intnorris2_pow,
		# 'intnorris3_pow': fit_functions.intnorris3_pow,
		# 'intnorris4_pow': fit_functions.intnorris4_pow,
		# 'intnorris5_pow': fit_functions.intnorris5_pow,
		# 'intnorris6_pow': fit_functions.intnorris6_pow,
		'intbknpow': fit_functions.intbknpow,
		'intgauss1_bknpow': fit_functions.intgauss1_bknpow,
		'intgauss2_bknpow': fit_functions.intgauss2_bknpow,
		'intgauss3_bknpow': fit_functions.intgauss3_bknpow,
		'intgauss4_bknpow': fit_functions.intgauss4_bknpow,
		'intgauss5_bknpow': fit_functions.intgauss5_bknpow,
		'intgauss6_bknpow': fit_functions.intgauss6_bknpow,
		# 'intnorris1_bknpow': fit_functions.intnorris1_bknpow,
		# 'intnorris2_bknpow': fit_functions.intnorris2_bknpow,
		# 'intnorris3_bknpow': fit_functions.intnorris3_bknpow,
		# 'intnorris4_bknpow': fit_functions.intnorris4_bknpow,
		# 'intnorris5_bknpow': fit_functions.intnorris5_bknpow,
		# 'intnorris6_bknpow': fit_functions.intnorris6_bknpow,
		'intbkn2pow': fit_functions.intbkn2pow,
		'intgauss1_bkn2pow': fit_functions.intgauss1_bkn2pow,
		'intgauss2_bkn2pow': fit_functions.intgauss2_bkn2pow,
		'intgauss3_bkn2pow': fit_functions.intgauss3_bkn2pow,
		'intgauss4_bkn2pow': fit_functions.intgauss4_bkn2pow,
		'intgauss5_bkn2pow': fit_functions.intgauss5_bkn2pow,
		'intgauss6_bkn2pow': fit_functions.intgauss6_bkn2pow,
		# 'intnorris1_bkn2pow': fit_functions.intnorris1_bkn2pow,
		# 'intnorris2_bkn2pow': fit_functions.intnorris2_bkn2pow,
		# 'intnorris3_bkn2pow': fit_functions.intnorris3_bkn2pow,
		# 'intnorris4_bkn2pow': fit_functions.intnorris4_bkn2pow,
		# 'intnorris5_bkn2pow': fit_functions.intnorris5_bkn2pow,
		# 'intnorris6_bkn2pow': fit_functions.intnorris6_bkn2pow,
		'intbkn3pow': fit_functions.intbkn3pow,
		'intgauss1_bkn3pow': fit_functions.intgauss1_bkn3pow,
		'intgauss2_bkn3pow': fit_functions.intgauss2_bkn3pow,
		'intgauss3_bkn3pow': fit_functions.intgauss3_bkn3pow,
		'intgauss4_bkn3pow': fit_functions.intgauss4_bkn3pow,
		'intgauss5_bkn3pow': fit_functions.intgauss5_bkn3pow,
		'intgauss6_bkn3pow': fit_functions.intgauss6_bkn3pow,
		# 'intnorris1_bkn3pow': fit_functions.intnorris1_bkn3pow,
		# 'intnorris2_bkn3pow': fit_functions.intnorris2_bkn3pow,
		# 'intnorris3_bkn3pow': fit_functions.intnorris3_bkn3pow,
		# 'intnorris4_bkn3pow': fit_functions.intnorris4_bkn3pow,
		# 'intnorris5_bkn3pow': fit_functions.intnorris5_bkn3pow,
		# 'intnorris6_bkn3pow': fit_functions.intnorris6_bkn3pow,
		'intbkn4pow': fit_functions.intbkn4pow,
		'intgauss1_bkn4pow': fit_functions.intgauss1_bkn4pow,
		'intgauss2_bkn4pow': fit_functions.intgauss2_bkn4pow,
		'intgauss3_bkn4pow': fit_functions.intgauss3_bkn4pow,
		'intgauss4_bkn4pow': fit_functions.intgauss4_bkn4pow,
		'intgauss5_bkn4pow': fit_functions.intgauss5_bkn4pow,
		'intgauss6_bkn4pow': fit_functions.intgauss6_bkn4pow,
		# 'intnorris1_bkn4pow': fit_functions.intnorris1_bkn4pow,
		# 'intnorris2_bkn4pow': fit_functions.intnorris2_bkn4pow,
		# 'intnorris3_bkn4pow': fit_functions.intnorris3_bkn4pow,
		# 'intnorris4_bkn4pow': fit_functions.intnorris4_bkn4pow,
		# 'intnorris5_bkn4pow': fit_functions.intnorris5_bkn4pow,
		# 'intnorris6_bkn4pow': fit_functions.intnorris6_bkn4pow,
	}

	return model,function_model#[model]

def plot_lcfit(grbdict=None,lc=None,p=None,resid=True,noshow=False):

### if no p, plot without

	if grbdict:
		lc=grbdict.lc
		p=grbdict.lcfit
	else:
		if not lc:
			print('Need to specify GRB dictionary or lc')
			return

	if p:
		if resid: 
			f,(ax1,ax2) = plot.subplots(2,sharex=True)
	else: 
		resid=False
		f,ax1=plot.subplots(1)

	xrttype=np.array(['WTSLEW','WT','WTUL','PC','PCUL'])
	color=np.array(['cyan','blue','blue','red','red'])

	tlim=[10**round(np.log10(min(lc['Time']+lc['T_-ve']))-0.5),10**round(np.log10(max(lc['Time']+lc['T_+ve']))+0.5)]

	for t in range(len(xrttype)):
		w=np.where(lc['Type']==xrttype[t])
		if len(w[-1])>0:

			if 'UL' in xrttype[t]: 
				uplims=True
				yerr=0.8*lc['Rate'][w]
				noleg='_'
			else:
				uplims=False
				yerr=[-lc['Rateneg'][w],lc['Ratepos'][w]]
				noleg=''

			ax1.errorbar(lc['Time'][w],lc['Rate'][w],xerr=[-lc['T_-ve'][w],lc['T_+ve'][w]],\
				yerr=yerr,ecolor=color[t],linestyle='None',\
				capsize=0,label=noleg+xrttype[t],uplims=uplims,fmt='none')

			if p:
				if resid: 
					yfit=fit_functions.call_function(p.model,lc['Time'][w],p)
					res=lc['Rate'][w]/yfit
					ax2.errorbar(lc['Time'][w],res,xerr=[-lc['T_-ve'][w],lc['T_+ve'][w]],\
						yerr=yerr/yfit,linestyle='None',capsize=0,fmt='none',ecolor=color[t],\
						uplims=uplims,label=noleg+xrttype[t])
					ax2.plot(tlim,[1,1],linestyle='--',color='black')
					f.subplots_adjust(hspace=0)

	if p:
		print(p.model)
#		yfit=getattr(importlib.import_module('fit_functions'),p.model)(lc['Time'],p.par)
		yfit=fit_functions.call_function(p.model,lc['Time'],p)
		ax1.plot(lc['Time'],yfit,color='green')

		
	ax1.legend(loc="upper right")
	ax1.set_yscale('log')
	ax1.set_xscale('log')
	ax1.set_ylabel(r'Count Rate (0.3-10 keV) (erg cm$^{-2}$ s$^{-1}$)')
#	ylim=ax1.get_ylim()
#	ax1.set_ylim([10**round(np.log10(ylim[0])-0.5),10**round(np.log10(ylim[1])+0.5)])
	ax1.yaxis.set_tick_params(right='on',which='both')
	if resid:
		ax2.set_xscale('log')
		ax2.set_xlabel('Time since trigger (s)')
		ax2.set_ylabel('Residual')
		ax2.set_ylim([0,3])
	else:
		ax1.set_xlabel('Time since trigger (s)')

	if noshow == False:
		plot.show()
		plot.close('all')

	return f,ax1

def read_lcfit(dir='',file=''):

	if not file: file=dir+'lc_fit_out_idl_int9.dat'
	if not os.path.exists(file):
		print('No fit file: '+file)
		p=0
	else:
		f=open(file,'r')
		lines=f.readlines()
		pnames=[]
		par=[]
		pneg=[]
		ppos=[]
		chisq=[]
		dof=[]
		go=0
		for line in lines:
			tmp=line.split()
			if tmp[0] == 'no': break
			if len(tmp) > 2:
				pnames.append(tmp[0])
				par.append(float(tmp[1]))
				pneg.append(float(tmp[2]))
				ppos.append(float(tmp[3]))
			if (len(tmp) == 2) & go==0:
				chisq=float(tmp[1])
				go=1
			if (len(tmp) == 2) & (go==1):
				dof=float(tmp[1])
				continue

		nump=len(par)
		nf=len([p for p in pnames if 'g' in p])
		model='nofit'
		if nump == 2: model='pow'
		if nump == 4: model='bknpow'
		if nump == 5: model='gauss1_pow'
		if nump == 6: model='bkn2pow'
		if nump == 7: model='gauss1_bknpow'
		if nump == 8: 
			model='bkn3pow'
			if nf == 2: model='gauss2_pow'
		if nump == 9: model='gauss1_bkn2pow'
		if nump == 10:
			model='bkn4pow'
			if nf == 2: model='gauss2_bknpow'
		if nump == 11:
			if nf == 3: model='gauss3_pow'
			if nf == 1: model='gauss1_bkn3pow'
		if nump == 12: model='gauss2_bkn2pow'
		if nump == 13: 
			if nf == 3: model='gauss3_bknpow'
			if nf == 1: model='gauss1_bkn4pow'
		if nump == 14: 
			if nf == 4: model='gauss4_pow'
			if nf == 2: model='gauss2_bkn3pow'
		if nump == 15: model='gauss3_bkn2pow'
		if nump == 16:  
			if nf == 4: model='gauss4_bknpow'
			if nf == 2: model='gauss2_bkn4pow'
		if nump == 17:  
			if nf == 5: model='gauss5_pow'
			if nf == 3: model='gauss3_bkn3pow'
		if nump == 18: model='gauss4_bkn2pow'
		if nump == 19:  
			if nf == 5: model='gauss5_bknpow'
			if nf == 3: model='gauss3_bkn4pow'
		if nump == 20:  
			if nf == 6: model='gauss6_pow'
			if nf == 4: model='gauss4_bkn3pow'
		if nump == 21: model='gauss5_bkn2pow'
		if nump == 22:  
			if nf == 6: model='gauss6_bknpow'
			if nf == 4: model='gauss4_bkn4pow'
		if nump == 23:  
			if nf == 7: model='gauss7_pow'
			if nf == 5: model='gauss5_bkn3pow'
		if nump == 24: model='gauss6_bkn2pow'
		if nump == 25:  
			if nf == 7: model='gauss7_bknpow'
			if nf == 5: model='gauss5_bkn4pow'
		if nump == 26: model='gauss6_bkn3pow'
		if nump == 27: model='gauss7_bkn2pow'
		if nump == 28: model='gauss6_bkn4pow'
		if nump == 29: model='gauss7_bkn3pow'
		if nump == 31: model='gauss7_bkn4pow'

		p=fit_params(model,pnames,par,pneg,ppos,chisq,dof)
	
	return p

class grb_object:

	def __init__(self,grb,targid,trigtime,met,lc,p,s):

		self.grb=grb
		self.targid=targid
		self.trigtime=trigtime
		self.met=met
		self.lc=lc
		self.lcfit=p
		self.specfit=s
	#	self=Table(names=('grb','targid','trigtime','met','z','lcfit','lc')) 

	def keys(self):
		print(['grb','targid','trigtime','met','lc','p','s'])

def load_data(dir=None):

	## Read curve.qdp header for GRB name, trigger number, & trigger time

	if dir ==None:
		dir='/Users/jracusin/GRBs/'
	grbs,targids=download_UL()
	mets=[]
	trigtimes=[]
	i=0
	grblist=[]
	grbdict={}

	for grb in grbs:
		curve_file=dir+grb+'/curve.qdp'

		if os.path.exists(curve_file):
			f=open(curve_file,'r')
			lines=f.readlines()
			tmp=re.split(',|=| ',lines[1])
			#print grb,tmp[9]
			if any("T0 for this burst is Swift" in t for t in tmp):
				met=float(tmp[9])
				trigtime=tmp[14]+'-'+str(time.strptime(tmp[15],'%b').tm_mon)+'-'+tmp[16]+' '+tmp[18]
			else:
				met=-1
				trigtime=''

			mets=np.append(mets,met)
			trigtimes=np.append(trigtimes,trigtime)

			targid=targids[i]
			lc=read_lc(dir+grb+'/')
			p=read_lcfit(dir+grb+'/')
			s=read_specfit(dir=dir)

			## create GRB object
			g=grb_object(grb,targid,trigtime,met,lc,p,s)
			## add to list
			grblist.append(g)
			## add to dictionaries of objects
			grbdict[g.grb]=g
		i=i+1
		
	## make record array
	c1=fits.Column(name='grb',format='10A',array=grbs)
	c2=fits.Column(name='targid',format='8A',array=targids)
	c3=fits.Column(name='trigtime',format='23A',array=trigtimes)
	c4=fits.Column(name='met',format='D',array=mets)
	coldefs = fits.ColDefs([c1, c2, c3, c4])
	tbhdu = fits.BinTableHDU.from_columns(coldefs)
	grbrec=tbhdu.data



	return grbdict,grbrec,grblist

		# self.grb=grbs
		# self.targid=targids
		# self.met=met
		# self.trigtime=trigtime

		# self.lc=lc
		### loop through and read in each GRB
		## can put in cuts like z-only, xrt-only, lat-only, gbm-only

### have object for each GRB
### have dictionary accessing each object by GRB name?
### need list or dictionary of dictionaries?

### create fits record array of all params
### have function to grab object for that GRB with fit params & LC?

class specfit_params:

	def __init__(self,mode,galnh,nh,nh_err_neg,nh_err_pos,gamma,gamma_err_neg,gamma_err_pos,\
		flux,flux_err_neg,flux_err_pos,unabs_flux,unabs_flux_err_neg,unabs_flux_err_pos,\
		cstat,dof,rate,corr,ontime):

#		self.mode=mode
		self.galnh=galnh
		self.nh=nh
		self.nh_err=[nh_err_neg,nh_err_pos]
		self.gamma=gamma
		self.gamma_err=[gamma_err_neg,gamma_err_pos]
		self.flux=flux
		self.flux_err=[flux_err_neg,flux_err_pos]
		self.unabs_flux=unabs_flux
		self.unabs_flux_err=[unabs_flux_err_neg,unabs_flux_err_pos]
		self.cstat=cstat
		self.dof=dof
		self.rate=rate
		self.corr=corr
		self.ontime=ontime

def read_specfit(dir=''):

	files=np.array(['interval0wt_fit.fit','interval0pc_fit.fit','late_timepc_fit.fit'])
	modes=['WT','PC','PCLATE']

	nfiles=len(files)
	if (len(dir)>0) & ('/' not in dir): 
		dir=dir+'/'

	spec={}
	i=0
	for file in files:
		if os.path.exists(dir+file):
#			print(file)
			f=open(dir+file,'r')
			lines=f.readlines()
			l=0
			mode=modes[i]
			for line in lines:
				tmp=re.split('\n|\t| |,|\(|\)|=|:',line)
				tmp=filter(None,tmp)
#				print tmp
				if l == 0: galnh=float(tmp[1])
				if l == 1: 
					nh=float(tmp[1])
					nh_err_neg=0
					nh_err_pos=0
					if float(tmp[2]) != 0.: 
						nh_err_neg=nh-float(tmp[2])
					if float(tmp[3]) != 0.: 
						nh_err_pos=float(tmp[3])-nh
				if l == 2:
					gamma=float(tmp[1])
					gamma_err_neg=0
					gamma_err_pos=0
					if float(tmp[2]) != 0.:
						gamma_err_neg=gamma-float(tmp[2])
					if float(tmp[3]) != 0.:
						gamma_err_pos=float(tmp[3])-gamma
				if l == 3:
					flux=float(tmp[2])
					flux_err_neg=1.
					flux_err_pos=1.
					if float(tmp[3]) != 1.:
						flux_err_neg=flux-float(tmp[3])
					if float(tmp[4]) != 1.:
						flux_err_pos=float(tmp[4])-flux
				if l == 4:
					unabs_flux=float(tmp[2])
					unabs_flux_err_neg=1.
					unabs_flux_err_pos=1.
					if float(tmp[3]) != 1.:
						unabs_flux_err_neg=unabs_flux-float(tmp[3])
					if float(tmp[4]) != 1.:
						unabs_flux_err_pos=float(tmp[4])-unabs_flux
				if l == 5:
					cstat=float(tmp[1])
					dof=float(tmp[3])
				if l == 6:
					rate=float(tmp[3])
				if l == 7:
					corr=float(tmp[2])
				if l == 8:
					ontime=tmp[1]

				l=l+1

			s=specfit_params(mode,galnh,nh,nh_err_neg,nh_err_pos,gamma,gamma_err_neg,gamma_err_pos,\
				flux,flux_err_neg,flux_err_pos,unabs_flux,unabs_flux_err_neg,unabs_flux_err_pos,\
				cstat,dof,rate,corr,ontime)
			i=i+1
			#spec.append(s)  ## list
			spec[mode]=s

	## make list of specfit objects

	return spec

class fit_params:
	
	def __init__(self,model,pnames,par,perror_neg,perror_pos,chisq,dof):
		self.model=model
		self.pnames=pnames
		self.par=par
		perror=np.array([perror_neg,perror_pos])
		perror=perror.transpose()
		self.perror=perror
		self.chisq=chisq
		self.dof=dof

	def list(self):
		print('Model = ',self.model)
		print('Pname = ',self.pnames)
		print('Par = ',self.par)
		print('Perror = ',self.perror)
		print('Chisq = ',self.chisq)
		print('DOF = ',self.dof)

	### to make list of object: plist=[fit_params(count) for count in xrange(n)]

def read_curve(file):

	f=open(file,'r')
	lines=f.readlines()
	header=[]
	start=0
	done=0
	data=[]
	for line in lines:
		tmp=line.split()
		if len(tmp) >0:
			if (tmp[1] == 'WTSLEW') & (not header):
				start=1
				continue
			if (tmp[1] == 'NO'):
				break
			if (start == 1) & (not header):
				header=tmp
#				header[0]='Time'
				d=Table(names=header)
				continue
			if (start == 1) & (len(header)>0):
				d.add_row(tmp)

	f.close()

	return d

def read_lc(dir=''):

	files=np.array(['WTCURVE.qdp','WTUL.qdp','PCCURVE.qdp','PCUL.qdp','curve.qdp'])
	type=np.array(['WT','WTUL','PC','PCUL','WTSLEW'])
	nfiles=len(files)
	if (len(dir)>0) & ('/' not in dir): 
		dir=dir+'/'

	start=0
	itworked=False
	for f in range(nfiles):
		if os.path.isfile(dir+files[f]):
#			print(files[f])
#			print f
			if f<=3:
				data=ascii.read(dir+files[f],header_start=2,data_start=3)
				ncol=len(data[0])
				ndata=len(data)
				if ncol >16:
					del data['SYS_NEG','SYS_POS']
				t=Column(np.repeat(type[f],ndata),name='Type')
				data.add_column(t)
				if start==0:
					d=data
					start=1
				else:
					d=join(d,data,join_type='outer')
#				print len(d)
			if f==4:
				if 'WTSLEW' in open(dir+files[f]).read():
					data=read_curve(dir+files[f])
					ndata=len(data)
					t=Column(np.repeat(type[f],ndata),name='Type')
					data.add_column(t)
					d=join(d,data,join_type='outer')
			itworked=True
#		print dir+files[f]

	if itworked: 
		d.rename_column('!Time','Time')
#		print 'what?'
	else: d=0

	return d

def download_UL(update=False,dir=None):

	import urllib

	# ### download trigIDs
	url="http://www.swift.ac.uk/xrt_curves/allcurves2.php"
	if dir == None:
		dir='/Users/jracusin/GRBs/'
	if os.path.exists(dir+'reftime.dat'):
		fref=open(dir+'reftime.dat','r')
		reftime=float(fref.read())
		fref.close()
	else:
		reftime=0.
#	reftime=1484340227.502976 ## Jan 13, 2017 - when this was written  time.time()

	filename=dir+'allcurves2.php'
	if not os.path.exists(filename) or update:
		if update: os.remove(filename)	
		urllib.urlretrieve(url,filename)
		#wget.download(url,filename)
		print 'downloading GRB list: ', filename
	f=open(filename,'r')
	lines=f.readlines()

	targids=[]
	grbs=[]
	for line in lines: 
		if "<td><p class='grb'>GRB" in line: 
			tmp=line
			tmp=re.split('<|>|/',line)
			targids=np.append(targids,tmp[10])
			grbs=np.append(grbs,tmp[4].replace(" ",""))

	# download LCs
	files=np.array(['curve.qdp','WTCURVE.qdp','WTUL.qdp','PCCURVE.qdp','PCUL.qdp',\
		'interval0wt_fit.fit','interval0pc_fit.fit','late_timepc_fit.fit'])
	### figure out spec files logic - right now won't download because curve.qdp exists

	for i in range(len(grbs)):
		grb=grbs[i]
		targid=targids[i]
		dir='/Users/jracusin/GRBs/'+grb+'/'
		if not os.path.exists(dir): os.makedirs(dir)
		fage=-1
		for file in files:
			if os.path.exists(dir+file):
				ftime=os.path.getmtime(dir+file)
				if file==files[0]:
					fage=ftime-reftime
				else: fage=0
			if 'qdp' in file: 
				lcspec='xrt_curves/'
			else: lcspec='xrt_spectra/'
			if fage < 0:  # if file created before reftime
				url="http://www.swift.ac.uk/"+lcspec+targid+"/"+file
				print 'downloading: ', url
				print dir+file
				urllib.urlretrieve(url,dir+file)
				#wget.download(url,dir+file)
			if os.path.exists(dir+file):
				f=open(dir+file,'r')
				lines=f.readlines()
				if any("404 page not found" in line for line in lines): 
					os.remove(dir+file)


	fref=open(dir+'reftime.dat','w')
	reftime=time.time()
	fref.write(str(reftime))
	fref.close()

	return grbs,targids