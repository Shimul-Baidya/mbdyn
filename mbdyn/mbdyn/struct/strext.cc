/* $Header$ */
/* 
 * MBDyn (C) is a multibody analysis code. 
 * http://www.mbdyn.org
 *
 * Copyright (C) 2007-2008
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

#ifdef HAVE_CONFIG_H
#include <mbconfig.h>           /* This goes first in every *.c,*.cc file */
#endif /* HAVE_CONFIG_H */

#include <dataman.h>
#include "strext.h"

#include <fstream>

/* StructExtForce - begin */

/* Costruttore */
StructExtForce::StructExtForce(unsigned int uL,
	std::vector<StructNode *>& nodes,
	std::vector<Vec3>& offsets,
	bool bUnsorted,
	bool bOutputAccelerations,
	std::string& fin,
	bool bRemoveIn,
        std::string& fout,
	bool bNoClobberOut,
	int iSleepTime,
	int iCoupling,
	int iPrecision,
	flag fOut)
: Elem(uL, fOut), 
ExtForce(uL, fin, bRemoveIn, fout, bNoClobberOut, iSleepTime, iCoupling, iPrecision, fOut), 
pRefNode(0),
RefOffset(0.),
bUnsorted(bUnsorted),
bOutputAccelerations(bOutputAccelerations)
{
	ASSERT(nodes.size() == offsets.size());
	Nodes.resize(nodes.size());
	Offsets.resize(nodes.size());
	F.resize(nodes.size());
	M.resize(nodes.size());

	for (unsigned int i = 0; i < nodes.size(); i++) {
		Nodes[i] = nodes[i];
		Offsets[i] = offsets[i];
	}

	if (bUnsorted) {
		done.resize(nodes.size());
	}

	if (bOutputAccelerations) {
		for (unsigned i = 0; i < nodes.size(); i++) {
			DynamicStructNode *pDSN = dynamic_cast<DynamicStructNode *>(Nodes[i]);
			if (pDSN == 0) {
				silent_cerr("StructExtForce"
					"(" << GetLabel() << "): "
					"StructNode(" << Nodes[i]->GetLabel() << ") "
					"is not dynamic"
					<< std::endl);
				throw ErrGeneric();
			}

			pDSN->ComputeAccelerations(true);
		}
	}
}

StructExtForce::~StructExtForce(void)
{
	NO_OP;
}


/*
 * Send output to companion software
 */
void
StructExtForce::Send(std::ostream& outf)
{
	if (pRefNode) {
#if 0
		// TODO
		Vec3 fRef = pRefNode->GetRCurr()*RefOffset;
		Vec3 xRef = pRefNode->GetXCurr() + fRef;
		Mat3x3 RRefT = pRefNode->GetRCurr().Transpose();

		for (unsigned int i = 0; i < Nodes.size(); i++) {
			Vec3 f = Nodes[i]->GetRCurr()*Offsets[i];
			Vec3 x = Nodes[i]->GetXCurr() + f;
			Vec3 v = Nodes[i]->GetVCurr() + Nodes[i]->GetWCurr().Cross(f);

			// manipulate

			outf << Nodes[i]->GetLabel()
				<< " " << x
				<< " " << Nodes[i]->GetRCurr()
				<< " " << v
				<< " " << Nodes[i]->GetWCurr()
				<< std::endl;
		}
#endif

	} else {
		for (unsigned int i = 0; i < Nodes.size(); i++) {
			const Mat3x3& R = Nodes[i]->GetRCurr();
			Vec3 f = R*Offsets[i];
			Vec3 x = Nodes[i]->GetXCurr() + f;
			const Vec3& w = Nodes[i]->GetWCurr();
			Vec3 wCrossf = w.Cross(f);
			Vec3 v = Nodes[i]->GetVCurr() + wCrossf;
			outf << Nodes[i]->GetLabel()
				<< " " << x
				<< " " << R
				<< " " << v
				<< " " << w;
			if (bOutputAccelerations) {
				const Vec3& wp = Nodes[i]->GetWPCurr();
				Vec3 a = Nodes[i]->GetXPPCurr() + w.Cross(wCrossf) + wp.Cross(f);

				outf
					<< " " << a
					<< " " << wp;
			}
			outf << std::endl;
		}
	}
}

