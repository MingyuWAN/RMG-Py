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
This script contains unit tests of the :mod:`rmgpy.kinetics.arrhenius` module.
"""

import math
import unittest

import numpy as np

import rmgpy.constants as constants
from rmgpy.kinetics.arrhenius import Arrhenius, ArrheniusEP, PDepArrhenius, MultiArrhenius, MultiPDepArrhenius


################################################################################

class TestArrhenius(unittest.TestCase):
    """
    Contains unit tests of the :class:`Arrhenius` class.
    """

    def setUp(self):
        """
        A function run before each unit test in this class.
        """
        self.A = 1.0e12
        self.n = 0.5
        self.Ea = 41.84
        self.T0 = 1.
        self.Tmin = 300.
        self.Tmax = 3000.
        self.comment = 'C2H6'
        self.arrhenius = Arrhenius(
            A=(self.A, "cm^3/(mol*s)"),
            n=self.n,
            Ea=(self.Ea, "kJ/mol"),
            T0=(self.T0, "K"),
            Tmin=(self.Tmin, "K"),
            Tmax=(self.Tmax, "K"),
            comment=self.comment,
        )

    def test_a_factor(self):
        """
        Test that the Arrhenius A property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.A.value_si * 1e6, self.A, delta=1e0)

    def test_n(self):
        """
        Test that the Arrhenius n property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.n.value_si, self.n, 6)

    def test_ea(self):
        """
        Test that the Arrhenius Ea property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.Ea.value_si * 0.001, self.Ea, 6)

    def test_temperature0(self):
        """
        Test that the Arrhenius T0 property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.T0.value_si, self.T0, 6)

    def test_temperature_min(self):
        """
        Test that the Arrhenius Tmin property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.Tmin.value_si, self.Tmin, 6)

    def test_temperature_max(self):
        """
        Test that the Arrhenius Tmax property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.Tmax.value_si, self.Tmax, 6)

    def test_comment(self):
        """
        Test that the Arrhenius comment property was properly set.
        """
        self.assertEqual(self.arrhenius.comment, self.comment)

    def test_is_temperature_valid(self):
        """
        Test the Arrhenius.is_temperature_valid() method.
        """
        Tdata = np.array([200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        validdata = np.array([False, True, True, True, True, True, True, True, True, True], np.bool)
        for T, valid in zip(Tdata, validdata):
            valid0 = self.arrhenius.is_temperature_valid(T)
            self.assertEqual(valid0, valid)

    def test_get_rate_coefficient(self):
        """
        Test the Arrhenius.get_rate_coefficient() method.
        """
        Tlist = np.array([200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        kexplist = np.array(
            [1.6721e-4, 6.8770e1, 5.5803e3, 5.2448e4, 2.0632e5, 5.2285e5, 1.0281e6, 1.7225e6, 2.5912e6, 3.6123e6])
        for T, kexp in zip(Tlist, kexplist):
            kact = self.arrhenius.get_rate_coefficient(T)
            self.assertAlmostEqual(kexp, kact, delta=1e-4 * kexp)

    def test_change_t0(self):
        """
        Test the Arrhenius.change_t0() method.
        """
        Tlist = np.array([300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500])
        k0list = np.array([self.arrhenius.get_rate_coefficient(T) for T in Tlist])
        self.arrhenius.change_t0(300)
        self.assertEqual(self.arrhenius.T0.value_si, 300)
        for T, kexp in zip(Tlist, k0list):
            kact = self.arrhenius.get_rate_coefficient(T)
            self.assertAlmostEqual(kexp, kact, delta=1e-6 * kexp)

    def test_fit_to_data(self):
        """
        Test the Arrhenius.fit_to_data() method.
        """
        Tdata = np.array([300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500])
        kdata = np.array([self.arrhenius.get_rate_coefficient(T) for T in Tdata])
        arrhenius = Arrhenius().fit_to_data(Tdata, kdata, kunits="m^3/(mol*s)")
        self.assertEqual(float(self.arrhenius.T0.value_si), 1)
        for T, k in zip(Tdata, kdata):
            self.assertAlmostEqual(k, arrhenius.get_rate_coefficient(T), delta=1e-6 * k)
        self.assertAlmostEqual(arrhenius.A.value_si, self.arrhenius.A.value_si, delta=1e0)
        self.assertAlmostEqual(arrhenius.n.value_si, self.arrhenius.n.value_si, 1, 4)
        self.assertAlmostEqual(arrhenius.Ea.value_si, self.arrhenius.Ea.value_si, 2)
        self.assertAlmostEqual(arrhenius.T0.value_si, self.arrhenius.T0.value_si, 4)

    def test_pickle(self):
        """
        Test that an Arrhenius object can be pickled and unpickled with no loss
        of information.
        """
        import pickle
        arrhenius = pickle.loads(pickle.dumps(self.arrhenius, -1))
        self.assertAlmostEqual(self.arrhenius.A.value, arrhenius.A.value, delta=1e0)
        self.assertEqual(self.arrhenius.A.units, arrhenius.A.units)
        self.assertAlmostEqual(self.arrhenius.n.value, arrhenius.n.value, 4)
        self.assertAlmostEqual(self.arrhenius.Ea.value, arrhenius.Ea.value, 4)
        self.assertEqual(self.arrhenius.Ea.units, arrhenius.Ea.units)
        self.assertAlmostEqual(self.arrhenius.T0.value, arrhenius.T0.value, 4)
        self.assertEqual(self.arrhenius.T0.units, arrhenius.T0.units)
        self.assertAlmostEqual(self.arrhenius.Tmin.value, arrhenius.Tmin.value, 4)
        self.assertEqual(self.arrhenius.Tmin.units, arrhenius.Tmin.units)
        self.assertAlmostEqual(self.arrhenius.Tmax.value, arrhenius.Tmax.value, 4)
        self.assertEqual(self.arrhenius.Tmax.units, arrhenius.Tmax.units)
        self.assertEqual(self.arrhenius.comment, arrhenius.comment)

    def test_repr(self):
        """
        Test that an Arrhenius object can be reconstructed from its repr()
        output with no loss of information.
        """
        namespace = {}
        exec('arrhenius = {0!r}'.format(self.arrhenius), globals(), namespace)
        self.assertIn('arrhenius', namespace)
        arrhenius = namespace['arrhenius']
        self.assertAlmostEqual(self.arrhenius.A.value, arrhenius.A.value, delta=1e0)
        self.assertEqual(self.arrhenius.A.units, arrhenius.A.units)
        self.assertAlmostEqual(self.arrhenius.n.value, arrhenius.n.value, 4)
        self.assertAlmostEqual(self.arrhenius.Ea.value, arrhenius.Ea.value, 4)
        self.assertEqual(self.arrhenius.Ea.units, arrhenius.Ea.units)
        self.assertAlmostEqual(self.arrhenius.T0.value, arrhenius.T0.value, 4)
        self.assertEqual(self.arrhenius.T0.units, arrhenius.T0.units)
        self.assertAlmostEqual(self.arrhenius.Tmin.value, arrhenius.Tmin.value, 4)
        self.assertEqual(self.arrhenius.Tmin.units, arrhenius.Tmin.units)
        self.assertAlmostEqual(self.arrhenius.Tmax.value, arrhenius.Tmax.value, 4)
        self.assertEqual(self.arrhenius.Tmax.units, arrhenius.Tmax.units)
        self.assertEqual(self.arrhenius.comment, arrhenius.comment)

    def test_change_rate(self):
        """
        Test the Arrhenius.change_rate() method.
        """
        Tlist = np.array([300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500])
        k0list = np.array([self.arrhenius.get_rate_coefficient(T) for T in Tlist])
        self.arrhenius.change_rate(2)
        for T, kexp in zip(Tlist, k0list):
            kact = self.arrhenius.get_rate_coefficient(T)
            self.assertAlmostEqual(2 * kexp, kact, delta=1e-6 * kexp)

    def test_to_cantera_kinetics(self):
        """
        Test that the Arrhenius cantera object can be set properly within 
        a cantera ElementaryReaction object
        """
        ctArrhenius = self.arrhenius.to_cantera_kinetics()
        self.assertAlmostEqual(ctArrhenius.pre_exponential_factor, 1e9, 6)
        self.assertAlmostEqual(ctArrhenius.temperature_exponent, 0.5)
        self.assertAlmostEqual(ctArrhenius.activation_energy, 41.84e6)

    def test_to_arrhenius_ep(self):
        """
        Tests that the Arrhenius object can be converted to ArrheniusEP
        """
        arr_rate = self.arrhenius.get_rate_coefficient(500)
        arr_ep = self.arrhenius.to_arrhenius_ep()
        arr_ep_rate = arr_ep.get_rate_coefficient(500, 10)  # the second number should not matter
        self.assertAlmostEqual(arr_rate, arr_ep_rate)

    def test_to_arrhenius_ep_with_alpha_and_hrxn(self):
        """
        Tests that the Arrhenius object can be converted to ArrheniusEP given parameters
        """
        hrxn = 5
        arr_rate = self.arrhenius.get_rate_coefficient(500)
        arr_ep = self.arrhenius.to_arrhenius_ep(alpha=1, dHrxn=hrxn)
        self.assertAlmostEqual(1., arr_ep.alpha.value_si)
        arr_ep_rate = arr_ep.get_rate_coefficient(500, hrxn)
        self.assertAlmostEqual(arr_rate, arr_ep_rate)

    def test_to_arrhenius_ep_throws_error_with_just_alpha(self):
        with self.assertRaises(Exception):
            self.arrhenius.to_arrhenius_ep(alpha=1)


################################################################################

class TestArrheniusEP(unittest.TestCase):
    """
    Contains unit tests of the :class:`ArrheniusEP` class.
    """

    def setUp(self):
        """
        A function run before each unit test in this class.
        """
        self.A = 1.0e12
        self.n = 0.5
        self.alpha = 0.5
        self.E0 = 41.84
        self.Tmin = 300.
        self.Tmax = 3000.
        self.comment = 'C2H6'
        self.arrhenius = ArrheniusEP(
            A=(self.A, "cm^3/(mol*s)"),
            n=self.n,
            alpha=self.alpha,
            E0=(self.E0, "kJ/mol"),
            Tmin=(self.Tmin, "K"),
            Tmax=(self.Tmax, "K"),
            comment=self.comment,
        )

    def test_a_factor(self):
        """
        Test that the ArrheniusEP A property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.A.value_si * 1e6, self.A, delta=1e0)

    def test_n(self):
        """
        Test that the ArrheniusEP n property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.n.value_si, self.n, 6)

    def test_alpha(self):
        """
        Test that the ArrheniusEP alpha property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.alpha.value_si, self.alpha, 6)

    def test_e0(self):
        """
        Test that the ArrheniusEP E0 property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.E0.value_si * 0.001, self.E0, 6)

    def test_temperature_min(self):
        """
        Test that the ArrheniusEP Tmin property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.Tmin.value_si, self.Tmin, 6)

    def test_temperature_max(self):
        """
        Test that the ArrheniusEP Tmax property was properly set.
        """
        self.assertAlmostEqual(self.arrhenius.Tmax.value_si, self.Tmax, 6)

    def test_comment(self):
        """
        Test that the ArrheniusEP comment property was properly set.
        """
        self.assertEqual(self.arrhenius.comment, self.comment)

    def test_is_temperature_valid(self):
        """
        Test the ArrheniusEP.is_temperature_valid() method.
        """
        Tdata = np.array([200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        validdata = np.array([False, True, True, True, True, True, True, True, True, True], np.bool)
        for T, valid in zip(Tdata, validdata):
            valid0 = self.arrhenius.is_temperature_valid(T)
            self.assertEqual(valid0, valid)

    def test_get_rate_coefficient(self):
        """
        Test the ArrheniusEP.get_rate_coefficient() method.
        """
        Tlist = np.array([200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        kexplist = np.array(
            [1.6721e-4, 6.8770e1, 5.5803e3, 5.2448e4, 2.0632e5, 5.2285e5, 1.0281e6, 1.7225e6, 2.5912e6, 3.6123e6])
        for T, kexp in zip(Tlist, kexplist):
            kact = self.arrhenius.get_rate_coefficient(T, )
            self.assertAlmostEqual(kexp, kact, delta=1e-4 * kexp)

    def test_pickle(self):
        """
        Test that an ArrheniusEP object can be pickled and unpickled with no loss
        of information.
        """
        import pickle
        arrhenius = pickle.loads(pickle.dumps(self.arrhenius, -1))
        self.assertAlmostEqual(self.arrhenius.A.value, arrhenius.A.value, delta=1e0)
        self.assertEqual(self.arrhenius.A.units, arrhenius.A.units)
        self.assertAlmostEqual(self.arrhenius.n.value, arrhenius.n.value, 4)
        self.assertAlmostEqual(self.arrhenius.alpha.value, arrhenius.alpha.value, 4)
        self.assertAlmostEqual(self.arrhenius.E0.value, arrhenius.E0.value, 4)
        self.assertEqual(self.arrhenius.E0.units, arrhenius.E0.units)
        self.assertAlmostEqual(self.arrhenius.Tmin.value, arrhenius.Tmin.value, 4)
        self.assertEqual(self.arrhenius.Tmin.units, arrhenius.Tmin.units)
        self.assertAlmostEqual(self.arrhenius.Tmax.value, arrhenius.Tmax.value, 4)
        self.assertEqual(self.arrhenius.Tmax.units, arrhenius.Tmax.units)
        self.assertEqual(self.arrhenius.comment, arrhenius.comment)

    def test_repr(self):
        """
        Test that an ArrheniusEP object can be reconstructed from its repr()
        output with no loss of information.
        """
        namespace = {}
        exec('arrhenius = {0!r}'.format(self.arrhenius), globals(), namespace)
        self.assertIn('arrhenius', namespace)
        arrhenius = namespace['arrhenius']
        self.assertAlmostEqual(self.arrhenius.A.value, arrhenius.A.value, delta=1e0)
        self.assertEqual(self.arrhenius.A.units, arrhenius.A.units)
        self.assertAlmostEqual(self.arrhenius.n.value, arrhenius.n.value, 4)
        self.assertAlmostEqual(self.arrhenius.alpha.value, arrhenius.alpha.value, 4)
        self.assertAlmostEqual(self.arrhenius.E0.value, arrhenius.E0.value, 4)
        self.assertEqual(self.arrhenius.E0.units, arrhenius.E0.units)
        self.assertAlmostEqual(self.arrhenius.Tmin.value, arrhenius.Tmin.value, 4)
        self.assertEqual(self.arrhenius.Tmin.units, arrhenius.Tmin.units)
        self.assertAlmostEqual(self.arrhenius.Tmax.value, arrhenius.Tmax.value, 4)
        self.assertEqual(self.arrhenius.Tmax.units, arrhenius.Tmax.units)
        self.assertEqual(self.arrhenius.comment, arrhenius.comment)

    def test_change_rate(self):
        """
        Test the ArrheniusEP.change_rate() method.
        """
        Tlist = np.array([300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500])
        k0list = np.array([self.arrhenius.get_rate_coefficient(T) for T in Tlist])
        self.arrhenius.change_rate(2)
        for T, kexp in zip(Tlist, k0list):
            kact = self.arrhenius.get_rate_coefficient(T)
            self.assertAlmostEqual(2 * kexp, kact, delta=1e-6 * kexp)


################################################################################

class TestPDepArrhenius(unittest.TestCase):
    """
    Contains unit tests of the :class:`PDepArrhenius` class.
    """

    def setUp(self):
        """
        A function run before each unit test in this class.
        """
        self.arrhenius0 = Arrhenius(
            A=(1.0e6, "s^-1"),
            n=1.0,
            Ea=(10.0, "kJ/mol"),
            T0=(300.0, "K"),
            Tmin=(300.0, "K"),
            Tmax=(2000.0, "K"),
            comment="""This data is completely made up""",
        )
        self.arrhenius1 = Arrhenius(
            A=(1.0e12, "s^-1"),
            n=1.0,
            Ea=(20.0, "kJ/mol"),
            T0=(300.0, "K"),
            Tmin=(300.0, "K"),
            Tmax=(2000.0, "K"),
            comment="""This data is completely made up""",
        )
        self.pressures = np.array([0.1, 10.0])
        self.arrhenius = [self.arrhenius0, self.arrhenius1]
        self.Tmin = 300.0
        self.Tmax = 2000.0
        self.Pmin = 0.1
        self.Pmax = 10.0
        self.comment = """This data is completely made up"""
        self.kinetics = PDepArrhenius(
            pressures=(self.pressures, "bar"),
            arrhenius=self.arrhenius,
            Tmin=(self.Tmin, "K"),
            Tmax=(self.Tmax, "K"),
            Pmin=(self.Pmin, "bar"),
            Pmax=(self.Pmax, "bar"),
            comment=self.comment,
        )

    def test_pressures(self):
        """
        Test that the PDepArrhenius pressures property was properly set.
        """
        self.assertEqual(len(self.kinetics.pressures.value_si), 2)
        for i in range(2):
            self.assertAlmostEqual(self.kinetics.pressures.value_si[i] * 1e-5, self.pressures[i], 4)

    def test_arrhenius(self):
        """
        Test that the PDepArrhenius arrhenius property was properly set.
        """
        self.assertEqual(len(self.kinetics.arrhenius), 2)
        for i in range(2):
            self.assertAlmostEqual(self.kinetics.arrhenius[i].A.value, self.arrhenius[i].A.value, delta=1e0)
            self.assertEqual(self.kinetics.arrhenius[i].A.units, self.arrhenius[i].A.units)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].n.value, self.arrhenius[i].n.value, 4)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].Ea.value, self.arrhenius[i].Ea.value, 4)
            self.assertEqual(self.kinetics.arrhenius[i].Ea.units, self.arrhenius[i].Ea.units)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].T0.value, self.arrhenius[i].T0.value, 4)
            self.assertEqual(self.kinetics.arrhenius[i].T0.units, self.arrhenius[i].T0.units)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].Tmin.value, self.arrhenius[i].Tmin.value, 4)
            self.assertEqual(self.kinetics.arrhenius[i].Tmin.units, self.arrhenius[i].Tmin.units)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].Tmax.value, self.arrhenius[i].Tmax.value, 4)
            self.assertEqual(self.kinetics.arrhenius[i].Tmax.units, self.arrhenius[i].Tmax.units)
            self.assertEqual(self.kinetics.arrhenius[i].comment, self.arrhenius[i].comment)

    def test_temperature_min(self):
        """
        Test that the PDepArrhenius Tmin property was properly set.
        """
        self.assertAlmostEqual(self.kinetics.Tmin.value_si, self.Tmin, 6)

    def test_temperature_max(self):
        """
        Test that the PDepArrhenius Tmax property was properly set.
        """
        self.assertAlmostEqual(self.kinetics.Tmax.value_si, self.Tmax, 6)

    def test_pressure_min(self):
        """
        Test that the PDepArrhenius Pmin property was properly set.
        """
        self.assertAlmostEqual(self.kinetics.Pmin.value_si * 1e-5, self.Pmin, 6)

    def test_pressure_max(self):
        """
        Test that the PDepArrhenius Pmax property was properly set.
        """
        self.assertAlmostEqual(self.kinetics.Pmax.value_si * 1e-5, self.Pmax, 6)

    def test_comment(self):
        """
        Test that the PDepArrhenius comment property was properly set.
        """
        self.assertEqual(self.kinetics.comment, self.comment)

    def test_is_pressure_dependent(self):
        """
        Test the PDepArrhenius.is_pressure_dependent() method.
        """
        self.assertTrue(self.kinetics.is_pressure_dependent())

    def test_get_rate_coefficient(self):
        """
        Test the PDepArrhenius.get_rate_coefficient() method.
        """
        P = 1e4
        for T in [300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500]:
            k0 = self.kinetics.get_rate_coefficient(T, P)
            k1 = self.arrhenius0.get_rate_coefficient(T)
            self.assertAlmostEqual(k0, k1, delta=1e-6 * k1)
        P = 1e6
        for T in [300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500]:
            k0 = self.kinetics.get_rate_coefficient(T, P)
            k1 = self.arrhenius1.get_rate_coefficient(T)
            self.assertAlmostEqual(k0, k1, delta=1e-6 * k1)
        P = 1e5
        for T in [300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500]:
            k0 = self.kinetics.get_rate_coefficient(T, P)
            k1 = math.sqrt(self.arrhenius0.get_rate_coefficient(T) * self.arrhenius1.get_rate_coefficient(T))
            self.assertAlmostEqual(k0, k1, delta=1e-6 * k1)

    def test_fit_to_data(self):
        """
        Test the PDepArrhenius.fit_to_data() method.
        """
        Tdata = np.array([300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500], np.float)
        Pdata = np.array([1e4, 3e4, 1e5, 3e5, 1e6], np.float)
        kdata = np.zeros([len(Tdata), len(Pdata)], np.float)
        for t in range(len(Tdata)):
            for p in range(len(Pdata)):
                kdata[t, p] = self.kinetics.get_rate_coefficient(Tdata[t], Pdata[p])
        kinetics = PDepArrhenius().fit_to_data(Tdata, Pdata, kdata, kunits="s^-1")
        for t in range(len(Tdata)):
            for p in range(len(Pdata)):
                self.assertAlmostEqual(kinetics.get_rate_coefficient(Tdata[t], Pdata[p]), kdata[t, p],
                                       delta=1e-6 * kdata[t, p])

    def test_pickle(self):
        """
        Test that a PDepArrhenius object can be successfully pickled and
        unpickled with no loss of information.
        """
        import pickle
        kinetics = pickle.loads(pickle.dumps(self.kinetics, -1))
        Narrh = 2
        self.assertEqual(len(self.kinetics.pressures.value), Narrh)
        self.assertEqual(len(kinetics.pressures.value), Narrh)
        self.assertEqual(len(self.kinetics.arrhenius), Narrh)
        self.assertEqual(len(kinetics.arrhenius), Narrh)
        for i in range(Narrh):
            self.assertAlmostEqual(self.kinetics.pressures.value[i], kinetics.pressures.value[i], 4)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].A.value, kinetics.arrhenius[i].A.value, delta=1e0)
            self.assertEqual(self.kinetics.arrhenius[i].A.units, kinetics.arrhenius[i].A.units)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].n.value, kinetics.arrhenius[i].n.value)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].T0.value, kinetics.arrhenius[i].T0.value, 4)
            self.assertEqual(self.kinetics.arrhenius[i].T0.units, kinetics.arrhenius[i].T0.units)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].Ea.value, kinetics.arrhenius[i].Ea.value, 4)
            self.assertEqual(self.kinetics.arrhenius[i].Ea.units, kinetics.arrhenius[i].Ea.units)
        self.assertAlmostEqual(self.kinetics.Tmin.value, kinetics.Tmin.value, 4)
        self.assertEqual(self.kinetics.Tmin.units, kinetics.Tmin.units)
        self.assertAlmostEqual(self.kinetics.Tmax.value, kinetics.Tmax.value, 4)
        self.assertEqual(self.kinetics.Tmax.units, kinetics.Tmax.units)
        self.assertAlmostEqual(self.kinetics.Pmin.value, kinetics.Pmin.value, 4)
        self.assertEqual(self.kinetics.Pmin.units, kinetics.Pmin.units)
        self.assertAlmostEqual(self.kinetics.Pmax.value, kinetics.Pmax.value, 4)
        self.assertEqual(self.kinetics.Pmax.units, kinetics.Pmax.units)
        self.assertEqual(self.kinetics.comment, kinetics.comment)

    def test_repr(self):
        """
        Test that a PDepArrhenius object can be successfully reconstructed
        from its repr() output with no loss of information.
        """
        namespace = {}
        exec('kinetics = {0!r}'.format(self.kinetics), globals(), namespace)
        self.assertIn('kinetics', namespace)
        kinetics = namespace['kinetics']
        Narrh = 2
        self.assertEqual(len(self.kinetics.pressures.value), Narrh)
        self.assertEqual(len(kinetics.pressures.value), Narrh)
        self.assertEqual(len(self.kinetics.arrhenius), Narrh)
        self.assertEqual(len(kinetics.arrhenius), Narrh)
        for i in range(Narrh):
            self.assertAlmostEqual(self.kinetics.pressures.value[i], kinetics.pressures.value[i], 4)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].A.value, kinetics.arrhenius[i].A.value, delta=1e0)
            self.assertEqual(self.kinetics.arrhenius[i].A.units, kinetics.arrhenius[i].A.units)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].n.value, kinetics.arrhenius[i].n.value)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].T0.value, kinetics.arrhenius[i].T0.value, 4)
            self.assertEqual(self.kinetics.arrhenius[i].T0.units, kinetics.arrhenius[i].T0.units)
            self.assertAlmostEqual(self.kinetics.arrhenius[i].Ea.value, kinetics.arrhenius[i].Ea.value, 4)
            self.assertEqual(self.kinetics.arrhenius[i].Ea.units, kinetics.arrhenius[i].Ea.units)
        self.assertAlmostEqual(self.kinetics.Tmin.value, kinetics.Tmin.value, 4)
        self.assertEqual(self.kinetics.Tmin.units, kinetics.Tmin.units)
        self.assertAlmostEqual(self.kinetics.Tmax.value, kinetics.Tmax.value, 4)
        self.assertEqual(self.kinetics.Tmax.units, kinetics.Tmax.units)
        self.assertAlmostEqual(self.kinetics.Pmin.value, kinetics.Pmin.value, 4)
        self.assertEqual(self.kinetics.Pmin.units, kinetics.Pmin.units)
        self.assertAlmostEqual(self.kinetics.Pmax.value, kinetics.Pmax.value, 4)
        self.assertEqual(self.kinetics.Pmax.units, kinetics.Pmax.units)
        self.assertEqual(self.kinetics.comment, kinetics.comment)

    def test_change_rate(self):
        """
        Test the PDepArrhenius.change_rate() method.
        """
        Tlist = np.array([300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500])
        k0list = np.array([self.kinetics.get_rate_coefficient(T, 1e5) for T in Tlist])
        self.kinetics.change_rate(2)
        for T, kexp in zip(Tlist, k0list):
            kact = self.kinetics.get_rate_coefficient(T, 1e5)
            self.assertAlmostEqual(2 * kexp, kact, delta=1e-6 * kexp)


