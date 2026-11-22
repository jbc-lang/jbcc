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
#include <time.h>

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

const char *jbc_num(const char *value)
{
    if (!*value || (!value[1] && strchr(".+-", *value))) return "1";
    struct decimal n;
    return parse_decimal(value, &n) ? "1" : "0";
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

const char *jbc_sum(const char *source, const char *file, int line, int column)
{
    /* The lowest mark present sets the reduction level for the entire array. */
    unsigned level = 254;
    for (const unsigned char *p = (const unsigned char *)source; *p; ++p)
        if (*p >= 252 && *p < level) level = *p;

    size_t capacity = strlen(source);
    char *item = strcpy(allocate(capacity), source);
    char *out = NULL;
    size_t used = 0;
    const char *total = "0";
    for (char *p = item; ; ++p) {
        unsigned char mark = (unsigned char)*p;
        if (mark && (mark < 252 || mark > 254)) continue;
        *p = '\0';
        struct decimal n;
        if (parse_decimal(item, &n))
            total = jbc_arithmetic('+', total, item, file, line, column);
        if (mark != level) {
            if (!mark && !out) return total;
            size_t bytes = strlen(total);
            if (bytes >= SIZE_MAX - used) fail("SUM result is too large");
            size_t required = used + bytes + 1;
            if (!out || required > capacity) {
                if (capacity < required)
                    capacity = required <= SIZE_MAX / 2 ? required * 2 : required;
                char *larger = allocate(capacity);
                if (used) memcpy(larger, out, used);
                out = larger;
            }
            memcpy(out + used, total, bytes);
            used += bytes;
            out[used++] = (char)mark;
            if (!mark) return out;
            total = "0";
        }
        item = p + 1;
    }
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

/* Cursor state belongs to the variable, including when passed by reference. */
typedef struct {
    const char *value;
    size_t remove_offset;
    int array_list;
} jbc_variable;

static jbc_variable select_lists[12];

typedef struct {
    jbc_variable *values;
    const int *bounds;
    int rank;
    size_t count;
} jbc_matrix;

static void assign_value(jbc_variable *slot, const char *value)
{
    slot->value = value;
    slot->remove_offset = 0;
    slot->array_list = 0;
}

/* Live matrix and COMMON slots can hold values allocated inside a loop. */
struct jbc_slots {
    struct jbc_slots *next;
    const char *name;
    size_t count;
    int rank;
    int *bounds;
    jbc_variable values[];
};

static struct jbc_slots *storages;

static struct jbc_slots *storage(size_t count, const char *name)
{
    if (name) {
        for (struct jbc_slots *s = storages; s; s = s->next)
            if (s->name && strcmp(name, s->name) == 0) return s;
    }
    if (count > (SIZE_MAX - sizeof(struct jbc_slots)) / sizeof(jbc_variable))
        fail("storage too large");
    struct jbc_slots *s = calloc(1, sizeof *s + count * sizeof(jbc_variable));
    if (!s) fail("out of memory");
    s->count = count;
    s->name = name;
    s->next = storages;
    storages = s;
    return s;
}

jbc_variable *jbc_storage(size_t count, const char *name)
{
    return storage(count, name)->values;
}

int jbc_dimension(const char *text, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(text, &n) || n.sign <= 0 || n.places || n.digits > 10)
        numeric_error(file, line, column, "expected a positive integer dimension");
    int64_t bound = integer(text, file, line, column);
    if (bound >= INT32_MAX) numeric_error(file, line, column, "dimensioned array is too large");
    return (int)bound;
}

struct jbc_slots *jbc_matrix_storage(struct jbc_slots *previous, const char *key,
                                     int rank, const int *bounds,
                                     const char *file, int line, int column)
{
    size_t count = 1;
    for (int i = 0; i < rank; ++i) {
        size_t extent = (size_t)bounds[i] + 1;
        if (count > INT32_MAX / extent)
            numeric_error(file, line, column, "dimensioned array is too large");
        count *= extent;
    }
    struct jbc_slots *s = previous ? previous : storage(count, key);
    size_t bytes = (size_t)rank * sizeof *bounds;
    if (!s->bounds) {
        s->bounds = malloc(bytes);
        if (!s->bounds) fail("out of memory");
        memcpy(s->bounds, bounds, bytes);
        s->rank = rank;
    } else if (s->rank != rank || memcmp(s->bounds, bounds, bytes)) {
        numeric_error(file, line, column, key ? "incompatible COMMON matrix dimensions"
                                              : "incompatible local matrix dimensions");
    }
    return s;
}

void jbc_release(jbc_variable *slots)
{
    struct jbc_slots **link = &storages;
    while ((*link)->values != slots) link = &(*link)->next;
    struct jbc_slots *s = *link;
    *link = s->next;
    free(s->bounds);
    free(s);
}

static void free_storages(void)
{
    while (storages) jbc_release(storages->values);
}

static int held_in_storage(const char *value)
{
    for (size_t i = 0; i < sizeof select_lists / sizeof select_lists[0]; ++i)
        if (select_lists[i].value == value) return 1;
    for (struct jbc_slots *s = storages; s; s = s->next)
        for (size_t i = 0; i < s->count; ++i)
            if (s->values[i].value == value) return 1;
    return 0;
}

void jbc_matrix_fill(jbc_variable *dest, size_t count, const char *value)
{
    for (size_t i = 0; i < count; ++i) assign_value(&dest[i], value);
}

void jbc_matrix_copy(jbc_variable *dest, const jbc_variable *src, size_t count,
                     const char *name, const char *file, int line, int column)
{
    for (size_t i = 0; i < count; ++i) {
        if (!src[i].value) {
            fprintf(stderr, "%s:%d:%d: unassigned element in matrix '%s'\n",
                    file, line, column, name);
            exit(EXIT_FAILURE);
        }
    }
    for (size_t i = 0; i < count; ++i) assign_value(&dest[i], src[i].value);
}

/* Convert a zero-based ordinal among the one-based elements to a storage
   offset. Each dimension also has a zero subscript in jbcc's storage. */
static size_t matrix_element_offset(size_t ordinal, int rank, const int *bounds)
{
    size_t offset = 0, stride = 1;
    for (int d = rank - 1; d >= 0; --d) {
        size_t bound = (size_t)bounds[d];
        offset += (ordinal % bound + 1) * stride;
        ordinal /= bound;
        stride *= bound + 1;
    }
    return offset;
}

static size_t matrix_elements(int rank, const int *bounds)
{
    size_t total = 1;
    for (int d = 0; d < rank; ++d) total *= (size_t)bounds[d];
    return total;
}

static size_t matrix_position(const char *value, size_t fallback, size_t total,
                              const char *statement, const char *file, int line, int column)
{
    if (!value) return fallback;
    struct decimal n;
    if (!parse_decimal(value, &n) || n.places) {
        fprintf(stderr, "%s:%d:%d: %s requires integer positions\n", file, line, column, statement);
        exit(EXIT_FAILURE);
    }
    int64_t pos = integer(value, file, line, column);
    if (pos == -1) return fallback;
    if (pos < 1 || (uint64_t)pos > total) {
        fprintf(stderr, "%s:%d:%d: %s position out of bounds\n", file, line, column, statement);
        exit(EXIT_FAILURE);
    }
    return (size_t)pos;
}

const char *jbc_matbuild(const jbc_variable *src, int rank, const int *bounds,
                         const char *start, const char *end, const char *delimiter,
                         const char *name, const char *file, int line, int column)
{
    size_t total = matrix_elements(rank, bounds);
    size_t first = matrix_position(start, 1, total, "MATBUILD", file, line, column);
    size_t last = matrix_position(end, total, total, "MATBUILD", file, line, column);
    if (first > last) return "";
    size_t length = *delimiter ? last - first : 0;
    for (size_t i = first; i <= last; ++i) {
        const char *value = src[matrix_element_offset(i - 1, rank, bounds)].value;
        if (!value) {
            fprintf(stderr, "%s:%d:%d: unassigned element %zu in matrix '%s'\n",
                    file, line, column, i, name);
            exit(EXIT_FAILURE);
        }
        size_t bytes = strlen(value);
        if (bytes > SIZE_MAX - length) fail("MATBUILD result is too large");
        length += bytes;
    }
    char *out = allocate(length);
    char *write = out;
    for (size_t i = first; i <= last; ++i) {
        if (i != first && *delimiter) *write++ = *delimiter;
        const char *value = src[matrix_element_offset(i - 1, rank, bounds)].value;
        size_t bytes = strlen(value);
        memcpy(write, value, bytes);
        write += bytes;
    }
    *write = '\0';
    return out;
}

size_t jbc_matrix_index(int rank, const int *bounds, const char **indices,
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

/* Keep live values and leave allocations made by calling bodies alone. */
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
                              int count, int level, const char *replacement, int inserting)
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
                if ((uintmax_t)(target - n) > SIZE_MAX) fail("dynamic array is too large");
                padding = (size_t)(target - n);
                begin = len;
                break;
            }
            begin = (size_t)(next - s) + 1;
        }
        const char *next = memchr(s + begin, mark, len - begin);
        end = next ? (size_t)(next - s) : len;
    }
    const char *part;
    if (inserting && level + 1 == count && len && target > 0 && !padding) {
        /* Keep the existing component (including an empty one) after the insertion. */
        part = jbc_concat(replacement, (const char[]){(char)mark, 0});
        end = begin;
    } else {
        part = array_part(s + begin, end - begin, index, count, level + 1, replacement, inserting);
    }
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
    return array_part(s, strlen(s), index, count, 0, replacement, 0);
}

