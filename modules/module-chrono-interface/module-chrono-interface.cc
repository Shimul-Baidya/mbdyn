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
  * With the contribution of Runsen Zhang <runsen.zhang@polimi.it>
  * during Google Summer of Code 2020
  */


#include "mbconfig.h"           /* This goes first in every *.c,*.cc file */

#include <iostream>
#include <cfloat>
#include <vector>

#include "elem.h"
#include "strnode.h"
#include "dataman.h"
#include "userelem.h"

#include "module-chrono-interface.h"
#include "mbdyn_ce.h"

ChronoInterfaceBaseElem::ChronoInterfaceBaseElem(
	unsigned uLabel, const DofOwner *pDO,
	DataManager* pDM, MBDynParser& HP)
: Elem(uLabel, flag(0)),
UserDefinedElem(uLabel, pDO)
{
	// Read element: obtain information from MBDyn script
	// help
	if (HP.IsKeyWord("help")) {
		silent_cout(
"									\n"
"Module: 	module-chrono-interface						\n"
"Organization:	Dipartimento di Ingegneria Aerospaziale			\n"
"		Politecnico di Milano					\n"
"		http://www.aero.polimi.it/				\n"
"									\n"
"	All rights reserved						\n"
			<< std::endl);

		if (!HP.IsArg()) {
			/*
			 * Exit quietly if nothing else is provided
			 */
			throw NoErr(MBDYN_EXCEPT_ARGS);
		}
	}
	
	/* read information from script - start*/
	// read the coupling type
	MBDyn_CE_CouplingType = ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_NONE;
	if (HP.IsKeyWord("chrono")){
		if (HP.IsKeyWord("none")){
			MBDyn_CE_CouplingType = ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_NONE;
		}
		else if (HP.IsKeyWord("loose")){
			MBDyn_CE_CouplingType = ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_LOOSE;
			std::cout << "loose coupling C::E interface: not implemented" << std::endl;
			throw ErrGeneric(MBDYN_EXCEPT_ARGS);
		}
		else if (HP.IsKeyWord("tight")){
			MBDyn_CE_CouplingType = ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_TIGHT;
		}
		else{
			MBDyn_CE_CouplingType = HP.GetInt();
			if (MBDyn_CE_CouplingType != 1)
			{
				std::cout << "multirate coupling C::E interface: not implemented" << std::endl;
				throw ErrGeneric(MBDYN_EXCEPT_ARGS);
			}
		}
	}

	// read nodes
	int MBDyn_CE_NodesNum = HP.GetInt();
	if (MBDyn_CE_NodesNum <= 0)
	{
		silent_cerr("ChronoInterface(" << uLabel << "): illegal node number " << MBDyn_CE_NodesNum <<
			" at line " << HP.GetLineData() << std::endl);
		throw ErrGeneric(MBDYN_EXCEPT_ARGS);
	}

	MBDyn_CE_Nodes.resize(MBDyn_CE_NodesNum);
	for (int i = 0; i < MBDyn_CE_NodesNum; i++)
	{
		MBDyn_CE_Nodes[i].pMBDyn_CE_Node = pDM->ReadNode<const StructNode, Node::STRUCTURAL>(HP);
		ReferenceFrame pNode_RF(MBDyn_CE_Nodes[i].pMBDyn_CE_Node); //get its coordinate
		if (HP.IsKeyWord("offset")){
			MBDyn_CE_Nodes[i].MBDyn_CE_Offset = HP.GetPosRel(pNode_RF); // return offset in the node coordinate
		}
		else {
			MBDyn_CE_Nodes[i].MBDyn_CE_Offset= Zero3;
		}
		MBDyn_CE_Nodes[i].MBDyn_CE_F = Zero3;
		MBDyn_CE_Nodes[i].MBDyn_CE_M = Zero3;
		MBDyn_CE_Nodes[i].MBDyn_CE_uLabel = MBDyn_CE_Nodes[i].pMBDyn_CE_Node->GetLabel();
	}
	/* read information from script - end*/


	// intial CE model, and allocate space for reloading C::E model data
	pMBDyn_CE_CEModel = MBDyn_CE_CEModel_Init(MBDyn_CE_CEModel_Data);


	/* initial public vectors (containers for the coupling variables) - start*/
	// allocate space for coupling variables
	MBDyn_CE_CouplingSize[0] = MBDyn_CE_NodesNum * (3 + 9 + 3 + 3 + 3 + 3); //kinematic motion
	MBDyn_CE_CouplingSize[1] = MBDyn_CE_NodesNum*(3 + 3); //dynamic variables

	MBDyn_CE_CouplingKinematic.resize(MBDyn_CE_CouplingSize[0], 0.0);
	MBDyn_CE_CouplingDynamic.resize(MBDyn_CE_CouplingSize[1], 0.0);

	pMBDyn_CE_CouplingKinematic_x = &MBDyn_CE_CouplingKinematic[0];
	pMBDyn_CE_CouplingKinematic_R = &MBDyn_CE_CouplingKinematic[3*MBDyn_CE_NodesNum];
	pMBDyn_CE_CouplingKinematic_xp = &MBDyn_CE_CouplingKinematic[12*MBDyn_CE_NodesNum];
	pMBDyn_CE_CouplingKinematic_omega = &MBDyn_CE_CouplingKinematic[15*MBDyn_CE_NodesNum];
	pMBDyn_CE_CouplingKinematic_xpp = &MBDyn_CE_CouplingKinematic[18*MBDyn_CE_NodesNum];
	pMBDyn_CE_CouplingKinematic_omegap = &MBDyn_CE_CouplingKinematic[21*MBDyn_CE_NodesNum];

	pMBDyn_CE_CouplingDynamic_f = &MBDyn_CE_CouplingDynamic[0];
	pMBDyn_CE_CouplingDynamic_m = &MBDyn_CE_CouplingDynamic[3*MBDyn_CE_NodesNum];
	/* initial public vectors - end*/
}

