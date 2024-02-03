/*
 * Publicly accessible functions when built as a library.
 */

#ifndef hyperscanner_h__
#define hyperscanner_h__

extern int hyperscan(char* fileName, const char* const* patterns, const unsigned int* pattern_flags, const unsigned int* pattern_ids, const unsigned int elements, hs_event onEvent, const int bufSize)

#endif