const char *jbc_read(const char *value, const char *name, const char *file, int line, int column)
{
    if (!value) {
        fprintf(stderr, "%s:%d:%d: unassigned variable '%s'\n", file, line, column, name);
        exit(EXIT_FAILURE);
    }
    return value;
}

void jbc_del(jbc_variable *slot, const char **indices, int count, const char *name,
             const char *file, int line, int column)
{
    const char *text = jbc_read(slot->value, name, file, line, column);
    uintmax_t position[3];
    for (int i = 0; i < count; ++i) {
        struct decimal number;
        if (!parse_decimal(indices[i], &number))
            numeric_error(file, line, column, "DEL requires numeric indices");
        /* An oversized position lies beyond the end of any stored array. */
        position[i] = number.sign > 0 ? strtoumax(number.whole, NULL, 10) : 0;
    }

    size_t length = strlen(text);
    const char *begin = text, *end = text + length;
    for (int i = 0; i < count; ++i) {
        int mark = 254 - i;
        if (!position[i]) return;
        for (uintmax_t n = 1; n < position[i]; ++n) {
            const char *next = memchr(begin, mark, (size_t)(end - begin));
            if (!next) return;
            begin = next + 1;
        }
        const char *next = memchr(begin, mark, (size_t)(end - begin));
        if (next) end = next;
        if (i == count - 1) {
            /* Remove the following delimiter, or the preceding one at the end. */
            if (next) ++end;
            else if (position[i] > 1) --begin;
        }
    }
    char *out = allocate(length - (size_t)(end - begin));
    size_t prefix = (size_t)(begin - text);
    memcpy(out, text, prefix);
    memcpy(out + prefix, end, (size_t)(text + length - end) + 1);
    assign_value(slot, out);
}

static const char *size_value(size_t n)
{
    char *out = allocate(3 * sizeof(n));
    snprintf(out, 3 * sizeof(n) + 1, "%zu", n);
    return out;
}

static const char *take_field(const char **field, unsigned char delimiter)
{
    if (!*field) return "";
    const char *start = *field;
    const char *next = delimiter ? strchr(start, delimiter) : NULL;
    size_t bytes = next ? (size_t)(next - start) : strlen(start);
    char *copy = allocate(bytes);
    memcpy(copy, start, bytes);
    copy[bytes] = '\0';
    *field = next ? next + 1 : NULL;
    return copy;
}

