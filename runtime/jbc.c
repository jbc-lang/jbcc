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
} jbc_variable;

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

struct jbc_slots *jbc_common_matrix(const char *key, int rank, const int *bounds,
                                    const char *file, int line, int column)
{
    size_t count = 1;
    for (int i = 0; i < rank; ++i) {
        size_t extent = (size_t)bounds[i] + 1;
        if (count > INT32_MAX / extent)
            numeric_error(file, line, column, "dimensioned array is too large");
        count *= extent;
    }
    struct jbc_slots *s = storage(count, key);
    size_t bytes = (size_t)rank * sizeof *bounds;
    if (!s->bounds) {
        s->bounds = malloc(bytes);
        if (!s->bounds) fail("out of memory");
        memcpy(s->bounds, bounds, bytes);
        s->rank = rank;
    } else if (s->rank != rank || memcmp(s->bounds, bounds, bytes)) {
        numeric_error(file, line, column, "incompatible COMMON matrix dimensions");
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
        const char *value = "";
        if (field) {
            const char *next = *delimiter ? strchr(field, (unsigned char)*delimiter) : NULL;
            size_t bytes = next ? (size_t)(next - field) : strlen(field);
            char *copy = allocate(bytes);
            memcpy(copy, field, bytes);
            copy[bytes] = '\0';
            value = copy;
            field = next ? next + 1 : NULL;
            ++assigned;
        }
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

static struct memory_record *find_record(struct memory_file *f, const char *key)
{
    for (struct memory_record *r = f->records; r; r = r->next)
        if (strcmp(r->key, key) == 0) return r;
    return NULL;
}

int jbc_read_record(const char *handle, const char *key, jbc_variable *out)
{
    struct memory_file *f = file_for(handle);
    struct memory_record *r = f ? find_record(f, key) : NULL;
    if (!r) {
        assign_value(out, "");
        return 0;
    }
    assign_value(out, strcpy(allocate(strlen(r->value)), r->value));
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

void jbc_exit(const char *value, const char *file, int line, int column)
{
    int64_t status = truncated(value, file, line, column);
    if (status < INT_MIN || status > INT_MAX)
        numeric_error(file, line, column, "EXIT status out of range");
    exit((int)status);
}

void jbc_ins(jbc_variable *slot, const char *value, const char **indices, int count,
             const char *file, int line, int column)
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
    const char *text = slot->value ? slot->value : "";
    assign_value(slot, array_part(text, strlen(text), index, count, 0, value, 1));
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
