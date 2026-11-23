#if defined(JBC_SEQUENTIAL) && defined(__APPLE__) && !defined(_DARWIN_C_SOURCE)
#define _DARWIN_C_SOURCE 1
#endif
#if (defined(JBC_SEQUENTIAL) || defined(JBC_SAVED_LISTS) || defined(JBC_REPORT) || defined(JBC_TERMINAL) || defined(JBC_HUSH) || defined(JBC_SLEEP) || defined(JBC_EXECUTE) || defined(JBC_PUTENV) || defined(JBC_SESSION)) && !defined(_POSIX_C_SOURCE)
#define _POSIX_C_SOURCE 200809L
#endif

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
static const char *jbc_command_line = "";
static int command_argc, next_argument = 1;
static char **command_argv;
static const char *jbc_input_prompt = "?";

struct input_chunk {
    struct input_chunk *next;
    size_t offset, length;
    unsigned char bytes[];
};

static struct input_chunk *input_data;
static struct input_chunk **input_data_tail = &input_data;

#ifdef JBC_CALLONEXIT
static void jbc_run_exit_callbacks(void);
#else
#define jbc_run_exit_callbacks() ((void)0)
#endif

#define jbc_terminate(status) do { jbc_run_exit_callbacks(); exit(status); } while (0)

static void fail(const char *message)
{
    fprintf(stderr, "jbcc runtime: %s\n", message);
    jbc_terminate(EXIT_FAILURE);
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
#ifdef JBC_REPORT
static void finish_reports(void);
#endif
#ifdef JBC_SEQUENTIAL
static int release_sequential(const char *token);
#endif

static void drop_input_chunk(void)
{
    struct input_chunk *chunk = input_data;
    input_data = chunk->next;
    if (!input_data) input_data_tail = &input_data;
    free(chunk);
}

void jbc_cleardata(void)
{
    while (input_data) drop_input_chunk();
}

void jbc_data(const char *text)
{
    size_t length = strlen(text);
    if (length >= SIZE_MAX - sizeof(struct input_chunk)) fail("DATA input is too large");
    struct input_chunk *chunk = malloc(sizeof *chunk + length + 1);
    if (!chunk) fail("out of memory");
    chunk->next = NULL;
    chunk->offset = 0;
    chunk->length = length + 1;
    for (size_t i = 0; i < length; ++i) {
        unsigned char c = (unsigned char)text[i];
        chunk->bytes[i] = c == 254 ? '\n' : c;
    }
    chunk->bytes[length] = '\n';
    *input_data_tail = chunk;
    input_data_tail = &chunk->next;
}

void jbc_finish(void)
{
    jbc_run_exit_callbacks();
#ifdef JBC_REPORT
    finish_reports();
#endif
    jbc_cleardata();
    free_storages();
    while (buffers) {
        struct jbc_buffer *next = buffers->next;
#ifdef JBC_SEQUENTIAL
        release_sequential(buffers->text);
#endif
        free(buffers);
        buffers = next;
    }
}

void jbc_init_arguments(int argc, char **argv)
{
    command_argc = argc;
    command_argv = argv;
    size_t length = argc ? (size_t)argc - 1 : 0;
    for (int i = 0; i < argc; ++i) {
        size_t bytes = strlen(argv[i]);
        if (bytes > SIZE_MAX - length) fail("command line is too large");
        length += bytes;
    }
    char *out = allocate(length), *write = out;
    for (int i = 0; i < argc; ++i) {
        if (i) *write++ = ' ';
        size_t bytes = strlen(argv[i]);
        memcpy(write, argv[i], bytes);
        write += bytes;
    }
    *write = '\0';
    jbc_command_line = out;
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

static int compare_decimals(struct decimal a, struct decimal b, int precision)
{
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

int jbc_compare(const char *left, const char *right, int precision)
{
    struct decimal a, b;
    if (!parse_decimal(left, &a) || !parse_decimal(right, &b))
        return strcmp(left, right);
    return compare_decimals(a, b, precision);
}

static void numeric_error(const char *file, int line, int column, const char *message)
{
    fprintf(stderr, "%s:%d:%d: %s\n", file, line, column, message);
    jbc_terminate(EXIT_FAILURE);
}

const char *jbc_get_argument(const char *position, const char *file, int line, int column)
{
    uintmax_t index = (uintmax_t)next_argument;
    if (position) {
        struct decimal n;
        if (!parse_decimal(position, &n) || n.places)
            numeric_error(file, line, column, "GET (ARG.) requires an integer index");
        if (n.sign < 0) return NULL;
        if (n.sign > 0) index = strtoumax(n.whole, NULL, 10);
    }
    if (index >= (uintmax_t)command_argc) return NULL;
    next_argument = (int)index + 1;
    return command_argv[index];
}

#ifdef JBC_HUSH
#include <fcntl.h>
#include <unistd.h>

static int jbc_hushed;

static void jbc_hush(const char *value, const char *file, int line, int column)
{
    static int saved_out, saved_err;
    int enabled = !jbc_hushed;
    if (value) {
        struct decimal n;
        if (!parse_decimal(value, &n))
            numeric_error(file, line, column, "HUSH requires a numeric operand");
        enabled = n.sign != 0;
    }
    if (enabled == jbc_hushed) return;
    if (fflush(stdout) || fflush(stderr))
        numeric_error(file, line, column, "cannot flush output for HUSH");
    if (enabled) {
        saved_out = fcntl(STDOUT_FILENO, F_DUPFD_CLOEXEC, 3);
        saved_err = fcntl(STDERR_FILENO, F_DUPFD_CLOEXEC, 3);
        int sink = open("/dev/null", O_WRONLY);
        if (saved_out < 0 || saved_err < 0 || sink < 0 ||
            dup2(sink, STDOUT_FILENO) < 0 || dup2(sink, STDERR_FILENO) < 0)
            numeric_error(file, line, column, "cannot suppress terminal output");
        close(sink);
    } else {
        if (dup2(saved_err, STDERR_FILENO) < 0 || dup2(saved_out, STDOUT_FILENO) < 0)
            numeric_error(file, line, column, "cannot restore terminal output");
        close(saved_err);
        close(saved_out);
    }
    jbc_hushed = enabled;
}
#else
#define jbc_hushed 0
#endif

static int64_t integer(const char *s, const char *file, int line, int column)
{
    errno = 0;
    intmax_t n = strtoimax(s, NULL, 10);
    if (errno || n > INT64_MAX || n < INT64_MIN)
        numeric_error(file, line, column, "integer operand out of range");
    return (int64_t)n;
}

int jbc_jump_index(const char *value, int count, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n) || n.places)
        numeric_error(file, line, column, "ON requires an integer selector");
    if (n.sign > 0) {
        errno = 0;
        uintmax_t index = strtoumax(value, NULL, 10);
        if (!errno && index <= (uintmax_t)count) return (int)index;
    }
#ifdef JBCC_ON_FALLTHROUGH
    return 0;
#else
    int position = n.sign > 0 ? count : 1;
    fprintf(stderr, "%s:%d:%d: warning: ON selector out of range, using label %d\n",
            file, line, column, position);
    return position;
#endif
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

enum precision_mode { TRUNCATE_RESULT, ROUND_RESULT };

static const char *format_decimal(long double result, enum precision_mode mode)
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
                if (mode == ROUND_RESULT && places > jbc_precision) places = jbc_precision;
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

static const char *arithmetic(char op, const char *left, const char *right,
                              int warn_on_zero_divisor, const char *file, int line, int column)
{
    struct decimal lhs, rhs;
    if (!parse_decimal(left, &lhs) || !parse_decimal(right, &rhs))
        numeric_error(file, line, column, "arithmetic requires numeric operands");
    if (op == '/' && rhs.sign == 0) {
        if (!warn_on_zero_divisor)
            numeric_error(file, line, column, "division by zero");
        fprintf(stderr, "%s:%d:%d: warning: DIVS: division by zero\n", file, line, column);
        return "0";
    }

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
    return format_decimal(result, TRUNCATE_RESULT);
}

const char *jbc_arithmetic(char op, const char *left, const char *right,
                           const char *file, int line, int column)
{
    return arithmetic(op, left, right, 0, file, line, column);
}

const char *jbc_div(const char *dividend, const char *divisor,
                    const char *file, int line, int column)
{
    if (!*dividend || !*divisor) return "";
    return jbc_arithmetic('/', dividend, divisor, file, line, column);
}

static const char *add_sum_item(const char *total, const char *item, struct decimal b,
                                const char *file, int line, int column);

/* Marks above the reduction level delimit independent totals. */
static const char *sum_elements(const char *source, unsigned level, const char *file, int line, int column)
{
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
            total = add_sum_item(total, item, n, file, line, column);
        if (!mark || mark > level) {
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

const char *jbc_sum(const char *source, const char *file, int line, int column)
{
    /* The lowest mark present sets the reduction level for the entire array. */
    unsigned level = 254;
    for (const unsigned char *p = (const unsigned char *)source; *p; ++p)
        if (*p >= 252 && *p < level) level = *p;

    return sum_elements(source, level, file, line, column);
}

const char *jbc_summation(const char *source, const char *file, int line, int column)
{
    return sum_elements(source, 254, file, line, column);
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
static jbc_variable jbc_record_id = {"", 0, 0};
static jbc_variable jbc_record = {"", 0, 0};

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

const char *jbc_getenv(const char *name, jbc_variable *out)
{
    const char *found = *name && !strchr(name, '=') ? getenv(name) : NULL;
    const char *value = found && *found ? strcpy(allocate(strlen(found)), found) : "";
    if (!out) return value;
    assign_value(out, value);
    return found ? "1" : "0";
}

#ifdef JBC_PUTENV
const char *jbc_putenv(const char *assignment)
{
    const char *equals = strchr(assignment, '=');
    if (!equals || equals == assignment) return "0";
    size_t length = (size_t)(equals - assignment);
    char *name = malloc(length + 1);
    if (!name) return "0";
    memcpy(name, assignment, length);
    name[length] = '\0';
    int status = setenv(name, equals + 1, 1);
    free(name);
    return status == 0 ? "1" : "0";
}
#endif

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
    if (jbc_record_id.value == value || jbc_record.value == value) return 1;
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

void jbc_matrix_copy(jbc_matrix dest, jbc_matrix src, const char *name,
                     const char *file, int line, int column)
{
    for (size_t i = 0; i < src.count; ++i) {
        if (!src.values[i].value) {
            fprintf(stderr, "%s:%d:%d: unassigned element in matrix '%s'\n",
                    file, line, column, name);
            jbc_terminate(EXIT_FAILURE);
        }
    }
    /* Identical shapes also have matching zero-subscript slots. Vector
       copies are contiguous even when their extents differ. */
    if (dest.rank == src.rank && (src.rank == 1 ||
        !memcmp(dest.bounds, src.bounds, src.rank * sizeof *src.bounds))) {
        size_t count = dest.count < src.count ? dest.count : src.count;
        for (size_t i = 0; i < count; ++i) assign_value(&dest.values[i], src.values[i].value);
        return;
    }

    assign_value(&dest.values[0], src.values[0].value);
    size_t count = matrix_elements(src.rank, src.bounds);
    size_t capacity = matrix_elements(dest.rank, dest.bounds);
    for (size_t i = 0; i < count && i < capacity; ++i) {
        size_t from = matrix_element_offset(i, src.rank, src.bounds);
        size_t to = matrix_element_offset(i, dest.rank, dest.bounds);
        assign_value(&dest.values[to], src.values[from].value);
    }
}

static size_t matrix_position(const char *value, size_t fallback, size_t total,
                              const char *statement, const char *file, int line, int column)
{
    if (!value) return fallback;
    struct decimal n;
    if (!parse_decimal(value, &n) || n.places) {
        fprintf(stderr, "%s:%d:%d: %s requires integer positions\n", file, line, column, statement);
        jbc_terminate(EXIT_FAILURE);
    }
    int64_t pos = integer(value, file, line, column);
    if (pos == -1) return fallback;
    if (pos < 1 || (uint64_t)pos > total) {
        fprintf(stderr, "%s:%d:%d: %s position out of bounds\n", file, line, column, statement);
        jbc_terminate(EXIT_FAILURE);
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
            jbc_terminate(EXIT_FAILURE);
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
        if (*slot || buffer->text == jbc_input_prompt ||
            held_in_storage(buffer->text)) {
            link = &buffer->next;
        } else {
            *link = buffer->next;
#ifdef JBC_SEQUENTIAL
            release_sequential(buffer->text);
#endif
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

const char *jbc_extract(const char *text, const char **indices, int count,
                        const char *file, int line, int column)
{
    int depth = 1;
    int64_t index[3];
    for (int i = 0; i < count; ++i) {
        struct decimal number;
        if (!parse_decimal(indices[i], &number))
            numeric_error(file, line, column, "EXTRACT requires numeric indices");
        if (number.sign) depth = i + 1;
        /* Oversized positions select a component past the end of the array. */
        uintmax_t position = number.sign > 0 ? strtoumax(number.whole, NULL, 10) : 0;
        index[i] = position > INT64_MAX ? INT64_MAX : (int64_t)position;
    }
    return array_part(text, strlen(text), index, depth, 0, NULL, 0);
}

const char *jbc_read(const char *value, const char *name, const char *file, int line, int column)
{
    if (!value) {
        fprintf(stderr, "%s:%d:%d: unassigned variable '%s'\n", file, line, column, name);
        jbc_terminate(EXIT_FAILURE);
    }
    return value;
}

static const char *delete_component(const char *text, const char **indices, int count,
                                    int omit_trailing_zeros, const char *file, int line, int column)
{
    int depth = omit_trailing_zeros ? 1 : count;
    uintmax_t position[3];
    for (int i = 0; i < count; ++i) {
        struct decimal number;
        if (!parse_decimal(indices[i], &number))
            numeric_error(file, line, column, omit_trailing_zeros ? "DELETE requires numeric indices"
                                                                  : "DEL requires numeric indices");
        if (omit_trailing_zeros && number.sign) depth = i + 1;
        /* An oversized position lies beyond the end of any stored array. */
        position[i] = number.sign > 0 ? strtoumax(number.whole, NULL, 10) : 0;
    }

    size_t length = strlen(text);
    const char *begin = text, *end = text + length;
    for (int i = 0; i < depth; ++i) {
        int mark = 254 - i;
        if (!position[i]) return text;
        for (uintmax_t n = 1; n < position[i]; ++n) {
            const char *next = memchr(begin, mark, (size_t)(end - begin));
            if (!next) return text;
            begin = next + 1;
        }
        const char *next = memchr(begin, mark, (size_t)(end - begin));
        if (next) end = next;
        if (i == depth - 1) {
            /* Remove the following delimiter, or the preceding one at the end. */
            if (next) ++end;
            else if (position[i] > 1) --begin;
        }
    }
    char *out = allocate(length - (size_t)(end - begin));
    size_t prefix = (size_t)(begin - text);
    memcpy(out, text, prefix);
    memcpy(out + prefix, end, (size_t)(text + length - end) + 1);
    return out;
}

const char *jbc_delete(const char *text, const char **indices, int count,
                       const char *file, int line, int column)
{
    return delete_component(text, indices, count, 1, file, line, column);
}

void jbc_del(jbc_variable *slot, const char **indices, int count, const char *name,
             const char *file, int line, int column)
{
    const char *text = jbc_read(slot->value, name, file, line, column);
    const char *result = delete_component(text, indices, count, 0, file, line, column);
    if (result != text) assign_value(slot, result);
}

static const char *size_value(uintmax_t n)
{
    char *out = allocate(3 * sizeof(n));
    snprintf(out, 3 * sizeof(n) + 1, "%" PRIuMAX, n);
    return out;
}

#ifdef JBC_CALLONEXIT
typedef void (*jbc_exit_callback)(jbc_variable *argument);
static jbc_exit_callback jbc_find_exit_callback(const char *name, size_t length);

struct exit_registration {
    struct exit_registration *next;
    jbc_exit_callback callback;
    char argument[];
};

static struct exit_registration *exit_callbacks;
static struct exit_registration **exit_callbacks_tail = &exit_callbacks;
static int running_exit_callbacks;

const char *jbc_callonexit(const char *request)
{
    if (running_exit_callbacks) return size_value(EBUSY);
    const char *mark = strchr(request, 253);
    size_t name_length = mark ? (size_t)(mark - request) : strlen(request);
    if (!name_length) return size_value(EINVAL);
    jbc_exit_callback callback = jbc_find_exit_callback(request, name_length);
    if (!callback) return size_value(ENOENT);
    for (struct exit_registration *entry = exit_callbacks; entry; entry = entry->next)
        if (entry->callback == callback) return "0";

    const char *argument = mark ? mark + 1 : "";
    size_t length = strlen(argument);
    if (length >= SIZE_MAX - sizeof(struct exit_registration)) return size_value(ENOMEM);
    struct exit_registration *entry = malloc(sizeof *entry + length + 1);
    if (!entry) return size_value(ENOMEM);
    entry->next = NULL;
    entry->callback = callback;
    memcpy(entry->argument, argument, length + 1);
    *exit_callbacks_tail = entry;
    exit_callbacks_tail = &entry->next;
    return "0";
}

static void jbc_run_exit_callbacks(void)
{
    if (running_exit_callbacks) return;
    running_exit_callbacks = 1;
    while (exit_callbacks) {
        struct exit_registration *entry = exit_callbacks;
        exit_callbacks = entry->next;
        jbc_exit_callback callback = entry->callback;
        /* The subroutine can retain this value in COMMON or a file. */
        const char *argument = strcpy(allocate(strlen(entry->argument)), entry->argument);
        free(entry);
        jbc_variable arg = {.value = argument};
        callback(&arg);
    }
    exit_callbacks_tail = &exit_callbacks;
}
#endif

#if defined(JBC_SESSION) || defined(JBC_SEQUENTIAL)
#include <unistd.h>

static const char *working_directory(void)
{
    size_t length = 256;
    for (;;) {
        char *cwd = allocate(length);
        if (getcwd(cwd, length)) return cwd;
        if (errno != ERANGE || length > SIZE_MAX / 2) return NULL;
        length *= 2;
    }
}
#endif

#ifdef JBC_SESSION
#include <pwd.h>

static uintmax_t port_number;
static int invalid_port_number;
static const char *login_override;
static const char *account_override;

static const char *session_environment(const char *name)
{
    const char *value = getenv(name);
    return value && *value ? strcpy(allocate(strlen(value)), value) : NULL;
}

void jbc_init_session(void)
{
    login_override = session_environment("JBCLOGNAME");
    account_override = login_override;
    if (!login_override) login_override = session_environment("JBASICLOGNAME");
    if (!account_override) account_override = session_environment("LOGNAME");

    const char *value = getenv("JBCPORTNO");
    if (!value || !*value) {
        port_number = (uintmax_t)getpid();
        return;
    }
    char *end;
    errno = 0;
    port_number = strtoumax(value, &end, 10);
    invalid_port_number = errno || *end || *value < '0' || *value > '9';
}

const char *jbc_port_number(const char *file, int line, int column)
{
    if (invalid_port_number)
        numeric_error(file, line, column, "JBCPORTNO requires a single nonnegative decimal port number");
    return size_value(port_number);
}

const char *jbc_login_name(void)
{
    if (login_override) return login_override;
    const struct passwd *user = getpwuid(getuid());
    if (!user || !user->pw_name) return "";
    return strcpy(allocate(strlen(user->pw_name)), user->pw_name);
}

const char *jbc_account_name(void)
{
    return account_override ? account_override : jbc_login_name();
}

const char *jbc_account_path(const char *file, int line, int column)
{
    const char *path = working_directory();
    if (!path) numeric_error(file, line, column, "cannot resolve @PATH");
    return path;
}

const char *jbc_process_id(void)
{
    return size_value((uintmax_t)getpid());
}

const char *jbc_terminal_type(void)
{
    const char *type = session_environment("TERM");
    return type ? type : "";
}

const char *jbc_terminal_name(void)
{
    const char *terminal = ttyname(STDIN_FILENO);
    return terminal ? strcpy(allocate(strlen(terminal)), terminal) : "phantom";
}
#endif

static size_t last_matrix_load;

const char *jbc_inmat(int rank, const int *bounds)
{
    if (!rank) return size_value(last_matrix_load);
    const size_t width = 3 * sizeof(int) + 1;
    char *out = allocate((size_t)rank * width), *write = out;
    for (int i = 0; i < rank; ++i) {
        if (i) *write++ = (char)253;
        write += snprintf(write, width, "%d", bounds[i]);
    }
    return out;
}

enum { JBC_LOCKED = -2 };

static int last_file_status;
static size_t blocked_record_locks;

void jbc_assign_system(const char *value, const char *key, const char *file, int line, int column)
{
    if (!jbc_compare(key, "1036", -1)) {
        if (jbc_compare(value, "0", -1))
            numeric_error(file, line, column, "SYSTEM(1036) can only be reset to zero");
        blocked_record_locks = 0;
        return;
    }
    if (!jbc_compare(key, "1039", -1))
        numeric_error(file, line, column, "ASSIGN TO SYSTEM(1039) requires a journaling backend");
    numeric_error(file, line, column, jbc_concat("unsupported ASSIGN TO SYSTEM key ", key));
}

static int file_result(int status)
{
    last_file_status = status;
    return status;
}

static int file_succeeded(int status)
{
    return file_result(status) == 0;
}

static const char *file_status_value(int status)
{
    return status == JBC_LOCKED ? "-2" : size_value((size_t)status);
}

const char *jbc_status(void)
{
    return file_status_value(last_file_status);
}

static int last_system_error;

static void tape_no_media(const char *channel, const char *statement,
                          const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(channel, &n) || n.places || n.sign < 0 || n.digits > 1)
        numeric_error(file, line, column,
                      jbc_concat(statement, " channel must be an integer from 0 to 9"));

    /* The runtime has no attached tape media. */
    last_system_error = 1;
}

int jbc_rewind(const char *channel, const char *file, int line, int column)
{
    tape_no_media(channel, "REWIND", file, line, column);
    return 0;
}

int jbc_readt(jbc_variable *out, const char *channel, const char *file, int line, int column)
{
    tape_no_media(channel, "READT", file, line, column);
    assign_value(out, "");
    return 0;
}

int jbc_writet(const char *record, const char *channel, const char *file, int line, int column)
{
    (void)record;
    tape_no_media(channel, "WRITET", file, line, column);
    return 0;
}

int jbc_weof(const char *channel, const char *file, int line, int column)
{
    tape_no_media(channel, "WEOF", file, line, column);
    return 0;
}

static int last_command_code;

const char *jbc_system_return_code(void)
{
    return size_value(last_command_code);
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
    last_matrix_load = field ? 0 : assigned;
    if (setting) assign_value(setting, size_value(assigned));
}

const char *jbc_remove(jbc_variable *out, jbc_variable *source, jbc_variable *setting,
                const char *name, const char *file, int line, int column)
{
    const char *text = jbc_read(source->value, name, file, line, column);
    const char *code = "0", *result = "";
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
        if (out) assign_value(out, part);
        result = part;
    }
    assign_value(setting, code);
    return result;
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

const char *jbc_compare_strings(const char *left, const char *right, const char *justification,
                                const char *file, int line, int column)
{
    int order;
    if (!strcmp(justification, "L")) order = strcmp(left, right);
    else if (!strcmp(justification, "R")) order = compare_right(left, right);
    else {
        numeric_error(file, line, column, "COMPARE justification must be L or R");
        return "";
    }
    if (order < 0) return "-1";
    return order > 0 ? "1" : "0";
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
static char *fmt_decimal(struct decimal n, size_t places)
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

const char *jbc_dround(const char *value, const char *precision,
                       const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n))
        numeric_error(file, line, column, "DROUND requires a numeric value");

    int64_t digits = jbc_precision < 0 ? 4 : jbc_precision;
    if (precision) {
        struct decimal requested;
        if (!parse_decimal(precision, &requested) || requested.sign < 0 || requested.places)
            numeric_error(file, line, column, "DROUND precision requires a nonnegative integer");
        digits = integer(precision, file, line, column);
    }
    size_t places = (uintmax_t)digits < n.places ? (size_t)digits : n.places;
    char *out = fmt_decimal(n, places);
    if (places) {
        char *end = out + strlen(out);
        while (end[-1] == '0') --end;
        if (end[-1] == '.') --end;
        *end = '\0';
    }
    return out;
}

/* Address a decimal digit in a common, zero-padded field. */
static int sum_digit(struct decimal n, size_t whole, size_t index)
{
    if (index < whole) {
        size_t pad = whole - n.digits;
        return index < pad ? 0 : n.whole[index - pad] - '0';
    }
    size_t place = index - whole;
    return place < n.places ? n.fraction[place] - '0' : 0;
}

static uintmax_t string_math_places(const char *precision, unsigned default_places,
                                    const char *diagnostic, const char *file, int line, int column)
{
    if (!precision) return default_places;
    struct decimal requested;
    if (!parse_decimal(precision, &requested) || requested.places)
        numeric_error(file, line, column, diagnostic);
    int64_t value = integer(precision, file, line, column);
    if (value < -1) numeric_error(file, line, column, diagnostic);
    return value < 0 ? default_places : (uintmax_t)value;
}

const char *jbc_smul(const char *left, const char *right, const char *precision,
                     const char *file, int line, int column)
{
    struct decimal a, b;
    if (!parse_decimal(left, &a) || !parse_decimal(right, &b))
        numeric_error(file, line, column, "SMUL requires numeric operands");

    uintmax_t places = string_math_places(precision, 16,
        "SMUL precision requires -1 or a nonnegative integer", file, line, column);
    if (!a.sign || !b.sign) return "0";

    size_t left_width = a.digits + a.places, right_width = b.digits + b.places;
    if (right_width > SIZE_MAX - left_width)
        numeric_error(file, line, column, "SMUL result is too large");
    size_t width = left_width + right_width;
    char *digits = allocate(width);
    memset(digits, '0', width);

    /* Multiply the unscaled digit strings, then restore the decimal point. */
    for (size_t i = left_width; i > 0; --i) {
        int carry = 0;
        int left_digit = sum_digit(a, a.digits, i - 1);
        for (size_t j = right_width; j > 0; --j) {
            size_t position = i + j - 1;
            int digit = digits[position] - '0'
                      + left_digit * sum_digit(b, b.digits, j - 1) + carry;
            digits[position] = (char)('0' + digit % 10);
            carry = digit / 10;
        }
        digits[i - 1] = (char)('0' + carry);
    }

    size_t whole = a.digits + b.digits;
    struct decimal result = {digits, digits + whole, whole, width - whole, a.sign * b.sign};
    while (result.digits && *result.whole == '0') {
        ++result.whole;
        --result.digits;
    }
    if (places < result.places) result.places = (size_t)places;
    while (result.places && result.fraction[result.places - 1] == '0') --result.places;
    return fmt_decimal(result, result.places);
}

static const char *add_sum_item(const char *total, const char *item, struct decimal b,
                                const char *file, int line, int column)
{
    if (!strchr(total, '.') && !strchr(item, '.'))
        return jbc_arithmetic('+', total, item, file, line, column);

    struct decimal a;
    parse_decimal(total, &a);
    int subtract = a.sign * b.sign < 0;
    int sign = a.sign ? a.sign : b.sign;
    if (subtract) {
        a.sign = b.sign = 1;
        if (compare_decimals(a, b, -1) < 0) {
            struct decimal swap = a;
            a = b;
            b = swap;
            sign = -sign;
        }
    }
    size_t whole = a.digits > b.digits ? a.digits : b.digits;
    size_t scale = a.places > b.places ? a.places : b.places;
    if (scale >= SIZE_MAX - whole) fail("SUM result is too large");
    char *digits = allocate(whole + scale + 1);
    int carry = 0;
    for (size_t i = whole + scale; i > 0; --i) {
        int x = sum_digit(a, whole, i - 1), y = sum_digit(b, whole, i - 1);
        int d = x + (subtract ? -y : y) + carry;
        carry = d < 0 ? -1 : d / 10;
        digits[i] = (char)('0' + d - 10 * carry);
    }
    digits[0] = (char)('0' + carry);
    struct decimal result = {digits, digits + whole + 1, whole + 1, scale, sign};
    while (result.digits && *result.whole == '0') {
        ++result.whole;
        --result.digits;
    }
    limit_places(&result, jbc_precision);
    while (result.places && result.fraction[result.places - 1] == '0') --result.places;
    if (jbc_precision < 0 && result.places > 15) {
        char *rounded = fmt_decimal(result, 15);
        char *end = rounded + strlen(rounded);
        while (end[-1] == '0') --end;
        if (end[-1] == '.') --end;
        *end = '\0';
        return rounded;
    }
    return fmt_decimal(result, result.places);
}

/* Decimal long division works on magnitudes with a common scale. Keep a
   leading zero for the borrow when subtracting a shifted divisor. */
static char *scaled_digits(struct decimal n, size_t scale)
{
    if (scale >= SIZE_MAX - n.digits) fail("decimal operand too large");
    size_t length = 1 + n.digits + scale;
    char *digits = allocate(length);
    digits[0] = '0';
    memcpy(digits + 1, n.whole, n.digits);
    memcpy(digits + 1 + n.digits, n.fraction, n.places);
    memset(digits + 1 + n.digits + n.places, '0', scale - n.places);
    digits[length] = '\0';
    return digits;
}

/* Divide one shifted window in place, with a leading digit for borrows. */
static char decimal_division_digit(char *start, const char *divisor, size_t width)
{
    char digit = '0';
    while (start[-1] != '0' || memcmp(start, divisor, width) >= 0) {
        int borrow = 0;
        for (size_t i = width; i > 0; --i) {
            int d = start[i - 1] - divisor[i - 1] - borrow;
            borrow = d < 0;
            start[i - 1] = (char)('0' + d + 10 * borrow);
        }
        start[-1] -= borrow;
        ++digit;
    }
    return digit;
}

const char *jbc_sdiv(const char *left, const char *right, const char *precision,
                     const char *file, int line, int column)
{
    struct decimal a, b;
    if (!parse_decimal(left, &a) || !parse_decimal(right, &b))
        numeric_error(file, line, column, "SDIV requires numeric operands");
    uintmax_t places = string_math_places(precision, 14,
        "SDIV precision requires -1 or a nonnegative integer", file, line, column);
    if (!b.sign) numeric_error(file, line, column, "SDIV division by zero");
    if (!a.sign) return "0";

    size_t scale = a.places > b.places ? a.places : b.places;
    char *digits = scaled_digits(a, scale);
    const char *divisor = scaled_digits(b, scale);
    divisor += strspn(divisor, "0");
    size_t width = strlen(divisor);
    size_t length = a.digits + scale;
    char *whole = allocate(length);
    memset(whole, '0', length);
    for (size_t end = width; end <= length; ++end) {
        char *start = digits + 1 + (end - width);
        whole[end - 1] = decimal_division_digit(start, divisor, width);
    }

    /* Feed zeros into the remainder to produce digits after the point. */
    char *remainder = allocate(width + 1);
    memset(remainder, '0', width + 1);
    remainder[width + 1] = '\0';
    size_t tail = length < width ? length : width;
    memcpy(remainder + 1 + (width - tail), digits + 1 + (length - tail), tail);

    char *fraction = NULL;
    size_t used = 0, capacity = 0;
    size_t limit = places < SIZE_MAX ? (size_t)places : SIZE_MAX;
    while (used < limit && strspn(remainder + 1, "0") < width) {
        if (used == capacity) {
            size_t increase = capacity ? capacity : 32;
            if (increase > limit - capacity) increase = limit - capacity;
            char *expanded = allocate(capacity + increase);
            if (used) memcpy(expanded, fraction, used);
            fraction = expanded;
            capacity += increase;
        }
        memmove(remainder, remainder + 1, width);
        remainder[width] = '0';
        fraction[used++] = decimal_division_digit(remainder + 1, divisor, width);
    }

    while (length && *whole == '0') { ++whole; --length; }
    while (used && fraction[used - 1] == '0') --used;
    struct decimal result = {whole, fraction, length, used, a.sign * b.sign};
    return fmt_decimal(result, used);
}

const char *jbc_rnd(const char *value, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n) || n.places)
        numeric_error(file, line, column, "RND requires an integer bound");
    if (!n.sign)
        numeric_error(file, line, column, "RND requires a nonzero bound");

    /* parse_decimal strips the sign and leading zeros from the digit span. */
    if (n.digits > 10)
        numeric_error(file, line, column, "RND bound exceeds 2147483647");
    uint64_t magnitude = strtoull(n.whole, NULL, 10);
    if (magnitude > INT32_MAX)
        numeric_error(file, line, column, "RND bound exceeds 2147483647");
    uint32_t bound = (uint32_t)magnitude;
    if (bound == 1) return "0";

    FILE *random = fopen("/dev/urandom", "rb");
    if (!random) numeric_error(file, line, column, "RND cannot open /dev/urandom");
    /* Discard the incomplete interval so each remainder is equally likely. */
    uint32_t threshold = (UINT64_C(1) << 32) % bound;
    uint32_t sample;
    do {
        if (fread(&sample, sizeof sample, 1, random) != 1) {
            fclose(random);
            numeric_error(file, line, column, "RND cannot read /dev/urandom");
        }
    } while (sample < threshold);
    fclose(random);
    return size_value(sample % bound);
}

const char *jbc_mod(const char *left, const char *right, const char *operand_error,
                    const char *file, int line, int column)
{
    struct decimal a, b;
    if (!parse_decimal(left, &a) || !parse_decimal(right, &b))
        numeric_error(file, line, column, operand_error);
    if (!b.sign) return left;
    if (!a.sign) return "0";

    size_t scale = a.places > b.places ? a.places : b.places;
    char *digits = scaled_digits(a, scale);
    const char *divisor = scaled_digits(b, scale);
    divisor += strspn(divisor, "0");
    size_t width = strlen(divisor);
    size_t length = a.digits + scale;
    for (size_t end = width; end <= length; ++end) {
        char *start = digits + 1 + (end - width);
        decimal_division_digit(start, divisor, width);
    }
    a.whole = digits + 1;
    a.fraction = a.whole + a.digits;
    a.places = scale;
    while (a.digits && *a.whole == '0') { ++a.whole; --a.digits; }
    while (a.places && a.fraction[a.places - 1] == '0') --a.places;
    limit_places(&a, jbc_precision);
    return fmt_decimal(a, a.places);
}

struct sort_element {
    const char *text;
    size_t length;
};

static int compare_sort_elements(const void *left, const void *right)
{
    const struct sort_element *a = left, *b = right;
    size_t common = a->length < b->length ? a->length : b->length;
    int order = memcmp(a->text, b->text, common);
    if (order) return order;
    return (a->length > b->length) - (a->length < b->length);
}

static const char *join_sorted_elements(struct sort_element *elements, size_t count, size_t length)
{
    qsort(elements, count, sizeof *elements, compare_sort_elements);
    char *out = allocate(length), *write = out;
    for (size_t i = 0; i < count; ++i) {
        if (i) *write++ = (char)254;
        memcpy(write, elements[i].text, elements[i].length);
        write += elements[i].length;
    }
    *write = '\0';
    return out;
}

const char *jbc_sort(const char *source)
{
    size_t count = 1;
    for (const char *p = source; *p; ++p)
        if ((unsigned char)*p >= 249) ++count;
    if (count == 1) return source;

    struct sort_element *elements = calloc(count, sizeof *elements);
    if (!elements) fail("out of memory");
    const char *start = source, *end = source;
    for (size_t i = 0; i < count; ++i) {
        while (*end && (unsigned char)*end < 249) ++end;
        elements[i] = (struct sort_element){start, (size_t)(end - start)};
        if (*end) start = ++end;
    }
    const char *out = join_sorted_elements(elements, count, (size_t)(end - source));
    free(elements);
    return out;
}

static const char *array_extreme(const char *source, int maximum)
{
    char *item = strcpy(allocate(strlen(source)), source);
    const char *selected = NULL;
    struct decimal best = {0};
    for (;;) {
        char *end = item + strcspn(item, "\376\375\374");
        char mark = *end;
        *end = '\0';
        const char *value = *item ? item : "0";
        struct decimal n;
        if (parse_decimal(value, &n)) {
            int cmp = selected ? compare_decimals(n, best, jbc_precision) : 0;
            if (!selected || (maximum ? cmp > 0 : cmp < 0)) {
                best = n;
                selected = value;
            }
        }
        if (!mark) break;
        item = end + 1;
    }
    if (!selected) return "0";
    /* The guide prints the original MAXIMUM on a precision tie, but a
       rounded MINIMUM when the selected element has excess places. */
    if (!maximum && jbc_precision >= 0 && best.places > (size_t)jbc_precision)
        return fmt_decimal(best, (size_t)jbc_precision);
    return strcpy(allocate(strlen(selected)), selected);
}

const char *jbc_maximum(const char *source)
{
    return array_extreme(source, 1);
}

const char *jbc_minimum(const char *source)
{
    return array_extreme(source, 0);
}

static const char *absolute_value(const char *value, const char *error,
                                  const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n))
        numeric_error(file, line, column, error);
    limit_places(&n, jbc_precision);
    n.sign = 1;
    return fmt_decimal(n, n.places);
}

const char *jbc_abs(const char *value, const char *file, int line, int column)
{
    return absolute_value(value, "ABS requires a numeric value", file, line, column);
}

static const char *negate_decimal(struct decimal n)
{
    limit_places(&n, jbc_precision);
    n.sign = -n.sign;
    return fmt_decimal(n, n.places);
}

static const char *negative_value(const char *value, const char *name,
                                  const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n)) {
        fprintf(stderr, "%s:%d:%d: warning: %s: Non-numeric value -- ZERO USED\n",
                file, line, column, name);
        return "0";
    }
    return negate_decimal(n);
}