void jbc_matparse(jbc_variable *dest, int rank, const int *bounds,
                  const char *start, const char *end, const char *source,
                  const char *delimiter, jbc_variable *setting,
                  const char *file, int line, int column)
{
    size_t total = matrix_elements(rank, bounds);
    size_t first = matrix_position(start, 1, total, "MATPARSE", file, line, column);
    size_t last = matrix_position(end, total, total, "MATPARSE", file, line, column);
    size_t assigned = 0;
    const char *field = *source ? source : NULL;
    for (size_t i = first; i <= last; ++i) {
        if (field) ++assigned;
        const char *value = take_field(&field, (unsigned char)*delimiter);
        assign_value(&dest[matrix_element_offset(i - 1, rank, bounds)], value);
    }
    if (first <= last) {
        /* The unparsed suffix can point inside a temporary collected after this statement. */
        assign_value(&dest[0], field && *field ? strcpy(allocate(strlen(field)), field) : "");
    }
    if (setting) assign_value(setting, size_value(assigned));
}

void jbc_remove(jbc_variable *out, jbc_variable *source, jbc_variable *setting,
                const char *name, const char *file, int line, int column)
{
    const char *text = jbc_read(source->value, name, file, line, column);
    const char *code = "0";
    if (source->remove_offset != SIZE_MAX) {
        const char *start = text + source->remove_offset;
        const char *end = start;
        while (*end && (unsigned char)*end < 249) ++end;
        size_t length = (size_t)(end - start);
        char *part = allocate(length);
        memcpy(part, start, length);
        part[length] = '\0';
        unsigned char mark = (unsigned char)*end;
        source->remove_offset = mark ? (size_t)(end - text) + 1 : SIZE_MAX;
        if (mark) code = size_value(256u - mark);
        assign_value(out, part);
    }
    assign_value(setting, code);
}

/* Compare as if the shorter item were padded on the left with spaces. */
static int compare_right(const char *a, const char *b)
{
    size_t na = strlen(a), nb = strlen(b);
    while (na != nb) {
        int cmp;
        if (na > nb) {
            cmp = (unsigned char)*a++ - ' ';
            --na;
        } else {
            cmp = ' ' - (unsigned char)*b++;
            --nb;
        }
        if (cmp) return cmp;
    }
    return strcmp(a, b);
}

static int contains_bytes(const char *element, size_t bytes, const char *needle, size_t length)
{
    if (length > bytes) return 0;
    for (size_t i = 0; i <= bytes - length; ++i)
        if (memcmp(element + i, needle, length) == 0) return 1;
    return 0;
}

int jbc_find(int substring, const char *needle, const char *source, const char *occurrence,
             jbc_variable *field, jbc_variable *value, jbc_variable *subvalue,
             const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(occurrence, &n) || n.places || n.sign <= 0)
        numeric_error(file, line, column, substring ? "FINDSTR occurrence must be a positive integer"
                                                    : "FIND occurrence must be a positive integer");
    int64_t remaining = integer(occurrence, file, line, column);
    size_t f = 1, v = 1, s = 1;
    size_t length = strlen(needle);
    for (;;) {
        size_t bytes = strcspn(source, "\376\375\374");
        int matched = substring ? contains_bytes(source, bytes, needle, length)
                                : bytes == length && memcmp(source, needle, bytes) == 0;
        if (matched && --remaining == 0) {
            assign_value(field, size_value(f));
            if (value) assign_value(value, size_value(v));
            if (subvalue) assign_value(subvalue, size_value(s));
            return 1;
        }
        switch ((unsigned char)source[bytes]) {
            case 254: ++f; v = 1; s = 1; break;
            case 253: ++v; s = 1; break;
            case 252: ++s; break;
            default: return 0;
        }
        source += bytes + 1;
    }
}

int jbc_locate(const char *needle, const char *source, int mark, const char *start,
               const char *order, jbc_variable *position, const char *file, int line, int column)
{
    if (*order && (strlen(order) != 2 || !strchr("AD", order[0]) || !strchr("LRN", order[1])))
        numeric_error(file, line, column, "unsupported LOCATE order");
    if (!*start || start[strspn(start, "0123456789")])
        numeric_error(file, line, column, "LOCATE start must be a positive integer");
    int64_t first = integer(start, file, line, column);
    if (first < 1) numeric_error(file, line, column, "LOCATE positions start at one");

    size_t index = 1;
    int found = 0;
    if (*source || !*needle) {
        char *item = strcpy(allocate(strlen(source)), source);
        for (;;) {
            char *next = strchr(item, mark);
            if (next) *next++ = '\0';
            if (index >= (uint64_t)first) {
                int cmp;
                if (*order && order[1] == 'N') cmp = jbc_compare(item, needle, -1);
                else if (*order && order[1] == 'R') cmp = compare_right(item, needle);
                else cmp = strcmp(item, needle);
                found = cmp == 0;
                if (found || (*order == 'A' && cmp > 0) || (*order == 'D' && cmp < 0)) break;
            }
            ++index;
            if (!next) break;
            item = next;
        }
    }
    assign_value(position, size_value(index));
    return found;
}

static int ascii_digit(unsigned char c)
{
    return c >= '0' && c <= '9';
}

static size_t read_decimal_count(const char **cursor, const char *end)
{
    size_t count = 0;
    while (*cursor < end && ascii_digit(**cursor)) {
        unsigned digit = (unsigned)(**cursor - '0');
        ++*cursor;
        count = count > (SIZE_MAX - digit) / 10 ? SIZE_MAX : 10 * count + digit;
    }
    return count;
}