################################################################################

class TestMultiArrhenius(unittest.TestCase):
    """
    Contains unit tests of the :class:`MultiArrhenius` class.
    """

    def setUp(self):
        """
        A function run before each unit test in this class.
        """
        self.Tmin = 350.
        self.Tmax = 1500.
        self.comment = 'Comment'
        self.arrhenius = [
            Arrhenius(
                A=(9.3e-14, "cm^3/(molecule*s)"),
                n=0.0,
                Ea=(4740 * constants.R * 0.001, "kJ/mol"),
                T0=(1, "K"),
                Tmin=(self.Tmin, "K"),
                Tmax=(self.Tmax, "K"),
                comment=self.comment,
            ),
            Arrhenius(
                A=(1.4e-9, "cm^3/(molecule*s)"),
                n=0.0,
                Ea=(11200 * constants.R * 0.001, "kJ/mol"),
                T0=(1, "K"),
                Tmin=(self.Tmin, "K"),
                Tmax=(self.Tmax, "K"),
                comment=self.comment,
            ),
        ]
        self.kinetics = MultiArrhenius(
            arrhenius=self.arrhenius,
            Tmin=(self.Tmin, "K"),
            Tmax=(self.Tmax, "K"),
            comment=self.comment,
        )
        self.single_kinetics = MultiArrhenius(
            arrhenius=self.arrhenius[:1],
            Tmin=(self.Tmin, "K"),
            Tmax=(self.Tmax, "K"),
            comment=self.comment,
        )

    def test_arrhenius(self):
        """
        Test that the MultiArrhenius A property was properly set.
        """
        self.assertEqual(self.kinetics.arrhenius, self.arrhenius)

    def test_temperature_min(self):
        """
        Test that the MultiArrhenius Tmin property was properly set.
        """
        self.assertAlmostEqual(self.kinetics.Tmin.value_si, self.Tmin, 6)

    def test_temperature_max(self):
        """
        Test that the MultiArrhenius Tmax property was properly set.
        """
        self.assertAlmostEqual(self.kinetics.Tmax.value_si, self.Tmax, 6)

    def test_comment(self):
        """
        Test that the MultiArrhenius comment property was properly set.
        """
        self.assertEqual(self.kinetics.comment, self.comment)

    def test_is_temperature_valid(self):
        """
        Test the MultiArrhenius.is_temperature_valid() method.
        """
        Tdata = np.array([200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        validdata = np.array([False, True, True, True, True, True, True, False, False, False], np.bool)
        for T, valid in zip(Tdata, validdata):
            valid0 = self.kinetics.is_temperature_valid(T)
            self.assertEqual(valid0, valid)

    def test_get_rate_coefficient(self):
        """
        Test the MultiArrhenius.get_rate_coefficient() method.
        """
        Tlist = np.array([200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        kexplist = np.array(
            [2.85400e-06, 4.00384e-01, 2.73563e+01, 8.50699e+02, 1.20181e+04, 7.56312e+04, 2.84724e+05, 7.71702e+05,
             1.67743e+06, 3.12290e+06])
        for T, kexp in zip(Tlist, kexplist):
            kact = self.kinetics.get_rate_coefficient(T)
            self.assertAlmostEqual(kexp, kact, delta=1e-4 * kexp)

    def test_pickle(self):
        """
        Test that a MultiArrhenius object can be pickled and unpickled with no loss
        of information.
        """
        import pickle
        kinetics = pickle.loads(pickle.dumps(self.kinetics, -1))
        self.assertEqual(len(self.kinetics.arrhenius), len(kinetics.arrhenius))
        for arrh0, arrh in zip(self.kinetics.arrhenius, kinetics.arrhenius):
            self.assertAlmostEqual(arrh0.A.value, arrh.A.value, delta=1e-18)
            self.assertEqual(arrh0.A.units, arrh.A.units)
            self.assertAlmostEqual(arrh0.n.value, arrh.n.value, 4)
            self.assertAlmostEqual(arrh0.Ea.value, arrh.Ea.value, 4)
            self.assertEqual(arrh0.Ea.units, arrh.Ea.units)
            self.assertAlmostEqual(arrh0.T0.value, arrh.T0.value, 4)
            self.assertEqual(arrh0.T0.units, arrh.T0.units)
        self.assertAlmostEqual(self.kinetics.Tmin.value, kinetics.Tmin.value, 4)
        self.assertEqual(self.kinetics.Tmin.units, kinetics.Tmin.units)
        self.assertAlmostEqual(self.kinetics.Tmax.value, kinetics.Tmax.value, 4)
        self.assertEqual(self.kinetics.Tmax.units, kinetics.Tmax.units)
        self.assertEqual(self.kinetics.comment, kinetics.comment)

    def test_repr(self):
        """
        Test that a MultiArrhenius object can be reconstructed from its repr()
        output with no loss of information.
        """
        namespace = {}
        exec('kinetics = {0!r}'.format(self.kinetics), globals(), namespace)
        self.assertIn('kinetics', namespace)
        kinetics = namespace['kinetics']
        self.assertEqual(len(self.kinetics.arrhenius), len(kinetics.arrhenius))
        for arrh0, arrh in zip(self.kinetics.arrhenius, kinetics.arrhenius):
            self.assertAlmostEqual(arrh0.A.value, arrh.A.value, delta=1e-18)
            self.assertEqual(arrh0.A.units, arrh.A.units)
            self.assertAlmostEqual(arrh0.n.value, arrh.n.value, 4)
            self.assertAlmostEqual(arrh0.Ea.value, arrh.Ea.value, 4)
            self.assertEqual(arrh0.Ea.units, arrh.Ea.units)
            self.assertAlmostEqual(arrh0.T0.value, arrh.T0.value, 4)
            self.assertEqual(arrh0.T0.units, arrh.T0.units)
        self.assertAlmostEqual(self.kinetics.Tmin.value, kinetics.Tmin.value, 4)
        self.assertEqual(self.kinetics.Tmin.units, kinetics.Tmin.units)
        self.assertAlmostEqual(self.kinetics.Tmax.value, kinetics.Tmax.value, 4)
        self.assertEqual(self.kinetics.Tmax.units, kinetics.Tmax.units)
        self.assertEqual(self.kinetics.comment, kinetics.comment)

    def test_to_arrhenius(self):
        """
        Test that we can convert to an Arrhenius
        """
        answer = self.single_kinetics.arrhenius[0]
        fitted = self.single_kinetics.to_arrhenius()

        self.assertAlmostEqual(fitted.A.value_si, answer.A.value_si, delta=1e0)
        self.assertAlmostEqual(fitted.n.value_si, answer.n.value_si, 1, 4)
        self.assertAlmostEqual(fitted.Ea.value_si, answer.Ea.value_si, 2)
        self.assertAlmostEqual(fitted.T0.value_si, answer.T0.value_si, 4)

    def test_to_arrhenius_temperature_range(self):
        """
        Test the to_arrhenius temperature range is set correctly.
        """
        answer = self.single_kinetics.arrhenius[0]
        fitted = self.single_kinetics.to_arrhenius(Tmin=800, Tmax=1200)
        self.assertAlmostEqual(fitted.Tmin.value_si, 800.0)
        self.assertAlmostEqual(fitted.Tmax.value_si, 1200.0)
        for T in [800, 1000, 1200]:
            self.assertAlmostEqual(fitted.get_rate_coefficient(T) / answer.get_rate_coefficient(T), 1.0)

    def test_to_arrhenius_multiple(self):
        """
        Test the to_arrhenius fitting multiple kinetics over a small range, see if we're within 5% at a few points
        """
        answer = self.kinetics
        fitted = self.kinetics.to_arrhenius(Tmin=800, Tmax=1200)
        self.assertAlmostEqual(fitted.Tmin.value_si, 800.0)
        self.assertAlmostEqual(fitted.Tmax.value_si, 1200.0)
        for T in [800, 1000, 1200]:
            self.assertAlmostEqual(fitted.get_rate_coefficient(T) / answer.get_rate_coefficient(T), 1.0, delta=0.05)

    def test_change_rate(self):
        """
        Test the MultiArrhenius.change_rate() method.
        """
        Tlist = np.array([300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500])
        k0list = np.array([self.kinetics.get_rate_coefficient(T) for T in Tlist])
        self.kinetics.change_rate(2)
        for T, kexp in zip(Tlist, k0list):
            kact = self.kinetics.get_rate_coefficient(T)
            self.assertAlmostEqual(2 * kexp, kact, delta=1e-6 * kexp)


################################################################################

class TestMultiPDepArrhenius(unittest.TestCase):
    """
    Contains unit tests of the :class:`MultiPDepArrhenius` class.
    """

    def setUp(self):
        """
        A function run before each unit test in this class.
        """
        self.Tmin = 350.
        self.Tmax = 1500.
        self.Pmin = 1e-1
        self.Pmax = 1e1
        self.pressures = np.array([1e-1, 1e1])
        self.comment = 'CH3 + C2H6 <=> CH4 + C2H5 (Baulch 2005)'
        self.arrhenius = [
            PDepArrhenius(
                pressures=(self.pressures, "bar"),
                arrhenius=[
                    Arrhenius(
                        A=(9.3e-16, "cm^3/(molecule*s)"),
                        n=0.0,
                        Ea=(4740 * constants.R * 0.001, "kJ/mol"),
                        T0=(1, "K"),
                        Tmin=(self.Tmin, "K"),
                        Tmax=(self.Tmax, "K"),
                        comment=self.comment,
                    ),
                    Arrhenius(
                        A=(9.3e-14, "cm^3/(molecule*s)"),
                        n=0.0,
                        Ea=(4740 * constants.R * 0.001, "kJ/mol"),
                        T0=(1, "K"),
                        Tmin=(self.Tmin, "K"),
                        Tmax=(self.Tmax, "K"),
                        comment=self.comment,
                    ),
                ],
                Tmin=(self.Tmin, "K"),
                Tmax=(self.Tmax, "K"),
                Pmin=(self.Pmin, "bar"),
                Pmax=(self.Pmax, "bar"),
                comment=self.comment,
            ),
            PDepArrhenius(
                pressures=(self.pressures, "bar"),
                arrhenius=[
                    Arrhenius(
                        A=(1.4e-11, "cm^3/(molecule*s)"),
                        n=0.0,
                        Ea=(11200 * constants.R * 0.001, "kJ/mol"),
                        T0=(1, "K"),
                        Tmin=(self.Tmin, "K"),
                        Tmax=(self.Tmax, "K"),
                        comment=self.comment,
                    ),
                    Arrhenius(
                        A=(1.4e-9, "cm^3/(molecule*s)"),
                        n=0.0,
                        Ea=(11200 * constants.R * 0.001, "kJ/mol"),
                        T0=(1, "K"),
                        Tmin=(self.Tmin, "K"),
                        Tmax=(self.Tmax, "K"),
                        comment=self.comment,
                    ),
                ],
                Tmin=(self.Tmin, "K"),
                Tmax=(self.Tmax, "K"),
                Pmin=(self.Pmin, "bar"),
                Pmax=(self.Pmax, "bar"),
                comment=self.comment,
            ),
        ]
        self.kinetics = MultiPDepArrhenius(
            arrhenius=self.arrhenius,
            Tmin=(self.Tmin, "K"),
            Tmax=(self.Tmax, "K"),
            Pmin=(self.Pmin, "bar"),
            Pmax=(self.Pmax, "bar"),
            comment=self.comment,
        )

    def test_arrhenius(self):
        """
        Test that the MultiPDepArrhenius arrhenius property was properly set.
        """
        self.assertEqual(self.kinetics.arrhenius, self.arrhenius)

    def test_temperature_min(self):
        """
        Test that the MultiPDepArrhenius Tmin property was properly set.
        """
        self.assertAlmostEqual(self.kinetics.Tmin.value_si, self.Tmin, 6)

    def test_temperature_max(self):
        """
        Test that the MultiPDepArrhenius Tmax property was properly set.
        """
        self.assertAlmostEqual(self.kinetics.Tmax.value_si, self.Tmax, 6)

    def test_pressure_min(self):
        """
        Test that the MultiPDepArrhenius Pmin property was properly set.
        """
        self.assertAlmostEqual(self.kinetics.Pmin.value_si * 1e-5, self.Pmin, 6)

    def test_pressure_max(self):
        """
        Test that the MultiPDepArrhenius Pmax property was properly set.
        """
        self.assertAlmostEqual(self.kinetics.Pmax.value_si * 1e-5, self.Pmax, 6)

    def test_comment(self):
        """
        Test that the MultiPDepArrhenius comment property was properly set.
        """
        self.assertEqual(self.kinetics.comment, self.comment)

    def test_is_temperature_valid(self):
        """
        Test the MultiPDepArrhenius.is_temperature_valid() method.
        """
        Tdata = np.array([200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        validdata = np.array([False, True, True, True, True, True, True, False, False, False], np.bool)
        for T, valid in zip(Tdata, validdata):
            valid0 = self.kinetics.is_temperature_valid(T)
            self.assertEqual(valid0, valid)

    def test_is_pressure_valid(self):
        """
        Test the MultiPDepArrhenius.is_pressure_valid() method.
        """
        Pdata = np.array([1e3, 1e4, 1e5, 1e6, 1e7])
        validdata = np.array([False, True, True, True, False], np.bool)
        for P, valid in zip(Pdata, validdata):
            valid0 = self.kinetics.is_pressure_valid(P)
            self.assertEqual(valid0, valid)

    def test_get_rate_coefficient(self):
        """
        Test the MultiPDepArrhenius.get_rate_coefficient() method.
        """
        Tlist = np.array([200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        Plist = np.array([1e4, 1e5, 1e6])
        kexplist = np.array([
            [2.85400e-08, 4.00384e-03, 2.73563e-01, 8.50699e+00, 1.20181e+02, 7.56312e+02, 2.84724e+03, 7.71702e+03,
             1.67743e+04, 3.12290e+04],
            [2.85400e-07, 4.00384e-02, 2.73563e+00, 8.50699e+01, 1.20181e+03, 7.56312e+03, 2.84724e+04, 7.71702e+04,
             1.67743e+05, 3.12290e+05],
            [2.85400e-06, 4.00384e-01, 2.73563e+01, 8.50699e+02, 1.20181e+04, 7.56312e+04, 2.84724e+05, 7.71702e+05,
             1.67743e+06, 3.12290e+06],
        ]).T
        for i in range(Tlist.shape[0]):
            for j in range(Plist.shape[0]):
                kexp = kexplist[i, j]
                kact = self.kinetics.get_rate_coefficient(Tlist[i], Plist[j])
                self.assertAlmostEqual(kexp, kact, delta=1e-4 * kexp)

    def test_get_rate_coefficient_diff_plist(self):
        """
        Test the MultiPDepArrhenius.get_rate_coefficient() when plists are different.
        """
        # modify the MultiPDepArrhenius object with an additional entry
        pressures = np.array([1e-1, 1e-1, 1e1])
        self.kinetics.arrhenius[0].pressures = (pressures, "bar")
        self.kinetics.arrhenius[0].arrhenius.insert(0, self.kinetics.arrhenius[0].arrhenius[0])

        Tlist = np.array([200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000])
        Plist = np.array([1e4, 1e5, 1e6])
        kexplist = np.array([
            [2.85400e-08, 4.00384e-03, 2.73563e-01, 8.50699e+00, 1.20181e+02, 7.56312e+02, 2.84724e+03, 7.71702e+03,
             1.67743e+04, 3.12290e+04],
            [2.85400e-07, 4.00384e-02, 2.73563e+00, 8.50699e+01, 1.20181e+03, 7.56312e+03, 2.84724e+04, 7.71702e+04,
             1.67743e+05, 3.12290e+05],
            [2.85400e-06, 4.00384e-01, 2.73563e+01, 8.50699e+02, 1.20181e+04, 7.56312e+04, 2.84724e+05, 7.71702e+05,
             1.67743e+06, 3.12290e+06],
        ]).T
        for i in range(Tlist.shape[0]):
            for j in range(Plist.shape[0]):
                kexp = kexplist[i, j]
                kact = self.kinetics.get_rate_coefficient(Tlist[i], Plist[j])
                self.assertAlmostEqual(kexp, kact, delta=1e-4 * kexp)

    def test_pickle(self):
        """
        Test that a MultiPDepArrhenius object can be pickled and unpickled with
        no loss of information.
        """
        import pickle
        kinetics = pickle.loads(pickle.dumps(self.kinetics, -1))
        self.assertEqual(len(self.kinetics.arrhenius), len(kinetics.arrhenius))
        self.assertAlmostEqual(self.kinetics.Tmin.value, kinetics.Tmin.value, 4)
        self.assertEqual(self.kinetics.Tmin.units, kinetics.Tmin.units)
        self.assertAlmostEqual(self.kinetics.Tmax.value, kinetics.Tmax.value, 4)
        self.assertEqual(self.kinetics.Tmax.units, kinetics.Tmax.units)
        self.assertEqual(self.kinetics.comment, kinetics.comment)

    def test_repr(self):
        """
        Test that a MultiPDepArrhenius object can be reconstructed from its
        repr() output with no loss of information.
        """
        namespace = {}
        exec('kinetics = {0!r}'.format(self.kinetics), globals(), namespace)
        self.assertIn('kinetics', namespace)
        kinetics = namespace['kinetics']
        self.assertEqual(len(self.kinetics.arrhenius), len(kinetics.arrhenius))
        self.assertAlmostEqual(self.kinetics.Tmin.value, kinetics.Tmin.value, 4)
        self.assertEqual(self.kinetics.Tmin.units, kinetics.Tmin.units)
        self.assertAlmostEqual(self.kinetics.Tmax.value, kinetics.Tmax.value, 4)
        self.assertEqual(self.kinetics.Tmax.units, kinetics.Tmax.units)
        self.assertEqual(self.kinetics.comment, kinetics.comment)

    def test_change_rate(self):
        """
        Test the PDepMultiArrhenius.change_rate() method.
        """
        Tlist = np.array([300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500])
        k0list = np.array([self.kinetics.get_rate_coefficient(T, 1e5) for T in Tlist])
        self.kinetics.change_rate(2)
        for T, kexp in zip(Tlist, k0list):
            kact = self.kinetics.get_rate_coefficient(T, 1e5)
            self.assertAlmostEqual(2 * kexp, kact, delta=1e-6 * kexp)
