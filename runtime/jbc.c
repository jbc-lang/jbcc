/* jbcc runtime for straight-line programs. Values are immutable strings. */
#include <errno.h>
#include <float.h>
#include <limits.h>
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

static void free_storages(void);

void jbc_finish(void)
{
    free_storages();
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

/* -1 preserves jbcc's default formatting until a PRECISION statement runs. */
static int jbc_precision = -1;

static void limit_places(struct decimal *n, int precision)
{
    if (precision < 0 || n->places <= (size_t)precision) return;
    n->places = (size_t)precision;
    while (n->places && n->fraction[n->places - 1] == '0') --n->places;
    if (!n->places && !n->digits) n->sign = 0;
}

int jbc_truth(const char *value)
{
    struct decimal n;
    if (!parse_decimal(value, &n)) return *value != '\0';
    limit_places(&n, jbc_precision);
    return n.sign != 0;
}

int jbc_compare(const char *left, const char *right, int precision)
{
    struct decimal a, b;
    if (!parse_decimal(left, &a) || !parse_decimal(right, &b))
        return strcmp(left, right);
    limit_places(&a, precision);
    limit_places(&b, precision);
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

void jbc_set_precision(const char *value, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n) || n.sign < 0 || n.places)
        numeric_error(file, line, column, "PRECISION requires a nonnegative integer");
    int64_t places = integer(value, file, line, column);
    if (places > INT_MAX) numeric_error(file, line, column, "PRECISION out of range");
    jbc_precision = (int)places;
}

static int multiply_overflows(int64_t a, int64_t b)
{
    if (a > 0) return b > INT64_MAX / a || b < INT64_MIN / a;
    if (a < 0 && b < 0) return a < INT64_MAX / b;
    if (a < 0 && b > 0) return a < INT64_MIN / b;
    return 0;
}

static const char *format_decimal(long double result)
{
    int places = 15;
    if (jbc_precision >= 0) {
        /* Find a round-trippable decimal before dropping fractional digits.
           Formatting directly at the requested width would round 2/3 up. */
        char scientific[DECIMAL_DIG + 32];
        for (int digits = LDBL_DIG; digits <= DECIMAL_DIG; ++digits) {
            snprintf(scientific, sizeof scientific, "%.*Le", digits - 1, result);
            if (strtold(scientific, NULL) == result || digits == DECIMAL_DIG) {
                int exponent = atoi(strchr(scientific, 'e') + 1);
                places = digits - 1 - exponent;
                if (places < 0) places = 0;
                break;
            }
        }
    }
    int length = snprintf(NULL, 0, "%.*Lf", places, result);
    if (length < 0) fail("decimal formatting failed");
    char *out = allocate((size_t)length);
    snprintf(out, (size_t)length + 1, "%.*Lf", places, result);
    if (places == 0) return strcmp(out, "-0") == 0 ? "0" : out;
    if (jbc_precision >= 0 && places > jbc_precision) {
        length -= places - jbc_precision;
        out[length] = '\0';
    }
    while (out[length - 1] == '0') out[--length] = '\0';
    if (out[length - 1] == '.') out[--length] = '\0';
    return strcmp(out, "-0") == 0 ? "0" : out;
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
    return format_decimal(result);
}

int jbc_for_test(const char *value, const char *limit, const char *step,
                 const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n) || !parse_decimal(limit, &n) || !parse_decimal(step, &n))
        numeric_error(file, line, column, "FOR requires numeric bounds and step");
    int cmp = jbc_compare(value, limit, jbc_precision);
    return n.sign < 0 ? cmp >= 0 : cmp <= 0;
}

/* Live matrix and COMMON slots can hold values allocated inside a loop. */
struct jbc_slots {
    struct jbc_slots *next;
    const char *name;
    size_t count;
    const char *values[];
};

static struct jbc_slots *storages;

const char **jbc_storage(size_t count, const char *name)
{
    if (name) {
        for (struct jbc_slots *s = storages; s; s = s->next)
            if (s->name && strcmp(name, s->name) == 0) return s->values;
    }
    if (count > (SIZE_MAX - sizeof(struct jbc_slots)) / sizeof(char *))
        fail("storage too large");
    struct jbc_slots *s = calloc(1, sizeof *s + count * sizeof(char *));
    if (!s) fail("out of memory");
    s->count = count;
    s->name = name;
    s->next = storages;
    storages = s;
    return s->values;
}

void jbc_release(const char **slots)
{
    struct jbc_slots **link = &storages;
    while ((*link)->values != slots) link = &(*link)->next;
    struct jbc_slots *s = *link;
    *link = s->next;
    free(s);
}

static void free_storages(void)
{
    while (storages) jbc_release(storages->values);
}

static int held_in_storage(const char *value)
{
    for (struct jbc_slots *s = storages; s; s = s->next)
        for (size_t i = 0; i < s->count; ++i)
            if (s->values[i] == value) return 1;
    return 0;
}

void jbc_matrix_fill(const char **dest, size_t count, const char *value)
{
    for (size_t i = 0; i < count; ++i) dest[i] = value;
}

void jbc_matrix_copy(const char **dest, const char *const *src, size_t count,
                     const char *name, const char *file, int line, int column)
{
    for (size_t i = 0; i < count; ++i) {
        if (!src[i]) {
            fprintf(stderr, "%s:%d:%d: unassigned element in matrix '%s'\n",
                    file, line, column, name);
            exit(EXIT_FAILURE);
        }
    }
    memmove(dest, src, count * sizeof *dest);
}

