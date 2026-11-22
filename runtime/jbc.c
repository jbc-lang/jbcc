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

/* Compare decimal text directly so significant digits survive on every target. */
struct decimal {
    const char *whole, *fraction;
    size_t digits, places;
    int sign;
};

static int parse_decimal(const char *text, struct decimal *n)
{
    n->sign = *text == '-' ? -1 : 1;
    if (*text == '+' || *text == '-') ++text;
    n->whole = text;
    n->digits = strspn(text, "0123456789");
    text += n->digits;
    if (*text == '.') ++text;
    n->fraction = text;
    n->places = strspn(text, "0123456789");
    if (text[n->places] || (!n->digits && !n->places)) return 0;
    while (n->digits && *n->whole == '0') {
        ++n->whole;
        --n->digits;
    }
    while (n->places && n->fraction[n->places - 1] == '0') --n->places;
    if (!n->places && !n->digits) n->sign = 0;
    return 1;
}

int jbc_truth(const char *value)
{
    struct decimal n;
    return parse_decimal(value, &n) ? n.sign != 0 : *value != '\0';
}

int jbc_compare(const char *left, const char *right)
{
    struct decimal a, b;
    if (!parse_decimal(left, &a) || !parse_decimal(right, &b))
        return strcmp(left, right);
    if (a.sign != b.sign) return a.sign - b.sign;
    if (a.digits != b.digits) return (a.digits > b.digits ? 1 : -1) * a.sign;
    int cmp = memcmp(a.whole, b.whole, a.digits);
    if (!cmp) {
        size_t common = a.places < b.places ? a.places : b.places;
        cmp = memcmp(a.fraction, b.fraction, common);
        if (!cmp) cmp = (a.places > b.places) - (a.places < b.places);
    }
    return ((cmp > 0) - (cmp < 0)) * a.sign;
}
