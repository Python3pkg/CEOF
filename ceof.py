#!/usr/bin/env python
# -*- coding: Latin-1 -*-

""" Class to deal with Complex EOF
"""

import numpy
import numpy as np
from numpy import ma
from UserDict import UserDict


def ceof2D(data):
    """ Estimate the complex EOF on a 2D array.

        Time should be the first dimension, so that the PC (eigenvalues) will
          be in respect to the first dimension.

    """
    assert type(data) is np.ndarray
    assert np.isfinite(data).all()
    # ---- Creating the complex field using Hilbert transform
    input_H = numpy.empty(data.shape, dtype=data.dtype)
    import scipy.fftpack
    for i in range(data.shape[1]):
        input_H[:,i] = scipy.fftpack.hilbert(data[:,i])

    U = data + 1j*input_H
    #if U.mask.any():
    #    print "There are masked values in U at CEOF_2D()"

    from pyclimate.svdeofs import svdeofs, getvariancefraction
    pcs, lambdas, eofs = svdeofs(U)

    return {'pcs': pcs, 'lambdas': lambdas, 'eofs': eofs}


class CEOF_2D(UserDict):
    """ Complex EOF of a scalar 2D array
    """
    def __init__(self, input, cfg={}):
        # ---- Checks ----
        if len(input.shape) != 2:
            print "The input should be a 2D array, ready to run the EOF"
            return
        # ----------------
        self.input = input.copy()
        self.data = {'input': input.copy()}
        if cfg == {}:
            self.cfg = {'cumvar':1,'normalize':'pc_median'}
        else:
            self.cfg = cfg

        self.go()

        return

    def go(self):
        # ---- Creating the complex field using Hilbert transform
        input_H = ma.masked_all(self['input'].shape)
        #input_H = numpy.zeros(self['input'].shape,dtype=self['input'].dtype)
        import scipy.fftpack
        for i in range(self['input'].shape[1]):
            input_H[:,i] = scipy.fftpack.hilbert(self['input'][:,i])
        U = self['input'] + 1j*input_H
        if U.mask.any():
            print "There are masked values in U at CEOF_2D()"

        from pyclimate.svdeofs import svdeofs, getvariancefraction
        pcs, lambdas, eofs = svdeofs(U.data)

        # Define how many modes will be returned by the explainned variance.
        # cumvar = 1 means 100%, i.e. all modes
        if self.cfg['cumvar'] == 1:
            nmodes = len(lambdas)
        else:
	    # This don't work. Need to improve it.
            nmodes = (numpy.arange(len(lambdas))[numpy.cumsum(getvariancefraction(lambdas))>=self.cfg['cumvar']])[0]
	
	if 'maxnmodes' in self.cfg:
	    nmodes = min(nmodes,self.cfg['maxnmodes'])

	print "Considering the first %s of %s modes." % (nmodes,len(lambdas))

        # ---- Normalize -----------------------------------------------------
        if 'normalize' in  self.cfg:
            if self.cfg['normalize'] == 'pc_std':
                print "Normalizing by the pc_std"
                #for n in range(pcs.shape[1]):
                for n in range(nmodes):
                    fac = (numpy.absolute(pcs[:,n])).std()
                    #print "mode %s, fac: %s" % (n,fac)
                    pcs[:,n] = pcs[:,n]/fac
                    eofs[:,n] = eofs[:,n]*fac
            elif self.cfg['normalize'] == 'pc_median':
                print "Normalizing by the pc_median"
                #for n in range(pcs.shape[1]):
                for n in range(nmodes):
                    #fac = (numpy.absolute(pcs[:,n])).mean()
                    fac = numpy.median((numpy.absolute(pcs[:,n])))
                    #print "mode %s, fac: %s" % (n,fac)
                    pcs[:,n] = pcs[:,n]/fac
                    eofs[:,n] = eofs[:,n]*fac
            elif self.cfg['normalize'] == 'pc_max':
                print "Normalizing by the pc_max"
                #for n in range(pcs.shape[1]):
                for n in range(nmodes):
                    fac = (numpy.absolute(pcs[:,n])).max()
                    #print "mode %s, fac: %s" % (n,fac)
                    pcs[:,n] = pcs[:,n]/fac
                    eofs[:,n] = eofs[:,n]*fac
            elif self.cfg['normalize'] == 'eof_max':
                print "Normalizing by the eof_max"
                for n in range(nmodes):
                    fac = (numpy.absolute(eofs[:,n])).max()
                    eofs[:,n] = eofs[:,n]/fac
                    pcs[:,n] = pcs[:,n]*fac
            elif self.cfg['normalize'] == 'eof_std':
                print "Normalizing by the eof_std"
                for n in range(nmodes):
                    fac = (numpy.absolute(eofs[:,n])).std()
                    #print "mode %s, fac: %s" % (n,fac)
                    eofs[:,n] = eofs[:,n]/fac
                    pcs[:,n] = pcs[:,n]*fac
            else:
                print "Don't understand the normalization config: %s" % self.cfg['normalize']

        self.data['eofs'] = eofs[:,:nmodes]
        self.data['pcs'] = pcs[:,:nmodes]
        self.data['lambdas'] = lambdas[:nmodes]
        self.data['variancefraction'] = getvariancefraction(lambdas)[:nmodes]

        return

