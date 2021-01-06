import dataclasses
import typing
import functools
from typing import Any
from typing import Optional


class TypeValidationError(Exception):
    def __init__(self, *args, errors: dict):
        super(TypeValidationError, self).__init__(*args)
        self.errors = errors

    def __repr__(self):
        cls = self.__class__
        cls_name = f'{cls.__module__}.{cls.__name__}' if cls.__module__ != '__main__' else cls.__name__
        attrs = ', '.join([repr(v) for v in self.args])
        return f'{cls_name}({attrs}, errors={repr(self.errors)})'

    def __str__(self):
        s = super(TypeValidationError, self).__str__()
        return f'{s} (errors = {self.errors})'


def _validate_type(expected_type: type, value: Any) -> Optional[str]:
    if not isinstance(value, expected_type):
        return f'must be an instance of {expected_type}, but received {type(value)}'


def _validate_typing_list(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    if not isinstance(value, list):
        return f'must be an instance of array, but received {type(value)}'

    expected_item_type = expected_type.__args__[0]
    errors = [_validate_types(expected_type=expected_item_type, value=v, strict=strict) for v in value]
    errors = [x for x in errors if x]
    if len(errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors: {errors}'


def _validate_typing_dict(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    if not isinstance(value, dict):
        return f'must be an instance of dict, but received {type(value)}'

    expected_key_type = expected_type.__args__[0]
    expected_value_type = expected_type.__args__[1]

    key_errors = [_validate_types(expected_type=expected_key_type, value=k, strict=strict) for k in value.keys()]
    key_errors = [k for k in key_errors if k]

    val_errors = [_validate_types(expected_type=expected_value_type, value=v, strict=strict) for v in value.values()]
    val_errors = [v for v in val_errors if v]

    if len(key_errors) > 0 and len(val_errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors in keys and values. '\
            f'key errors: {key_errors}, value errors: {val_errors}'
    elif len(key_errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors in keys: {key_errors}'
    elif len(val_errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors in values: {val_errors}'


def _validate_typing_callable(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    _ = strict
    if not isinstance(value, type(lambda a: a)):
        return f'must be an instance of {expected_type._name}, but received {type(value)}'


_validate_typing_mappings = {
    'List': _validate_typing_list,
    'Dict': _validate_typing_dict,
    'Callable': _validate_typing_callable,
}


def _validate_sequential_types(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    validate_func = _validate_typing_mappings.get(expected_type._name)
    if validate_func is not None:
        return validate_func(expected_type, value, strict)

    if str(expected_type).startswith('typing.Union'):
        is_valid = any(_validate_types(expected_type=t, value=value, strict=strict) is None
                       for t in expected_type.__args__)
        if not is_valid:
            return f'must be an instance of {expected_type}, but received {value}'
        return

    if strict:
        raise RuntimeError(f'Unknown type of {expected_type} (_name = {expected_type._name})')


def _validate_types(expected_type: type, value: Any, strict: bool) -> Optional[str]:
    if isinstance(expected_type, type):
        return _validate_type(expected_type=expected_type, value=value)

    if isinstance(expected_type, typing._GenericAlias):
        return _validate_sequential_types(expected_type=expected_type, value=value, strict=strict)


def dataclass_type_validator(target, strict: bool = False):
    fields = dataclasses.fields(target)

    errors = {}
    for field in fields:
        field_name = field.name
        expected_type = field.type
        value = getattr(target, field_name)

        err = _validate_types(expected_type=expected_type, value=value, strict=strict)
        if err is not None:
            errors[field_name] = err

    if len(errors) > 0:
        raise TypeValidationError('Dataclass Type Validation Error', errors=errors)


def dataclass_validate(cls):
    """Dataclass decorator to automatically add validation to a dataclass.

    So you don't have to add a __post_init__ method, or if you have one, you don't have
    to remember to add the dataclass_type_validator(self) call to it; just decorate your
    dataclass with this instead.
    """
    if hasattr(cls, "__post_init__"):
        wrapped_func_name = "__post_init__"
    else:
        # No __post_init__ to wrap, but it means there's no post-init processing
        # taking place, so we can wrap the constructor instead.
        wrapped_func_name = "__init__"
    orig_func = getattr(cls, wrapped_func_name)

    @functools.wraps(orig_func)
    def wrapper(self, *args, **kwargs):
        # Call constructor or __post_init__ as appropriate
        orig_func(self, *args, **kwargs)
        # And then do validation
        dataclass_type_validator(self, strict=True)

    setattr(cls, wrapped_func_name, wrapper)
    return cls
