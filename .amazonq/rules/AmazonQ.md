# AI Coding Companion Instructions
* Use this information to find information and write better code.
## Code Structure & Quality
- **Modular Design**: Generate code in distinct, logical modules with clear responsibilities for improved organization and collaboration. However, don't over-abstract the code. Human readability is as important as extensibility.
- **Meaningful Naming**: Use descriptive, domain-specific names for variables, functions, and classes to enhance readability.
- **Error Handling**: Implement comprehensive error handling with informative messages and recovery strategies.

## Tests
* Information on how automated tests are implemented in the project can be found [HERE](./tests/README.md)
* Unit tests should run independently and mock all dependencies
* Development should follow a Test Driven Development (TDD) process where the test is written first and run for failure, then the logic is written and the test is observed to pass.

# Documentation
* `README.md` files exist in many directories that explain how to work with the files in the directory.
* When adding / updating documentation keep the documentation concise and to the point.
* Don't add documentation or commentary on industry best practices or documentation that does not directly relate to the solution.

### Unit Tests
* When code has been completed, run unit tests 
* Run tests using this command from the top directory of the repository:
``` bash
make test
```

### Steps to Develop Code
* When developing code, try to do exactly what is asked
* Do not introduce new requirements or infer features or functionality
* Follow a Test Driven Development (TDD) process when writing code. First write a unit test, watch it fail. Then write the test logic and watch it pass.
* Always add concise documentation when adding new logic. Update existing documentation to when changing logic.
* After developing code, run `Format & Lint`, and then run `Unit Tests`. Ensure these processes pass.
* If unit tests or lint do not pass, then fix them, and rerun until they do pass.

### Code Conventions
* Always use explicit strong types where possible in method signatures and return types.
* Prefer to use named parameters over positional parameters when making method calls.
* Do not create `__init__.py` files unless explicitly asked to do so.
* Always prefer classes with `@staticmethod`'s over plain methods. 
* This project uses [Google Docstring Style](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings)
* Add this header at the top of each file:
``` python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
```