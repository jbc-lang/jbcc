/* jbcc runtime for straight-line programs. Values are immutable strings. */
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct jbc_buffer {
    struct jbc_buffer *next;
    char text[];
};

static struct jbc_buffer *buffers;

static void fail(const char *message)
{
    fprintf(stderr, "jbcc runtime: %s\n", message);
    exit(EXIT_FAILURE);
}

static char *allocate(size_t length)
{
    if (length >= SIZE_MAX - sizeof(struct jbc_buffer))
        fail("value is too large");
    struct jbc_buffer *buffer = malloc(sizeof *buffer + length + 1);
    if (!buffer)
        fail("out of memory");
    buffer->next = buffers;
    buffers = buffer;
    return buffer->text;
}

void jbc_finish(void)
{
    while (buffers) {
        struct jbc_buffer *next = buffers->next;
        free(buffers);
        buffers = next;
    }
}

const char *jbc_concat(const char *left, const char *right)
{
    size_t a = strlen(left), b = strlen(right);
    if (b > SIZE_MAX - a)
        fail("value is too large");
    char *out = allocate(a + b);
    memcpy(out, left, a);
    memcpy(out + a, right, b + 1);
    return out;
}

static int64_t integer(const char *text, const char *file, int line, int column)
{
    char *end;
    errno = 0;
    intmax_t n = strtoimax(text, &end, 10);
    if (errno == ERANGE || n < INT64_MIN || n > INT64_MAX || end == text || *end) {
        fprintf(stderr, "%s:%d:%d: '+' requires signed 64-bit integers\n", file, line, column);
        exit(EXIT_FAILURE);
    }
    return (int64_t)n;
}

const char *jbc_add(const char *left, const char *right, const char *file, int line, int column)
{
    int64_t a = integer(left, file, line, column);
    int64_t b = integer(right, file, line, column);
    if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b)) {
        fprintf(stderr, "%s:%d:%d: integer addition overflow\n", file, line, column);
        exit(EXIT_FAILURE);
    }
    char *out = allocate(20);
    snprintf(out, 21, "%" PRId64, a + b);
    return out;
}

void jbc_print(const char *value)
{
    puts(value);
}
