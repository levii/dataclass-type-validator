# dataclass-type-validator

The `dataclass-type-validator` is a type validation library for the properties of `dataclasses.dataclass` using Python type hint information.

## Installation

`pip install dataclass-type-validator` or add `dataclass-type-validator` line to `requirements.txt`

## A Simple Example

### Explicitly calling dataclass_type_validator from within your dataclass
```python
from dataclasses import dataclass
from typing import List
from dataclass_type_validator import dataclass_type_validator
from dataclass_type_validator import TypeValidationError

@dataclass()
class User:
    id: int
    name: str
    friend_ids: List[int]

    def __post_init__(self):
        dataclass_type_validator(self)


# Valid User
User(id=10, name='John Smith', friend_ids=[1, 2])
# => User(id=10, name='John Smith', friend_ids=[1, 2])

# Invalid User
try:
    User(id='a', name=['John', 'Smith'], friend_ids=['a'])
except TypeValidationError as e:
    print(e)
# => TypeValidationError: Dataclass Type Validation (errors = {
#   'id': "must be an instance of <class 'int'>, but received <class 'str'>",
#   'name': "must be an instance of <class 'str'>, but received <class 'list'>",
#   'friend_ids': 'must be an instance of typing.List[int], but there are some errors:
#       ["must be an instance of <class \'int\'>, but received <class \'str\'>"]'})
```

### The same, but using the class decorator instead
```python
from dataclasses import dataclass
from typing import List
from dataclass_type_validator import dataclass_validate
from dataclass_type_validator import TypeValidationError

@dataclass_validate
@dataclass()
class User:
    id: int
    name: str
    friend_ids: List[int]


# Valid User
User(id=10, name='John Smith', friend_ids=[1, 2])
# => User(id=10, name='John Smith', friend_ids=[1, 2])

# Invalid User
try:
    User(id='a', name=['John', 'Smith'], friend_ids=['a'])
except TypeValidationError as e:
    print(e)
# => TypeValidationError: Dataclass Type Validation (errors = {
#   'id': "must be an instance of <class 'int'>, but received <class 'str'>",
#   'name': "must be an instance of <class 'str'>, but received <class 'list'>",
#   'friend_ids': 'must be an instance of typing.List[int], but there are some errors:
#       ["must be an instance of <class \'int\'>, but received <class \'str\'>"]'})
```
You can also pass the `strict` param (which defaults to False) to the decorator:
```python
@dataclass_validate(strict=True)
@dataclass(frozen=True)
class SomeList:
    values: List[str]

# Invalid item contained in typed List
try:
    SomeList(values=["one", "two", 3])
except TypeValidationError as e:
    print(e)
# => TypeValidationError: Dataclass Type Validation Error (errors = {
#   'x': 'must be an instance of typing.List[str], but there are some errors: 
#       ["must be an instance of <class \'str\'>, but received <class \'int\'>"]'})
```

You can also pass the `before_post_init` param (which defaults to False) to the decorator,
to force the type validation to occur before `__post_init__()` is called.  This can be used
to ensure the types of the field values have been validated before your higher-level semantic
validation is performed in `__post_init__()`.
```python
@dataclass_validate(before_post_init=True)
@dataclass
class User:
    id: int
    name: str

    def __post_init__(self):
        # types of id and name have already been checked before this is called.
        # Otherwise, the following check will throw a TypeError if user passed 
        # `id` as a string or other type that cannot be compared to int.
        if id < 1:
            raise ValueError("superuser not allowed")
```
