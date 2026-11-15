#ifndef KRYON_BROWSER_SCRIPT_BRIDGE_H
#define KRYON_BROWSER_SCRIPT_BRIDGE_H

#include <stddef.h>
#include <stdint.h>

void *browser_script_create(const uint8_t *bootstrap, uint64_t bootstrap_size,
                            uint64_t memory_limit, uint64_t stack_limit,
                            uint32_t time_limit_ms, uint8_t *error,
                            uint64_t error_capacity);
int32_t browser_script_eval(void *handle, const uint8_t *source,
                            uint64_t source_size, uint8_t *error,
                            uint64_t error_capacity);
int32_t browser_script_finish(void *handle, uint8_t *output,
                              uint64_t output_capacity, uint8_t *error,
                              uint64_t error_capacity);
void browser_script_destroy(void *handle);

#endif
