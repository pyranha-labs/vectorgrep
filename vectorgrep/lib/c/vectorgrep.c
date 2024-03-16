/*
 * Vectorscan library used to perform pattern matching against lines in text files.
 *
 * Primary use is through the vectorscan() function, which sends results to an external caller.
 * It can also be built as a standalone executable for manual testing.
 *
 * See utils/build_vectorgrep.sh for full build process including vectorscan and zstd.
 *
 * Usage:
 *     ./vectorgrep <pattern> <input file>
 */

#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <hs.h>
// Use zstd_zlibwrapper.h instead of zlib.h, it has equivalents for all required gz* calls compatible with both types.
// If a non-ZSTD compatible build is required, replace with zlib.h and no additional changes are needed.
#include <zstd_zlibwrapper.h>

// Return codes for failures from vectorgrep.
typedef enum vectorgrep_ret {
    VECTORGREP_COMPILE_MEM = 1,
    VECTORGREP_COMPILE = 2,
    VECTORGREP_SCRATCH = 3,
    VECTORGREP_DB = 4,
    VECTORGREP_STATE_MEM = 5,
    VECTORGREP_GZ_OPEN = 6,
    VECTORGREP_SCAN = 7
} vectorgrep_ret_t;

/*
 * Stateful information used to buffer line matches from Vectorscan during callbacks.
 *
 * id: The index of the pattern that matched the line.
 * line_number: The index of the line matched.
 * line: Contents of the line that was matched.
 */
typedef struct vectorgrep_result {
    unsigned int id;
    unsigned long long line_number;
    char* line;
} vectorgrep_result_t;

/*
 * Callback function used by vectorgrep onEvent in order to send a result to an external caller.
 *
 * results: Batch of results to return to external caller.
 * result_count: How many entries are in the result batch.
 */
typedef void (*hs_event) (vectorgrep_result_t* results, int result_count);

/*
 * Stateful information used to track additional information from Vectorscan during callbacks.
 *
 * match_count: Total number of matches found since starting scan.
 * line_number: The index of the line matched.
 * line: Contents of the line that was matched.
 * callback: Function to call with simplified match information from Vectorscan.
 */
typedef struct vectorgrep_state {
    unsigned long long match_count;
    unsigned long long line_number;
    char* line;
    hs_event callback;
    unsigned int max_result_index;
    int result_index;
    vectorgrep_result_t* results;
} vectorgrep_state_t;

/*
 * Callback function used by Vectorscan to pass-through match information to an external callback.
 *
 * id: The index of the pattern that matched the line.
 * start: The beginning position of the pattern matched within the line.
 * end: The last position of the pattern matched within the line.
 * flags: What flags were set on this pattern in order to match. i.e. HS_FLAG_DOTALL
 * ctx: Pointer to any data type passed through for reference by hs_scan(). i.e. line as (char*), struct, etc.
 */
static int hs_callback(unsigned int id, unsigned long long start, unsigned long long end, unsigned int flags, void *ctx) {
    vectorgrep_state_t* state = (vectorgrep_state_t*) ctx;
    state->match_count++;

    // Update the next result in the buffer, without calling the callback, to help reduce possible overhead.
    state->result_index++;
    int result_index = state->result_index;
    state->results[result_index].id = id;
    state->results[result_index].line_number = state->line_number;
    strcpy(state->results[result_index].line, state->line);

    // If the result buffer is full, send all results to the external callback and reset.
    if (state->result_index == state->max_result_index) {
        state->callback(state->results, state->result_index + 1);
        state->result_index = -1;
    }

    // Return 0 per Vectorscan documentation to indicate result was handled.
    return 0;
}

/*
 * Dummy callback function to allow testing library through main() by printing the matched lines.
 */
static void event_handler(vectorgrep_result_t* results, int result_count) {
    for (int index = 0; index < result_count; index++) {
        // Print off a line similar to grep -n, where it starts with the line number.
        vectorgrep_result_t result = results[index];
        printf("%llu:%s", result.line_number, result.line);
    }
}

/*
 * Initialize an Vectorscan database from multiple regex patterns.
 *
 * db: Location of the Vectorscan database in memory. It will be initialized in-place.
 * expressions: Regex patterns to initialize into the database.
 * expression_flags: Flags to set on each regex pattern in order to match. i.e. HS_FLAG_DOTALL
 *     Flags in vectorscan use a bitwise OR operator to combine flags. e.g. HS_FLAG_DOTALL | HS_FLAG_SINGLEMATCH == 10
* expression_ids: IDs to apply to each regex pattern to group related patterns and prevent separate callbacks.
 *     Provide unique IDs if every pattern should return matches for a line, even if another pattern already matched.
 * elements: Size the pattern array.
 */
