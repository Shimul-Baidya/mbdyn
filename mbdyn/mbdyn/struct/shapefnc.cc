/* 
 * MBDyn (C) is a multibody analysis code. 
 * http://www.mbdyn.org
 *
 * Copyright (C) 1996-2000
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
 * the Free Software Foundation; either version 2 of the License, or
 * any later version.
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

#ifdef HAVE_CONFIG_H
#include <mbconfig.h>           /* This goes first in every *.c,*.cc file */
#endif /* HAVE_CONFIG_H */

#include <matvec3.h>
#include <shapefnc.h>
#include <float.h>

/* Funzioni di forma e loro derivate */
const doublereal dN2_1 = .5;            /* ShapeFunc2N(0., 1, 0) */
const doublereal dN2_2 = .5;            /* ShapeFunc3N(0., 2, 0) */

const doublereal dN2P_1 = -.5;          /* ShapeFunc2N(0., 1, 1) */
const doublereal dN2P_2 = .5;           /* ShapeFunc2N(0., 2, 1) */

/* Per l'interpolazione piu' compatta */
const doublereal dN2[2] = {
	dN2_1, dN2_2
};

const doublereal dN2P[2] = {
	dN2P_1, dN2P_2
};

/* Funzioni di interpolazione */
doublereal 
ShapeFunc2N(doublereal d, integer iNode, integer iOrd)
{
	ASSERT(iOrd == 0 || iOrd == 1);
	ASSERT(iNode == 1 || iNode == 2);
	
	switch (iOrd) {
	case 0:
		switch (iNode) {
		case 1:
			return .5*(1.-d);
			
		case 2:
			return .5*(1.+d);
			
		default:
			THROW(ErrGeneric());
		}
		
	case 1:
		switch (iNode) {
		case 1:		
			return -.5;
			
		case 2:
			return .5;
			
		default:
			THROW(ErrGeneric());
		}
	}
	
	/* Per evitare warnings */
	return 0.;
}

doublereal
DxDcsi2N(doublereal d, const Vec3& X1, const Vec3& X2)
{
	doublereal dN1p = ShapeFunc2N(d, 1, 1);
	doublereal dN2p = ShapeFunc2N(d, 2, 1);
	Vec3 DXDcsi(X1*dN1p+X2*dN2p);
	doublereal dd = DXDcsi.Dot();

	if (dd > DBL_EPSILON) {
		return sqrt(dd);
	}

	return 0.;
}

/* Punto di valutazione */
const doublereal dS = 1./sqrt(3.);

/* Funzioni di forma e loro derivate - punto I */
const doublereal dN1_I = (1.+sqrt(3.))/6.;       /* ShapeFunc3N(-dS, 1) */
const doublereal dN2_I = 2./3.;                  /* ShapeFunc3N(-dS, 2) */
const doublereal dN3_I = (1.-sqrt(3.))/6.;       /* ShapeFunc3N(-dS, 3) */

const doublereal dN1P_I = -(2.*sqrt(3.)+3.)/6.;  /* ShapeFunc3N(-dS, 1, 1) */
const doublereal dN2P_I = 2./sqrt(3.);           /* ShapeFunc3N(-dS, 2, 1) */
const doublereal dN3P_I = -(2.*sqrt(3.)-3.)/6.;  /* ShapeFunc3N(-dS, 3, 1) */

/* Funzioni di forma e loro derivate - punto II */
const doublereal dN1II = dN3_I;
const doublereal dN2II = dN2_I;
const doublereal dN3II = dN1_I;

const doublereal dN1PII = -dN3P_I;
const doublereal dN2PII = -dN2P_I;
const doublereal dN3PII = -dN1P_I;

/* Per l'interpolazione piu' compatta */
const doublereal dN3[2][3] = {
	{ dN1_I, dN2_I, dN3_I },
	{ dN1II, dN2II, dN3II }
};

const doublereal dN3P[2][3] = {
	{ dN1P_I, dN2P_I, dN3P_I },
	{ dN1PII, dN2PII, dN3PII }
};

doublereal 
ShapeFunc3N(doublereal d, integer iNode, integer iOrd)
{
	ASSERT(iOrd == 0 || iOrd == 1);
	ASSERT(iNode == 1 || iNode == 2 || iNode == 3);
	
	switch (iOrd) {
	case 0:
		switch (iNode) {
		case 1:		
			return .5*d*(d-1.);
			
		case 2:		
			return 1.-d*d;
			
		case 3:		
			return .5*d*(d+1.);
			
		default:
			THROW(ErrGeneric());
		}
		
	case 1:
		switch (iNode) {
		case 1:		
			return d-.5;
			
		case 2:
			return -2.*d;
			
		case 3:
			return d+.5;
			
		default:
			THROW(ErrGeneric());
		}
	}
	
	/* Per evitare warnings */
	return 0.;
}

doublereal
DxDcsi3N(doublereal d, const Vec3& X1, const Vec3& X2, const Vec3& X3)
{
	doublereal dN1p = ShapeFunc3N(d, 1, 1);
	doublereal dN2p = ShapeFunc3N(d, 2, 1);
	doublereal dN3p = ShapeFunc3N(d, 3, 1);
	Vec3 DXDcsi(X1*dN1p+X2*dN2p+X3*dN3p);
	doublereal dd = DXDcsi.Dot();

	if (dd > DBL_EPSILON) {
		return sqrt(dd);
	}

	return 0.;
}

