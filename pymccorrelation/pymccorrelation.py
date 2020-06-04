"""
pymccorrelation.py

Python implementation of Curran (2014) method for calculating Spearman's
rank correlation coefficient with uncertainties. Extended to also calculate
Kendall's Tau.

Kendall tau implementation follow Isobe, Feigelson & Nelson (1986) method for
calculating the correlation coefficient with uncertainties on censored data
(upper/lowerlimit).

Copyright 2019-2020 George C. Privon, Yiqing Song

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import numpy as _np
import scipy.stats as st
from scipy.stats import spearmanr as _spearmanr


def perturb_values(x, y, dx, dy, Nperturb=10000):
    """
    For input points (x, y) with errors (dx, dy) return Nperturb sets of
    values draw from Gaussian distributions centered at x+-dx and y+-dy.
    """

    assert len(x) == len(y)
    assert len(dx) == len(dy)
    assert len(x) == len(dx)

    Nvalues = len(x)

    xp = _np.random.normal(loc=x,
                           scale=dx,
                           size=(Nperturb, Nvalues))
    yp = _np.random.normal(loc=y,
                           scale=dy,
                           size=(Nperturb, Nvalues))

    if Nperturb == 1:
        xp = xp.flatten()
        yp = yp.flatten()

    return xp, yp


#generalized kendall tau test described in Isobe,Feigelson & Nelson 1986
#need to come up some way to vectorize this function, very slow
def kendall(x,y,xlim,ylim):
    #x, y are two arrays, either may contain censored data
    #xlim, ylim are arrays indicating if x or y are lower or upperlimits,-1--lowerlimit,+1--upperlimit,0--detection
    num=len(x)#x,y should have same length
    #set up pair counters
    a=np.zeros((num,num))
    b=np.zeros((num,num))
    
    for i in range(num):
        for j in range(num):
            if x[i]==x[j]:
                a[i,j]=0
            elif x[i] > x[j]: #if x[i] is definitely > x[j]
                if (xlim[i]==0 or xlim[i]==-1) and (xlim[j]==0 or xlim[j]==1):
                    a[i,j]=-1
            else: #if x[i] is definitely < x[j], all other uncertain cases have aij=0
                if (xlim[i]==0 or xlim[i]==1) and (xlim[j]==0 or xlim[j]==-1):
                    a[i,j]=1
            
    for i in range(num):
        for j in range(num):
            if y[i]==y[j]:
                b[i,j]=0
            elif y[i] > y[j]:
                if (ylim[i]==0 or ylim[i]==-1) and (ylim[j]==0 or ylim[j]==1):
                    b[i,j]=-1
            else:
                 if (ylim[i]==0 or ylim[i]==0) and (ylim[j]==0 or ylim[j]==-1):
                    b[i,j]=1
                    
            
    S = np.sum(a*b)
    var = (4/(num*(num-1)*(num-2)))*(np.sum(a*np.sum(a,axis=1,keepdims=True))-np.sum(a*a))\
    *(np.sum(b*np.sum(b,axis=1,keepdims=True))-np.sum(b*b))+(2/(num*(num-1)))*np.sum(a*a)*np.sum(b*b)
    z=S/np.sqrt(var)
    tau=z*np.sqrt(2*(2*num+5))/(3*np.sqrt(num*(num-1)))
    pval=st.norm.sf(abs(z))*2
    return tau,pval


def pymcspearman(x, y, dx=None, dy=None,
                 Nboot=None,
                 Nperturb=None,
                 percentiles=(16, 50, 84), return_dist=False):
    """
    Compute spearman rank coefficient with uncertainties using several methods.
    Arguments:
    x: independent variable array
    y: dependent variable array
    dx: uncertainties on independent variable (assumed to be normal)
    dy: uncertainties on dependent variable (assumed to be normal)
    Nboot: number of times to bootstrap (does not boostrap if =None)
    Nperturb: number of times to perturb (does not perturb if =None)
    percentiles: list of percentiles to compute from final distribution
    return_dist: if True, return the full distribution of rho and p-value
    """

    if Nperturb is not None and dx is None and dy is None:
        raise ValueError("dx or dy must be provided if perturbation is to be used.")
    if len(x) != len(y):
        raise ValueError("x and y must be the same length.")
    if dx is not None and len(dx) != len(x):
        raise ValueError("dx and x must be the same length.")
    if dy is not None and len(dy) != len(y):
        raise ValueError("dx and x must be the same length.")

    rho = []
    rho = []
    pval = []

    Nvalues = len(x)

    if Nboot is not None:
        # generate all the needed bootstrapping indices
        members = _np.random.randint(0, high=Nvalues-1,
                                     size=(Nboot, Nvalues))
        # loop over sets of bootstrapping indices and compute
        # correlation coefficient
        for i in range(Nboot):
            xp = x[members[i, :]]
            yp = y[members[i, :]]
            if Nperturb is not None:
                # return only 1 perturbation on top of the bootstrapping
                xp, yp = perturb_values(x[members[i, :]], y[members[i, :]],
                                        dx[members[i, :]], dy[members[i, :]],
                                        Nperturb=1)

            trho, tpval = _spearmanr(xp, yp)

            rho.append(trho)
            pval.append(tpval)
    elif Nperturb is not None:
        # generate Nperturb perturbed copies of the dataset
        xp, yp = perturb_values(x, y, dx, dy, Nperturb=Nperturb)
        # loop over each perturbed copy and compute the correlation
        # coefficient
        for i in range(Nperturb):
            trho, tpval = _spearmanr(xp[i, :], yp[i, :])

            rho.append(trho)
            pval.append(tpval)
    else:
        import warnings as _warnings
        _warnings.warn("No bootstrapping or perturbation applied. Returning \
normal spearman rank values.")
        return _spearmanr(x, y)

    frho = _np.percentile(rho, percentiles)
    fpval = _np.percentile(pval, percentiles)

    if return_dist:
        return frho, fpval, rho, pval
    return frho, fpval


def pymckendall(x, y, xlim, ylim, dx=None, dy=None,
                Nboot=None,
                Nperturb=None,
                percentiles=(16,50,84), return_dist=False):
    """
    Compute Kendall tau coefficient with uncertainties using several methods.
    Arguments:
    x: independent variable array
    y: dependent variable array
    xlim: array indicating if x is upperlimit (1), lowerlimit(-1), or detection(0)
    ylim: array indicating if x is upperlimit (1), lowerlimit(-1), or detection(0)
    dx: uncertainties on independent variable (assumed to be normal)
    dy: uncertainties on dependent variable (assumed to be normal)
    Nboot: number of times to bootstrap (does not boostrap if =None)
    Nperturb: number of times to perturb (does not perturb if =None)
    percentiles: list of percentiles to compute from final distribution
    return_dist: if True, return the full distribution of rho and p-value
    """

    if Nperturb is not None and dx is None and dy is None:
        raise ValueError("dx or dy must be provided if perturbation is to be used.")
    if len(x) != len(y):
        raise ValueError("x and y must be the same length.")
    if dx is not None and len(dx) != len(x):
        raise ValueError("dx and x must be the same length.")
    if dy is not None and len(dy) != len(y):
        raise ValueError("dx and x must be the same length.")

    rho = []
    pval = []

    Nvalues = len(x)

    if Nboot is not None:
        tau = np.zeros(Nboot)
        pval = np.zeros(Nboot)
        members = np.random.randint(0, high=Nvalues-1, size=(Nboot,Nvalues)) #randomly resample
        xp = x[members]
        yp = y[members]
        xplim = xlim[members] #get lim indicators for resampled x, y
        yplim = ylim[members]
        if Nperturb is not None:
            xp[xplim==0] += np.random.normal(size=np.shape(xp[xplim==0])) * dx[members][xplim==0] #only perturb the detections
            yp[yplim==0] += np.random.normal(size=np.shape(yp[yplim==0])) * dy[members][yplim==0] #only perturb the detections
        
        #calculate tau and pval for each iteration
        for i in range(Nboot):
            tau[i],pval[i] = kendall(xp[i,:], yp[i,:], xplim[i,:], yplim[i,:])
       
    elif Nperturb is not None:
        tau = np.zeros(Nperturb)
        pval = np.zeros(Nperturb)
        yp=[y]*Nperturb+np.random.normal(size=(Nperturb,Nvalues))*dy #perturb all data first
        xp=[x]*Nperturb+np.random.normal(size=(Nperturb,Nvalues))*dx
        yp[:,ylim!=0]=y[ylim!=0] #set upperlimits and lowerlimits to be unperturbed
        xp[:,xlim!=0]=x[xlim!=0] #so only real detections are perturbed
            
        for i in range(Nperturb):
            tau[i], pval[i] = kendall(xp[i,:], yp[i,:], xlim, ylim) #need to vectorize!

    else:
        import warnings as _warnings
        _warnings.warn("No bootstrapping or perturbation applied. Returning \
    normal generalized kendall tau.")
        tau,pval=kendall(x, y, xlim, ylim)
        return tau,pval

    ftau = np.nanpercentile(tau, percentiles)
    fpval = np.nanpercentile(pval, percentiles)

    if return_dist:
        return ftau, fpval, tau, pval
    return ftau, fpval


def run_tests():
    """
    Test output of pymcspearman against tabulated values from MCSpearman
    """

    from tempfile import NamedTemporaryFile as ntf
    from urllib.request import urlretrieve

    # get test data
    tfile = ntf()
    urlretrieve("https://raw.githubusercontent.com/PACurran/MCSpearman/master/test.data",
                tfile.name)
    # open temporary file
    data = _np.genfromtxt(tfile,
                         usecols=(0, 1, 2, 3),
                         dtype=[('x', float),
                                ('dx', float),
                                ('y', float),
                                ('dy', float)])

    # tabulated results from a MCSpearman run with 10000 iterations
    MCSres = [(0.8308, 0.001),  # spearman only
              (0.8213, 0.0470), # bootstrap only
              (0.7764, 0.0356), # perturbation only
              (0.7654, 0.0584)] # bootstrapping and perturbation

    # spearman only
    res = pymcspearman(data['x'], data['y'], dx=data['dx'], dy=data['dy'],
                       Nboot=None,
                       Nperturb=None,
                       return_dist=True)
    try:
        assert _np.isclose(MCSres[0][0], res[0],
                           atol=MCSres[0][1])
        _sys.stdout.write("Passed spearman check.\n")
    except AssertionError:
        _sys.stderr.write("Spearman comparison failed.\n")

    # bootstrap only
    res = pymcspearman(data['x'], data['y'], dx=data['dx'], dy=data['dy'],
                       Nboot=10000,
                       Nperturb=None,
                       return_dist=True)
    try:
        assert _np.isclose(MCSres[1][0], _np.mean(res[2]),
                           atol=MCSres[1][1])
        _sys.stdout.write("Passed bootstrap only method check.\n")
    except AssertionError:
        _sys.stderr.write("Bootstrap only method comparison failed.\n")

    # perturbation only
    res = pymcspearman(data['x'], data['y'], dx=data['dx'], dy=data['dy'],
                       Nboot=None,
                       Nperturb=10000,
                       return_dist=True)
    try:
        assert _np.isclose(MCSres[2][0], _np.mean(res[2]),
                           atol=MCSres[2][1])
        _sys.stdout.write("Passed perturbation only method check.\n")
    except AssertionError:
        _sys.stderr.write("Perturbation only method comparison failed.\n")

    # composite method
    res = pymcspearman(data['x'], data['y'], dx=data['dx'], dy=data['dy'],
                       Nboot=10000,
                       Nperturb=10000,
                       return_dist=True)
    try:
        assert _np.isclose(MCSres[3][0], _np.mean(res[2]),
                           atol=MCSres[3][1])
        _sys.stdout.write("Passed composite method check.\n")
    except AssertionError:
        _sys.stderr.write("Composite method comparison failed.\n")


def main():
    """
    run tests
    """

    run_tests()


if __name__ == "__main__":
    import sys as _sys
    _sys.stdout.write("\nModule run as a program. Running test suite.\n\n")
    main()
