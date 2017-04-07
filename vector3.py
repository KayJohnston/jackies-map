from math import *


class Vector3(object):
    __slots__ = ('_v',)

    def __init__(self, *args):
        """Creates a Vector3 from 3 numeric values or a list-like object
        containing at least 3 values. No arguments result in a null vector.
        """
        if len(args) == 3:
            self._v = [float(args[0]), float(args[1]), float(args[2])]
        elif not args:
            self._v = [0., 0., 0.]
        elif len(args) == 1:
            self._v = [float(args[0][0]), float(args[0][1]), float(args[0][2])]
        else:
            raise ValueError("Vector3.__init__ takes 0, 1 or 3 parameters")

    def copy(self):
        v = self.__new__(self.__class__, object)
        v._v = self._v[:]
        return v

    __copy__ = copy

    def _get_x(self):
        return self._v[0]
    x = property(_get_x, None, None, "x component.")

    def _get_y(self):
        return self._v[1]
    y = property(_get_y, None, None, "y component.")

    def _get_z(self):
        return self._v[2]
    z = property(_get_z, None, None, "z component.")

    def _get_length(self):
        x, y, z = self._v
        return sqrt(x*x + y*y + z*z)
    length = property(_get_length, None, None, "Length of the vector")

    def unit(self):
        """Returns a unit vector."""
        x, y, z = self._v
        l = sqrt(x*x + y*y + z*z)
        return Vector3(x/l, y/l, z/l)

    def __str__(self):
        x, y, z = self._v
        return "[%.4f, %.4f, %.4f]" % (x, y, z)

    def __repr__(self):
        x, y, z = self._v
        return "Vector3(%s, %s, %s)" % (x, y, z)

    def __len__(self):
        return 3

    def __iter__(self):
        return iter(self._v)

    def __getitem__(self, index):
        try:
            return self._v[index]
        except IndexError:
            raise IndexError("There are 3 values in this object, index should be 0, 1 or 2!")

    def __eq__(self, rhs):
        x, y, z = self._v
        xx, yy, zz = rhs
        return (x == xx and y == yy and z == zz)

    def __ne__(self, rhs):
        x, y, z = self._v
        xx, yy, zz = rhs
        return (x != xx or y != yy or z != zz)

    def __hash__(self):
        return hash(tuple(self._v))

    def __add__(self, rhs):
        x, y, z = self._v
        ox, oy, oz = rhs
        return Vector3(x+ox, y+oy, z+oz)
    
    def __iadd__(self, rhs):
        raise TypeError("this class does not allow in-place modifications")

    def __radd__(self, lhs):
        x, y, z = self._v
        ox, oy, oz = lhs
        return Vector3(x+ox, y+oy, z+oz)

    def __sub__(self, rhs):
        x, y, z = self._v
        ox, oy, oz = rhs
        return Vector3(x-ox, y-oy, z-oz)
    
    def __isub__(self, rhs):
        raise TypeError("this class does not allow in-place modifications")

    def __rsub__(self, lhs):
        x, y, z = self._v
        ox, oy, oz = lhs
        return Vector3(ox-x, oy-y, oz-z)

    def __abs__(self):
        x, y, z = self._v
        return Vector3(abs(x), abs(y), abs(z))

    def __mul__(self, rhs):
        x, y, z = self._v
        if hasattr(rhs, "__getitem__"):
            ox, oy, oz = rhs
            return Vector3(x*ox, y*oy, z*oz)
        else:
            return Vector3(x*rhs, y*rhs, z*rhs)

    def __imul__(self, rhs):
        raise TypeError("this class does not allow in-place modifications")

    def __rmul__(self, lhs):
        x, y, z = self._v
        if hasattr(lhs, "__getitem__"):
            ox, oy, oz = lhs
            return Vector3(x*ox, y*oy, z*oz)
        else:
            return Vector3(x*lhs, y*lhs, z*lhs)

    def __div__(self, rhs):
        """Return the result of dividing this vector by another vector, or a scalar (single number)."""
        x, y, z = self._v
        if hasattr(rhs, "__getitem__"):
            ox, oy, oz = rhs
            return Vector3(x/ox, y/oy, z/oz)
        else:
            return Vector3(x/rhs, y/rhs, z/rhs)

    def __floordiv__(self, rhs):
        return self.__div__(rhs)

    def __truediv__(self, rhs):
        return self.__div__(rhs)

    def __idiv__(self, rhs):
        raise TypeError("this class does not allow in-place modifications")

    def __rdiv__(self, lhs):
        x, y, z = self._v
        if hasattr(lhs, "__getitem__"):
            ox, oy, oz = lhs
            return Vector3(ox/x, oy/y, oz/z)
        else:
            return Vector3(lhs/x, lhs/y, lhs/z)

    def __neg__(self):
        x, y, z = self._v
        return Vector3(-x, -y, -z)

    def __pos__(self):
        return self.copy()

    def __nonzero__(self):
        x, y, z = self._v
        return x and y and z

    def __bool__(self):
        return self.__nonzero__()

    def __call__(self, keys):
        """Returns a tuple of the values in a vector

        keys -- An iterable containing the keys (x, y or z)
        eg v = Vector3(1.0, 2.0, 3.0)
        v('zyx') -> (3.0, 2.0, 1.0)
        """
        ord_x = ord('x')
        v = self._v
        return tuple(v[ord(c)-ord_x] for c in keys)

    def as_tuple(self):
        return tuple(self._v)

    def get_normalised(self):
        x, y, z = self._v
        l = sqrt(x*x + y*y + z*z)
        return Vector3(x/l, y/l, z/l)
    get_normalized = get_normalised

    def dot(self, other):
        x, y, z = self._v
        ox, oy, oz = other
        return x*ox + y*oy + z*oz

    def cross(self, other):
        x, y, z = self._v
        bx, by, bz = other
        return Vector3(y*bz - by*z, z*bx - bz*x, x*by - bx*y)

    def cross_tuple(self, other):
        x, y, z = self._v
        bx, by, bz = other
        return (y*bz - by*z, z*bx - bz*x, x*by - bx*y)

    def angle_to(self, other):
        """Returns the angle, in radians, between this vector and another."""
        dot_p = self.get_normalised().dot(other.get_normalised())
        if abs(dot_p - 1.0) < 0.000001:
          return 0.0
        else:
          return acos(dot_p)


