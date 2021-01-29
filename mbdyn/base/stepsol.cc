/* $Header$ */
/*
 * MBDyn (C) is a multibody analysis code.
 * http://www.mbdyn.org
 *
 * Copyright (C) 1996-2017
 *
 * Pierangelo Masarati	<masarati@aero.polimi.it>
 * Paolo Mantegazza	<mantegazza@aero.polimi.it>
 *
 * Dipartimento di Ingegneria Aerospaziale - Politecnico di Milano
 * via La Masa, 34 - 20156 Milano, Italy
 * http://www.aero.polimi.it
 *
 * Changing this copyright notice is forbidden.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation (version 2 of the License).
 *
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 */

 /*
  *
  * Copyright (C) 2003-2017
  * Giuseppe Quaranta	<quaranta@aero.polimi.it>
  *
  * classi che impementano l'integrazione al passo
  */

#include "mbconfig.h"           /* This goes first in every *.c,*.cc file */

#include <limits>

#include "schurdataman.h"
#include "external.h"
#include "ls.h"
#include "solver.h"
#include "invsolver.h"
#include "stepsol.h"

StepIntegrator::StepIntegrator(const integer MaxIt,
		const doublereal dT,
		const doublereal dSolutionTol,
		const integer stp,
		const integer sts)
: pDM(0),
pDofs(0),
outputPred(false),
MaxIters(MaxIt),
dTol(dT),
dSolTol(dSolutionTol),
steps(stp),
unkstates(sts)
{
	NO_OP;
}

StepIntegrator::~StepIntegrator(void)
{
	NO_OP;
}

void
StepIntegrator::SetDataManager(DataManager* pDatMan)
{
	pDM = pDatMan;
	pDofs = &pDM->GetDofs();
}

integer
StepIntegrator::GetIntegratorNumPreviousStates(void) const
{
	return steps;
}

integer
StepIntegrator::GetIntegratorNumUnknownStates(void) const
{
	return unkstates;
}

integer
StepIntegrator::GetIntegratorMaxIters(void) const
{
	return MaxIters;
}

doublereal
StepIntegrator::GetIntegratorDTol(void) const
{
	return dTol;
}

doublereal
StepIntegrator::GetIntegratorDSolTol(void) const
{
	return dSolTol;
}

void
StepIntegrator::OutputTypes(const bool fpred)
{
	outputPred  = fpred;
}

void
StepIntegrator::SetDriveHandler(const DriveHandler* /* pDH */ )
{
	NO_OP;
}

#include "stepsol.hc"

ImplicitStepIntegrator::ImplicitStepIntegrator(const integer MaxIt,
		const doublereal dT,
		const doublereal dSolutionTol,
		const integer stp,
		const integer sts,
		const bool bmod_res_test)
: StepIntegrator(MaxIt, dT, dSolutionTol, stp, sts),
bEvalProdCalledFirstTime(true),
pXCurr(0),
pXPrimeCurr(0),
bModResTest(bmod_res_test)
{
	NO_OP;
}

ImplicitStepIntegrator::~ImplicitStepIntegrator(void)
{
	NO_OP;
}

void
ImplicitStepIntegrator::EvalProd(doublereal Tau, const VectorHandler& f0,
	const VectorHandler& w, VectorHandler& z) const
{
	/* matrix-free product
         *
         * J(XCurr) * w = -||w|| * (Res(XCurr + sigma * Tau * w/||w||) - f0) / (sigma * Tau)
         *
         */
	if (bEvalProdCalledFirstTime) {
		XTau.Resize(w.iGetSize());
		SavedState.Resize(w.iGetSize());
		SavedDerState.Resize(w.iGetSize());
		bEvalProdCalledFirstTime = false;
	}

	SavedState = *pXCurr;
	SavedDerState = *pXPrimeCurr;

	/* if w = 0; J * w = 0 */
	ASSERT(pDM != NULL);

	doublereal nw = w.Norm();
        if (nw < std::numeric_limits<doublereal>::epsilon()) {
                z.Reset();
                return;
        }
        doublereal sigma = pXCurr->InnerProd(w);
        sigma /=  nw;
        if (fabs(sigma) > std::numeric_limits<doublereal>::epsilon()) {
                doublereal xx = (fabs( sigma) <= 1.) ? 1. : fabs(sigma);
                Tau = copysign(Tau*xx, sigma);
        }
        Tau /= nw;
#ifdef DEBUG_ITERATIVE
	std::cout << "Tau " << Tau << std::endl;
#endif /* DEBUG_ITERATIVE */

	XTau.Reset();
	z.Reset();
        XTau.ScalarMul(w, Tau);
	Update(&XTau);
#ifdef  USE_EXTERNAL
        External::SendFreeze();
#endif /* USE_EXTERNAL */
	/* deal with throwing elements: do not honor their requests while perfoming matrix free update */
	try {
		Residual(&z);
	}
	catch (DataManager::ChangedEquationStructure& e) {
	}
	XTau.ScalarMul(XTau, -1.);

	/* riporta tutto nelle condizioni inziali */
#if 0
	Update(&XTau);
#endif
	*pXCurr = SavedState;
	*pXPrimeCurr = SavedDerState;
	pDM->Update();
	z -= f0;
	z.ScalarMul(z, -1./Tau);
}

