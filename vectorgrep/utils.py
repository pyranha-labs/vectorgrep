"""Utilities for scanning text files with Vectorscan."""

import ctypes
import os
import re
import threading
from typing import Callable

# Flags pulled from hs_compile.h
HS_FLAG_CASELESS = 1
HS_FLAG_DOTALL = 2
HS_FLAG_MULTILINE = 4
HS_FLAG_SINGLEMATCH = 8

# Use 101-125 as utility return codes to avoid conflicts with vectorscan and linux return codes.
RC_INVALID_FILE = 101

__libvectorgrep__ = None
__libvectorgrep_path__ = ""
__libvectorscan__ = None
__libvectorscan_path__ = ""
__libzstd__ = None
__libzstd_path__ = ""


class Result(ctypes.Structure):
    """Information about a regex result used to buffer matches from Vectorscan before callbacks.

    C implementation located in vectorgrep/lib/c/vectorgrep.c.

    Fields:
        id: The index of the pattern that matched the line.
        line_number: The index of the line matched in the file.
        line: Contents of the line that was matched.
    """

    _fields_ = [
        ("id", ctypes.c_uint),
        ("line_number", ctypes.c_ulonglong),
        ("line", ctypes.c_char_p),
    ]


# C function type used by vectorgrep to send line match batches back to python.
# Must be declared after struct class for proper pointer declaration.
CALLBACK_TYPE = ctypes.CFUNCTYPE(
    None,
    ctypes.POINTER(Result),
    ctypes.c_int,
    use_errno=False,
    use_last_error=False,
)


def _get_vectorscan_lib() -> ctypes.cdll:
    """Lazily load the Vectorscan library to allow use in subprocesses.

    This library will only be used if an equivalent library is not already installed on the system.
    This behaves similar to a module property in that it will only load if not previously loaded.
    """
    global __libvectorscan__  # pylint: disable=global-statement
    if __libvectorscan__ is None:
        # Load and cache the Vectorscan library to prevent repeat loads within the process.
        __libvectorscan__ = ctypes.cdll.LoadLibrary(__libvectorscan_path__)
    return __libvectorscan__


def _get_vectorgrep_lib() -> ctypes.cdll:
    """Lazily load the VectorGrep library, which relies on Vectorscan, to allow use in subprocesses.

    This behaves similar to a module property in that it will only load if not previously loaded.
    """
    # Cache ZSTD/Vectorscan libraries first to provide vectorgrep lib fallback to local builds.
    # These will only be used if the OS does not have the libraries installed already.
    _get_zstd_lib()
    _get_vectorscan_lib()
    global __libvectorgrep__  # pylint: disable=global-statement
    if __libvectorgrep__ is None:
        # Load and cache the vectorgrep library to prevent repeat loads within the process.
        __libvectorgrep__ = ctypes.cdll.LoadLibrary(__libvectorgrep_path__)
    return __libvectorgrep__


def _get_zstd_lib() -> ctypes.cdll:
    """Lazily load the ZSTD library to allow use in subprocesses.

    This library will only be used if libzstd is not already installed on the system.
    This behaves similar to a module property in that it will only load if not previously loaded.
    """
    global __libzstd__  # pylint: disable=global-statement
    if __libzstd__ is None:
        # Load and cache the ZSTD library to prevent repeat loads within the process.
        __libzstd__ = ctypes.cdll.LoadLibrary(__libzstd_path__)
    return __libzstd__


def check_compatibility(
    patterns: list,
    flags: list[int] = (),
) -> int:
    """Helper to test regex pattern compilation in Vectorscan without scanning a file.

    Examples of bad patterns tested by Vectorscan can be found in their code at: unit/hyperscan/bad_patterns.cpp

    Args:
        patterns: Regex patterns in text format used to match lines.
        flags: Flags to set on each pattern in order to match. i.e. HS_FLAG_DOTALL
            Flags must use bitwise OR operator to combine flags. e.g. HS_FLAG_DOTALL | HS_FLAG_SINGLEMATCH = 10
            Defaults to: HS_FLAG_DOTALL | HS_FLAG_MULTILINE | HS_FLAG_SINGLEMATCH

    Returns:
        The response code received from the C backend if there was a failure, 0 otherwise.
    """
    pattern_array, flags_array, ids_array = prepare_patterns(patterns, flags=flags)
    vectorgrep_lib = _get_vectorgrep_lib()
    ret_code = vectorgrep_lib.check_patterns(
        pattern_array,
        flags_array,
        ids_array,
        len(pattern_array),
    )
    return ret_code