/* Keep a spare leading digit for a carry when rounding, e.g. 9.995 -> 10.00. */
static const char *fmt_decimal(struct decimal n, size_t places)
{
    size_t whole = n.digits ? n.digits : 1;
    if (places > SIZE_MAX - 4 || whole > SIZE_MAX - places - 4) fail("FMT result too large");
    char *out = allocate(whole + places + 4);
    char *first = out + 2;
    first[-1] = '0';
    if (n.digits) memcpy(first, n.whole, whole);
    else first[0] = '0';
    char *end = first + whole;
    if (places) {
        *end++ = '.';
        size_t copied = n.places < places ? n.places : places;
        memcpy(end, n.fraction, copied);
        memset(end + copied, '0', places - copied);
        end += places;
    }
    *end = '\0';
    if (n.places > places && n.fraction[places] >= '5') {
        char *digit = end;
        do {
            --digit;
            if (*digit == '.') continue;
            if (*digit != '9') { ++*digit; break; }
            *digit = '0';
        } while (digit >= first);
        if (digit < first) first = digit;
    }
    if (n.sign < 0 && first[strspn(first, "0.")] != '\0') *--first = '-';
    /* The runtime's collector tracks buffers by their starting address. */
    memmove(out, first, (size_t)(end - first) + 1);
    return out;
}

const char *jbc_abs(const char *value, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n))
        numeric_error(file, line, column, "ABS requires a numeric value");
    limit_places(&n, jbc_precision);
    n.sign = 1;
    return fmt_decimal(n, n.places);
}

const char *jbc_negate(const char *value, const char *file, int line, int column)
{
    struct decimal n;
    if (strchr(value, '.') && parse_decimal(value, &n) &&
        (jbc_precision >= 0 || n.places <= 15)) {
        limit_places(&n, jbc_precision);
        n.sign = -n.sign;
        return fmt_decimal(n, n.places);
    }
    return jbc_arithmetic('-', "0", value, file, line, column);
}

const char *jbc_fmt(const char *text, const char *mask, const char *file, int line, int column)
{
    const char *p = mask;
    int wrap = ascii_digit(*p);
    char fill = ' ';
    size_t width = 0;
    if (wrap) {
        width = read_decimal_count(&p, mask + strlen(mask));
        if ((*p == '\'' || *p == '"') && p[1] && p[2] == *p) {
            fill = p[1];
            p += 3;
        }
    }
    if (*p != 'L' && *p != 'R') goto unsupported;
    char align = *p++;
    int precision = -1;
    if (ascii_digit(*p)) precision = *p++ - '0';
    if (!wrap && (*p == '%' || *p == '#' || *p == '*')) {
        fill = *p == '%' ? '0' : (*p == '#' ? ' ' : '*');
        ++p;
        if (!ascii_digit(*p)) goto unsupported;
        width = read_decimal_count(&p, mask + strlen(mask));
        if (!width) goto unsupported;
    }
    if (*p || (wrap && !width)) goto unsupported;
    if (width == SIZE_MAX) numeric_error(file, line, column, "FMT width too large");
    struct decimal n;
    if (precision >= 0 && parse_decimal(text, &n)) text = fmt_decimal(n, (size_t)precision);
    if (!*text || !width) return text;
    size_t length = strlen(text);
    size_t blocks = wrap ? 1 + (length - 1) / width : 1;
    if (width > (SIZE_MAX - (blocks - 1)) / blocks)
        numeric_error(file, line, column, "FMT result too large");
    char *out = allocate(blocks * width + (blocks - 1));
    char *write = out;
    if (!wrap && length > width && align == 'R') text += length - width;
    for (size_t i = 0; i < blocks; ++i) {
        size_t used = length < width ? length : width;
        memset(write, fill, width);
        memcpy(write + (align == 'R' ? width - used : 0), text, used);
        write += width;
        text += used;
        length -= used;
        if (i + 1 < blocks) *write++ = (char)251;
    }
    *write = '\0';
    return out;

unsupported:
    fprintf(stderr, "%s:%d:%d: unsupported FMT mask '%s'\n", file, line, column, mask);
    exit(EXIT_FAILURE);
}

static int pattern_byte(unsigned char c, char kind)
{
    int alpha = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
    switch (kind) {
    case 'A': return alpha;
    case 'N': return ascii_digit(c);
    case 'C': return alpha || ascii_digit(c);
    default:  return 1; /* X */
    }
}

/* reachable[i] means the preceding pattern matched exactly the first i bytes.
   Keep one row per pattern component so adjacent variable counts can share
   a run of input bytes without recursive backtracking. */
static int match_alternative(const char *text, size_t n, const char *p, const char *end,
                             char *reachable, char *next)
{
    memset(reachable, 0, n + 1);
    reachable[0] = 1;
    while (p < end) {
        const char *literal = p;
        size_t literal_length = 0;
        size_t low = 0, high = 0;
        char kind = 0;
        if (*p == '\'' || *p == '"') {
            char quote = *p++;
            literal = p;
            const char *close = memchr(p, quote, (size_t)(end - p));
            if (!close) return 0;
            p = close + 1;
            literal_length = (size_t)(close - literal);
        } else if (ascii_digit(*p)) {
            low = read_decimal_count(&p, end);
            high = low ? low : SIZE_MAX;
            if (end - p >= 2 && *p == '-' && ascii_digit(p[1])) {
                const char *after = p + 1;
                size_t upper = read_decimal_count(&after, end);
                if (after < end && strchr("ANCX", *after)) {
                    p = after;
                    high = upper;
                }
            }
            if (p < end && strchr("ANCX", *p)) kind = *p++;
            else literal_length = (size_t)(p - literal);
        } else {
            do { ++p; } while (p < end && !ascii_digit(*p) && *p != '\'' && *p != '"');
            literal_length = (size_t)(p - literal);
        }

        if (kind) {
            size_t run = 0, latest = 0;
            int have_start = 0;
            for (size_t i = 0; i <= n; ++i) {
                if (i && pattern_byte((unsigned char)text[i - 1], kind)) ++run;
                else { run = 0; have_start = 0; }
                if (run >= low && reachable[i - low]) {
                    latest = i - low;
                    have_start = 1;
                }
                next[i] = have_start && i - latest <= high;
            }
        } else {
            if (literal_length > n) return 0;
            for (size_t i = 0; i <= n; ++i)
                next[i] = i >= literal_length && reachable[i - literal_length] &&
                          memcmp(text + (i - literal_length), literal, literal_length) == 0;
        }
        char *swap = reachable;
        reachable = next;
        next = swap;
    }
    return reachable[n];
}