/* scale factor for tests */
doublereal
ImplicitStepIntegrator::TestScale(const NonlinearSolverTest *pTest, doublereal& dCoef) const
{
	dCoef = 1.;

	if (bModResTest) {
#ifdef USE_MPI
#warning "ImplicitStepIntegrator::TestScale() not available with Schur solution"
#endif /* USE_MPI */

		doublereal dXPr = 0.;

		DataManager::DofIterator_const CurrDof = pDofs->begin();

	   	for (int iCntp1 = 1; iCntp1 <= pXPrimeCurr->iGetSize();
			iCntp1++, ++CurrDof)
		{
			ASSERT(CurrDof != pDofs->end());

			if (CurrDof->Order == DofOrder::DIFFERENTIAL) {
				doublereal d = pXPrimeCurr->operator()(iCntp1);
				doublereal d2 = d*d;

				doublereal ds = pTest->dScaleCoef(iCntp1);
				doublereal ds2 = ds*ds;
				d2 *= ds2;

				dXPr += d2;
			}
			/* else if ALGEBRAIC: non aggiunge nulla */
		}

	   	return 1./(1. + dXPr);

	} else {
		return 1.;
	}
}


DerivativeSolver::DerivativeSolver(const doublereal Tl,
		const doublereal dSolTl,
		const doublereal dC,
		const integer iMaxIt,
		const bool bmod_res_test,
		const integer iMaxIterCoef,
		const doublereal dFactorCoef)
: ImplicitStepIntegrator(iMaxIt, Tl, dSolTl, 1, 1, bmod_res_test),
dCoef(dC),
iMaxIterCoef(iMaxIterCoef),
dFactorCoef(dFactorCoef)
{
	NO_OP;
}

DerivativeSolver::~DerivativeSolver(void)
{
	NO_OP;
}

doublereal
DerivativeSolver::Advance(Solver* pS,
		const doublereal TStep,
		const doublereal /* dAph */,
		const StepChange /* StType */,
		std::deque<MyVectorHandler*>& qX,
		std::deque<MyVectorHandler*>& qXPrime,
		MyVectorHandler*const pX,
		MyVectorHandler*const pXPrime,
		integer& EffIter,
		doublereal& Err,
		doublereal& SolErr)
{
	/* no predizione */
	ASSERT(pDM != NULL);

	/* Make a deep copy of the current state in order to restore it later */
	MyVectorHandler X(*pX);
	MyVectorHandler XPrime(*pXPrime);

	pXCurr = &X;
	pXPrimeCurr = &XPrime;

	try {
		pDM->LinkToSolution(*pXCurr, *pXPrimeCurr);

		bool bConverged = false;
		const doublereal dInitialCoef = dCoef;
		doublereal dCoefBest = dCoef;
		doublereal dResErrMin = std::numeric_limits<doublereal>::max();
		doublereal dSolErrMin = dResErrMin;
		const integer iMaxPowerCoef = iMaxIterCoef > 0 ? 2 * iMaxIterCoef + 1 : 0;
                integer MaxIterFact = 1;

		for (int i = 0; i <= iMaxPowerCoef; ++i) {
			const bool bLastChance = i == iMaxPowerCoef;

			try {
				Err = 0.;
                                SolErr = 0.;

				pS->pGetNonlinearSolver()->Solve(this,
					pS,
                                                                 MaxIterFact * MaxIters,
					dTol,
					EffIter,
					Err,
					dSolTol,
					SolErr);
				bConverged = true;
			} catch (NonlinearSolver::NoConvergence& e) {
				if (bLastChance) {
					throw;
				}
			} catch (NonlinearSolver::ErrSimulationDiverged& e) {
				if (bLastChance) {
					throw;
				}
			} catch (LinearSolver::ErrFactor& e) {
                                pDM->GetSolver()->pGetSolutionManager()->MatrReset();

				if (bLastChance) {
					throw;
				}
			}

			if (bConverged) {
				break;
			}

			/* Save smallest residual error and corresponding derivative coefficient. */
			if (Err < dResErrMin) {
				dResErrMin = Err;
				dSolErrMin = SolErr;
				dCoefBest = dCoef;
			}

                        /* Restore the previous state after initial assembly. */
                        
			*pXCurr = *pX;
			*pXPrimeCurr = *pXPrime;

			pDM->LinkToSolution(*pXCurr, *pXPrimeCurr);
                        pDM->DerivativesUpdate(); /* has to be called here because the first residual of the nonlinear solver will be incorrect otherwise */

#ifdef DEBUG
                        for (integer i = 1; i <= pXCurr->iGetSize(); ++i) {
                            DofOrder::Order eOrder = pDM->GetDofType(i);
                            
                            if (eOrder == DofOrder::DIFFERENTIAL && pXCurr->dGetCoef(i) != pX->dGetCoef(i)) {
                                DEBUGCOUT("warning: XCurr(" << i << ") = " << pXCurr->dGetCoef(i) << " X(i)=" << pX->dGetCoef(i) << std::endl);
                            }

                            if (eOrder == DofOrder::ALGEBRAIC && pXPrimeCurr->dGetCoef(i) != pXPrime->dGetCoef(i)) {
                                DEBUGCOUT("warning: XPrimeCurr(" << i << ") = " << pXPrimeCurr->dGetCoef(i) << " XPrime(i)=" << pXPrime->dGetCoef(i) << std::endl);
                            }
                        }
#endif

			/* Try different values for derivatives coefficient. */
			if (i < iMaxIterCoef) {
				dCoef *= dFactorCoef;
			} else if (i == iMaxIterCoef) {
				dCoef = dInitialCoef / dFactorCoef;
			} else if (i < 2 * iMaxIterCoef) {
				dCoef /= dFactorCoef;
			} else {
				/* Convergence could not be achieved with any coefficient.
				 * Choose those coefficient with smallest residual error 
				 * and increase the tolerance, so it will converge in any case. */
				const doublereal dSafetyFactor = 1.01;

				dCoef = dCoefBest;
				dTol = dSafetyFactor * dResErrMin;
				dSolTol = dSafetyFactor * dSolErrMin;
                                MaxIterFact = 2;
			}

			silent_cout("Derivatives(" << i + 1  << '/' << 2 * iMaxIterCoef + 1
				<< ") t=" << pDM->dGetTime()
				<< " coef=" << dCoef / TStep
				<< " tol=" << dTol
				<< std::endl);
		}
		/* if it gets here, it surely converged */
		pDM->AfterConvergence();

		*pX = *pXCurr;
		*pXPrime = *pXPrimeCurr;

                pDM->LinkToSolution(*pX, *pXPrime);

		pXCurr = 0;
		pXPrimeCurr = 0;
	} catch (...) {
		/* Clean up pointers to local variables */
                pDM->LinkToSolution(*pX, *pXPrime);
		pXCurr = 0;
		pXPrimeCurr = 0;
		throw;
	}

	return Err;
}