def configure_libraries(
    libhs: str | None = None,
    libvectorgrep: str | None = None,
    libzstd: str | None = None,
) -> None:
    """Set the paths to library files.

    Args:
        libhs: Path to the vectorscan/hyperscan library object on the local system.
            Uses "libhs" moniker from Hyperscan until further notice.
        libvectorgrep: Path to the libvectorgrep library object on the local system.
        libzstd: Path to the zstd library object on the local system.
    """
    if libhs:
        if __libvectorscan__:
            raise ValueError("libhs already loaded, configuration overrides must be called before library usage")
        global __libvectorscan_path__  # pylint: disable=global-statement
        __libvectorscan_path__ = libhs
    if libvectorgrep:
        if __libvectorgrep__:
            raise ValueError(
                "libvectorgrep already loaded, configuration overrides must be called before library usage"
            )
        global __libvectorgrep_path__  # pylint: disable=global-statement
        __libvectorgrep_path__ = libvectorgrep
    if libzstd:
        if __libzstd__:
            raise ValueError("libzstd already loaded, configuration overrides must be called before library usage")
        global __libzstd_path__  # pylint: disable=global-statement
        __libzstd_path__ = libzstd


def grep(  # pylint: disable=too-many-arguments
    file: str,
    patterns: list[str],
    ignore_case: bool = False,
    count_only: bool = False,
    only_matching: bool = False,
    no_messages: bool = False,
    errors: str = "ignore",
    max_match_count: int = 0,
) -> tuple[int | list[tuple[int, str]], int]:
    """Basic reusable grep like function using Vectorscan.

    Contrary to the "grep" in the name, it returns the lines instead of printing them. Useful for testing
    basic functionality on a system, or simple use cases.

    Args:
        file: Path to a file on the local filesystem.
        patterns: Regex patterns compatible with Vectorscan.
        ignore_case: Perform case-insensitive matching.
        count_only: Whether to count the matches, instead of decode the byte lines and store them.
        only_matching: Save only the matched (non-empty) parts of a matching line, with each part on a separate line.
        no_messages: Suppress error messages about nonexistent or unreadable files.
        errors: Error handling scheme to use for the handling of decoding errors.
            Refer to python "bytes.decode()" for more information.
        max_match_count: Stop reading the file after requested number of matches found.
            Use 0 to indicate no limit.

    Returns:
        Line count, or list of tuples with the line index and matching line, and return code.
            Return codes 1-7 are from vectorscan, and 101-125 from python.

    Raises:
        FileNotFoundError if the file does not exist and no_messages is false.
        ValueError if the file is a directory and no_messages is false.
    """
    return_code = 0
    compiled_patterns = [re.compile(pattern) for pattern in patterns]
    results = [] if not count_only else 0

    # Exception messages taken directly from "grep" error messages.
    # Silent behavior also taken from "grep" to not raise or print a message if path is invalid.
    if not os.path.exists(file):
        return_code = RC_INVALID_FILE
        if not no_messages:
            raise FileNotFoundError("No such file or directory")
    if os.path.isdir(file):
        return_code = RC_INVALID_FILE
        if not no_messages:
            raise ValueError("is a directory")

    if not return_code:

        def _c_callback(matches: list, count: int) -> None:
            """Called by the C library everytime it finds a batch of matching lines."""
            nonlocal results
            if count_only:
                results += count
            else:
                if only_matching:
                    # "Only matching" grep behavior converts every line into every match group per line.
                    for index in range(count):
                        match = matches[index]
                        line = match.line.decode(errors=errors)
                        # NOTE: Do not use findall, only finditer provides the correct results.
                        for partial in compiled_patterns[match.id].finditer(line):
                            results.append((match.line_number + 1, f"{partial.group()}\n"))
                else:
                    for index in range(count):
                        match = matches[index]
                        line = match.line.decode(errors=errors)
                        results.append((match.line_number + 1, line))

        # Always use vectorscan function defaults, but add caseless if user requested.
        flags = HS_FLAG_DOTALL | HS_FLAG_MULTILINE | HS_FLAG_SINGLEMATCH
        if ignore_case:
            flags |= HS_FLAG_CASELESS
        return_code = scan(
            file,
            patterns,
            _c_callback,
            flags=[flags for _ in patterns],
            max_match_count=max_match_count,
        )

    return results, return_code