ChronoInterfaceBaseElem::~ChronoInterfaceBaseElem(void)
{
	// destroy private data
	MBDyn_CE_CEModel_Destroy(pMBDyn_CE_CEModel);
	
}

void 
ChronoInterfaceBaseElem::SetValue(DataManager *pDM,
									   VectorHandler &X, VectorHandler &XP,
									   SimulationEntity::Hints *h)
{
	// save the data of C::E model
	switch (MBDyn_CE_CouplingType)
	{
	case ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_NONE :
		break;
	case ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_TIGHT:
		if(MBDyn_CE_CEModel_DataSave(pMBDyn_CE_CEModel, MBDyn_CE_CEModel_Data))
		{
			silent_cerr("ChronoInterface(" << uLabel << ") data saving process is wrong " << std::endl);
			throw ErrGeneric(MBDYN_EXCEPT_ARGS);
		}
		break;
	case ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_LOOSE :
	case ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_STSTAGGERED :
	default:
		break;
	}
}

void 
ChronoInterfaceBaseElem::Update(const VectorHandler &XCurr,
                        const VectorHandler &XprimeCurr)
{
	if (MBDyn_CE_CouplingType==ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_NONE)
		return;
}

void 
ChronoInterfaceBaseElem::AfterConvergence(const VectorHandler &X,
                                  const VectorHandler &XP)
{
	if (MBDyn_CE_CouplingType==ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_NONE){
		
	}
	return;
}