size_t jbc_index(int rank, const int *bounds, const char **indices,
                 const char *file, int line, int column)
{
    size_t offset = 0;
    for (int i = 0; i < rank; ++i) {
        struct decimal n;
        if (!parse_decimal(indices[i], &n) || n.places || n.sign < 0 || n.digits > 10)
            numeric_error(file, line, column, "invalid matrix subscript");
        int64_t v = strtoll(indices[i], NULL, 10);
        if (v > bounds[i]) numeric_error(file, line, column, "matrix subscript out of bounds");
        offset = offset * ((size_t)bounds[i] + 1) + (size_t)v;
    }
    return offset;
}

/* Keep variable values and protect temporaries belonging to enclosing loops. */
void jbc_collect(struct jbc_buffer *mark, const char ***live)
{
    struct jbc_buffer **link = &buffers;
    while (*link != mark) {
        struct jbc_buffer *buffer = *link;
        const char ***slot = live;
        while (*slot && **slot != buffer->text) ++slot;
        if (*slot || held_in_storage(buffer->text)) {
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

const char *jbc_char(const char *value, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n) || n.sign < 0 || n.places || n.digits > 3)
        numeric_error(file, line, column, "CHAR requires an integer from 0 to 255");
    unsigned int code = 0;
    for (size_t i = 0; i < n.digits; ++i)
        code = code * 10 + (unsigned int)(n.whole[i] - '0');
    if (code > 255)
        numeric_error(file, line, column, "CHAR requires an integer from 0 to 255");
    if (code == 0)
        numeric_error(file, line, column, "CHAR(0) requires strings with embedded NUL support");
    char *out = allocate(1);
    ((unsigned char *)out)[0] = (unsigned char)code;
    out[1] = '\0';
    return out;
}

static int64_t truncated(const char *value, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n)) numeric_error(file, line, column, "expected a numeric value");
    if (!n.digits) return 0;
    return integer(value, file, line, column);
}

const char *jbc_int(const char *value, const char *file, int line, int column)
{
    int64_t n = truncated(value, file, line, column);
    char *out = allocate(20);
    snprintf(out, 21, "%" PRId64, n);
    return out;
}

const char *jbc_space(const char *value, const char *file, int line, int column)
{
    int64_t n = truncated(value, file, line, column);
    if (n <= 0) return "";
    if ((uint64_t)n >= SIZE_MAX) fail("SPACE result too large");
    char *out = allocate((size_t)n);
    memset(out, ' ', (size_t)n);
    out[n] = '\0';
    return out;
}

const char *jbc_substring(const char *text, const char *start, const char *length,
                          const char *file, int line, int column, const char *replacement)
{
    size_t n = strlen(text);
    int64_t i = truncated(start, file, line, column);
    int64_t count = truncated(length, file, line, column);
    size_t offset = 0;
    if (i > 0) offset = (uint64_t)(i - 1) > n ? n : (size_t)(i - 1);
    if (i < 0 && i >= -(int64_t)n) offset = n - (size_t)(-i);
    size_t take = count <= 0 ? 0 : (uint64_t)count > n - offset ? n - offset : (size_t)count;
    if (!replacement) {
        char *out = allocate(take);
        memcpy(out, text + offset, take);
        out[take] = '\0';
        return out;
    }
    size_t added = strlen(replacement);
    if (added > SIZE_MAX - (n - take)) fail("substring result too large");
    char *out = allocate(n - take + added);
    memcpy(out, text, offset);
    memcpy(out + offset, replacement, added);
    memcpy(out + offset + added, text + offset + take, n - offset - take + 1);
    return out;
}

#ifdef JBC_TRIG
static long double radians(const char *s, const char *file, int line, int column)
{
    struct decimal n;
    long double degrees = strtold(s, NULL);
    if (!parse_decimal(s, &n) || !isfinite(degrees))
        numeric_error(file, line, column, "expected an angle in degrees");
    return fmodl(degrees, 360.0L) * (3.14159265358979323846L / 180.0L);
}

const char *jbc_sin(const char *s, const char *file, int line, int column)
{
    return format_decimal(sinl(radians(s, file, line, column)));
}

const char *jbc_cos(const char *s, const char *file, int line, int column)
{
    return format_decimal(cosl(radians(s, file, line, column)));
}
#endif

#ifdef JBC_TERMINAL
#include <sys/ioctl.h>
#include <unistd.h>

const char *jbc_system(const char *code, const char *file, int line, int column)
{
    if (jbc_compare(code, "14", -1)) numeric_error(file, line, column, "only SYSTEM(14) is supported");
    int bytes = 0;
    fflush(stdout);
    int result;
    do {
        result = ioctl(STDIN_FILENO, FIONREAD, &bytes);
    } while (result < 0 && errno == EINTR);
    if (result < 0) {
        /* Devices such as /dev/null have no input queue to inspect. */
        if (errno == ENODEV || errno == ENOTTY || errno == EOPNOTSUPP)
            return "0";
        numeric_error(file, line, column, "cannot query pending input bytes");
    }
    return bytes > 0 ? size_value((size_t)bytes) : "0";
}

const char *jbc_cursor(const char *code, const char *file, int line, int column)
{
    if (jbc_compare(code, "-2", -1)) numeric_error(file, line, column, "only @(-2) is supported");
    return "\033[H";
}
#endif
