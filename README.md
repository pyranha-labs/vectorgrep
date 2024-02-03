# HyperGrep

[![os: linux](https://img.shields.io/badge/os-linux-blue)](https://docs.python.org/3.10/)
[![python: 3.10+](https://img.shields.io/badge/python-3.10_|_3.11-blue)](https://devguide.python.org/versions)
[![python style: google](https://img.shields.io/badge/python%20style-google-blue)](https://google.github.io/styleguide/pyguide.html)
[![imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://github.com/PyCQA/isort)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![code style: pycodestyle](https://img.shields.io/badge/code%20style-pycodestyle-green)](https://github.com/PyCQA/pycodestyle)
[![doc style: pydocstyle](https://img.shields.io/badge/doc%20style-pydocstyle-green)](https://github.com/PyCQA/pydocstyle)
[![static typing: mypy](https://img.shields.io/badge/static_typing-mypy-green)](https://github.com/python/mypy)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint)
[![testing: pytest](https://img.shields.io/badge/testing-pytest-yellowgreen)](https://github.com/pytest-dev/pytest)
[![security: bandit](https://img.shields.io/badge/security-bandit-black)](https://github.com/PyCQA/bandit)
[![license: MIT](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

HyperGrep is a fast (Hyperspeed) Global Regular Expression Processing library for Python. It uses Intel Hyperscan
to maximize performance, and can be used with multi-threaded or multi-processed applications. While a standard grep
if designed to print, this is designed to allow full control over processing matches. The library supports scanning
plaintext, gzip, and ztsd compressed files for regular expressions, and customizing the action to take when matched.

For full information on the amazing performance that can be obtained through Intel Hyperscan with, refer to:  
[Hyperscan](https://github.com/intel/hyperscan)


## Table Of Contents

  * [Key Features](#key-features)
  * [Compatibility](#compatibility)
  * [Getting Started](#getting-started)
    * [Installation](#installation)
    * [Examples](#examples)
    * [Contribute](#contribute)
    * [Advanced Guides](#advanced-guides)
  * [FAQ](#faq)


## Key Features

- **Simplicity**
  - No experience with Hyperscan required. Provides "grep" styled interfaces.
  - No external dependencies, and no building required (on natively supported platforms).
  - Built in support for compressed and uncompressed files.
- **Speed**
  - Uses Hyperscan, a high-performance multiple regex matching library.
  - Performs read and regex operations outside Python.
  - Batches results for Python, reducing overhead (customizable).
- **Parallelism**
  - Bypasses GIL (Global Interpreter Lock) during read and regex operations to allow proper multithreading.
  - Python consumer threads (callbacks) are able to handle many producer threads (readers).


## Compatibility

- Supports Python 3.10+
- Supports Linux systems with x86_64 architecture
  - Tested on Ubuntu Trusty (14.04) and above
  - Other Linux distros may work, but are not guaranteed
  - May be able to be built on Windows/OSX manually
  - More platforms are planned to be supported (natively) in the future
- Some regex constructs are not supported by Hyperscan in order to guarantee stable performance
  - For more information refer to: [Unsupported Constructs](https://intel.github.io/hyperscan/dev-reference/compilation.html#unsupported-constructs)


## Getting Started

### Installation

- Install HyperGrep via pip:
    ```shell
    pip install hypergrep
    ```

- Or via git clone:
    ```shell
    git clone <path to fork>
    cd hypergrep
    pip install .
    ```

- Or build and install from wheel:
    ```shell
    # Build locally.
    git clone <path to fork>
    cd hypergrep
    make wheel
    
    # Push dist/hypergrep*.tar.gz to environment where it will be installed.
    pip install dist/hypergrep*.tar.gz
    ```

### Examples

- Read one file with the example single threaded command:
    ```shell
    # hypergrep/scanner.py <regex> <file>
    hypergrep/scanner.py pattern ./hypergrep/scanner.py
    ```

- Read multiple files with the multithreaded command (drop in replacement for `grep` where patterns are compatible):
    ```shell
    # From install:
    # hypergrep <regex> <file(s)>
    hypergrep pattern ./hypergrep/scanner.py

    # From package:
    # hypergrep/multiscanner.py <regex> <file>
    hypergrep/multiscanner.py pattern ./hypergrep/scanner.py
    ```

- Collect all matches from a file, similar to grep, and perform a custom operation on results:
    ```python
    import hypergrep
    
    file = "./hypergrep/scanner.py"
    pattern = 'pattern'
    
    results, return_code = hypergrep.grep(file, [pattern])
    for index, line in results:
        print(f'{index}: {line}')
    ```

- Manually scan a file and perform a custom operation on match:
    ```python
    import hypergrep
    
    file = "./hypergrep/scanner.py"
    pattern = 'pattern'

    def on_match(matches: list, count: int) -> None:
        for index in range(count):
            match = matches[index]
            line = match.line.decode(errors='ignore')
            print(f'Custom print: {line.rstrip()}')
    
    hypergrep.scan(file, [pattern], on_match)
    ```

- Override the `libhs` and/or `libzstd` libraries to use files outside the package.
Must be called before any other usage of `hypergrep`:
    ```python
    import hypergrep

    hypergrep.configure_libraries(
        libhs='/home/myuser/libhs.so.mybuild',
        libzstd='/home/myuser/libzstd.so.mybuild',
    )
    ```

### Contributing

Refer to the [Contributing Guide](CONTRIBUTING.md) for information on how to contribute to this project.

### Advanced Guides

Refer to [How Tos](docs/HOW_TO.md) for more advanced topics, such as building the shared library objects.


## FAQ

#### Q: How does HyperGrep compare to other Hyperscan python libraries?

**A:** HyperGrep has a specific goal: provide a high performance "grep" like interface in python,
but with more control. It is not intended to be a full set of bindings to Hyperscan. If you need
full control over the low level backend, there are other python libraries intended for that use case. Here are
a few of the reasons for the focused goal of this library:

- Simplify developer integration.
  - No experience with Hyperscan required.
  - Familiarity with `grep` variants beneficial, but not required.
- Avoid messy subprocess chains common in "parallel grep" implementations.
  - Commands like `zgrep` are actually a `zcat` + `grep`. This can lead to 3+ processes per file read.
  - Subprocessing is messy in general, best to minimize its use as much as possible.
- Optimize performance.
  - Reduce callbacks to/from python to reduce overhead.
  - Allow true multithreading during read and regex matching.
  - Provide the pattern matched in multi-regex searches, without having to repeat the search in Python.

When it comes to performance, here is an example of the benefit of this design. Due to the performance of
Hyperscan, it is also often faster than native `grep` variants, even while using python. Scenario setup:
- 2.10GHz Intel x86_64 Processor
- ~17M line file (~300M gzip compressed, ~3G uncompressed).
- ~800 PCRE patterns.
- Counting only, no extra processing of lines.
- Each job run 5 times and averaged (lower is better).

|   | Scenario (Uncompressed timings in parenthesis) | HyperGrep     | Full bindings     | zgrep (grep)  |
|---|------------------------------------------------|---------------|-------------------|---------------|
| 1 | ~90K matches, 1 pattern                        | 8.2s (2.5s)   | 22.8s (15.5s)     | 12.5s (5.2s)  |
| 2 | ~900K matches, 10 patterns                     | 9.7s (3.8s)   | 25.7s (16.8s)     | 19.8s (17.3s) |
| 3 | ~15M matches, ~800 patterns                    | 44.2s (38.1s) | 73.5s (57.7s)     | *             |
| 4 | Scenario #3 (x4 files), 1 process (4 threads)  | 49.6s (46.8s) | 1432.6s (1302.2s) | *             |

* GNU grep does not allow multiple PCRE patterns natively, and concatenation via "or" failed.