void 
ChronoInterfaceBaseElem::AfterPredict(VectorHandler &X,
                              VectorHandler &XP)
{
	// 1. mbdyn writes kinematic coupling variables to buffer;
	// 2. C::E models read the coupling data from buffer; 
	// 3. C::E models reload data;
	// 4. C::E models do the integration (l=0);
	switch (MBDyn_CE_CouplingType)
	{
	case ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_NONE :
		break;
	case ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_TIGHT:
		MBDyn_CE_SendDataToBuf();
		/*step 2 C::E models read the coupling data from buffer::to do*/
		if(MBDyn_CE_CEModel_DataReload(pMBDyn_CE_CEModel, MBDyn_CE_CEModel_Data))
		{
			silent_cerr("ChronoInterface(" << uLabel << ") data reloading process is wrong " << std::endl);
			throw ErrGeneric(MBDYN_EXCEPT_ARGS);
		}
		MBDyn_CE_CEModel_Update(pMBDyn_CE_CEModel, 1.0e-3);
		break;
	case ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_LOOSE :
	case ChronoInterfaceBaseElem::MBDyn_CE_COUPLING::COUPLING_STSTAGGERED :
	default:
		break;
	}
}


void
ChronoInterfaceBaseElem::WorkSpaceDim(integer* piNumRows, integer* piNumCols) const
{
	*piNumRows = 0;
	*piNumCols = 0;
}

VariableSubMatrixHandler& 
ChronoInterfaceBaseElem::AssJac(VariableSubMatrixHandler& WorkMat,
	doublereal dCoef, 
	const VectorHandler& XCurr,
	const VectorHandler& XPrimeCurr)
{
	DEBUGCOUT("Entering C::E-interface::AssJac()" << std::endl);

	WorkMat.SetNullMatrix();
	return WorkMat;
}

SubVectorHandler& 
ChronoInterfaceBaseElem::AssRes(SubVectorHandler& WorkVec,
	doublereal dCoef,
	const VectorHandler& XCurr, 
	const VectorHandler& XPrimeCurr)
{
	WorkVec.ResizeReset(0);
	return WorkVec;
}


void 
ChronoInterfaceBaseElem::InitialWorkSpaceDim(
	integer* piNumRows,
	integer* piNumCols) const
{
	*piNumRows = 0;
	*piNumCols = 0;
}

VariableSubMatrixHandler&
ChronoInterfaceBaseElem::InitialAssJac(
	VariableSubMatrixHandler& WorkMat, 
	const VectorHandler& XCurr)
{
	DEBUGCOUT("Entering C::E-interface::InitialAssJac()" << std::endl);

	WorkMat.SetNullMatrix();
	return WorkMat;
}

SubVectorHandler& 
ChronoInterfaceBaseElem::InitialAssRes(
	SubVectorHandler& WorkVec,
	const VectorHandler& XCurr)
{
	WorkVec.ResizeReset(0);
	return WorkVec;
}