def prepare_patterns(
    patterns: list[str],
    flags: list[int] = (),
    ids: list[int] = (),
) -> tuple[ctypes.Array, ctypes.Array, ctypes.Array]:
    """Prepare python regexes and flags for use with Vectorscan.

    Args:
        patterns: Regex patterns in text format used to match lines.
        flags: Flags to set on each pattern in order to match. i.e. HS_FLAG_DOTALL
            Flags must use bitwise OR operator to combine flags. e.g. HS_FLAG_DOTALL | HS_FLAG_SINGLEMATCH = 10
            Defaults to: HS_FLAG_DOTALL | HS_FLAG_MULTILINE | HS_FLAG_SINGLEMATCH
        ids: IDs to apply to each pattern to group related patterns and prevent separate callbacks.
            Defaults to: All patterns share the same ID; multiple callbacks for the same line are not received.

    Returns:
        C array of strings, and C array of ints, compatible as C lib function args.
    """
    if not flags:
        # Set the default flags for most common usage if none were provided.
        # Vectorscan/Hyperscan flags: https://intel.github.io/hyperscan/dev-reference/api_files.html
        # HS_FLAG_DOTALL for performance.
        # HS_FLAG_MULTILINE to match ^ and $ against newlines.
        # HS_FLAG_SINGLEMATCH to stop after first callback for a pattern.
        flags = [HS_FLAG_DOTALL | HS_FLAG_MULTILINE | HS_FLAG_SINGLEMATCH for _ in patterns]
    if len(flags) != len(patterns):
        raise ValueError(
            f"Found {len(flags)} flags, expecting {len(patterns)}. Vectorscan flags must be provided for each regex to compile the database."
        )

    if not ids:
        # Set the default group IDs to 0 for the most common usage if none were provided (all patterns in 1 group).
        # This will ensure that searching will stop after the first match, and only 1 callback is received per line.
        ids = [0 for _ in patterns]
    if len(ids) != len(patterns):
        raise ValueError(
            f"Found {len(ids)} ids, expecting {len(patterns)}. Vectorscan ids must be provided for each regex to compile the database."
        )

    # C string arrays must be created by performing the following:
    # 1. Convert all strings to bytes.
    # 2. Find the C char pointer class for the array length, i.e. a list of 29 strings is a c_char_p_Array_29
    # 3. Assign the pointer for the byte list to every position in the C array to mimic a C array of char pointers.
    encoded_patterns = []
    for pattern in patterns:
        if not pattern:
            # Vectorscan does not allow empty strings for matching, prevent attempts to use.
            raise ValueError(f'Invalid pattern "{pattern}" found. Please provide a valid regex for Vectorscan.')
        encoded_patterns.append(pattern.encode())
    pattern_array = (ctypes.c_char_p * (len(encoded_patterns)))()
    pattern_array[:] = encoded_patterns
    flags_array = (ctypes.c_uint * (len(flags)))()
    flags_array[:] = [ctypes.c_uint(flag) for flag in flags]
    ids_array = (ctypes.c_uint * (len(ids)))()
    ids_array[:] = [ctypes.c_uint(id_num) for id_num in ids]
    return pattern_array, flags_array, ids_array


def scan(  # pylint: disable=too-many-arguments
    path: str,
    patterns: list[str],
    callback: Callable,
    flags: list[int] = (),
    ids: list[int] = (),
    buffer_size: int = 262140,
    buffer_count: int = 16,
    max_match_count: int = 0,
) -> int:
    """Read a text file for regex patterns using Vectorscan.

    Supports GZIP, ZSTD, and Plain Text files.

    Args:
        path: Location of the file to be read by vectorscan.
        patterns: Regex patterns in text format used to match lines.
        callback: Where every regex hit (line index, pattern id, and byte string) are sent.
            Must match CALLBACK_TYPE.
        flags: Flags to set on each pattern in order to match. i.e. HS_FLAG_DOTALL
            Flags must use bitwise OR operator to combine flags. e.g. HS_FLAG_DOTALL | HS_FLAG_SINGLEMATCH = 10
            Defaults to: HS_FLAG_DOTALL | HS_FLAG_MULTILINE | HS_FLAG_SINGLEMATCH
        ids: IDs to apply to each pattern to group related patterns and prevent separate callbacks.
            Defaults to: All patterns share the same ID; multiple callbacks for the same line are not received.
        buffer_size: How large of a buffer to use while reading in chars. Reads up to first newline or len - 1.
        buffer_count: How many line matches to buffer before calling callback.
            Reduces overhead of C callback calls, at cost of delaying python processing.
            Basic guidelines:
                Multithreading + millions of matches = increase limit.
                Multiprocessing or few matches = decrease limit or leave as is.
        max_match_count: Stop reading the file after requested number of matches found.
            Use 0 to indicate no limit.

    Returns:
        Response code received from the C backend if there was a failure, 0 otherwise.
    """
    pattern_array, flags_array, ids_array = prepare_patterns(patterns, flags=flags, ids=ids)

    # Wrap the callback in the ctype to allow passing to C functions.
    callback = CALLBACK_TYPE(callback)
    vectorgrep_lib = _get_vectorgrep_lib()
    ret_code = 0

    # NOTE: Do not remove this wrapper or change thread from daemon to ensure that Python receives signals.
    def _wrapper() -> None:
        """Wrapper to allow running the CDLL call as non-blocking and allow Python to intercept signals."""
        nonlocal ret_code
        ret_code = vectorgrep_lib.vectorscan(
            path.encode(),
            pattern_array,
            flags_array,
            ids_array,
            len(pattern_array),
            callback,
            buffer_size,
            buffer_count,
            ctypes.c_ulonglong(max_match_count),
        )

    vectorscan_thread = threading.Thread(target=_wrapper, daemon=True)
    vectorscan_thread.start()
    try:
        # Hard cap the thread at 1 hour in case anything goes wrong.
        vectorscan_thread.join(timeout=3600)
    except KeyboardInterrupt:
        ret_code = 130
    return ret_code


# Call configuration update at least once to use defaults.
if not __libvectorgrep_path__:
    module = os.path.abspath(os.path.dirname(__file__))
    configure_libraries(
        libhs=os.path.join(module, "lib", "libhs.so.5.4.11"),
        libvectorgrep=os.path.join(module, "lib", "libvectorgrep.so"),
        libzstd=os.path.join(module, "lib", "libzstd.so.1.5.5"),
    )
