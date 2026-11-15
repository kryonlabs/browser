#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "../src/script_bridge.h"

static int failures;

static void check(int condition, const char *name) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", name);
        failures++;
    }
}

static double seconds(void) {
    struct timespec value;
    clock_gettime(CLOCK_MONOTONIC, &value);
    return (double)value.tv_sec + (double)value.tv_nsec / 1000000000.0;
}

int main(void) {
    static const char bootstrap[] =
        "(() => { const encode = JSON.stringify.bind(JSON);"
        "return () => encode({answer: globalThis.answer || 0}); })()";
    struct {
        uint8_t data[sizeof(bootstrap) - 1];
        uint8_t sentinel;
    } exact_bootstrap;
    uint8_t error[257];
    uint8_t output[1024];
    memcpy(exact_bootstrap.data, bootstrap, sizeof(exact_bootstrap.data));
    exact_bootstrap.sentinel = 'x';
    void *script = browser_script_create(
        exact_bootstrap.data, sizeof(exact_bootstrap.data), UINT64_C(8388608),
        UINT64_C(262144), 100, error, sizeof(error));
    check(script != NULL, "create bounded runtime from exact-length input");
    if (script) {
        static const char isolation[] =
            "if (typeof std !== 'undefined' || typeof os !== 'undefined' || "
            "typeof process !== 'undefined' || typeof require !== 'undefined') "
            "throw new Error('host API leaked')";
        static const char throws[] = "throw new Error('page-private secret')";
        static const char recovery[] = "globalThis.answer = 6 * 7";
        struct {
            uint8_t data[sizeof(recovery) - 1];
            uint8_t sentinel;
        } exact_recovery;
        memcpy(exact_recovery.data, recovery, sizeof(exact_recovery.data));
        exact_recovery.sentinel = 'x';
        check(browser_script_eval(script, (const uint8_t *)isolation,
                                  strlen(isolation), error, sizeof(error)) == 0,
              "no std, os, process, or require API");
        check(browser_script_eval(script, (const uint8_t *)throws,
                                  strlen(throws), error, sizeof(error)) == 1 &&
                  strcmp((const char *)error, "Error: page-private secret") == 0,
              "script error detail is returned to the caller and contained");
        check(browser_script_eval(script, exact_recovery.data,
                                  sizeof(exact_recovery.data), error,
                                  sizeof(error)) == 0,
              "runtime continues with exact-length input after an exception");
        check(browser_script_finish(script, output, sizeof(output), error,
                                    sizeof(error)) == 0 &&
                  strcmp((const char *)output, "{\"answer\":42}") == 0,
              "snapshot returns post-error state");
        browser_script_destroy(script);
    }

    script = browser_script_create(
        (const uint8_t *)bootstrap, strlen(bootstrap), UINT64_C(8388608),
        UINT64_C(262144), 35, error, sizeof(error));
    if (script) {
        static const char loop[] = "for (;;) {}";
        double started = seconds();
        int status = browser_script_eval(script, (const uint8_t *)loop,
                                         strlen(loop), error, sizeof(error));
        double elapsed = seconds() - started;
        check(status == 2 && elapsed < 0.75,
              "interrupt deadline stops an infinite loop");
        browser_script_destroy(script);
    } else {
        check(0, "create deadline runtime");
    }

    script = browser_script_create(
        (const uint8_t *)bootstrap, strlen(bootstrap), UINT64_C(2097152),
        UINT64_C(131072), 100, error, sizeof(error));
    if (script) {
        static const char allocation[] =
            "globalThis.huge = new ArrayBuffer(64 * 1024 * 1024)";
        check(browser_script_eval(script, (const uint8_t *)allocation,
                                  strlen(allocation), error,
                                  sizeof(error)) != 0,
              "memory limit rejects a large allocation");
        browser_script_destroy(script);
    } else {
        check(0, "create memory-limited runtime");
    }

    script = browser_script_create(
        (const uint8_t *)bootstrap, strlen(bootstrap), UINT64_C(8388608),
        UINT64_C(262144), 35, error, sizeof(error));
    if (script) {
        static const char hostile[] = "throw {toString(){for(;;){}}}";
        double started = seconds();
        check(browser_script_eval(script, (const uint8_t *)hostile,
                                  strlen(hostile), error, sizeof(error)) == 2 &&
                  seconds() - started < 0.75,
              "exception formatting remains inside the page deadline");
        browser_script_destroy(script);
    } else check(0, "create exception-formatting runtime");

    if (failures == 0)
        puts("QuickJS isolation, exception recovery, deadline and memory limit verified");
    return failures != 0;
}
