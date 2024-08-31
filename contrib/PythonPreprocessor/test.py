import MBDynLib as l

# Assuming these are your inputs
beam_idx = 1000  # Index of the beam
nodes = [2001, 2002, 2003]  # List of node labels (for a 3-node beam)
positions = [(0., 0., 0.), (0., 0., 0.), (0., 0., 0.)]  # Relative positions of the nodes
orientations = ['reference', 'reference', 'reference']  # Relative orientations (assuming 'reference' as an example)
const_laws_orientations = ['eye', 'eye']  # Orientation matrices for the constitutive laws at points I and II
const_laws = [
    'linear elastic generic, diag, 1e6, 0.6e6, 0.6e6, 1e3, 2e3, 1e4',
    'same'  # Assuming you want the same law for the second section
]
output = 'yes'  # Custom output flag (optional)

# Instantiate the Beam object
beam = l.Beam(
    idx=beam_idx,
    nodes=nodes,
    positions=positions,
    orientations=orientations,
    const_laws_orientations=const_laws_orientations,
    const_laws=const_laws,
    output=output
)

# The Beam object is now created and can be used in your code
print(beam)
