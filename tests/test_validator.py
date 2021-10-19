import pytest
import dataclasses
import typing
import sys

from dataclass_type_validator import dataclass_type_validator, dataclass_validate
from dataclass_type_validator import TypeValidationError


@dataclasses.dataclass(frozen=True)
class DataclassTestNumber:
    number: int
    optional_number: typing.Optional[int] = None

    def __post_init__(self):
        dataclass_type_validator(self)


class TestTypeValidationNumber:
    def test_build_success(self):
        assert isinstance(DataclassTestNumber(
            number=1,
            optional_number=None,
        ), DataclassTestNumber)
        assert isinstance(DataclassTestNumber(
            number=1,
            optional_number=1
        ), DataclassTestNumber)

    def test_build_failure_on_number(self):
        with pytest.raises(TypeValidationError):
            assert isinstance(DataclassTestNumber(
                number=1,
                optional_number='string'
            ), DataclassTestNumber)


@dataclasses.dataclass(frozen=True)
class DataclassTestString:
    string: str
    optional_string: typing.Optional[str] = None

    def __post_init__(self):
        dataclass_type_validator(self)


class TestTypeValidationString:
    def test_build_success(self):
        assert isinstance(DataclassTestString(
            string='string',
            optional_string=None
        ), DataclassTestString)
        assert isinstance(DataclassTestString(
            string='string',
            optional_string='string'
        ), DataclassTestString)

    def test_build_failure_on_string(self):
        with pytest.raises(TypeValidationError):
            assert isinstance(DataclassTestString(
                string='str',
                optional_string=123
            ), DataclassTestString)


@dataclasses.dataclass(frozen=True)
class DataclassTestList:
    array_of_numbers: typing.List[int]
    array_of_strings: typing.List[str]
    array_of_optional_strings: typing.List[typing.Optional[str]]

    def __post_init__(self):
        dataclass_type_validator(self)


class TestTypeValidationList:
    def test_build_success(self):
        assert isinstance(DataclassTestList(
            array_of_numbers=[],
            array_of_strings=[],
            array_of_optional_strings=[],
        ), DataclassTestList)
        assert isinstance(DataclassTestList(
            array_of_numbers=[1, 2],
            array_of_strings=['abc'],
            array_of_optional_strings=['abc', None]
        ), DataclassTestList)

    def test_build_failure_on_array_numbers(self):
        with pytest.raises(TypeValidationError, match='must be an instance of typing.List\\[int\\]'):
            assert isinstance(DataclassTestList(
                array_of_numbers=['abc'],
                array_of_strings=['abc'],
                array_of_optional_strings=['abc', None]
            ), DataclassTestList)

    def test_build_failure_on_array_strings(self):
        with pytest.raises(TypeValidationError, match='must be an instance of typing.List\\[str\\]'):
            assert isinstance(DataclassTestList(
                array_of_numbers=[1, 2],
                array_of_strings=[123],
                array_of_optional_strings=['abc', None]
            ), DataclassTestList)

    def test_build_failure_on_array_optional_strings(self):
        with pytest.raises(TypeValidationError,
                           match=f"must be an instance of typing.List\\[{optional_type_name('str')}\\]"):
            assert isinstance(DataclassTestList(
                array_of_numbers=[1, 2],
                array_of_strings=['abc'],
                array_of_optional_strings=[123, None]
            ), DataclassTestList)


@dataclasses.dataclass(frozen=True)
class DataclassTestUnion:
    string_or_number: typing.Union[str, int]
    optional_string: typing.Optional[str]

    def __post_init__(self):
        dataclass_type_validator(self)


class TestTypeValidationUnion:
    def test_build_success(self):
        assert isinstance(DataclassTestUnion(
            string_or_number='abc',
            optional_string='abc'
        ), DataclassTestUnion)
        assert isinstance(DataclassTestUnion(
            string_or_number=123,
            optional_string=None
        ), DataclassTestUnion)

    def test_build_failure(self):
        with pytest.raises(TypeValidationError, match='must be an instance of typing.Union\\[str, int\\]'):
            assert isinstance(DataclassTestUnion(
                string_or_number=None,
                optional_string=None
            ), DataclassTestUnion)

        with pytest.raises(TypeValidationError, match=f'must be an instance of {optional_type_name("str")}'):
            assert isinstance(DataclassTestUnion(
                string_or_number=123,
                optional_string=123
            ), DataclassTestUnion)


@dataclasses.dataclass(frozen=True)
class DataclassTestLiteral:
    restricted_value: typing.Literal['foo', 'bar']

    def __post_init__(self):
        dataclass_type_validator(self, strict=True)


class TestTypeValidationLiteral:
    def test_build_success(self):
        assert isinstance(DataclassTestLiteral(
            restricted_value='foo'
        ), DataclassTestLiteral)
        assert isinstance(DataclassTestLiteral(
            restricted_value='bar'
        ), DataclassTestLiteral)

    def test_build_failure(self):
        with pytest.raises(TypeValidationError, match='must be one of \\[foo, bar\\] but received fizz'):
            assert isinstance(DataclassTestLiteral(
                restricted_value='fizz'
            ), DataclassTestLiteral)

        with pytest.raises(TypeValidationError, match='must be one of \\[foo, bar\\] but received None'):
            assert isinstance(DataclassTestLiteral(
                restricted_value=None,
            ), DataclassTestLiteral)


