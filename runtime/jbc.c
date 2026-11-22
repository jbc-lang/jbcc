/* jbcc runtime for straight-line programs. Values are immutable strings. */
#include <errno.h>
#include <math.h>
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

static void numeric_error(const char *file, int line, int column, const char *message)
{
    fprintf(stderr, "%s:%d:%d: %s\n", file, line, column, message);
    exit(EXIT_FAILURE);
}

static int64_t integer(const char *s, const char *file, int line, int column)
{
    errno = 0;
    intmax_t n = strtoimax(s, NULL, 10);
    if (errno || n > INT64_MAX || n < INT64_MIN)
        numeric_error(file, line, column, "integer operand out of range");
    return (int64_t)n;
}

static int multiply_overflows(int64_t a, int64_t b)
{
    if (a > 0) return b > INT64_MAX / a || b < INT64_MIN / a;
    if (a < 0 && b < 0) return a < INT64_MAX / b;
    if (a < 0 && b > 0) return a < INT64_MIN / b;
    return 0;
}

const char *jbc_arithmetic(char op, const char *left, const char *right,
                           const char *file, int line, int column)
{
    struct decimal lhs, rhs;
    if (!parse_decimal(left, &lhs) || !parse_decimal(right, &rhs))
        numeric_error(file, line, column, "arithmetic requires numeric operands");
    if (op == '/' && rhs.sign == 0)
        numeric_error(file, line, column, "division by zero");

    if (op != '/' && !strchr(left, '.') && !strchr(right, '.')) {
        int64_t a = integer(left, file, line, column);
        int64_t b = integer(right, file, line, column);
        int64_t result;
        if (op == '+') {
            if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b))
                numeric_error(file, line, column, "integer addition overflow");
            result = a + b;
        } else if (op == '-') {
            if ((b > 0 && a < INT64_MIN + b) || (b < 0 && a > INT64_MAX + b))
                numeric_error(file, line, column, "integer subtraction overflow");
            result = a - b;
        } else {
            if (multiply_overflows(a, b))
                numeric_error(file, line, column, "integer multiplication overflow");
            result = a * b;
        }
        char *out = allocate(20);
        snprintf(out, 21, "%" PRId64, result);
        return out;
    }

    long double a = strtold(left, NULL), b = strtold(right, NULL);
    long double result;
    switch (op) {
        case '+': result = a + b; break;
        case '-': result = a - b; break;
        case '*': result = a * b; break;
        default: result = a / b; break;
    }
    if (!isfinite(a) || !isfinite(b) || !isfinite(result))
        numeric_error(file, line, column, "decimal arithmetic out of range");
    int length = snprintf(NULL, 0, "%.15Lf", result);
    if (length < 0) fail("decimal formatting failed");
    char *out = allocate((size_t)length);
    snprintf(out, (size_t)length + 1, "%.15Lf", result);
    while (out[length - 1] == '0') out[--length] = '\0';
    if (out[length - 1] == '.') out[--length] = '\0';
    return strcmp(out, "-0") == 0 ? "0" : out;
}

int jbc_for_test(const char *value, const char *limit, const char *step,
                 const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n) || !parse_decimal(limit, &n) || !parse_decimal(step, &n))
        numeric_error(file, line, column, "FOR requires numeric bounds and step");
    int cmp = jbc_compare(value, limit);
    return n.sign < 0 ? cmp >= 0 : cmp <= 0;
}

/* Keep variable values and protect temporaries belonging to enclosing loops. */
void jbc_collect(struct jbc_buffer *mark, const char ***live)
{
    struct jbc_buffer **link = &buffers;
    while (*link != mark) {
        struct jbc_buffer *buffer = *link;
        const char ***slot = live;
        while (*slot && **slot != buffer->text) ++slot;
        if (*slot) {
            link = &buffer->next;
        } else {
            *link = buffer->next;
            free(buffer);
        }
    }
}

/* Locate a component at this level, recurse within its byte range, then
   splice the replacement back into the enclosing value. */
static const char *array_part(const char *s, size_t len, const int64_t *index,
                              int count, int level, const char *replacement)
{
    if (level == count) {
        if (replacement) return replacement;
        char *out = allocate(len);
        memcpy(out, s, len);
        out[len] = '\0';
        return out;
    }
    unsigned char mark = (unsigned char)(254 - level);
    size_t begin = 0, end = 0, padding = 0;
    int64_t target = index[level];
    if (target == -1 && replacement) {
        begin = end = len;
        padding = len != 0;
    } else {
        if (target < 1) return "";
        for (int64_t n = 1; n < target; ++n) {
            const char *next = memchr(s + begin, mark, len - begin);
            if (!next) {
                if (!replacement) return "";
                padding = (size_t)(target - n);
                begin = len;
                break;
            }
            begin = (size_t)(next - s) + 1;
        }
        const char *next = memchr(s + begin, mark, len - begin);
        end = next ? (size_t)(next - s) : len;
    }
    const char *part = array_part(s + begin, end - begin, index, count, level + 1, replacement);
    if (!replacement) return part;
    size_t bytes = strlen(part), kept = len - (end - begin);
    if (padding > SIZE_MAX - kept || bytes > SIZE_MAX - kept - padding)
        fail("dynamic array is too large");
    char *out = allocate(kept + padding + bytes);
    memcpy(out, s, begin);
    memset(out + begin, mark, padding);
    memcpy(out + begin + padding, part, bytes);
    memcpy(out + begin + padding + bytes, s + end, len - end);
    out[kept + padding + bytes] = '\0';
    return out;
}

