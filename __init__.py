import os
import numpy as np
from montepython.likelihood_class import Likelihood_prior
from scipy import interpolate
from scipy.interpolate import interp1d
from scipy.integrate import quad
import scipy.integrate as integrate
from numpy import log, exp, sin, cos
from scipy.special.orthogonal import p_roots

class ngcz1_pqb(Likelihood_prior):

    # initialisation of the class is done within the parent Likelihood_prior. For
    # this case, it does not differ, actually, from the __init__ method in
    # Likelihood class.

    def __init__(self,path,data,command_line):
        Likelihood_prior.__init__(self,path,data,command_line)

        self.n_gauss = 3
        [self.gauss_mu,self.gauss_w]=p_roots(self.n_gauss)

        self.n_gauss2 = 8
        [self.gauss_mu2,self.gauss_w2]=p_roots(self.n_gauss2)


        self.mesh_mu = np.meshgrid(self.gauss_mu,self.gauss_mu,self.gauss_mu,self.gauss_mu2,self.gauss_mu2, sparse=True, indexing='ij')

        triag = [ [0 for x in range(self.ksize*self.ksize*self.ksize)] for y in range(3)]
        ntriag = self.ntriag

        self.weights = np.zeros(ntriag,'float64')
        datafile = open(os.path.join(self.data_directory, self.weights_file), 'r')
        for i in range(ntriag):
            line = datafile.readline()
            self.weights[i] = float(line.split()[0])
        datafile.close()
	self.Bk = np.zeros(ntriag,'float64')

        khere = np.zeros(ntriag,'float64')
        khere2 = np.zeros(ntriag,'float64')
        khere3 = np.zeros(ntriag,'float64')
        datafile = open(os.path.join(self.data_directory, self.measurements_b_file), 'r')
        for i in range(ntriag):
            line = datafile.readline()
            khere[i] = float(line.split()[0])
            khere2[i] = float(line.split()[1])
            khere3[i] = float(line.split()[2])
            self.Bk[i] = float(line.split()[3])
        datafile.close()
        self.kf = 0.00163625

        self.k = np.zeros(self.ksize, 'float64')
        self.k = np.linspace(self.kmin,self.kmax,self.ksize)

### this is just taken from the file
        self.new_triag = [ [0 for x in range(ntriag)] for y in range(3)]
        self.dk = 0.01
        for j in range(ntriag):
                self.new_triag[0][j] = int(khere[j]/self.dk) - int(self.kmin/self.dk)
                self.new_triag[1][j] = int(khere2[j]/self.dk) - int(self.kmin/self.dk)
                self.new_triag[2][j] = int(khere3[j]/self.dk) - int(self.kmin/self.dk)

        self.ksize2 = 0
        self.omit = 0
        self.ksizemu0 = 0

        dx=np.loadtxt(os.path.join(self.data_directory, self.measurements_p_file), skiprows = 0)
        self.k1 = dx[:,0]
        self.Pk01 = dx[:,1]
        self.Pk21 = dx[:,2]
        self.Pk41 = dx[:,3]
	self.ksize1 = len(self.k1)
        del dx
        for i in range(self.ksize1):
                if (self.k1[i] < self.kmax2 and self.k1[i] >= self.kmin2):
                        self.ksize2 = self.ksize2 + 1
                if self.k1[i] < self.kmin2:
                        self.omit = self.omit + 1
                if (self.k1[i] < self.kmax2 and self.k1[i] >= self.kmaxpl):
                        self.ksizemu0 = self.ksizemu0 + 1
	#print('self.ksize2=',self.ksize2)
        #print('self.ksize1=',self.ksize1)

        self.ksizep0p2 = self.ksize2 - self.ksizemu0
        self.omit2 = self.ksizep0p2 + self.omit


        self.k2 = np.zeros(self.ksize2,'float64')
        self.kp0p2 = np.zeros(self.ksizep0p2,'float64')
        self.kmu0 = np.zeros(self.ksizemu0,'float64')

        self.Pk0 = np.zeros(self.ksize2,'float64')
        self.Pk2 = np.zeros(self.ksize2,'float64')
        self.Pk4 = np.zeros(self.ksize2,'float64')

        self.Pk0p0p2 = np.zeros(self.ksizep0p2,'float64')
        self.Pk2p0p2 = np.zeros(self.ksizep0p2,'float64')
        self.Pk4p0p2 = np.zeros(self.ksizep0p2,'float64')
        self.Q0 = np.zeros(self.ksizemu0,'float64')

        self.alphas = np.zeros(2,'float64')
        datafile = open(os.path.join(self.data_directory, self.alpha_means), 'r')
        for i in range(2):
            line = datafile.readline()
            while line.find('#') != -1:
                line = datafile.readline()
            self.alphas[i] = float(line.split()[0])
        datafile.close()

        for i in range(self.ksize2):
                self.k2[i] = self.k1[i + self.omit]
                self.Pk0[i] = self.Pk01[i + self.omit]
                self.Pk2[i] = self.Pk21[i + self.omit]
                self.Pk4[i] = self.Pk41[i + self.omit]
        for i in range(self.ksizep0p2):
                self.kp0p2[i] = self.k2[i]
                self.Pk4p0p2[i] = self.Pk4[i]
                self.Pk2p0p2[i] = self.Pk2[i]
                self.Pk0p0p2[i] = self.Pk0[i]
        for i in range(self.ksizemu0):
                self.kmu0[i] = self.k2[i+self.ksizep0p2]
                self.Q0[i] = self.Pk0[i+self.ksizep0p2]-self.Pk2[i+self.ksizep0p2]/2.+3.*self.Pk4[i+self.ksizep0p2]/8.

	

