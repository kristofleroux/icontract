# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=no-self-use

import abc
import unittest
from typing import Optional  # pylint: disable=unused-import

import icontract


class TestOK(unittest.TestCase):
    def test_ensure_then(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result % 2 == 0)
            def func(self) -> int:
                return 10

        class B(A):
            @icontract.post(lambda result: result % 3 == 0)
            def func(self) -> int:
                return 6

        b = B()
        b.func()

    def test_count_checks(self):
        class Increment:
            count = 0

            def __call__(self) -> bool:
                Increment.count += 1
                return True

        inc = Increment()

        @icontract.inv(lambda self: inc())
        class SomeClass:
            def __init__(self) -> None:
                pass

            def some_func(self) -> None:
                return

        inst = SomeClass()
        self.assertEqual(1, Increment.count)  # Invariant needs to be checked once after the initialization.

        inst.some_func()
        self.assertEqual(3, Increment.count)  # Invariant needs to be checked before and after some_func.

    def test_count_checks_in_slot_wrappers(self):
        class Increment:
            count = 0

            def __call__(self) -> bool:
                Increment.count += 1
                return True

        inc = Increment()

        @icontract.inv(lambda self: inc())
        class SomeClass:
            pass

        inst = SomeClass()
        self.assertEqual(1, Increment.count)  # Invariant needs to be checked once after the initialization.

        _ = str(inst)
        self.assertEqual(3, Increment.count)  # Invariant needs to be checked before and after __str__.


class TestViolation(unittest.TestCase):
    def test_inherited_without_implementation(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result < 100)
            def func(self) -> int:
                return 1000

        class B(A):
            pass

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("result < 100: result was 1000", str(violation_err))

    def test_inherited_with_modified_implementation(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result < 100)
            def func(self) -> int:
                return 1000

        class B(A):
            def func(self) -> int:
                return 10000

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("result < 100: result was 10000", str(violation_err))

    def test_ensure_then_violated_in_base(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result % 2 == 0)
            def func(self) -> int:
                return 10

        class B(A):
            @icontract.post(lambda result: result % 3 == 0)
            def func(self) -> int:
                return 3

        b = B()

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("result % 2 == 0: result was 3", str(violation_err))

    def test_ensure_then_violated_in_child(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result % 2 == 0)
            def func(self) -> int:
                return 10

        class B(A):
            @icontract.post(lambda result: result % 3 == 0)
            def func(self) -> int:
                return 2

        b = B()

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("result % 3 == 0: result was 2", str(violation_err))

    def test_abstract_method(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result < 100)
            @abc.abstractmethod
            def func(self) -> int:
                pass

        class B(A):
            def func(self) -> int:
                return 1000

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("result < 100: result was 1000", str(violation_err))

    def test_that_base_postconditions_apply_to_init_if_not_defined(self):
        class A(icontract.DBC):
            @icontract.post(lambda self: self.x >= 0)
            def __init__(self, x: int) -> None:
                self.x = x

            def __repr__(self) -> str:
                return self.__class__.__name__

        class B(A):
            pass

        icontract_violation_error = None  # Optional[icontract.ViolationError]
        try:
            _ = B(x=-1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('self.x >= 0:\n' 'self was B\n' 'self.x was -1', str(icontract_violation_error))

    def test_that_base_postconditions_dont_apply_to_init_if_overridden(self):
        class A(icontract.DBC):
            @icontract.post(lambda self: self.x >= 0)
            def __init__(self, x: int) -> None:
                self.x = x

        class B(A):
            # pylint: disable=super-init-not-called
            @icontract.post(lambda self: self.x < 0)
            def __init__(self, x: int) -> None:
                self.x = x

            def __repr__(self) -> str:
                return self.__class__.__name__

        # postconditions of B need to be satisfied, but not from A
        _ = B(x=-100)

        icontract_violation_error = None  # Optional[icontract.ViolationError]
        try:
            _ = B(x=0)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('self.x < 0:\n' 'self was B\n' 'self.x was 0', str(icontract_violation_error))


class TestPropertyOK(unittest.TestCase):
    def test_getter_setter_deleter_ok(self):
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.deleted = False
                self._some_prop = 1

            @property
            @icontract.post(lambda self, result: self._some_prop == result)
            def some_prop(self) -> int:
                return self._some_prop

            @some_prop.setter
            @icontract.post(lambda self, value: self.some_prop == value)
            def some_prop(self, value: int) -> None:
                self._some_prop = value

            @some_prop.deleter
            @icontract.post(lambda self: self.deleted)
            def some_prop(self) -> None:
                self.deleted = True

        class SomeClass(SomeBase):
            pass

        some_inst = SomeClass()
        some_inst.some_prop = 3
        self.assertEqual(3, some_inst.some_prop)

        del some_inst.some_prop
        self.assertTrue(some_inst.deleted)


class TestPropertyViolation(unittest.TestCase):
    def test_getter(self):
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = True

            @property
            @icontract.post(lambda self: not self.toggled)
            def some_prop(self) -> int:
                return 0

        class SomeClass(SomeBase):
            @property
            def some_prop(self) -> int:
                return 0

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))

    def test_setter(self):
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = True

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.setter
            @icontract.post(lambda self: not self.toggled)
            def some_prop(self, value: int) -> None:
                pass

        class SomeClass(SomeBase):
            @SomeBase.some_prop.setter  # pylint: disable=no-member
            def some_prop(self, value: int) -> None:
                pass

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = 0
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))

    def test_deleter(self):
        class SomeBase(icontract.DBC):
            def __init__(self):
                self.toggled = True

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.deleter
            @icontract.post(lambda self: not self.toggled)
            def some_prop(self) -> None:
                pass

        class SomeClass(SomeBase):
            def __repr__(self):
                return self.__class__.__name__

            @SomeBase.some_prop.deleter  # pylint: disable=no-member
            def some_prop(self) -> None:
                pass

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            del some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))

    def test_setter_strengthened(self):
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = True

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.setter
            def some_prop(self, value: int) -> None:
                pass

        class SomeClass(SomeBase):
            @SomeBase.some_prop.setter  # pylint: disable=no-member
            @icontract.post(lambda self: not self.toggled)
            def some_prop(self, value: int) -> None:
                pass

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = 0
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))


class TestInvalid(unittest.TestCase):
    def test_abstract_method_not_implemented(self):
        # pylint: disable=abstract-method
        class A(icontract.DBC):
            @icontract.post(lambda result: result < 100)
            @abc.abstractmethod
            def func(self) -> int:
                pass

        class B(A):
            pass

        type_err = None  # type: Optional[TypeError]
        try:
            _ = B()
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        self.assertEqual("Can't instantiate abstract class B with abstract methods func", str(type_err))


if __name__ == '__main__':
    unittest.main()