import dataclasses
import typing
import functools
import sys
from typing import Any
from typing import Optional
from typing import Dict

GlobalNS_T = Dict[str, Any]


class TypeValidationError(Exception):
    """Exception raised on type validation errors.
    """

    def __init__(self, *args, target: dataclasses.dataclass, errors: dict):
        super(TypeValidationError, self).__init__(*args)
        self.class_ = target.__class__
        self.errors = errors

    def __repr__(self):
        cls = self.class_
        cls_name = (
            f"{cls.__module__}.{cls.__name__}"
            if cls.__module__ != "__main__"
            else cls.__name__
        )
        attrs = ", ".join([repr(v) for v in self.args])
        return f"{cls_name}({attrs}, errors={repr(self.errors)})"

    def __str__(self):
        cls = self.class_
        cls_name = (
            f"{cls.__module__}.{cls.__name__}"
            if cls.__module__ != "__main__"
            else cls.__name__
        )
        s = cls_name
        return f"{s} (errors = {self.errors})"


def _validate_type(expected_type: type, value: Any) -> Optional[str]:
    if not isinstance(value, expected_type):
        return f'must be an instance of {expected_type}, but received {type(value)}'


def _validate_iterable_items(expected_type: type, value: Any, strict: bool, globalns: GlobalNS_T) -> Optional[str]:
    expected_item_type = expected_type.__args__[0]
    errors = [_validate_types(expected_type=expected_item_type, value=v, strict=strict, globalns=globalns)
              for v in value]
    errors = [x for x in errors if x]
    if len(errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors: {errors}'


def _validate_typing_list(expected_type: type, value: Any, strict: bool, globalns: GlobalNS_T) -> Optional[str]:
    if not isinstance(value, list):
        return f'must be an instance of list, but received {type(value)}'
    return _validate_iterable_items(expected_type, value, strict, globalns)


def _validate_typing_tuple(expected_type: type, value: Any, strict: bool, globalns: GlobalNS_T) -> Optional[str]:
    if not isinstance(value, tuple):
        return f'must be an instance of tuple, but received {type(value)}'
    return _validate_iterable_items(expected_type, value, strict, globalns)


def _validate_typing_frozenset(expected_type: type, value: Any, strict: bool, globalns: GlobalNS_T) -> Optional[str]:
    if not isinstance(value, frozenset):
        return f'must be an instance of frozenset, but received {type(value)}'
    return _validate_iterable_items(expected_type, value, strict, globalns)


def _validate_typing_dict(expected_type: type, value: Any, strict: bool, globalns: GlobalNS_T) -> Optional[str]:
    if not isinstance(value, dict):
        return f'must be an instance of dict, but received {type(value)}'

    expected_key_type = expected_type.__args__[0]
    expected_value_type = expected_type.__args__[1]

    key_errors = [_validate_types(expected_type=expected_key_type, value=k, strict=strict, globalns=globalns)
                  for k in value.keys()]
    key_errors = [k for k in key_errors if k]

    val_errors = [_validate_types(expected_type=expected_value_type, value=v, strict=strict, globalns=globalns)
                  for v in value.values()]
    val_errors = [v for v in val_errors if v]

    if len(key_errors) > 0 and len(val_errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors in keys and values. '\
            f'key errors: {key_errors}, value errors: {val_errors}'
    elif len(key_errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors in keys: {key_errors}'
    elif len(val_errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors in values: {val_errors}'


def _validate_typing_callable(expected_type: type, value: Any, strict: bool, globalns: GlobalNS_T) -> Optional[str]:
    _ = strict
    if not isinstance(value, type(lambda a: a)):
        return f'must be an instance of {expected_type._name}, but received {type(value)}'


def _validate_typing_literal(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    _ = strict
    if value not in expected_type.__args__:
        return f'must be one of [{", ".join(expected_type.__args__)}] but received {value}'


_validate_typing_mappings = {
    'List': _validate_typing_list,
    'Tuple': _validate_typing_tuple,
    'FrozenSet': _validate_typing_frozenset,
    'Dict': _validate_typing_dict,
    'Callable': _validate_typing_callable,
}


def _validate_sequential_types(expected_type: type, value: Any, strict: bool, globalns: GlobalNS_T) -> Optional[str]:
    validate_func = _validate_typing_mappings.get(expected_type._name)
    if validate_func is not None:
        return validate_func(expected_type, value, strict, globalns)

    if str(expected_type).startswith('typing.Literal'):
        return _validate_typing_literal(expected_type, value, strict)

    if str(expected_type).startswith('typing.Union') or str(expected_type).startswith('typing.Optional'):
        is_valid = any(_validate_types(expected_type=t, value=value, strict=strict, globalns=globalns) is None
                       for t in expected_type.__args__)
        if not is_valid:
            return f'must be an instance of {expected_type}, but received {value}'
        return

    if strict:
        raise RuntimeError(f'Unknown type of {expected_type} (_name = {expected_type._name})')


def _validate_types(expected_type: type, value: Any, strict: bool, globalns: GlobalNS_T) -> Optional[str]:
    if isinstance(expected_type, type):
        return _validate_type(expected_type=expected_type, value=value)

    if isinstance(expected_type, typing._GenericAlias):
        return _validate_sequential_types(expected_type=expected_type, value=value,
                                          strict=strict, globalns=globalns)

    if isinstance(expected_type, typing.ForwardRef):
        referenced_type = _evaluate_forward_reference(expected_type, globalns)
        return _validate_type(expected_type=referenced_type, value=value)


def _evaluate_forward_reference(ref_type: typing.ForwardRef, globalns: GlobalNS_T):
    """ Support evaluating ForwardRef types on both Python 3.8 and 3.9. """
    if sys.version_info < (3, 9):
        return ref_type._evaluate(globalns, None)
    return ref_type._evaluate(globalns, None, set())


def dataclass_type_validator(target, strict: bool = False):
    fields = dataclasses.fields(target)
    globalns = sys.modules[target.__module__].__dict__.copy()

    errors = {}
    for field in fields:
        field_name = field.name
        expected_type = field.type
        value = getattr(target, field_name)

        err = _validate_types(expected_type=expected_type, value=value, strict=strict, globalns=globalns)
        if err is not None:
            errors[field_name] = err

    if len(errors) > 0:
        raise TypeValidationError(
            "Dataclass Type Validation Error", target=target, errors=errors
        )


def dataclass_validate(cls=None, *, strict: bool = False, before_post_init: bool = False):
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
        return functools.partial(dataclass_validate, strict=strict, before_post_init=before_post_init)

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
            dataclass_type_validator(self, strict=strict)
            return orig_method(self, *args, **kwargs)
    else:
        # Normal case - call validator at the end of __init__ or __post_init__.
        @functools.wraps(orig_method)
        def method_wrapper(self, *args, **kwargs):
            x = orig_method(self, *args, **kwargs)
            dataclass_type_validator(self, strict=strict)
            return x
    setattr(cls, wrapped_method_name, method_wrapper)

    return cls
