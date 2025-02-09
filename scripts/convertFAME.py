#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#                                                                             #
# RMG - Reaction Mechanism Generator                                          #
#                                                                             #
# Copyright (c) 2002-2019 Prof. William H. Green (whgreen@mit.edu),           #
# Prof. Richard H. West (r.west@neu.edu) and the RMG Team (rmg_dev@mit.edu)   #
#                                                                             #
# Permission is hereby granted, free of charge, to any person obtaining a     #
# copy of this software and associated documentation files (the 'Software'),  #
# to deal in the Software without restriction, including without limitation   #
# the rights to use, copy, modify, merge, publish, distribute, sublicense,    #
# and/or sell copies of the Software, and to permit persons to whom the       #
# Software is furnished to do so, subject to the following conditions:        #
#                                                                             #
# The above copyright notice and this permission notice shall be included in  #
# all copies or substantial portions of the Software.                         #
#                                                                             #
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR  #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,    #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER      #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING     #
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER         #
# DEALINGS IN THE SOFTWARE.                                                   #
#                                                                             #
###############################################################################

"""
Convert a FAME input file to a MEASURE input file.
MEASURE is the previous version of CanTherm.
CanTherm is the previous version of Arkane.
"""

import argparse
import logging
import os.path

import rmgpy.constants as constants
from arkane.pdep import PressureDependenceJob
from rmgpy.kinetics import Arrhenius
from rmgpy.molecule import Molecule
from rmgpy.pdep import Network, Configuration, SingleExponentialDown
from rmgpy.quantity import Quantity, Energy
from rmgpy.reaction import Reaction
from rmgpy.species import Species, TransitionState
from rmgpy.statmech import HarmonicOscillator, HinderedRotor, Conformer
from rmgpy.thermo import ThermoData
from rmgpy.transport import TransportData


################################################################################

