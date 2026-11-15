#define _POSIX_C_SOURCE 200809L

#include "script_bridge.h"

#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "quickjs.h"

typedef struct BrowserScript {
    JSRuntime *runtime;
    JSContext *context;
    JSValue snapshot;
    uint64_t deadline_ns;
    int interrupted;
} BrowserScript;

static uint64_t monotonic_ns(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
        return 0;
    return (uint64_t)now.tv_sec * UINT64_C(1000000000) +
           (uint64_t)now.tv_nsec;
}

static void set_error(uint8_t *output, uint64_t capacity,
                      const char *message) {
    size_t size;
    if (!output || capacity == 0)
        return;
    size = strlen(message);
    if (size >= capacity)
        size = (size_t)capacity - 1;
    memcpy(output, message, size);
    output[size] = 0;
}

static int interrupt_script(JSRuntime *runtime, void *opaque) {
    BrowserScript *script = opaque;
    (void)runtime;
    if (monotonic_ns() < script->deadline_ns)
        return 0;
    script->interrupted = 1;
    return 1;
}

static void discard_exception(BrowserScript *script) {
    JSValue exception = JS_GetException(script->context);
    JS_FreeValue(script->context, exception);
}

/* Render the exception only into the local page status, never a console/log.
   Conversion is still under the page deadline (including hostile toString). */
static void exception_error(BrowserScript *script, uint8_t *output,
                            uint64_t capacity) {
    JSValue exception = JS_GetException(script->context);
    const char *text = JS_ToCString(script->context, exception);
    set_error(output, capacity, text ? text : "JavaScript exception");
    if (output && capacity) {
        for (uint64_t i = 0; i < capacity && output[i]; i++)
            if (output[i] < 32 || output[i] == 127) output[i] = ' ';
    }
    if (text) JS_FreeCString(script->context, text);
    else discard_exception(script);
    JS_FreeValue(script->context, exception);
}

static JSValue eval_bytes(BrowserScript *script, const uint8_t *source,
                          uint64_t source_size, const char *filename) {
    char *terminated = malloc((size_t)source_size + 1);
    JSValue value;

    if (!terminated)
        return JS_ThrowOutOfMemory(script->context);
    memcpy(terminated, source, (size_t)source_size);
    terminated[source_size] = 0;
    value = JS_Eval(script->context, terminated, (size_t)source_size, filename,
                    JS_EVAL_TYPE_GLOBAL);
    free(terminated);
    return value;
}

void browser_script_destroy(void *handle) {
    BrowserScript *script = handle;
    if (!script)
        return;
    if (script->context) {
        JS_FreeValue(script->context, script->snapshot);
        JS_FreeContext(script->context);
    }
    if (script->runtime)
        JS_FreeRuntime(script->runtime);
    free(script);
}

void *browser_script_create(const uint8_t *bootstrap, uint64_t bootstrap_size,
                            uint64_t memory_limit, uint64_t stack_limit,
                            uint32_t time_limit_ms, uint8_t *error,
                            uint64_t error_capacity) {
    BrowserScript *script;
    JSValue value;

    set_error(error, error_capacity, "");
    if (!bootstrap || bootstrap_size == 0 ||
        bootstrap_size > UINT64_C(2097152) ||
        memory_limit < UINT64_C(1048576) ||
        stack_limit < UINT64_C(65536) ||
        time_limit_ms == 0 || time_limit_ms > 1000) {
        set_error(error, error_capacity, "JavaScript configuration rejected");
        return NULL;
    }
    script = calloc(1, sizeof(*script));
    if (!script) {
        set_error(error, error_capacity, "JavaScript runtime unavailable");
        return NULL;
    }
    script->snapshot = JS_UNDEFINED;
    script->runtime = JS_NewRuntime();
    if (!script->runtime) {
        set_error(error, error_capacity, "JavaScript runtime unavailable");
        browser_script_destroy(script);
        return NULL;
    }
    JS_SetMemoryLimit(script->runtime, (size_t)memory_limit);
    JS_SetMaxStackSize(script->runtime, (size_t)stack_limit);
    JS_SetInterruptHandler(script->runtime, interrupt_script, script);
    script->context = JS_NewContext(script->runtime);
    if (!script->context) {
        set_error(error, error_capacity, "JavaScript memory limit reached");
        browser_script_destroy(script);
        return NULL;
    }
    /* Context setup is engine work, not page execution. Start the page-wide
       budget immediately before evaluating the trusted DOM bootstrap. */
    script->deadline_ns =
        monotonic_ns() + (uint64_t)time_limit_ms * UINT64_C(1000000);
    value = eval_bytes(script, bootstrap, bootstrap_size, "<browser-dom>");
    if (JS_IsException(value)) {
        discard_exception(script);
        set_error(error, error_capacity,
                  script->interrupted ? "JavaScript time limit reached"
                                      : "JavaScript DOM setup failed");
        browser_script_destroy(script);
        return NULL;
    }
    if (!JS_IsFunction(script->context, value)) {
        JS_FreeValue(script->context, value);
        set_error(error, error_capacity, "JavaScript DOM setup failed");
        browser_script_destroy(script);
        return NULL;
    }
    script->snapshot = value;
    return script;
}

int32_t browser_script_eval(void *handle, const uint8_t *source,
                            uint64_t source_size, uint8_t *error,
                            uint64_t error_capacity) {
    BrowserScript *script = handle;
    JSValue value;

    set_error(error, error_capacity, "");
    if (!script || !source || source_size > UINT64_C(524288)) {
        set_error(error, error_capacity, "JavaScript source limit reached");
        return 2;
    }
    if (monotonic_ns() >= script->deadline_ns) {
        set_error(error, error_capacity, "JavaScript time limit reached");
        return 2;
    }
    script->interrupted = 0;
    value = eval_bytes(script, source, source_size, "<inline-script>");
    if (JS_IsException(value)) {
        exception_error(script, error, error_capacity);
        if (script->interrupted) {
            set_error(error, error_capacity, "JavaScript time limit reached");
            return 2;
        }
        return 1;
    }
    JS_FreeValue(script->context, value);
    return 0;
}

int32_t browser_script_finish(void *handle, uint8_t *output,
                              uint64_t output_capacity, uint8_t *error,
                              uint64_t error_capacity) {
    BrowserScript *script = handle;
    JSValue value;
    const char *text;
    size_t size = 0;

    set_error(error, error_capacity, "");
    if (output && output_capacity)
        output[0] = 0;
    if (!script || !output || output_capacity == 0) {
        set_error(error, error_capacity, "JavaScript result rejected");
        return 1;
    }
    if (monotonic_ns() >= script->deadline_ns) {
        set_error(error, error_capacity, "JavaScript time limit reached");
        return 2;
    }
    script->interrupted = 0;
    value = JS_Call(script->context, script->snapshot, JS_UNDEFINED, 0, NULL);
    if (JS_IsException(value)) {
        discard_exception(script);
        set_error(error, error_capacity,
                  script->interrupted ? "JavaScript time limit reached"
                                      : "JavaScript result failed");
        return script->interrupted ? 2 : 1;
    }
    text = JS_ToCStringLen2(script->context, &size, value, 0);
    JS_FreeValue(script->context, value);
    if (!text) {
        set_error(error, error_capacity, "JavaScript memory limit reached");
        return 1;
    }
    if (size >= output_capacity) {
        JS_FreeCString(script->context, text);
        set_error(error, error_capacity, "JavaScript result limit reached");
        return 2;
    }
    memcpy(output, text, size);
    output[size] = 0;
    JS_FreeCString(script->context, text);
    return 0;
}