void
DerivativeSolver::Residual(VectorHandler* pRes) const
{
	ASSERT(pDM != NULL);
	pDM->AssRes(*pRes, dCoef);
}

void
DerivativeSolver::Jacobian(MatrixHandler* pJac) const
{
	ASSERT(pDM != NULL);
	pDM->AssJac(*pJac, dCoef);
}

void
DerivativeSolver::UpdateDof(const int DCount,
		const DofOrder::Order Order,
		const VectorHandler* const pSol) const
{
	doublereal d = pSol->operator()(DCount);
	if (Order == DofOrder::DIFFERENTIAL) {
		pXPrimeCurr->IncCoef(DCount, d);

#if 1 /* FIXME: update state derivatives only */
		pXCurr->IncCoef(DCount, dCoef*d);
#endif

	} else {
		pXCurr->IncCoef(DCount, d);
#if 1 /* FIXME: update state only */
		pXPrimeCurr->IncCoef(DCount, dCoef*d);
#endif
	}
	//std::cout<<"DerivateUpdate, DCount = "<< DCount <<"; Order = "<< Order <<"; d = "<< d <<"; pXCurr = "<<pXCurr->operator()(DCount)<<std::endl;
	//std::cout<<"DerivateUpdate, DCount = "<< DCount <<"; Order = "<< Order <<"; pXPrimeCurr = "<<pXPrimeCurr->operator()(DCount)<<std::endl;
}

void
DerivativeSolver::Update(const VectorHandler* pSol) const
{
	DEBUGCOUTFNAME("DerivativeSolver::Update");
	ASSERT(pDM != NULL);

	UpdateLoop(this, &DerivativeSolver::UpdateDof, pSol);
	pDM->DerivativesUpdate();
}

/* scale factor for tests */
doublereal
DerivativeSolver::TestScale(const NonlinearSolverTest *pTest, doublereal& dAlgebraicEqu) const
{
	dAlgebraicEqu = dCoef;
	return 1.;
}


StepNIntegrator::StepNIntegrator(const integer MaxIt,
		const doublereal dT,
		const doublereal dSolutionTol,
		const integer stp,
		const bool bmod_res_test)
: ImplicitStepIntegrator(MaxIt, dT, dSolutionTol, stp, 1, bmod_res_test),
db0Differential(0.),
db0Algebraic(0.)
{
	NO_OP;
}

StepNIntegrator::~StepNIntegrator(void)
{
	NO_OP;
}

void
StepNIntegrator::Residual(VectorHandler* pRes) const
{
	ASSERT(pDM != NULL);
	pDM->AssRes(*pRes, db0Differential);
}

