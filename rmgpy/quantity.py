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
This module contains classes and methods for working with physical quantities,
particularly the :class:`Quantity` class for representing physical quantities.
"""

import logging

import cython
import numpy as np
import quantities as pq

import rmgpy.constants as constants
from rmgpy.exceptions import QuantityError
from rmgpy.rmgobject import RMGObject, expand_to_dict

################################################################################

# Explicitly set the default units to SI
pq.set_default_units('si')

# These units are not defined by the quantities package, but occur frequently
# in data handled by RMG, so we define them manually
pq.UnitQuantity('kilocalories', pq.cal * 1e3, symbol='kcal')
pq.UnitQuantity('kilojoules', pq.J * 1e3, symbol='kJ')
pq.UnitQuantity('kilomoles', pq.mol * 1e3, symbol='kmol')
pq.UnitQuantity('molecule', pq.mol / 6.02214179e23, symbol='molecule')
pq.UnitQuantity('molecules', pq.mol / 6.02214179e23, symbol='molecules')
pq.UnitQuantity('debye', 1.0 / (constants.c * 1e21) * pq.C * pq.m, symbol='De')

################################################################################

# Units that should not be used in RMG-Py:
NOT_IMPLEMENTED_UNITS = [
    'degC',
    'C',
    'degF',
    'F',
    'degR',
    'R'
]


################################################################################

class Units(RMGObject):
    """
    The :class:`Units` class provides a representation of the units of a
    physical quantity. The attributes are:

    =================== ========================================================
    Attribute           Description
    =================== ========================================================
    `units`             A string representation of the units
    =================== ========================================================

    Functions that return the conversion factors to and from SI units are
    provided.
    """

    # A dict of conversion factors (to SI) for each of the frequent units
    # Here we also define that cm^-1 is not to be converted to m^-1 (or Hz, J, K, etc.)
    conversionFactors = {'cm^-1': 1.0}

    def __init__(self, units=''):
        if units in NOT_IMPLEMENTED_UNITS:
            raise NotImplementedError(
                'The units {} are not yet supported. Please choose SI units.'.format(units)
            )
        self.units = units

    def get_conversion_factor_to_si(self):
        """
        Return the conversion factor for converting a quantity in a given set
        of`units` to the SI equivalent units.
        """
        try:
            # Process several common units manually for speed
            factor = Units.conversionFactors[self.units]
        except KeyError:
            # Fall back to (slow!) quantities package for less common units
            factor = float(pq.Quantity(1.0, self.units).simplified)
            # Cache the conversion factor so we don't ever need to use
            # quantities to compute it again
            Units.conversionFactors[self.units] = factor
        return factor

    def get_conversion_factor_from_si(self):
        """
        Return the conversion factor for converting a quantity to a given set
        of `units` from the SI equivalent units.
        """
        return 1.0 / self.get_conversion_factor_to_si()

    # A dict of conversion factors from SI (with same dimensionality as keys)
    # to combinations of cm/mol/s which is like SI except cm instead of m. Used as a cache.
    conversion_factors_from_si_to_cm_mol_s = {'s^-1': 1.0}

    def get_conversion_factor_from_si_to_cm_mol_s(self):
        """
        Return the conversion factor for converting into SI units
        only with all lengths in cm, instead of m.
        This is useful for outputting chemkin file kinetics.
        Depending on the stoichiometry of the reaction the reaction rate
        coefficient could be /s, cm^3/mol/s, cm^6/mol^2/s, and for
        heterogeneous reactions even more possibilities.
        Only lengths are changed. Everything else is in SI, i.e.
        moles (not molecules) and seconds (not minutes).
        """
        cython.declare(factor=cython.double, metres=cython.int)
        try:
            factor = Units.conversion_factors_from_si_to_cm_mol_s[self.units]
        except KeyError:
            # Fall back to (slower) quantities package for units not seen before
            dimensionality = pq.Quantity(1.0, self.units).simplified.dimensionality
            metres = dimensionality.get(pq.m, 0)
            factor = 100 ** metres

            # Cache the conversion factor so we don't ever need to use
            # quantities to compute it again
            Units.conversion_factors_from_si_to_cm_mol_s[self.units] = factor
        return factor


################################################################################

class ScalarQuantity(Units):
    """
    The :class:`ScalarQuantity` class provides a representation of a scalar
    physical quantity, with optional units and uncertainty information. The
    attributes are:

    =================== ========================================================
    Attribute           Description
    =================== ========================================================
    `value`             The numeric value of the quantity in the given units
    `units`             The units the value was specified in
    `uncertainty`       The numeric uncertainty in the value in the given units (unitless if multiplicative)
    `uncertainty_type`   The type of uncertainty: ``'+|-'`` for additive, ``'*|/'`` for multiplicative
    `value_si`          The numeric value of the quantity in the corresponding SI units
    `uncertainty_si`    The numeric value of the uncertainty in the corresponding SI units (unitless if multiplicative)
    =================== ========================================================

    It is often more convenient to perform computations using SI units instead
    of the given units of the quantity. For this reason, the SI equivalent of
    the `value` attribute can be directly accessed using the `value_si`
    attribute. This value is cached on the :class:`ScalarQuantity` object for
    speed.
    """

    def __init__(self, value=0.0, units='', uncertainty=0.0, uncertainty_type='+|-'):
        if value is None:
            value = 0.0
        Units.__init__(self, units)
        self.value = value
        self.uncertainty_type = uncertainty_type
        self.uncertainty = float(uncertainty)

    def __reduce__(self):
        """
        Return a tuple of information used to pickle the scalar quantity.
        """
        return (ScalarQuantity, (self.value, self.units, self.uncertainty, self.uncertainty_type))

    def __str__(self):
        """
        Return a string representation of the scalar quantity.
        """
        result = '{0:g}'.format(self.value)
        if self.uncertainty != 0.0:
            result += ' {0} {1:g}'.format(self.uncertainty_type, self.uncertainty)
        if self.units != '':
            result += ' {0}'.format(self.units)
        return result

    def __repr__(self):
        """
        Return a string representation that can be used to reconstruct the
        scalar quantity.
        """
        if self.units == '' and self.uncertainty == 0.0:
            return '{0:g}'.format(self.value)
        else:
            result = '({0:g},{1!r}'.format(self.value, self.units)
            if self.uncertainty != 0.0:
                result += ',{0!r},{1:g}'.format(self.uncertainty_type, self.uncertainty)
            result += ')'
            return result

    def as_dict(self):
        """
        A helper function for YAML dumping
        """
        output_dict = dict()
        output_dict['class'] = self.__class__.__name__
        output_dict['value'] = self.value
        if self.units != '':
            output_dict['units'] = self.units
        if self.uncertainty != 0.0:
            output_dict['uncertainty'] = self.uncertainty
            output_dict['uncertainty_type'] = self.uncertainty_type
        return output_dict

    def copy(self):
        """
        Return a copy of the quantity.
        """
        return ScalarQuantity(self.value, self.units, self.uncertainty, self.uncertainty_type)

    @property
    def value(self):
        """
        The numeric value of the quantity, in the given units
        """
        return self.value_si * self.get_conversion_factor_from_si()

    @value.setter
    def value(self, v):
        self.value_si = float(v) * self.get_conversion_factor_to_si()

    @property
    def uncertainty(self):
        """
        The numeric value of the uncertainty, in the given units if additive, or no units if multiplicative.
        """
        if self.is_uncertainty_additive():
            return self.uncertainty_si * self.get_conversion_factor_from_si()
        else:
            return self.uncertainty_si

    @uncertainty.setter
    def uncertainty(self, v):
        if self.is_uncertainty_additive():
            self.uncertainty_si = float(v) * self.get_conversion_factor_to_si()
        else:
            self.uncertainty_si = float(v)

    @property
    def uncertainty_type(self):
        """
        The type of uncertainty: ``'+|-'`` for additive, ``'*|/'`` for multiplicative
        """
        return self._uncertainty_type

    @uncertainty_type.setter
    def uncertainty_type(self, v):
        """
        Check the uncertainty type is valid, then set it.
        """
        if v not in ['+|-', '*|/']:
            raise QuantityError('Unexpected uncertainty type "{0}"; valid values are "+|-" and "*|/".'.format(v))
        self._uncertainty_type = v

    def equals(self, quantity):
        """
        Return ``True`` if the everything in a quantity object matches
        the parameters in this object.  If there are lists of values or uncertainties,
        each item in the list must be matching and in the same order.
        Otherwise, return ``False``
        (Originally intended to return warning if units capitalization was
        different, however, Quantity object only parses units matching in case, so
        this will not be a problem.)
        """

        def approx_equal(x, y, atol=.01):
            """
            Returns true if two float/double values are approximately equal
            within a relative error of 1% or under a user specific absolute tolerance.
            """
            return abs(x - y) <= 1e-2 * abs(x) or abs(x - y) <= 1e-2 * abs(y) or abs(x - y) <= atol

        if isinstance(quantity, ScalarQuantity):
            if (self.uncertainty_type == quantity.uncertainty_type and
                    approx_equal(self.uncertainty * self.get_conversion_factor_to_si(),
                                 quantity.uncertainty * quantity.get_conversion_factor_to_si()) and
                    self.units == quantity.units):

                if self.units == "kcal/mol":
                    # set absolute tolerance to .01 kcal/mol = 42 J/mol
                    atol = 42
                else:
                    # for other units, set it to .01
                    atol = .01

                if not approx_equal(self.value_si, quantity.value_si, atol):
                    return False

                return True

        return False

    def is_uncertainty_additive(self):
        """
        Return ``True`` if the uncertainty is specified in additive format
        and ``False`` otherwise.
        """
        return self.uncertainty_type == '+|-'

    def is_uncertainty_multiplicative(self):
        """
        Return ``True`` if the uncertainty is specified in multiplicative 
        format and ``False`` otherwise.
        """
        return self.uncertainty_type == '*|/'


################################################################################


class ArrayQuantity(Units):
    """
    The :class:`ArrayQuantity` class provides a representation of an array of
    physical quantity values, with optional units and uncertainty information. 
    The attributes are:

    =================== ========================================================
    Attribute           Description
    =================== ========================================================
    `value`             The numeric value of the quantity in the given units
    `units`             The units the value was specified in
    `uncertainty`       The numeric uncertainty in the value (unitless if multiplicative)
    `uncertainty_type`   The type of uncertainty: ``'+|-'`` for additive, ``'*|/'`` for multiplicative
    `value_si`          The numeric value of the quantity in the corresponding SI units
    `uncertainty_si`    The numeric value of the uncertainty in the corresponding SI units (unitless if multiplicative)
    =================== ========================================================

    It is often more convenient to perform computations using SI units instead
    of the given units of the quantity. For this reason, the SI equivalent of
    the `value` attribute can be directly accessed using the `value_si`
    attribute. This value is cached on the :class:`ArrayQuantity` object for 
    speed.
    """

    def __init__(self, value=None, units='', uncertainty=None, uncertainty_type='+|-'):
        Units.__init__(self, units)
        self.value = value if value is not None else np.array([0.0])
        self.uncertainty_type = uncertainty_type
        if uncertainty is None or np.array_equal(uncertainty, np.array([0.0])):
            self.uncertainty = np.zeros_like(self.value)
        elif isinstance(uncertainty, (int, float)):
            self.uncertainty = np.ones_like(self.value) * uncertainty
        else:
            uncertainty = np.array(uncertainty)
            if uncertainty.ndim != self.value.ndim:
                raise QuantityError('The given uncertainty has {0:d} dimensions, while the given value has {1:d}'
                                    ' dimensions.'.format(uncertainty.ndim, self.value.ndim))
            for i in range(self.value.ndim):
                if self.value.shape[i] != uncertainty.shape[i]:
                    raise QuantityError('Dimension {0:d} has {1:d} elements for the given value, but {2:d} elements for'
                                        ' the given uncertainty.'.format(i, self.value.shape[i], uncertainty.shape[i]))
            else:
                self.uncertainty = uncertainty

    def __reduce__(self):
        """
        Return a tuple of information used to pickle the array quantity.
        """
        return (ArrayQuantity, (self.value, self.units, self.uncertainty, self.uncertainty_type))

    def __str__(self):
        """
        Return a string representation of the array quantity.
        """
        if self.value.ndim == 1:
            value = '[{0}]'.format(','.join(['{0:g}'.format(float(v)) for v in self.value]))
        elif self.value.ndim == 2:
            value = []
            for i in range(self.value.shape[0]):
                value.append('[{0}]'.format(','.join(['{0:g}'.format(float(self.value[i, j])) for j in
                                                      range(self.value.shape[1])])))
            value = '[{0}]'.format(','.join(value))

        if self.uncertainty.ndim == 1:
            uncertainty = '[{0}]'.format(','.join(['{0:g}'.format(float(v)) for v in self.uncertainty]))
        elif self.uncertainty.ndim == 2:
            uncertainty = []
            for i in range(self.uncertainty.shape[0]):
                uncertainty.append('[{0}]'.format(','.join(['{0:g}'.format(float(self.uncertainty[i, j])) for j in
                                                            range(self.uncertainty.shape[1])])))
            uncertainty = '[{0}]'.format(','.join(uncertainty))

        result = '{0}'.format(value)
        if (self.uncertainty > 0).any():
            result += ' {0} {1}'.format(self.uncertainty_type, uncertainty)
        if self.units != '':
            result += ' {0}'.format(self.units)
        return result

    def __repr__(self):
        """
        Return a string representation that can be used to reconstruct the
        array quantity.
        """
        if self.value.ndim == 1:
            value = '[{0}]'.format(','.join(['{0:g}'.format(float(v)) for v in self.value]))
        elif self.value.ndim == 2:
            value = []
            for i in range(self.value.shape[0]):
                value.append('[{0}]'.format(','.join(['{0:g}'.format(float(self.value[i, j])) for j in
                                                      range(self.value.shape[1])])))
            value = '[{0}]'.format(','.join(value))

        if self.uncertainty.ndim == 1:
            uncertainty = '[{0}]'.format(','.join(['{0:g}'.format(float(v)) for v in self.uncertainty]))
        elif self.uncertainty.ndim == 2:
            uncertainty = []
            for i in range(self.uncertainty.shape[0]):
                uncertainty.append('[{0}]'.format(','.join(['{0:g}'.format(float(self.uncertainty[i, j])) for j in
                                                            range(self.uncertainty.shape[1])])))
            uncertainty = '[{0}]'.format(','.join(uncertainty))

        if self.units == '' and not np.any(self.uncertainty != 0.0):
            return '{0}'.format(value)
        else:
            result = '({0},{1!r}'.format(value, self.units)
            if np.any(self.uncertainty != 0.0):
                result += ',{0!r},{1}'.format(self.uncertainty_type, uncertainty)
            result += ')'
            return result

    def as_dict(self):
        """
        A helper function for YAML dumping
        """
        output_dict = dict()
        output_dict['class'] = self.__class__.__name__
        output_dict['value'] = expand_to_dict(self.value)
        if self.units != '':
            output_dict['units'] = self.units
        if self.uncertainty is not None and any([val != 0.0 for val in np.nditer(self.uncertainty)]):
            logging.info(self.uncertainty)
            logging.info(type(self.uncertainty))
            output_dict['uncertainty'] = expand_to_dict(self.uncertainty)
            output_dict['uncertainty_type'] = self.uncertainty_type
        return output_dict

    def copy(self):
        """
        Return a copy of the quantity.
        """
        return ArrayQuantity(self.value.copy(), self.units, self.uncertainty.copy(), self.uncertainty_type)

    @property
    def value(self):
        """
        The numeric value of the array quantity, in the given units.
        """
        return self.value_si * self.get_conversion_factor_from_si()

    @value.setter
    def value(self, v):
        if isinstance(v, float):
            self.value_si = np.array([v]) * self.get_conversion_factor_to_si()
        else:
            self.value_si = np.array(v) * self.get_conversion_factor_to_si()

    @property
    def uncertainty(self):
        """
        The numeric value of the uncertainty, in the given units if additive, or no units if multiplicative.
        """
        if self.is_uncertainty_additive():
            return self.uncertainty_si * self.get_conversion_factor_from_si()
        else:
            return self.uncertainty_si

    @uncertainty.setter
    def uncertainty(self, v):
        if self.is_uncertainty_additive():
            self.uncertainty_si = np.array(v) * self.get_conversion_factor_to_si()
        else:
            self.uncertainty_si = np.array(v)

    @property
    def uncertainty_type(self):
        """
        The type of uncertainty: ``'+|-'`` for additive, ``'*|/'`` for multiplicative
        """
        return self._uncertainty_type

    @uncertainty_type.setter
    def uncertainty_type(self, v):
        """
        Check the uncertainty type is valid, then set it.
        
        If you set the uncertainty then change the type, we have no idea what to do with 
        the units. This ensures you set the type first.
        """
        if v not in ['+|-', '*|/']:
            raise QuantityError('Unexpected uncertainty type "{0}"; valid values are "+|-" and "*|/".'.format(v))
        self._uncertainty_type = v

    def equals(self, quantity):
        """
        Return ``True`` if the everything in a quantity object matches
        the parameters in this object.  If there are lists of values or uncertainties,
        each item in the list must be matching and in the same order.
        Otherwise, return ``False``
        (Originally intended to return warning if units capitalization was
        different, however, Quantity object only parses units matching in case, so
        this will not be a problem.)
        """

        def approx_equal(x, y, atol=.01):
            """
            Returns true if two float/double values are approximately equal
            within a relative error of 1% or under a user specific absolute tolerance.
            """
            return abs(x - y) <= 1e-2 * abs(x) or abs(x - y) <= 1e-2 * abs(y) or abs(x - y) <= atol

        if isinstance(quantity, ArrayQuantity):
            if (self.uncertainty_type == quantity.uncertainty_type and self.units == quantity.units):

                if self.units == "kcal/mol":
                    # set absolute tolerance to .01 kcal/mol = 42 J/mol
                    atol = 42
                else:
                    # for other units, set it to .01
                    atol = .01

                if self.value.ndim != quantity.value.ndim:
                    return False
                for i in range(self.value.ndim):
                    if self.value.shape[i] != quantity.value.shape[i]:
                        return False
                for v1, v2 in zip(self.value.flat, quantity.value.flat):
                    if not approx_equal(v1, v2, atol):
                        return False

                if self.uncertainty.ndim != quantity.uncertainty.ndim:
                    return False
                for i in range(self.uncertainty.ndim):
                    if self.uncertainty.shape[i] != quantity.uncertainty.shape[i]:
                        return False
                for v1, v2 in zip(self.uncertainty.flat, quantity.uncertainty.flat):
                    if not approx_equal(v1, v2, atol):
                        return False

                return True

        return False

    def is_uncertainty_additive(self):
        """
        Return ``True`` if the uncertainty is specified in additive format
        and ``False`` otherwise.
        """
        return self.uncertainty_type == '+|-'

    def is_uncertainty_multiplicative(self):
        """
        Return ``True`` if the uncertainty is specified in multiplicative 
        format and ``False`` otherwise.
        """
        return self.uncertainty_type == '*|/'


################################################################################

def Quantity(*args, **kwargs):
    """
    Create a :class:`ScalarQuantity` or :class:`ArrayQuantity` object for a
    given physical quantity. The physical quantity can be specified in several
    ways:
    
    * A scalar-like or array-like value (for a dimensionless quantity)
    
    * An array of arguments (including keyword arguments) giving some or all of
      the `value`, `units`, `uncertainty`, and/or `uncertainty_type`.
    
    * A tuple of the form ``(value,)``, ``(value,units)``, 
      ``(value,units,uncertainty)``, or 
      ``(value,units,uncertainty_type,uncertainty)``
    
    * An existing :class:`ScalarQuantity` or :class:`ArrayQuantity` object, for
      which a copy is made
    
    """
    # Initialize attributes
    value = None
    units = ''
    uncertainty_type = '+|-'
    uncertainty = None

    if len(args) == 1 and len(kwargs) == 0 and args[0] is None:
        return None

    # Unpack args if necessary
    if isinstance(args, tuple) and len(args) == 1 and isinstance(args[0], tuple):
        args = args[0]

    # Process args    
    n_args = len(args)
    if n_args == 1 and isinstance(args[0], (ScalarQuantity, ArrayQuantity)):
        # We were given another quantity object, so make a (shallow) copy of it
        other = args[0]
        value = other.value
        units = other.units
        uncertainty_type = other.uncertainty_type
        uncertainty = other.uncertainty
    elif n_args == 1:
        # If one parameter is given, it should be a single value
        value, = args
    elif n_args == 2:
        # If two parameters are given, it should be a value and units
        value, units = args
    elif n_args == 3:
        # If three parameters are given, it should be a value, units and uncertainty
        value, units, uncertainty = args
    elif n_args == 4:
        # If four parameters are given, it should be a value, units, uncertainty type, and uncertainty
        value, units, uncertainty_type, uncertainty = args
    elif n_args != 0:
        raise QuantityError('Invalid parameters {0!r} passed to ArrayQuantity.__init__() method.'.format(args))

    # Process kwargs
    for k, v in kwargs.items():
        if k == 'value':
            if len(args) >= 1:
                raise QuantityError('Multiple values for argument {0} passed to ArrayQuantity.__init__() method.'.format(k))
            else:
                value = v
        elif k == 'units':
            if len(args) >= 2:
                raise QuantityError('Multiple values for argument {0} passed to ArrayQuantity.__init__() method.'.format(k))
            else:
                units = v
        elif k == 'uncertainty':
            if len(args) >= 3:
                raise QuantityError('Multiple values for argument {0} passed to ArrayQuantity.__init__() method.'.format(k))
            else:
                uncertainty = v
        elif k == 'uncertainty_type':
            if len(args) >= 4:
                raise QuantityError('Multiple values for argument {0} passed to ArrayQuantity.__init__() method.'.format(k))
            else:
                uncertainty_type = v
        else:
            raise QuantityError('Invalid keyword argument {0} passed to ArrayQuantity.__init__() method.'.format(k))

    # Process units and uncertainty type parameters
    if uncertainty_type not in ['+|-', '*|/']:
        raise QuantityError('Unexpected uncertainty type "{0}"; valid values are "+|-" and "*|/".'.format(uncertainty_type))

    if isinstance(value, (list, tuple, np.ndarray)):
        return ArrayQuantity(value, units, uncertainty, uncertainty_type)

    try:
        value = float(value)
    except TypeError:
        return ArrayQuantity(value, units, uncertainty, uncertainty_type)

    uncertainty = 0.0 if uncertainty is None else float(uncertainty)
    return ScalarQuantity(value, units, uncertainty, uncertainty_type)


################################################################################

class UnitType(object):
    """
    The :class:`UnitType` class represents a factory for producing
    :class:`ScalarQuantity` or :class:`ArrayQuantity` objects of a given unit
    type, e.g. time, volume, etc.
    """

    def __init__(self, units, common_units=None, extra_dimensionality=None):
        self.units = units
        self.dimensionality = pq.Quantity(1.0, units).simplified.dimensionality
        self.common_units = common_units or []
        self.extra_dimensionality = {}
        if extra_dimensionality:
            for unit, factor in extra_dimensionality.items():
                self.extra_dimensionality[pq.Quantity(1.0, unit).simplified.dimensionality] = factor

    def __call__(self, *args, **kwargs):
        # Make a ScalarQuantity or ArrayQuantity object out of the given parameter
        quantity = Quantity(*args, **kwargs)
        if quantity is None:
            return quantity

        units = quantity.units

        # If the units are in the common units, then we can do the conversion
        # very quickly and avoid the slow calls to the quantities package
        if units == self.units or units in self.common_units:
            return quantity

        # Check that the units are consistent with this unit type
        # This uses the quantities package (slow!)
        units = pq.Quantity(1.0, units)
        dimensionality = units.simplified.dimensionality
        if dimensionality == self.dimensionality:
            pass
        elif dimensionality in self.extra_dimensionality:
            quantity.value_si *= self.extra_dimensionality[dimensionality]
            quantity.units = self.units
        else:
            raise QuantityError('Invalid units {0!r}. Try common units: {1}'.format(quantity.units, self.common_units))

        # Return the Quantity or ArrayQuantity object object
        return quantity


Acceleration = UnitType('m/s^2')

Area = UnitType('m^2')

Concentration = UnitType('mol/m^3')

SurfaceConcentration = UnitType('mol/m^2')

Dimensionless = UnitType('')

DipoleMoment = UnitType('C*m', extra_dimensionality={
    'De': 1.0 / (1.0e21 * constants.c),
})

"We have to allow 'energies' to be created in units of Kelvins, because Chemkin does so"
Energy = Enthalpy = FreeEnergy = UnitType(
    'J/mol',
    common_units=['kJ/mol', 'cal/mol', 'kcal/mol', 'eV/molecule'],
    extra_dimensionality={'K': constants.R,
                         'cm^-1': constants.h * constants.c * 100
                         # the following hack also allows 'J' and 'kJ' etc. to be specified without /mol[ecule]
                         # so is not advisable (and fails unit tests)
                         # 'eV': constants.Na, # allow people to be lazy and neglect the "/molecule"
                         },
)

Entropy = HeatCapacity = UnitType('J/(mol*K)', common_units=['kJ/(mol*K)', 'cal/(mol*K)', 'kcal/(mol*K)'])

Flux = UnitType('mol/(m^2*s)')

Frequency = UnitType('cm^-1', extra_dimensionality={
    's^-1': 1.0 / (constants.c * 100.),
    'Hz': 1.0 / (constants.c * 100.),
    'J': 1.0 / (constants.h * constants.c * 100.),
    'K': constants.kB / (constants.h * constants.c * 100.),
})

Force = UnitType('N')

Inertia = UnitType('kg*m^2')

Length = UnitType('m')

Mass = UnitType('amu', extra_dimensionality={'kg/mol': 1000. * constants.amu})

Momentum = UnitType('kg*m/s^2')

Power = UnitType('W')

Pressure = UnitType('Pa', common_units=['bar', 'atm', 'torr', 'psi', 'mbar'])

Temperature = UnitType('K', common_units=[])

Time = UnitType('s')

Velocity = UnitType('m/s')

Volume = UnitType('m^3')

# Polarizability = UnitType('C*m^2*V^-1')
"""
What's called Polarizability in the transport properties is in fact a polarizability volume,
which is related by $4*\pi*\epsilon_0$ where $\epsilon_0$ is the permittivity of free space.
Rather than mess around with conversions, I suggest we just use "Volume" as the units for 
what we call 'polarizability'. Chemkin expects it in Angstrom^3. We'll store it in m^3.
"""

# RateCoefficient is handled as a special case since it can take various
# units depending on the reaction order
RATECOEFFICIENT_CONVERSION_FACTORS = {
    (1.0 / pq.s).dimensionality: 1.0,
    (pq.m ** 3 / pq.s).dimensionality: 1.0,
    (pq.m ** 6 / pq.s).dimensionality: 1.0,
    (pq.m ** 9 / pq.s).dimensionality: 1.0,
    (pq.m ** 3 / (pq.mol * pq.s)).dimensionality: 1.0,
    (pq.m ** 6 / (pq.mol ** 2 * pq.s)).dimensionality: 1.0,
    (pq.m ** 9 / (pq.mol ** 3 * pq.s)).dimensionality: 1.0,
}
RATECOEFFICIENT_COMMON_UNITS = ['s^-1', 'm^3/(mol*s)', 'cm^3/(mol*s)', 'm^3/(molecule*s)', 'cm^3/(molecule*s)']


def RateCoefficient(*args, **kwargs):
    # Make a ScalarQuantity or ArrayQuantity object out of the given parameter
    quantity = Quantity(*args, **kwargs)
    if quantity is None:
        return quantity

    units = quantity.units

    # If the units are in the common units, then we can do the conversion
    # very quickly and avoid the slow calls to the quantities package
    if units in RATECOEFFICIENT_COMMON_UNITS:
        return quantity

    dimensionality = pq.Quantity(1.0, quantity.units).simplified.dimensionality
    try:
        factor = RATECOEFFICIENT_CONVERSION_FACTORS[dimensionality]
        quantity.value_si *= factor
    except KeyError:
        raise QuantityError('Invalid units {0!r}. Common units: {1}'
                            ''.format(quantity.units, RATECOEFFICIENT_COMMON_UNITS))

    # Return the Quantity or ArrayQuantity object object
    return quantity


# SurfaceRateCoefficient is handled as a special case since it can take various
# units depending on the reaction order
SURFACERATECOEFFICIENT_CONVERSION_FACTORS = {
    (1.0 / pq.s).dimensionality: 1.0,
    (pq.m ** 3 / pq.s).dimensionality: 1.0,
    (pq.m ** 6 / pq.s).dimensionality: 1.0,
    (pq.m ** 9 / pq.s).dimensionality: 1.0,
    (pq.m ** 3 / (pq.mol * pq.s)).dimensionality: 1.0,
    (pq.m ** 6 / (pq.mol ** 2 * pq.s)).dimensionality: 1.0,
    (pq.m ** 9 / (pq.mol ** 3 * pq.s)).dimensionality: 1.0,
    (pq.m ** 2 / pq.s).dimensionality: 1.0,
    (pq.m ** 5 / pq.s).dimensionality: 1.0,
    (pq.m ** 2 / (pq.mol * pq.s)).dimensionality: 1.0,
    (pq.m ** 5 / (pq.mol ** 2 * pq.s)).dimensionality: 1.0,
    (pq.m ** 4 / (pq.mol ** 2 * pq.s)).dimensionality: 1.0,
}
SURFACERATECOEFFICIENT_COMMON_UNITS = [
    's^-1',  # unimolecular
    'm^3/(mol*s)', 'cm^3/(mol*s)', 'm^3/(molecule*s)', 'cm^3/(molecule*s)',  # single site adsorption
    'm^2/(mol*s)', 'cm^2/(mol*s)', 'm^2/(molecule*s)', 'cm^2/(molecule*s)',
    # bimolecular surface (Langmuir-Hinshelwood)
    'm^5/(mol^2*s)', 'cm^5/(mol^2*s)', 'm^5/(molecule^2*s)', 'cm^5/(molecule^2*s)',  # dissociative adsorption
    'm^4/(mol^2*s)', 'cm^4/(mol^2*s)', 'm^4/(molecule^2*s)', 'cm^4/(molecule^2*s)',  # Surface_Bidentate_Dissociation
]


def SurfaceRateCoefficient(*args, **kwargs):
    # Make a ScalarQuantity or ArrayQuantity object out of the given parameter
    quantity = Quantity(*args, **kwargs)
    if quantity is None:
        return quantity

    units = quantity.units

    # If the units are in the common units, then we can do the conversion
    # very quickly and avoid the slow calls to the quantities package
    if units in SURFACERATECOEFFICIENT_COMMON_UNITS:
        return quantity

    dimensionality = pq.Quantity(1.0, quantity.units).simplified.dimensionality
    try:
        factor = SURFACERATECOEFFICIENT_CONVERSION_FACTORS[dimensionality]
        quantity.value_si *= factor
    except KeyError:
        raise QuantityError('Invalid units {0!r}.'.format(quantity.units))

    # Return the Quantity or ArrayQuantity object object
    return quantity