const char *jbc_neg(const char *value, const char *file, int line, int column)
{
    return negative_value(value, "NEG", file, line, column);
}

const char *jbc_negate(const char *value, const char *file, int line, int column)
{
    struct decimal n;
    if (strchr(value, '.') && parse_decimal(value, &n) &&
        (jbc_precision >= 0 || n.places <= 15))
        return negate_decimal(n);
    return jbc_arithmetic('-', "0", value, file, line, column);
}

static const char *skip_wrap_spaces(const char *start, const char *end)
{
    while (start < end && *start == ' ') ++start;
    return start;
}

static size_t word_wrap_line(const char *start, const char *end, uintmax_t width,
                             const char **next)
{
    size_t remaining = (size_t)(end - start);
    size_t take = remaining < width ? remaining : (size_t)width;
    if (take < remaining && start[take] != ' ') {
        size_t split = take;
        while (split && start[split - 1] != ' ') --split;
        if (split) take = split;
    }
    *next = skip_wrap_spaces(start + take, end);
    while (take && start[take - 1] == ' ') --take;
    return take;
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
    if (*p != 'L' && *p != 'R' && !(wrap && *p == 'T')) goto unsupported;
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
    const char *end = text + length;
    size_t blocks = wrap ? 1 + (length - 1) / width : 1;
    if (align == 'T') {
        text = skip_wrap_spaces(text, end);
        blocks = 1;
        for (const char *start = text; start < end;) {
            word_wrap_line(start, end, width, &start);
            if (start < end) ++blocks;
        }
    }
    if (width > (SIZE_MAX - (blocks - 1)) / blocks)
        numeric_error(file, line, column, "FMT result too large");
    char *out = allocate(blocks * width + (blocks - 1));
    char *write = out;
    if (!wrap && length > width && align == 'R') text += length - width;
    for (size_t i = 0; i < blocks; ++i) {
        size_t remaining = (size_t)(end - text);
        size_t used = remaining < width ? remaining : width;
        const char *next = text + used;
        if (align == 'T') used = word_wrap_line(text, end, width, &next);
        memset(write, fill, width);
        memcpy(write + (align == 'R' ? width - used : 0), text, used);
        write += width;
        text = next;
        if (i + 1 < blocks) *write++ = (char)251;
    }
    *write = '\0';
    return out;

unsupported:
    fprintf(stderr, "%s:%d:%d: unsupported FMT mask '%s'\n", file, line, column, mask);
    jbc_terminate(EXIT_FAILURE);
}

static int ascii_alpha(unsigned char c)
{
    return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
}