#include "naivemh.h"
void
StepNIntegrator::Jacobian(MatrixHandler* pJac) const
{
	ASSERT(pDM != NULL);
	pDM->AssJac(*pJac, db0Differential);

	// Finite difference check of Jacobian matrix
	// Uncomment this whenever you need to debug your new Jacobian
	// NOTE: might not be safe!
	if (pDM->bFDJac()) {
 		NaiveMatrixHandler fdjac(pJac->iGetNumRows());
 		fdjac.Reset();
 		MyVectorHandler basesol(pJac->iGetNumRows());
 		MyVectorHandler incsol(pJac->iGetNumRows());
 		MyVectorHandler inc(pJac->iGetNumRows());
 		Residual(&basesol);
 		doublereal ddd = 0.001;
 		for (integer i = 1; i <= pJac->iGetNumRows(); i++) {
 			incsol.Reset();
 			inc.Reset();
 			inc.PutCoef(i, ddd);
 			Update(&inc);
 			// std::cerr << pXPrimeCurr->operator()(30) << std::endl;
 			pDM->AssRes(incsol, db0Differential);
 			inc.Reset();
 			inc.PutCoef(i, -ddd);
 			Update(&inc);
 			incsol -= basesol;
 			incsol *= (1./(-ddd));
 			for (integer j = 1; j <= pJac->iGetNumCols(); j++) {
 				fdjac.PutCoef(j, i, std::abs(incsol(j)) > 1.E-100 ? incsol(j) : 0.);
 			}
 		}

 		std::cerr << "\nxxxxxxxxxxxxxxx\n" << std::endl;
 		std::cerr << *pJac << std::endl;
 		std::cerr << "\n---------------\n" << std::endl;
 		std::cerr << fdjac << std::endl;
 		std::cerr << "\n===============\n" << std::endl;
	}
}

void
StepNIntegrator::UpdateDof(const int DCount,
	const DofOrder::Order Order,
	const VectorHandler* const pSol) const
{
	doublereal d = pSol->operator()(DCount);
	if (Order == DofOrder::DIFFERENTIAL) {
		pXPrimeCurr->IncCoef(DCount, d);

		/* Nota: b0Differential e b0Algebraic
		 * possono essere distinti;
		 * in ogni caso sono calcolati
		 * dalle funzioni di predizione
		 * e sono dati globali */
		pXCurr->IncCoef(DCount, db0Differential*d);

	} else {
		pXCurr->IncCoef(DCount, d);
		pXPrimeCurr->IncCoef(DCount, db0Algebraic*d);
	}
	
	//std::cout<<"Update, DCount = "<< DCount <<"; Order = "<< Order <<"; d = "<< d <<"; pXCurr = "<<pXCurr->operator()(DCount)<<std::endl;
	//std::cout<<"Update, DCount = "<< DCount <<"; Order = "<< Order <<"; pXPrimeCurr = "<<pXPrimeCurr->operator()(DCount)<<std::endl;
	
}

void
StepNIntegrator::Update(const VectorHandler* pSol) const
{
	DEBUGCOUTFNAME("StepNIntegrator::Update");
	ASSERT(pDM != NULL);

	UpdateLoop(this, &StepNIntegrator::UpdateDof, pSol);
	pDM->Update();
}

doublereal StepNIntegrator::TestScale(const NonlinearSolverTest *pTest, doublereal& dAlgebraicEqu) const
{
	const doublereal dDiffEqu = ImplicitStepIntegrator::TestScale(pTest, dAlgebraicEqu);
	dAlgebraicEqu = db0Differential;

	return dDiffEqu;
}

/* StepNIntegrator - end */


/* Step1Integrator - begin */

Step1Integrator::Step1Integrator(const integer MaxIt,
		const doublereal dT,
		const doublereal dSolutionTol,
		const bool bmod_res_test)
: StepNIntegrator(MaxIt, dT, dSolutionTol, 1, bmod_res_test),
pXPrev(NULL),
pXPrimePrev(NULL)
{
	NO_OP;
}

Step1Integrator::~Step1Integrator(void)
{
	NO_OP;
}

/* predizione valida per tutti i metodi del second'ordine
  a patto di utilizzare le giuste funzioni implementate per
  ciascun metodo
  */

void Step1Integrator::PredictDof(const int DCount,
	const DofOrder::Order Order,
	const VectorHandler* const pSol) const
{
	if (Order == DofOrder::DIFFERENTIAL) {
		doublereal dXnm1 = pXPrev->operator()(DCount);
		doublereal dXPnm1 = pXPrimePrev->operator()(DCount);
		doublereal dXPn = dPredDer(dXnm1, dXPnm1);
		doublereal dXn = dPredState(dXnm1, dXPn, dXPnm1);
		pXPrimeCurr->PutCoef(DCount, dXPn);
		pXCurr->PutCoef(DCount, dXn);

	} else if (Order == DofOrder::ALGEBRAIC) {
		doublereal dXnm1 = pXPrev->operator()(DCount);
		doublereal dXInm1 =
			pXPrimePrev->operator()(DCount);

		doublereal dXn = dPredDerAlg(dXInm1, dXnm1);
		doublereal dXIn = dPredStateAlg(dXInm1, dXn, dXnm1);

		pXCurr->PutCoef(DCount, dXn);
		pXPrimeCurr->PutCoef(DCount, dXIn);

	} else {
		silent_cerr("Step1Integrator::"
			"PredictDof(): "
			"unknown order for local dof "
			<< DCount << std::endl);
		throw ErrGeneric(MBDYN_EXCEPT_ARGS);
	}
	
	//std::cout<<"Predict, DCount = "<< DCount <<"; Order = "<< Order << "; pXPrev = "<<pXPrev->operator()(DCount)<<"; pXCurr = "<<pXCurr->operator()(DCount)<<std::endl;
	//std::cout<<"Predict, DCount = "<< DCount <<"; Order = "<< Order << "; pXPrimePrev = "<<pXPrimePrev->operator()(DCount)<<"; pXPrimeCurr = "<<pXPrimeCurr->operator()(DCount)<<std::endl;
	
}


