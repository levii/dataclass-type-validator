import dataclasses
import functools
import logging
import typing
from typing import Any, Optional, Tuple, Type

from pydantic import BaseModel, Extra
from pydantic.error_wrappers import ErrorWrapper, ValidationError
from pydantic.errors import ExtraError, MissingError
from pydantic.utils import ROOT_KEY, GetterDict

logger = logging.getLogger(__name__)


class TypeValidationError(Exception):
    """Exception raised on type validation errors."""

    def __init__(self, *args, target: dataclasses.dataclass, errors: dict):
        super(TypeValidationError, self).__init__(*args)
        self.class_ = target.__class__
        self.errors = errors

    def __repr__(self):
        cls = self.class_
        cls_name = f"{cls.__module__}.{cls.__name__}" if cls.__module__ != "__main__" else cls.__name__
        attrs = ", ".join([repr(v) for v in self.args])
        return f"{cls_name}({attrs}, errors={repr(self.errors)})"

    def __str__(self):
        cls = self.class_
        cls_name = f"{cls.__module__}.{cls.__name__}" if cls.__module__ != "__main__" else cls.__name__
        s = cls_name
        return f"{s} (errors = {self.errors})"


class EnforceError(Exception):
    """Exception raised on enforcing validation errors."""

    def __init__(self, *args):
        super(EnforceError, self).__init__(*args)
        pass


def _validate_type(expected_type: type, value: Any) -> Optional[str]:
    if not isinstance(value, expected_type):
        return f"must be an instance of {expected_type}, but received {type(value)}"