const char *jbc_matches(const char *text, const char *pattern)
{
    size_t n = strlen(text);
    char *rows = calloc(n + 1, 2);
    if (!rows) fail("out of memory");
    int matched;
    do {
        const char *mark = strchr(pattern, 253);
        const char *end = mark ? mark : pattern + strlen(pattern);
        matched = match_alternative(text, n, pattern, end, rows, rows + n + 1);
        if (!mark) break;
        pattern = mark + 1;
    } while (!matched);
    free(rows);
    return matched ? "1" : "0";
}

static int leap_year(int year)
{
    return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
}

/* Zero-based Gregorian ordinal of the jBC epoch, 1967-12-31. */
enum { JBC_DATE_EPOCH = 718430 };

static const struct tm *local_clock(const char *file, int line, int column, const char *error)
{
    time_t now = time(NULL);
    const struct tm *today = now == (time_t)-1 ? NULL : localtime(&now);
    if (!today) numeric_error(file, line, column, error);
    return today;
}

const char *jbc_time(const char *file, int line, int column)
{
    const struct tm *now = local_clock(file, line, column, "TIME cannot read local time");
    return size_value(now->tm_hour * 3600 + now->tm_min * 60 + now->tm_sec);
}

static int month_length(int year, int month)
{
    static const int lengths[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    return lengths[month - 1] + (month == 2 && leap_year(year));
}

static const char *internal_date(int year, int day_of_year)
{
    int years = year - 1;
    int days = years * 365 + years / 4 - years / 100 + years / 400
             + day_of_year - 1 - JBC_DATE_EPOCH;
    char *out = allocate(11);
    snprintf(out, 12, "%d", days);
    return out;
}

const char *jbc_date(const char *file, int line, int column)
{
    const struct tm *today = local_clock(file, line, column, "DATE cannot read local date");
    if (today->tm_year < 1 - 1900 || today->tm_year > 9999 - 1900)
        numeric_error(file, line, column, "DATE outside years 1 through 9999");
    return internal_date(today->tm_year + 1900, today->tm_yday + 1);
}

const char *jbc_iconv(const char *value, const char *mask, const char *file, int line, int column)
{
    if (strcmp(mask, "D") && strcmp(mask, "D4")) {
        fprintf(stderr, "%s:%d:%d: unsupported ICONV mask '%s'\n", file, line, column, mask);
        exit(EXIT_FAILURE);
    }
    if (strspn(value, "0123456789") != 8 || value[8])
        numeric_error(file, line, column, "ICONV date requires YYYYMMDD");
    int date = atoi(value);
    int year = date / 10000, month = date / 100 % 100, day = date % 100;
    if (year == 0 || month < 1 || month > 12 || day < 1 || day > month_length(year, month))
        numeric_error(file, line, column, "invalid ICONV calendar date");
    int day_of_year = day;
    for (int m = 1; m < month; ++m) day_of_year += month_length(year, m);
    return internal_date(year, day_of_year);
}

static const char *const month_names[] = {"JANUARY", "FEBRUARY", "MARCH", "APRIL",
    "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"};

const char *jbc_timedate(const char *file, int line, int column)
{
    const struct tm *now = local_clock(file, line, column, "TIMEDATE cannot read local time");
    if (now->tm_year < 1 - 1900 || now->tm_year > 9999 - 1900)
        numeric_error(file, line, column, "TIMEDATE outside years 1 through 9999");
    char *out = allocate(20);
    snprintf(out, 21, "%02d:%02d:%02d %02d %.3s %04d", now->tm_hour, now->tm_min,
             now->tm_sec, now->tm_mday, month_names[now->tm_mon], now->tm_year + 1900);
    return out;
}

const char *jbc_oconv(const char *value, const char *mask, const char *file, int line, int column)
{
    static const char *const weekdays[] = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY",
        "FRIDAY", "SATURDAY", "SUNDAY"};

    if (strncmp(mask, "MT", 2) == 0) {
        const char *suffix = mask + 2;
        int with_seconds = *suffix == 'S';
        if (with_seconds) ++suffix;
        if (*suffix && strcmp(suffix, ":") != 0) goto unsupported;
        struct decimal n;
        if (!parse_decimal(value, &n) || n.places || n.sign < 0 || n.digits > 5)
            numeric_error(file, line, column, "OCONV time requires whole seconds from 0 to 86399");
        int seconds = (int)integer(value, file, line, column);
        if (seconds > 86399)
            numeric_error(file, line, column, "OCONV time requires whole seconds from 0 to 86399");
        char *out = allocate(8);
        snprintf(out, 9, "%02d:%02d:%02d", seconds / 3600, seconds / 60 % 60, seconds % 60);
        if (!with_seconds) out[5] = '\0';
        return out;
    }

    if (*mask != 'D') goto unsupported;
    const char *p = mask + 1;
    char part = 0, separator = 0;
    int width = 4, european = 0, name = 0;
    if (*p && strchr("DMJQWY", *p)) part = *p++;
    if ((!part || part == 'Y') && *p >= '0' && *p <= '4') width = *p++ - '0';
    if ((part == 'M' || part == 'W') && *p == 'A') { name = 1; ++p; }
    if (!part && *p && strchr("/-.", *p)) {
        separator = *p++;
        if (*p == 'E') { european = 1; ++p; }
    }
    if (*p) goto unsupported;

    struct decimal n;
    if (!parse_decimal(value, &n) || n.places)
        numeric_error(file, line, column, "OCONV date requires an integer day count");
    int64_t days = integer(value, file, line, column);
    if (days < -JBC_DATE_EPOCH || days > 2933628)
        numeric_error(file, line, column, "OCONV date outside years 1 through 9999");
    int ordinal = (int)days + JBC_DATE_EPOCH;
    int weekday = ordinal % 7;
    int year = 1 + 400 * (ordinal / 146097);
    int remaining = ordinal % 146097;
    while (remaining >= 365 + leap_year(year)) {
        remaining -= 365 + leap_year(year);
        ++year;
    }
    int day_of_year = remaining + 1;
    int month = 0;
    for (; month < 11; ++month) {
        int length = month_length(year, month + 1);
        if (remaining < length) break;
        remaining -= length;
    }
    int day = remaining + 1;
    switch (part) {
        case 'D': return size_value(day);
        case 'M': return name ? month_names[month] : size_value(month + 1);
        case 'J': return size_value(day_of_year);
        case 'Q': return size_value(month / 3 + 1);
        case 'W': return name ? weekdays[weekday] : size_value(weekday + 1);
    }
    char full_year[5];
    snprintf(full_year, sizeof full_year, "%04d", year);
    const char *suffix = full_year + 4 - width;
    char *out = allocate(11);
    if (part == 'Y') strcpy(out, suffix);
    else if (separator)
        snprintf(out, 12, "%02d%c%02d%s%s", european ? day : month + 1, separator,
                 european ? month + 1 : day, width ? (char[]){separator, 0} : "", suffix);
    else
        snprintf(out, 12, "%02d %.3s%s%s", day, month_names[month], width ? " " : "", suffix);
    return out;

unsupported:
    fprintf(stderr, "%s:%d:%d: unsupported OCONV mask '%s'\n", file, line, column, mask);
    exit(EXIT_FAILURE);
}