void
Step1Integrator::Predict(void)
{
   	DEBUGCOUTFNAME("Step1Integrator::Predict");
   	ASSERT(pDM != NULL);
	UpdateLoop(this, &Step1Integrator::PredictDof);
}

doublereal
Step1Integrator::Advance(Solver* pS,
		const doublereal TStep,
		const doublereal dAph, const StepChange StType,
		std::deque<MyVectorHandler*>& qX,
	 	std::deque<MyVectorHandler*>& qXPrime,
		MyVectorHandler*const pX,
 		MyVectorHandler*const pXPrime,
		integer& EffIter,
		doublereal& Err,
		doublereal& SolErr)
{
	ASSERT(pDM != NULL);
	pXCurr  = pX;
	pXPrev  = qX[0];

	pXPrimeCurr  = pXPrime;
	pXPrimePrev  = qXPrime[0];

	/* predizione */
	SetCoef(TStep, dAph, StType);
	Predict();
	pDM->LinkToSolution(*pXCurr, *pXPrimeCurr);
      	pDM->AfterPredict();

#ifdef DEBUG
      	integer iNumDofs = pDM->iGetNumDofs();
	if (outputPred) {
		std::cout << "After prediction, time=" << pDM->dGetTime() << std::endl;
		std::cout << "Dof:      |    XCurr  ";
		for (unsigned idx = 0; idx < qX.size(); idx++) {
			std::cout << "|  XPrev[" << idx << "] ";
		}
		std::cout << "|   XPrime  ";
		for (unsigned idx = 0; idx < qXPrime.size(); idx++) {
			std::cout << "| XPPrev[" << idx << "] ";
		}
		std::cout << "|" << std::endl;
		for (int iTmpCnt = 1; iTmpCnt <= iNumDofs; iTmpCnt++) {
    			std::cout << std::setw(8) << iTmpCnt << ": ";
			std::cout << std::setw(12) << pX->operator()(iTmpCnt);
			for (unsigned int ivec = 0; ivec < qX.size(); ivec++) {
				std::cout << std::setw(12)
				<< (qX[ivec])->operator()(iTmpCnt);
			}
			std::cout << std::setw(12) << pXPrime->operator()(iTmpCnt);
			for (unsigned int ivec = 0; ivec < qXPrime.size(); ivec++) {
				std::cout << std::setw(12)
				<< (qXPrime[ivec])->operator()(iTmpCnt);
			}
			std::cout << " " << pDM->DataManager::GetDofDescription(iTmpCnt) << std::endl;
 		}
	}
#endif /* DEBUG */

	Err = 0.;
	pS->pGetNonlinearSolver()->Solve(this, pS, MaxIters, dTol,
    			EffIter, Err, dSolTol, SolErr);

	/* if it gets here, it surely converged */
	pDM->AfterConvergence();

	return Err;
}

/* Step1Integrator - end */


/* Step2Integrator - begin */

Step2Integrator::Step2Integrator(const integer MaxIt,
		const doublereal dT,
		const doublereal dSolutionTol,
		const bool bmod_res_test)
: StepNIntegrator(MaxIt, dT, dSolutionTol, 2, bmod_res_test),
pXPrev(NULL),
pXPrev2(NULL),
pXPrimePrev(NULL),
pXPrimePrev2(NULL)
{
	NO_OP;
}

Step2Integrator::~Step2Integrator(void)
{
	NO_OP;
}

/* predizione valida per tutti i metodi del second'ordine
  a patto di utilizzare le giuste funzioni implementate per
  ciascun metodo
  */
void Step2Integrator::PredictDof(const int DCount,
	const DofOrder::Order Order,
	const VectorHandler* const pSol) const
{
	if (Order == DofOrder::DIFFERENTIAL) {
		doublereal dXnm1 = pXPrev->operator()(DCount);
		doublereal dXnm2 = pXPrev2->operator()(DCount);
		doublereal dXPnm1 = pXPrimePrev->operator()(DCount);

		doublereal dXPnm2 =
			pXPrimePrev2->operator()(DCount);
		doublereal dXPn = dPredDer(dXnm1, dXnm2,
				dXPnm1, dXPnm2);
		doublereal dXn = dPredState(dXnm1, dXnm2,
				dXPn, dXPnm1, dXPnm2);

		pXPrimeCurr->PutCoef(DCount, dXPn);
		pXCurr->PutCoef(DCount, dXn);

	} else if (Order == DofOrder::ALGEBRAIC) {
		doublereal dXnm1 = pXPrev->operator()(DCount);
		doublereal dXnm2 = pXPrev2->operator()(DCount);
		doublereal dXInm1 =
			pXPrimePrev->operator()(DCount);

		doublereal dXn = dPredDerAlg(dXInm1,
				dXnm1, dXnm2);
		doublereal dXIn = dPredStateAlg(dXInm1,
				dXn, dXnm1, dXnm2);

		pXCurr->PutCoef(DCount, dXn);
		pXPrimeCurr->PutCoef(DCount, dXIn);

	} else {
		silent_cerr("Step2Integrator::"
			"PredictDof(): "
			"unknown order for local dof "
			<< DCount << std::endl);
		throw ErrGeneric(MBDYN_EXCEPT_ARGS);
	}
	
	//std::cout<<"Predict, DCount = "<< DCount <<"; Order = "<< Order << "; pXPrev2 = "<<pXPrev2->operator()(DCount) << "; pXPrev = "<<pXPrev->operator()(DCount)<<"; pXCurr = "<<pXCurr->operator()(DCount)<<std::endl;
	//std::cout<<"Predict, DCount = "<< DCount <<"; Order = "<< Order << "; pXPrimePrev2 = "<<pXPrimePrev2->operator()(DCount) << "; pXPrimePrev = "<<pXPrimePrev->operator()(DCount)<<"; pXPrimeCurr = "<<pXPrimeCurr->operator()(DCount)<<std::endl;
	
}