#        self.invcov = np.loadtxt(os.path.join(self.data_directory, self.covmat_file))
#        self.invcov = np.zeros(
#            (3*3*self.ksize2+self.ntriag, 3*self.ksizep0p2 +self.ksizemu0+self.ntriag), 'float64')
        self.cov1 = np.zeros((4*self.ksize1+self.ntriag+2, 4*self.ksize1 +self.ntriag+2), 'float64')
        self.cov = np.zeros((3*self.ksizep0p2+self.ksizemu0+self.ntriag+2, 2+3*self.ksizep0p2+self.ksizemu0 +self.ntriag), 'float64')

        datafile = open(os.path.join(self.data_directory, self.covmat_file), 'r')
        for i in range(4*self.ksize1+self.ntriag+2):
            line = datafile.readline()
            while line.find('#') != -1:
                line = datafile.readline()
            for j in range(4*self.ksize1+self.ntriag+2):
                self.cov1[i,j] = float(line.split()[j])

        for i in range(self.ksizep0p2):
                for j in range(self.ksizep0p2):
                        self.cov[i][j] = self.cov1[self.omit + i, self.omit + j]
                        self.cov[i][j+self.ksizep0p2] = self.cov1[self.omit + i,self.omit + j + self.ksize1]
                        self.cov[i + self.ksizep0p2][j] = self.cov1[self.omit + i + self.ksize1,self.omit + j]
                        self.cov[i + self.ksizep0p2][j + self.ksizep0p2] = self.cov1[self.omit + i + self.ksize1, self.omit + j + self.ksize1]
                        self.cov[i + 2*self.ksizep0p2][j] = self.cov1[self.omit + i + 2*self.ksize1,self.omit + j]
                        self.cov[i][j + 2*self.ksizep0p2] = self.cov1[self.omit + i,self.omit + j+ 2*self.ksize1]
                        self.cov[i + 2*self.ksizep0p2][j + 2*self.ksizep0p2] = self.cov1[self.omit + i + 2*self.ksize1, self.omit + j + 2*self.ksize1]
                        self.cov[i + 2*self.ksizep0p2][j+self.ksizep0p2] = self.cov1[self.omit + i + 2*self.ksize1,self.omit + j +self.ksize1]
                        self.cov[i+self.ksizep0p2][j + 2*self.ksizep0p2] = self.cov1[self.omit + i + self.ksize1,self.omit + j + 2*self.ksize1]

        for i in range(self.ksizemu0):
                for j in range(self.ksizemu0):
                        self.cov[i + 3*self.ksizep0p2][j + 3*self.ksizep0p2] = self.cov1[self.omit2+i + 3*self.ksize1, self.omit2+j + 3*self.ksize1]

        for i in range(self.ksizep0p2):
                for j in range(self.ksizemu0):
                        self.cov[i][j + 3*self.ksizep0p2] = self.cov1[self.omit+i, self.omit2+j + 3*self.ksize1]
                        self.cov[i + 2*self.ksizep0p2][j + 3*self.ksizep0p2] = self.cov1[self.omit+i+2*self.ksize1, self.omit2+j + 3*self.ksize1]
                        self.cov[i + self.ksizep0p2][j + 3*self.ksizep0p2] = self.cov1[self.omit+i+self.ksize1, self.omit2+j + 3*self.ksize1]
                        self.cov[j + 3*self.ksizep0p2][i] = self.cov1[self.omit2+j + 3*self.ksize1,self.omit+i]
                        self.cov[j + 3*self.ksizep0p2][i + self.ksizep0p2] = self.cov1[self.omit2+j + 3*self.ksize1,self.omit+i+self.ksize1]
                        self.cov[j + 3*self.ksizep0p2][i + 2*self.ksizep0p2] = self.cov1[self.omit2+j + 3*self.ksize1,self.omit+i+2*self.ksize1]

        for i in range(self.ntriag):
                for j in range(self.ntriag):
                        self.cov[3*self.ksizep0p2+self.ksizemu0+i][3*self.ksizep0p2+self.ksizemu0+j] = self.cov1[4*self.ksize1 + i, 4*self.ksize1 + j]

	for i in range(self.ksizep0p2):
		self.cov[i][-1] = self.cov1[self.omit + i, -1]
		self.cov[-1][i] = self.cov1[-1, self.omit + i]
		self.cov[i][-2] = self.cov1[self.omit + i, -2]
		self.cov[-2][i] = self.cov1[-2, self.omit + i]
                self.cov[i+self.ksizep0p2][-1] = self.cov1[self.omit+self.ksize1 + i, -1]
                self.cov[-1][i+self.ksizep0p2] = self.cov1[-1, self.omit+self.ksize1 + i]
                self.cov[i+self.ksizep0p2][-2] = self.cov1[self.omit+self.ksize1 + i, -2]
                self.cov[-2][i+self.ksizep0p2] = self.cov1[-2, self.omit+self.ksize1 + i]		
                self.cov[i+2*self.ksizep0p2][-1] = self.cov1[self.omit+2*self.ksize1 + i, -1]
                self.cov[-1][i+2*self.ksizep0p2] = self.cov1[-1, self.omit+2*self.ksize1 + i]
                self.cov[i+2*self.ksizep0p2][-2] = self.cov1[self.omit+2*self.ksize1 + i, -2]
                self.cov[-2][i+2*self.ksizep0p2] = self.cov1[-2, self.omit+2*self.ksize1 + i]
	for i in range(self.ksizemu0):
		self.cov[i + 3*self.ksizep0p2][-1] = self.cov1[self.omit2+3*self.ksize1 + i, -1]
                self.cov[i + 3*self.ksizep0p2][-2] = self.cov1[self.omit2+3*self.ksize1 + i, -2]
                self.cov[-1][i + 3*self.ksizep0p2] = self.cov1[-1,self.omit2+3*self.ksize1 + i]
		self.cov[-2][i + 3*self.ksizep0p2] = self.cov1[-2,self.omit2+3*self.ksize1 + i]

	self.cov[-1][-1] = self.cov1[-1,-1]
        self.cov[-2][-2] = self.cov1[-2,-2]
        self.cov[-1][-2] = self.cov1[-1,-2]
        self.cov[-2][-1] = self.cov1[-2,-1]

	if self.cross:
		for i in range(self.ksizep0p2):
			for j in range(self.ntriag):
				self.cov[i][3*self.ksizep0p2+self.ksizemu0+j] = self.cov1[i+self.omit][4*self.ksize1+j]
                        	self.cov[i+self.ksizep0p2][3*self.ksizep0p2+self.ksizemu0+j] = self.cov1[i+self.ksize1+self.omit][4*self.ksize1+j]
                        	self.cov[i+2*self.ksizep0p2][3*self.ksizep0p2+j+self.ksizemu0] = self.cov1[i+2*self.ksize1+self.omit][4*self.ksize1+j]
                        	self.cov[3*self.ksizep0p2+self.ksizemu0+j][i] = self.cov1[4*self.ksize1+j][i+self.omit]
                        	self.cov[3*self.ksizep0p2+self.ksizemu0+j][i+self.ksizep0p2] = self.cov1[4*self.ksize1+j][i+self.ksize1+self.omit]
                        	self.cov[3*self.ksizep0p2+self.ksizemu0+j][i+2*self.ksizep0p2] = self.cov1[4*self.ksize1+j][i+2*self.ksize1+self.omit]
                for i in range(self.ksizemu0):
                        for j in range(self.ntriag):
                                self.cov[i+3*self.ksizep0p2][3*self.ksizep0p2+self.ksizemu0+j] = self.cov1[i+self.omit2+3*self.ksize1][4*self.ksize1+j]
				self.cov[3*self.ksizep0p2+self.ksizemu0+j][i+3*self.ksizep0p2] = self.cov1[4*self.ksize1+j][i+self.omit2+3*self.ksize1]
		for j in range(self.ntriag):
			self.cov[3*self.ksizep0p2+self.ksizemu0+j][-1] = self.cov1[4*self.ksize1+j][-1]
			self.cov[-1][3*self.ksizep0p2+self.ksizemu0+j] = self.cov1[-1][4*self.ksize1+j] 		
                        self.cov[3*self.ksizep0p2+self.ksizemu0+j][-2] = self.cov1[4*self.ksize1+j][-2]                         
                        self.cov[-2][3*self.ksizep0p2+self.ksizemu0+j] = self.cov1[-2][4*self.ksize1+j]


	self.cov = self.cov/self.covrescale
        self.invcov = np.linalg.inv(self.cov)
        datafile.close()
        self.logdetcov = np.linalg.slogdet(self.cov)[1]


        self.D1 = lambda k1,k2,k3,beta: (15. + 10.*beta+beta**2. + 2.*beta**2.*((k3**2.-k1**2.-k2**2.)/(2.*k1*k2))**2.)/15.
        self.D2 = lambda k1,k2,k3,beta: beta/3+(4 *beta**2.)/15-(k1**2. *beta**2.)/(15 *k2**2.)-(k2**2. *beta**2.)/(15 *k1**2.)-(k1**2. *beta**2.)/(30 *k3**2.)+(k1**4 *beta**2.)/(30 *k2**2. *k3**2.)-(k2**2. *beta**2.)/(30 *k3**2.)+(k2**4. *beta**2.)/(30 *k1**2. *k3**2.)+(k3**2. *beta**2.)/(30 *k1**2.)+(k3**2. *beta**2.)/(30 *k2**2.)+(2 *beta**3)/35-(k1**2. *beta**3.)/(70 *k2**2.)-(k2**2. *beta**3)/(70 *k1**2.)-(k1**2. *beta**3)/(70 *k3**2.)+(k1**4 *beta**3)/(70 *k2**2.*k3**2.)-(k2**2. *beta**3)/(70 *k3**2.)+(k2**4 *beta**3)/(70 *k1**2. *k3**2.)-(k3**2. *beta**3)/(70 *k1**2.)-(k3**2. *beta**3)/(70 *k2**2.)+(k3**4 *beta**3)/(70 *k1**2. *k2**2.)
        self.D3 = lambda k1,k2,k3,beta: beta/6-(k1**2. *beta)/(12 *k2**2.)-(k2**2. *beta)/(12 *k1**2.)+(k3**2. *beta)/(12 *k1**2.)+(k3**2. *beta)/(12 *k2**2.)+ beta**2./6-(k1**2. *beta**2.)/(12 *k2**2.)-(k2**2. *beta**2.)/(12 *k1**2.)+(k3**2. *beta**2.)/(60 *k1**2.)+(k3**2. *beta**2.)/(60 *k2**2.)+(k3**4. *beta**2.)/(15 *k1**2. *k2**2.)+(2 *beta**3.)/35-(k1**4. *beta**3.)/(140 *k2**4.)-(3 *k1**2. *beta**3.)/(140 *k2**2.)-(3 *k2**2. *beta**3.)/(140 *k1**2.)-(k2**4. *beta**3.)/(140 *k1**4.)-(k3**2. *beta**3.)/(35 *k1**2.)+(3 *k1**2. *k3**2. *beta**3.)/(140 *k2**4.)-(k3**2. *beta**3.)/(35 *k2**2.)+(3 *k2**2. *k3**2. *beta**3.)/(140 *k1**4.)-(3 *k3**4. *beta**3.)/(140 *k1**4.)-(3 *k3**4. *beta**3.)/(140 *k2**4.)+(3 *k3**4. *beta**3.)/(70 *k1**2. *k2**2.)+(k3**6 *beta**3.)/(140 *k1**2. *k2**4.)+(k3**6 *beta**3.)/(140 *k1**4. *k2**2.)+ beta**4./105-(k1**4. *beta**4.)/(420 *k2**4.)-(k1**2. *beta**4.)/(420 *k2**2.)-(k2**2. *beta**4.)/(420 *k1**2.)-(k2**4. *beta**4.)/(420 *k1**4.)-(k3**2. *beta**4.)/(105 *k1**2.)+(k1**2. *k3**2. *beta**4.)/(180 *k2**4.)-(k3**2. *beta**4.)/(105 *k2**2.)+(k2**2. *k3**2. *beta**4.)/(180 *k1**4.)-(k3**4. *beta**4.)/(420 *k1**4.)-(k3**4. *beta**4.)/(420 *k2**4.)+(k3**4. *beta**4.)/(70 *k1**2. *k2**2.)-(k3**6 *beta**4.)/(420 *k1**2. *k2**4.)-(k3**6 *beta**4.)/(420 *k1**4. *k2**2.)+(k3**8 *beta**4.)/(630 *k1**4. *k2**4.)
        self.F2 = lambda k1,k2,k3,beta,b1,b2,bG2: (b1*(-5.*(k1**2.-k2**2.)**2.+3.*(k1**2.+k2**2.)*k3**2.+2.*k3**4.)*self.D1(k1,k2,k3,beta) + b1*(-3.*(k1**2.-k2**2.)**2.-1.*(k1**2.+k2**2.)*k3**2.+4.*k3**4.)*self.D2(k1,k2,k3,beta) + 7.*self.D1(k1,k2,k3,beta)*(2.*b2*k1**2.*k2**2. + bG2*(k1-k2-k3)*(k1+k2-k3)*(k1-k2+k3)*(k1+k2+k3)))*b1**2./28./k1**2./k2**2. + b1**4.*self.D3(k1,k2,k3,beta)

        self.F2real = lambda k1,k2,k3,b1,b2,bG2: (b1*(-5.*(k1**2.-k2**2.)**2.+3.*(k1**2.+k2**2.)*k3**2.+2.*k3**4.) + 7.*(2.*b2*k1**2.*k2**2. + bG2*(k1-k2-k3)*(k1+k2-k3)*(k1-k2+k3)*(k1+k2+k3)))*b1**2./28./k1**2./k2**2.

        self.G2 = lambda k1,k2,k3: -((3*(k1**2-k2**2)**2+(k1**2+k2**2)*k3**2-4*k3**4)/(28 *k1**2 *k2**2))


        self.Bbinl0 = lambda I01,I02,I21,I22,I41,I42,I61,I62,Im21,Im22,Im41,Im42,k32,k34,k36,k38,k3m2,e1,e2,e3,e4,e5,e6,e7,e8,e9,e10,e11,e12,e13,e14,e15,e16,e17,e18,e19,e20,e21: 2.*(e1*I22*k3m2*I01 + e2*I61*Im42*k3m2 + e3*k32*Im22*I01 + e4*k34*Im42*I01 + e5*I01*I02 + e6*I41*Im22*k3m2 + e7*I41*Im42+ e8*I21*I02*k3m2 + e9*I21*Im22 + e10*I21*k32*Im42 + Im41*(e11*I62*k3m2 + e12*k34*I02 + e13*k36*Im22 + e14*I42 + e15*k38*Im42 + e16*I22*k32) + Im21*(e17*I42*k3m2 +e18*k32*I02 + e19*I22 + e20*k36*Im42 +e21*k34*Im22) )


        self.Bbin = lambda I01,I02,I21,I22,Im21,Im22,k32,k34,c1,c2,c3,c4,b1: 2.*(b1**2.)*(c1*I01*I02 + c2*(I21*Im22+I22*Im21)+c3*(I02*Im21+I01*Im22)*k32 +c4*(Im21*Im22)*k34)