const char *jbc_trim(const char *text, const char *character, const char *mode,
                     const char *file, int line, int column)
{
    if (!*mode || mode[1] || !strchr("LTBARFED", *mode))
        numeric_error(file, line, column, "unknown TRIM mode");
    const char *set = *character ? character : " ";
    if (strchr("FED", *mode)) set = " \t";
    else if (set[1]) numeric_error(file, line, column, "TRIM requires a single trim byte");

    char *out = allocate(strlen(text));
    char *write = out;
    while (*text) {
        size_t run = strspn(text, set);
        if (!run) {
            run = strcspn(text, set);
            memcpy(write, text, run);
            write += run;
        } else {
            int leading = write == out && strchr("LBFRD", *mode);
            int trailing = !text[run] && strchr("TBERD", *mode);
            if (!leading && !trailing && *mode != 'A') {
                size_t keep = (*mode == 'R' || *mode == 'D') ? 1 : run;
                memcpy(write, text, keep);
                write += keep;
            }
        }
        text += run;
    }
    *write = '\0';
    return out;
}

const char *jbc_convert(const char *text, const char *from, const char *to)
{
    if (!*from || !*text) return text;
    unsigned char map[256];
    for (size_t i = 0; i < sizeof map; ++i) map[i] = (unsigned char)i;
    size_t to_length = strlen(to);
    /* Install earlier entries last, so the first occurrence wins. */
    for (size_t i = strlen(from); i > 0; --i) {
        size_t pos = i - 1;
        map[(unsigned char)from[pos]] = pos < to_length ? (unsigned char)to[pos] : 0;
    }
    char *out = allocate(strlen(text));
    char *write = out;
    for (const unsigned char *read = (const unsigned char *)text; *read; ++read) {
        unsigned char mapped = map[*read];
        if (mapped) *write++ = (char)mapped;
    }
    *write = '\0';
    return out;
}

static const char *shift_delimiters(const char *text, int first, int last, int step)
{
    size_t length = strlen(text);
    char *out = allocate(length);
    for (size_t i = 0; i < length; ++i) {
        unsigned char byte = (unsigned char)text[i];
        out[i] = (byte >= first && byte <= last) ? (char)(byte + step) : text[i];
    }
    out[length] = '\0';
    return out;
}

const char *jbc_raise(const char *text)
{
    return shift_delimiters(text, 248, 254, 1);
}