void
Step2Integrator::Predict(void)
{
   	DEBUGCOUTFNAME("Step2Integrator::Predict");
   	ASSERT(pDM != NULL);
	UpdateLoop(this, &Step2Integrator::PredictDof);
}

doublereal
Step2Integrator::Advance(Solver* pS,
		const doublereal TStep,
		const doublereal dAph, const StepChange StType,
		std::deque<MyVectorHandler*>& qX,
	 	std::deque<MyVectorHandler*>& qXPrime,
		MyVectorHandler*const pX,
		MyVectorHandler*const pXPrime,
		integer& EffIter,
		doublereal& Err,
		doublereal& SolErr)
{
	ASSERT(pDM != NULL);
	pXCurr  = pX;
	pXPrev  = qX[0];
	pXPrev2 = qX[1];

	pXPrimeCurr  = pXPrime;
	pXPrimePrev  = qXPrime[0];
	pXPrimePrev2 = qXPrime[1];

	/* predizione */
	SetCoef(TStep, dAph, StType);
	Predict();
	pDM->LinkToSolution(*pXCurr, *pXPrimeCurr);
      	pDM->AfterPredict();

#ifdef DEBUG
	integer iNumDofs = pDM->iGetNumDofs();
	if (outputPred) {
		std::cout << "After prediction, time=" << pDM->dGetTime() << std::endl;
		std::cout << "Dof:      |    XCurr  ";
		for (unsigned idx = 0; idx < qX.size(); idx++) {
			std::cout << "|  XPrev[" << idx << "] ";
		}
		std::cout << "|   XPrime  ";
		for (unsigned idx = 0; idx < qXPrime.size(); idx++) {
			std::cout << "| XPPrev[" << idx << "] ";
		}
		std::cout << "|" << std::endl;
		for (int iTmpCnt = 1; iTmpCnt <= iNumDofs; iTmpCnt++) {
    			std::cout << std::setw(8) << iTmpCnt << ": ";
			std::cout << std::setw(12) << pX->operator()(iTmpCnt);
			for (unsigned int ivec = 0; ivec < qX.size(); ivec++) {
				std::cout << std::setw(12)
					<< (qX[ivec])->operator()(iTmpCnt);
			}
			std::cout << std::setw(12) << pXPrime->operator()(iTmpCnt);
			for (unsigned int ivec = 0; ivec < qXPrime.size(); ivec++) {
				std::cout << std::setw(12)
					<< (qXPrime[ivec])->operator()(iTmpCnt);
			}
			std::cout << " " << pDM->DataManager::GetDofDescription(iTmpCnt) << std::endl;
 		}
	}
#endif /* DEBUG */

	Err = 0.;
	pS->pGetNonlinearSolver()->Solve(this, pS, MaxIters, dTol,
    			EffIter, Err, dSolTol, SolErr);

	/* if it gets here, it surely converged */
	pDM->AfterConvergence();

	return Err;
}

/* Step2Integrator - end */

/* Inverse Dynamics - Begin */

/*
 *
 * Portions Copyright (C) 2008
 * Alessandro Fumagalli
 *
 * <alessandro.fumagalli@polimi.it>
 *
 */

InverseDynamicsStepSolver::InverseDynamicsStepSolver(const integer MaxIt,
		const doublereal dT,
		const doublereal dSolutionTol,
		const integer stp,
		const integer sts,
		const bool bmod_res_test)
: StepIntegrator(MaxIt, dT, dSolutionTol, stp, sts),
XTau(0),
SavedState(0),
SavedDerState(0),
bEvalProdCalledFirstTime(true),
iOrder(InverseDynamics::UNDEFINED),
m_bJacobian(true),
pXCurr(0),
pXPrimeCurr(0),
pXPrimePrimeCurr(0),
pLambdaCurr(0),
bModResTest(bmod_res_test)
{
	return;
}

InverseDynamicsStepSolver::~InverseDynamicsStepSolver(void)
{
	NO_OP;
}

