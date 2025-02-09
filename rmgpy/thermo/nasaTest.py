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
This script contains unit tests of the :mod:`rmgpy.thermo.nasa` module.
"""

import os.path
import unittest

import numpy as np

import rmgpy.constants as constants
from rmgpy.quantity import ScalarQuantity
from rmgpy.thermo.nasa import NASA, NASAPolynomial


################################################################################


class TestNASA(unittest.TestCase):
    """
    Contains unit tests of the MultiNASA class.
    """

    def setUp(self):
        """
        A function run before each unit test in this class.
        """
        self.coeffs_low = [4.03055, -0.00214171, 4.90611e-05, -5.99027e-08, 2.38945e-11, -11257.6, 3.5613]
        self.coeffs_high = [-0.307954, 0.0245269, -1.2413e-05, 3.07724e-09, -3.01467e-13, -10693, 22.628]
        self.Tmin = 300.
        self.Tmax = 3000.
        self.Tint = 650.73
        self.E0 = -782292.  # J/mol.
        self.comment = "C2H6"
        self.nasa = NASA(
            polynomials=[
                NASAPolynomial(coeffs=self.coeffs_low, Tmin=(self.Tmin, "K"), Tmax=(self.Tint, "K")),
                NASAPolynomial(coeffs=self.coeffs_high, Tmin=(self.Tint, "K"), Tmax=(self.Tmax, "K")),
            ],
            Tmin=(self.Tmin, "K"),
            Tmax=(self.Tmax, "K"),
            E0=(self.E0, "J/mol"),
            comment=self.comment,
        )

    def tearDown(self):
        """
        Reset the database & liquid parameters for solution
        """
        import rmgpy.data.rmg
        rmgpy.data.rmg.database = None

    def test_poly_low(self):
        """
        Test that the NASA low-temperature polynomial was properly set.
        """
        self.assertEqual(len(self.nasa.poly1.coeffs), len(self.coeffs_low))
        for coeff0, coeff in zip(self.nasa.poly1.coeffs, self.coeffs_low):
            self.assertAlmostEqual(coeff / coeff0, 1.0, 6)
        self.assertEqual(self.nasa.poly1.Tmin.value_si, self.Tmin)
        self.assertEqual(self.nasa.poly1.Tmax.value_si, self.Tint)

    def test_poly_high(self):
        """
        Test that the NASA high-temperature polynomial was properly set.
        """
        self.assertEqual(len(self.nasa.poly2.coeffs), len(self.coeffs_high))
        for coeff0, coeff in zip(self.nasa.poly2.coeffs, self.coeffs_high):
            self.assertAlmostEqual(coeff / coeff0, 1.0, 6)
        self.assertEqual(self.nasa.poly2.Tmin.value_si, self.Tint)
        self.assertEqual(self.nasa.poly2.Tmax.value_si, self.Tmax)

    def test_temperature_min(self):
        """
        Test that the NASA Tmin property was properly set.
        """
        self.assertAlmostEqual(self.nasa.Tmin.value_si / self.Tmin, 1.0, 6,
                               '{0} != {1} within 6 places'.format(self.nasa.Tmin, self.Tmin))

    def test_temperature_max(self):
        """
        Test that the NASA Tmax property was properly set.
        """
        self.assertAlmostEqual(self.nasa.Tmax.value_si / self.Tmax, 1.0, 6,
                               '{0} != {1} within 6 places'.format(self.nasa.Tmax, self.Tmax))

    def test_e0(self):
        """
        Test that the NASA E0 property was properly set.
        """
        self.assertAlmostEqual(self.nasa.E0.value_si / self.E0, 1.0, 6,
                               '{0} != {1} within 6 places'.format(self.nasa.Tmax, self.Tmax))

    def test_comment(self):
        """
        Test that the NASA comment property was properly set.
        """
        self.assertEqual(self.nasa.comment, self.comment)

    def test_is_temperature_valid(self):
        """
        Test the NASA.is_temperature_valid() method.
        """
        Tdata = [200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000]
        valid_data = [False, True, True, True, True, True, True, True, True, True]
        for T, valid in zip(Tdata, valid_data):
            valid0 = self.nasa.is_temperature_valid(T)
            self.assertEqual(valid0, valid)

    def test_get_heat_capacity(self):
        """
        Test the NASA.get_heat_capacity() method.
        """
        Tlist = np.array([400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        cp_exp_list = np.array([7.80157, 10.5653, 12.8213, 14.5817, 15.9420,
                                16.9861, 17.78645, 18.4041, 18.8883]) * constants.R
        for T, cp_exp in zip(Tlist, cp_exp_list):
            cp_act = self.nasa.get_heat_capacity(T)
            self.assertAlmostEqual(cp_exp / cp_act, 1.0, 4, '{0} != {1}'.format(cp_exp, cp_act))

    def test_get_enthalpy(self):
        """
        Test the NASA.get_enthalpy() method.
        """
        Tlist = np.array([400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        h_exp_list = np.array([-22.7613, -12.1027, -6.14236, -2.16615, 0.743456,
                               2.99256, 4.79397, 6.27334, 7.51156]) * constants.R * Tlist
        for T, h_exp in zip(Tlist, h_exp_list):
            h_act = self.nasa.get_enthalpy(T)
            self.assertAlmostEqual(h_exp / h_act, 1.0, 3, '{0} != {1}'.format(h_exp, h_act))

    def test_get_entropy(self):
        """
        Test the NASA.get_entropy() method.
        """
        Tlist = np.array([400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        s_exp_list = np.array([29.6534, 33.3516, 36.7131, 39.7715, 42.5557,
                               45.0952, 47.4179, 49.5501, 51.5152]) * constants.R
        for T, s_exp in zip(Tlist, s_exp_list):
            s_act = self.nasa.get_entropy(T)
            self.assertAlmostEqual(s_exp / s_act, 1.0, 4, '{0} != {1}'.format(s_exp, s_act))

    def test_get_free_energy(self):
        """
        Test the NASA.get_free_energy() method.
        """
        Tlist = np.array([400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        for T in Tlist:
            g_exp = self.nasa.get_enthalpy(T) - T * self.nasa.get_entropy(T)
            g_act = self.nasa.get_free_energy(T)
            self.assertAlmostEqual(g_exp / g_act, 1.0, 4, '{0} != {1}'.format(g_exp, g_act))

    def test_pickle(self):
        """
        Test that a NASA object can be pickled and unpickled with no loss of
        information.
        """
        import pickle
        nasa = pickle.loads(pickle.dumps(self.nasa))
        self.assertEqual(len(self.nasa.poly1.coeffs), len(nasa.poly1.coeffs))
        for coeff0, coeff in zip(self.nasa.poly1.coeffs, nasa.poly1.coeffs):
            self.assertAlmostEqual(coeff / coeff0, 1.0, 6)
        self.assertEqual(self.nasa.poly1.Tmin.value, nasa.poly1.Tmin.value)
        self.assertEqual(self.nasa.poly1.Tmin.units, nasa.poly1.Tmin.units)
        self.assertEqual(self.nasa.poly1.Tmax.value, nasa.poly1.Tmax.value)
        self.assertEqual(self.nasa.poly1.Tmax.units, nasa.poly1.Tmax.units)
        self.assertEqual(self.nasa.poly1.comment, nasa.poly1.comment)
        self.assertEqual(len(self.nasa.poly2.coeffs), len(nasa.poly2.coeffs))
        for coeff0, coeff in zip(self.nasa.poly2.coeffs, nasa.poly2.coeffs):
            self.assertAlmostEqual(coeff / coeff0, 1.0, 6)
        self.assertEqual(self.nasa.poly2.Tmin.value, nasa.poly2.Tmin.value)
        self.assertEqual(self.nasa.poly2.Tmin.units, nasa.poly2.Tmin.units)
        self.assertEqual(self.nasa.poly2.Tmax.value, nasa.poly2.Tmax.value)
        self.assertEqual(self.nasa.poly2.Tmax.units, nasa.poly2.Tmax.units)
        self.assertEqual(self.nasa.poly2.comment, nasa.poly2.comment)
        self.assertEqual(self.nasa.Tmin.value, nasa.Tmin.value)
        self.assertEqual(self.nasa.Tmin.units, nasa.Tmin.units)
        self.assertEqual(self.nasa.Tmax.value, nasa.Tmax.value)
        self.assertEqual(self.nasa.Tmax.units, nasa.Tmax.units)
        self.assertEqual(self.nasa.E0.value, nasa.E0.value)
        self.assertEqual(self.nasa.E0.units, nasa.E0.units)
        self.assertEqual(self.nasa.comment, nasa.comment)

    def test_repr(self):
        """
        Test that a NASA object can be reconstructed from its repr() output
        with no loss of information.
        """
        namespace = {}
        exec('nasa = {0!r}'.format(self.nasa), globals(), namespace)
        self.assertIn('nasa', namespace)
        nasa = namespace['nasa']
        self.assertEqual(len(self.nasa.poly1.coeffs), len(nasa.poly1.coeffs))
        for coeff0, coeff in zip(self.nasa.poly1.coeffs, nasa.poly1.coeffs):
            self.assertAlmostEqual(coeff / coeff0, 1.0, 6)
        self.assertEqual(self.nasa.poly1.Tmin.value, nasa.poly1.Tmin.value)
        self.assertEqual(self.nasa.poly1.Tmin.units, nasa.poly1.Tmin.units)
        self.assertEqual(self.nasa.poly1.Tmax.value, nasa.poly1.Tmax.value)
        self.assertEqual(self.nasa.poly1.Tmax.units, nasa.poly1.Tmax.units)
        self.assertEqual(self.nasa.poly1.comment, nasa.poly1.comment)
        self.assertEqual(len(self.nasa.poly2.coeffs), len(nasa.poly2.coeffs))
        for coeff0, coeff in zip(self.nasa.poly2.coeffs, nasa.poly2.coeffs):
            self.assertAlmostEqual(coeff / coeff0, 1.0, 6)
        self.assertEqual(self.nasa.poly2.Tmin.value, nasa.poly2.Tmin.value)
        self.assertEqual(self.nasa.poly2.Tmin.units, nasa.poly2.Tmin.units)
        self.assertEqual(self.nasa.poly2.Tmax.value, nasa.poly2.Tmax.value)
        self.assertEqual(self.nasa.poly2.Tmax.units, nasa.poly2.Tmax.units)
        self.assertEqual(self.nasa.poly2.comment, nasa.poly2.comment)
        self.assertEqual(self.nasa.Tmin.value, nasa.Tmin.value)
        self.assertEqual(self.nasa.Tmin.units, nasa.Tmin.units)
        self.assertEqual(self.nasa.Tmax.value, nasa.Tmax.value)
        self.assertEqual(self.nasa.Tmax.units, nasa.Tmax.units)
        self.assertEqual(self.nasa.E0.value, nasa.E0.value)
        self.assertEqual(self.nasa.E0.units, nasa.E0.units)
        self.assertEqual(self.nasa.comment, nasa.comment)

    def test_to_cantera(self):
        """
        Test that conversion to a Cantera NasaPoly2 object works
        """
        nasapoly2 = self.nasa.to_cantera()
        # NasaPoly2 units use J/kmol rather than J/mol
        self.assertAlmostEqual(self.nasa.get_enthalpy(900), nasapoly2.h(900) / 1000, 1)
        self.assertAlmostEqual(self.nasa.get_entropy(700), nasapoly2.s(700) / 1000, 1)

    def test_to_nasa(self):
        """
        Test if the entropy computed from other thermo implementations is close to what NASA computes.
        """

        from rmgpy import settings
        from rmgpy.data.rmg import RMGDatabase
        from rmgpy.species import Species

        # Load databases
        database = RMGDatabase()
        database.load_thermo(os.path.join(settings['database.directory'], 'thermo'), thermo_libraries=['Narayanaswamy'])
        database.load_solvation(os.path.join(settings['database.directory'], 'solvation'))

        spc = Species().from_smiles('CC')
        spc.get_thermo_data()

        T = 1350.  # not 298K!

        # nasa to thermodata
        nasa = spc.thermo
        s_nasa = nasa.get_entropy(T)

        td = nasa.to_thermo_data()
        s_td = td.get_entropy(T)

        self.assertAlmostEqual(s_nasa, s_td, -1)
        self.assertEqual(td.comment, nasa.comment)

        # thermodata to nasa
        nasa = td.to_nasa(Tmin=100.0, Tmax=5000.0, Tint=1000.0)
        s_nasa = nasa.get_entropy(T)

        self.assertAlmostEqual(s_nasa, s_td, -1)
        self.assertEqual(td.comment, nasa.comment)

        # wilhoit to nasa
        wilhoit = nasa.to_wilhoit()
        nasa = wilhoit.to_nasa(Tmin=100.0, Tmax=5000.0, Tint=1000.0)
        s_nasa = nasa.get_entropy(T)

        self.assertAlmostEqual(s_nasa, s_td, -1)
        self.assertEqual(wilhoit.comment, nasa.comment)

        # nasa to wilhoi performed in wilhoitTest

    def test_nasa_as_dict_full(self):
        """
        Test that NASA.as_dict functions properly with all attributes
        """
        nasa_dict = self.nasa.as_dict()
        self.assertEqual(nasa_dict['E0']['value'], self.E0)
        self.assertEqual(nasa_dict['Tmin']['value'], self.Tmin)
        self.assertEqual(nasa_dict['Tmax']['value'], self.Tmax)
        self.assertEqual(nasa_dict['comment'], self.comment)
        self.assertTupleEqual(tuple(nasa_dict['polynomials']['polynomial1']['coeffs']['object']),
                              tuple(self.coeffs_low))
        self.assertTupleEqual(tuple(nasa_dict['polynomials']['polynomial2']['coeffs']['object']),
                              tuple(self.coeffs_high))
        self.assertEqual(nasa_dict['polynomials']['polynomial1']['Tmin']['value'], self.Tmin)
        self.assertEqual(nasa_dict['polynomials']['polynomial1']['Tmax']['value'], self.Tint)
        self.assertEqual(nasa_dict['polynomials']['polynomial2']['Tmin']['value'], self.Tint)
        self.assertEqual(nasa_dict['polynomials']['polynomial2']['Tmax']['value'], self.Tmax)

    def test_nasa_as_dict_minimal(self):
        """
        Test that NASA.as_dict does not contain empty, optional attributes
        """
        nasa_dict = NASA().as_dict()
        keys = list(nasa_dict.keys())
        self.assertNotIn('Tmin', keys)
        self.assertNotIn('Tmax', keys)
        self.assertNotIn('E0', keys)
        self.assertNotIn('Cp0', keys)
        self.assertNotIn('CpInf', keys)
        self.assertNotIn('label', keys)
        self.assertNotIn('comment', keys)

    def test_nasa_polynomial_as_dict(self):
        """
        Test that NASAPolynomial.as_dict returns all non-empty, non-redundant attributes properly.
        """
        nasa_poly_dict = self.nasa.polynomials[0].as_dict()
        self.assertEqual(nasa_poly_dict, {'coeffs': {'object': [4.03055, -0.00214171, 4.90611e-05, -5.99027e-08,
                                                                2.38945e-11, -11257.6, 3.5613],
                                                     'class': 'np_array'},
                                          'Tmax': {'units': 'K', 'class': 'ScalarQuantity', 'value': 650.73},
                                          'Tmin': {'units': 'K', 'class': 'ScalarQuantity', 'value': 300.0},
                                          'class': 'NASAPolynomial'}
                         )

    def test_make_nasa(self):
        """
        Test that a NASA object can be reconstructed from a dictionary (also test NASAPolynomial by extension)
        """
        nasa_dict = self.nasa.as_dict()
        new_nasa = NASA.__new__(NASA)
        class_dictionary = {'ScalarQuantity': ScalarQuantity,
                            'np_array': np.array,
                            'NASA': NASA,
                            'NASAPolynomial': NASAPolynomial,
                            }

        new_nasa.make_object(nasa_dict, class_dictionary)


################################################################################


if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(verbosity=2))