const char *jbc_alpha(const char *text)
{
    if (!*text) return "0";
    for (; *text; ++text)
        if (!ascii_alpha((unsigned char)*text)) return "0";
    return "1";
}

static int pattern_byte(unsigned char c, char kind)
{
    switch (kind) {
    case 'A': return ascii_alpha(c);
    case 'N': return ascii_digit(c);
    case 'C': return ascii_alpha(c) || ascii_digit(c);
    default:  return 1; /* X */
    }
}

struct match_span {
    size_t start, length;
};

/* reachable[i] means the preceding pattern matched exactly the first i bytes.
   Keep one row per pattern component so adjacent variable counts can share
   a run of input bytes without recursive backtracking. */
static int match_alternative(const char *text, size_t n, const char *p, const char *end,
                             char *reachable, char *next, size_t field,
                             struct match_span *spans, struct match_span *result)
{
    size_t component = 0;
    struct match_span *next_spans = spans ? spans + n + 1 : NULL;
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

        ++component;
        if (!kind && literal_length > n) return 0;
        size_t run = 0, start = 0;
        int have_start = 0;
        for (size_t i = 0; i <= n; ++i) {
            if (kind) {
                if (i && pattern_byte((unsigned char)text[i - 1], kind)) ++run;
                else { run = 0; have_start = 0; }
                if (run >= low && reachable[i - low]) {
                    start = i - low;
                    have_start = 1;
                }
                next[i] = have_start && i - start <= high;
            } else {
                start = i >= literal_length ? i - literal_length : 0;
                next[i] = i >= literal_length && reachable[start] &&
                          memcmp(text + start, literal, literal_length) == 0;
            }
            if (field && component >= field && next[i]) {
                next_spans[i] = component == field ? (struct match_span){start, i - start} : spans[start];
            }
        }
        struct match_span *previous_spans = spans;
        spans = next_spans;
        next_spans = previous_spans;
        char *swap = reachable;
        reachable = next;
        next = swap;
    }
    if (reachable[n] && field && field <= component) *result = spans[n];
    return reachable[n];
}

static const char *match_pattern(const char *text, const char *pattern, size_t field)
{
    size_t n = strlen(text);
    char *rows = calloc(n + 1, 2);
    struct match_span *spans = field ? calloc(n + 1, 2 * sizeof *spans) : NULL;
    if (!rows || (field && !spans)) fail("out of memory");
    struct match_span result = {0, 0};
    int matched;
    do {
        const char *mark = strchr(pattern, 253);
        const char *end = mark ? mark : pattern + strlen(pattern);
        matched = match_alternative(text, n, pattern, end, rows, rows + n + 1, field, spans, &result);
        if (!mark) break;
        pattern = mark + 1;
    } while (!matched);
    free(rows);
    free(spans);
    if (!field) return matched ? "1" : "0";
    if (!result.length) return "";
    char *value = allocate(result.length);
    memcpy(value, text + result.start, result.length);
    value[result.length] = '\0';
    return value;
}

const char *jbc_matches(const char *text, const char *pattern)
{
    return match_pattern(text, pattern, 0);
}

const char *jbc_matchfield(const char *text, const char *pattern, const char *field,
                           const char *file, int line, int column)
{
    struct decimal index;
    if (!parse_decimal(field, &index) || index.places)
        numeric_error(file, line, column, "MATCHFIELD requires an integer field number");
    if (index.sign <= 0 || !*text || !*pattern) return "";
    errno = 0;
    uintmax_t position = strtoumax(field, NULL, 10);
    if (errno || position > SIZE_MAX) return "";
    return match_pattern(text, pattern, (size_t)position);
}

static int leap_year(int year)
{
    return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
}

/* Zero-based Gregorian ordinal of the jBC epoch, 1967-12-31. */
enum { JBC_DATE_EPOCH = 718430 };

static const struct tm *read_local_clock(void)
{
    time_t now = time(NULL);
    return now == (time_t)-1 ? NULL : localtime(&now);
}

static const struct tm *local_clock(const char *file, int line, int column, const char *error)
{
    const struct tm *today = read_local_clock();
    if (!today) numeric_error(file, line, column, error);
    return today;
}

static const char *time_from_clock(const struct tm *now)
{
    return size_value(now->tm_hour * 3600 + now->tm_min * 60 + now->tm_sec);
}