#        self.F2 = lambda k1,k2,k3,beta,b1,b2,bG2: (b1*(-5.*(k1**2.-k2**2.)**2.+3.*(k1**2.+k2**2.)*k3**2.+2.*k3**4.)*self.D1(k1,k2,k3,beta) + b1*(-3.*(k1**2.-k2**2.)**2.-1.*(k1**2.+k2**2.)*k3**2.+4.*k3**4.)*0. + 7.*self.D1(k1,k2,k3,beta)*(2.*b2*k1**2.*k2**2. + bG2*(k1-k2-k3)*(k1+k2-k3)*(k1-k2+k3)*(k1+k2+k3)))*b1**2./28./k1**2./k2**2.

        self.j2 = lambda x: (3./x**2.-1.)*np.sin(x)/x - 3.*np.cos(x)/x**2.
 

    def loglkl(self, cosmo, data):

        h = cosmo.h()


        #norm = (data.mcmc_parameters['norm']['current'] *
        #         data.mcmc_parameters['norm']['scale'])
	norm = 1.


        i_s=repr(3)
        b1 = (data.mcmc_parameters['b^{('+i_s+')}_1']['current'] *
             data.mcmc_parameters['b^{('+i_s+')}_1']['scale'])

        print("FIXING B1 FOR TESTING")
        print(b1)
        b1 = 1.8682
        print(b1)

        b2 = (data.mcmc_parameters['b^{('+i_s+')}_2']['current'] *
             data.mcmc_parameters['b^{('+i_s+')}_2']['scale'])
        bG2 = (data.mcmc_parameters['b^{('+i_s+')}_{G_2}']['current'] *
             data.mcmc_parameters['b^{('+i_s+')}_{G_2}']['scale'])

#        c1 = (data.mcmc_parameters['c1']['current'] *
#                 data.mcmc_parameters['c1']['scale'])

	c1 = 0.
	
        fNL = (data.mcmc_parameters['f_{NL}']['current'] *
                 data.mcmc_parameters['f_{NL}']['scale'])

##        bGamma3 = (data.mcmc_parameters['b_{Gamma_3}']['current'] *
##                 data.mcmc_parameters['b_{Gamma_3}']['scale'])
#        css0 = (data.mcmc_parameters['c^2_{0}']['current'] *
#                 data.mcmc_parameters['c^2_{0}']['scale'])
#        css2 = (data.mcmc_parameters['c^2_{2}']['current'] *
#                 data.mcmc_parameters['c^2_{2}']['scale'])
#        b4 = (data.mcmc_parameters['b_4']['current'] *
#                 data.mcmc_parameters['b_4']['scale'])
#        css4 = (data.mcmc_parameters['c^2_{4}']['current'] *
#                 data.mcmc_parameters['c^2_{4}']['scale'])

#        a0 = (data.mcmc_parameters['a_0']['current'] *
#                 data.mcmc_parameters['a_0']['scale'])

        dk2 = 0.005;
        #ddkmin = 0.00163625

###### mean values ######
	psh = 3500.
        #bGamma3 = 0.57
        #bGamma3 = -bG2 -(b1-1.)/15.
        bGamma3 = 23.*(b1-1.)/42.
        Pshot = 0.
	Bshot = 1.
        a0 = 0.
        a2 = 0.
        css4 = 0.
        css2 = 30.
        css0 = 0.
        b4 = 500.*1.