void
InverseDynamicsStepSolver::EvalProd(doublereal Tau, const VectorHandler& f0,
	const VectorHandler& w, VectorHandler& z) const
{
	/* matrix-free product
         *
         * J(XCurr) * w = -||w|| * (Res(XCurr + sigma * Tau * w/||w||) - f0) / (sigma * Tau)
         *
         */
	if (bEvalProdCalledFirstTime) {
		XTau.Resize(w.iGetSize());
		SavedState.Resize(w.iGetSize());
		SavedDerState.Resize(w.iGetSize());
		bEvalProdCalledFirstTime = false;
	}

	SavedState = *pXCurr;
	SavedDerState = *pXPrimeCurr;

	/* if w = 0; J * w = 0 */
	ASSERT(pDM != NULL);

	doublereal nw = w.Norm();
        if (nw < std::numeric_limits<doublereal>::epsilon()) {
                z.Reset();
                return;
        }
        doublereal sigma = pXCurr->InnerProd(w);
        sigma /=  nw;
        if (fabs(sigma) > std::numeric_limits<doublereal>::epsilon()) {
                doublereal xx = (fabs( sigma) <= 1.) ? 1. : fabs(sigma);
                Tau = copysign(Tau*xx, sigma);
        }
        Tau /= nw;
#ifdef DEBUG_ITERATIVE
	std::cout << "Tau " << Tau << std::endl;
#endif /* DEBUG_ITERATIVE */

	XTau.Reset();
	z.Reset();
        XTau.ScalarMul(w, Tau);
	Update(&XTau);
#ifdef  USE_EXTERNAL
        External::SendFreeze();
#endif /* USE_EXTERNAL */
	/* deal with throwing elements: do not honor their requests while perfoming matrix free update */
	try {
		Residual(&z);
	}
	catch (DataManager::ChangedEquationStructure& e) {
	}
	XTau.ScalarMul(XTau, -1.);

	/* riporta tutto nelle condizioni inziali */
#if 0
	Update(&XTau);
#endif
	*pXCurr = SavedState;
	*pXPrimeCurr = SavedDerState;
	pDM->Update();
	z -= f0;
	z.ScalarMul(z, -1./Tau);
}

/* scale factor for tests */
doublereal
InverseDynamicsStepSolver::TestScale(const NonlinearSolverTest *pTest, doublereal& dCoef) const
{
	dCoef = 1.;

	if (bModResTest) {
#ifdef USE_MPI
#warning "InverseDynamicsStepSolver::TestScale() not available with Schur solution"
#endif /* USE_MPI */

		doublereal dXPr = 0.;

		DataManager::DofIterator_const CurrDof = pDofs->begin();

	   	for (int iCntp1 = 1; iCntp1 <= pXPrimeCurr->iGetSize();
			iCntp1++, ++CurrDof)
		{
			ASSERT(CurrDof != pDofs->end());

			if (CurrDof->Order == DofOrder::DIFFERENTIAL) {
				doublereal d = pXPrimeCurr->operator()(iCntp1);
				doublereal d2 = d*d;

				doublereal ds = pTest->dScaleCoef(iCntp1);
				doublereal ds2 = ds*ds;
				d2 *= ds2;

				dXPr += d2;
			}
			/* else if ALGEBRAIC: non aggiunge nulla */
		}

	   	return 1./(1. + dXPr);

	} else {
		return 1.;
	}
}

void
InverseDynamicsStepSolver::SetOrder(InverseDynamics::Order iOrder)
{
	this->iOrder = iOrder;
}

InverseDynamics::Order
InverseDynamicsStepSolver::GetOrder(void) const
{
	return iOrder;
}

bool
InverseDynamicsStepSolver::bJacobian(void) const
{
	return m_bJacobian;
}