const char *jbc_time(const char *file, int line, int column)
{
    return time_from_clock(local_clock(file, line, column, "TIME cannot read local time"));
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

static const char *date_from_clock(const struct tm *today, const char *file, int line, int column)
{
    if (!today) numeric_error(file, line, column, "DATE cannot read local date");
    if (today->tm_year < 1 - 1900 || today->tm_year > 9999 - 1900)
        numeric_error(file, line, column, "DATE outside years 1 through 9999");
    return internal_date(today->tm_year + 1900, today->tm_yday + 1);
}

const char *jbc_date(const char *file, int line, int column)
{
    return date_from_clock(read_local_clock(), file, line, column);
}

static struct tm startup_clock;
static int have_startup_clock;

void jbc_init_startup_clock(void)
{
    const struct tm *snapshot = read_local_clock();
    if (snapshot) {
        startup_clock = *snapshot;
        have_startup_clock = 1;
    }
}

const char *jbc_startup_date(const char *file, int line, int column)
{
    return date_from_clock(have_startup_clock ? &startup_clock : NULL, file, line, column);
}

const char *jbc_startup_time(const char *file, int line, int column)
{
    if (!have_startup_clock) numeric_error(file, line, column, "@TIME cannot read startup clock");
    return time_from_clock(&startup_clock);
}

enum input_conversion { ICONV_UNSUPPORTED, ICONV_DATE, ICONV_TIME };

static enum input_conversion input_mask(const char *mask)
{
    if (!strcmp(mask, "D") || !strcmp(mask, "D4")) return ICONV_DATE;
    if (!strcmp(mask, "MT") || !strcmp(mask, "MTS")) return ICONV_TIME;
    return ICONV_UNSUPPORTED;
}

static const char *input_date(const char *value, const char **error)
{
    if (strspn(value, "0123456789") != 8 || value[8]) {
        *error = "ICONV date requires YYYYMMDD";
        return NULL;
    }
    int date = atoi(value);
    int year = date / 10000, month = date / 100 % 100, day = date % 100;
    if (year == 0 || month < 1 || month > 12 || day < 1 || day > month_length(year, month)) {
        *error = "invalid ICONV calendar date";
        return NULL;
    }
    int day_of_year = day;
    for (int m = 1; m < month; ++m) day_of_year += month_length(year, m);
    return internal_date(year, day_of_year);
}

static const char *input_time(const char *value, const char **error)
{
    const char *p = value;
    size_t width = strspn(p, "0123456789");
    if (!width || width > 2 || p[width] != ':') goto invalid;
    size_t hour = read_decimal_count(&p, p + width);
    size_t minute, second = 0;
    ++p;
    width = strspn(p, "0123456789");
    if (width != 2) goto invalid;
    minute = read_decimal_count(&p, p + width);
    if (*p == ':') {
        ++p;
        width = strspn(p, "0123456789");
        if (width != 2) goto invalid;
        second = read_decimal_count(&p, p + width);
    }
    while (*p == ' ') ++p;
    if (!strcmp(p, "AM") || !strcmp(p, "PM")) {
        if (!hour || hour > 12) goto invalid;
        hour = hour % 12 + (*p == 'P' ? 12 : 0);
    } else if (*p || hour > 23) goto invalid;
    if (minute >= 60 || second >= 60) goto invalid;
    return size_value(hour * 3600 + minute * 60 + second);

invalid:
    *error = "ICONV time requires a valid H:MM or H:MM:SS";
    return NULL;
}

static const char *convert_input(const char *value, enum input_conversion conversion,
                                 const char **error)
{
    return conversion == ICONV_TIME ? input_time(value, error) : input_date(value, error);
}

const char *jbc_iconv(const char *value, const char *mask, const char *file, int line, int column)
{
    enum input_conversion conversion = input_mask(mask);
    if (conversion == ICONV_UNSUPPORTED) {
        fprintf(stderr, "%s:%d:%d: unsupported ICONV mask '%s'\n", file, line, column, mask);
        jbc_terminate(EXIT_FAILURE);
    }
    const char *error = NULL;
    const char *result = convert_input(value, conversion, &error);
    if (!result) numeric_error(file, line, column, error);
    return result;
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

struct output_conversion {
    char part, separator;
    int width, european, name, seconds;
};

static int output_mask(const char *mask, struct output_conversion *conversion)
{
    *conversion = (struct output_conversion){.width = 4};
    if (strncmp(mask, "MT", 2) == 0) {
        const char *suffix = mask + 2;
        conversion->part = 'T';
        conversion->seconds = *suffix == 'S';
        if (conversion->seconds) ++suffix;
        return !*suffix || !strcmp(suffix, ":");
    }

    if (*mask != 'D') return 0;
    const char *p = mask + 1;
    if (*p && strchr("DMJQWY", *p)) conversion->part = *p++;
    if ((!conversion->part || conversion->part == 'Y') && *p >= '0' && *p <= '4')
        conversion->width = *p++ - '0';
    if ((conversion->part == 'M' || conversion->part == 'W') && *p == 'A') {
        conversion->name = 1;
        ++p;
    }
    if (!conversion->part && *p && strchr("/-.", *p)) {
        conversion->separator = *p++;
        if (*p == 'E') {
            conversion->european = 1;
            ++p;
        }
    }
    return !*p;
}

static const char *convert_output(const char *value, const struct output_conversion *conversion,
                                  const char **error)
{
    static const char *const weekdays[] = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY",
        "FRIDAY", "SATURDAY", "SUNDAY"};

    struct decimal n;
    if (conversion->part == 'T') {
        if (parse_decimal(value, &n) && !n.places && n.sign >= 0 && n.digits <= 5) {
            int seconds = atoi(value);
            if (seconds <= 86399) {
                char *out = allocate(8);
                snprintf(out, 9, "%02d:%02d:%02d", seconds / 3600, seconds / 60 % 60, seconds % 60);
                if (!conversion->seconds) out[5] = '\0';
                return out;
            }
        }
        *error = "OCONV time requires whole seconds from 0 to 86399";
        return NULL;
    }

    if (!parse_decimal(value, &n) || n.places) {
        *error = "OCONV date requires an integer day count";
        return NULL;
    }
    errno = 0;
    intmax_t days = strtoimax(value, NULL, 10);
    if (errno || days > INT64_MAX || days < INT64_MIN) {
        *error = "integer operand out of range";
        return NULL;
    }
    if (days < -JBC_DATE_EPOCH || days > 2933628) {
        *error = "OCONV date outside years 1 through 9999";
        return NULL;
    }
    char part = conversion->part, separator = conversion->separator;
    int width = conversion->width, european = conversion->european, name = conversion->name;
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
}

const char *jbc_oconv(const char *value, const char *mask, const char *file, int line, int column)
{
    struct output_conversion conversion;
    if (!output_mask(mask, &conversion)) {
        fprintf(stderr, "%s:%d:%d: unsupported OCONV mask '%s'\n", file, line, column, mask);
        jbc_terminate(EXIT_FAILURE);
    }
    const char *error = NULL;
    const char *result = convert_output(value, &conversion, &error);
    if (!result) numeric_error(file, line, column, error);
    return result;
}

static char *trim_element(char *out, const char *text, const char *set, char mode)
{
    char *write = out;
    while (*text) {
        size_t run = strspn(text, set);
        if (!run) {
            run = strcspn(text, set);
            memmove(write, text, run);
            write += run;
        } else {
            int leading = write == out && strchr("LBFRD", mode);
            int trailing = !text[run] && strchr("TBERD", mode);
            if (!leading && !trailing && mode != 'A') {
                size_t keep = (mode == 'R' || mode == 'D') ? 1 : run;
                memmove(write, text, keep);
                write += keep;
            }
        }
        text += run;
    }
    return write;
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
    *trim_element(out, text, set, *mode) = '\0';
    return out;
}

const char *jbc_trims(const char *source)
{
    char *out = strcpy(allocate(strlen(source)), source);
    char *write = out, *item = out;
    for (;;) {
        char *end = item + strcspn(item, "\376\375\374");
        char mark = *end;
        *end = '\0';
        write = trim_element(write, item, " ", 'R');
        *write++ = mark;
        if (!mark) return out;
        item = end + 1;
    }
}

/* IBM CP037 and ISO-8859-1 share a reversible one-byte mapping.
   https://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/EBCDIC/CP037.TXT */
static const unsigned char cp037_to_latin1[256] = {
    0x00, 0x01, 0x02, 0x03, 0x9c, 0x09, 0x86, 0x7f, 0x97, 0x8d, 0x8e, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
    0x10, 0x11, 0x12, 0x13, 0x9d, 0x85, 0x08, 0x87, 0x18, 0x19, 0x92, 0x8f, 0x1c, 0x1d, 0x1e, 0x1f,
    0x80, 0x81, 0x82, 0x83, 0x84, 0x0a, 0x17, 0x1b, 0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x05, 0x06, 0x07,
    0x90, 0x91, 0x16, 0x93, 0x94, 0x95, 0x96, 0x04, 0x98, 0x99, 0x9a, 0x9b, 0x14, 0x15, 0x9e, 0x1a,
    0x20, 0xa0, 0xe2, 0xe4, 0xe0, 0xe1, 0xe3, 0xe5, 0xe7, 0xf1, 0xa2, 0x2e, 0x3c, 0x28, 0x2b, 0x7c,
    0x26, 0xe9, 0xea, 0xeb, 0xe8, 0xed, 0xee, 0xef, 0xec, 0xdf, 0x21, 0x24, 0x2a, 0x29, 0x3b, 0xac,
    0x2d, 0x2f, 0xc2, 0xc4, 0xc0, 0xc1, 0xc3, 0xc5, 0xc7, 0xd1, 0xa6, 0x2c, 0x25, 0x5f, 0x3e, 0x3f,
    0xf8, 0xc9, 0xca, 0xcb, 0xc8, 0xcd, 0xce, 0xcf, 0xcc, 0x60, 0x3a, 0x23, 0x40, 0x27, 0x3d, 0x22,
    0xd8, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0xab, 0xbb, 0xf0, 0xfd, 0xfe, 0xb1,
    0xb0, 0x6a, 0x6b, 0x6c, 0x6d, 0x6e, 0x6f, 0x70, 0x71, 0x72, 0xaa, 0xba, 0xe6, 0xb8, 0xc6, 0xa4,
    0xb5, 0x7e, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7a, 0xa1, 0xbf, 0xd0, 0xdd, 0xde, 0xae,
    0x5e, 0xa3, 0xa5, 0xb7, 0xa9, 0xa7, 0xb6, 0xbc, 0xbd, 0xbe, 0x5b, 0x5d, 0xaf, 0xa8, 0xb4, 0xd7,
    0x7b, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0xad, 0xf4, 0xf6, 0xf2, 0xf3, 0xf5,
    0x7d, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x50, 0x51, 0x52, 0xb9, 0xfb, 0xfc, 0xf9, 0xfa, 0xff,
    0x5c, 0xf7, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5a, 0xb2, 0xd4, 0xd6, 0xd2, 0xd3, 0xd5,
    0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0xb3, 0xdb, 0xdc, 0xd9, 0xda, 0x9f,
};

static const unsigned char latin1_to_cp037[256] = {
    0x00, 0x01, 0x02, 0x03, 0x37, 0x2d, 0x2e, 0x2f, 0x16, 0x05, 0x25, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
    0x10, 0x11, 0x12, 0x13, 0x3c, 0x3d, 0x32, 0x26, 0x18, 0x19, 0x3f, 0x27, 0x1c, 0x1d, 0x1e, 0x1f,
    0x40, 0x5a, 0x7f, 0x7b, 0x5b, 0x6c, 0x50, 0x7d, 0x4d, 0x5d, 0x5c, 0x4e, 0x6b, 0x60, 0x4b, 0x61,
    0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8, 0xf9, 0x7a, 0x5e, 0x4c, 0x7e, 0x6e, 0x6f,
    0x7c, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6,
    0xd7, 0xd8, 0xd9, 0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xba, 0xe0, 0xbb, 0xb0, 0x6d,
    0x79, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96,
    0x97, 0x98, 0x99, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8, 0xa9, 0xc0, 0x4f, 0xd0, 0xa1, 0x07,
    0x20, 0x21, 0x22, 0x23, 0x24, 0x15, 0x06, 0x17, 0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x09, 0x0a, 0x1b,
    0x30, 0x31, 0x1a, 0x33, 0x34, 0x35, 0x36, 0x08, 0x38, 0x39, 0x3a, 0x3b, 0x04, 0x14, 0x3e, 0xff,
    0x41, 0xaa, 0x4a, 0xb1, 0x9f, 0xb2, 0x6a, 0xb5, 0xbd, 0xb4, 0x9a, 0x8a, 0x5f, 0xca, 0xaf, 0xbc,
    0x90, 0x8f, 0xea, 0xfa, 0xbe, 0xa0, 0xb6, 0xb3, 0x9d, 0xda, 0x9b, 0x8b, 0xb7, 0xb8, 0xb9, 0xab,
    0x64, 0x65, 0x62, 0x66, 0x63, 0x67, 0x9e, 0x68, 0x74, 0x71, 0x72, 0x73, 0x78, 0x75, 0x76, 0x77,
    0xac, 0x69, 0xed, 0xee, 0xeb, 0xef, 0xec, 0xbf, 0x80, 0xfd, 0xfe, 0xfb, 0xfc, 0xad, 0xae, 0x59,
    0x44, 0x45, 0x42, 0x46, 0x43, 0x47, 0x9c, 0x48, 0x54, 0x51, 0x52, 0x53, 0x58, 0x55, 0x56, 0x57,
    0x8c, 0x49, 0xcd, 0xce, 0xcb, 0xcf, 0xcc, 0xe1, 0x70, 0xdd, 0xde, 0xdb, 0xdc, 0x8d, 0x8e, 0xdf,
};

static const char *translate_bytes(const char *value, const unsigned char table[256])
{
    size_t length = strlen(value);
    char *out = allocate(length);
    for (size_t i = 0; i < length; ++i)
        ((unsigned char *)out)[i] = table[(unsigned char)value[i]];
    out[length] = '\0';
    return out;
}

const char *jbc_ascii(const char *value)
{
    return translate_bytes(value, cp037_to_latin1);
}

const char *jbc_ebcdic(const char *value)
{
    return translate_bytes(value, latin1_to_cp037);
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

static const char *enclose(const char *text, char quote)
{
    size_t length = strlen(text);
    if (length > SIZE_MAX - 2) fail("quoted value is too large");
    char *out = allocate(length + 2);
    out[0] = quote;
    memcpy(out + 1, text, length);
    out[length + 1] = quote;
    out[length + 2] = '\0';
    return out;
}

const char *jbc_quote(const char *text)
{
    return enclose(text, '"');
}

const char *jbc_squote(const char *text)
{
    return enclose(text, '\'');
}

static const char *shift_bytes(const char *text, int first, int last, int step)
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

const char *jbc_upcase(const char *text)
{
    return shift_bytes(text, 'a', 'z', 'A' - 'a');
}

const char *jbc_downcase(const char *text)
{
    return shift_bytes(text, 'A', 'Z', 'a' - 'A');
}

const char *jbc_raise(const char *text)
{
    return shift_bytes(text, 248, 254, 1);
}

const char *jbc_lower(const char *text)
{
    return shift_bytes(text, 249, 255, -1);
}

const char *jbc_len(const char *s)
{
    return size_value(strlen(s));
}

const char *jbc_fold(const char *text, const char *size, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(size, &n) || n.sign < 0 || n.places)
        numeric_error(file, line, column, "FOLD width must be a nonnegative integer");
    uintmax_t width = n.sign ? (uintmax_t)integer(size, file, line, column) : 1;
    size_t length = strlen(text);
    if (!length) return "";
    /* Only a break within a word adds a byte without consuming a space. */
    size_t extra = (size_t)((length - 1) / width);
    if (extra > SIZE_MAX - length) numeric_error(file, line, column, "FOLD result too large");
    char *out = allocate(length + extra), *write = out;
    const char *field = text;
    for (;;) {
        const char *mark = strchr(field, 254);
        const char *end = mark ? mark : field + strlen(field);
        const char *start = skip_wrap_spaces(field, end);
        while (start < end) {
            const char *next;
            size_t take = word_wrap_line(start, end, width, &next);
            memcpy(write, start, take);
            write += take;

            start = next;
            if (start < end) *write++ = (char)254;
        }
        if (!mark) break;
        *write++ = (char)254;
        field = mark + 1;
    }
    *write = '\0';
    return out;
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
   selected fields. A missing occurrence has no start pointer. */
static const char *field_range(const char *s, const char *separator, size_t width,
                               int64_t first, int64_t count, size_t *bytes)
{
    while (first > 1) {
        const char *next = width ? strstr(s, separator) : NULL;
        if (!next) {
            *bytes = 0;
            return NULL;
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

static size_t field_before, field_after;

const char *jbc_col1(void)
{
    return size_value(field_before);
}

const char *jbc_col2(void)
{
    return size_value(field_after);
}

const char *jbc_field(const char *s, const char *separator, const char *start,
                      const char *count, const char *file, int line, int column)
{
    int64_t first = field_index(start, file, line, column);
    int64_t length = field_index(count, file, line, column);
    size_t bytes;
    const char *selected = field_range(s, separator, strlen(separator), first, length, &bytes);
    field_before = selected && *separator ? (size_t)(selected - s) : 0;
    field_after = selected && *separator ? field_before + bytes + 1 : 0;
    if (!bytes) return "";
    if (selected == s && !s[bytes]) return s;
    char *field = allocate(bytes);
    memcpy(field, selected, bytes);
    field[bytes] = '\0';
    return field;
}

const char *jbc_reuse_scalar(const char *value, const char *message, const char *file, int line, int column)
{
    if (strpbrk(value, "\376\375\374"))
        numeric_error(file, line, column, message);
    return value;
}

struct array_cursor {
    const char *item;
    size_t length;
    unsigned mark;
    int present;
    int reuse;
};

static void read_array_item(struct array_cursor *cursor, const char *item)
{
    cursor->item = item;
    cursor->length = strcspn(item, "\376\375\374");
    unsigned char mark = (unsigned char)item[cursor->length];
    cursor->mark = mark ? mark : 256;
}

static struct array_cursor array_cursor(const char *text, int reuse, int present)
{
    struct array_cursor cursor = {0};
    cursor.present = present;
    cursor.reuse = reuse;
    read_array_item(&cursor, text);
    return cursor;
}

/* The higher-level mark waits while the other side visits its siblings. */
static void advance_array_item(struct array_cursor *cursor, unsigned mark)
{
    if (cursor->reuse) return;
    cursor->present = cursor->mark == mark;
    if (cursor->present) read_array_item(cursor, cursor->item + cursor->length + 1);
}

/* Run once to size the result, then again to fill it. A side that reaches
   a higher-level mark waits while the other emits its remaining siblings. */
static size_t join_array_elements(const char *left, const char *separator, const char *right,
                              int reuse_left, int reuse_right, char *out)
{
    size_t used = 0, width = strlen(separator);
    struct array_cursor lhs = array_cursor(left, reuse_left, *left != 0);
    struct array_cursor rhs = array_cursor(right, reuse_right, *right != 0);
    for (;;) {
        size_t a = lhs.present ? lhs.length : 0;
        size_t b = rhs.present ? rhs.length : 0;
        /* SPLICE propagates a paired empty element. CATS has no
           separator and concatenates the available bytes at every position. */
        if (!width || !(lhs.present && rhs.present && (!a || !b))) {
            if (a > SIZE_MAX - used || width > SIZE_MAX - used - a ||
                b > SIZE_MAX - used - a - width) fail("array concatenation result too large");
            if (out) {
                memcpy(out + used, lhs.item, a);
                memcpy(out + used + a, separator, width);
                memcpy(out + used + a + width, rhs.item, b);
            }
            used += a + width + b;
        }
        unsigned mark = lhs.mark < rhs.mark ? lhs.mark : rhs.mark;
        if (mark == 256) return used;
        if (used == SIZE_MAX) fail("array concatenation result too large");
        if (out) out[used] = (char)mark;
        ++used;
        advance_array_item(&lhs, mark);
        advance_array_item(&rhs, mark);
    }
}

static const char *join_arrays(const char *left, const char *separator, const char *right,
                       int reuse_left, int reuse_right)
{
    size_t length = join_array_elements(left, separator, right, reuse_left, reuse_right, NULL);
    char *out = allocate(length);
    join_array_elements(left, separator, right, reuse_left, reuse_right, out);
    out[length] = '\0';
    return out;
}

const char *jbc_splice(const char *left, const char *separator, const char *right,
                       int reuse_left, int reuse_right)
{
    if (!*separator || (!*left && !*right)) return "";
    return join_arrays(left, separator, right, reuse_left, reuse_right);
}

const char *jbc_cats(const char *left, const char *right, int reuse_left, int reuse_right)
{
    if (!*left) return right;
    if (!*right) return left;
    return join_arrays(left, "", right, reuse_left, reuse_right);
}

/* Supply NUL-terminated scalar views at the original array's byte offsets. */
static char *split_array_items(const char *array, size_t *marks)
{
    char *copy = malloc(strlen(array) + 1);
    if (!copy) fail("out of memory");
    strcpy(copy, array);
    for (char *p = copy; (p = strpbrk(p, "\376\375\374")) != NULL; ++p) {
        *p = '\0';
        if (marks) ++*marks;
    }
    return copy;
}

static const char *convert_input_array(const char *source, enum input_conversion conversion,
                                       const char *file, int line, int column)
{
    if (!*source) return source;
    size_t marks = 0, length = strlen(source);
    char *items = split_array_items(source, &marks);
    /* A time such as 9:00 can grow by one byte when converted to seconds. */
    const size_t limit = SIZE_MAX - sizeof(struct jbc_buffer) - 1;
    if (length >= limit || marks >= limit - length)
        numeric_error(file, line, column, "ICONVS result too large");
    char *out = allocate(length + marks + 1), *write = out;
    for (const char *item = items;;) {
        const char *error = NULL;
        const char *value = *item ? convert_input(item, conversion, &error) : item;
        if (!value) {
            free(items);
            return NULL;
        }
        size_t bytes = strlen(value);
        memcpy(write, value, bytes);
        write += bytes;
        const char *end = item + strlen(item);
        char mark = source[end - items];
        *write++ = mark;
        if (!mark) break;
        item = end + 1;
    }
    free(items);
    return out;
}

const char *jbc_iconvs(const char *source, const char *mask, const char *file, int line, int column)
{
    if (!*mask) numeric_error(file, line, column, "ICONVS requires a conversion mask");
    const char *codes = mask;
    while (codes) {
        enum input_conversion conversion = input_mask(take_field(&codes, 253));
        if (conversion == ICONV_UNSUPPORTED) {
            file_result(2);
            return "";
        }
        source = convert_input_array(source, conversion, file, line, column);
        if (!source) {
            file_result(1);
            return "";
        }
    }
    file_result(0);
    return source;
}

const char *jbc_oconvs(const char *source, const char *mask, const char *file, int line, int column)
{
    if (!*mask) numeric_error(file, line, column, "OCONVS requires a conversion mask");

    size_t count = 1;
    for (const char *mark = mask; (mark = strchr(mark, 253)); ++mark) ++count;
    struct output_conversion *conversions = calloc(count, sizeof *conversions);
    if (!conversions) fail("out of memory");
    const char *codes = mask;
    for (size_t i = 0; i < count; ++i) {
        if (!output_mask(take_field(&codes, 253), &conversions[i])) {
            free(conversions);
            file_result(2);
            return "";
        }
    }

    char *items = split_array_items(source, NULL);
    const size_t limit = SIZE_MAX - sizeof(struct jbc_buffer) - 1;
    size_t capacity = strlen(source), used = 0;
    char *out = allocate(capacity);
    int status = 0;
    for (const char *item = items;;) {
        const char *value = item;
        for (size_t i = 0; *value && i < count; ++i) {
            const char *error = NULL;
            value = convert_output(value, &conversions[i], &error);
            if (!value) {
                value = item;
                status = 1;
                break;
            }
        }
        const char *end = item + strlen(item);
        char mark = source[end - items];
        size_t bytes = strlen(value), separator = mark != '\0';
        if (bytes > limit - used || separator > limit - used - bytes)
            numeric_error(file, line, column, "OCONVS result too large");
        size_t required = used + bytes + separator;
        if (required > capacity) {
            capacity = required <= limit / 2 ? 2 * required : required;
            char *larger = allocate(capacity);
            memcpy(larger, out, used);
            out = larger;
        }
        memcpy(out + used, value, bytes);
        used += bytes;
        out[used++] = mark;
        if (!mark) break;
        item = end + 1;
    }
    free(items);
    free(conversions);
    file_result(status);
    return out;
}

const char *jbc_fmts(const char *source, const char *mask, const char *file, int line, int column)
{
    if (!*source) return jbc_fmt(source, mask, file, line, column);
    char *items = split_array_items(source, NULL);
    const size_t limit = SIZE_MAX - sizeof(struct jbc_buffer) - 1;
    size_t capacity = strlen(source), used = 0;
    char *out = allocate(capacity);
    for (const char *item = items;;) {
        const char *end = item + strlen(item);
        char mark = source[end - items];
        const char *formatted = jbc_fmt(item, mask, file, line, column);
        size_t bytes = strlen(formatted), separator = mark != '\0';
        if (bytes > limit - used || separator > limit - used - bytes)
            numeric_error(file, line, column, "FMTS result too large");
        size_t required = used + bytes + separator;
        if (required > capacity) {
            capacity = required <= limit / 2 ? 2 * required : required;
            char *larger = allocate(capacity);
            memcpy(larger, out, used);
            out = larger;
        }
        memcpy(out + used, formatted, bytes);
        used += bytes;
        out[used++] = mark;
        if (!mark) break;
        item = end + 1;
    }
    free(items);
    return out;
}

static const char *array_arithmetic(char op, const char *left, const char *right,
                                     int reuse_left, int reuse_right,
                                     const char *file, int line, int column)
{
    struct array_cursor lhs = array_cursor(left, reuse_left, 1);
    struct array_cursor rhs = array_cursor(right, reuse_right, 1);
    char *left_items = split_array_items(left, NULL);
    char *right_items = split_array_items(right, NULL);
    const size_t limit = SIZE_MAX - sizeof(struct jbc_buffer) - 1;
    size_t capacity = strlen(left), right_length = strlen(right), used = 0;
    if (capacity < right_length) capacity = right_length;
    char *out = allocate(capacity);
    for (;;) {
        const char *a = left_items + (lhs.item - left);
        const char *b = right_items + (rhs.item - right);
        const char *item = "";
        if (op == '-') {
            const char *minuend = lhs.present && *a ? a : "0";
            const char *subtrahend = rhs.present && *b ? b : "0";
            item = jbc_arithmetic('-', minuend, subtrahend, file, line, column);
        } else if (!lhs.present || !rhs.present) {
            item = "0";
            if (op == '+') item = lhs.present ? a : b;
            else if (op == '/' && lhs.present) item = a;
        } else if (*a && *b) {
            item = arithmetic(op, a, b, op == '/', file, line, column);
        }

        size_t bytes = strlen(item);
        unsigned mark = lhs.mark < rhs.mark ? lhs.mark : rhs.mark;
        size_t separator = mark != 256;
        if (bytes > limit - used || separator > limit - used - bytes)
            numeric_error(file, line, column, "array arithmetic result too large");
        size_t required = used + bytes + separator;
        if (required > capacity) {
            capacity = required <= limit / 2 ? 2 * required : required;
            char *larger = allocate(capacity);
            memcpy(larger, out, used);
            out = larger;
        }
        memcpy(out + used, item, bytes);
        used += bytes;
        if (mark == 256) break;
        out[used++] = (char)mark;
        advance_array_item(&lhs, mark);
        advance_array_item(&rhs, mark);
    }
    out[used] = '\0';
    free(left_items);
    free(right_items);
    return out;
}

const char *jbc_adds(const char *left, const char *right, int reuse_left, int reuse_right,
                     const char *file, int line, int column)
{
    return array_arithmetic('+', left, right, reuse_left, reuse_right, file, line, column);
}

const char *jbc_subs(const char *left, const char *right, int reuse_left, int reuse_right,
                     const char *file, int line, int column)
{
    return array_arithmetic('-', left, right, reuse_left, reuse_right, file, line, column);
}

const char *jbc_muls(const char *left, const char *right, int reuse_left, int reuse_right,
                     const char *file, int line, int column)
{
    return array_arithmetic('*', left, right, reuse_left, reuse_right, file, line, column);
}

const char *jbc_divs(const char *left, const char *right, int reuse_left, int reuse_right,
                     const char *file, int line, int column)
{
    return array_arithmetic('/', left, right, reuse_left, reuse_right, file, line, column);
}

static const char *array_sign(const char *source, int absolute, const char *file, int line, int column)
{
    if (!*source) return "";
    size_t marks = 0, length = strlen(source);
    char *items = split_array_items(source, &marks);
    /* A decimal can gain a minus sign and a leading zero. */
    const size_t limit = SIZE_MAX - sizeof(struct jbc_buffer) - 1;
    if (length > limit || marks + 1 > (limit - length) / 2)
        numeric_error(file, line, column, absolute ? "ABSS result too large" : "NEGS result too large");
    char *out = allocate(length + 2 * (marks + 1)), *write = out;
    for (const char *item = items;;) {
        const char *value = "";
        if (*item && absolute)
            value = absolute_value(item, "ABSS requires numeric elements", file, line, column);
        else if (*item)
            value = negative_value(item, "NEGS", file, line, column);
        size_t bytes = strlen(value);
        memcpy(write, value, bytes);
        write += bytes;

        const char *end = item + strlen(item);
        char mark = source[end - items];
        *write++ = mark;
        if (!mark) break;
        item = end + 1;
    }
    free(items);
    return out;
}

const char *jbc_negs(const char *source, const char *file, int line, int column)
{
    return array_sign(source, 0, file, line, column);
}

const char *jbc_abss(const char *source, const char *file, int line, int column)
{
    return array_sign(source, 1, file, line, column);
}

static const char *compare_array_items(const char *left, const char *right, int reuse_left,
                                       int reuse_right, const char *equal, const char *unequal)
{
    struct array_cursor lhs = array_cursor(left, reuse_left, 1);
    struct array_cursor rhs = array_cursor(right, reuse_right, 1);
    if (lhs.mark == 256 && rhs.mark == 256)
        return !*left || !*right ? "" : (jbc_compare(left, right, jbc_precision) ? unequal : equal);

    size_t marks = 0;
    char *a = split_array_items(left, &marks);
    char *b = split_array_items(right, &marks);
    if (marks > (SIZE_MAX - 1) / 2) fail("array comparison result too large");
    char *out = allocate(2 * marks + 1), *write = out;
    for (;;) {
        if (!lhs.present || !rhs.present) *write++ = *unequal;
        else if (lhs.length && rhs.length)
            *write++ = jbc_compare(a + (lhs.item - left), b + (rhs.item - right), jbc_precision) ? *unequal : *equal;
        unsigned mark = lhs.mark < rhs.mark ? lhs.mark : rhs.mark;
        if (mark == 256) break;
        *write++ = (char)mark;
        advance_array_item(&lhs, mark);
        advance_array_item(&rhs, mark);
    }
    *write = '\0';
    free(a);
    free(b);
    return out;
}

const char *jbc_eqs(const char *left, const char *right, int reuse_left, int reuse_right)
{
    return compare_array_items(left, right, reuse_left, reuse_right, "1", "0");
}

const char *jbc_nes(const char *left, const char *right, int reuse_left, int reuse_right)
{
    return compare_array_items(left, right, reuse_left, reuse_right, "0", "1");
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
        if (selected) memmove(write, selected, bytes);
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

struct record_lock {
    struct record_lock *next;
    int foreign;
    char key[];
};

struct memory_file {
    struct memory_file *next;
    struct memory_record *records, *last_read;
    struct record_lock *locks;
    size_t serial;
    char list_token;
    const char *section;
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

/* A lock is keyed independently of record existence. NULL selects every key. */
static void release_locks(struct memory_file *f, const char *key, int include_foreign)
{
    struct record_lock **link = &f->locks;
    while (*link) {
        struct record_lock *lock = *link;
        if ((include_foreign || !lock->foreign) && (!key || strcmp(lock->key, key) == 0)) {
            *link = lock->next;
            free(lock);
        } else {
            link = &lock->next;
        }
    }
}

static struct record_lock *find_lock(struct memory_file *f, const char *key)
{
    for (struct record_lock *lock = f->locks; lock; lock = lock->next)
        if (!strcmp(lock->key, key)) return lock;
    return NULL;
}

static void add_lock(struct memory_file *f, const char *key, int foreign)
{
    struct record_lock *lock = malloc(sizeof *lock + strlen(key) + 1);
    if (!lock) fail("out of memory");
    lock->foreign = foreign;
    strcpy(lock->key, key);
    lock->next = f->locks;
    f->locks = lock;
}

static void free_files(void)
{
    while (files) {
        struct memory_file *file = files;
        files = file->next;
        clear_records(file);
        release_locks(file, NULL, 1);
        free(file);
    }
}

static char *record_copy(const char *s)
{
    char *copy = malloc(strlen(s) + 1);
    if (!copy) fail("out of memory");
    return strcpy(copy, s);
}

static struct memory_file *find_memory_file(const char *section, const char *name)
{
    for (struct memory_file *f = files; f; f = f->next)
        if (strcmp(f->section, section) == 0 && strcmp(f->name, name) == 0) return f;
    return NULL;
}

void jbc_create_memory_file(const char *section, const char *name)
{
    if (find_memory_file(section, name)) return;
    if (!files && atexit(free_files) != 0) fail("cannot register file cleanup");
    struct memory_file *f = calloc(1, sizeof *f + strlen(name) + 1);
    if (!f) fail("out of memory");
    f->section = section;
    strcpy(f->name, name);
    f->next = files;
    files = f;
}

void jbc_seed_memory_lock(const char *name, const char *key)
{
    struct memory_file *f = find_memory_file("", name);
    if (!f) fail("memory lock requires a registered data file");
    if (!find_lock(f, key)) add_lock(f, key, 1);
}

/* A descriptor can be closed through a reference argument in a nested call.
   Track its slot as well as its opening frame to retire that cleanup entry. */
struct opened_file {
    struct opened_file *next;
    struct memory_file *file;
    const void *scope;
    jbc_variable *slot;
};

static struct opened_file *local_opens;

static void remember_open(const void *scope, jbc_variable *slot, struct memory_file *f)
{
    for (struct opened_file *p = local_opens; p; p = p->next)
        if (p->scope == scope && p->slot == slot && p->file == f) return;
    struct opened_file *p = malloc(sizeof *p);
    if (!p) fail("out of memory");
    *p = (struct opened_file){local_opens, f, scope, slot};
    local_opens = p;
}

void jbc_close_local_files(const void *scope)
{
    struct opened_file **link = &local_opens;
    while (*link) {
        struct opened_file *p = *link;
        if (p->scope == scope) {
            release_locks(p->file, NULL, 0);
            *link = p->next;
            free(p);
        } else link = &p->next;
    }
}

int jbc_open_file(const char *section, const char *name, jbc_variable *out, const void *scope,
                  jbc_variable *setting)
{
    struct memory_file *f = find_memory_file(section, name);
    if (f && scope) remember_open(scope, out, f);
    assign_value(out, f ? f->name : "");
    if (setting) assign_value(setting, f ? "0" : "128");
    return file_result(f ? 0 : 128);
}

static struct memory_file *file_for(const char *handle)
{
    for (struct memory_file *f = files; f; f = f->next)
        if (f->name == handle) return f;
    return NULL;
}

int jbc_close_file(jbc_variable *slot)
{
    struct memory_file *f = file_for(slot->value);
    if (!f) return file_succeeded(128);
    struct opened_file **link = &local_opens;
    while (*link) {
        struct opened_file *p = *link;
        if (p->slot == slot && p->file == f) {
            *link = p->next;
            free(p);
            break;
        }
        link = &p->next;
    }
    release_locks(f, NULL, 0);
    assign_value(slot, NULL);
    return file_succeeded(0);
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

static size_t last_external_selection;

const char *jbc_selected(void)
{
    return size_value(last_external_selection);
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

static void set_array_list(jbc_variable *slot, const char *value, int has_entries)
{
    assign_value(slot, value);
    slot->array_list = 1;
    if (!has_entries) slot->remove_offset = SIZE_MAX;
}

void jbc_formlist(const char *source, jbc_variable *list, jbc_variable *setting)
{
    set_array_list(list_slot(list), source, *source != '\0');
    if (setting) assign_value(setting, jbc_dcount(source, "\376"));
}

int jbc_select(const char *source, jbc_variable *list, jbc_variable *setting)
{
    int use_default = source == NULL;
    struct memory_file *f = file_for(use_default ? jbc_default_file.value : source);
    int success = f || !use_default;
    list = list_slot(list);
    if (!f && !use_default) set_array_list(list, source, *source != '\0');
    else assign_value(list, f ? &f->list_token : "");
    if (setting) assign_value(setting, success ? "" : "128");
    return success;
}

int jbc_sselect(const char *source, jbc_variable *list, jbc_variable *setting)
{
    struct memory_file *f = file_for(source ? source : jbc_default_file.value);
    const char *value = "";
    size_t count = 0, length = 0;
    for (struct memory_record *r = f ? f->records : NULL; r; r = r->next) {
        size_t bytes = strlen(r->key);
        if (bytes >= SIZE_MAX - length) fail("select list too large");
        length += bytes + 1;
        ++count;
    }
    if (count) {
        struct sort_element *elements = calloc(count, sizeof *elements);
        if (!elements) fail("out of memory");
        size_t i = 0;
        for (struct memory_record *r = f->records; r; r = r->next)
            elements[i++] = (struct sort_element){r->key, strlen(r->key)};
        value = join_sorted_elements(elements, count, length - 1);
        free(elements);
    }
    list = list_slot(list);
    if (f) set_array_list(list, value, count != 0);
    else assign_value(list, "");
    if (setting) assign_value(setting, f ? "" : "128");
    return f != NULL;
}

static struct memory_file *selected_file(const char *token)
{
    for (struct memory_file *f = files; f; f = f->next)
        if (&f->list_token == token) return f;
    return NULL;
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
    struct memory_file *f = selected_file(list->value);
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

#if defined(JBC_SAVED_LISTS) || defined(JBC_SEQUENTIAL)
static int file_error(int error)
{
    if (error == ENOENT || error == ENOTDIR) return 128;
    if (error == EACCES || error == EPERM || error == EROFS) return 24576;
    return 32768;
}
#endif

#ifdef JBC_SAVED_LISTS
#include <unistd.h>

/* Copy the remaining keys when a file-backed cursor crosses the list boundary. */
static const char *list_snapshot(const char *value, size_t offset, size_t *count)
{
    *count = 0;
    if (offset == SIZE_MAX) return "";
    struct memory_file *f = selected_file(value);
    if (f) {
        struct memory_record *first = f->records;
        while (first && first->serial <= offset) first = first->next;
        size_t length = 0;
        for (struct memory_record *r = first; r; r = r->next) {
            size_t bytes = strlen(r->key);
            if (bytes >= SIZE_MAX - length) fail("select list too large");
            length += bytes + 1;
            ++*count;
        }
        char *out = allocate(length), *end = out;
        for (struct memory_record *r = first; r; r = r->next) {
            if (r != first) *end++ = (char)254;
            size_t bytes = strlen(r->key);
            memcpy(end, r->key, bytes);
            end += bytes;
        }
        *end = '\0';
        return out;
    }
    const char *tail = value + offset;
    *count = *value ? 1 + occurrences(tail, "\376") : 0;
    return offset ? strcpy(allocate(strlen(tail)), tail) : tail;
}

/* List names are arbitrary bytes. Encode every byte in one path component. */
static const char *saved_list_path(const char *directory, const char *name)
{
    static const char hex[] = "0123456789abcdef";
    size_t length = strlen(name);
    if (length > SIZE_MAX / 2) fail("list name too long");
    char *encoded = allocate(2 * length);
    for (size_t i = 0; i < length; ++i) {
        unsigned char c = (unsigned char)name[i];
        encoded[2 * i] = hex[c >> 4];
        encoded[2 * i + 1] = hex[c & 15];
    }
    encoded[2 * length] = '\0';
    return jbc_concat(jbc_concat(directory, "/list-"), encoded);
}

int jbc_writelist(const char *source, const char *name, jbc_variable *setting)
{
    size_t count;
    const char *value = list_snapshot(source, 0, &count);
    int status = 0;
    if (!*name) {
        set_array_list(&select_lists[0], value, count != 0);
        last_external_selection = count;
    } else {
        const char *directory = getenv("JBCC_LIST_DIR");
        if (!directory || !*directory) status = 128;
        else {
            const char *path = saved_list_path(directory, name);
            char *temp = record_copy(jbc_concat(directory, "/.list-XXXXXX"));
            int fd = mkstemp(temp);
            if (fd < 0) status = file_error(errno);
            else {
                FILE *out = fdopen(fd, "wb");
                if (!out) {
                    status = file_error(errno);
                    close(fd);
                } else {
                    if (fputs(value, out) == EOF) status = file_error(errno);
                    if (fclose(out) && !status) status = file_error(errno);
                }
                if (!status && rename(temp, path)) status = file_error(errno);
                if (status) unlink(temp);
            }
            free(temp);
        }
    }
    if (setting) assign_value(setting, size_value((size_t)status));
    return !status;
}

int jbc_readlist(const char *name, jbc_variable *out, jbc_variable *setting)
{
    size_t count = 0;
    const char *value = "";
    int found = 0;
    if (!*name) {
        jbc_variable *active = &select_lists[0];
        found = active->array_list || selected_file(active->value);
        if (found) {
            value = list_snapshot(active->value, active->remove_offset, &count);
            assign_value(active, NULL);
        }
    } else {
        const char *directory = getenv("JBCC_LIST_DIR");
        FILE *in = directory && *directory ? fopen(saved_list_path(directory, name), "rb") : NULL;
        if (in) {
            char *bytes = NULL;
            size_t capacity = 0;
            ssize_t n = getdelim(&bytes, &capacity, '\0', in);
            found = feof(in) && !ferror(in);
            if (fclose(in)) found = 0;
            if (found && n > 0) {
                value = strcpy(allocate((size_t)n), bytes);
                count = 1 + occurrences(value, "\376");
            }
            free(bytes);
        }
    }
    if (found) set_array_list(out, value, count != 0);
    else assign_value(out, "");
    if (setting) assign_value(setting, size_value(count));
    return found;
}

void jbc_deletelist(const char *name, const char *file, int line, int column)
{
    if (!*name) {
        assign_value(&select_lists[0], NULL);
        return;
    }
    const char *directory = getenv("JBCC_LIST_DIR");
    if (!directory || !*directory)
        numeric_error(file, line, column, "DELETELIST requires JBCC_LIST_DIR");
    if (unlink(saved_list_path(directory, name)) && errno != ENOENT)
        numeric_error(file, line, column, strerror(errno));
}
#endif

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
    if (!file) return file_result(128);
    for (struct record_lock *lock = file->locks; lock; lock = lock->next) {
        if (lock->foreign) {
            /* Keep the original error status unless a LOCKED arm handles it. */
            if (setting) assign_value(setting, "32768");
            file_result(32768);
            return JBC_LOCKED;
        }
    }
    clear_records(file);
    release_locks(file, NULL, 0);
    return file_result(0);
}

int jbc_delete_record(const char *handle, const char *key, jbc_variable *setting)
{
    struct memory_file *f = file_for(handle);
    if (setting) assign_value(setting, f ? "0" : "128");
    if (!f) return file_succeeded(128);
    struct record_lock *lock = find_lock(f, key);
    if (lock && lock->foreign) {
        if (setting) assign_value(setting, "32768");
        return file_succeeded(32768);
    }
    release_locks(f, key, 0);
    struct memory_record **link = record_link(f, key);
    if (*link) {
        struct memory_record *record = *link;
        *link = record->next;
        if (f->last_read == record) f->last_read = NULL;
        free_record(record);
    }
    return file_succeeded(0);
}

int jbc_read_record(const char *handle, const char *key, jbc_variable *out)
{
    struct memory_file *f = file_for(handle);
    struct memory_record *r = f ? *record_link(f, key) : NULL;
    if (!r) {
        assign_value(out, "");
        return file_succeeded(128);
    }
    assign_value(out, strcpy(allocate(strlen(r->value)), r->value));
    return file_succeeded(0);
}

const char *jbc_recordlocked(const char *handle, const char *key)
{
    struct memory_file *f = file_for(handle);
    struct record_lock *lock = f ? find_lock(f, key) : NULL;
    return !lock ? "0" : lock->foreign ? "-2" : "2";
}

void jbc_release_lock(const char *handle, const char *key)
{
    if (key) {
        struct memory_file *f = file_for(handle);
        if (f) release_locks(f, key, 0);
    } else {
        for (struct memory_file *f = files; f; f = f->next)
            release_locks(f, NULL, 0);
    }
}

static int lock_for_update(struct memory_file *f, const char *key, jbc_variable *setting)
{
    if (!f) {
        if (setting) assign_value(setting, "32768");
        return 32768;
    }
    struct record_lock *lock = find_lock(f, key);
    if (lock && lock->foreign) {
        if (blocked_record_locks < SIZE_MAX) ++blocked_record_locks;
        if (setting) assign_value(setting, "-2");
        return JBC_LOCKED;
    }
    if (!lock) add_lock(f, key, 0);
    return 0;
}

int jbc_readu(const char *handle, const char *key, jbc_variable *out, jbc_variable *setting)
{
    struct memory_file *f = file_for(handle);
    if (!f) assign_value(out, "");
    int status = lock_for_update(f, key, setting);
    if (status) return file_result(status);
    int found = jbc_read_record(handle, key, out);
    if (setting) assign_value(setting, found ? "" : "128");
    return file_result(found ? 0 : 128);
}

int jbc_recordlocku(const char *handle, const char *key, jbc_variable *setting)
{
    int status = lock_for_update(file_for(handle), key, setting);
    if (!status && setting) assign_value(setting, "");
    return file_result(status);
}

int jbc_matread(const char *handle, const char *key, jbc_variable *dest, int rank,
                const int *bounds, size_t storage_count, jbc_variable *setting, int update)
{
    last_matrix_load = 0;
    struct memory_file *f = file_for(handle);
    if (update) {
        int status = lock_for_update(f, key, setting);
        if (status) return file_result(status);
    }
    struct memory_record *record = f ? *record_link(f, key) : NULL;
    if (!record) {
        if (setting) assign_value(setting, "128");
        return file_result(128);
    }

    size_t total = matrix_elements(rank, bounds);
    const char *field = *record->value ? record->value : NULL;
    jbc_matrix_fill(dest, storage_count, "");
    for (size_t i = 0; i < total && field; ++i) {
        const char *value = take_field(&field, i + 1 == total ? 0 : 254);
        assign_value(&dest[matrix_element_offset(i, rank, bounds)], value);
    }
    size_t fields = *record->value ? 1 + occurrences(record->value, "\376") : 0;
    last_matrix_load = fields <= total ? fields : 0;
    if (setting) assign_value(setting, size_value(fields));
    return file_result(0);
}

int jbc_read_field(const char *handle, const char *key, const char *field, jbc_variable *out,
                   jbc_variable *setting, int update, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(field, &n))
        numeric_error(file, line, column, update ? "READVU requires a numeric field number"
                                                 : "READV requires a numeric field number");
    struct memory_file *f = file_for(handle);
    if (update) {
        if (!f) assign_value(out, "");
        int status = lock_for_update(f, key, setting);
        if (status) return file_result(status);
    }
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
    return file_result(record ? 0 : 128);
}

static int write_record_status(const char *handle, const char *key, const char *value,
                               int64_t field, int keep_lock)
{
    struct memory_file *f = file_for(handle);
    if (!f) return 128;
    struct record_lock *lock = find_lock(f, key);
    if (lock && lock->foreign) return 32768;
    struct memory_record **link = record_link(f, key);
    struct memory_record *r = *link;
    if (field) {
        const char *current = r ? r->value : "";
        value = array_part(current, strlen(current), &field, 1, 0, value, 0);
    }
    if (!r) {
        r = calloc(1, sizeof *r);
        if (!r) fail("out of memory");
        r->key = record_copy(key);
        if (f->serial == SIZE_MAX - 1) fail("file record counter overflow");
        r->serial = ++f->serial;
        *link = r;
    }
    char *copy = record_copy(value);
    free(r->value);
    r->value = copy;
    if (lock && !keep_lock) release_locks(f, key, 0);
    return 0;
}

int jbc_write_record(const char *handle, const char *key, const char *value,
                     jbc_variable *setting, int keep_lock)
{
    int status = write_record_status(handle, key, value, 0, keep_lock);
    if (setting) assign_value(setting, status ? size_value((size_t)status) : "");
    return file_succeeded(status);
}

int jbc_write_field(const char *handle, const char *key, const char *field, const char *value,
                    jbc_variable *setting, int keep_lock, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(field, &n) || n.sign <= 0 || n.places)
        numeric_error(file, line, column, keep_lock ? "WRITEVU requires a positive integer field number"
                                                    : "WRITEV requires a positive integer field number");
    int64_t position = integer(field, file, line, column);
    int status = write_record_status(handle, key, value, position, keep_lock);
    if (setting) assign_value(setting, status ? size_value((size_t)status) : "");
    return file_succeeded(status);
}

int jbc_matwrite(const char *handle, const char *key, const jbc_variable *src, int rank,
                 const int *bounds, jbc_variable *setting, const char *name,
                 const char *file, int line, int column)
{
    const char *record = jbc_matbuild(src, rank, bounds, NULL, NULL, "\376", name, file, line, column);
    int status = write_record_status(handle, key, record, 0, 0);
    if (setting) {
        const char *result = status == 128 ? "128" : "32768";
        assign_value(setting, status ? result : jbc_dcount(record, "\376"));
    }
    return file_result(status);
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

const char *jbc_seq(const char *value)
{
    return size_value((unsigned char)*value);
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
    jbc_run_exit_callbacks();
#ifdef JBC_REPORT
    finish_reports();
#endif
    exit((int)status);
}

void jbc_stop(int aborting, const char *const *args, size_t count)
{
    if (!aborting) jbc_run_exit_callbacks();
#ifdef JBC_REPORT
    if (!aborting) finish_reports();
#endif
    if (count) {
        fflush(stdout);
        struct decimal message;
        if (parse_decimal(args[0], &message))
            fprintf(stderr, "%s [%s]", aborting ? "ABORT" : "STOP", args[0]);
        else
            fputs(args[0], stderr);
        for (size_t i = 1; i < count; ++i) {
            fputc(' ', stderr);
            fputs(args[i], stderr);
        }
        fputc('\n', stderr);
    }
    jbc_terminate(aborting ? EXIT_FAILURE : EXIT_SUCCESS);
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

static uint32_t bitxor_operand(const char *value, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n))
        numeric_error(file, line, column, "BITXOR requires numeric operands");
    uint32_t bits = 0;
    for (size_t i = 0; i < n.digits; ++i)
        bits = (uint32_t)(UINT64_C(10) * bits + (unsigned)(n.whole[i] - '0'));
    return n.sign < 0 ? (uint32_t)(0u - bits) : bits;
}

const char *jbc_bitxor(const char *left, const char *right, const char *file, int line, int column)
{
    if (!*left || !*right) return "";
    uint32_t bits = bitxor_operand(left, file, line, column) ^
                    bitxor_operand(right, file, line, column);
    int64_t result = bits <= INT32_MAX ? (int64_t)bits : (int64_t)bits - (INT64_C(1) << 32);
    char *out = allocate(11);
    snprintf(out, 12, "%" PRId64, result);
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

static size_t space_count(const char *value, const char *file, int line, int column,
                          const char *size_error)
{
    int64_t n = truncated(value, file, line, column);
    if (n <= 0) return 0;
    if ((uint64_t)n > SIZE_MAX - sizeof(struct jbc_buffer) - 1)
        numeric_error(file, line, column, size_error);
    return (size_t)n;
}

const char *jbc_space(const char *value, const char *file, int line, int column)
{
    size_t count = space_count(value, file, line, column, "SPACE result too large");
    if (!count) return "";
    char *out = allocate(count);
    memset(out, ' ', count);
    out[count] = '\0';
    return out;
}

/* Size every element before allocating the result, then fill it in place. */
static size_t fill_space_array(const char *source, const char *items, char *out,
                               const char *file, int line, int column)
{
    const size_t limit = SIZE_MAX - sizeof(struct jbc_buffer) - 1;
    size_t used = 0;
    for (const char *item = items;;) {
        if (!*item) numeric_error(file, line, column, "SPACES requires nonempty elements");
        size_t count = space_count(item, file, line, column, "SPACES result too large");
        const char *end = item + strlen(item);
        char mark = source[end - items];
        size_t bytes = count + (mark != '\0');
        if (bytes > limit - used) numeric_error(file, line, column, "SPACES result too large");
        if (out) {
            memset(out + used, ' ', count);
            out[used + count] = mark;
        }
        used += bytes;
        if (!mark) return used;
        item = end + 1;
    }
}

const char *jbc_spaces(const char *source, const char *file, int line, int column)
{
    char *items = split_array_items(source, NULL);
    size_t length = fill_space_array(source, items, NULL, file, line, column);
    char *out = allocate(length);
    fill_space_array(source, items, out, file, line, column);
    free(items);
    return out;
}

static size_t substring_range(size_t n, int64_t start, int64_t count, size_t *offset)
{
    *offset = 0;
    if (start > 0) *offset = (uint64_t)(start - 1) > n ? n : (size_t)(start - 1);
    if (start < 0 && start >= -(int64_t)n) *offset = n - (size_t)(-start);
    size_t available = n - *offset;
    return count <= 0 ? 0 : (uint64_t)count > available ? available : (size_t)count;
}

const char *jbc_substrings(const char *source, const char *start, const char *length,
                           const char *file, int line, int column)
{
    int64_t first = truncated(start, file, line, column);
    int64_t count = truncated(length, file, line, column);
    char *out = allocate(strlen(source));
    char *write = out;
    for (;;) {
        size_t bytes = strcspn(source, "\376\375\374");
        size_t offset;
        size_t take = substring_range(bytes, first, count, &offset);
        memcpy(write, source + offset, take);
        write += take;
        source += bytes;
        *write++ = *source;
        if (!*source) return out;
        ++source;
    }
}

const char *jbc_substring(const char *text, const char *start, const char *length,
                          const char *file, int line, int column, const char *replacement)
{
    int64_t first = start ? truncated(start, file, line, column) : 0;
    int64_t count = truncated(length, file, line, column);
    if (!start && !replacement && count <= 0) return "";
    size_t n = strlen(text);
    size_t offset, take;
    if (start) {
        take = substring_range(n, first, count, &offset);
    } else {
        take = count <= 0 ? 0 : (uint64_t)count > n ? n : (size_t)count;
        offset = n - take;
    }
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

const char *jbc_left(const char *text, const char *length, const char *file, int line, int column)
{
    return jbc_substring(text, "1", length, file, line, column, NULL);
}

const char *jbc_right(const char *text, const char *length, const char *file, int line, int column)
{
    return jbc_substring(text, NULL, length, file, line, column, NULL);
}

#ifdef JBC_MATH
const char *jbc_ln(const char *text, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(text, &n))
        numeric_error(file, line, column, "LN requires a numeric operand");
    if (n.sign <= 0)
        numeric_error(file, line, column, "LN requires a positive operand");
    long double value = strtold(text, NULL);
    if (!isfinite(value) || value == 0)
        numeric_error(file, line, column, "LN operand out of range");
    return format_decimal(logl(value), ROUND_RESULT);
}

const char *jbc_exp(const char *text, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(text, &n))
        numeric_error(file, line, column, "EXP requires a numeric operand");
    long double value = strtold(text, NULL);
    if (!isfinite(value))
        numeric_error(file, line, column, "EXP operand out of range");
    long double result = expl(value);
    if (!isfinite(result))
        numeric_error(file, line, column, "EXP result out of range");
    return format_decimal(result, ROUND_RESULT);
}

const char *jbc_sqrt(const char *text, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(text, &n))
        numeric_error(file, line, column, "SQRT requires a numeric operand");
    if (n.sign < 0)
        numeric_error(file, line, column, "SQRT requires a nonnegative operand");
    if (!n.sign) return "0";
    long double value = strtold(text, NULL);
    if (!isfinite(value) || value == 0)
        numeric_error(file, line, column, "SQRT operand out of range");
    return format_decimal(sqrtl(value), ROUND_RESULT);
}

const char *jbc_pwr(const char *left, const char *right, const char *file, int line, int column)
{
    struct decimal base, exponent;
    if (!parse_decimal(left, &base) || !parse_decimal(right, &exponent))
        numeric_error(file, line, column, "PWR requires numeric operands");
    if (base.sign < 0 && exponent.places) {
        fprintf(stderr, "%s:%d:%d: negative base with fractional exponent in PWR\n", file, line, column);
        return "0";
    }
    if (!base.sign && exponent.sign < 0)
        numeric_error(file, line, column, "zero raised to a negative power");

    long double x = strtold(left, NULL), y = strtold(right, NULL);
    if (!isfinite(x) || !isfinite(y))
        numeric_error(file, line, column, "PWR operand out of range");
    long double result = powl(fabsl(x), y);
    if (!isfinite(result)) numeric_error(file, line, column, "PWR result out of range");
    /* The decimal text retains the parity of integer exponents too large
       to be represented exactly by the host floating-point type. */
    if (base.sign < 0 && exponent.digits && (exponent.whole[exponent.digits - 1] - '0') % 2)
        result = -result;
    return format_decimal(result, TRUNCATE_RESULT);
}

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
    return format_decimal(sinl(radians(s, file, line, column)), TRUNCATE_RESULT);
}

const char *jbc_cos(const char *s, const char *file, int line, int column)
{
    return format_decimal(cosl(radians(s, file, line, column)), TRUNCATE_RESULT);
}
#endif

#ifdef JBC_EXECUTE
#include <fcntl.h>
#include <sys/wait.h>
#include <unistd.h>

static int command_exit_code(int status)
{
    return WIFSIGNALED(status) ? 128 + WTERMSIG(status) : WEXITSTATUS(status);
}

static const char *read_command_output(FILE *stream, const char **result, const char *nul_error)
{
    char *bytes = NULL;
    size_t capacity = 0;
    ssize_t length = getdelim(&bytes, &capacity, '\0', stream);
    const char *error = NULL;
    if (ferror(stream) || (length < 0 && !feof(stream))) error = "cannot read command output";
    else if (length > 0 && bytes[length - 1] == '\0') error = nul_error;
    else *result = length > 0 ? jbc_convert(bytes, "\n", "\376") : "";
    free(bytes);
    return error;
}

static void redirect_command_fd(int fd, int target)
{
    if (fd == target) {
        if (fcntl(fd, F_SETFD, 0) == -1) _exit(127);
    } else {
        if (dup2(fd, target) == -1) _exit(127);
        close(fd);
    }
}

static FILE *command_input(void)
{
    FILE *stream = tmpfile();
    if (!stream) return NULL;
    for (const struct input_chunk *chunk = input_data; chunk; chunk = chunk->next) {
        size_t length = chunk->length - chunk->offset;
        if (fwrite(chunk->bytes + chunk->offset, 1, length, stream) != length) {
            fclose(stream);
            return NULL;
        }
    }
    if (!fseek(stream, 0, SEEK_SET)) return stream;
    fclose(stream);
    return NULL;
}

void jbc_execute(const char *command, jbc_variable *capture, jbc_variable *returning,
                 const char *file, int line, int column)
{
    if ((unsigned char)command[0] == 255) {
        if (command[1] != 's')
            numeric_error(file, line, column, "unsupported EXECUTE shell selector");
        command += 2;
    }
    if (strchr(command, 254))
        numeric_error(file, line, column, "field-mark-separated EXECUTE commands are unsupported");
    if (fflush(stdout) == EOF || fflush(stderr) == EOF)
        numeric_error(file, line, column, "cannot flush output before EXECUTE");
    if (!capture && !returning && !input_data) {
        int status = system(command);
        if (status == -1) numeric_error(file, line, column, "cannot execute command");
        last_command_code = command_exit_code(status);
        return;
    }

    /* Spool stdin to let a child read any amount or exit without reading. */
    FILE *input = input_data ? command_input() : NULL;
    if (input_data && !input) numeric_error(file, line, column, "cannot prepare queued command input");
    int input_fd = input ? fileno(input) : -1;
    int output_pipe[2];
    FILE *output = NULL;
    if (capture) {
        if (pipe(output_pipe) == -1 || !(output = fdopen(output_pipe[0], "r")))
            numeric_error(file, line, column, "cannot open command output pipe");
    }
    /* Spool stderr so the child can write either stream without blocking on the other. */
    FILE *errors = returning ? tmpfile() : NULL;
    if (returning && !errors) numeric_error(file, line, column, "cannot open command error file");
    int error_fd = errors ? fileno(errors) : -1;
    pid_t child = fork();
    if (child == -1) numeric_error(file, line, column, "cannot start command");
    if (!child) {
        if (input_fd != -1) redirect_command_fd(input_fd, STDIN_FILENO);
        if (capture) {
            close(output_pipe[0]);
            redirect_command_fd(output_pipe[1], STDOUT_FILENO);
        }
        if (returning) redirect_command_fd(error_fd, STDERR_FILENO);
        execl("/bin/sh", "sh", "-c", command, (char *)NULL);
        _exit(127);
    }
    if (input) {
        fclose(input);
        jbc_cleardata();
    }

    const char *captured = "", *messages = "", *error = NULL;
    if (capture) {
        close(output_pipe[1]);
        error = read_command_output(output, &captured, "CAPTURING cannot store a NUL byte");
        fclose(output);
    }
    int status;
    pid_t waited;
    do { waited = waitpid(child, &status, 0); } while (waited == -1 && errno == EINTR);
    if (waited == -1) error = "cannot wait for command";
    if (errors) {
        if (!error && fseek(errors, 0, SEEK_SET)) error = "cannot rewind command error file";
        if (!error) error = read_command_output(errors, &messages, "RETURNING cannot store a NUL byte");
        fclose(errors);
    }
    if (error) numeric_error(file, line, column, error);
    last_command_code = command_exit_code(status);
    if (capture) assign_value(capture, captured);
    if (returning) {
        const char *value = jbc_system_return_code();
        if (*messages) value = jbc_concat(value, jbc_concat("\376", messages));
        assign_value(returning, value);
    }
}
#endif

#ifdef JBC_SLEEP
void jbc_sleep(const char *duration, const char *file, int line, int column)
{
    struct decimal n;
    if (strchr(duration, ':'))
        numeric_error(file, line, column, "SLEEP until a clock time is unsupported");
    if (!parse_decimal(duration, &n) || n.sign < 0)
        numeric_error(file, line, column, "SLEEP requires a nonnegative duration in seconds");

    int64_t seconds = n.digits ? integer(duration, file, line, column) : 0;
    struct timespec delay = {(time_t)seconds, 0};
    if (delay.tv_sec != seconds)
        numeric_error(file, line, column, "SLEEP duration out of range");
    long place = 100000000L;
    for (size_t i = 0; i < n.places && place; ++i) {
        delay.tv_nsec += (n.fraction[i] - '0') * place;
        place /= 10;
    }
    while (delay.tv_sec || delay.tv_nsec) {
        struct timespec remaining;
        if (nanosleep(&delay, &remaining) == 0) break;
        if (errno != EINTR) numeric_error(file, line, column, "SLEEP failed");
        delay = remaining;
    }
}
#endif

#ifdef JBC_TERMINAL
#include <fcntl.h>
#include <signal.h>
#include <termios.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <unistd.h>

/* Bounded and timed reads need each keystroke before the line is submitted. */
static struct termios input_saved;
static volatile sig_atomic_t input_modified;
static int input_echo = -1;

static struct sigaction saved_interrupt;
static int break_key_disabled;

static void ignore_interrupt(int signal_number)
{
    (void)signal_number;
}

void jbc_break_key(int enabled, const char *file, int line, int column)
{
    if (enabled == !break_key_disabled) return;
    if (enabled) {
        if (sigaction(SIGINT, &saved_interrupt, NULL) < 0)
            numeric_error(file, line, column, "BREAK ON cannot restore the interrupt handler");
    } else {
        /* A caught signal resets on exec, so children keep their own SIGINT handling. */
        struct sigaction action = {0};
        action.sa_handler = ignore_interrupt;
        action.sa_flags = SA_RESTART;
        sigemptyset(&action.sa_mask);
        if (sigaction(SIGINT, &action, &saved_interrupt) < 0)
            numeric_error(file, line, column, "BREAK OFF cannot set the interrupt handler");
    }
    break_key_disabled = !enabled;
}

void jbc_echo(int enabled)
{
    input_echo = enabled;
}

void jbc_inputclear(const char *file, int line, int column)
{
    if (!isatty(STDIN_FILENO)) return;
    int result;
    do {
        result = tcflush(STDIN_FILENO, TCIFLUSH);
    } while (result < 0 && errno == EINTR);
    if (result < 0) numeric_error(file, line, column, "INPUTCLEAR cannot clear terminal input");
}

static void input_signal(int sig)
{
    if (input_modified) tcsetattr(STDIN_FILENO, TCSANOW, &input_saved);
    signal(sig, SIG_DFL);
    raise(sig);
}

int jbc_input(jbc_variable *out, const char *limit_text, int suppress_newline, int discard_excess,
              const char *timeout_text, const char *file, int line, int column)
{
    const int signals[] = {SIGINT, SIGTERM, SIGHUP, SIGQUIT, SIGPIPE};
    struct sigaction saved[sizeof signals / sizeof *signals];
    size_t handlers = 0;
    int echo_fd = -1, edit = 0;
    const char *error = NULL;
    char *text = NULL;
    size_t length = 0, capacity = 0;

    int64_t limit = limit_text ? truncated(limit_text, file, line, column) : 0;
    if (limit < 0) numeric_error(file, line, column, "negative INPUT length");
    int64_t ticks = timeout_text ? truncated(timeout_text, file, line, column) : 0;
    if (ticks < 0) numeric_error(file, line, column, "negative INPUT timeout");
    struct timespec interval = {(time_t)(ticks / 10), (long)(ticks % 10) * 100000000L};
    if (interval.tv_sec != ticks / 10) numeric_error(file, line, column, "INPUT timeout too large");
    int echo_chars = 0, ended_line = 0, timed_out = 0;
    if (!input_data && (input_echo >= 0 || jbc_hushed || suppress_newline || limit_text || timeout_text) &&
        isatty(STDIN_FILENO)) {
        if (tcgetattr(STDIN_FILENO, &input_saved) != 0)
            numeric_error(file, line, column, "cannot read input terminal settings");
        if (input_echo >= 0 || limit_text || timeout_text || (input_saved.c_lflag & (ECHO | ECHONL))) {
            int enabled = input_echo >= 0 ? input_echo : (input_saved.c_lflag & ECHO) != 0;
            echo_chars = !jbc_hushed && enabled;
            if (echo_chars || (!jbc_hushed && input_echo != 0 && !suppress_newline &&
                               (input_saved.c_lflag & ECHONL))) {
                const char *tty = ttyname(STDIN_FILENO);
                if (!tty || (echo_fd = open(tty, O_WRONLY | O_NOCTTY)) < 0)
                    numeric_error(file, line, column, "cannot echo terminal input");
            }
            struct sigaction action = {0};
            action.sa_handler = input_signal;
            sigemptyset(&action.sa_mask);
            for (; handlers < sizeof signals / sizeof *signals; ++handlers) {
                int sig = signals[handlers];
                if (sigaction(sig, NULL, &saved[handlers]) ||
                    (saved[handlers].sa_handler == SIG_DFL && sigaction(sig, &action, NULL))) {
                    error = "cannot protect input terminal settings";
                    break;
                }
            }
            struct termios mode = input_saved;
            edit = (mode.c_lflag & ICANON) != 0;
            mode.c_lflag &= ~(ICANON | ECHO | ECHONL);
            mode.c_cc[VMIN] = 1;
            mode.c_cc[VTIME] = 0;
            input_modified = 1;
            if (!error && tcsetattr(STDIN_FILENO, TCSANOW, &mode))
                error = "cannot set input terminal mode";
        }
    }
    if (!error && (fputs(jbc_input_prompt, stdout) == EOF || fflush(stdout)))
        error = "cannot write input prompt";
    while (!error && (discard_excess || !limit_text || length < (uint64_t)limit)) {
        if (!input_data && timeout_text) {
            fd_set readable;
            FD_ZERO(&readable);
            FD_SET(STDIN_FILENO, &readable);
            int ready = pselect(STDIN_FILENO + 1, &readable, NULL, NULL, &interval, NULL);
            if (ready < 0 && errno == EINTR) continue;
            if (ready < 0) { error = "cannot wait for input"; break; }
            if (!ready) { timed_out = 1; break; }
        }
        unsigned char c;
        ssize_t count = 1;
        if (input_data) {
            c = input_data->bytes[input_data->offset++];
            if (input_data->offset == input_data->length) drop_input_chunk();
        } else {
            count = read(STDIN_FILENO, &c, 1);
        }
        if (count < 0 && errno == EINTR) continue;
        if (count < 0) { error = "cannot read input"; break; }
        if (!count || (edit && c != _POSIX_VDISABLE && c == input_saved.c_cc[VEOF])) break;
        if (c == '\n') {
            ended_line = 1;
            break;
        }
        if (edit && c != _POSIX_VDISABLE && (c == input_saved.c_cc[VERASE] || c == input_saved.c_cc[VKILL])) {
            size_t keep = c == input_saved.c_cc[VKILL] || !length ? 0 : length - 1;
            while (length > keep) {
                --length;
                if (echo_chars && write(echo_fd, "\b \b", 3) != 3) error = "cannot echo terminal input";
            }
            continue;
        }
        if (discard_excess && length == (uint64_t)limit) {
            if (echo_chars && write(echo_fd, "\a", 1) != 1) error = "cannot ring INPUT bell";
            continue;
        }
        if (c == 0) { error = "INPUT cannot store a NUL byte"; break; }
        if (length == capacity) {
            if (capacity > SIZE_MAX / 2) { error = "input line too long"; break; }
            capacity = capacity ? 2 * capacity : 128;
            char *grown = realloc(text, capacity);
            if (!grown) { error = "out of memory"; break; }
            text = grown;
        }
        text[length++] = (char)c;
        if (echo_chars && write(echo_fd, &c, 1) != 1) error = "cannot echo terminal input";
    }
    if (!error && echo_fd >= 0 && !suppress_newline &&
        (ended_line || (!discard_excess && limit_text && length == (uint64_t)limit))) {
        if (write(echo_fd, "\n", 1) != 1) error = "cannot echo terminal newline";
    }
    if (input_modified && tcsetattr(STDIN_FILENO, TCSANOW, &input_saved))
        error = "cannot restore input terminal mode";
    input_modified = 0;
    while (handlers) {
        --handlers;
        sigaction(signals[handlers], &saved[handlers], NULL);
    }
    if (echo_fd >= 0) close(echo_fd);
    if (error) {
        free(text);
        numeric_error(file, line, column, error);
    }
    char *value = allocate(length);
    if (length) memcpy(value, text, length);
    value[length] = '\0';
    free(text);
    assign_value(out, value);
    return !timed_out;
}

#ifdef JBC_SESSION
const char *jbc_system(const char *code, const char *file, int line, int column)
{
    if (!jbc_compare(code, "0", -1)) return size_value(last_system_error);
    if (!jbc_compare(code, "17", -1)) return jbc_system_return_code();
    if (!jbc_compare(code, "18", -1)) return jbc_port_number(file, line, column);
    if (!jbc_compare(code, "19", -1)) return jbc_login_name();
    if (!jbc_compare(code, "24", -1)) {
        if (jbc_hushed) return "0";
        if (input_echo >= 0) return input_echo ? "1" : "0";
        struct termios mode;
        return !tcgetattr(STDIN_FILENO, &mode) && (mode.c_lflag & ECHO) ? "1" : "0";
    }
    if (!jbc_compare(code, "1036", -1)) return size_value(blocked_record_locks);
    if (jbc_compare(code, "14", -1))
        numeric_error(file, line, column, jbc_concat("unsupported SYSTEM key ", code));
    int bytes = 0;
    fflush(stdout);
    int result;
    do {
        result = ioctl(STDIN_FILENO, FIONREAD, &bytes);
    } while (result < 0 && errno == EINTR);
    if (result < 0) {
        /* Devices such as /dev/null have no input queue to inspect. */
        if (errno != ENODEV && errno != ENOTTY && errno != EOPNOTSUPP)
            numeric_error(file, line, column, "cannot query pending input bytes");
        bytes = 0;
    }

    uintmax_t pending = bytes > 0 ? (unsigned)bytes : 0;
    for (const struct input_chunk *chunk = input_data; chunk; chunk = chunk->next)
        pending += chunk->length - chunk->offset;
    return pending ? size_value(pending) : "0";
}
#endif

const char *jbc_cursor(const char *col, const char *row, const char *file, int line, int column)
{
    if (!row) {
        if (jbc_compare(col, "-1", -1) == 0) return "\033[2J\033[H";
        if (jbc_compare(col, "-2", -1) == 0) return "\033[H";
        if (jbc_compare(col, "-3", -1) == 0) return "\033[J";
        if (jbc_compare(col, "-4", -1) == 0) return "\033[K";
        numeric_error(file, line, column, "unsupported one-argument @ code");
    }
    int64_t x = truncated(col, file, line, column);
    int64_t y = truncated(row, file, line, column);
    if (x < 0 || y < 0) numeric_error(file, line, column, "negative cursor coordinate");
    /* Two uint64_t values need at most 20 decimal digits each. */
    size_t capacity = sizeof("\033[;H") + 2 * 20;
    char *out = allocate(capacity - 1);
    snprintf(out, capacity, "\033[%" PRIu64 ";%" PRIu64 "H", (uint64_t)y + 1, (uint64_t)x + 1);
    return out;
}
#endif

#ifdef JBC_REPORT
#include <sys/ioctl.h>
#include <unistd.h>


#define JBC_SCREEN (-1)
struct report_banner {
    char *text;
    const char *file;
    int line, column;
};

struct report {
    FILE *out;
    struct report_banner heading, footing;
    int64_t page;
    unsigned rows, lines, footing_lines;
    int heading_no_pause, footing_no_pause, partial_line;
};

static struct report screen, printers[128];
static int jbc_print_channel = JBC_SCREEN;

static int printer_number(const char *unit, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(unit, &n) || n.places || n.sign < 0 || n.digits > 3)
        numeric_error(file, line, column, "print unit must be an integer from 0 to 127");
    int number = (int)integer(unit, file, line, column);
    if (number > 127) numeric_error(file, line, column, "print unit must be an integer from 0 to 127");
    return number;
}

int jbc_report_channel(const char *unit, const char *file, int line, int column)
{
    if (!unit) return jbc_print_channel;
    int n = printer_number(unit, file, line, column);
    return n == 0 ? jbc_print_channel : n;
}

static unsigned report_rows(FILE *out)
{
    struct winsize size;
    return out == stdout && !ioctl(STDOUT_FILENO, TIOCGWINSZ, &size) && size.ws_row
        ? size.ws_row : 24;
}

const char *jbc_lptrhigh(void)
{
    unsigned rows = jbc_print_channel == JBC_SCREEN
        ? report_rows(stdout) : printers[jbc_print_channel].rows;
    return size_value(rows);
}

static struct report *open_report(int channel, const char *file, int line, int column)
{
    struct report *r = channel == JBC_SCREEN ? &screen : &printers[channel];
    if (r->out) return r;
    r->page = 1;
    r->rows = 24;
    if (channel == JBC_SCREEN) {
        r->out = stdout;
        r->rows = report_rows(r->out);
        return r;
    }
    const char *dir = getenv("JBCC_PRINT_DIR");
    if (!dir || !*dir) numeric_error(file, line, column, "printer output requires JBCC_PRINT_DIR");
    char suffix[32];
    snprintf(suffix, sizeof suffix, "/unit-%d-XXXXXX", channel);
    size_t length = strlen(dir);
    if (length > SIZE_MAX - sizeof suffix) fail("print directory path is too long");
    char *path = allocate(length + strlen(suffix));
    strcpy(path, dir);
    strcpy(path + length, suffix);
    int fd = mkstemp(path);
    if (fd < 0) numeric_error(file, line, column, "cannot create print job in JBCC_PRINT_DIR");
    r->out = fdopen(fd, "w");
    if (!r->out) {
        close(fd);
        unlink(path);
        numeric_error(file, line, column, "cannot open print job");
    }
    setbuf(r->out, NULL);
    return r;
}

enum printer_mode { JBC_PRINTER_ON, JBC_PRINTER_OFF, JBC_PRINTER_CLOSE, JBC_PRINTER_RESET };

static void report_footer(struct report *r);

void jbc_printer(enum printer_mode mode, const char *unit, const char *file, int line, int column)
{
    int n = unit ? printer_number(unit, file, line, column) :
        (jbc_print_channel == JBC_SCREEN ? 0 : jbc_print_channel);
    struct report *r = &printers[n];
    if (mode == JBC_PRINTER_ON) {
        open_report(n, file, line, column);
        jbc_print_channel = n;
    } else if (mode == JBC_PRINTER_OFF) {
        if (!unit || n == jbc_print_channel) jbc_print_channel = JBC_SCREEN;
    } else {
        if (mode == JBC_PRINTER_CLOSE) {
            if (n == jbc_print_channel) jbc_print_channel = JBC_SCREEN;
            if (r->out) report_footer(r);
            if (r->out && fclose(r->out)) numeric_error(file, line, column, "cannot close print job");
            r->out = NULL;
        }
        free(r->heading.text);
        free(r->footing.text);
        FILE *out = r->out;
        *r = (struct report){.out = out, .page = 1, .rows = 24};
    }
}

static void report_char(struct report *r, int ch)
{
    if (r->out) fputc(ch, r->out);
    r->partial_line = ch != '\n';
    if (ch == '\n' && r->lines < UINT_MAX) ++r->lines;
}

static int render_banner(struct report *r, const struct report_banner *banner, const char *kind)
{
    const char *p = banner->text;
    if (!p) return 0;
    if ((unsigned char)*p == 254) ++p;
    int pending_line = 0;
    int no_pause = 0;
    while (*p) {
        if (*p == '\'' || *p == '"') {
            char quote = *p++;
            if (*p == quote) {
                report_char(r, *p++);
                pending_line = 1;
                continue;
            }
            while (*p && *p != quote) {
                switch (*p++) {
                case 'N': no_pause = 1; break;
                case 'L': report_char(r, '\n'); pending_line = 0; break;
                case 'P': {
                    int padded = *p == 'P';
                    if (padded) ++p;
                    if (r->out) fprintf(r->out, "%*" PRId64, padded ? 4 : 1, r->page);
                    pending_line = 1;
                    break;
                }
                case 'D': {
                    if (r->out) {
                        const char *date = jbc_date(banner->file, banner->line, banner->column);
                        fputs(jbc_oconv(date, "D", banner->file, banner->line, banner->column), r->out);
                    }
                    pending_line = 1;
                    break;
                }
                case 'T':
                    if (r->out) fputs(jbc_timedate(banner->file, banner->line, banner->column), r->out);
                    pending_line = 1;
                    break;
                default:
                    goto invalid_option;
                }
            }
            if (!*p)
                numeric_error(banner->file, banner->line, banner->column,
                              jbc_concat("unterminated ", jbc_concat(kind, " option")));
            ++p;
        } else if (*p == '^') {
            int padded = *++p == '^';
            if (padded) ++p;
            if (r->out) fprintf(r->out, "%*" PRId64, padded ? 4 : 1, r->page);
            pending_line = 1;
        } else {
            int ch = (unsigned char)*p++;
            if (ch == ']') ch = '\n';
            if (ch == '\\') goto invalid_option;
            report_char(r, ch);
            pending_line = ch != '\n';
        }
    }
    if (pending_line) report_char(r, '\n');
    return no_pause;

invalid_option:
    numeric_error(banner->file, banner->line, banner->column,
                  jbc_concat("unsupported ", jbc_concat(kind, " option")));
    return 0;
}

static unsigned report_body_limit(const struct report *r)
{
    return r->rows > r->footing_lines ? r->rows - r->footing_lines : 1;
}

static void report_title(struct report *r)
{
    if (!r->heading.text) return;
    r->heading_no_pause = render_banner(r, &r->heading, "HEADING");
    /* Leave room for one body line even if the title fills the screen. */
    unsigned limit = report_body_limit(r);
    if (r->lines >= limit) r->lines = limit - 1;
}

static void report_footer(struct report *r)
{
    if (!r->footing_lines || (!r->lines && !r->partial_line)) return;
    if (r->partial_line) report_char(r, '\n');
    unsigned limit = report_body_limit(r);
    while (r->lines < limit) report_char(r, '\n');
    render_banner(r, &r->footing, "FOOTING");
    if (ferror(r->out))
        numeric_error(r->footing.file, r->footing.line, r->footing.column, "report write failed");
}

static void finish_reports(void)
{
    if (screen.out) report_footer(&screen);
    free(screen.heading.text);
    free(screen.footing.text);
    for (size_t i = 0; i < sizeof printers / sizeof printers[0]; ++i) {
        if (printers[i].out) report_footer(&printers[i]);
        free(printers[i].heading.text);
        free(printers[i].footing.text);
    }
}

static void report_break(struct report *r, int64_t next_page)
{
    report_footer(r);
    if (r->out == stdout && (r->heading.text || r->footing.text) &&
        !r->heading_no_pause && !r->footing_no_pause && isatty(STDIN_FILENO) && isatty(STDOUT_FILENO)) {
        fflush(stdout);
        char ch;
        for (;;) {
            ssize_t count = read(STDIN_FILENO, &ch, 1);
            if (count < 0 && errno == EINTR) continue;
            if (count <= 0 || ch == '\n') break;
        }
    }
    fputc('\f', r->out);
    r->lines = 0;
    r->partial_line = 0;
    r->page = next_page;
    report_title(r);
}

static int64_t next_report_page(const struct report *r)
{
    if (r->page == INT64_MAX) fail("page number overflow");
    return r->page + 1;
}

void jbc_page(const char *unit, const char *number, const char *file, int line, int column)
{
    struct report *r = open_report(jbc_report_channel(unit, file, line, column), file, line, column);
    int64_t next_page;
    if (number) {
        struct decimal value;
        if (!parse_decimal(number, &value) || value.places)
            numeric_error(file, line, column, "PAGE requires an integer page number");
        next_page = integer(number, file, line, column);
    } else next_page = next_report_page(r);
    report_break(r, next_page);
    if (ferror(r->out)) numeric_error(file, line, column, "report write failed");
}

void jbc_heading(const char *unit, const char *heading, int no_eject, const char *file, int line, int column)
{
    struct report *r = open_report(jbc_report_channel(unit, file, line, column), file, line, column);
    int first = !r->heading.text;
    char *copy = record_copy(heading);
    free(r->heading.text);
    r->heading = (struct report_banner){copy, file, line, column};
    r->rows = report_rows(r->out);
    if (first && !r->footing.text) {
        r->lines = 0;
        r->partial_line = 0;
    }
    if ((unsigned char)*heading == 254) return;
    if (first) report_title(r);
    else if (!no_eject) report_break(r, next_report_page(r));
    if (ferror(r->out)) numeric_error(file, line, column, "report write failed");
}

void jbc_footing(const char *unit, const char *footing, const char *file, int line, int column)
{
    struct report *r = open_report(jbc_report_channel(unit, file, line, column), file, line, column);
    char *copy = *footing ? record_copy(footing) : NULL;
    free(r->footing.text);
    r->footing = (struct report_banner){copy, file, line, column};
    r->rows = report_rows(r->out);
    /* Count template lines without writing or evaluating date and time options. */
    struct report measure = {0};
    r->footing_no_pause = render_banner(&measure, &r->footing, "FOOTING");
    r->footing_lines = measure.lines;
}

void jbc_output(int channel, const char *text, const char *file, int line, int column)
{
    struct report *r = open_report(channel, file, line, column);
    if (channel == JBC_SCREEN && jbc_print_channel != JBC_SCREEN) {
        fputs(text, r->out);
    } else {
        while (*text) {
            if ((r->heading.text || r->footing.text) && r->lines >= report_body_limit(r))
                report_break(r, next_report_page(r));
            report_char(r, (unsigned char)*text++);
        }
    }
    if (ferror(r->out)) numeric_error(file, line, column, "report write failed");
}
#else
#define JBC_SCREEN (-1)
#define jbc_print_channel JBC_SCREEN
#define jbc_output(channel, text, file, line, column) ((void)(channel), fputs((text), stdout))
#endif

#ifdef JBC_SEQUENTIAL
#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <termios.h>
#include <unistd.h>

enum sequential_buffering { SEQ_PRISTINE, SEQ_USED, SEQ_UNBUFFERED };
enum sequential_access { SEQ_READ_WRITE, SEQ_READ_ONLY, SEQ_WRITE_ONLY };

/* The immutable token is shared by scalar aliases. Only its address identifies
   the handle. A pending handle remembers a missing file until the first write. */
struct sequential_file {
    struct sequential_file *next;
    const char *token;
    FILE *stream;
    enum sequential_buffering buffering;
    enum sequential_access access;
    unsigned depth;
};
static struct sequential_file *sequential_files;
static unsigned seq_depth;

static struct sequential_file **sequential_slot(const char *token)
{
    struct sequential_file **slot = &sequential_files;
    while (*slot && (*slot)->token != token) slot = &(*slot)->next;
    return slot;
}

static FILE *sequential_stream(struct sequential_file *file)
{
    if (file->buffering == SEQ_PRISTINE) file->buffering = SEQ_USED;
    return file->stream;
}

static int release_sequential(const char *token)
{
    struct sequential_file **slot = sequential_slot(token), *file = *slot;
    if (!file) return 0;
    *slot = file->next;
    int result = file->stream ? fclose(file->stream) : 0;
    free(file);
    return result;
}

/* Returning routines transfer handles in result, reference arguments and
   persistent storage to their caller. Local-only handles release their lock. */
void jbc_leave_sequential(const char ***roots)
{
    struct sequential_file *file = sequential_files;
    while (file && file->depth == seq_depth) {
        struct sequential_file *next = file->next;
        const char ***root = roots;
        while (*root && **root != file->token) ++root;
        if (*root || held_in_storage(file->token)) --file->depth;
        else release_sequential(file->token);
        file = next;
    }
    --seq_depth;
}

void jbc_seq_setting(jbc_variable *out, int status)
{
    assign_value(out, file_status_value(status));
}

static const char *os_search_path(const char *path, int error)
{
    if (file_error(error) != 128 || strchr(path, '/') || !*path) return NULL;
    return getenv("JEDIFILEPATH");
}

static const char *next_os_path(const char *path, const char **directories)
{
    while (*directories && **directories) {
        const char *dir = take_field(directories, ':');
        if (*dir) return jbc_concat(jbc_concat(dir, "/"), path);
    }
    return NULL;
}

static int open_os_file(const char **name, int flags)
{
    const char *path = *name;
    int fd = open(path, flags);
    if (fd >= 0) return fd;
    int error = errno;
    const char *directories = os_search_path(path, error);
    const char *candidate;
    while ((candidate = next_os_path(path, &directories))) {
        fd = open(candidate, flags);
        if (fd >= 0) {
            *name = candidate;
            return fd;
        }
        error = errno;
        if (file_error(error) != 128) break;
    }
    errno = error;
    return -1;
}

static int open_sequential(const char **path, enum sequential_access access, int create,
                           int append, int search_path, FILE **out)
{
    int flags = access == SEQ_READ_ONLY ? O_RDONLY : access == SEQ_WRITE_ONLY ? O_WRONLY : O_RDWR;
    const char *mode = access == SEQ_READ_ONLY ? "rb" : access == SEQ_WRITE_ONLY ? "wb" : "r+b";
    if (create) flags |= O_CREAT | O_EXCL;
    flags |= O_NONBLOCK | O_NOCTTY | O_CLOEXEC;
    int fd = search_path ? open_os_file(path, flags) : open(*path, flags, 0666);
    if (fd < 0) return file_error(errno);
    struct stat st;
    int status = 0;
    if (fstat(fd, &st) < 0) status = 32768;
    else if (S_ISREG(st.st_mode)) {
        if (flock(fd, (access == SEQ_READ_ONLY ? LOCK_SH : LOCK_EX) | LOCK_NB) < 0)
            status = errno == EWOULDBLOCK ? JBC_LOCKED : file_error(errno);
    } else if (search_path || !S_ISCHR(st.st_mode) || !isatty(fd)) status = 32768;
    if (!status && append && lseek(fd, 0, SEEK_END) < 0) status = file_error(errno);
    if (!status && !(*out = fdopen(fd, mode))) status = file_error(errno);
    if (status) close(fd);
    return status;
}

int jbc_openseq(const char *path, const char *name, int existing, int append,
                enum sequential_access access, int search_path, jbc_variable *out)
{
    if (name) path = jbc_concat(jbc_concat(path, "/"), name);
    FILE *stream = NULL;
    int status = open_sequential(&path, access, 0, append, search_path, &stream);
    assign_value(out, "");
    if (status && (status != 128 || existing || access == SEQ_READ_ONLY)) return file_result(status);
    struct sequential_file *file = malloc(sizeof *file);
    if (!file) fail("out of memory");
    file->token = strcpy(allocate(strlen(path)), path);
    file->depth = seq_depth;
    file->access = access;
    file->stream = stream;
    file->buffering = SEQ_PRISTINE;
    file->next = sequential_files;
    sequential_files = file;
    assign_value(out, file->token);
    return file_result(status);
}

static const speed_t tty_rates[] = {B50, B75, B110, B134, B150, B200, B300, B600,
                                    B1200, B1800, B2400, B4800, B9600, B19200, B38400};
static const tcflag_t tty_data_sizes[] = {CS5, CS6, CS7, CS8};

static const char *tty_baud_code(speed_t speed)
{
    for (size_t i = 0; i < sizeof tty_rates / sizeof *tty_rates; ++i)
        if (tty_rates[i] == speed) return size_value(i + 1);
    return "";
}

int jbc_ttyget(const char *token, jbc_variable *out)
{
    const struct sequential_file *file = *sequential_slot(token);
    assign_value(out, "");
    if (!file || !file->stream) return file_result(128);

    struct termios mode;
    if (tcgetattr(fileno(file->stream), &mode) < 0) return file_result(file_error(errno));
    tcflag_t control = mode.c_cflag;
    tcflag_t local = mode.c_lflag;
    tcflag_t input = mode.c_iflag;
    int bits = 5;
    while (bits < 8 && (control & CSIZE) != tty_data_sizes[bits - 5]) ++bits;
    int canonical = (local & ICANON) != 0;
    int minimum = canonical ? 0 : mode.c_cc[VMIN];
    int timeout_ms = canonical ? 0 : mode.c_cc[VTIME] * 100;
    int parity = !(control & PARENB) ? 0 : (control & PARODD) ? 2 : 1;
    int break_key = (input & IGNBRK) ? 0 : (input & BRKINT) ? 1 : 2;
    const char *baud = tty_baud_code(cfgetospeed(&mode));

    /* Populate the supported values in fields 1, 7, 10 and 11. */
    char settings[128];
    snprintf(settings, sizeof settings,
             "%d\375%d\375%d\376\376\376\376\376\376%d"
             "\376\376\376\375%s\375%d\375%d\375%d\376%d\375\375%d",
             !canonical, minimum, timeout_ms, (local & ECHO) != 0,
             baud, bits, (control & CSTOPB) ? 2 : 1, parity,
             (local & ISIG) != 0, break_key);
    assign_value(out, strcpy(allocate(strlen(settings)), settings));
    return file_result(0);
}

enum tty_setting {
    TTY_UNSUPPORTED, TTY_MODE, TTY_MINIMUM, TTY_TIME, TTY_ECHO, TTY_BAUD,
    TTY_DATA, TTY_STOP, TTY_PARITY, TTY_SIGNALS, TTY_BREAK, TTY_SETTING_COUNT
};

static int parse_tty_settings(const char *text, int settings[TTY_SETTING_COUNT])
{
    /* Rows are attribute positions and columns are value positions. */
    static const enum tty_setting slots[11][5] = {
        [0] = {TTY_MODE, TTY_MINIMUM, TTY_TIME},
        [6] = {TTY_ECHO},
        [9] = {TTY_UNSUPPORTED, TTY_BAUD, TTY_DATA, TTY_STOP, TTY_PARITY},
        [10] = {TTY_SIGNALS, TTY_UNSUPPORTED, TTY_BREAK}
    };
    static const int maxima[TTY_SETTING_COUNT] = {
        [TTY_MODE] = 1, [TTY_MINIMUM] = 255, [TTY_TIME] = 25500, [TTY_ECHO] = 1,
        [TTY_BAUD] = sizeof tty_rates / sizeof *tty_rates, [TTY_DATA] = 8,
        [TTY_STOP] = 2, [TTY_PARITY] = 2, [TTY_SIGNALS] = 1, [TTY_BREAK] = 2
    };
    for (int i = 0; i < TTY_SETTING_COUNT; ++i) settings[i] = -1;

    size_t field = 0, value = 0;
    int found = 0;
    while (*text) {
        const char *end = text + strcspn(text, "\376\375");
        if (end != text) {
            if (field >= sizeof slots / sizeof *slots ||
                value >= sizeof *slots / sizeof **slots) return 0;
            enum tty_setting slot = slots[field][value];
            if (slot == TTY_UNSUPPORTED) return 0;
            int n = 0;
            while (text < end) {
                if (*text < '0' || *text > '9') return 0;
                n = n * 10 + (*text++ - '0');
                if (n > maxima[slot]) return 0;
            }
            settings[slot] = n;
            found = 1;
        }
        if (!*end) break;
        if ((unsigned char)*end == 254) {
            ++field;
            value = 0;
        } else ++value;
        text = end + 1;
    }
    return found;
}

static void tty_set_flag(tcflag_t *flags, tcflag_t mask, int enabled)
{
    if (enabled) *flags |= mask;
    else *flags &= ~mask;
}

int jbc_ttyset(const char *token, const char *text)
{
    const struct sequential_file *file = *sequential_slot(token);
    if (!file || !file->stream) return file_result(128);
    int fd = fileno(file->stream);
    struct termios before;
    if (tcgetattr(fd, &before) < 0) return file_result(file_error(errno));

    int s[TTY_SETTING_COUNT];
    if (!parse_tty_settings(text, s) || s[TTY_BAUD] == 0 ||
        (s[TTY_DATA] >= 0 && s[TTY_DATA] < 5) || s[TTY_STOP] == 0 ||
        (s[TTY_TIME] >= 0 && s[TTY_TIME] % 100)) return file_result(32768);

    struct termios next = before;
    if (s[TTY_MODE] >= 0) tty_set_flag(&next.c_lflag, ICANON, s[TTY_MODE] == 0);
    int canonical = (next.c_lflag & ICANON) != 0;
    if (canonical && (s[TTY_MINIMUM] > 0 || s[TTY_TIME] > 0)) return file_result(32768);
    if (!canonical && s[TTY_MINIMUM] >= 0) next.c_cc[VMIN] = (cc_t)s[TTY_MINIMUM];
    if (!canonical && s[TTY_TIME] >= 0) next.c_cc[VTIME] = (cc_t)(s[TTY_TIME] / 100);
    if (s[TTY_ECHO] >= 0) tty_set_flag(&next.c_lflag, ECHO, s[TTY_ECHO]);
    if (s[TTY_SIGNALS] >= 0) tty_set_flag(&next.c_lflag, ISIG, s[TTY_SIGNALS]);
    if (s[TTY_BREAK] >= 0) {
        tty_set_flag(&next.c_iflag, IGNBRK, s[TTY_BREAK] == 0);
        tty_set_flag(&next.c_iflag, BRKINT, s[TTY_BREAK] == 1);
    }
    if (s[TTY_DATA] >= 0) next.c_cflag = (next.c_cflag & ~CSIZE) | tty_data_sizes[s[TTY_DATA] - 5];
    if (s[TTY_STOP] >= 0) tty_set_flag(&next.c_cflag, CSTOPB, s[TTY_STOP] == 2);
    if (s[TTY_PARITY] >= 0) {
        tty_set_flag(&next.c_cflag, PARENB, s[TTY_PARITY] != 0);
        tty_set_flag(&next.c_cflag, PARODD, s[TTY_PARITY] == 2);
    }
    if (s[TTY_BAUD] > 0) {
        speed_t rate = tty_rates[s[TTY_BAUD] - 1];
        if (cfsetispeed(&next, rate) || cfsetospeed(&next, rate)) return file_result(file_error(errno));
    }

    if (tcsetattr(fd, TCSANOW, &next) < 0) return file_result(file_error(errno));
    /* POSIX allows success even when the driver applies only some settings. */
    struct termios actual;
    tcflag_t control_mask = CSIZE | CSTOPB | PARENB;
    if (next.c_cflag & PARENB) control_mask |= PARODD;
    if (tcgetattr(fd, &actual) < 0 ||
        ((next.c_cflag ^ actual.c_cflag) & control_mask) ||
        ((next.c_lflag ^ actual.c_lflag) & (ICANON | ECHO | ISIG)) ||
        ((next.c_iflag ^ actual.c_iflag) & (IGNBRK | BRKINT)) ||
        (!canonical && (next.c_cc[VMIN] != actual.c_cc[VMIN] ||
                        next.c_cc[VTIME] != actual.c_cc[VTIME])) ||
        (s[TTY_BAUD] > 0 && (cfgetispeed(&next) != cfgetispeed(&actual) ||
                            cfgetospeed(&next) != cfgetospeed(&actual)))) {
        (void)tcsetattr(fd, TCSANOW, &before);
        return file_result(32768);
    }
    return file_result(0);
}

int jbc_osread(const char *path, jbc_variable *out)
{
    assign_value(out, "");
    int fd = open_os_file(&path, O_RDONLY | O_NONBLOCK | O_NOCTTY | O_CLOEXEC);
    if (fd < 0) return file_result(file_error(errno));

    struct stat st;
    int status = 0;
    const size_t limit = SIZE_MAX - sizeof(struct jbc_buffer) - 1;
    size_t length = 0, capacity = 0;
    char *contents = NULL;
    if (fstat(fd, &st) < 0) status = file_error(errno);
    else if (!S_ISREG(st.st_mode)) status = 32768;
    while (!status) {
        char block[4096];
        ssize_t count = read(fd, block, sizeof block);
        if (count < 0 && errno == EINTR) continue;
        if (count < 0) {
            status = file_error(errno);
            break;
        }
        if (!count) break;
        size_t added = (size_t)count;
        if (added > limit - length) {
            status = 32768;
            break;
        }
        size_t needed = length + added;
        if (needed > capacity) {
            size_t grown = needed <= limit / 2 ? 2 * needed : needed;
            char *larger = realloc(contents, grown);
            if (!larger) {
                status = 32768;
                break;
            }
            contents = larger;
            capacity = grown;
        }
        memcpy(contents + length, block, added);
        length = needed;
    }
    if (close(fd) && !status) status = file_error(errno);

    if (!status && length) {
        if (contents[length - 1] == '\n') --length;
        char *value = allocate(length);
        for (size_t i = 0; i < length; ++i)
            value[i] = contents[i] ? contents[i] : (char)128;
        value[length] = '\0';
        assign_value(out, value);
    }
    free(contents);
    return file_result(status);
}

int jbc_readseq(const char *token, jbc_variable *out)
{
    struct sequential_file *file = *sequential_slot(token);
    assign_value(out, "");
    if (!file || !file->stream) return file_result(128);
    if (file->access == SEQ_WRITE_ONLY) return file_result(24576);
    FILE *in = sequential_stream(file);
    char record[1024];
    size_t length = 0;
    int ch, binary = 0;
    while ((ch = fgetc(in)) != EOF && ch != '\n') {
        if (ch == 0) binary = 1;
        if (length < sizeof record) record[length++] = (char)ch;
    }
    if (ferror(in) || binary) return file_result(32768);
    if (ch == EOF && !length) return file_result(128);
    char *value = allocate(length);
    memcpy(value, record, length);
    value[length] = '\0';
    assign_value(out, value);
    return file_result(0);
}

static int parse_byte_offset(const char *value, off_t *position)
{
    struct decimal n;
    if (!parse_decimal(value, &n) || n.sign < 0 || n.places) return 0;
    errno = 0;
    intmax_t number = strtoimax(value, NULL, 10);
    *position = (off_t)number;
    return !errno && (intmax_t)*position == number;
}

static int read_sequential_block(FILE *in, uintmax_t requested, int os_block, jbc_variable *out)
{
    if (!requested) return 0;
    off_t position = ftello(in);
    struct stat info;
    if (position < 0 || fstat(fileno(in), &info)) return file_error(errno);
    if (position >= info.st_size) return os_block ? 0 : 128;
    /* Bound allocation by the bytes left in an open regular file. */
    uintmax_t remaining = (uintmax_t)(info.st_size - position);
    size_t amount = (size_t)(remaining < requested ? remaining : requested);
    if (amount >= SIZE_MAX - sizeof(struct jbc_buffer)) return 32768;
    char *value = allocate(amount);
    size_t length = fread(value, 1, amount, in);
    if (ferror(in)) return file_error(errno);
    if (os_block) {
        for (size_t i = 0; i < length; ++i)
            if (!value[i]) value[i] = (char)128;
    } else {
        if (length != requested) return 128;
        if (memchr(value, '\0', length)) return 32768;
    }
    value[length] = '\0';
    assign_value(out, value);
    return 0;
}

int jbc_readblk(const char *token, const char *size, jbc_variable *out,
                const char *source, int line, int column)
{
    if (!*token || !*size)
        numeric_error(source, line, column, "READBLK requires nonempty handle and block size");
    struct decimal n;
    if (!parse_decimal(size, &n) || n.sign <= 0 || n.places)
        numeric_error(source, line, column, "READBLK requires a positive integer block size");
    errno = 0;
    uintmax_t requested = strtoumax(size, NULL, 10);
    if (errno || requested > SIZE_MAX)
        numeric_error(source, line, column, "READBLK block size out of range");

    struct sequential_file *file = *sequential_slot(token);
    assign_value(out, "");
    if (!file || !file->stream) return file_result(128);
    if (file->access == SEQ_WRITE_ONLY) return file_result(24576);
    FILE *in = sequential_stream(file);
    return file_result(read_sequential_block(in, requested, 0, out));
}

int jbc_osbread(const char *token, const char *offset, const char *size, jbc_variable *out)
{
    assign_value(out, "");
    struct sequential_file *file = *sequential_slot(token);
    if (!file || !file->stream) return file_result(128);
    if (file->access == SEQ_WRITE_ONLY) return file_result(24576);

    struct decimal n;
    if (!parse_decimal(size, &n) || n.sign < 0 || n.places) return file_result(32768);
    errno = 0;
    uintmax_t requested = strtoumax(size, NULL, 10);
    if (errno || requested > SIZE_MAX) return file_result(32768);

    off_t position = 0;
    if (offset && !parse_byte_offset(offset, &position)) return file_result(32768);
    FILE *in = sequential_stream(file);
    if (offset && fseeko(in, position, SEEK_SET)) return file_result(file_error(errno));
    clearerr(in);
    return file_result(read_sequential_block(in, requested, 1, out));
}

static int writable_sequential(struct sequential_file *file)
{
    if (!file) return 128;
    if (file->access == SEQ_READ_ONLY) return 24576;
    if (file->stream) return 0;
    return open_sequential(&file->token, file->access, 1, 0, 0, &file->stream);
}

static int write_os_bytes(FILE *out, const char *value)
{
    size_t remaining = strlen(value);
    while (remaining) {
        unsigned char bytes[4096];
        size_t length = remaining < sizeof bytes ? remaining : sizeof bytes;
        for (size_t i = 0; i < length; ++i) {
            unsigned char byte = (unsigned char)value[i];
            bytes[i] = byte == 128 ? 0 : byte;
        }
        if (fwrite(bytes, 1, length, out) != length) return file_error(errno);
        value += length;
        remaining -= length;
    }
    return fflush(out) ? file_error(errno) : 0;
}

int jbc_osbwrite(const char *token, const char *offset, const char *value, int nodelay)
{
    struct sequential_file *file = *sequential_slot(token);
    if (!file || !file->stream) return file_result(128);
    if (file->access == SEQ_READ_ONLY) return file_result(24576);

    off_t position = 0;
    if (offset && !parse_byte_offset(offset, &position)) return file_result(32768);
    FILE *out = sequential_stream(file);
    /* Positioning also synchronizes stdio after a buffered read. */
    if (fseeko(out, position, offset ? SEEK_SET : SEEK_CUR)) return file_result(file_error(errno));
    clearerr(out);
    int status = write_os_bytes(out, value);
    if (!status && nodelay && fsync(fileno(out))) status = file_error(errno);
    return file_result(status);
}

int jbc_oswrite(const char *path, const char *value, int append)
{
    int flags = O_WRONLY | O_NONBLOCK | O_NOCTTY | O_CLOEXEC;
    if (append) flags |= O_APPEND;
    int fd = open_os_file(&path, flags);
    if (fd < 0 && file_error(errno) == 128) fd = open(path, flags | O_CREAT, 0666);
    if (fd < 0) return file_result(file_error(errno));

    struct stat info;
    int status = 0;
    FILE *out = NULL;
    if (fstat(fd, &info) < 0) status = file_error(errno);
    else if (!S_ISREG(info.st_mode)) status = 32768;
    else if (flock(fd, LOCK_EX | LOCK_NB) < 0)
        status = errno == EWOULDBLOCK ? JBC_LOCKED : file_error(errno);
    else if (!(out = fdopen(fd, append ? "ab" : "wb"))) status = file_error(errno);
    if (!out) {
        close(fd);
        return file_result(status);
    }

    if (!append && ftruncate(fd, 0)) status = file_error(errno);
    if (!status) status = write_os_bytes(out, value);
    if (fclose(out) && !status) status = file_error(errno);
    return file_result(status);
}

int jbc_osdelete(const char *path)
{
    if (unlink(path) == 0) return file_result(0);

    const char *directories = os_search_path(path, errno);
    const char *candidate;
    while ((candidate = next_os_path(path, &directories))) {
        if (unlink(candidate) == 0) return file_result(0);
        if (file_error(errno) != 128) break;
    }
    return file_result(1);
}

int jbc_createseq(const char *token, const char *source, int line, int column)
{
    if (!*token) numeric_error(source, line, column, "CREATE requires an OPENSEQ handle");
    struct sequential_file *file = *sequential_slot(token);
    if (file && file->stream) return file_result(32768);
    return file_result(writable_sequential(file));
}

int jbc_seek(const char *token, const char *offset, const char *origin,
             const char *source, int line, int column)
{
    if (!*token || !*offset || !*origin)
        numeric_error(source, line, column, "SEEK requires nonempty handle, offset and origin");
    struct sequential_file *file = *sequential_slot(token);
    if (!file || !file->stream) return file_result(128);
    struct decimal n;
    if (!parse_decimal(origin, &n) || n.places || n.sign < 0 || n.digits > 1)
        return file_result(32768);
    int relative = n.digits ? *n.whole - '0' : 0;
    if (relative > 2 || !parse_decimal(offset, &n) || n.places) return file_result(32768);
    errno = 0;
    intmax_t delta = strtoimax(offset, NULL, 10);
    if (errno) return file_result(32768);

    FILE *stream = sequential_stream(file);
    off_t base = 0;
    if (relative == 1) {
        base = ftello(stream);
        if (base < 0) return file_result(file_error(errno));
    } else if (relative == 2) {
        struct stat st;
        if (fstat(fileno(stream), &st)) return file_result(file_error(errno));
        base = st.st_size;
    }
    if (delta < -(intmax_t)base || delta > INTMAX_MAX - base) return file_result(32768);
    intmax_t target = base + delta;
    if ((off_t)target != target) return file_result(32768);
    return file_result(fseeko(stream, (off_t)target, SEEK_SET) ? file_error(errno) : 0);
}

int jbc_flushseq(const char *token, const char *source, int line, int column)
{
    if (!*token) numeric_error(source, line, column, "FLUSH requires an OPENSEQ handle");
    struct sequential_file *file = *sequential_slot(token);
    if (!file || !file->stream) return file_result(128);
    return file_result(fflush(sequential_stream(file)) ? file_error(errno) : 0);
}

void jbc_timeout(const char *token, const char *seconds, const char *source, int line, int column)
{
    const struct sequential_file *file = *sequential_slot(token);
    if (!file || !file->stream)
        numeric_error(source, line, column, "TIMEOUT requires an open sequential handle");

    struct decimal duration;
    if (!parse_decimal(seconds, &duration) || duration.sign < 0)
        numeric_error(source, line, column, "TIMEOUT requires nonnegative decimal seconds");
    if (isatty(fileno(file->stream)))
        numeric_error(source, line, column, "TIMEOUT is unavailable on terminal handles");

    /* Regular files return data or EOF without waiting for incoming bytes. */
}

int jbc_nobuf(const char *token)
{
    struct sequential_file *file = *sequential_slot(token);
    if (!file || !file->stream) return file_result(128);
    if (file->buffering == SEQ_UNBUFFERED) return file_result(0);
    /* C only permits changing the buffering before using the stream. */
    if (file->buffering == SEQ_USED || setvbuf(file->stream, NULL, _IONBF, 0))
        return file_result(32768);
    file->buffering = SEQ_UNBUFFERED;
    return file_result(0);
}

int jbc_weofseq(const char *token)
{
    struct sequential_file *file = *sequential_slot(token);
    int status = writable_sequential(file);
    if (status) return file_result(status);
    FILE *out = sequential_stream(file);
    /* Discard prefetched input so a later READSEQ sees the new EOF. */
    off_t position = ftello(out);
    if (position < 0 || fflush(out) || ftruncate(fileno(out), position) ||
        fseeko(out, position, SEEK_SET)) return file_result(file_error(errno));
    return file_result(0);
}

static int write_sequential(const char *token, const char *value, int append, int flush, int newline)
{
    struct sequential_file *file = *sequential_slot(token);
    if (!newline && (!file || !file->stream)) return 128;
    int status = writable_sequential(file);
    if (status) return status;
    FILE *out = sequential_stream(file);
    /* Positioning synchronizes stdio after a buffered read. */
    if (fseeko(out, 0, append ? SEEK_END : SEEK_CUR) ||
        fputs(value, out) == EOF || (newline && fputc('\n', out) == EOF) || fflush(out))
        return file_error(errno);
    if (flush && fsync(fileno(out))) return file_error(errno);
    return 0;
}

int jbc_writeseq(const char *token, const char *value, int append, int flush)
{
    return file_result(write_sequential(token, value, append, flush, 1));
}

int jbc_writeblk(const char *token, const char *value, const char *source, int line, int column)
{
    if (!*token || !*value)
        numeric_error(source, line, column, "WRITEBLK requires nonempty handle and data");
    return file_result(write_sequential(token, value, 0, 0, 0));
}

int jbc_closeseq(jbc_variable *slot)
{
    if (!*sequential_slot(slot->value)) return file_succeeded(128);
    int status = release_sequential(slot->value);
    assign_value(slot, "");
    return file_succeeded(status ? 32768 : 0);
}
#endif

/* STATUS attributes use their one-based jBC positions. */
enum { STATUS_ATTRIBUTES = 24 };

#ifdef JBC_SEQUENTIAL
static int status_timestamp(jbc_variable *attrs, time_t stamp)
{
    struct tm t;
    if (!localtime_r(&stamp, &t) || t.tm_year < 1 - 1900 || t.tm_year > 9999 - 1900)
        return 32768;
    attrs[0].value = size_value(t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec);
    attrs[1].value = internal_date(t.tm_year + 1900, t.tm_yday + 1);
    return 0;
}

static const char *sequential_path(const char *path)
{
    if (*path == '/') return path;
    const char *cwd = working_directory();
    if (!cwd) return NULL;
    const char *separator = strcmp(cwd, "/") ? "/" : "";
    return jbc_concat(jbc_concat(cwd, separator), path);
}

static int sequential_status(const char *handle, jbc_variable *attrs)
{
    struct sequential_file *file = *sequential_slot(handle);
    if (!file || !file->stream) return 128;
    FILE *stream = sequential_stream(file);
    struct stat st;
    if (fstat(fileno(stream), &st)) return file_error(errno);
    off_t pos = ftello(stream);
    if (pos < 0) return file_error(errno);

    attrs[1].value = size_value((uintmax_t)pos);
    attrs[2].value = feof(stream) ? "1" : "0";
    attrs[3].value = ferror(stream) ? "1" : "0";
    attrs[4].value = size_value(pos < st.st_size ? (uintmax_t)(st.st_size - pos) : 0);
    char *mode = allocate(4);
    snprintf(mode, 5, "%o", (unsigned)st.st_mode & 07777);
    attrs[5].value = mode;
    attrs[6].value = size_value((uintmax_t)st.st_size);
    attrs[7].value = size_value(st.st_nlink);
    attrs[8].value = size_value(st.st_uid);
    attrs[9].value = size_value(st.st_gid);
    attrs[10].value = size_value(st.st_ino);
    attrs[11].value = size_value(st.st_dev);
    attrs[12].value = size_value(st.st_rdev);
    if (status_timestamp(attrs + 13, st.st_atime) ||
        status_timestamp(attrs + 15, st.st_mtime) ||
        status_timestamp(attrs + 17, st.st_ctime)) return 32768;
    attrs[19].value = "0";
    attrs[20].value = sequential_path(file->token);
    if (!attrs[20].value) return file_error(errno);
    attrs[21].value = "SEQ";
    return 0;
}
#endif

int jbc_file_status(const char *handle, jbc_variable *out, jbc_variable *setting,
                    const char *source, int line, int column)
{
    if (!*handle) numeric_error(source, line, column, "STATUS requires a nonempty file descriptor");
    jbc_variable attrs[STATUS_ATTRIBUTES + 1] = {{0}};
    for (int i = 1; i <= STATUS_ATTRIBUTES; ++i) attrs[i].value = "";
    struct memory_file *file = file_for(handle);
    int status = 128;
    if (file) {
        size_t bytes = 0;
        for (struct memory_record *r = file->records; r; r = r->next) bytes += strlen(r->value);
        attrs[6].value = size_value(bytes);
        attrs[20].value = file->name;
        attrs[21].value = "MEMORY";
        status = 0;
    }
#ifdef JBC_SEQUENTIAL
    else status = sequential_status(handle, attrs);
#endif
    const int bounds[] = {STATUS_ATTRIBUTES};
    const char *value = status ? "" : jbc_matbuild(attrs, 1, bounds, NULL, NULL, "\376", "STATUS",
                                                   source, line, column);
    assign_value(out, value);
    if (setting) assign_value(setting, size_value((size_t)status));
    return file_succeeded(status);
}

const char *jbc_fileinfo(const char *handle, const char *key, const char *source, int line, int column)
{
    int validity = !jbc_compare(key, "0", -1);
    if (!validity && jbc_compare(key, "2", -1))
        numeric_error(source, line, column, "FILEINFO supports keys 0 and 2");
    struct memory_file *memory = file_for(handle);
    const char *path = memory ? memory->name : NULL;
#ifdef JBC_SEQUENTIAL
    struct sequential_file *sequential = *sequential_slot(handle);
    if (validity) return memory || (sequential && sequential->stream) ? "1" : "0";
    if (sequential && sequential->stream) {
        path = sequential_path(sequential->token);
        if (!path) numeric_error(source, line, column, "cannot resolve FILEINFO path");
    }
#else
    if (validity) return memory ? "1" : "0";
#endif
    /* An exposed path is text and must have a different identity from the handle. */
    return path ? strcpy(allocate(strlen(path)), path) : "";
}