#### standard deviations ######
        sigbGamma3 = 0.
        sigPshot = 1.*psh
        sigBshot = 1.*psh
        sigc1 = 5.
        siga0 = psh*1.
        sigcs0 = 30.
        sigcs2 = 30.
        sigcs4 = 30.
        sigb4 = 500.
        siga2 = psh*1.


        z = self.z;
        fz = cosmo.scale_independent_growth_factor_f(z)

        # Run CLASS-PT


	if (self.binningPk>0):
            kint = np.linspace(log(1.e-4),log(0.4075),100)
            kint = np.exp(kint)
            krange_2 = len(kint)
	else:
            kint = self.k2
            krange_2 = self.ksize2


        P0inttab = np.zeros(krange_2)
        P2inttab = np.zeros(krange_2)
        P4inttab = np.zeros(krange_2)

        all_theory = cosmo.get_pk_mult(kint*h,self.z,krange_2)


        Azeta = cosmo.A_s()*2.*np.pi**2.
        fnlc = Azeta**0.5*1944/625*np.pi**4.

        #P0inttab = (norm**2.*all_theory[15] +norm**4.*(all_theory[21])+ norm**1.*b1*all_theory[16] +norm**3.*b1*(all_theory[22]) + norm**0.*b1**2.*all_theory[17] +norm**2.*b1**2.*all_theory[23] + 0.25*norm**2.*b2**2.*all_theory[1] +b1*b2*norm**2.*all_theory[30]+ b2*norm**3.*all_theory[31] + b1*bG2*norm**2.*all_theory[32]+ bG2*norm**3.*all_theory[33] + b2*bG2*norm**2.*all_theory[4]+ bG2**2.*norm**2.*all_theory[5] + 2.*css0*norm**2.*all_theory[11]/h**2. + (2.*bG2+0.8*bGamma3*norm)*norm**2.*(b1*all_theory[7]+norm*all_theory[8]))*h**3. + (psh)*Pshot + a0*(10**4)*(kint/0.5)**2.  + fz**2.*b4*kint**2.*(norm**2.*fz**2./9. + 2.*fz*b1*norm/7. + b1**2./5)*(35./8.)*all_theory[13]*h + a2*(1./3.)*(10.**4.)*(kint/0.45)**2. + fnlc*fNL*(h**3.)*(all_theory[51]+b1*all_theory[52]+b1**2.*all_theory[53]+0.5*b1*b2*all_theory[60]+0.5*b2*all_theory[61]+b1*bG2*all_theory[62]+bG2*all_theory[63])
        #P2inttab = (norm**2.*all_theory[18] +  norm**4.*(all_theory[24])+ norm**1.*b1*all_theory[19] +norm**3.*b1*(all_theory[25]) + b1**2.*norm**2.*all_theory[26] +b1*b2*norm**2.*all_theory[34]+ b2*norm**3.*all_theory[35] + b1*bG2*norm**2.*all_theory[36]+ bG2*norm**3.*all_theory[37]  + 2.*css2*norm**2.*all_theory[12]/h**2. + (2.*bG2+0.8*bGamma3*norm)*norm**3.*all_theory[9])*h**3. + fz**2.*b4*kint**2.*((norm**2.*fz**2.*70. + 165.*fz*b1*norm+99.*b1**2.)*4./693.)*(35./8.)*all_theory[13]*h + a2*(10.**4.)*(2./3.)*(kint/0.45)**2.+ fnlc*fNL*(h**3.)*(all_theory[54]+b1*all_theory[55]+b1**2.*all_theory[56]+0.5*b1*b2*all_theory[64]+0.5*b2*all_theory[65]+b1*bG2*all_theory[66]+bG2*all_theory[67])
        #P4inttab = (norm**2.*all_theory[20] + norm**4.*all_theory[27]+ b1*norm**3.*all_theory[28] + b1**2.*norm**2.*all_theory[29] + b2*norm**3.*all_theory[38] + bG2*norm**3.*all_theory[39]  +2.*css4*norm**2.*all_theory[13]/h**2.)*h**3. + fz**2.*b4*kint**2.*(norm**2.*fz**2.*210./143. + 30.*fz*b1*norm/11.+b1**2.)*all_theory[13]*h+fnlc*fNL*(h**3.)*(all_theory[57]+b1*all_theory[58]+b1**2.*all_theory[59]+0.5*b1*b2*all_theory[68]+0.5*b2*all_theory[69]+b1*bG2*all_theory[70]+bG2*all_theory[71])


        P0inttab = (norm**2.*all_theory[15] +norm**4.*(all_theory[21])+ norm**1.*b1*all_theory[16] +norm**3.*b1*(all_theory[22]) + norm**0.*b1**2.*all_theory[17] +norm**2.*b1**2.*all_theory[23] + 0.25*norm**2.*b2**2.*all_theory[1] +b1*b2*norm**2.*all_theory[30]+ b2*norm**3.*all_theory[31] + b1*bG2*norm**2.*all_theory[32]+ bG2*norm**3.*all_theory[33] + b2*bG2*norm**2.*all_theory[4]+ bG2**2.*norm**2.*all_theory[5] + 2.*css0*norm**2.*all_theory[11]/h**2. + (2.*bG2+0.8*bGamma3*norm)*norm**2.*(b1*all_theory[7]+norm*all_theory[8]))*h**3. + (psh)*Pshot + a0*(10**4)*(kint/0.5)**2.  + fz**2.*b4*kint**2.*(norm**2.*fz**2./9. + 2.*fz*b1*norm/7. + b1**2./5)*(35./8.)*all_theory[13]*h + a2*(1./3.)*(10.**4.)*(kint/0.45)**2.
        P2inttab = (norm**2.*all_theory[18] +  norm**4.*(all_theory[24])+ norm**1.*b1*all_theory[19] +norm**3.*b1*(all_theory[25]) + b1**2.*norm**2.*all_theory[26] +b1*b2*norm**2.*all_theory[34]+ b2*norm**3.*all_theory[35] + b1*bG2*norm**2.*all_theory[36]+ bG2*norm**3.*all_theory[37]  + 2.*css2*norm**2.*all_theory[12]/h**2. + (2.*bG2+0.8*bGamma3*norm)*norm**3.*all_theory[9])*h**3. + fz**2.*b4*kint**2.*((norm**2.*fz**2.*70. + 165.*fz*b1*norm+99.*b1**2.)*4./693.)*(35./8.)*all_theory[13]*h + a2*(10.**4.)*(2./3.)*(kint/0.45)**2.
        P4inttab = (norm**2.*all_theory[20] + norm**4.*all_theory[27]+ b1*norm**3.*all_theory[28] + b1**2.*norm**2.*all_theory[29] + b2*norm**3.*all_theory[38] + bG2*norm**3.*all_theory[39]  +2.*css4*norm**2.*all_theory[13]/h**2.)*h**3. + fz**2.*b4*kint**2.*(norm**2.*fz**2.*210./143. + 30.*fz*b1*norm/11.+b1**2.)*all_theory[13]*h

        E0bG3 = (0.8*sigbGamma3*norm)*norm**2.*(b1*all_theory[7]+norm*all_theory[8])*h**3.
        E2bG3 = (0.8*sigbGamma3*norm)*norm**3.*all_theory[9]*h**3.
        Ecs4 = 2.*norm**2.*all_theory[13]*h**1.
        Ecs2 = 2.*norm**2.*all_theory[12]*h**1.
        Ecs0 = 2.*norm**2.*all_theory[11]*h**1.
        Eb4 = fz**2.*kint**2.*all_theory[13]*h


        x1 = np.zeros(3*self.ksizep0p2 + self.ksizemu0+self.ntriag+2)
        EbG3cov = np.zeros(3*self.ksizep0p2+self.ntriag+ self.ksizemu0+2)
        Pshotcov = np.zeros(3*self.ksizep0p2+self.ntriag+ self.ksizemu0+2)
        Bshotcov = np.zeros(3*self.ksizep0p2+self.ntriag+ self.ksizemu0+2)
        c1cov = np.zeros(3*self.ksizep0p2+self.ntriag+ self.ksizemu0+2)

        a0cov = np.zeros(3*self.ksizep0p2+self.ntriag+ self.ksizemu0+2)
        a2cov = np.zeros(3*self.ksizep0p2+self.ntriag+ self.ksizemu0+2)
        Ecs4cov = np.zeros(3*self.ksizep0p2+self.ntriag+ self.ksizemu0+2)
        Ecs2cov = np.zeros(3*self.ksizep0p2+self.ntriag+ self.ksizemu0+2)
        Ecs0cov = np.zeros(3*self.ksizep0p2+self.ntriag+ self.ksizemu0+2)

        Eb4cov = np.zeros(3*self.ksizep0p2+self.ksizemu0+self.ntriag+2)


        P0int = interpolate.InterpolatedUnivariateSpline(kint,P0inttab,ext=3)
        P2int = interpolate.InterpolatedUnivariateSpline(kint,P2inttab,ext=3)
        P4int = interpolate.InterpolatedUnivariateSpline(kint,P4inttab,ext=3)
        E0bG3int = interpolate.InterpolatedUnivariateSpline(kint,E0bG3,ext=3)
        E2bG3int = interpolate.InterpolatedUnivariateSpline(kint,E2bG3,ext=3)
        Ecs4int = interpolate.InterpolatedUnivariateSpline(kint,Ecs4,ext=3)
        Ecs2int = interpolate.InterpolatedUnivariateSpline(kint,Ecs2,ext=3)
        Ecs0int = interpolate.InterpolatedUnivariateSpline(kint,Ecs0,ext=3)
        Eb4int = interpolate.InterpolatedUnivariateSpline(kint,Eb4,ext=3)

        integr0bG3 = lambda k: exp(3.*k)*E0bG3int(exp(k))
        integr2bG3 = lambda k: exp(3.*k)*E2bG3int(exp(k))
        integrand0 = lambda k: exp(3.*k)*P0int(exp(k))
        integrand2 = lambda k: exp(3.*k)*P2int(exp(k))
        integrand4 = lambda k: exp(3.*k)*P4int(exp(k))
        integrandEcs4 = lambda k: exp(3.*k)*Ecs4int(exp(k))
        integrandEcs2 = lambda k: exp(3.*k)*Ecs2int(exp(k))
        integrandEcs0 = lambda k: exp(3.*k)*Ecs0int(exp(k))
        integrandEb4 = lambda k: exp(3.*k)*Eb4int(exp(k))



        P0th = np.zeros(self.ksize2)
        P2th = np.zeros(self.ksize2)
        P4th = np.zeros(self.ksize2)

        E0bG3th = np.zeros(self.ksize2)
        E2bG3th = np.zeros(self.ksize2)
        Ecs4th = np.zeros(self.ksize2)
        Ecs2th = np.zeros(self.ksize2)
        Ecs0th = np.zeros(self.ksize2)
        Eb4th = np.zeros(self.ksize2)

        if (self.binningPk>0) :
	#print('Beginning of 0th integration')
            for i in range(self.ksize2):
                P0th[i] = integrate.quad(integrand0, log(dk2*i+self.kmin2), log(dk2*(i+1)+self.kmin2))[0]*3./((dk2*(i+1)+self.kmin2)**3.-(dk2*i+self.kmin2)**3.)
                P2th[i] = integrate.quad(integrand2, log(dk2*i+self.kmin2), log(dk2*(i+1)+self.kmin2))[0]*3./((dk2*(i+1)+self.kmin2)**3.-(dk2*i+self.kmin2)**3.)
                P4th[i] = integrate.quad(integrand4, log(dk2*i+self.kmin2), log(dk2*(i+1)+self.kmin2))[0]*3./((dk2*(i+1)+self.kmin2)**3.-(dk2*i+self.kmin2)**3.)
                Ecs0th[i] = integrate.quad(integrandEcs0, log(dk2*i+self.kmin2), log(dk2*(i+1)+self.kmin2))[0]*3./((dk2*(i+1)+self.kmin2)**3.-(dk2*i+self.kmin2)**3.)
                Ecs2th[i] = integrate.quad(integrandEcs2, log(dk2*i+self.kmin2), log(dk2*(i+1)+self.kmin2))[0]*3./((dk2*(i+1)+self.kmin2)**3.-(dk2*i+self.kmin2)**3.)
                Ecs4th[i] = integrate.quad(integrandEcs4, log(dk2*i+self.kmin2), log(dk2*(i+1)+self.kmin2))[0]*3./((dk2*(i+1)+self.kmin2)**3.-(dk2*i+self.kmin2)**3.)
                E0bG3th[i] = integrate.quad(integr0bG3, log(dk2*i+self.kmin2), log(dk2*(i+1)+self.kmin2))[0]*3./((dk2*(i+1)+self.kmin2)**3.-(dk2*i+self.kmin2)**3.)
                E2bG3th[i] = integrate.quad(integr2bG3, log(dk2*i+self.kmin2), log(dk2*(i+1)+self.kmin2))[0]*3./((dk2*(i+1)+self.kmin2)**3.-(dk2*i+self.kmin2)**3.)
                Eb4th[i] = integrate.quad(integrandEb4, log(dk2*i+self.kmin2), log(dk2*(i+1)+self.kmin2))[0]*3./((dk2*(i+1)+self.kmin2)**3.-(dk2*i+self.kmin2)**3.)
	else:
		P0th = P0inttab
		P2th = P2inttab
		Ecs0th = Ecs0
		Ecs2th = Ecs2
		Ecs4th = Ecs4
		E0bG3th = E0bG3
		E2bG3th = E2bG3
		Eb4th = Eb4

        for i in range(self.ksizep0p2):
            x1[i] = P0th[i] - self.Pk0p0p2[i]
            x1[i + self.ksizep0p2] = P2th[i] - self.Pk2p0p2[i]
            x1[i + 2*self.ksizep0p2] = P4th[i] - self.Pk4p0p2[i]
            Pshotcov[i] = 1.
            a0cov[i] = (self.k2[i]/0.45)**2.
            a2cov[i] = (1./3.)*(self.k2[i]/0.45)**2.
            a2cov[i+self.ksizep0p2] = (2./3.)*(self.k2[i]/0.45)**2.;
            Ecs4cov[i+2*self.ksizep0p2] = Ecs4th[i]
            Ecs2cov[i+self.ksizep0p2] = Ecs2th[i]
            Ecs0cov[i] = Ecs0th[i]
            EbG3cov[i] = E0bG3th[i]
            EbG3cov[i+self.ksizep0p2] = E2bG3th[i]

            Eb4cov[i] = Eb4th[i]*(norm**2.*fz**2./9. + 2.*fz*b1*norm/7. + b1**2./5)*(35./8.)
            Eb4cov[i + self.ksizep0p2] = Eb4th[i]*((norm**2.*fz**2.*70. + 165.*fz*b1*norm+99.*b1**2.)*4./693.)*(35./8.)
            Eb4cov[i + 2*self.ksizep0p2] = Eb4th[i]*(norm**2.*fz**2.*210./143. + 30.*fz*b1*norm/11.+b1**2.)

        for i in range(self.ksizemu0):
            x1[i + 3*self.ksizep0p2] = P0th[i + self.ksizep0p2]-P2th[i + self.ksizep0p2]/2.+3.*P4th[i + self.ksizep0p2]/8. - self.Q0[i]
            Pshotcov[i + 3*self.ksizep0p2] = 1.
            a0cov[i + 3*self.ksizep0p2] = (self.k2[i + self.ksizep0p2]/0.45)**2.
            EbG3cov[i + 3*self.ksizep0p2] = E0bG3th[i + self.ksizep0p2] - E2bG3th[i + self.ksizep0p2]/2.
            Ecs4cov[i + 3*self.ksizep0p2] = 3.*Ecs4th[i+self.ksizep0p2]/8.
            Ecs2cov[i + 3*self.ksizep0p2] = -1.*Ecs2th[i+self.ksizep0p2]/2.
            Ecs0cov[i + 3*self.ksizep0p2] = Ecs0th[i+self.ksizep0p2]
            Eb4cov[i + 3*self.ksizep0p2] = Eb4th[i+self.ksizep0p2]*((norm**2.*fz**2./9. + 2.*fz*b1*norm/7. + b1**2./5)*(35./8.) - ((norm**2.*fz**2.*70. + 165.*fz*b1*norm+99.*b1**2.)*4./693.)*(35./8.)/2. +3.*(norm**2.*fz**2.*210./143. + 30.*fz*b1*norm/11.+b1**2.)/8.)


        x1[-2] = self.rdHfid/(cosmo.rs_drag()*cosmo.Hubble(self.z)) - self.alphas[0]
        x1[-1] = self.rdDAfid/(cosmo.rs_drag()/cosmo.angular_distance(self.z)) - self.alphas[1]
	