def _validate_iterable_items(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    expected_item_type = expected_type.__args__[0]
    errors = [_validate_types(expected_type=expected_item_type, value=v, strict=strict) for v in value]
    errors = [x for x in errors if x]
    if len(errors) > 0:
        return f"must be an instance of {expected_type}, but there are some errors: {errors}"


def _validate_typing_list(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    if not isinstance(value, list):
        return f"must be an instance of list, but received {type(value)}"
    return _validate_iterable_items(expected_type, value, strict)


def _validate_typing_tuple(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    if not isinstance(value, tuple):
        return f"must be an instance of tuple, but received {type(value)}"
    return _validate_iterable_items(expected_type, value, strict)


def _validate_typing_frozenset(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    if not isinstance(value, frozenset):
        return f"must be an instance of frozenset, but received {type(value)}"
    return _validate_iterable_items(expected_type, value, strict)


def _validate_typing_dict(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    if not isinstance(value, dict):
        return f"must be an instance of dict, but received {type(value)}"

    expected_key_type = expected_type.__args__[0]
    expected_value_type = expected_type.__args__[1]

    key_errors = [_validate_types(expected_type=expected_key_type, value=k, strict=strict) for k in value.keys()]
    key_errors = [k for k in key_errors if k]

    val_errors = [_validate_types(expected_type=expected_value_type, value=v, strict=strict) for v in value.values()]
    val_errors = [v for v in val_errors if v]

    if len(key_errors) > 0 and len(val_errors) > 0:
        return (
            f"must be an instance of {expected_type}, but there are some errors in keys and values. "
            f"key errors: {key_errors}, value errors: {val_errors}"
        )
    elif len(key_errors) > 0:
        return f"must be an instance of {expected_type}, but there are some errors in keys: {key_errors}"
    elif len(val_errors) > 0:
        return f"must be an instance of {expected_type}, but there are some errors in values: {val_errors}"


def _validate_typing_callable(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    _ = strict
    if not isinstance(value, type(lambda a: a)):
        return f"must be an instance of {expected_type._name}, but received {type(value)}"


def _validate_typing_literal(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    _ = strict
    if value not in expected_type.__args__:
        return f'must be one of [{", ".join(expected_type.__args__)}] but received {value}'


_validate_typing_mappings = {
    "List": _validate_typing_list,
    "Tuple": _validate_typing_tuple,
    "FrozenSet": _validate_typing_frozenset,
    "Dict": _validate_typing_dict,
    "Callable": _validate_typing_callable,
}


def _validate_sequential_types(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    validate_func = _validate_typing_mappings.get(expected_type._name)
    if validate_func is not None:
        return validate_func(expected_type, value, strict)

    if str(expected_type).startswith("typing.Literal"):
        return _validate_typing_literal(expected_type, value, strict)

    if str(expected_type).startswith("typing.Union"):
        is_valid = any(_validate_types(expected_type=t, value=value, strict=strict) is None for t in expected_type.__args__)
        if not is_valid:
            return f"must be an instance of {expected_type}, but received {value}"
        return

    if strict:
        raise RuntimeError(f"Unknown type of {expected_type} (_name = {expected_type._name})")


def _validate_types(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    if isinstance(expected_type, type):
        return _validate_type(expected_type=expected_type, value=value)

    if isinstance(expected_type, typing._GenericAlias):
        return _validate_sequential_types(expected_type=expected_type, value=value, strict=strict)


def dataclass_type_validator(target, strict: bool = False, enforce: bool = False):
    if isinstance(target, BaseModel):
        fields = target.fields.values()
    else:
        fields = dataclasses.fields(target)

    errors = {}
    for field in fields:
        field_name = field.name
        expected_type = field.type
        value = getattr(target, field_name)

        err = _validate_types(expected_type=expected_type, value=value, strict=strict)
        if err is not None:
            errors[field_name] = err
            if enforce:
                val = (
                    field.default
                    if not isinstance(field.default, (dataclasses._MISSING_TYPE, type(None)))
                    else field.default_factory()
                )
                if isinstance(val, (dataclasses._MISSING_TYPE, type(None))):
                    raise EnforceError("Can't enforce values as there is no default")
                setattr(target, field_name, val)

    if len(errors) > 0 and not enforce:
        raise TypeValidationError("Dataclass Type Validation Error", target=target, errors=errors)

    elif len(errors) > 0 and enforce:
        cls = target.__class__
        cls_name = f"{cls.__module__}.{cls.__name__}" if cls.__module__ != "__main__" else cls.__name__
        logger.warning(f"Dataclass type validation failed, types are enforced. {cls_name} errors={repr(errors)})")


def pydantic_type_validator(
    model: Type[BaseModel], input_data: "DictStrAny", cls: "ModelOrDc" = None, enforce: bool = False
) -> Tuple["DictStrAny", "SetStr", Optional[ValidationError]]:
    """
    validate data against a model.
    """
    _missing = object()
    values = {}
    errors = []
    # input_data names, possibly alias
    names_used = set()
    # field names, never aliases
    fields_set = set()
    config = model.__config__
    check_extra = config.extra is not Extra.ignore
    cls_ = cls or model

    for validator in model.__pre_root_validators__:
        if pydantic_type_validator.__name__ == validator.__code__.co_names[0]:
            continue
        try:
            input_data = validator(cls_, input_data)
        except (ValueError, TypeError, AssertionError) as exc:
            errors.append(ValidationError([ErrorWrapper(exc, loc=ROOT_KEY)], cls_))

    for name, field in model.__fields__.items():
        value = input_data.get(field.alias, _missing)
        using_name = False
        if value is _missing and config.allow_population_by_field_name and field.alt_alias:
            value = input_data.get(field.name, _missing)
            using_name = True

        if value is _missing:
            if field.required:
                errors.append(ErrorWrapper(MissingError(), loc=field.alias))
                continue

            value = field.get_default()

            if not config.validate_all and not field.validate_always:
                values[name] = value
                continue
        else:
            fields_set.add(name)
            if check_extra:
                names_used.add(field.name if using_name else field.alias)

        v_, errors_ = field.validate(value, values, loc=field.alias, cls=cls_)
        if errors_ and enforce:
            values[name] = field.get_default()
            errors_ = None
        if isinstance(errors_, ErrorWrapper):
            errors.append(errors_)
        elif isinstance(errors_, list):
            errors.extend(errors_)
        else:
            values[name] = v_

    if check_extra:
        if isinstance(input_data, GetterDict):
            extra = input_data.extra_keys() - names_used
        else:
            extra = input_data.keys() - names_used
        if extra:
            fields_set |= extra
            if config.extra is Extra.allow:
                for f in extra:
                    values[f] = input_data[f]
            else:
                for f in sorted(extra):
                    errors.append(ErrorWrapper(ExtraError(), loc=f))

    for skip_on_failure, validator in model.__post_root_validators__:
        if skip_on_failure and errors:
            continue
        try:
            values = validator(cls_, values)
        except (ValueError, TypeError, AssertionError) as exc:
            errors.append(ErrorWrapper(exc, loc=ROOT_KEY))

    if errors:
        return values, fields_set, ValidationError(errors, cls_)
    else:
        return values, fields_set, None


def dataclass_validate(
    cls=None,
    *,
    strict: bool = False,
    before_post_init: bool = False,
    enforce: bool = False,
):
    """Dataclass decorator to automatically add validation to a dataclass.

    So you don't have to add a __post_init__ method, or if you have one, you don't have
    to remember to add the dataclass_type_validator(self) call to it; just decorate your
    dataclass with this instead.

    :param strict: bool
    :param before_post_init: bool - if True, force the validation logic to occur before
        __post_init__ is called.  Only has effect if the class defines __post_init__.
        This setting allows you to ensure the field values are already validated to
        be the correct type before any additional logic in __post_init__ does further
        validation.  Default: False.
    """
    if cls is None:
        return functools.partial(
            dataclass_validate,
            strict=strict,
            before_post_init=before_post_init,
            enforce=enforce,
        )

    if not hasattr(cls, "__post_init__"):
        # No post-init method, so no processing.  Wrap the constructor instead.
        wrapped_method_name = "__init__"
    else:
        # Normally make validation take place at the end of __post_init__
        wrapped_method_name = "__post_init__"

    orig_method = getattr(cls, wrapped_method_name)

    if wrapped_method_name == "__post_init__" and before_post_init:
        # User wants to force validation to run before __post_init__, so call it
        # before the wrapped function.
        @functools.wraps(orig_method)
        def method_wrapper(self, *args, **kwargs):
            dataclass_type_validator(self, strict=strict, enforce=enforce)
            return orig_method(self, *args, **kwargs)

    else:
        # Normal case - call validator at the end of __init__ or __post_init__.
        @functools.wraps(orig_method)
        def method_wrapper(self, *args, **kwargs):
            x = orig_method(self, *args, **kwargs)
            dataclass_type_validator(self, strict=strict, enforce=enforce)
            return x

    setattr(cls, wrapped_method_name, method_wrapper)

    return cls


if __name__ == "__main__":
    # @dataclasses.dataclass
    # class TestClass:
    #    k: str = "key"
    #    v: float = 1.2

    # test_class = TestClass(k=1.2, v="key")

    # @dataclasses.dataclass
    # class TestClass:
    #    k: str = "key"
    #    v: float = 1.2

    #    def __post_init__(self):
    #        dataclass_type_validator(self, enforce=True)

    # test_class = TestClass(k=1.2, v="key")
    from pydantic import root_validator

    class TestClass(BaseModel):
        k: str = "key"
        v: float = 1.2

        @root_validator(pre=True)
        def enforce_validator(cls, values):
            values = pydantic_type_validator(cls, values, enforce=True)
            return values

        def validate_class(self):
            from pydantic import validate_model

            object_setattr = object.__setattr__
            values, fields_set, validation_error = validate_model(self.__class__, self.dict())
            if validation_error:
                raise validation_error
            object_setattr(self, "__dict__", values)
            object_setattr(self, "__fields_set__", fields_set)
            self._init_private_attributes()

    test_class = TestClass(k=1.2, v="key")
    print(test_class)
    setattr(test_class, "v", "key")
    print(test_class)
    test_class.validate_class()
    print(test_class)
    TestClass()
