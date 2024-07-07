import MBDynLib as l

law = l.LinearViscoelasticGeneric(
                law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
                stiffness=[[1.0]],
                viscosity=[[2.0]],
                factor=0.5)

print(law)