def parse_command_line_arguments():
    """
    Parse the command-line arguments being passed to MEASURE. These are
    described in the module docstring.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('file', metavar='FILE', type=str, nargs='+',
                        help='a file to convert')
    parser.add_argument('-d', '--dictionary', metavar='DICTFILE', type=str, nargs=1,
                        help='the RMG dictionary corresponding to these files')
    parser.add_argument('-x', '--max-energy', metavar='VALUE UNITS', type=str, nargs=2,
                        help='A maximum energy to crop at')

    return parser.parse_args()


################################################################################

def loadFAMEInput(path, moleculeDict=None):
    """
    Load the contents of a FAME input file into the MEASURE object. FAME
    is an early version of MEASURE written in Fortran and used by RMG-Java.
    This script enables importing FAME input files into MEASURE so we can
    use the additional functionality that MEASURE provides. Note that it
    is mostly designed to load the FAME input files generated automatically
    by RMG-Java, and may not load hand-crafted FAME input files. If you
    specify a `moleculeDict`, then this script will use it to associate
    the species with their structures.
    """

    def readMeaningfulLine(f):
        line = f.readline()
        while line != '':
            line = line.strip()
            if len(line) > 0 and line[0] != '#':
                return line
            else:
                line = f.readline()
        return ''

    moleculeDict = moleculeDict or {}

    logging.info('Loading file "{0}"...'.format(path))
    f = open(path)

    job = PressureDependenceJob(network=None)

    # Read method
    method = readMeaningfulLine(f).lower()
    if method == 'modifiedstrongcollision':
        job.method = 'modified strong collision'
    elif method == 'reservoirstate':
        job.method = 'reservoir state'

    # Read temperatures
    Tcount, Tunits, Tmin, Tmax = readMeaningfulLine(f).split()
    job.Tmin = Quantity(float(Tmin), Tunits)
    job.Tmax = Quantity(float(Tmax), Tunits)
    job.Tcount = int(Tcount)
    Tlist = []
    for i in range(int(Tcount)):
        Tlist.append(float(readMeaningfulLine(f)))
    job.Tlist = Quantity(Tlist, Tunits)

    # Read pressures
    Pcount, Punits, Pmin, Pmax = readMeaningfulLine(f).split()
    job.Pmin = Quantity(float(Pmin), Punits)
    job.Pmax = Quantity(float(Pmax), Punits)
    job.Pcount = int(Pcount)
    Plist = []
    for i in range(int(Pcount)):
        Plist.append(float(readMeaningfulLine(f)))
    job.Plist = Quantity(Plist, Punits)

    # Read interpolation model
    model = readMeaningfulLine(f).split()
    if model[0].lower() == 'chebyshev':
        job.interpolation_model = ('chebyshev', int(model[1]), int(model[2]))
    elif model[0].lower() == 'pdeparrhenius':
        job.interpolation_model = ('pdeparrhenius',)

    # Read grain size or number of grains
    job.minimum_grain_count = 0
    job.maximum_grain_size = None
    for i in range(2):
        data = readMeaningfulLine(f).split()
        if data[0].lower() == 'numgrains':
            job.minimum_grain_count = int(data[1])
        elif data[0].lower() == 'grainsize':
            job.maximum_grain_size = (float(data[2]), data[1])

    # A FAME file is almost certainly created during an RMG job, so use RMG mode
    job.rmgmode = True

    # Create the Network
    job.network = Network()

    # Read collision model
    data = readMeaningfulLine(f)
    assert data.lower() == 'singleexpdown'
    alpha0units, alpha0 = readMeaningfulLine(f).split()
    T0units, T0 = readMeaningfulLine(f).split()
    n = readMeaningfulLine(f)
    energy_transfer_model = SingleExponentialDown(
        alpha0=Quantity(float(alpha0), alpha0units),
        T0=Quantity(float(T0), T0units),
        n=float(n),
    )

    species_dict = {}

    # Read bath gas parameters
    bath_gas = Species(label='bath_gas', energy_transfer_model=energy_transfer_model)
    mol_wt_units, mol_wt = readMeaningfulLine(f).split()
    if mol_wt_units == 'u': mol_wt_units = 'amu'
    bath_gas.molecular_weight = Quantity(float(mol_wt), mol_wt_units)
    sigmaLJunits, sigmaLJ = readMeaningfulLine(f).split()
    epsilonLJunits, epsilonLJ = readMeaningfulLine(f).split()
    assert epsilonLJunits == 'J'
    bath_gas.transport_data = TransportData(
        sigma=Quantity(float(sigmaLJ), sigmaLJunits),
        epsilon=Quantity(float(epsilonLJ) / constants.kB, 'K'),
    )
    job.network.bath_gas = {bath_gas: 1.0}

    # Read species data
    n_spec = int(readMeaningfulLine(f))
    for i in range(n_spec):
        species = Species()
        species.conformer = Conformer()
        species.energy_transfer_model = energy_transfer_model

        # Read species label
        species.label = readMeaningfulLine(f)
        species_dict[species.label] = species
        if species.label in moleculeDict:
            species.molecule = [moleculeDict[species.label]]

        # Read species E0
        E0units, E0 = readMeaningfulLine(f).split()
        species.conformer.e0 = Quantity(float(E0), E0units)
        species.conformer.e0.units = 'kJ/mol'

        # Read species thermo data
        H298units, H298 = readMeaningfulLine(f).split()
        S298units, S298 = readMeaningfulLine(f).split()
        Cpcount, Cpunits = readMeaningfulLine(f).split()
        Cpdata = []
        for i in range(int(Cpcount)):
            Cpdata.append(float(readMeaningfulLine(f)))
        if S298units == 'J/mol*K': S298units = 'J/(mol*K)'
        if Cpunits == 'J/mol*K': Cpunits = 'J/(mol*K)'
        species.thermo = ThermoData(
            H298=Quantity(float(H298), H298units),
            S298=Quantity(float(S298), S298units),
            Tdata=Quantity([300, 400, 500, 600, 800, 1000, 1500], "K"),
            Cpdata=Quantity(Cpdata, Cpunits),
            Cp0=(Cpdata[0], Cpunits),
            CpInf=(Cpdata[-1], Cpunits),
        )

        # Read species collision parameters
        mol_wt_units, mol_wt = readMeaningfulLine(f).split()
        if mol_wt_units == 'u': mol_wt_units = 'amu'
        species.molecular_weight = Quantity(float(mol_wt), mol_wt_units)
        sigmaLJunits, sigmaLJ = readMeaningfulLine(f).split()
        epsilonLJunits, epsilonLJ = readMeaningfulLine(f).split()
        assert epsilonLJunits == 'J'
        species.transport_data = TransportData(
            sigma=Quantity(float(sigmaLJ), sigmaLJunits),
            epsilon=Quantity(float(epsilonLJ) / constants.kB, 'K'),
        )

        # Read species vibrational frequencies
        freq_count, freq_units = readMeaningfulLine(f).split()
        frequencies = []
        for j in range(int(freq_count)):
            frequencies.append(float(readMeaningfulLine(f)))
        species.conformer.modes.append(HarmonicOscillator(
            frequencies=Quantity(frequencies, freq_units),
        ))

        # Read species external rotors
        rotCount, rotUnits = readMeaningfulLine(f).split()
        if int(rotCount) > 0:
            raise NotImplementedError('Cannot handle external rotational modes in FAME input.')

        # Read species internal rotors
        freq_count, freq_units = readMeaningfulLine(f).split()
        frequencies = []
        for j in range(int(freq_count)):
            frequencies.append(float(readMeaningfulLine(f)))
        barr_count, barr_units = readMeaningfulLine(f).split()
        barriers = []
        for j in range(int(barr_count)):
            barriers.append(float(readMeaningfulLine(f)))
        if barr_units == 'cm^-1':
            barr_units = 'J/mol'
            barriers = [barr * constants.h * constants.c * constants.Na * 100. for barr in barriers]
        elif barr_units in ['Hz', 's^-1']:
            barr_units = 'J/mol'
            barriers = [barr * constants.h * constants.Na for barr in barriers]
        elif barr_units != 'J/mol':
            raise Exception('Unexpected units "{0}" for hindered rotor barrier height.'.format(barr_units))
        inertia = [V0 / 2.0 / (nu * constants.c * 100.) ** 2 / constants.Na for nu, V0 in zip(frequencies, barriers)]
        for I, V0 in zip(inertia, barriers):
            species.conformer.modes.append(HinderedRotor(
                inertia=Quantity(I, "kg*m^2"),
                barrier=Quantity(V0, barr_units),
                symmetry=1,
                semiclassical=False,
            ))

        # Read overall symmetry number
        species.conformer.spin_multiplicity = int(readMeaningfulLine(f))

    # Read isomer, reactant channel, and product channel data
    n_isom = int(readMeaningfulLine(f))
    n_reac = int(readMeaningfulLine(f))
    n_prod = int(readMeaningfulLine(f))
    for i in range(n_isom):
        data = readMeaningfulLine(f).split()
        assert data[0] == '1'
        job.network.isomers.append(species_dict[data[1]])
    for i in range(n_reac):
        data = readMeaningfulLine(f).split()
        assert data[0] == '2'
        job.network.reactants.append([species_dict[data[1]], species_dict[data[2]]])
    for i in range(n_prod):
        data = readMeaningfulLine(f).split()
        if data[0] == '1':
            job.network.products.append([species_dict[data[1]]])
        elif data[0] == '2':
            job.network.products.append([species_dict[data[1]], species_dict[data[2]]])

    # Read path reactions
    n_rxn = int(readMeaningfulLine(f))
    for i in range(n_rxn):

        # Read and ignore reaction equation
        equation = readMeaningfulLine(f)
        reaction = Reaction(transition_state=TransitionState(), reversible=True)
        job.network.path_reactions.append(reaction)
        reaction.transition_state.conformer = Conformer()

        # Read reactant and product indices
        data = readMeaningfulLine(f).split()
        reac = int(data[0]) - 1
        prod = int(data[1]) - 1
        if reac < n_isom:
            reaction.reactants = [job.network.isomers[reac]]
        elif reac < n_isom + n_reac:
            reaction.reactants = job.network.reactants[reac - n_isom]
        else:
            reaction.reactants = job.network.products[reac - n_isom - n_reac]
        if prod < n_isom:
            reaction.products = [job.network.isomers[prod]]
        elif prod < n_isom + n_reac:
            reaction.products = job.network.reactants[prod - n_isom]
        else:
            reaction.products = job.network.products[prod - n_isom - n_reac]

        # Read reaction E0
        E0units, E0 = readMeaningfulLine(f).split()
        reaction.transition_state.conformer.e0 = Quantity(float(E0), E0units)
        reaction.transition_state.conformer.e0.units = 'kJ/mol'

        # Read high-pressure limit kinetics
        data = readMeaningfulLine(f)
        assert data.lower() == 'arrhenius'
        A_units, A = readMeaningfulLine(f).split()
        if '/' in A_units:
            index = A_units.find('/')
            A_units = '{0}/({1})'.format(A_units[0:index], A_units[index + 1:])
        Ea_units, Ea = readMeaningfulLine(f).split()
        n = readMeaningfulLine(f)
        reaction.kinetics = Arrhenius(
            A=Quantity(float(A), A_units),
            Ea=Quantity(float(Ea), Ea_units),
            n=Quantity(float(n)),
        )
        reaction.kinetics.Ea.units = 'kJ/mol'

    f.close()

    job.network.isomers = [Configuration(isomer) for isomer in job.network.isomers]
    job.network.reactants = [Configuration(*reactants) for reactants in job.network.reactants]
    job.network.products = [Configuration(*products) for products in job.network.products]

    return job


def pruneNetwork(network, Emax):
    """
    Prune the network by removing any configurations with ground-state energy
    above `Emax` in J/mol and any reactions with transition state energy above
    `Emax` from the network. All reactions involving removed configurations
    are also removed. Any configurations that have zero reactions as a result
    of this process are also removed.
    """

    # Remove configurations with ground-state energies above the given Emax
    isomers_to_remove = []
    for isomer in network.isomers:
        if isomer.E0 > Emax:
            isomers_to_remove.append(isomer)
    for isomer in isomers_to_remove:
        network.isomers.remove(isomer)

    reactants_to_remove = []
    for reactant in network.reactants:
        if reactant.E0 > Emax:
            reactants_to_remove.append(reactant)
    for reactant in reactants_to_remove:
        network.reactants.remove(reactant)

    products_to_remove = []
    for product in network.products:
        if product.E0 > Emax:
            products_to_remove.append(product)
    for product in products_to_remove:
        network.products.remove(product)

    # Remove path reactions involving the removed configurations
    removed_configurations = []
    removed_configurations.extend([isomer.species for isomer in isomers_to_remove])
    removed_configurations.extend([reactant.species for reactant in reactants_to_remove])
    removed_configurations.extend([product.species for product in products_to_remove])
    reactions_to_remove = []
    for rxn in network.path_reactions:
        if rxn.reactants in removed_configurations or rxn.products in removed_configurations:
            reactions_to_remove.append(rxn)
    for rxn in reactions_to_remove:
        network.path_reactions.remove(rxn)

    # Remove path reactions with barrier heights above the given Emax
    reactions_to_remove = []
    for rxn in network.path_reactions:
        if rxn.transition_state.conformer.E0.value_si > Emax:
            reactions_to_remove.append(rxn)
    for rxn in reactions_to_remove:
        network.path_reactions.remove(rxn)

    def ismatch(speciesList1, speciesList2):
        if len(speciesList1) == len(speciesList2) == 1:
            return (speciesList1[0] is speciesList2[0])
        elif len(speciesList1) == len(speciesList2) == 2:
            return ((speciesList1[0] is speciesList2[0] and speciesList1[1] is speciesList2[1]) or
                    (speciesList1[0] is speciesList2[1] and speciesList1[1] is speciesList2[0]))
        elif len(speciesList1) == len(speciesList2) == 3:
            return ((speciesList1[0] is speciesList2[0] and speciesList1[1] is speciesList2[1] and speciesList1[2] is
                     speciesList2[2]) or
                    (speciesList1[0] is speciesList2[0] and speciesList1[1] is speciesList2[2] and speciesList1[2] is
                     speciesList2[1]) or
                    (speciesList1[0] is speciesList2[1] and speciesList1[1] is speciesList2[0] and speciesList1[2] is
                     speciesList2[2]) or
                    (speciesList1[0] is speciesList2[1] and speciesList1[1] is speciesList2[2] and speciesList1[2] is
                     speciesList2[0]) or
                    (speciesList1[0] is speciesList2[2] and speciesList1[1] is speciesList2[0] and speciesList1[2] is
                     speciesList2[1]) or
                    (speciesList1[0] is speciesList2[2] and speciesList1[1] is speciesList2[1] and speciesList1[2] is
                     speciesList2[0]))
        else:
            return False

    # Remove orphaned configurations (those with zero path reactions involving them)
    isomers_to_remove = []
    for isomer in network.isomers:
        for rxn in network.path_reactions:
            if ismatch(rxn.reactants, isomer.species) or ismatch(rxn.products, isomer.species):
                break
        else:
            isomers_to_remove.append(isomer)
    for isomer in isomers_to_remove:
        network.isomers.remove(isomer)

    reactants_to_remove = []
    for reactant in network.reactants:
        for rxn in network.path_reactions:
            if ismatch(rxn.reactants, reactant.species) or ismatch(rxn.products, reactant.species):
                break
        else:
            reactants_to_remove.append(reactant)
    for reactant in reactants_to_remove:
        network.reactants.remove(reactant)

    products_to_remove = []
    for product in network.products:
        for rxn in network.path_reactions:
            if ismatch(rxn.reactants, product.species) or ismatch(rxn.products, product.species):
                break
        else:
            products_to_remove.append(product)
    for product in products_to_remove:
        network.products.remove(product)


################################################################################

if __name__ == '__main__':

    # Parse the command-line arguments
    args = parse_command_line_arguments()

    if args.max_energy:
        Emax = float(args.max_energy[0])
        Eunits = str(args.max_energy[1])
        Emax = Energy(Emax, Eunits).value_si
    else:
        Emax = None

    # Load RMG dictionary if specified
    moleculeDict = {}
    if args.dictionary is not None:
        f = open(args.dictionary[0])
        adjlist = ''
        label = ''
        for line in f:
            if len(line.strip()) == 0:
                if len(adjlist.strip()) > 0:
                    molecule = Molecule()
                    molecule.from_adjacency_list(adjlist)
                    moleculeDict[label] = molecule
                adjlist = ''
                label = ''
            else:
                if len(adjlist.strip()) == 0:
                    label = line.strip()
                adjlist += line

        f.close()

    method = None

    for fstr in args.file:

        # Construct Arkane job from FAME input
        job = loadFAMEInput(fstr, moleculeDict)

        if Emax is not None:
            pruneNetwork(job.network, Emax)

        # Save MEASURE input file based on the above
        dirname, basename = os.path.split(os.path.abspath(fstr))
        basename, ext = os.path.splitext(basename)
        path = os.path.join(dirname, basename + '.py')
        job.save_input_file(path)