void
ChronoInterfaceBaseElem::MBDyn_CE_SendDataToBuf()
{
	/*
				mbdynce_x = x + mbdynce_f
				mbdynce_R = R
				mbdynce_v = xp + mbdynce_w cross mbdynce_f
				mbdynce_w = w
				mbdynce_a = xpp + mbdynce_wp cross mbdynce_f + mbdynce_w cross mbdynce_w cross mbdynce_f
				mbdynce_wp = wp
	*/
	for (unsigned mbdynce_i = 0; mbdynce_i < MBDyn_CE_NodesNum;mbdynce_i++)
	{
		const MBDYN_CE_POINTDATA& mbdynce_point = MBDyn_CE_Nodes[mbdynce_i];
		// rotation and position
		const Mat3x3 & mbdynce_R = mbdynce_point.pMBDyn_CE_Node->GetRCurr();
		Vec3 mbdynce_f = mbdynce_R * mbdynce_point.MBDyn_CE_Offset;
		Vec3 mbdynce_x = mbdynce_point.pMBDyn_CE_Node->GetXCurr() + mbdynce_f;
		// angular velocity and velocity
		const Vec3 &mbdynce_w = mbdynce_point.pMBDyn_CE_Node->GetWCurr();
		Vec3 mbdynce_wCrossf = mbdynce_w.Cross(mbdynce_f);
		Vec3 mbdynce_v = mbdynce_point.pMBDyn_CE_Node->GetVCurr() + mbdynce_wCrossf;
		// angular acceleration and acceleration
		const Vec3 &mbdynce_wp = mbdynce_point.pMBDyn_CE_Node->GetWPCurr();
		Vec3 mbdynce_a = mbdynce_point.pMBDyn_CE_Node->GetXPPCurr() + mbdynce_wp.Cross(mbdynce_f) + mbdynce_w.Cross * (mbdynce_wCrossf);

		double mbdynce_tempvec3_x[3];
		double mbdynce_tempvec3_v[3];
		double mbdynce_tempvec3_a[3];
		double mbdynce_tempvec3_w[3];
		double mbdynce_tempvec3_wp[3];
		MBDyn_CE_Vec3D(mbdynce_x, mbdynce_tempvec3_x);
		MBDyn_CE_Vec3D(mbdynce_v, mbdynce_tempvec3_v);
		MBDyn_CE_Vec3D(mbdynce_a, mbdynce_tempvec3_a);
		MBDyn_CE_Vec3D(mbdynce_w, mbdynce_tempvec3_w);
		MBDyn_CE_Vec3D(mbdynce_wp, mbdynce_tempvec3_wp);

		double mbdynce_tempmat3x3_R[9];
		MBDyn_CE_Mat3x3D(mbdynce_tempmat3x3_R[9]);

		memcpy(&pMBDyn_CE_CouplingKinematic_x[3 * mbdynce_i], mbdynce_tempvec3_x, 3 * sizeof(double));
		memcpy(&pMBDyn_CE_CouplingKinematic_R[9* mbdynce_i], mbdynce_tempmat3x3_R, 9 * sizeof(double));
		memcpy(&pMBDyn_CE_CouplingKinematic_xp[3 * mbdynce_i], mbdynce_tempvec3_v, 3 * sizeof(double));
		memcpy(&pMBDyn_CE_CouplingKinematic_omega[3 * mbdynce_i], mbdynce_tempvec3_w, 3 * sizeof(double));
		memcpy(&pMBDyn_CE_CouplingKinematic_xpp[3 * mbdynce_i], mbdynce_tempvec3_a, 3 * sizeof(double));
		memcpy(&pMBDyn_CE_CouplingKinematic_omegap[3 * mbdynce_i], mbdynce_tempvec3_wp, 3 * sizeof(double));
	}
	MBDyn_CE_CEModel_RecvFromBuf(pMBDyn_CE_CEModel, MBDyn_CE_CouplingKinematic);
}

void
ChronoInterfaceBaseElem::Output(OutputHandler& OH) const
{
	// should do something useful
	NO_OP;
}

std::ostream&
ChronoInterfaceBaseElem::Restart(std::ostream& out) const
{
	return out << "# ModuleChronoInterface: is doing now" << std::endl;
}


extern "C" int
module_init(const char *module_name, void *pdm, void *php)
{
	UserDefinedElemRead *rf = new UDERead<ChronoInterfaceBaseElem>; // or new ChronoInterfaceElemRead;
	std::cout << "create your C::E models:"
			  << "\n";
	if (!SetUDE("ChronoInterface", rf)) {
		delete rf;

		silent_cerr("module-Chrono-Interface: "
			"module_init(" << module_name << ") "
			"failed" << std::endl);

		return -1;
	}

	return 0;
}

/* private functions: start*/
void 
ChronoInterfaceBaseElem::MBDyn_CE_Vec3D(Vec3 mbdynce_Vec3, double* mbdynce_temp)
{
	*mbdynce_temp = static_cast<double>(*mbdynce_Vec3.pGetVec());
	*(mbdynce_temp + 1) = static_cast<double>(*(mbdynce_Vec3.pGetVec() + 1));
	*(mbdynce_temp + 2) = static_cast<double>(*(mbdynce_Vec3.pGetVec() + 2));
}

void 
ChronoInterfaceBaseElem::MBDyn_CE_Mat3x3D(Mat3x3 mbdynce_Mat3x3, double *mbdynce_temp)
{
	for (unsigned i = 0; i < 8;i++)
	{
		*(mbdynce_temp + i) = static_cast<double>(*(mbdynce_Mat3x3.pGetMat() + i));
	}
}
/* private functions: end*/