doublereal
InverseDynamicsStepSolver::Advance(InverseSolver* pS,
		const doublereal TStep,
		const StepChange StType,
		MyVectorHandler*const pX,
 		MyVectorHandler*const pXPrime,
 		MyVectorHandler*const pXPrimePrime,
 		MyVectorHandler*const pLambda,
		integer& EffIter,
		doublereal& Err,
		doublereal& SolErr)
{
	ASSERT(pDM != NULL);
	pXCurr = pX;
	pXPrimeCurr = pXPrime;
	pXPrimePrimeCurr = pXPrimePrime;
	pLambdaCurr = pLambda;

	pDM->LinkToSolution(*pXCurr, *pXPrimeCurr, *pXPrimePrimeCurr, *pLambdaCurr);

	Err = 0.;
	NonlinearSolver *pNLSolver = pS->pGetNonlinearSolver();

	/* Position */
	SetOrder(InverseDynamics::POSITION);

	/* Setting iOrder = 0, the residual is called only
	 * for constraints, on positions */
	pNLSolver->Solve(this, pS, MaxIters, dTol,
    			EffIter, Err, dSolTol, SolErr);

	SolutionManager *pSM = pS->pGetSolutionManager();
	MatrixHandler *pMat = pSM->pMatHdl();
	VectorHandler *pRes = pSM->pResHdl();
	VectorHandler *pSol = pSM->pSolHdl();

	/* use position */
	// Update(pSol);

	/* Velocity */
	SetOrder(InverseDynamics::VELOCITY);

	pRes->Reset();
	pSol->Reset();
	/* there's no need to check changes in
	 * equation structure... it is already
	 * performed by NonlinearSolver->Solve() */
	Residual(pRes);

	if (pS->outputRes()) {
		silent_cout("Residual(velocity):" << std::endl);
		pS->PrintResidual(*pRes, 0);
	}

	if (bJacobian()) {
		pSM->MatrReset();
		Jacobian(pMat);

		if (pS->outputJac()) {
			silent_cout("Jacobian(velocity):" << std::endl << *pMat);
		}

		EffIter++;
	}

	pSM->Solve();

	if (pS->outputSol()) {
		silent_cout("Solution(velocity):" << std::endl);
		pS->PrintSolution(*pSol, 0);
	}

	/* use velocity */
	Update(pSol);

	// TODO: if UNDERDETERMINED_UNDERACTUATED_COLLOCATED,
	// InverseDynamics::ACCELERATION and InverseDynamics::INVERSE_DYNAMICS
	// are solved together

	/* Acceleration */
	SetOrder(InverseDynamics::ACCELERATION);

	pRes->Reset();
	pSol->Reset();
	Residual(pRes);

	if (pS->outputRes()) {
		silent_cout("Residual(acceleration):" << std::endl);
		pS->PrintResidual(*pRes, 0);
	}

	if (bJacobian()) {
		pSM->MatrReset();
		Jacobian(pMat);

		if (pS->outputJac()) {
			silent_cout("Jacobian(acceleration):" << std::endl << *pMat);
		}

		EffIter++;
	}

	pSM->Solve();

	if (pS->outputSol()) {
		silent_cout("Solution(acceleration):" << std::endl);
		pS->PrintSolution(*pSol, 0);
	}

	Update(pSol);

	/* Forces */
	SetOrder(InverseDynamics::INVERSE_DYNAMICS);

	pRes->Reset();
	pSol->Reset();
	Residual(pRes);

	if (pS->outputRes()) {
		silent_cout("Residual(inverseDynamics):" << std::endl);
		pS->PrintResidual(*pRes, 0);
	}

	if (bJacobian()) {
		pSM->MatrReset();
		Jacobian(pMat);

		if (pS->outputJac()) {
			silent_cout("Jacobian(inverseDynamics):" << std::endl << *pMat);
		}

		EffIter++;
	}

	switch (dynamic_cast<const InverseSolver *>(pDM->GetSolver())->GetProblemType()) {
	case InverseDynamics::FULLY_ACTUATED_COLLOCATED:
		pSM->SolveT();
		break;

	default:
		pSM->Solve();
	}

	if (pS->outputSol()) {
		silent_cout("Solution(inverseDynamics):" << std::endl);
		pS->PrintSolution(*pSol, 0);
	}

	Update(pSol);

	pDM->IDAfterConvergence();

	return Err;
}

void
InverseDynamicsStepSolver::Residual(VectorHandler* pRes) const
{
	ASSERT(pDM != NULL);
	switch (iOrder) {
	case InverseDynamics::INVERSE_DYNAMICS:
		pDM->AssRes(*pRes);
		break;

	default:
		pDM->AssConstrRes(*pRes, iOrder);
		break;
	}
}

void
InverseDynamicsStepSolver::Jacobian(MatrixHandler* pJac) const
{
	ASSERT(pDM != NULL);
	pDM->AssConstrJac(*pJac);
}

void
InverseDynamicsStepSolver::Update(const VectorHandler* pSol) const
{
	DEBUGCOUTFNAME("InverseDynamicsStepSolver::Update");
	ASSERT(pDM != NULL);

	switch (iOrder) {
	case InverseDynamics::POSITION:
		*pXCurr += *pSol;
		break;

	case InverseDynamics::VELOCITY:
		*pXPrimeCurr = *pSol;
		break;

	case InverseDynamics::ACCELERATION:
		*pXPrimePrimeCurr = *pSol;
		break;

	case InverseDynamics::INVERSE_DYNAMICS:
		*pLambdaCurr = *pSol;
		break;

	default:
		ASSERT(0);
		throw ErrGeneric(MBDYN_EXCEPT_ARGS);
	}

	pDM->Update(iOrder);

	// prepare m_bJacobian for next phase
	switch (dynamic_cast<const InverseSolver *>(pDM->GetSolver())->GetProblemType()) {
	case InverseDynamics::FULLY_ACTUATED_COLLOCATED:
		switch (iOrder) {
		case InverseDynamics::INVERSE_DYNAMICS:
		case InverseDynamics::POSITION:
			m_bJacobian = true;
			break;

		case InverseDynamics::VELOCITY:
		case InverseDynamics::ACCELERATION:
			m_bJacobian = false;
			break;

		default:
			break;
		}
		break;

	case InverseDynamics::FULLY_ACTUATED_NON_COLLOCATED:
		switch (iOrder) {
		case InverseDynamics::INVERSE_DYNAMICS:
		case InverseDynamics::POSITION:
		case InverseDynamics::ACCELERATION:
			m_bJacobian = true;
			break;

		case InverseDynamics::VELOCITY:
			m_bJacobian = false;
			break;

		default:
			break;
		}
		break;

	case InverseDynamics::UNDERDETERMINED_UNDERACTUATED_COLLOCATED:
		// TODO
		throw ErrGeneric(MBDYN_EXCEPT_ARGS);

	case InverseDynamics::UNDERDETERMINED_FULLY_ACTUATED:
		m_bJacobian = true;
		break;

	default:
		break;
	}
}

/* Inverse Dynamics - End */
