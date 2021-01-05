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