void
StructExtForce::Recv(std::istream& inf)
{
	if (bUnsorted) {
		done.resize(Nodes.size());

		for (unsigned int i = 0; i < Nodes.size(); i++) {
			done[i] = false;
		}

		unsigned cnt;
		for (cnt = 0; inf; cnt++) {
			/* assume unsigned int label */
			unsigned l, i;
			doublereal f[3], m[3];

			inf >> l
				>> f[0] >> f[1] >> f[2]
				>> m[0] >> m[1] >> m[2];

			if (!inf) {
				break;
			}

			for (i = 0; i < Nodes.size(); i++) {
				if (Nodes[i]->GetLabel() == l) {
					break;
				}
			}

			if (i == Nodes.size()) {
				silent_cerr("StructExtForce"
					"(" << GetLabel() << "): "
					"unknown label " << l
					<< " as " << cnt << "-th node"
					<< std::endl);
				throw ErrGeneric();
			}

			if (done[i]) {
				silent_cerr("StructExtForce"
					"(" << GetLabel() << "): "
					"label " << l << " already done"
					<< std::endl);
				throw ErrGeneric();
			}

			done[i] = true;

			F[i] = Vec3(f);
			M[i] = Vec3(m);
		}

		if (cnt != Nodes.size()) {
			silent_cerr("StructExtForce(" << GetLabel() << "): "
				"invalid node number " << cnt
				<< std::endl);

			for (unsigned int i = 0; i < Nodes.size(); i++) {
				if (!done[i]) {
					silent_cerr("StructExtForce"
						"(" << GetLabel() << "): "
						"node " << Nodes[i]->GetLabel()
						<< " not done" << std::endl);
					throw ErrGeneric();
				}
			}

			throw ErrGeneric();
		}

	} else {
		for (unsigned i = 0; i < Nodes.size(); i++) {
			/* assume unsigned int label */
			unsigned l;
			doublereal f[3], m[3];

			inf >> l
				>> f[0] >> f[1] >> f[2]
				>> m[0] >> m[1] >> m[2];

			if (!inf) {
				break;
			}

			if (Nodes[i]->GetLabel() != l) {
				silent_cerr("StructExtForce"
					"(" << GetLabel() << "): "
					"invalid " << i << "-th label " << l
					<< std::endl);
				throw ErrGeneric();
			}

			F[i] = Vec3(f);
			M[i] = Vec3(m);
		}
	}
}

SubVectorHandler&
StructExtForce::AssRes(SubVectorHandler& WorkVec,
	doublereal dCoef,
	const VectorHandler& XCurr, 
	const VectorHandler& XPrimeCurr)
{
	ExtForce::Recv();

	WorkVec.ResizeReset(6*Nodes.size());

	if (pRefNode) {
		// manipulate

	} else {
		for (unsigned int i = 0; i < Nodes.size(); i++) {
			integer iFirstIndex = Nodes[i]->iGetFirstMomentumIndex();
			for (int r = 1; r <= 6; r++) {
				WorkVec.PutRowIndex(i*6 + r, iFirstIndex + r);
			}

			WorkVec.Add(i*6 + 1, F[i]);
			WorkVec.Add(i*6 + 4, M[i] + (Nodes[i]->GetRCurr()*Offsets[i]).Cross(F[i]));
		}
	}

	return WorkVec;
}

void
StructExtForce::Output(OutputHandler& OH) const
{
	std::ostream& out = OH.Forces();

	for (unsigned int i = 0; i < Nodes.size(); i++) {
		out << GetLabel() << "." << Nodes[i]->GetLabel()
			<< " " << F[i]
			<< " " << M[i]
			<< std::endl;
	}
}
 
Elem*
ReadStructExtForce(DataManager* pDM, 
	MBDynParser& HP, 
	unsigned int uLabel)
{
	std::string fin;
	bool bUnlinkIn;
	std::string fout;
	bool bNoClobberOut;
	int iSleepTime;
	int iCoupling;
	int iPrecision;
	
	ReadExtForce(pDM, HP, uLabel, fin, bUnlinkIn, fout, bNoClobberOut, iSleepTime, iCoupling, iPrecision);

	bool bUnsorted(false);
	if (HP.IsKeyWord("unsorted")) {
		bUnsorted = true;
	}

	bool bOutputAccelerations(false);
	if (HP.IsKeyWord("accelerations")) {
		bOutputAccelerations = true;
	}

	int n = HP.GetInt();
	if (n <= 0) {
		silent_cerr("StructExtForce(" << uLabel << "): illegal node number " << n <<
			" at line " << HP.GetLineData() << std::endl);
		throw ErrGeneric();
	}

	std::vector<StructNode *> Nodes(n);
	std::vector<Vec3> Offsets(n);

	for (int i = 0; i < n; i++ ) {
		Nodes[i] = (StructNode*)pDM->ReadNode(HP, Node::STRUCTURAL);
		
		ReferenceFrame RF(Nodes[i]);

		if (HP.IsKeyWord("offset")) {
			Offsets[i] = HP.GetPosRel(RF);
		} else {
			Offsets[i] = Vec3(0.);
		}
	}

	flag fOut = pDM->fReadOutput(HP, Elem::FORCE);
	Elem *pEl = 0;
	SAFENEWWITHCONSTRUCTOR(pEl, StructExtForce,
		StructExtForce(uLabel, Nodes, Offsets,
			bUnsorted, bOutputAccelerations,
			fin, bUnlinkIn, fout, bNoClobberOut,
			iSleepTime, iCoupling, iPrecision, fOut));

	return pEl;
}

