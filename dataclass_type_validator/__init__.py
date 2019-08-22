import dataclasses
import typing
from typing import Any
from typing import Optional


def _validate_type(expected_type: type, value: Any) -> Optional[str]:
    if not isinstance(value, expected_type):
        return f'must be an instance of {expected_type}, but received {type(value)}'


def _validate_typing_list(expected_type: type, value: Any) -> Optional[str]:
    if not isinstance(value, list):
        return f'must be an instance of array, but received {type(value)}'

    expected_item_type = expected_type.__args__[0]
    errors = [_validate_types(expected_type=expected_item_type, value=v) for v in value]
    errors = [x for x in errors if x]
    if len(errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors: {errors}'


def _validate_typing_dict(expected_type: type, value: Any) -> Optional[str]:
    if not isinstance(value, dict):
        return f'must be an instance of dict, but received {type(value)}'

    expected_key_type = expected_type.__args__[0]
    expected_value_type = expected_type.__args__[1]

    key_errors = [_validate_types(expected_type=expected_key_type, value=k) for k in value.keys()]
    key_errors = [k for k in key_errors if k]

    val_errors = [_validate_types(expected_type=expected_value_type, value=v) for v in value.values()]
    val_errors = [v for v in val_errors if v]

    if len(key_errors) > 0 and len(val_errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors in keys and values. '\
            f'key errors: {key_errors}, value errors: {val_errors}'
    elif len(key_errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors in keys: {key_errors}'
    elif len(val_errors) > 0:
        return f'must be an instance of {expected_type}, but there are some errors in values: {val_errors}'


def _validate_typing_callable(expected_type: type, value: Any) -> Optional[str]:
    if not isinstance(value, type(lambda a: a)):
        return f'must be an instance of {expected_type._name}, but received {type(value)}'


_validate_typing_mappings = {
    'List': _validate_typing_list,
    'Dict': _validate_typing_dict,
    'Callable': _validate_typing_callable,
}


def _validate_sequential_types(expected_type: type, value: Any) -> Optional[str]:
    validate_func = _validate_typing_mappings.get(expected_type._name)
    if validate_func is not None:
        return validate_func(expected_type, value)

    if str(expected_type).startswith('typing.Union'):
        is_valid = any(_validate_types(expected_type=t, value=value) is None for t in expected_type.__args__)
        if not is_valid:
            return f'must be an instance of {expected_type}, but received {value}'
        return

    raise RuntimeError(f'Unknown type of {expected_type} (_name = {expected_type._name})')


def _validate_types(expected_type: type, value: Any) -> Optional[str]:
    if isinstance(expected_type, type):
        return _validate_type(expected_type=expected_type, value=value)

    if isinstance(expected_type, typing._GenericAlias):
        return _validate_sequential_types(expected_type=expected_type, value=value)


def dataclass_type_validator(target):
    fields = dataclasses.fields(target)
    values = dataclasses.asdict(target)

    errors = {}
    for field in fields:
        field_name = field.name
        expected_type = field.type
        value = values[field_name]

        err = _validate_types(expected_type=expected_type, value=value)
        if err is not None:
            errors[field_name] = err

    if len(errors) > 0:
        raise ValueError(f'Dataclass Type Validation Error: {errors}')
