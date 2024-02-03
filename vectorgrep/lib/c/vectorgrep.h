/*
 * Publicly accessible functions when built as a library.
 */

#ifndef vectorgrep_h__
#define vectorgrep_h__

extern int vectorscan(char* fileName, const char* const* patterns, const unsigned int* pattern_flags, const unsigned int* pattern_ids, const unsigned int elements, hs_event onEvent, const int bufSize)

#endif