def ceof_reconstruct(eofs, pcs, modes):
    """
    """
    if modes == 'all':
        modes = range(pcs.shape[1])
    elif type(modes) == int:
        modes = range(modes)
    print "Reconstructing from EOF using the modes: %s" % modes
    T = pcs.shape[0]
    eof_amp=(eofs.real**2+eofs.imag**2)**0.5
    eof_phase=numpy.arctan2(eofs.imag,eofs.real)
    pc_amp = (numpy.real(pcs)**2+numpy.imag(pcs)**2)**0.5
    pc_phase = numpy.arctan2(numpy.imag(pcs),numpy.real(pcs))	

    data = ma.zeros((T,eofs.shape[0],eofs.shape[1]))
    for t in range(T):
        for n in modes:
            data[t] = data[t] + eof_amp[:,:,n]*pc_amp[t,n]*numpy.cos(eof_phase[:,:,n]+pc_phase[t,n])
    return data

def make_animation(data, eofdata, t, lat, lon, outputfilename, limits = None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt   # For plotting graphs.
    import pylab
    from mpl_toolkits.basemap import Basemap

    #import numpy as np
    #import subprocess                 # For issuing commands to the OS.
    import os
    import sys                        # For determining the Python version.

    not_found_msg = """
    The mencoder command was not found;
    mencoder is used by this script to make an avi file from a set of pngs.
    It is typically not installed by default on linux distros because of
    legal restrictions, but it is widely available.
    """

    if limits == None:
        LatIni = lat.min()
        LatFin = lat.max()
        LonIni = lon.min()
        LonFin = lon.max()
    else:
        LatIni = limits['LatIni']
        LatFin = limits['LatFin']
        LonIni = limits['LonIni']
        LonFin = limits['LonFin']

    #try:
    #    subprocess.check_call(['mencoder'])
    #except subprocess.CalledProcessError:
    #    print "mencoder command was found"
    #    pass # mencoder is found, but returns non-zero exit as expected
    #         # This is a quick and dirty check; it leaves some spurious output
    #	     # for the user to puzzle over.
    #except OSError:
    #	 print not_found_msg
    #     sys.exit("quitting\n")

    parallels = numpy.arange(-5,20.1,5)
    meridians = numpy.arange(300,340,10)
    V = range(-20, 21, 1)
    for i in range(len(t)) :
        #fig = plt.figure(figsize=(14,10.5), dpi=100)
        pylab.subplot(211)
        map = Basemap(projection='merc',lat_ts=0,llcrnrlon=LonIni,llcrnrlat=LatIni, urcrnrlon=LonFin, urcrnrlat=LatFin,resolution='l',area_thresh=1000.)
        X, Y = map(*pylab.meshgrid(lon, lat))
        map.contourf(X,Y, data[i], V)
        plt.colorbar(shrink=0.8)
        map.drawcoastlines()
        map.fillcontinents(color='0.0')
        map.drawparallels(parallels,labels=[1,0,0,1])
        map.drawmeridians(meridians,labels=[1,0,0,1])
        plt.title('%s' % (t[i].strftime('%Y-%m-%d')))
        #
        pylab.subplot(212)
        map = Basemap(projection='merc',lat_ts=0,llcrnrlon=LonIni,llcrnrlat=LatIni, urcrnrlon=LonFin, urcrnrlat=LatFin,resolution='l',area_thresh=1000.)
        X, Y = map(*pylab.meshgrid(lon, lat))
        map.contourf(X,Y, eofdata[i], V)
        plt.colorbar(shrink=0.8)
        map.drawcoastlines()
        map.fillcontinents(color='0.0')
        map.drawparallels(parallels,labels=[1,0,0,1])
        map.drawmeridians(meridians,labels=[1,0,0,1])
        plt.title('%s (EOF reconstructed)' % (t[i].strftime('%Y-%m-%d')))
        # ----
        filename = str('../tmp/%04d' % i) + '.png'
        plt.savefig(filename, dpi=100)
        print 'Wrote file', filename
        #
        # Clear the figure to make way for the next image.
        #
        plt.clf()

    command = ('mencoder',
               'mf://../tmp/*.png',
               '-mf',
               'type=png:w=800:h=600:fps=2',
               '-ovc',
               'lavc',
               '-lavcopts',
               'vcodec=mpeg4',
               '-oac',
               'copy',
               '-o',
               outputfilename)
    
    os.spawnvp(os.P_WAIT, 'mencoder', command)

    #print "\n\nabout to execute:\n%s\n\n" % ' '.join(command)
    #subprocess.check_call(command)

    print "\n\n The movie was written to 'output.avi'"

    print "\n\n You may want to delete *.png now.\n\n"
    return


class CEOF_Filter():
    """ Unfinished
    
        This will be a class to filter using EOF. One define the number of modes
	  or the desired variability to be explainned. The field is decomposed
	  by CEOF, than the field is reconstructed considering only the n first
	  modes.



    """
    def __init__(self,input,metadata={'variancefraction_explainned':0.95}):
        """
	"""
	N = pcs.shape[1]    # Now it is all the modes.
        T = pcs.shape[0]
	I = eofs.shape[0]
	J = eofs.shape[1]
        data_filtered = numpy.zeros((T, I, J))

        eof_amp=(eof.real**2+eof.imag**2)**0.5
        eof_phase=numpy.arctan2(eof.imag,eof.real)
        pc_amp = (numpy.real(pc)**2+numpy.imag(pc)**2)**0.5
        pc_phase = numpy.arctan2(numpy.imag(pc),numpy.real(pc))	

	for t in range(T):
            for n in range(N):
	        data_filtered[t] = data_filtered[t] + eof_amp[:,:,n]*pc_amp[t,n]*numpy.cos(eof_phase[:,:,n]+pc_phase[t,n])
        return

def CEOF_2D_limited(input,metadata={'variancefraction_explainned':0.95}):
        #self.data['input']=input.copy
        ceof = CEOF_2D(input)
        if 'nmodes' not in metadata:
            nmodes=len(ceof['variancefraction'])
        if 'variancefraction_explainned' in metadata:
            nmodes=(numpy.ones(ceof['variancefraction'].shape)[numpy.cumsum(ceof['variancefraction'])<=metadata['variancefraction_explainned']]).sum().astype('i')
        if 'nmodes_max' in metadata:
            if metadata['nmodes_max']<nmodes:
                nmodes=metadata['nmodes_max']
        nt,ni,nj=input.shape
        filtred=numpy.zeros((nt,ni,nj))
        for t in range(nt):
            #for n in range(20):
            for n in range(ceof['pcs'].shape[1]):
                filtred[t,:,:]+=ceof['eofs'][:,:,n].real*x['pcs'][t,n].real
        #self.data['filtred']=filtred
        return filtred


class CEOF(UserDict):
    """
    """
    def __init__(self, input, metadata={}, logger=None, **keywords):
        """
            Time should be the first dimension, i.e. axis=0
        """
        self.input = input.copy()
        self.data = input.copy()
        self.metadata = metadata

        self.go()
        return

    def gridto2D(self,var,ind=None):
        """
        """
        I,J,K = self.data[var].shape

        if ind == None:
            ind = numpy.ones((J,K))==1

        N = ((numpy.ones(ind.shape)[ind]).sum())

        self.data2D={}
        for k in ['lat','lon']:
            self.data2D[k]=ma.masked_all(N,dtype=self.data[k].dtype)

        self.data2D['grid_index'] = ma.masked_all((N,2))

        for k in [var]:
            self.data2D[k]=ma.masked_all((I,N),dtype=self.data[k].dtype)

        n=-1
        for j in range(J):
            for k in range(K):
                if ind[j,k]:
                    n+=1
                    self.data2D['grid_index'][n] = numpy.array([j,k])
                    self.data2D['lat'][n]=self.data['Lat'][j,k]
                    self.data2D['lon'][n]=self.data['Lon'][j,k]
                    self.data2D[var][:,n]=self.data[var][:,j,k]
        return

    def filter(self,var,l,type,l2=None):
        #from maud import window_mean
        from maud import window_1Dmean_grid
        from datetime import timedelta
        
        if len((set(numpy.diff(self.data['datetime'])))) !=1:
            print "Class incomplete. Can't deal with a non regular time series"
            return

        dt=self.data['datetime'][1]-self.data['datetime'][0]
        if type == 'bandpass':
            tscale = dt.days+dt.seconds/86400.
            ll = (l.days+l.seconds/86400.)/tscale
            ll2 = (l2.days+l2.seconds/86400.)/tscale
            #lowpass = window_mean.window_1Dmean_grid(self.data[var], ll/2., method='hann', axis=0)
            lowpass = window_1Dmean_grid(self.data[var], ll/2., method='hann', axis=0)
            output = window_1Dmean_grid(lowpass, ll2/2., method='hann', axis=0)
            output = lowpass - output

            print "ATENTION!!!! Improve this here!!!"
            self.halfpower_period = "20-120"
        else:
            ll=(l.days+l.seconds/86400.)/(dt.days+dt.seconds/86400.)

            if ll<1:
                print "This filter will have no effect. Data series have not enough resolution."
                return

            lowpass=window_mean.window_1Dmean_grid(self.data[var],ll/2.,method='hann',axis=0)
            #lowpass=window_mean.window_1Dmean(self.data[var],ll,method='hanning',axis=0)
            if type=='lowpass':
                output=lowpass
            elif type=='highpass':
                #self.data[var]=x_highpass=self.data[var]-(lowpass-lowpass.mean())
                output=self.data[var]-(lowpass)
                #output=self.data[var]-lowpass
            else:
                print "On function filter, type must be lowpass or highpass"

            halfpower_period = window_mean.get_halfpower_period(self.data[var],output,dt=dt)
            print "Filter half window size: %s" % l
            print "Half Power Period: %s" % halfpower_period
            self.halfpower_period = halfpower_period
        
        # ----
	## I should move this to inside the window_mean_1D_grid
	#nt,ni,nj = self.data[var].shape
	#gain = ma.masked_all((nt,ni,nj))
	#for i in range(ni):
	#    for j in range(nj):
	#        if output[:,i,j].mask.all()==False:
        #            gain[:,i,j] = numpy.absolute(numpy.fft.fft(output[:,i,j]-output[:,i,j].mean())) / numpy.absolute(numpy.fft.fft(self.data[var][:,i,j]-self.data[var][:,i,j].mean()))
	#gain_median = ma.masked_all(nt)
	#for t in range(nt):
	#    gain_median[t] = numpy.median(gain[t,:,:].compressed()[numpy.isfinite(gain[t,:,:].compressed())])
	#freq=numpy.fft.fftfreq(nt)/dt.days
	#import rpy2.robjects as robjects
	#smooth = robjects.r['smooth.spline'](robjects.FloatVector(gain_median[numpy.ceil(nt/2.):]),robjects.FloatVector(-freq[numpy.ceil(nt/2.):]),spar=.4)
	##smooth = robjects.r['smooth.spline'](robjects.FloatVector(-freq[numpy.ceil(nt/2.):]),robjects.FloatVector(gain_median[numpy.ceil(nt/2.):]),spar=.4)
	#s_interp = robjects.r['predict'](smooth,x=0.5)
	#halfpower_period = 1./s_interp.rx2['y'][0]

        # ----
        self.data[var]=output

        return

    def select_data(self, var, polygon_coordinates):
        """
        """
        #var = 'ssh'
        T,I,J = self.data[var].shape
        tmp=numpy.ones((J,K))==1
        for i in range(I):
            for j in range(J):
                   tmp[i,j] = ((self.data[var].mask)[:,i,j]).all()==False


        from shapely.geometry import Polygon
        from shapely.geometry import Point
        polygon = Polygon(polygon_coordinates)

        ind = ind&tmp
        return ind



    def set_wavelenght(self):
        """ Estimate the wavelenghts from the gradient of the EOF


	"""

        eof_phase=numpy.arctan2(self['eofs'].imag, self['eofs'].real)

        eof_phase_360 = eof_phase.copy()
        eof_phase_360[eof_phase<0] = 2*numpy.pi+eof_phase[eof_phase<0]

        from fluid.common.common import _diff_centred
        dx_eof_phase = _diff_centred(eof_phase,dim=1)
        dx_eof_phase_360 = _diff_centred(eof_phase_360, dim=1)

        ind = abs(dx_eof_phase)>abs(dx_eof_phase_360)
        dx_eof_phase[ind] = dx_eof_phase_360[ind]

	self.data['dx_eof_phase'] = dx_eof_phase

        #from scipy.interpolate import bisplrep, bisplev
        #tck = bisplrep(x['Lon'], x['Lat'], eof_phase)
        #dx_eof_phase_spline = bisplev(x['Lon'][0,:], x['Lat'][:,0],tck,dx=1)#/self.data['dX']

        from fluid.common.common import lonlat2dxdy
        #dX, dY = lonlat2dxdy( x['Lon'][0,:], self['Lat'][:,0])
        dX, dY = lonlat2dxdy( self['lon'], self['lat'])

        L_x = ma.masked_all(dx_eof_phase.shape)
	for n in range(dx_eof_phase.shape[-1]):
	    L_x[:,:,n] = dX/dx_eof_phase[:,:,n]*2*numpy.pi*1e-3

        #self.data['L_x'] = dX/dx_eof_phase*2*numpy.pi*1e-3
        self.data['L_x'] = L_x


        #from fluid.common.common import _diff_centred
        #eof_phase=numpy.arctan2(x['eofs'].imag,x['eofs'].real)
        #deof_x=_diff_centred(eof_phase,dim=1)
        #pylab.contourf(eof_phase[:,:,0])
        #pylab.figure()
        #pylab.contourf(deof_x[:,:,0],numpy.linspace(-0.5,0.5,20))
        #pylab.colorbar()
        #pylab.show()

        return


    def go(self):
        var = self.metadata['ceof']['var']

        if ('Lat' not in self.keys()) or ('Lon' not in self.keys()):
            self.data['Lon'], self.data['Lat'] = numpy.meshgrid(self.data['lon'],self.data['lat'])
        if 'prefilter' in self.metadata:
            print "Filtering in time"
            if self.metadata['prefilter']['type'] == 'bandpass':
                self.filter(var,l=self.metadata['prefilter']['l'],type=self.metadata['prefilter']['type'], l2=self.metadata['prefilter']['l2'],)
            else:
                self.filter(var,l=self.metadata['prefilter']['l'],type=self.metadata['prefilter']['type'])
        # ---- Normalize -----------------------------------------------------
        #self.data['ssh']=self.data['ssh']-self.data['ssh'].mean()
        # --------------------------------------------------------------------
        # Damn ugly way to resolve it, but will work for now.
        import re
        I, J, K = self.data[var].shape
        ind = numpy.ones((J,K)) == 1
        #tmp=numpy.ones((J,K))==1
        for j in range(J):
            for k in range(K):
                ind[j, k] = ((self.data[var].mask)[:, j, k]).all() == False
    
        if 'ceof_coord' in self.metadata:
            coord = self.metadata['ceof_coord']
            assert type(coord) == list
            from shapely.geometry import Point, Polygon
            polygon = Polygon(coord)
            for j in range(J):
                for k in range(K):
                        ind[j,k] = ind[j,k] & polygon.intersects(
                                Point(self.data['Lon'][j,k],
                                    self.data['Lat'][j,k]))
  
        #ind = ind&tmp
    
        N = ((numpy.ones(ind.shape)[ind]).sum())
        grid_index = ma.masked_all((N,2), dtype='i')
        n = -1
        for j in range(J):
            for k in range(K):
                if ind[j, k]:
                    n += 1
                    grid_index[n, :] = [j, k]
        #else:
        #    #N = ((numpy.ones(ind.shape)[ind]).sum())
	#    N = J*K
        #    grid_index = ma.masked_all((N,2),dtype='i')
        #    n=-1
        #    for j in range(J):
        #        for k in range(K):
        #            n+=1
        #            grid_index[n,:] = [j,k]
    
        self.grid_index = grid_index
        data2D = numpy.zeros((I,N), dtype=self.data[var].dtype)
        for n, ind in enumerate(self.grid_index):
            data2D[:, n] = self.data[var][:,ind[0], ind[1]]

        print "Running CEOF_2D()"
        #metadata = {'cumvar':1,'normalize':'pc_std'}
        #ceof = CEOF_2D(self.data2D['ssh'],metadata=metadata)
        ceof = CEOF_2D(data2D, cfg=self.metadata['ceof'])

        #for k in ceof.keys():
        #    print k, ceof[k].shape, type(ceof[k])

        nmodes=len(ceof['lambdas'])

        #print dir(ceof['eofs'])
        #print ceof['eofs'].dtype

        self.data['variancefraction'] = ceof['variancefraction']
        self.data['lambdas'] = ceof['lambdas']
        self.data['pcs'] = ceof['pcs']
        #self.data['eofs'] = ma.masked_all((J,K,nmodes),dtype=ceof['eofs'].dtype)
        self.data['eofs'] = ma.masked_all((J,K,nmodes),dtype='complex128')
        for n,ind in enumerate(self.grid_index):
            self.data['eofs'][ind[0],ind[1],:] = ceof['eofs'][n,:]

	# ----
	self.set_wavelenght()

        #for k in self.data.keys():
        #    print k, self.data[k].shape, type(self.data[k])

        if 'figs' in self.metadata:
	    print "Creating figures for %s modes" % nmodes
            #for nmode in range(5):
            #for n in range(10):
            for n in range(nmodes):
                #eof2D=ceof['eofs'][:,nmode]
                #pc2D=ceof['pcs'][:,nmode]
                ##
                ##eof=ma.masked_all(self.data['ssh'].shape[1:],dtype=eofs.dtype)
                #eof=ma.masked_all(self.data['ssh'].shape[1:],dtype='complex128')
                ##pc=ma.masked_all(self.data['ssh'].shape[1:],dtype=pcs.dtype)
                #pc=ma.masked_all(self.data['ssh'].shape[1:],dtype='complex128')
                ##
                ##for n,i in enumerate(ind):
                ##
                ## ---- 2D back to grid ----
                #for n,ind in enumerate(self.data2D['grid_index']):
                #    #print n,ind
                #    eof[ind[0],ind[1]] = eof2D[n]
                #    #pc[ind[0],ind[1]] = pc2D[n]
                #pc = pc2D
                #print pc2D.shape
                #varfrac = round(getvariancefraction(lambdas)[nmode]*1e2)
                #varfrac = ceof['variancefraction'][nmode]
                #fig = self.plot(eof_amp,eof_phase,pc_amp,pc_phase,nmode,varfrac)
                if 'suffix' in self.metadata['figs']:
                    filename="../figs/CEOF_%s_mode%s.eps" % (self.metadata['figs']['suffix'],(n+1))
                else:
                    filename="../figs/CEOF_mode%s.eps" % (n+1)
                limits={'LatIni':-5, 'LatFin':15, 'LonIni':-60, 'LonFin':-25}
                self.plot(self['eofs'][:,:,n],self['pcs'][:,n],(n+1),self['variancefraction'][n],filename=filename,limits=limits,cumvarfrac=self['variancefraction'][:(n+1)].sum())
                #fig.show()

                #import pylab
                #pylab.savefig("../fig/CEOF_mode%s.eps" % nmode)
                ##print "dir(fig)",dir(fig)
                ##fig.close()
                #pylab.close()



        # --------------------------------------------------------------------
        #y=x['eofs'][:,:,0]
        #
        #eofs = x['eofs'][:,:,3]
        #
        #
        #eofs_amp = numpy.absolute(eofs)
        #eofs_phase=numpy.arctan2(eofs.imag,eofs.real)
        ##pcs_phase=numpy.arctan2(pcs.imag,pcs.real)
        #
        #dx_eofs_phase=ma.masked_all(eofs_phase.shape)
        #dy_eofs_phase=ma.masked_all(eofs_phase.shape)
        #
        ##dx_eofs_phase[:,0,:]=eofs_phase[:,1,:]-eofs_phase[:,0,:]
        ##dx_eofs_phase[:,:,1:-1]=eofs_phase[:,:,2:]-eofs_phase[:,:,:-2]
        ##dx_eofs_phase[:,-1,:]=eofs_phase[:,-1,:]-eofs_phase[:,-2,:]
        ##ind=(dx_eofs_phase>3)|(dx_eofs_phase<-3)
        ##dx_eofs_phase.mask[ind]=True
        #
        #
        #dx_eofs_phase[:,1:-1] = (eofs_phase[:,2:]-eofs_phase[:,:-2])/2.
        #ind = ((numpy.sign(eofs_phase[:,2:])*numpy.sign(eofs_phase[:,:-2]))<0) & (numpy.absolute(dx_eofs_phase[:,1:-1])>2)
        #dx_eofs_phase.mask[ind] = True
        #
        #dy_eofs_phase[1:-1,:] = (eofs_phase[2:,:]-eofs_phase[:-2,:])/2.
        #ind = ((numpy.sign(eofs_phase[2:,:])*numpy.sign(eofs_phase[:-2,:]))<0) & (numpy.absolute(dy_eofs_phase[1:-1,:])>2)
        #dy_eofs_phase.mask[ind] = True
        # --------------------------------------------------------------------
        #eofs_phase=numpy.arctan2(eofs.imag,eofs.real)
        #pcs_phase=numpy.arctan2(pcs.imag,pcs.real)

        #dx_eofs_phase=ma.masked_all(eofs_phase.shape)

        #dx_eofs_phase[:,0,:]=eofs_phase[:,1,:]-eofs_phase[:,0,:]
        #dx_eofs_phase[:,1:-1,:]=eofs_phase[:,2:,:]-eofs_phase[:,:-2,:]
        #dx_eofs_phase[:,-1,:]=eofs_phase[:,-1,:]-eofs_phase[:,-2,:]
        #ind=(dx_eofs_phase>3)|(dx_eofs_phase<-3)
        #dx_eofs_phase.mask[ind]=True



        #dphase=ma.masked_all(pcs_phase.shape)


        #dphase[0,:]=(pcs_phase[1,:]-pcs_phase[0,:])
        #dphase[1:-1,:]=(pcs_phase[2:,:]-pcs_phase[:-2,:])
        #dphase[-1,:]=(pcs_phase[-1,:]-pcs_phase[-2,:])

        #ind = (numpy.absolute(dphase[1:-1,:])>2) & (pcs_phase[:-2,:]<0) & (pcs_phase[2:,:]>0)
        #dphase[1:-1,:][ind]=(pcs_phase[2:,:][ind]-(2*numpy.pi+pcs_phase[:-2,:][ind]))
        ##ind = (numpy.absolute(dphase[1:-1,:])>2) & (pcs_phase[:-2,:]>0) & (pcs_phase[2:,:]<0)
        ##dphase[1:-1,:][ind]=(2*numpy.pi+pcs_phase[2:,:][ind])-pcs_phase[:-2,:][ind]

        #ind = (numpy.absolute(dphase[1:-1,:])>3) & (pcs_phase[:-2,:]<0) & (pcs_phase[2:,:]<0)
        #ind = (numpy.absolute(dphase[1:-1,:])>3) & (pcs_phase[:-2,:]>0) & (pcs_phase[2:,:]<0)
        # --------------------------------------------------------------------


    def plot(self,eof,pc,nmode,varfrac,filename,limits=None,cumvarfrac=None):
        """ Plot one mode of the CEOF
        """
        import pylab
        import matplotlib
        from mpl_toolkits.basemap import Basemap

        if limits == None:
            LatIni = self['Lat'].min()
            LatFin = self['Lat'].max()
            LonIni = self['Lon'].min()
            LonFin = self['Lon'].max()
        else:
            LatIni = limits['LatIni']
            LatFin = limits['LatFin']
            LonIni = limits['LonIni']
            LonFin = limits['LonFin']

        # ----
        cdict = {'red': ((0.0, 0.0, 0.0),
                 (0.5, 0.879, 0.879),
                 (1.0, 0.0, 0.0)),
         'green': ((0.0, 0.281, 0.281),
                   (0.5, 0.418, 0.418),
                   (1.0, 0.281, 0.281)),
         'blue': ((0.0, 0.195, 0.195),
                  (0.5, 0.184, 0.184),
                  (1.0, 0.281, 0.281))}
        um_sym_cmap = matplotlib.colors.LinearSegmentedColormap('um_sym_colormap',cdict,256)

        cdict = {'red': ((0.0, 0.879, 0.879),
                 (1.0, 0.0, 0.0)),
         'green': ((0.0, 0.418, 0.418),
                   (1.0, 0.281, 1.0)),
         'blue': ((0.0, 0.184, 0.184),
                  (1.0, 0.281, 0.281))}
        um_cmap = matplotlib.colors.LinearSegmentedColormap('um_colormap',cdict,256)

        #cdict = {'red': ((0.0, 0.879, 0.879),
        #         (0.5, 0.0, 0.0),
        #         (1.0, 0.879, 0.879)),
        # 'green': ((0.0, 0.418, 0.418),
        #           (0.5, 0.281, 0.281),
        #           (1.0, 0.418, 0.418)),
        # 'blue': ((0.0, 0.184, 0.184),
        #          (0.5, 0.195, 0.195),
        #          (1.0, 0.184, 0.184))}
        #um_cmap = matplotlib.colors.LinearSegmentedColormap('um_colormap',cdict,256)

        cdict = {'red': ((0.0, 0.0, 0.0),
                 (0.5, 1.0, 1.0),
                 (1.0, 0.0, 0.0)),
         'green': ((0.0, 0.0, 0.0),
                   (0.5, 1.0, 1.0),
                   (1.0, 0.0, 0.0)),
         'blue': ((0.0, 0.0, 0.0),
                  (0.5, 1.0, 1.0),
                  (1.0, 0.0, 0.0))}
        bw_cmap = matplotlib.colors.LinearSegmentedColormap('bw_colormap',cdict,256)

        cdict = {'red': ((0.0, 0.45, 0.45),
                 (0.5, 0.95, 0.95),
                 (1.0, 0.45, 0.45)),
         'green': ((0.0, 0.45, 0.45),
                   (0.5, 0.95, 0.95),
                   (1.0, 0.45, 0.45)),
         'blue': ((0.0, 0.45, 0.45),
                  (0.5, .95, 0.95),
                  (1.0, 0.45, 0.45))}
        grey_cmap = matplotlib.colors.LinearSegmentedColormap('grey_colormap',cdict,256)


        # ----

        parallels = numpy.arange(-5,20.1,5)
        meridians = numpy.arange(300,340,10)

        margin=0.08
        left=margin
        bottom=margin
        height_eof = (1-4*margin)*.44
        width_eof =  (1-3*margin)*.5

        height_pc = (1-4*margin)*.28
        width_pc = (1-2*margin)*1
        # ----
        eof_amp=(eof.real**2+eof.imag**2)**0.5
        eof_phase=numpy.arctan2(eof.imag,eof.real)
        pc_amp = (numpy.real(pc)**2+numpy.imag(pc)**2)**0.5
        pc_phase = numpy.arctan2(numpy.imag(pc),numpy.real(pc))

        fig = pylab.figure(figsize=(14,10.5), dpi=300)
	cumvarfrac = None
	if cumvarfrac != None:
            title = "Mode: %i (%i%%) (cumulative %i%%)" % (nmode,varfrac*1e2,cumvarfrac*1e2)
	else:
            title = "Mode: %i (%i%%)" % (nmode,varfrac*1e2)

        #if 'halfpower_period' in self:
	if 'prefilter' in self.metadata:
            if type(self.halfpower_period) == str:
                halfpower_period = self.halfpower_period
            else:
                halfpower_period = round(self.halfpower_period)
	    title = "%s (%s half power:%s days)" % (title,self.metadata['prefilter']['type'], halfpower_period)
        fig.text(.5, .95, title, horizontalalignment='center',fontsize=16)
        #
        pylab.axes([left, bottom + 2*height_pc + 2*margin, width_eof, height_eof])
        map = Basemap(projection='merc',lat_ts=0,llcrnrlon=LonIni,llcrnrlat=LatIni, urcrnrlon=LonFin, urcrnrlat=LatFin,resolution='l',area_thresh=1000.)
        X, Y = map(*pylab.meshgrid(self.data['lon'],self.data['lat']))
        map.contourf(X,Y,eof_amp*1e2)
        pylab.title("CEOF amplitude")
        cbar = pylab.colorbar()
        cbar.set_label('[cm]')
        map.drawcoastlines()
        map.fillcontinents(color='0.0')
        map.drawparallels(parallels,labels=[1,0,0,1])
        map.drawmeridians(meridians,labels=[1,0,0,1])

        pylab.axes([left+width_eof+margin, bottom + 2*height_pc + 2*margin, width_eof, height_eof])
        map = Basemap(projection='merc',lat_ts=0,llcrnrlon=LonIni,llcrnrlat=LatIni, urcrnrlon=LonFin, urcrnrlat=LatFin,resolution='l',area_thresh=1000.)
        X, Y = map(*pylab.meshgrid(self.data['lon'],self.data['lat']))
        V=[-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]
        #V = range(-180,181,20)
        #import matplotlib.cm as cm
        #map.pcolor(X[0,:],Y[:,0],eof_phase*180/numpy.pi,cmap=um_sym_cmap)
        #map.contourf(X,Y,eof_phase*180/numpy.pi,V,cmap=um_sym_cmap)
        #from scipy.stats import scoreatpercentile
        #scoreatpercentile(x.flatten(),15)

        from numpy import ma
        #ind_sig = eof_amp<0.01
	#eof_phase_deg = eof_phase*180/numpy.pi
        map.contourf(X, Y, eof_phase*180/numpy.pi, V, cmap=grey_cmap)
        map.contourf(X,Y,ma.masked_array(eof_phase*180/numpy.pi, mask=eof_amp<0.01),V,cmap=um_sym_cmap)

        cbar = pylab.colorbar()
        cbar.set_label('[degrees]')
        pylab.title("CEOF phase")
        map.drawcoastlines()
        map.fillcontinents(color='0.0')
        map.drawparallels(parallels,labels=[1,0,0,1])
        map.drawmeridians(meridians,labels=[1,0,0,1])
        # ----
        #pylab.subplot(2,2,2)
        pylab.axes([left, bottom+margin+height_pc, width_pc, height_pc])
        pylab.plot_date(pylab.date2num(self.data['datetime']),pc_amp,'-')
        fig.autofmt_xdate()
        pylab.title("PC amplitude")
        pylab.ylabel('[dimensionless]')
        pylab.grid()
        # ----
        #pylab.subplot(2,2,4)
        pylab.axes([left, bottom, width_pc, height_pc])
        pylab.plot_date(pylab.date2num(self.data['datetime']),pc_phase*180/numpy.pi,'.')
        fig.autofmt_xdate()
	v = pylab.axis()
	pylab.axis((v[0],v[1],-181,181))
        pylab.title("PC phase")
        pylab.ylabel('[degrees]')
        pylab.grid()
        # ----
        #pylab.subplot(2,2,4)
        #pylab.axes([left + margin + width_l, bottom, width_r, height_r])
        #pylab.plot(numpy.absolute(scipy.fftpack.fft(pc_amp))[1:pc_amp.shape[0]/2])
        #pylab.title("PC FFT")
        #pylab.grid()
        # ----
        #pylab.show()
        print "Saving figure %s" % filename
        #fig.savefig(filename)
        pylab.savefig(filename)
        pylab.close()
        return