const char *jbc_array(const char *s, const char **indices, int count, const char *replacement)
{
    int64_t index[3];
    for (int i = 0; i < count; ++i) {
        char *end;
        errno = 0;
        intmax_t n = strtoimax(indices[i], &end, 10);
        if (errno || end == indices[i] || *end || n > INT64_MAX || n < -1)
            fail("expected an integer dynamic-array index");
        if (replacement && n == 0) fail("dynamic-array indices start at one");
        index[i] = n;
    }
    return array_part(s, strlen(s), index, count, 0, replacement);
}

const char *jbc_read(const char *value, const char *name, const char *file, int line, int column)
{
    if (!value) {
        fprintf(stderr, "%s:%d:%d: unassigned variable '%s'\n", file, line, column, name);
        exit(EXIT_FAILURE);
    }
    return value;
}

static const char *size_value(size_t n)
{
    char *out = allocate(3 * sizeof(n));
    snprintf(out, 3 * sizeof(n) + 1, "%zu", n);
    return out;
}

const char *jbc_len(const char *s)
{
    return size_value(strlen(s));
}

const char *jbc_not(const char *s)
{
    return jbc_truth(s) ? "0" : "1";
}

static size_t occurrences(const char *s, const char *separator)
{
    size_t width = strlen(separator);
    if (!width) return strlen(s);
    size_t count = 0;
    while ((s = strstr(s, separator)) != NULL) {
        ++count;
        s += width;
    }
    return count;
}

const char *jbc_count(const char *s, const char *separator)
{
    return size_value(occurrences(s, separator));
}

const char *jbc_dcount(const char *s, const char *separator)
{
    if (!*s) return "0";
    if (!*separator) return jbc_len(s);
    return size_value(1 + occurrences(s, separator));
}

static int64_t field_index(const char *s, const char *file, int line, int column)
{
    if (!*s || strspn(s, "0123456789") != strlen(s))
        numeric_error(file, line, column, "FIELD requires positive integer positions and counts");
    int64_t n = integer(s, file, line, column);
    if (!n) numeric_error(file, line, column, "FIELD positions and counts start at one");
    return n;
}

const char *jbc_field(const char *s, const char *separator, const char *start,
                      const char *count, const char *file, int line, int column)
{
    int64_t first = field_index(start, file, line, column);
    int64_t length = field_index(count, file, line, column);
    size_t width = strlen(separator);
    if (!width) return first == 1 ? s : "";
    while (--first) {
        const char *next = strstr(s, separator);
        if (!next) return "";
        s = next + width;
    }
    const char *end = s;
    while (length--) {
        end = strstr(end, separator);
        if (!end) return s;
        if (length) end += width;
    }
    size_t bytes = (size_t)(end - s);
    char *field = allocate(bytes);
    memcpy(field, s, bytes);
    field[bytes] = '\0';
    return field;
}

/* Test files own their record bytes independently of expression temporaries.
   Each opened descriptor is the unique address of its file's name. */
struct memory_record {
    struct memory_record *next;
    char *key, *value;
};

struct memory_file {
    struct memory_file *next;
    struct memory_record *records;
    char name[];
};

static struct memory_file *files;

static void free_files(void)
{
    while (files) {
        struct memory_file *file = files;
        files = file->next;
        while (file->records) {
            struct memory_record *record = file->records;
            file->records = record->next;
            free(record->key);
            free(record->value);
            free(record);
        }
        free(file);
    }
}

static char *record_copy(const char *s)
{
    char *copy = malloc(strlen(s) + 1);
    if (!copy) fail("out of memory");
    return strcpy(copy, s);
}

void jbc_create_memory_file(const char *name)
{
    for (struct memory_file *f = files; f; f = f->next)
        if (strcmp(f->name, name) == 0) return;
    if (!files && atexit(free_files) != 0) fail("cannot register file cleanup");
    struct memory_file *f = calloc(1, sizeof *f + strlen(name) + 1);
    if (!f) fail("out of memory");
    strcpy(f->name, name);
    f->next = files;
    files = f;
}

int jbc_open_file(const char *name, const char **out)
{
    for (struct memory_file *f = files; f; f = f->next) {
        if (strcmp(f->name, name) == 0) {
            *out = f->name;
            return 1;
        }
    }
    *out = "";
    return 0;
}

static struct memory_file *file_for(const char *handle)
{
    for (struct memory_file *f = files; f; f = f->next)
        if (f->name == handle) return f;
    return NULL;
}

static struct memory_record *find_record(struct memory_file *f, const char *key)
{
    for (struct memory_record *r = f->records; r; r = r->next)
        if (strcmp(r->key, key) == 0) return r;
    return NULL;
}

int jbc_read_record(const char *handle, const char *key, const char **out)
{
    struct memory_file *f = file_for(handle);
    struct memory_record *r = f ? find_record(f, key) : NULL;
    if (!r) {
        *out = "";
        return 0;
    }
    *out = strcpy(allocate(strlen(r->value)), r->value);
    return 1;
}

int jbc_write_record(const char *handle, const char *key, const char *value)
{
    struct memory_file *f = file_for(handle);
    if (!f) return 0;
    struct memory_record *r = find_record(f, key);
    if (!r) {
        r = calloc(1, sizeof *r);
        if (!r) fail("out of memory");
        r->key = record_copy(key);
        r->next = f->records;
        f->records = r;
    }
    free(r->value);
    r->value = record_copy(value);
    return 1;
}