@dataclasses.dataclass(frozen=True)
class DataclassTestDict:
    str_to_str: typing.Dict[str, str]
    str_to_any: typing.Dict[str, typing.Any]

    def __post_init__(self):
        dataclass_type_validator(self)


class TestTypeValidationDict:
    def test_build_success(self):
        assert isinstance(DataclassTestDict(
            str_to_str={'str': 'str'},
            str_to_any={'str': 'str', 'str2': 123}
        ), DataclassTestDict)

    def test_build_failure(self):
        with pytest.raises(TypeValidationError, match='must be an instance of typing.Dict\\[str, str\\]'):
            assert isinstance(DataclassTestDict(
                str_to_str={'str': 123},
                str_to_any={'key': []}
            ), DataclassTestDict)


@dataclasses.dataclass(frozen=True)
class DataclassTestCallable:
    func: typing.Callable[[int, int], int]

    def __post_init__(self):
        dataclass_type_validator(self)


class TestTypeValidationCallable:
    def test_build_success(self):
        assert isinstance(DataclassTestCallable(
            func=lambda a, b: a * b
        ), DataclassTestCallable)

    def test_build_failure(self):
        with pytest.raises(TypeValidationError, match='must be an instance of Callable'):
            assert isinstance(DataclassTestCallable(
                func=None,
            ), DataclassTestCallable)


@dataclasses.dataclass(frozen=True)
class DataclassTestForwardRef:
    number: 'int'
    ref: typing.Optional['DataclassTestForwardRef'] = None

    def __post_init__(self):
        dataclass_type_validator(self)


class TestTypeValidationForwardRef:
    def test_build_success(self):
        assert isinstance(DataclassTestForwardRef(
            number=1,
            ref=None,
        ), DataclassTestForwardRef)
        assert isinstance(DataclassTestForwardRef(
            number=1,
            ref=DataclassTestForwardRef(2, None)
        ), DataclassTestForwardRef)

    def test_build_failure_on_number(self):
        with pytest.raises(TypeValidationError):
            assert isinstance(DataclassTestForwardRef(
                number=1,
                ref='string'
            ), DataclassTestForwardRef)


@dataclasses.dataclass(frozen=True)
class ChildValue:
    child: str

    def __post_init__(self):
        dataclass_type_validator(self)


@dataclasses.dataclass(frozen=True)
class ParentValue:
    child: ChildValue

    def __post_init__(self):
        dataclass_type_validator(self)


class TestNestedDataclass:
    def test_build_success(self):
        assert isinstance(ParentValue(
            child=ChildValue(child='string')
        ), ParentValue)

    def test_build_failure(self):
        with pytest.raises(TypeValidationError,
                           match="must be an instance of <class 'tests.test_validator.ChildValue'>"):
            assert isinstance(ParentValue(
                child=None
            ), ParentValue)


@dataclass_validate
@dataclasses.dataclass(frozen=True)
class DataclassWithPostInitTestDecorator:
    number: int
    optional_number: typing.Optional[int] = None

    def __post_init__(self):
        dataclass_type_validator(self)


class TestDecoratorWithPostInit:
    def test_build_success(self):
        assert isinstance(DataclassWithPostInitTestDecorator(
            number=1,
            optional_number=None,
        ), DataclassWithPostInitTestDecorator)
        assert isinstance(DataclassWithPostInitTestDecorator(
            number=1,
            optional_number=1
        ), DataclassWithPostInitTestDecorator)

    def test_build_failure_on_number(self):
        with pytest.raises(TypeValidationError):
            _ = DataclassWithPostInitTestDecorator(
                number=1,
                optional_number='string'
            )


@dataclass_validate
@dataclasses.dataclass(frozen=True)
class DataclassWithoutPostInitTestDecorator:
    number: int
    optional_number: typing.Optional[int] = None


class TestDecoratorWithoutPostInit:
    def test_build_success(self):
        assert isinstance(DataclassWithoutPostInitTestDecorator(
            number=1,
            optional_number=None,
        ), DataclassWithoutPostInitTestDecorator)
        assert isinstance(DataclassWithoutPostInitTestDecorator(
            number=1,
            optional_number=1
        ), DataclassWithoutPostInitTestDecorator)

    def test_build_failure_on_number(self):
        with pytest.raises(TypeValidationError):
            _ = DataclassWithoutPostInitTestDecorator(
                number=1,
                optional_number='string'
            )


@dataclass_validate(strict=True)
@dataclasses.dataclass(frozen=True)
class DataclassWithStrictChecking:
    values: typing.List[int]


class TestDecoratorStrict:
    def test_build_success(self):
        assert isinstance(DataclassWithStrictChecking(
            values=[1, 2, 3],
        ), DataclassWithStrictChecking)

    def test_build_failure_on_number(self):
        with pytest.raises(TypeValidationError):
            _ = DataclassWithStrictChecking(
                values=[1, 2, "three"],
            )


def optional_type_name(arg_type_name):
    """ Gets the typename string for an typing.Optional.
        On python 3.8 an Optional[int] is converted to a typing.Union[int, NoneType].
        On python 3.9 it remains unchanged as Optional[int].
    """
    if sys.version_info < (3, 9):
        return f"typing.Union\\[({arg_type_name}, NoneType|NoneType, {arg_type_name})\\]"

    return f"typing.Optional\\[{arg_type_name}\\]"