const char *jbc_lower(const char *text)
{
    return shift_delimiters(text, 249, 255, -1);
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

static const char *change_substrings(const char *text, const char *search, const char *replacement,
                                     int64_t limit, int64_t first)
{
    if (!*search) return text;
    size_t width = strlen(search);
    const char *match = strstr(text, search);
    for (int64_t i = 1; match && i < first; ++i)
        match = strstr(match + width, search);
    if (!match) return text;

    size_t count = 1 + occurrences(match + width, search);
    if (limit > 0 && (uint64_t)limit < count) count = (size_t)limit;
    size_t bytes = strlen(replacement);
    size_t kept = strlen(text) - count * width;
    if (bytes > (SIZE_MAX - kept) / count) fail("CHANGE result is too large");
    char *out = allocate(kept + count * bytes);
    char *write = out;
    for (;;) {
        size_t prefix = (size_t)(match - text);
        memcpy(write, text, prefix);
        write += prefix;
        memcpy(write, replacement, bytes);
        write += bytes;
        text = match + width;
        if (!--count) break;
        match = strstr(text, search);
    }
    strcpy(write, text);
    return out;
}

const char *jbc_change(const char *text, const char *search, const char *replacement,
                       const char *limit, const char *first, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(limit, &n) || n.places || !parse_decimal(first, &n) || n.places)
        numeric_error(file, line, column, "CHANGE requires integer occurrence arguments");
    return change_substrings(text, search, replacement, integer(limit, file, line, column),
                             integer(first, file, line, column));
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

/* Each selected range fits inside its input, including separators between
   selected fields. A missing occurrence selects an empty range. */
static const char *field_range(const char *s, const char *separator, size_t width,
                               int64_t first, int64_t count, size_t *bytes)
{
    while (first > 1) {
        const char *next = width ? strstr(s, separator) : NULL;
        if (!next) {
            *bytes = 0;
            return "";
        }
        s = next + width;
        --first;
    }
    const char *end = s;
    while (width && count--) {
        const char *next = strstr(end, separator);
        if (!next) break;
        end = next;
        if (!count) {
            *bytes = (size_t)(end - s);
            return s;
        }
        end += width;
    }
    *bytes = (size_t)(end - s) + strlen(end);
    return s;
}

const char *jbc_field(const char *s, const char *separator, const char *start,
                      const char *count, const char *file, int line, int column)
{
    int64_t first = field_index(start, file, line, column);
    int64_t length = field_index(count, file, line, column);
    size_t bytes;
    const char *selected = field_range(s, separator, strlen(separator), first, length, &bytes);
    if (!bytes) return "";
    if (selected == s && !s[bytes]) return s;
    char *field = allocate(bytes);
    memcpy(field, selected, bytes);
    field[bytes] = '\0';
    return field;
}

const char *jbc_fields(const char *source, const char *separator, const char *start,
                       const char *count, const char *file, int line, int column)
{
    int64_t first = field_index(start, file, line, column);
    int64_t length = field_index(count, file, line, column);
    size_t width = strlen(separator);
    char *out = strcpy(allocate(strlen(source)), source);
    char *write = out, *item = out;
    for (;;) {
        char *end = item + strcspn(item, "\376\375\374");
        char mark = *end;
        *end = '\0';
        size_t bytes;
        const char *selected = field_range(item, separator, width, first, length, &bytes);
        memmove(write, selected, bytes);
        write += bytes;
        *write++ = mark;
        if (!mark) return out;
        item = end + 1;
    }
}

/* Test files own their record bytes independently of expression temporaries.
   Each opened descriptor is the unique address of its file's name. */
struct memory_record {
    struct memory_record *next;
    size_t serial;
    char *key, *value;
};

struct memory_file {
    struct memory_file *next;
    struct memory_record *records, *last_read;
    size_t serial;
    char list_token;
    char name[];
};

static struct memory_file *files;
jbc_variable jbc_default_file;

static void free_record(struct memory_record *record)
{
    free(record->key);
    free(record->value);
    free(record);
}

static void clear_records(struct memory_file *file)
{
    file->last_read = NULL;
    while (file->records) {
        struct memory_record *record = file->records;
        file->records = record->next;
        free_record(record);
    }
}

static void free_files(void)
{
    while (files) {
        struct memory_file *file = files;
        files = file->next;
        clear_records(file);
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

int jbc_open_file(const char *name, jbc_variable *out)
{
    for (struct memory_file *f = files; f; f = f->next) {
        if (strcmp(f->name, name) == 0) {
            assign_value(out, f->name);
            return 1;
        }
    }
    assign_value(out, "");
    return 0;
}

static struct memory_file *file_for(const char *handle)
{
    for (struct memory_file *f = files; f; f = f->next)
        if (f->name == handle) return f;
    return NULL;
}

/* Each cursor stores its last record serial, so deletion cannot leave it
   pointing at freed storage. last_read speeds up sequential iteration. */

static jbc_variable *list_slot(jbc_variable *slot)
{
    if (slot->array_list) return slot;
    const char *s = slot->value;
    if (s && *s >= '0' && *s <= '9' && !s[1]) return &select_lists[*s - '0'];
    if (s && strcmp(s, "10") == 0) return &select_lists[10];
    return slot;
}

void jbc_clearselect(jbc_variable *slot, const char *file, int line, int column)
{
    /* CLEARSELECT also accepts list 11, unlike SELECT and READNEXT. */
    if (!slot->array_list && slot->value && strcmp(slot->value, "11") == 0) slot = &select_lists[11];
    else slot = list_slot(slot);
    if (!slot->array_list && slot->value && *slot->value)
        numeric_error(file, line, column, "CLEARSELECT requires a select list");
    assign_value(slot, "");
}

int jbc_select(const char *source, jbc_variable *list, jbc_variable *setting)
{
    int use_default = source == NULL;
    struct memory_file *f = file_for(use_default ? jbc_default_file.value : source);
    int success = f || !use_default;
    list = list_slot(list);
    assign_value(list, f ? &f->list_token : (use_default ? "" : source));
    if (!f && !use_default) {
        list->array_list = 1;
        if (!*source) list->remove_offset = SIZE_MAX;
    }
    if (setting) assign_value(setting, success ? "" : "128");
    return success;
}

int jbc_readnext(jbc_variable *list, jbc_variable *key, jbc_variable *mv, jbc_variable *setting,
                 const char *file, int line, int column)
{
    list = list_slot(list);
    if (list->array_list) {
        int found = list->remove_offset != SIZE_MAX;
        const char *value = "";
        if (found) {
            const char *field = list->value + list->remove_offset;
            value = take_field(&field, 254);
            list->remove_offset = field ? (size_t)(field - list->value) : SIZE_MAX;
        }
        assign_value(key, value);
        if (mv) assign_value(mv, found ? "0" : "");
        if (setting) assign_value(setting, "");
        return found;
    }
    struct memory_file *f = files;
    while (f && &f->list_token != list->value) f = f->next;
    if (!f && list->value && *list->value)
        numeric_error(file, line, column, "READNEXT requires a select list");
    struct memory_record *r = NULL;
    if (f && list->remove_offset != SIZE_MAX) {
        r = f->last_read && f->last_read->serial == list->remove_offset
            ? f->last_read->next : f->records;
        while (r && r->serial <= list->remove_offset) r = r->next;
        list->remove_offset = r ? r->serial : SIZE_MAX;
        f->last_read = r;
    }
    assign_value(key, r ? strcpy(allocate(strlen(r->key)), r->key) : "");
    if (mv) assign_value(mv, r ? "0" : "");
    if (setting) assign_value(setting, "");
    return r != NULL;
}

static struct memory_record **record_link(struct memory_file *f, const char *key)
{
    struct memory_record **link = &f->records;
    while (*link && strcmp((*link)->key, key) != 0) link = &(*link)->next;
    return link;
}

int jbc_clear_file(const char *handle, jbc_variable *setting)
{
    struct memory_file *file = file_for(handle);
    if (setting) assign_value(setting, file ? "" : "128");
    if (!file) return 0;
    clear_records(file);
    return 1;
}

int jbc_delete_record(const char *handle, const char *key, jbc_variable *setting)
{
    struct memory_file *f = file_for(handle);
    if (setting) assign_value(setting, f ? "0" : "128");
    if (!f) return 0;
    struct memory_record **link = record_link(f, key);
    if (*link) {
        struct memory_record *record = *link;
        *link = record->next;
        if (f->last_read == record) f->last_read = NULL;
        free_record(record);
    }
    return 1;
}

int jbc_read_record(const char *handle, const char *key, jbc_variable *out)
{
    struct memory_file *f = file_for(handle);
    struct memory_record *r = f ? *record_link(f, key) : NULL;
    if (!r) {
        assign_value(out, "");
        return 0;
    }
    assign_value(out, strcpy(allocate(strlen(r->value)), r->value));
    return 1;
}

int jbc_matread(const char *handle, const char *key, jbc_variable *dest, int rank,
                const int *bounds, size_t storage_count, jbc_variable *setting)
{
    struct memory_file *f = file_for(handle);
    struct memory_record *record = f ? *record_link(f, key) : NULL;
    if (!record) {
        if (setting) assign_value(setting, "128");
        return 128;
    }

    size_t total = matrix_elements(rank, bounds);
    const char *field = *record->value ? record->value : NULL;
    jbc_matrix_fill(dest, storage_count, "");
    for (size_t i = 0; i < total && field; ++i) {
        const char *value = take_field(&field, i + 1 == total ? 0 : 254);
        assign_value(&dest[matrix_element_offset(i, rank, bounds)], value);
    }
    if (setting) assign_value(setting, jbc_dcount(record->value, "\376"));
    return 0;
}

int jbc_read_field(const char *handle, const char *key, const char *field, jbc_variable *out,
                   jbc_variable *setting, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(field, &n))
        numeric_error(file, line, column, "READV requires a numeric field number");
    struct memory_file *f = file_for(handle);
    struct memory_record *record = f ? *record_link(f, key) : NULL;
    const char *value = "";
    if (record && n.sign == 0) value = key;
    if (record && n.sign > 0 && !n.places) {
        errno = 0;
        intmax_t index = strtoimax(field, NULL, 10);
        if (!errno && index <= INT64_MAX) {
            int64_t position = (int64_t)index;
            value = array_part(record->value, strlen(record->value), &position, 1, 0, NULL, 0);
        }
    }
    assign_value(out, value);
    if (setting) assign_value(setting, record ? "" : "128");
    return record ? 0 : 128;
}

int jbc_write_record(const char *handle, const char *key, const char *value)
{
    struct memory_file *f = file_for(handle);
    if (!f) return 0;
    struct memory_record **link = record_link(f, key);
    struct memory_record *r = *link;
    if (!r) {
        r = calloc(1, sizeof *r);
        if (!r) fail("out of memory");
        r->key = record_copy(key);
        if (f->serial == SIZE_MAX - 1) fail("file record counter overflow");
        r->serial = ++f->serial;
        *link = r;
    }
    free(r->value);
    r->value = record_copy(value);
    return 1;
}

int jbc_matwrite(const char *handle, const char *key, const jbc_variable *src, int rank,
                 const int *bounds, jbc_variable *setting, const char *name,
                 const char *file, int line, int column)
{
    const char *record = jbc_matbuild(src, rank, bounds, NULL, NULL, "\376", name, file, line, column);
    int written = jbc_write_record(handle, key, record);
    if (setting) assign_value(setting, written ? jbc_dcount(record, "\376") : "128");
    return written ? 0 : 128;
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

void jbc_exit(const char *value, const char *file, int line, int column)
{
    int64_t status = truncated(value, file, line, column);
    if (status < INT_MIN || status > INT_MAX)
        numeric_error(file, line, column, "EXIT status out of range");
    exit((int)status);
}

const char *jbc_update_array(const char *source, const char *value, const char **indices,
                             int count, int inserting, const char *file, int line, int column)
{
    int64_t index[3];
    int appended = 0;
    for (int i = 0; i < count; ++i) {
        index[i] = truncated(indices[i], file, line, column);
        if (index[i] < 0) {
            index[i] = appended ? 1 : -1;
            appended = 1;
        }
    }
    while (count > 1 && index[count - 1] == 0) --count;
    for (int i = 0; i < count; ++i) {
        if (!index[i]) index[i] = 1;
    }
    return array_part(source, strlen(source), index, count, 0, value, inserting);
}

void jbc_ins(jbc_variable *slot, const char *value, const char **indices, int count,
             const char *file, int line, int column)
{
    const char *source = slot->value ? slot->value : "";
    assign_value(slot, jbc_update_array(source, value, indices, count, 1, file, line, column));
}

const char *jbc_index(const char *text, const char *needle, const char *occurrence,
                      const char *file, int line, int column)
{
    int64_t remaining = truncated(occurrence, file, line, column);
    size_t width = strlen(needle);
    if (!width || remaining < 1) return "0";
    const char *cursor = text;
    while ((cursor = strstr(cursor, needle)) != NULL) {
        if (--remaining == 0) return size_value((size_t)(cursor - text) + 1);
        cursor += width;
    }
    return "0";
}

const char *jbc_int(const char *value, const char *file, int line, int column)
{
    int64_t n = truncated(value, file, line, column);
    char *out = allocate(20);
    snprintf(out, 21, "%" PRId64, n);
    return out;
}

const char *jbc_str(const char *text, const char *count, const char *file, int line, int column)
{
    int64_t repetitions = truncated(count, file, line, column);
    if (repetitions <= 0 || !*text) return "";
    if (repetitions == 1) return text;
    size_t width = strlen(text);
    if ((uint64_t)repetitions > (SIZE_MAX - sizeof(struct jbc_buffer) - 1) / width)
        numeric_error(file, line, column, "STR result too large");
    size_t bytes = width * (size_t)repetitions;
    char *out = allocate(bytes);
    for (size_t offset = 0; offset < bytes; offset += width)
        memcpy(out + offset, text, width);
    out[bytes] = '\0';
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