static int init_hs_db(
    hs_database_t** db,
    const char* const* expressions,
    const unsigned int* expression_flags,
    const unsigned int* expression_ids,
    int elements
) {
    int ret = 0;

    hs_compile_error_t* err = NULL;
    if (hs_compile_multi(expressions, expression_flags, expression_ids, elements, HS_MODE_BLOCK, NULL, db, &err) != HS_SUCCESS) {
        ret = VECTORGREP_COMPILE;
    }

    hs_free_compile_error(err);
    return ret;
}

/*
 * Helper to test regex pattern compilation.
 *
 * patterns: Regular expressions to be scanned against every line.
 * pattern_flags: Flags to set on each pattern in order to match. i.e. HS_FLAG_DOTALL
 *     Flags in vectorscan use a bitwise OR operator to combine flags. e.g. HS_FLAG_DOTALL | HS_FLAG_SINGLEMATCH == 10
 * pattern_ids: IDs to apply to each pattern to group related patterns and prevent separate callbacks.
 *     Provide unique IDs if every pattern should return matches for a line, even if another pattern already matched.
 * elements: Size the pattern array.
 */
int check_patterns(
    const char* const* patterns,
    const unsigned int* pattern_flags,
    const unsigned int* pattern_ids,
    const unsigned int elements
) {
    int ret = 0;
    hs_database_t* db = NULL;
    if (init_hs_db(&db, patterns, pattern_flags, pattern_ids, elements) != 0) {
        ret = VECTORGREP_DB;
    }
    hs_free_database(db);
    return ret;
}

/*
 * Scan a GZIP file using Vectorscan.
 *
 * file_name: Location of a local file that can be read line by line.
 * state: Stateful information used to track additional details from Vectorscan during callbacks.
 * db: A compiled Vectorscan pattern database.
 * scratch: A per-thread Vectorscan scratch space allocated for this database.
 * buffer_size: How large of a char buffer to use while reading in strings. Reads up to first newline or len - 1.
 * max_match_count: Stop reading the file after requested number of matches found.
 */
int vectorscan_gz(
    char* file_name,
    vectorgrep_state_t* state,
    hs_database_t* db,
    hs_scratch_t* scratch,
    int buffer_size,
    unsigned long long max_match_count
) {
    int ret = 0;

    // To avoid manual line scanning, use zlib gz* functions to open files and read into buffer.
    // For details on manually reading gzips without gzopen: https://zlib.net/zlib_how.html
    gzFile input_file = gzopen(file_name, "rb");
    if (input_file == Z_NULL) {
        // File could not be opened for reading due to permissions, or bad file type.
        ret = VECTORGREP_GZ_OPEN;
    }

    char* buf = malloc(sizeof(char) * buffer_size);
    while (1) {
        state->line = gzgets(input_file, buf, buffer_size);
        if (state->line == Z_NULL) {
            // EOF or unreadable file.
            break;
        }

        // NOTE: Strip off leading null (0) characters or else the string will look like it is empty.
        // A line may start with any number of leading nulls. Look for the first non-null and update the start.
        if (buf[0] == 0) {
            for (int line_start = 1; line_start < buffer_size; line_start++) {
                if (buf[line_start] != 0) {
                    state->line = buf + line_start;
                    break;
                }
            }
        }

        // Vectorscan the buffer up to the end of the current line. ZLIB will read up to a newline or max buffer length.
        if (hs_scan(db, state->line, strlen(state->line), 0, scratch, hs_callback, state) != HS_SUCCESS) {
            fprintf(stderr, "ERROR: Unable to scan buffer. Exiting.\n");
            ret = VECTORGREP_SCAN;
            break;
        }
        if (max_match_count > 0 && state->match_count >= max_match_count) {
            break;
        }
        state->line_number++;
    }
    gzclose(input_file);

    free(buf);
    return ret;
}