### bispectrum part starts

        Ashot = 0.
        c0 = 0.
        c2 = 0.
        SigmaB = 0.
        beta = fz/b1
        #all_theory_2 = cosmo.get_pk_mult(self.k*h,self.z,self.ksize)
        a0 = 1. + 2.*beta/3. + beta**2./5.
        Plintab = np.zeros(krange_2)
        Plintab = -1.*norm**2.*(all_theory[10]/h**2./kint**2)*h**3
        P2 = norm**2.*(all_theory[14])*h**3.

        delta = np.zeros(self.ntriag)
        Pbar = psh
        ng = (1.+Ashot)/Pbar

        rbao = cosmo.rs_drag()*h
        P0int = interpolate.InterpolatedUnivariateSpline(kint,Plintab,ext=3)

	#print('1st Sigma integration')
        Sigma = integrate.quad(lambda k: (4*np.pi)*exp(1.*k)*P0int(exp(k))*(1.-3*(2*rbao*exp(k)*cos(exp(k)*rbao)+(-2+rbao**2*exp(k)**2)*sin(rbao*exp(k)))/(exp(k)*rbao)**3)/(3*(2*np.pi)**3.), log(2.e-4), log(0.2))[0]
        deltaSigma = integrate.quad(lambda k: (4*np.pi)*exp(1.*k)*P0int(exp(k))*(self.j2(exp(k)*rbao))/((2*np.pi)**3.), log(2.e-4), log(0.2))[0]
	#print('End of 1st Sigma integration')

        Pw = (Plintab-P2)/(np.exp(-kint**2.*Sigma)-np.exp(-kint**2.*Sigma)*(1+kint**2.*Sigma));
        Pnw = Plintab - Pw*np.exp(-kint**2.*Sigma)

        Pwfunc = interpolate.InterpolatedUnivariateSpline(kint,Pw,ext=3)
        Pnwfunc = interpolate.InterpolatedUnivariateSpline(kint,Pnw,ext=3)

        ks = 0.05

	#print('2nd Sigma integration')
        Sigma2 = integrate.quad(lambda k: (4*np.pi)*exp(1.*k)*P0int(exp(k))*(1.-3*(2*rbao*exp(k)*cos(exp(k)*rbao)+(-2+rbao**2*exp(k)**2)*sin(rbao*exp(k)))/(exp(k)*rbao)**3)/(3*(2*np.pi)**3.), log(2.e-4), log(ks))[0]
        deltaSigma2 = integrate.quad(lambda k: (4*np.pi)*exp(1.*k)*P0int(exp(k))*(self.j2(exp(k)*rbao))/((2*np.pi)**3.), log(2.e-4), log(ks))[0]
	#print('End of 2nd Sigma integration')


        #Pres = lambda k, mu: P0int(k)
        Pres = lambda k, mu: Pnwfunc(k) +  np.exp(-k**2.*(Sigma2*(1.+2.*fz*mu**2.*(2.+fz)) + deltaSigma2*mu**2.*fz**2.*(mu**2.-1.)))*Pwfunc(k) -(c0+c1*mu**2.+c2*mu**4.)*(k/0.3)**2.*P0int(k)/(b1+fz*mu**2.)
        PresC = lambda k, mu:Pnwfunc(k) +  np.exp(-k**2.*(Sigma2*(1.+2.*fz*mu**2.*(2.+fz)) + deltaSigma2*mu**2.*fz**2.*(mu**2.-1.)))*Pwfunc(k) -(mu**2.)*(k/0.3)**2.*P0int(k)/(b1+fz*mu**2.)

        da=cosmo.angular_distance(self.z)/(self.hfid/h)
        hz=cosmo.Hubble(self.z)*(self.hfid/h)/self.kmsMpc


        apar=self.hzfid/hz
        aperp=da/self.dafid
        B0th = np.zeros(self.ntriag)
        new_triag = self.new_triag;


        Azeta = cosmo.A_s()*2.*np.pi**2.

        Tfunc = lambda k: (P0int(k)/(Azeta*((k/0.05)**(cosmo.n_s()-1.))/k**3.))**0.5

        #Tfunc = lambda k: (P0int(k)/(Azeta*((k/0.05)**cosmo.n_s())/k**3.))**0.5
        BNG = lambda k1, k2, k3: Azeta**2.*(Tfunc(k1)*Tfunc(k2)*Tfunc(k3)*(18./5.)*(-1./k1**3./k2**3.
                        -1./k3**3./k2**3.-1./k1**3./k3**3.-2./k1**2./k2**2./k3**2.
                        +1/k1/k2**2./k3**3.+1/k1/k3**2./k2**3.+1/k2/k3**2./k1**3.
                        +1/k2/k1**2./k3**3.+1/k3/k1**2./k2**3.+1/k3/k2**2./k1**3.))

        EBPshot = np.zeros(self.ntriag);
	EBBshot = np.zeros(self.ntriag);



        def Bfunc3(k1,k2,k3,mu,phi,kc1=0,kc2=0,kc3=0,apar=1,aperp=1):
                kk1 = (kc1+k1*dk1/2.)
                kk2 = (kc2+k2*dk2/2.)
                kk3 = (kc3+k3*dk3/2.)
                ddk1 = dk1/2.
                ddk2 = dk2/2.
                ddk3 = dk3/2.
                xxfunc = (kk3**2.-kk1**2.-kk2**2.)/(2.*kk1*kk2);
                yyfunc = np.sqrt(np.abs(1.-xxfunc**2.))
                mmu2 = xxfunc*mu - np.sqrt(1.-mu**2.)*yyfunc*np.cos(phi*2.*np.pi)
                mmu3 = -(kk2/kk3)*mmu2-(kk1/kk3)*mu;
                nnu1 = mu/apar/(np.sqrt(np.abs(mu**2./apar**2. + (1-mu**2.)/aperp**2.)));
                nnu2 = mmu2/apar/(np.sqrt(np.abs(mmu2**2./apar**2.+(1-mmu2**2.)/aperp**2.)));
                nnu3 = mmu3/apar/(np.sqrt(np.abs(mmu3**2./apar**2. + (1-mmu3**2.)/aperp**2.)));
                qq1 = np.sqrt(np.abs(mu**2/apar**2 + (1.-mu**2)/aperp**2));
                qq2 = np.sqrt(np.abs(mmu2**2/apar**2 + (1.-mmu2**2)/aperp**2))
                qq3 = np.sqrt(np.abs(mmu3**2/apar**2 + (1.-mmu3**2)/aperp**2))
                PPres1 = Pres(kk1*qq1,nnu1)
                PPres2 = Pres(kk2*qq2,nnu2)
                PPres3 = Pres(kk3*qq3,nnu3)
                zz21 = self.F2real(kk1*qq1,kk2*qq2,kk3*qq3,b1,b2,bG2)+b1**3.*beta*((nnu2*kk2*qq2+nnu1*kk1*qq1)/kk3/qq3)**2.*self.G2(kk1*qq1,kk2*qq2,kk3*qq3)+(b1**4.*beta/2.)*(nnu2*kk2*qq2+nnu1*kk1*qq1)*(nnu1*(1.+beta*nnu2**2.)/kk1/qq1 + nnu2*(1.+beta*nnu1**2.)/kk2/qq2)
                zz22 = self.F2real(kk1*qq1,kk3*qq3,kk2*qq2,b1,b2,bG2)+b1**3.*beta*((nnu3*kk3*qq3+nnu1*kk1*qq1)/kk2/qq2)**2.*self.G2(kk1*qq1,kk3*qq3,kk2*qq2)+(b1**4.*beta/2.)*(nnu3*kk3*qq3+nnu1*kk1*qq1)*(nnu1*(1.+beta*nnu3**2.)/kk1/qq1 + nnu3*(1.+beta*nnu1**2.)/kk3/qq3)
                zz23 = self.F2real(kk2*qq2,kk3*qq3,kk1*qq1,b1,b2,bG2)+b1**3.*beta*((nnu2*kk2*qq2+nnu3*kk3*qq3)/kk1/qq1)**2.*self.G2(kk2*qq2,kk3*qq3,kk1*qq1)+(b1**4.*beta/2.)*(nnu2*kk2*qq2+nnu3*kk3*qq3)*(nnu2*(1.+beta*nnu3**2.)/kk2/qq2 + nnu3*(1.+beta*nnu2**2.)/kk3/qq3)

                FF2func1 = zz21*(1+beta*nnu1**2)*(1.+beta*nnu2**2.)*PPres1*kk1*ddk1*PPres2*kk2*ddk2*kk3*ddk3 + 1.*0.5*(Bshot/ng)*b1**2.*PPres1*kk1*(1.+beta*nnu1**2.*(Bshot+2.*(1.+Pshot))/Bshot + beta**2.*nnu1**4.*2.*(1.+Pshot)/Bshot)*kk2*kk3*ddk1*ddk2*ddk3 + ((1.+Pshot)/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/2.
                FF2func2 = zz22*(1+beta*nnu1**2)*(1.+beta*nnu3**2.)*PPres1*kk1*ddk1*PPres3*kk3*ddk3*kk2*ddk2 + 1.*0.5*(Bshot/ng)*b1**2.*PPres2*kk2*(1.+beta*nnu2**2.*(Bshot+2.+2.*Pshot)/Bshot + beta**2.*nnu2**4.*2.*(1.+Pshot)/Bshot)*kk1*kk3*ddk1*ddk2*ddk3 + 0.*(1/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/6.
                FF2func3 = zz23*(1+beta*nnu2**2)*(1.+beta*nnu3**2.)*PPres2*kk2*ddk2*PPres3*kk3*ddk3*kk1*ddk1 + 1.*0.5*(Bshot/ng)*b1**2.*PPres3*kk3*(1.+beta*nnu3**2.*(Bshot+2.+2.*Pshot)/Bshot + beta**2.*nnu3**4.*2.*(1.+Pshot)/Bshot)*kk2*kk1*ddk1*ddk2*ddk3 + 0.*(1/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/6.
                FFnlfunc = fNL*BNG(kk1*qq1,kk2*qq2,kk3*qq3)*b1**3.*(1+beta*nnu1**2)*(1.+beta*nnu3**2.)*(1+beta*nnu2**2)*kk1*kk2*kk3*ddk1*ddk2*ddk3

                Bfunc3 = (2.*FF2func1 + 2.*FF2func2 + 2.*FF2func3 + FFnlfunc)/apar**2./aperp**4.
                return Bfunc3




        def EBfunc(k1,k2,k3,mu,phi,kc1=0,kc2=0,kc3=0,apar=1,aperp=1):
                kk1 = (kc1+k1*dk1/2.)
                kk2 = (kc2+k2*dk2/2.)
                kk3 = (kc3+k3*dk3/2.)
                ddk1 = dk1/2.
                ddk2 = dk2/2.
                ddk3 = dk3/2.
                xxfunc = (kk3**2.-kk1**2.-kk2**2.)/(2.*kk1*kk2);
                yyfunc = np.sqrt(np.abs(1.-xxfunc**2.))
                mmu2 = xxfunc*mu - np.sqrt(1.-mu**2.)*yyfunc*np.cos(phi*2.*np.pi)
                mmu3 = -(kk2/kk3)*mmu2-(kk1/kk3)*mu;
                nnu1 = mu/apar/(np.sqrt(np.abs(mu**2./apar**2. + (1-mu**2.)/aperp**2.)));
                nnu2 = mmu2/apar/(np.sqrt(np.abs(mmu2**2./apar**2.+(1-mmu2**2.)/aperp**2.)));
                nnu3 = mmu3/apar/(np.sqrt(np.abs(mmu3**2./apar**2. + (1-mmu3**2.)/aperp**2.)));
                qq1 = np.sqrt(np.abs(mu**2/apar**2 + (1.-mu**2)/aperp**2));
                qq2 = np.sqrt(np.abs(mmu2**2/apar**2 + (1.-mmu2**2)/aperp**2))
                qq3 = np.sqrt(np.abs(mmu3**2/apar**2 + (1.-mmu3**2)/aperp**2))
                PPres1 = Pres(kk1*qq1,nnu1)
                PPres2 = Pres(kk2*qq2,nnu2)
                PPres3 = Pres(kk3*qq3,nnu3)
		EBfunc = b1**2.*(((1.+beta*nnu1**2.)*PPres1+PPres2*(1.+beta*nnu2**2.)+ PPres3*(1.+beta*nnu3**2.))*kk1*kk2*kk3*ddk1*ddk2*ddk3)/apar**2./aperp**4.
                return EBfunc


        def EPfunc(k1,k2,k3,mu,phi,kc1=0,kc2=0,kc3=0,apar=1,aperp=1):
                kk1 = (kc1+k1*dk1/2.)
                kk2 = (kc2+k2*dk2/2.)
                kk3 = (kc3+k3*dk3/2.)
                ddk1 = dk1/2.
                ddk2 = dk2/2.
                ddk3 = dk3/2.
                xxfunc = (kk3**2.-kk1**2.-kk2**2.)/(2.*kk1*kk2);
                yyfunc = np.sqrt(np.abs(1.-xxfunc**2.))
                mmu2 = xxfunc*mu - np.sqrt(1.-mu**2.)*yyfunc*np.cos(phi*2.*np.pi)
                mmu3 = -(kk2/kk3)*mmu2-(kk1/kk3)*mu;
                nnu1 = mu/apar/(np.sqrt(np.abs(mu**2./apar**2. + (1-mu**2.)/aperp**2.)));
                nnu2 = mmu2/apar/(np.sqrt(np.abs(mmu2**2./apar**2.+(1-mmu2**2.)/aperp**2.)));
                nnu3 = mmu3/apar/(np.sqrt(np.abs(mmu3**2./apar**2. + (1-mmu3**2.)/aperp**2.)));
                qq1 = np.sqrt(np.abs(mu**2/apar**2 + (1.-mu**2)/aperp**2));
                qq2 = np.sqrt(np.abs(mmu2**2/apar**2 + (1.-mmu2**2)/aperp**2))
                qq3 = np.sqrt(np.abs(mmu3**2/apar**2 + (1.-mmu3**2)/aperp**2))
                PPres1 = Pres(kk1*qq1,nnu1)
                PPres2 = Pres(kk2*qq2,nnu2)
                PPres3 = Pres(kk3*qq3,nnu3)
		EPfunc = (b1*(2.*beta*nnu1**2.*(1.+beta*nnu1**2.)*PPres1+PPres2*(beta*nnu2**2.*2.)*(1.+beta*nnu2**2.)+ PPres3*(2.*beta*nnu3**2.)*(1.+beta*nnu3**2.) + 2.*psh)*kk1*kk2*kk3*ddk1*ddk2*ddk3)/apar**2./aperp**4.
                return EPfunc



        def Bfunc4(k1,k2,k3,mu,phi,kc1=0,kc2=0,kc3=0,apar=1,aperp=1):
                kk1 = (kc1+k1*dk1/2.)
                kk2 = (kc2+k2*dk2/2.)
                kk3 = (kc3+k3*dk3/2.)
                ddk1 = dk1/2.
                ddk2 = dk2/2.
                ddk3 = dk3/2.
                xxfunc = (kk3**2.-kk1**2.-kk2**2.)/(2.*kk1*kk2);
                yyfunc = np.sqrt(np.abs(1.-xxfunc**2.))
                mmu2 = xxfunc*mu - np.sqrt(1.-mu**2.)*yyfunc*np.cos(phi*2.*np.pi)
                mmu3 = -(kk2/kk3)*mmu2-(kk1/kk3)*mu;
                nnu1 = mu/apar/(np.sqrt(np.abs(mu**2./apar**2. + (1-mu**2.)/aperp**2.)));
                nnu2 = mmu2/apar/(np.sqrt(np.abs(mmu2**2./apar**2.+(1-mmu2**2.)/aperp**2.)));
                nnu3 = mmu3/apar/(np.sqrt(np.abs(mmu3**2./apar**2. + (1-mmu3**2.)/aperp**2.)));
                qq1 = np.sqrt(np.abs(mu**2/apar**2 + (1.-mu**2)/aperp**2));
                qq2 = np.sqrt(np.abs(mmu2**2/apar**2 + (1.-mmu2**2)/aperp**2))
                qq3 = np.sqrt(np.abs(mmu3**2/apar**2 + (1.-mmu3**2)/aperp**2))
                PPres1 = Pres(kk1*qq1,nnu1)
                PPres2 = Pres(kk2*qq2,nnu2)
                PPres3 = Pres(kk3*qq3,nnu3)

                PPres1C = PresC(kk1*qq1,nnu1)
                PPres2C = PresC(kk2*qq2,nnu2)
                PPres3C = PresC(kk3*qq3,nnu3)
                zz21 = self.F2real(kk1*qq1,kk2*qq2,kk3*qq3,b1,b2,bG2)+b1**3.*beta*((nnu2*kk2*qq2+nnu1*kk1*qq1)/kk3/qq3)**2.*self.G2(kk1*qq1,kk2*qq2,kk3*qq3)+(b1**4.*beta/2.)*(nnu2*kk2*qq2+nnu1*kk1*qq1)*(nnu1*(1.+beta*nnu2**2.)/kk1/qq1 + nnu2*(1.+beta*nnu1**2.)/kk2/qq2)
                zz22 = self.F2real(kk1*qq1,kk3*qq3,kk2*qq2,b1,b2,bG2)+b1**3.*beta*((nnu3*kk3*qq3+nnu1*kk1*qq1)/kk2/qq2)**2.*self.G2(kk1*qq1,kk3*qq3,kk2*qq2)+(b1**4.*beta/2.)*(nnu3*kk3*qq3+nnu1*kk1*qq1)*(nnu1*(1.+beta*nnu3**2.)/kk1/qq1 + nnu3*(1.+beta*nnu1**2.)/kk3/qq3)
                zz23 = self.F2real(kk2*qq2,kk3*qq3,kk1*qq1,b1,b2,bG2)+b1**3.*beta*((nnu2*kk2*qq2+nnu3*kk3*qq3)/kk1/qq1)**2.*self.G2(kk2*qq2,kk3*qq3,kk1*qq1)+(b1**4.*beta/2.)*(nnu2*kk2*qq2+nnu3*kk3*qq3)*(nnu2*(1.+beta*nnu3**2.)/kk2/qq2 + nnu3*(1.+beta*nnu2**2.)/kk3/qq3)
                FF2func1 = zz21*(1+beta*nnu1**2)*(1.+beta*nnu2**2.)*PPres1*kk1*ddk1*PPres2*kk2*ddk2*kk3*ddk3 + 1.*0.5*(Bshot/ng)*b1**2.*PPres1*kk1*(1.+beta*nnu1**2.*(Bshot+2.*(1.+Pshot))/Bshot + beta**2.*nnu1**4.*2.*(1.+Pshot)/Bshot)*kk2*kk3*ddk1*ddk2*ddk3 + ((1.+Pshot)/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/2.
                FF2func2 = zz22*(1+beta*nnu1**2)*(1.+beta*nnu3**2.)*PPres1*kk1*ddk1*PPres3*kk3*ddk3*kk2*ddk2 + 1.*0.5*(Bshot/ng)*b1**2.*PPres2*kk2*(1.+beta*nnu2**2.*(Bshot+2.+2.*Pshot)/Bshot + beta**2.*nnu2**4.*2.*(1.+Pshot)/Bshot)*kk1*kk3*ddk1*ddk2*ddk3 + 0.*(1/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/6.
                FF2func3 = zz23*(1+beta*nnu2**2)*(1.+beta*nnu3**2.)*PPres2*kk2*ddk2*PPres3*kk3*ddk3*kk1*ddk1 + 1.*0.5*(Bshot/ng)*b1**2.*PPres3*kk3*(1.+beta*nnu3**2.*(Bshot+2.+2.*Pshot)/Bshot + beta**2.*nnu3**4.*2.*(1.+Pshot)/Bshot)*kk2*kk1*ddk1*ddk2*ddk3 + 0.*(1/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/6.
                FF2func1C = zz21*(1+beta*nnu1**2)*(1.+beta*nnu2**2.)*PPres1C*kk1*ddk1*PPres2C*kk2*ddk2*kk3*ddk3 + 1.*0.5*(Bshot/ng)*b1**2.*PPres1C*kk1*(1.+beta*nnu1**2.*(Bshot+2.*(1.+Pshot))/Bshot + beta**2.*nnu1**4.*2.*(1.+Pshot)/Bshot)*kk2*kk3*ddk1*ddk2*ddk3 + ((1.+Pshot)/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/2.
                FF2func2C = zz22*(1+beta*nnu1**2)*(1.+beta*nnu3**2.)*PPres1C*kk1*ddk1*PPres3C*kk3*ddk3*kk2*ddk2 + 1.*0.5*(Bshot/ng)*b1**2.*PPres2C*kk2*(1.+beta*nnu2**2.*(Bshot+2.+2.*Pshot)/Bshot + beta**2.*nnu2**4.*2.*(1.+Pshot)/Bshot)*kk1*kk3*ddk1*ddk2*ddk3 + 0.*(1/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/6.
                FF2func3C = zz23*(1+beta*nnu2**2)*(1.+beta*nnu3**2.)*PPres2C*kk2*ddk2*PPres3C*kk3*ddk3*kk1*ddk1 + 1.*0.5*(Bshot/ng)*b1**2.*PPres3C*kk3*(1.+beta*nnu3**2.*(Bshot+2.+2.*Pshot)/Bshot + beta**2.*nnu3**4.*2.*(1.+Pshot)/Bshot)*kk2*kk1*ddk1*ddk2*ddk3 + 0.*(1/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/6.

                Bfunc4 = (2.*FF2func1C + 2.*FF2func2C + 2.*FF2func3C - 2.*FF2func1 - 2.*FF2func2 - 2.*FF2func3)/apar**2./aperp**4.
                return Bfunc4






        for j in range(int(self.ntriag)):
                kc1 = self.k[new_triag[0][j]]
                kc2 = self.k[new_triag[1][j]]
                kc3 = self.k[new_triag[2][j]]
                dk1 = self.dk
                dk2 = self.dk
                dk3 = self.dk
                if (self.k[new_triag[0][j]]<self.dk):
                        kc1 = 0.0058
                        dk1  = 0.0084
                if (self.k[new_triag[1][j]]<self.dk):
                        kc2 = 0.0058
                        dk2  = 0.0084
                if (self.k[new_triag[2][j]]<self.dk):
                        kc3 = 0.0058
                        dk3  = 0.0084

                Nk1 = ((kc1+dk1/2.)**2. - (kc1-dk1/2.)**2.)/2.
                Nk2 = ((kc2+dk2/2.)**2. - (kc2-dk2/2.)**2.)/2.
                Nk3 = ((kc3+dk3/2.)**2. - (kc3-dk3/2.)**2.)/2.

                mat4 = Bfunc3(*self.mesh_mu,kc1=kc1,kc2=kc2,kc3=kc3,apar=apar,aperp=aperp)
                B0th[j] = np.matmul(np.matmul(np.matmul(np.matmul(np.matmul(mat4,self.gauss_w2)/2.,self.gauss_w2)/2.,self.gauss_w),self.gauss_w),self.gauss_w)/Nk1/Nk2/Nk3


                delta[j] = B0th[j]*self.weights[j] - self.Bk[j]
		x1[3*self.ksizep0p2 + self.ksizemu0 + j] = delta[j]

		mat5 = EBfunc(*self.mesh_mu,kc1=kc1,kc2=kc2,kc3=kc3,apar=apar,aperp=aperp)
		mat6 = EPfunc(*self.mesh_mu,kc1=kc1,kc2=kc2,kc3=kc3,apar=apar,aperp=aperp)
		mat7 = Bfunc4(*self.mesh_mu,kc1=kc1,kc2=kc2,kc3=kc3,apar=apar,aperp=aperp)

		EBBshot[j] = np.matmul(np.matmul(np.matmul(np.matmul(np.matmul(mat5,self.gauss_w2)/2.,self.gauss_w2)/2.,self.gauss_w),self.gauss_w),self.gauss_w)/Nk1/Nk2/Nk3
		EBPshot[j] = np.matmul(np.matmul(np.matmul(np.matmul(np.matmul(mat6,self.gauss_w2)/2.,self.gauss_w2)/2.,self.gauss_w),self.gauss_w),self.gauss_w)/Nk1/Nk2/Nk3
		Pshotcov[3*self.ksizep0p2 + self.ksizemu0 + j] = EBPshot[j]
		Bshotcov[3*self.ksizep0p2 + self.ksizemu0 + j] = EBBshot[j]		
                c1cov[3*self.ksizep0p2 + self.ksizemu0 + j] = np.matmul(np.matmul(np.matmul(np.matmul(np.matmul(mat7,self.gauss_w2)/2.,self.gauss_w2)/2.,self.gauss_w),self.gauss_w),self.gauss_w)/Nk1/Nk2/Nk3

        print(x1[self.ksizep0p2:self.ksizep0p2+10])
        print(x1[2*self.ksizep0p2:2*self.ksizep0p2+10])
        print(x1[3*self.ksizep0p2:3*self.ksizep0p2+10])
        print(x1[3*self.ksizep0p2+self.ksizemu0:3*self.ksizep0p2+self.ksizemu0+10])
        print(x1[-2:])


	chi2 =0.
        marg_cov = self.cov + np.outer(EbG3cov,EbG3cov) + sigPshot**2.*np.outer(Pshotcov,Pshotcov) + siga0**2.*np.outer(a0cov,a0cov) + siga2**2.*np.outer(a2cov,a2cov) + sigcs4**2.*np.outer(Ecs4cov,Ecs4cov)+sigcs2**2.*np.outer(Ecs2cov,Ecs2cov)+sigcs0**2.*np.outer(Ecs0cov,Ecs0cov) + sigb4**2.*np.outer(Eb4cov,Eb4cov) + sigBshot**2.*np.outer(Bshotcov,Bshotcov) + sigc1**2.*np.outer(c1cov,c1cov)
        chi2 = np.inner(x1,np.inner(np.linalg.inv(marg_cov),x1));
        chi2 +=np.linalg.slogdet(marg_cov)[1] - self.logdetcov
	chi2 +=(Pshot)**2. + 1.*(Bshot-1.)**2.+1.*(c1)**2./5.**2.+ (b2 - 0.)**2./1.**2. + (bG2 - 0.)**2/1.**2.
        #chi2 += (b2/norm - 0.)**2./1.**2. + (bG2/norm - 0.)**2./1.**2.
        loglkl = -0.5 * chi2
	#print('chi2 PxB=',chi2)
#	chi2=np.dot(x1,np.dot(self.invcov,x1))+(Pshot)**2/0.3**2

        return loglkl