class Vector3M(Vector3):
    def __init__(self, *args):
        super(Vector3M, self).__init__(*args)

    def _set_x(self, x):
        assert isinstance(x, float), "Must be a float"
        self._v[0] = x
    x = property(Vector3._get_x, _set_x, None, "x component.")

    def _set_y(self, y):
        assert isinstance(y, float), "Must be a float"
        self._v[1] = y
    y = property(Vector3._get_y, _set_y, None, "y component.")

    def _set_z(self, z):
        assert isinstance(z, float), "Must be a float"
        self._v[2] = z
    z = property(Vector3._get_z, _set_z, None, "z component.")
    
    def _set_length(self, length):
        v = self._v
        try:
            x, y, z = v
            l = length / sqrt(x*x + y*y + z*z)
        except ZeroDivisionError:
            v[0] = 0.
            v[1] = 0.
            v[2] = 0.
            return self
        v[0] = x*l
        v[1] = y*l
        v[2] = z*l
    length = property(Vector3._get_length, _set_length, None, "Length of the vector")

    def set(self, x, y, z):
        assert (isinstance(x, float) and
                isinstance(y, float) and
                isinstance(z, float)), "x, y, z must be floats"
        v = self._v
        v[0] = x
        v[1] = y
        v[2] = z
        return self

    def __setitem__(self, index, value):
        assert isinstance(value, float), "Must be a float"
        try:
            self._v[index] = value
        except IndexError:
            raise IndexError("There are 3 values in this object, index should be 0, 1 or 2!")

    def __iadd__(self, rhs):
        ox, oy, oz = rhs
        v = self._v
        v[0] += ox
        v[1] += oy
        v[2] += oz
        return self

    def _isub__(self, rhs):
        ox, oy, oz = rhs
        v = self._v
        v[0] -= ox
        v[1] -= oy
        v[2] -= oz
        return self

    def __imul__(self, rhs):
        v = self._v
        if hasattr(rhs, "__getitem__"):
            ox, oy, oz = rhs
            v[0] *= ox
            v[1] *= oy
            v[2] *= oz
        else:
            v[0] *= rhs
            v[1] *= rhs
            v[2] *= rhs
        return self

    def __idiv__(self, rhs):
        """Divide this vector by another vector, or a scalar (single number)."""
        v = self._v
        if hasattr(rhs, "__getitem__"):
            v[0] /= ox
            v[1] /= oy
            v[2] /= oz
        else:
            v[0] /= rhs
            v[1] /= rhs
            v[2] /= rhs
        return self
 
    def scale(self, scale):
        v = self._v
        if hasattr(rhs, "__getitem__"):
            ox, oy, oz = rhs
            v[0] *= ox
            v[1] *= oy
            v[2] *= oz
        else:
            v[0] *= rhs
            v[1] *= rhs
            v[2] *= rhs
        return self

    def normalise(self):
        v = self._v
        x, y, z = v
        l = sqrt(x*x + y*y + z*z)
        try:
            v[0] /= l
            v[1] /= l
            v[2] /= l
        except ZeroDivisionError:
            v[0] = 0.0
            v[1] = 0.0
            v[2] = 0.0
        return self
    normalize = normalise

def mean(points):
    return sum(points, Vector3(0, 0, 0)) / max(len(points), 1)