/*
 * Scan a file using Vectorscan for high performance using multiple regexes.
 *
 * file_name: Location of a local file that can be read line by line.
 * patterns: Regular expressions to be scanned against every line.
 * pattern_flags: Flags to set on each pattern in order to match. i.e. HS_FLAG_DOTALL
 *     Flags in vectorscan use a bitwise OR operator to combine flags. e.g. HS_FLAG_DOTALL | HS_FLAG_SINGLEMATCH == 10
 * pattern_ids: IDs to apply to each pattern to group related patterns and prevent separate callbacks.
 *     Provide unique IDs if every pattern should return matches for a line, even if another pattern already matched.
 * elements: Size the pattern array.
 * on_event: Function to call with simplified match information from Vectorscan.
 * buffer_size: How large of a char buffer to use while reading in strings. Reads up to first newline or len - 1.
 * buffer_count: How many buffers should be used to batch on_event results. Total memory = buffer_size * buffer_count.
 * max_match_count: Stop reading the file after requested number of matches found.
 */
int vectorscan(
    char* file_name,
    const char* const* patterns,
    const unsigned int* pattern_flags,
    const unsigned int* pattern_ids,
    const unsigned int elements,
    hs_event on_event,
    const int buffer_size,
    int buffer_count,
    unsigned long long max_match_count
) {
    if (max_match_count > 0 && max_match_count < buffer_count) {
        // If there is a low cap on allowed matches, decrease the buffer size to optimize memory usage.
        buffer_count = max_match_count;
    }
    int ret = 0;

    // Initialize the Vectorscan database, scratch, and state. If any cannot be created, skip processing.
    vectorgrep_state_t* state = (vectorgrep_state_t*) malloc(sizeof(vectorgrep_state_t));
    if (!state) {
        ret = VECTORGREP_STATE_MEM;
        goto cleanup;
    }
    state->match_count = 0;
    state->line_number = 0;
    state->callback = on_event;

    state->result_index = -1;
    state->max_result_index = buffer_count - 1;
    int max_results = state->max_result_index + 1;
    state->results = (vectorgrep_result_t*) malloc(sizeof(vectorgrep_result_t) * max_results);
    if (!state->results) {
        ret = VECTORGREP_COMPILE_MEM;
        goto cleanup;
    }
    // Allocate the result strings separately due to dynamic size to prevent segfaults.
    int results_allocated = 0;
    for (int i = 0; i < max_results; i++) {
        state->results[i].line = malloc(sizeof(char) * buffer_size);
        if (!state->results[i].line) {
            ret = VECTORGREP_COMPILE_MEM;
            goto cleanup;
        }
        results_allocated++;
    }

    hs_database_t* db = NULL;
    hs_scratch_t* scratch = NULL;
    if (init_hs_db(&db, patterns, pattern_flags, pattern_ids, elements) != 0) {
        fprintf(stderr, "ERROR: Unable to create database. Exiting.\n");
        ret = VECTORGREP_DB;
        goto cleanup;
    }
    if (hs_alloc_scratch(db, &scratch) != HS_SUCCESS) {
        fprintf(stderr, "ERROR: Unable to allocate scratch space. Exiting.\n");
        ret = VECTORGREP_SCRATCH;
        goto cleanup;
    }

    // Route scan based on file type to isolate dynamic buffer allocation scope.
    ret = vectorscan_gz(file_name, state, db, scratch, buffer_size, max_match_count);

    // Ensure the buffer is sent if there are any remaining results.
    if (state->result_index != -1) {
        state->callback(state->results, state->result_index + 1);
    }

cleanup:
    // Ensure all buffers are reclaimed before exiting in case usage is multi-threaded.
    for (int index = 0; index < results_allocated; index++) {
        free(state->results[index].line);
    }
    free(state);

    // Ensure the scratch, database, and state are freed before exiting.
    hs_free_scratch(scratch);
    hs_free_database(db);
    return ret;
}

/*
 * Simple function to test reading a file and printing matches when run as a standalone tool.
 *
 * argc: Number of arguments passed from the command line.
 * argv: Arguments passed from the command line.
 */
int main(int argc, char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <pattern> <input file(s)...>\n", argv[0]);
        return -1;
    }

    int ret = 0;
    for (int i = 2; i < argc; i++) {
        char* input_file = argv[i];
        const char* patterns[1];
        unsigned int pattern_flags[1];
        unsigned int pattern_ids[1];
        patterns[0] = argv[1];
        // HS_FLAG_DOTALL for performance.
        // HS_FLAG_MULTILINE to match ^ and $ against newlines.
        // HS_FLAG_SINGLEMATCH to stop after first callback for a pattern.
        pattern_flags[i - 2] = HS_FLAG_DOTALL | HS_FLAG_MULTILINE | HS_FLAG_SINGLEMATCH;
        pattern_ids[i - 2] = i - 2;
        ret = vectorscan(input_file, patterns, pattern_flags, pattern_ids, 1, event_handler, 65535, 256, 0);
    }
    return ret;
}
