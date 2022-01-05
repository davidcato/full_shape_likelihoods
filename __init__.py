import numpy as np
from montepython.likelihood_class import Likelihood_prior
from scipy import interpolate
import scipy.integrate as integrate
from fs_utils import Datasets, BkUtils, PkTheory

class full_shape_spectra(Likelihood_prior):

        # initialisation of the class is done within the parent Likelihood_prior. For
        # this case, it does not differ, actually, from the __init__ method in
        # Likelihood class.

        def __init__(self,path,data,command_line):
                """Initialize the full shape likelihood. This loads the data-set and pre-computes a number of useful quantities."""

                # Initialize the likelihood
                Likelihood_prior.__init__(self,path,data,command_line)

                # Load the data
                self.dataset = Datasets(self)

                # Pre-load useful quantities for bispectra
                if self.use_B: 
                        self.bk_utils = BkUtils() 

                # Define nuisance parameter mean and standard deviations
                self.prior_bGamma3 = lambda b1: (23.*(b1-1.)/42., 0.)  
                self.prior_cs0 = 0, 30.
                self.prior_cs2 = 30., 30.
                self.prior_cs4 = 0., 30.
                self.prior_b4 = 500., 500.
                self.prior_c1 = 0., 5.
                self.prior_a0 = 0., self.inv_nbar
                self.prior_a2 = 0., self.inv_nbar
                self.prior_bphi = 1., 5.
                
        def loglkl(self, cosmo, data):
                """Compute the log-likelihood for a given set of cosmological and nuisance parameters. Note that this marginalizes over nuisance parameters that enter the model linearly."""

                # Load cosmological parameters
                h = cosmo.h()
                As = cosmo.A_s()
                norm = 1. # (A_s/A_s_fid)^{1/2}
                fNL = (data.mcmc_parameters['f_{NL}']['current'] * data.mcmc_parameters['f_{NL}']['scale'])
                fNL2 = (data.mcmc_parameters['f^{(2)}_{NL}']['current'] * data.mcmc_parameters['f^{(2)}_{NL}']['scale'])
                
                # Load non-linear nuisance parameters
                i_s=repr(3)
                b1 = (data.mcmc_parameters['b^{('+i_s+')}_1']['current'] *
                data.mcmc_parameters['b^{('+i_s+')}_1']['scale'])
                b2 = (data.mcmc_parameters['b^{('+i_s+')}_2']['current'] *
                data.mcmc_parameters['b^{('+i_s+')}_2']['scale'])
                bG2 = (data.mcmc_parameters['b^{('+i_s+')}_{G_2}']['current'] *
                data.mcmc_parameters['b^{('+i_s+')}_{G_2}']['scale'])
                
                print("FIXING B1 FOR TESTING")
                print(b1)
                b1 = 1.8682
                print(b1)

                ## Define parameter mean and variances   
                mean_bGamma3, std_bGamma3 = self.prior_bGamma3(b1)
                mean_cs0, std_cs0 = self.prior_cs0
                mean_cs2, std_cs2 = self.prior_cs2
                mean_cs4, std_cs4 = self.prior_cs4
                mean_b4, std_b4 = self.prior_b4
                mean_c1, std_c1 = self.prior_c1
                mean_a0, std_a0 = self.prior_a0
                mean_a2, std_a2 = self.prior_a2
                mean_bphi, std_bphi = self.prior_bphi

                # Means
                Pshot = 0.
                Bshot = 1.
                # Standard deviations
                std_Pshot = 1.*self.inv_nbar
                std_Bshot = 1.*self.inv_nbar
                
                # Define local variables 
                dataset = self.dataset
                nP, nQ, nB, nAP = dataset.nP, dataset.nQ, dataset.nB, dataset.nAP
                
                z = self.z
                fz = cosmo.scale_independent_growth_factor_f(z)
                
                # Compute useful quantities for AP parameters
                if self.use_AP or self.use_B:
                        DA_th = cosmo.angular_distance(z)
                        rs_th = cosmo.rs_drag()
                        Hz_th = cosmo.Hubble(z)

                # Create output arrays
                theory_minus_data = np.zeros(3*nP+nB+nQ+nAP)
                deriv_bGamma3, deriv_Pshot, deriv_Bshot, deriv_c1, deriv_a0, deriv_a2, deriv_cs0, deriv_cs2, deriv_cs4, deriv_b4, deriv_bphi = [np.zeros(3*nP+nB+nQ+nAP) for _ in range(11)]

                if self.bin_integration_P:
                        k_grid = np.linspace(np.log(1.e-4),np.log(max(dataset.kPQ)+0.01),100)
                        k_grid = np.exp(k_grid)
                else:
                        k_grid = dataset.kPQ

                # Run CLASS-PT
                all_theory = cosmo.get_pk_mult(k_grid*h,z,len(k_grid))

                ## fNL utilities
                Plintab = -1.*norm**2.*(all_theory[10]/h**2./k_grid**2)*h**3
                P0int = interpolate.InterpolatedUnivariateSpline(k_grid,Plintab,ext=3)

                Azeta = As*2.*np.pi**2.
                Tfunc = lambda k: (P0int(k)/(Azeta*((k*h/0.05)**(cosmo.n_s()-1.))/k**3.))**0.5
                
                #### Pk
                if self.use_P:

                        # Define PkTheory class, used to compute power spectra and derivatives
                        pk_theory = PkTheory(self, all_theory, h, As, fNL, fNL2, norm, fz, k_grid, dataset.kPQ, nP, nQ, Tfunc(k_grid))
                        
                        # Compute theory model for Pl and add to (theory - data)
                        P0, P2, P4 = pk_theory.compute_Pl_oneloop(b1, b2, bG2, mean_bGamma3, mean_cs0, mean_cs2, mean_cs4, mean_b4, mean_a0, mean_a2, self.inv_nbar, Pshot, mean_bphi)
                        theory_minus_data[0*nP:1*nP] = P0 - dataset.P0
                        theory_minus_data[1*nP:2*nP] = P2 - dataset.P2
                        theory_minus_data[2*nP:3*nP] = P4 - dataset.P4

                        # Compute derivatives of Pl with respect to parameters
                        deriv_bGamma3P, deriv_cs0P, deriv_cs2P, deriv_cs4P, deriv_b4P, deriv_PshotP, deriv_a0P, deriv_a2P, deriv_bphiP = pk_theory.compute_Pl_derivatives(b1)
                        
                        # Add to joint derivative vector
                        deriv_bGamma3[:3*nP] = deriv_bGamma3P
                        deriv_cs0[:3*nP] = deriv_cs0P
                        deriv_cs2[:3*nP] = deriv_cs2P
                        deriv_cs4[:3*nP] = deriv_cs4P
                        deriv_b4[:3*nP] = deriv_b4P
                        deriv_Pshot[:3*nP] = deriv_PshotP
                        deriv_a0[:3*nP] = deriv_a0P
                        deriv_a2[:3*nP] = deriv_a2P
                        deriv_bphi[:3*nP] = deriv_bphiP
                        
                #### Q0
                if self.use_Q:
                        
                        # Compute theoretical Q0 model and add to (theory - data)
                        Q0 = pk_theory.compute_Q0_oneloop(b1, b2, bG2, mean_bGamma3, mean_cs0, mean_cs2, mean_cs4, mean_b4, mean_a0, mean_a2, self.inv_nbar, Pshot, mean_bphi)
                        theory_minus_data[3*nP:3*nP+nQ] = Q0 - dataset.Q0

                        # Compute derivatives of Q0 with respect to parameters
                        deriv_bGamma3Q, deriv_cs0Q, deriv_cs2Q, deriv_cs4Q, deriv_b4Q, deriv_PshotQ, deriv_a0Q, deriv_a2Q, deriv_bphiQ = pk_theory.compute_Q0_derivatives(b1)

                        # Add to joint derivative vector
                        deriv_bGamma3[3*nP:3*nP+nQ] = deriv_bGamma3Q
                        deriv_cs0[3*nP:3*nP+nQ] = deriv_cs0Q
                        deriv_cs2[3*nP:3*nP+nQ] = deriv_cs2Q
                        deriv_cs4[3*nP:3*nP+nQ] = deriv_cs4Q
                        deriv_b4[3*nP:3*nP+nQ] = deriv_b4Q
                        deriv_Pshot[3*nP:3*nP+nQ] = deriv_PshotQ
                        deriv_a0[3*nP:3*nP+nQ] = deriv_a0Q
                        deriv_a2[3*nP:3*nP+nQ] = deriv_a2Q
                        deriv_bphi[3*nP:3*nP+nQ] = deriv_bphiQ

                #### AP
                if self.use_AP:  

                        # Compute theoretical AP model and add to (theory - data)
                        A_par = self.rdHfid/(rs_th*Hz_th)
                        A_perp = self.rdDAfid/(rs_th/DA_th)
                        theory_minus_data[-2] = A_par - dataset.alphas[0]
                        theory_minus_data[-1] = A_perp - dataset.alphas[1]

                print("TODO: sort out 1/nbar")
                print("TODO: add Bk module")
                print("TODO: sort Pk/Bk shot")
                print("TODO: what is fNL / fNL2?")
                print("only include bphi if using fNL?")

                #### Bispectrum
                if self.use_B:

                        class BkTheory(object):
                                def __init__(self, options):
                                        """Compute the theoretical power spectrum P(k) and parameter derivatives for a given cosmology and set of nuisance parameters."""
                                        self.options = options
                                        self.dataset = options.dataset
                                
                                def compute_B0_tree(self, b1, b2, bG2):
                                        """Compute the tree-level bispectrum, given the bias parameters."""
            
                                def compute_B0_derivatives(self, b1):
                                        """Compute the derivatives of the power spectrum multipoles with respect to parameters entering the model linearly"""
            
                        bk_theory = BkTheory(self)

                        print("NB: should move BkUtils into Bk class?")

                        # Define local variables
                        kB, dkB = dataset.kB, dataset.dkB
                
                        ### MESSY BELOW HERE!!
                        Ashot = 0.
                        beta = fz/b1

                        P2 = norm**2.*(all_theory[14])*h**3.
                        ng = (1.+Ashot)/self.inv_nbar

                        # IR resummation parameters
                        r_bao = cosmo.rs_drag()*h
                        ks_IR = 0.05

                        P0int = interpolate.InterpolatedUnivariateSpline(k_grid,Plintab,ext=3)
                        Sigma = integrate.quad(lambda k: (4*np.pi)*np.exp(1.*k)*P0int(np.exp(k))*(1.-3*(2*r_bao*np.exp(k)*np.cos(np.exp(k)*r_bao)+(-2+r_bao**2*np.exp(k)**2)*np.sin(r_bao*np.exp(k)))/(np.exp(k)*r_bao)**3)/(3*(2*np.pi)**3.), np.log(2.e-4), np.log(0.2))[0]
        
                        # Wiggly power spectrum
                        Pw = (Plintab-P2)/(np.exp(-k_grid**2.*Sigma)-np.exp(-k_grid**2.*Sigma)*(1+k_grid**2.*Sigma))
                        Pwfunc = interpolate.InterpolatedUnivariateSpline(k_grid,Pw,ext=3)
                        
                        # Non-Wiggly power spectrum
                        Pnw = Plintab - Pw*np.exp(-k_grid**2.*Sigma)
                        Pnwfunc = interpolate.InterpolatedUnivariateSpline(k_grid,Pnw,ext=3)

                        Sigma2 = integrate.quad(lambda k: (4*np.pi)*np.exp(1.*k)*P0int(np.exp(k))*(1.-3*(2*r_bao*np.exp(k)*np.cos(np.exp(k)*r_bao)+(-2+r_bao**2*np.exp(k)**2)*np.sin(r_bao*np.exp(k)))/(np.exp(k)*r_bao)**3)/(3*(2*np.pi)**3.), np.log(2.e-4), np.log(ks_IR))[0]
                        deltaSigma2 = integrate.quad(lambda k: (4*np.pi)*np.exp(1.*k)*P0int(np.exp(k))*(self.bk_utils.j2(np.exp(k)*r_bao))/((2*np.pi)**3.), np.log(2.e-4), np.log(ks_IR))[0]

                        # IR resummed spectra
                        P_IR = lambda k, mu: Pnwfunc(k) +  np.exp(-k**2.*(Sigma2*(1.+2.*fz*mu**2.*(2.+fz)) + deltaSigma2*mu**2.*fz**2.*(mu**2.-1.)))*Pwfunc(k) -(mean_c1*mu**2.)*(k/0.3)**2.*P0int(k)/(b1+fz*mu**2.)
                        P_IRC = lambda k, mu:Pnwfunc(k) +  np.exp(-k**2.*(Sigma2*(1.+2.*fz*mu**2.*(2.+fz)) + deltaSigma2*mu**2.*fz**2.*(mu**2.-1.)))*Pwfunc(k) -(mu**2.)*(k/0.3)**2.*P0int(k)/(b1+fz*mu**2.)

                        # IR resummed spectra
                        P_IR = lambda k, mu: Pnwfunc(k) +  np.exp(-k**2.*(Sigma2*(1.+2.*fz*mu**2.*(2.+fz)) + deltaSigma2*mu**2.*fz**2.*(mu**2.-1.)))*Pwfunc(k) -(mean_c1*mu**2.)*(k/0.3)**2.*P0int(k)/(b1+fz*mu**2.)
                        P_IRC = lambda k, mu:Pnwfunc(k) +  np.exp(-k**2.*(Sigma2*(1.+2.*fz*mu**2.*(2.+fz)) + deltaSigma2*mu**2.*fz**2.*(mu**2.-1.)))*Pwfunc(k) -(mu**2.)*(k/0.3)**2.*P0int(k)/(b1+fz*mu**2.)

                        kmsMpc = 3.33564095198145e-6 # conversion factor

                        # Define coordinate rescaling parameters
                        DA=DA_th/(self.h_fid/h)
                        Hz=Hz_th*(self.h_fid/h)/kmsMpc
                        apar=self.Hz_fid/Hz
                        aperp=DA/self.DA_fid

                        B0 = np.zeros(nB)
                        new_triag = dataset.new_triag

                        Azeta = As*2.*np.pi**2.

                        def B_matrices(k1,k2,k3,mu1,phi,kc1=0,kc2=0,kc3=0,apar=1,aperp=1):
                                ddk1 = dk1/2.
                                ddk2 = dk2/2.
                                ddk3 = dk3/2.
                                kk1 = (kc1+k1*ddk1)
                                kk2 = (kc2+k2*ddk2)
                                kk3 = (kc3+k3*ddk3)
                                xxfunc = (kk3**2.-kk1**2.-kk2**2.)/(2.*kk1*kk2)
                                yyfunc = np.sqrt(np.abs(1.-xxfunc**2.))
                                mu2 = xxfunc*mu1 - np.sqrt(1.-mu1**2.)*yyfunc*np.cos(phi*2.*np.pi)
                                mu3 = -(kk2/kk3)*mu2-(kk1/kk3)*mu1

                                BNG = lambda k1, k2, k3: Azeta**2.*(Tfunc(k1)*Tfunc(k2)*Tfunc(k3)*(18./5.)*(-1./k1**3./k2**3.-1./k3**3./k2**3.-1./k1**3./k3**3.-2./k1**2./k2**2./k3**2.+1/k1/k2**2./k3**3.+1/k1/k3**2./k2**3.+1/k2/k3**2./k1**3.+1/k2/k1**2./k3**3.+1/k3/k1**2./k2**3.+1/k3/k2**2./k1**3.))

                                def BNG2(k1, k2, k3):
                                        phere=27./(743./(7.*(20.*np.pi**2.-193.))-21.);
                                        kt=k1+k2+k3;
                                        e2=k1*k2+k1*k3+k3*k2;
                                        e3=k1*k2*k3;
                                        Dhere=(kt-2.*k1)*(kt-2.*k2)*(kt-2.*k3)
                                        Ghere=2.*e2/3.-(k1**2.+k2**2.+k3**2.)/3.
                                        Norto = (840.*np.pi**2.-7363.-189.*(20.*np.pi**2.-193.))/(29114. - 2940.*np.pi**2.)
                                        BNG2func = Azeta**2.*(18./5.)*Tfunc(k1)*Tfunc(k2)*Tfunc(k3)*(1./(k1**2.*k2**2.*k3**2.))*((1.+phere)*Dhere/e3 -phere*Ghere**3./e3**2.)/Norto
                                        return BNG2func

                                # Coordinate distortion on mu
                                nnu = lambda mu: mu/apar/(np.sqrt(np.abs(mu**2./apar**2. + (1-mu**2.)/aperp**2.)))
                                nnu1, nnu2, nnu3 = nnu(mu1), nnu(mu2), nnu(mu3)

                                # Coordinate distortion on length
                                qq = lambda mu: np.sqrt(np.abs(mu**2/apar**2 + (1.-mu**2)/aperp**2))
                                qq1, qq2, qq3 = qq(mu1), qq(mu2), qq(mu3)

                                # IR resummed spectra
                                PP_IR1, PP_IR2, PP_IR3 = P_IR(kk1*qq1,nnu1), P_IR(kk2*qq2,nnu2), P_IR(kk3*qq3,nnu3)
                                PP_IR1C, PP_IR2C, PP_IR3C = P_IRC(kk1*qq1,nnu1), P_IRC(kk2*qq2,nnu2), P_IRC(kk3*qq3,nnu3)

                                ### Bfunc3
                                zz21 = self.bk_utils.F2(kk1*qq1,kk2*qq2,kk3*qq3,b1,b2,bG2)+b1**3.*beta*((nnu2*kk2*qq2+nnu1*kk1*qq1)/kk3/qq3)**2.*self.bk_utils.G2(kk1*qq1,kk2*qq2,kk3*qq3)+(b1**4.*beta/2.)*(nnu2*kk2*qq2+nnu1*kk1*qq1)*(nnu1*(1.+beta*nnu2**2.)/kk1/qq1 + nnu2*(1.+beta*nnu1**2.)/kk2/qq2)
                                zz22 = self.bk_utils.F2(kk1*qq1,kk3*qq3,kk2*qq2,b1,b2,bG2)+b1**3.*beta*((nnu3*kk3*qq3+nnu1*kk1*qq1)/kk2/qq2)**2.*self.bk_utils.G2(kk1*qq1,kk3*qq3,kk2*qq2)+(b1**4.*beta/2.)*(nnu3*kk3*qq3+nnu1*kk1*qq1)*(nnu1*(1.+beta*nnu3**2.)/kk1/qq1 + nnu3*(1.+beta*nnu1**2.)/kk3/qq3)
                                zz23 = self.bk_utils.F2(kk2*qq2,kk3*qq3,kk1*qq1,b1,b2,bG2)+b1**3.*beta*((nnu2*kk2*qq2+nnu3*kk3*qq3)/kk1/qq1)**2.*self.bk_utils.G2(kk2*qq2,kk3*qq3,kk1*qq1)+(b1**4.*beta/2.)*(nnu2*kk2*qq2+nnu3*kk3*qq3)*(nnu2*(1.+beta*nnu3**2.)/kk2/qq2 + nnu3*(1.+beta*nnu2**2.)/kk3/qq3)

                                FF2func1 = zz21*(1+beta*nnu1**2)*(1.+beta*nnu2**2.)*PP_IR1*kk1*ddk1*PP_IR2*kk2*ddk2*kk3*ddk3 + 1.*0.5*(Bshot/ng)*b1**2.*PP_IR1*kk1*(1.+beta*nnu1**2.*(Bshot+1.*(1.+Pshot))/Bshot + beta**2.*nnu1**4.*1.*(1.+Pshot)/Bshot)*kk2*kk3*ddk1*ddk2*ddk3 + ((1.+Pshot)/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/2.
                                FF2func2 = zz22*(1+beta*nnu1**2)*(1.+beta*nnu3**2.)*PP_IR1*kk1*ddk1*PP_IR3*kk3*ddk3*kk2*ddk2 + 1.*0.5*(Bshot/ng)*b1**2.*PP_IR2*kk2*(1.+beta*nnu2**2.*(Bshot+1.+1.*Pshot)/Bshot + beta**2.*nnu2**4.*1.*(1.+Pshot)/Bshot)*kk1*kk3*ddk1*ddk2*ddk3 + 0.*(1/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/6.
                                FF2func3 = zz23*(1+beta*nnu2**2)*(1.+beta*nnu3**2.)*PP_IR2*kk2*ddk2*PP_IR3*kk3*ddk3*kk1*ddk1 + 1.*0.5*(Bshot/ng)*b1**2.*PP_IR3*kk3*(1.+beta*nnu3**2.*(Bshot+1.+1.*Pshot)/Bshot + beta**2.*nnu3**4.*1.*(1.+Pshot)/Bshot)*kk2*kk1*ddk1*ddk2*ddk3 + 0.*(1/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/6.
                                
                                FF2func1C = zz21*(1+beta*nnu1**2)*(1.+beta*nnu2**2.)*PP_IR1C*kk1*ddk1*PP_IR2C*kk2*ddk2*kk3*ddk3 + 1.*0.5*(Bshot/ng)*b1**2.*PP_IR1C*kk1*(1.+beta*nnu1**2.*(Bshot+2.*(1.+Pshot))/Bshot + beta**2.*nnu1**4.*2.*(1.+Pshot)/Bshot)*kk2*kk3*ddk1*ddk2*ddk3 + ((1.+Pshot)/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/2.
                                FF2func2C = zz22*(1+beta*nnu1**2)*(1.+beta*nnu3**2.)*PP_IR1C*kk1*ddk1*PP_IR3C*kk3*ddk3*kk2*ddk2 + 1.*0.5*(Bshot/ng)*b1**2.*PP_IR2C*kk2*(1.+beta*nnu2**2.*(Bshot+2.+2.*Pshot)/Bshot + beta**2.*nnu2**4.*2.*(1.+Pshot)/Bshot)*kk1*kk3*ddk1*ddk2*ddk3 + 0.*(1/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/6.
                                FF2func3C = zz23*(1+beta*nnu2**2)*(1.+beta*nnu3**2.)*PP_IR2C*kk2*ddk2*PP_IR3C*kk3*ddk3*kk1*ddk1 + 1.*0.5*(Bshot/ng)*b1**2.*PP_IR3C*kk3*(1.+beta*nnu3**2.*(Bshot+2.+2.*Pshot)/Bshot + beta**2.*nnu3**4.*2.*(1.+Pshot)/Bshot)*kk2*kk1*ddk1*ddk2*ddk3 + 0.*(1/ng)**2.*kk1*kk2*kk3*ddk1*ddk2*ddk3/6.

                                if fNL==0 and fNL2==0:
                                        FFnlfunc = 0.
                                else:
                                        FFnlfunc = (fNL*BNG(kk1*qq1,kk2*qq2,kk3*qq3)+fNL2*BNG2(kk1*qq1,kk2*qq2,kk3*qq3))*b1**3.*(1+beta*nnu1**2)*(1.+beta*nnu3**2.)*(1+beta*nnu2**2)*kk1*kk2*kk3*ddk1*ddk2*ddk3

                                B_matrix1 = (2.*FF2func1 + 2.*FF2func2 + 2.*FF2func3 + FFnlfunc)/apar**2./aperp**4.
                                
                                B_matrix2 = b1**2.*(((1.+beta*nnu1**2.)*PP_IR1+PP_IR2*(1.+beta*nnu2**2.)+ PP_IR3*(1.+beta*nnu3**2.))*kk1*kk2*kk3*ddk1*ddk2*ddk3)/apar**2./aperp**4.
                
                                B_matrix3 = (b1**2.*(1.*beta*nnu1**2.*(1.+beta*nnu1**2.)*PP_IR1+PP_IR2*(beta*nnu2**2.)*(1.+beta*nnu2**2.)+ PP_IR3*(beta*nnu3**2.)*(1.+beta*nnu3**2.)) + 2.*self.inv_nbar*(1.+Pshot))*kk1*kk2*kk3*ddk1*ddk2*ddk3/apar**2./aperp**4.
                                
                                B_matrix4 = (2.*FF2func1C + 2.*FF2func2C + 2.*FF2func3C - 2.*FF2func1 - 2.*FF2func2 - 2.*FF2func3)/apar**2./aperp**4.
                                
                                return B_matrix1, B_matrix2, B_matrix3, B_matrix4

                        for j in range(int(nB)):
                                kc1 = kB[new_triag[0][j]]
                                kc2 = kB[new_triag[1][j]]
                                kc3 = kB[new_triag[2][j]]
                                dk1 = dkB
                                dk2 = dkB
                                dk3 = dkB
                                if (kB[new_triag[0][j]]<dkB):
                                        kc1 = 0.0058
                                        dk1  = 0.0084
                                if (kB[new_triag[1][j]]<dkB):
                                        kc2 = 0.0058
                                        dk2  = 0.0084
                                if (kB[new_triag[2][j]]<dkB):
                                        kc3 = 0.0058
                                        dk3  = 0.0084

                                # Idealized bin volume
                                Nk123 = ((kc1+dk1/2.)**2. - (kc1-dk1/2.)**2.)*((kc2+dk2/2.)**2. - (kc2-dk2/2.)**2.)*((kc3+dk3/2.)**2. - (kc3-dk3/2.)**2.)/8.
                                
                                # Compute matrices
                                B_matrix1, B_matrix2, B_matrix3, B_matrix4 = B_matrices(*self.bk_utils.mesh_mu,kc1=kc1,kc2=kc2,kc3=kc3,apar=apar,aperp=aperp)
                                
                                # Sum over angles to compute B0
                                B0[j] = np.matmul(np.matmul(np.matmul(np.matmul(np.matmul(B_matrix1,self.bk_utils.gauss_w2)/2.,self.bk_utils.gauss_w2)/2.,self.bk_utils.gauss_w),self.bk_utils.gauss_w),self.bk_utils.gauss_w)/Nk123

                                # Add to output array
                                theory_minus_data[3*nP+nQ+j] = B0[j]*dataset.discreteness_weights[j] - dataset.B0[j]
                                
                                # Update nuisance parameter covariance
                                derivB_Pshot = np.matmul(np.matmul(np.matmul(np.matmul(np.matmul(B_matrix3,self.bk_utils.gauss_w2)/2.,self.bk_utils.gauss_w2)/2.,self.bk_utils.gauss_w),self.bk_utils.gauss_w),self.bk_utils.gauss_w)/Nk123
                                derivB_Bshot = np.matmul(np.matmul(np.matmul(np.matmul(np.matmul(B_matrix2,self.bk_utils.gauss_w2)/2.,self.bk_utils.gauss_w2)/2.,self.bk_utils.gauss_w),self.bk_utils.gauss_w),self.bk_utils.gauss_w)/Nk123
                                derivB_c1 = np.matmul(np.matmul(np.matmul(np.matmul(np.matmul(B_matrix4,self.bk_utils.gauss_w2)/2.,self.bk_utils.gauss_w2)/2.,self.bk_utils.gauss_w),self.bk_utils.gauss_w),self.bk_utils.gauss_w)/Nk123

                                deriv_Pshot[3*nP+nQ+j] = derivB_Pshot
                                deriv_Bshot[3*nP+nQ+j] = derivB_Bshot		
                                deriv_c1[3*nP+nQ+j] = derivB_c1

                ### COMBINE AND COMPUTE LIKELIHOOD

                print(theory_minus_data[:10])
                print(theory_minus_data[nP:nP+10])
                print(theory_minus_data[2*nP:2*nP+10])
                print(theory_minus_data[3*nP:3*nP+10])
                print(theory_minus_data[3*nP+nQ:3*nP+nQ+10])
                print(theory_minus_data[-2:])

                # Assemble full covariance including nuisance parameter marginalizations
                marg_cov = dataset.cov + std_bGamma3*np.outer(deriv_bGamma3,deriv_bGamma3) + std_Pshot**2.*np.outer(deriv_Pshot,deriv_Pshot) + std_a0**2.*np.outer(deriv_a0,deriv_a0) + std_a2**2.*np.outer(deriv_a2,deriv_a2) + std_cs4**2.*np.outer(deriv_cs4,deriv_cs4)+std_cs2**2.*np.outer(deriv_cs2,deriv_cs2)+std_cs0**2.*np.outer(deriv_cs0,deriv_cs0) + std_b4**2.*np.outer(deriv_b4,deriv_b4) + std_Bshot**2.*np.outer(deriv_Bshot,deriv_Bshot) + std_c1**2.*np.outer(deriv_c1,deriv_c1)  + std_bphi**2.*np.outer(deriv_bphi,deriv_bphi)

                # Compute chi2
                chi2 = np.inner(theory_minus_data,np.inner(np.linalg.inv(marg_cov),theory_minus_data))
                
                # Correct normalizations
                chi2 += np.linalg.slogdet(marg_cov)[1] - dataset.logdetcov
                
                # Add parameter priors
                chi2 += (b2-0.)**2./1.**2. + (bG2-0.)**2./1.**2.
                
                return -0.5*chi2
