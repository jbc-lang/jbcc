#if defined(JBC_SEQUENTIAL) && defined(__APPLE__) && !defined(_DARWIN_C_SOURCE)
#define _DARWIN_C_SOURCE 1
#endif
#if (defined(JBC_SEQUENTIAL) || defined(JBC_SAVED_LISTS) || defined(JBC_REPORT) || defined(JBC_TERMINAL) || defined(JBC_HUSH) || defined(JBC_SLEEP) || defined(JBC_EXECUTE) || defined(JBC_PUTENV) || defined(JBC_HOST_INFO) || defined(JBC_REGEXP) || defined(JBC_SESSION) || defined(JBC_TIMESTAMP)) && !defined(_POSIX_C_SOURCE)
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
#if defined(JBC_SESSION) && !defined(__wasi__)
#include <sys/utsname.h>
#endif
#ifdef __wasi__
#include <wasi/api.h>
#endif

struct jbc_buffer {
    struct jbc_buffer *next;
    char text[];
};

static struct jbc_buffer *buffers;
static const char *jbc_command_line = "";
static int command_argc, next_argument = 1;
static char **command_argv;
static const char *jbc_input_prompt = "?";
/* INPUTNULL: the character that INPUT @ reads as an empty answer. */
static char input_null_char;

void jbc_inputnull(const char *value)
{
    input_null_char = *value ? *value : '_';
}

#ifdef JBC_TERMINAL
/* INPUT @ with only the INPUTNULL character gives an empty value; plain
   INPUT keeps it, as TAFC PB201214 does (guide, INPUTNULL). */
static const char *input_null_value(const char *value, const char *cursor)
{
    return cursor && input_null_char && value[0] == input_null_char && !value[1] ? "" : value;
}
#endif
/* 1 under prime emulation (the default, as in T24), 0 under jbase. The
   generated main clears it for --emulation jbase. */
static int jbc_emulation_prime = 1;

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

static const char *trim_blanks(const char *text);

/* TAFC PB201214 (tests/tafc/emulation-rules-*.b): the empty string is
   numeric. Under prime, spaces and tabs around a number are skipped and a
   lone sign or point is not a number; under jbase a lone sign or point is
   numeric and blanks are not. */
const char *jbc_num(const char *value)
{
    if (!*value) return "1";
    if (jbc_emulation_prime) value = trim_blanks(value);
    else if (!value[1] && strchr(".+-", *value)) return "1";
    struct decimal n;
    return parse_decimal(value, &n) ? "1" : "0";
}

/* -1 preserves jbcc's default formatting until a PRECISION statement runs. */
static int jbc_precision = -1;

/* Round a decimal half away from zero to precision places, as TAFC reads a
   number at the current precision (TAFC-CROSSCHECK.md, "TAFC's number
   model"). A carry rewrites the digits into a new buffer. */
static void limit_places(struct decimal *n, int precision)
{
    if (precision < 0 || n->places <= (size_t)precision) return;
    int carry = n->fraction[precision] >= '5';
    n->places = (size_t)precision;
    if (carry) {
        size_t length = n->digits + n->places;
        char *digits = allocate(length + 2);
        digits[0] = '0';
        memcpy(digits + 1, n->whole, n->digits);
        memcpy(digits + 1 + n->digits, n->fraction, n->places);
        size_t i = length + 1;
        while (i-- > 0) {
            if (digits[i] == '9') digits[i] = '0';
            else { ++digits[i]; break; }
        }
        digits[length + 1] = '\0';
        size_t whole = n->digits + 1;
        n->whole = digits;
        n->digits = whole;
        n->fraction = digits + whole;
        while (n->digits && *n->whole == '0') {
            ++n->whole;
            --n->digits;
        }
    }
    while (n->places && n->fraction[n->places - 1] == '0') --n->places;
    if (!n->places && !n->digits) n->sign = 0;
}

/* Leading and trailing spaces and tabs around a number are skipped. */
static const char *trim_blanks(const char *text)
{
    size_t start = strspn(text, " \t"), end = strlen(text);
    while (end > start && (text[end - 1] == ' ' || text[end - 1] == '\t')) --end;
    if (start == 0 && text[end] == '\0') return text;
    char *out = allocate(end - start);
    memcpy(out, text + start, end - start);
    out[end - start] = '\0';
    return out;
}

int jbc_truth(const char *value)
{
    struct decimal n;
    /* Prime ignores spaces and tabs around a number: ' ' is false. */
    if (jbc_emulation_prime) value = trim_blanks(value);
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

int jbc_transaction(int sync, const char *note, const char *file, int line, int column,
                    const char *message)
{
    (void)sync;
    (void)note;
    numeric_error(file, line, column, message);
    return 0;
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

const char *jbc_sentence(const char *position, const char *file, int line, int column)
{
    if (!position || !*position) return jbc_command_line;
    struct decimal n;
    if (!parse_decimal(position, &n) || n.places)
        numeric_error(file, line, column, "SENTENCE requires an integer index");
    if (n.sign < 0) return "";
    uintmax_t index = n.sign == 0 ? 0 : strtoumax(n.whole, NULL, 10);
    return index < (uintmax_t)command_argc ? command_argv[index] : "";
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

/* Exact decimals for arithmetic, as TAFC PB201214 computes
   (TAFC-CROSSCHECK.md, "TAFC's number model"): an operand is rounded half
   away from zero to the precision P, + and - are exact, and * and / are
   exact and then truncated toward zero to P. Integers have no size limit.
   A value is its decimal digits without leading zeros (none for zero), the
   number of those digits after the point, and a sign. */
struct exact {
    char *digits;
    size_t length, scale;
    int negative;
};

static void exact_normalize(struct exact *n)
{
    size_t lead = 0;
    while (lead < n->length && n->digits[lead] == '0') ++lead;
    n->digits += lead;
    n->length -= lead;
    while (n->scale && n->length && n->digits[n->length - 1] == '0') {
        --n->length;
        --n->scale;
    }
    if (!n->length) {
        n->scale = 0;
        n->negative = 0;
    }
}

/* Parse text and round it half away from zero to places. */
static int exact_parse(const char *text, size_t places, struct exact *n)
{
    struct decimal d;
    if (!parse_decimal(trim_blanks(text), &d)) return 0;
    size_t kept = d.places < places ? d.places : places;
    n->digits = allocate(d.digits + kept + 1);
    n->digits[0] = '0'; /* room for a carry */
    memcpy(n->digits + 1, d.whole, d.digits);
    memcpy(n->digits + 1 + d.digits, d.fraction, kept);
    n->length = d.digits + kept + 1;
    n->scale = kept;
    n->negative = d.sign < 0;
    if (d.places > places && d.fraction[places] >= '5') {
        size_t i = n->length;
        while (i-- > 0) {
            if (n->digits[i] == '9') n->digits[i] = '0';
            else { ++n->digits[i]; break; }
        }
    }
    exact_normalize(n);
    return 1;
}

static void exact_operand(const char *text, int places, struct exact *n)
{
    if (!exact_parse(text, (size_t)places, n)) fail("arithmetic requires numeric operands");
}

/* Digits of n with zeros appended to reach scale. */
static char *exact_scaled(struct exact n, size_t scale, size_t *length)
{
    size_t extra = scale - n.scale;
    *length = n.length + extra;
    char *out = allocate(*length);
    memcpy(out, n.digits, n.length);
    memset(out + n.length, '0', extra);
    out[*length] = '\0';
    return out;
}

static int digits_compare(const char *a, size_t na, const char *b, size_t nb)
{
    while (na && *a == '0') { ++a; --na; }
    while (nb && *b == '0') { ++b; --nb; }
    if (na != nb) return na > nb ? 1 : -1;
    int cmp = memcmp(a, b, na);
    return (cmp > 0) - (cmp < 0);
}

static char *digits_add(const char *a, size_t na, const char *b, size_t nb, size_t *n)
{
    size_t size = (na > nb ? na : nb) + 1;
    char *out = allocate(size);
    int carry = 0;
    for (size_t i = 0; i < size; ++i) {
        int sum = carry + (i < na ? a[na - 1 - i] - '0' : 0) + (i < nb ? b[nb - 1 - i] - '0' : 0);
        out[size - 1 - i] = (char)('0' + sum % 10);
        carry = sum / 10;
    }
    out[size] = '\0';
    *n = size;
    return out;
}

/* a - b for a >= b. */
static char *digits_subtract(const char *a, size_t na, const char *b, size_t nb, size_t *n)
{
    char *out = allocate(na);
    int borrow = 0;
    for (size_t i = 0; i < na; ++i) {
        int d = (a[na - 1 - i] - '0') - borrow - (i < nb ? b[nb - 1 - i] - '0' : 0);
        borrow = d < 0;
        out[na - 1 - i] = (char)('0' + (d < 0 ? d + 10 : d));
    }
    out[na] = '\0';
    *n = na;
    return out;
}

static char *digits_multiply(const char *a, size_t na, const char *b, size_t nb, size_t *n)
{
    size_t size = na + nb;
    unsigned *sums = calloc(size ? size : 1, sizeof *sums);
    if (!sums) fail("out of memory");
    for (size_t i = 0; i < na; ++i)
        for (size_t j = 0; j < nb; ++j)
            sums[i + j + 1] += (unsigned)(a[i] - '0') * (unsigned)(b[j] - '0');
    char *out = allocate(size);
    unsigned carry = 0;
    for (size_t k = size; k-- > 0;) {
        unsigned v = sums[k] + carry;
        out[k] = (char)('0' + v % 10);
        carry = v / 10;
    }
    free(sums);
    out[size] = '\0';
    *n = size;
    return out;
}

/* Truncated quotient of two digit strings, divisor nonzero. */
static char *digits_divide(const char *a, size_t na, const char *b, size_t nb, size_t *n)
{
    char *out = allocate(na ? na : 1);
    char *rest = allocate(nb + 1);
    size_t used = 0;
    for (size_t i = 0; i < na; ++i) {
        rest[used++] = a[i];
        int q = 0;
        while (digits_compare(rest, used, b, nb) >= 0) {
            size_t length;
            char *difference = digits_subtract(rest, used, b, nb, &length);
            memcpy(rest, difference, length);
            used = length;
            ++q;
        }
        out[i] = (char)('0' + q);
        /* Keep the remainder short so it never outgrows its buffer. */
        size_t lead = 0;
        while (lead + 1 < used && rest[lead] == '0') ++lead;
        memmove(rest, rest + lead, used - lead);
        used -= lead;
    }
    out[na] = '\0';
    *n = na;
    return out;
}

static struct exact exact_arithmetic(char op, struct exact x, struct exact y, int places)
{
    struct exact r = {"", 0, 0, 0};
    if (op == '+' || op == '-') {
        if (op == '-') y.negative = !y.negative && y.length;
        size_t scale = x.scale > y.scale ? x.scale : y.scale, na, nb;
        char *a = exact_scaled(x, scale, &na), *b = exact_scaled(y, scale, &nb);
        r.scale = scale;
        if (x.negative == y.negative) {
            r.digits = digits_add(a, na, b, nb, &r.length);
            r.negative = x.negative;
        } else if (digits_compare(a, na, b, nb) >= 0) {
            r.digits = digits_subtract(a, na, b, nb, &r.length);
            r.negative = x.negative;
        } else {
            r.digits = digits_subtract(b, nb, a, na, &r.length);
            r.negative = y.negative;
        }
    } else if (op == '*') {
        r.digits = digits_multiply(x.digits, x.length, y.digits, y.length, &r.length);
        r.scale = x.scale + y.scale;
        r.negative = x.negative != y.negative;
        if (r.scale > (size_t)places) {
            size_t drop = r.scale - (size_t)places;
            r.length = drop < r.length ? r.length - drop : 0;
            r.scale = (size_t)places;
        }
    } else {
        /* x/y truncated to places: (X * 10^(sy+places)) / (Y * 10^sx). */
        struct exact numerator = x, denominator = y;
        size_t nn, nd;
        char *a = exact_scaled(numerator, numerator.scale + y.scale + (size_t)places, &nn);
        char *b = exact_scaled(denominator, denominator.scale + x.scale, &nd);
        r.digits = digits_divide(a, nn, b, nd, &r.length);
        r.scale = (size_t)places;
        r.negative = x.negative != y.negative;
    }
    exact_normalize(&r);
    return r;
}

static const char *exact_text(struct exact n)
{
    if (!n.length) return "0";
    size_t whole = n.length > n.scale ? n.length - n.scale : 0;
    size_t size = (size_t)n.negative + (whole ? whole : 1) + (n.scale ? 1 + n.scale : 0);
    char *out = allocate(size), *w = out;
    if (n.negative) *w++ = '-';
    if (whole) {
        memcpy(w, n.digits, whole);
        w += whole;
    } else {
        *w++ = '0';
    }
    if (n.scale) {
        *w++ = '.';
        size_t pad = n.scale - (n.length - whole);
        memset(w, '0', pad);
        memcpy(w + pad, n.digits + whole, n.length - whole);
        w += n.scale;
    }
    *w = '\0';
    return out;
}

#ifdef JBC_MATH
/* A math function's double result, rounded half away from zero to the
   precision, as TAFC's JRunDRoundValue does: EXP(1) is 2.7183. */
static const char *format_decimal(long double result)
{
    int places = jbc_precision < 0 ? 4 : jbc_precision;
    char text[LDBL_MAX_10_EXP + 64];
    snprintf(text, sizeof text, "%.*Lf", places + 8 > 40 ? places + 8 : 40, result);
    struct exact n;
    if (!exact_parse(text, (size_t)places, &n)) return "0";
    return exact_text(n);
}
#endif

/* An arithmetic operand as TAFC PB201214 reads it (tests/tafc/
   nonnumeric-operands.b): prime skips spaces and tabs around a number; an
   empty string, a lone sign or a lone point is 0; anything else that is
   not a decimal number warns and is 0, and execution continues. */
static const char *numeric_operand(const char *text, const char *file, int line, int column)
{
    struct decimal n;
    if (jbc_emulation_prime) text = trim_blanks(text);
    if (parse_decimal(text, &n)) return text;
    if (!*text || ((text[0] == '+' || text[0] == '-' || text[0] == '.') &&
                   (!text[1] || (text[1] == '.' && text[0] != '.' && !text[2]))))
        return "0";
    fprintf(stderr, "%s:%d:%d: warning: Non-numeric value -- ZERO USED\n", file, line, column);
    return "0";
}

/* Masked decimal conversions MDn, MRn and MLn as TAFC PB201214 applies
   them (tests/tafc/md-masks.b): M, D, R or L, n decimal places, an optional
   scaling digit m (default n), then any of Z (zero gives ''), "," (thousands
   separator), "$" (prefix), "-" or M (trailing minus), C (CR), D (DB),
   E (<negative>), P (no scaling when the value has a point) and T
   (truncate instead of rounding half away from zero). OCONV divides by
   10^m; ICONV multiplies and rounds to a whole number. */
struct md_mask {
    char justify, sign;
    int places, scale, zero, thousands, dollar, keep_point, truncate;
};

static int md_parse(const char *mask, struct md_mask *md)
{
    if (mask[0] != 'M' || !mask[1] || !strchr("DRL", mask[1]) || mask[2] < '0' || mask[2] > '9')
        return 0;
    memset(md, 0, sizeof *md);
    md->justify = mask[1];
    const char *p = mask + 2;
    md->places = *p++ - '0';
    md->scale = *p >= '0' && *p <= '9' ? *p++ - '0' : md->places;
    for (; *p; ++p) {
        if (*p == 'Z') md->zero = 1;
        else if (*p == ',') md->thousands = 1;
        else if (*p == '$') md->dollar = 1;
        else if (*p == 'P') md->keep_point = 1;
        else if (*p == 'T') md->truncate = 1;
        else if (strchr("-MCDE", *p) && !md->sign) md->sign = *p == 'M' ? '-' : *p;
        else return 0;
    }
    return 1;
}

/* n rounded half away from zero (or truncated) to places. */
static struct exact exact_round(struct exact n, size_t places, int truncate)
{
    if (n.scale <= places) return n;
    size_t drop = n.scale - places;
    int up = 0;
    if (!truncate && drop <= n.length) up = n.digits[n.length - drop] >= '5';
    struct exact r = n;
    r.length = n.length > drop ? n.length - drop : 0;
    r.scale = places;
    r.digits = allocate(r.length + 1);
    r.digits[0] = '0';
    memcpy(r.digits + 1, n.digits, r.length);
    ++r.length;
    if (up) {
        size_t i = r.length;
        while (i-- > 0) {
            if (r.digits[i] == '9') r.digits[i] = '0';
            else { ++r.digits[i]; break; }
        }
    }
    int negative = n.negative;
    exact_normalize(&r);
    r.negative = negative && r.length;
    return r;
}

/* The digits of n with exactly places decimals and optional grouping. */
static const char *fixed_digits(struct exact n, size_t places, int thousands)
{
    size_t frac = n.scale, whole = n.length > frac ? n.length - frac : 0;
    size_t size = (whole ? whole : 1) + (whole / 3) + 1 + places + 1;
    char *out = allocate(size), *w = out;
    if (!whole) *w++ = '0';
    for (size_t i = 0; i < whole; ++i) {
        if (thousands && i && (whole - i) % 3 == 0) *w++ = ',';
        *w++ = n.digits[i];
    }
    if (places) {
        *w++ = '.';
        size_t present = n.length - whole;
        for (size_t i = 0; i < places; ++i) {
            size_t lead = frac - present;
            *w++ = i < lead ? '0' : i - lead < present ? n.digits[whole + i - lead] : '0';
        }
    }
    *w = '\0';
    return out;
}

static const char *md_output(const char *value, const struct md_mask *md)
{
    if (!*value && md->justify != 'R') return "";
    const char *text = *value ? value : "0";
    struct decimal check;
    if (!parse_decimal(text, &check)) return value;
    struct exact n;
    exact_parse(text, check.places, &n);
    int negative = check.sign < 0;
    if (!(md->keep_point && strchr(text, '.'))) n.scale += (size_t)md->scale;
    n = exact_round(n, (size_t)md->places, md->truncate);
    if (md->zero && !n.length) return "";
    const char *digits = fixed_digits(n, (size_t)md->places, md->thousands);
    const char *before = "", *after = "";
    switch (md->sign) {
    case '-': after = negative ? "-" : " "; break;
    case 'C': after = negative ? "CR" : "  "; break;
    case 'D': after = negative ? "  " : "DB"; break;
    case 'E': before = negative ? "<" : " "; after = negative ? ">" : " "; break;
    default: before = negative ? "-" : ""; break;
    }
    size_t size = 1 + strlen(before) + strlen(digits) + strlen(after);
    char *out = allocate(size);
    snprintf(out, size + 1, "%s%s%s%s", md->dollar ? "$" : "", before, digits, after);
    return out;
}

static const char *md_input(const char *value, const struct md_mask *md, int *status)
{
    size_t length = strlen(value);
    char *plain = allocate(length), *w = plain;
    for (const char *p = value; *p; ++p)
        if (*p != ',') *w++ = *p;
    *w = '\0';
    struct decimal check;
    if (!*plain || !parse_decimal(plain, &check)) {
        *status = 1;
        return "";
    }
    struct exact n;
    exact_parse(plain, check.places, &n);
    size_t shift = (size_t)md->scale;
    if (n.scale >= shift) {
        n.scale -= shift;
    } else if (n.length) {
        size_t extra = shift - n.scale;
        char *digits = allocate(n.length + extra);
        memcpy(digits, n.digits, n.length);
        memset(digits + n.length, '0', extra);
        n.digits = digits;
        n.length += extra;
        n.scale = 0;
    }
    *status = 0;
    return exact_text(exact_round(n, 0, 0));
}

static const char *arithmetic(char op, const char *left, const char *right,
                              int warn_on_zero_divisor, const char *file, int line, int column)
{
    struct decimal lhs, rhs;
    left = numeric_operand(left, file, line, column);
    right = numeric_operand(right, file, line, column);
    parse_decimal(left, &lhs);
    parse_decimal(right, &rhs);
    /* A zero divisor warns and gives 0, and execution continues, as TAFC
       does under prime; under jbase TAFC enters its debugger, which ends a
       program that has no terminal, so jbcc stops there. */
    if (op == '/' && rhs.sign == 0 && !jbc_emulation_prime)
        numeric_error(file, line, column, "division by zero");
    if (op == '/' && rhs.sign == 0) {
        fprintf(stderr, "%s:%d:%d: warning: %sdivision by zero\n", file, line, column,
                warn_on_zero_divisor ? "DIVS: " : "");
        return "0";
    }

    if (op != '/' && !strchr(left, '.') && !strchr(right, '.') && lhs.digits < 19 &&
        rhs.digits < 19) {
        int64_t a = integer(left, file, line, column);
        int64_t b = integer(right, file, line, column);
        int64_t result;
        if (op == '+') {
            if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b))
                goto exact;
            result = a + b;
        } else if (op == '-') {
            if ((b > 0 && a < INT64_MIN + b) || (b < 0 && a > INT64_MAX + b))
                goto exact;
            result = a - b;
        } else {
            if (multiply_overflows(a, b))
                goto exact;
            result = a * b;
        }
        char *out = allocate(20);
        snprintf(out, 21, "%" PRId64, result);
        return out;
    }

exact:;
    int places = jbc_precision < 0 ? 4 : jbc_precision;
    struct exact x, y;
    exact_operand(left, places, &x);
    exact_operand(right, places, &y);
    return exact_text(exact_arithmetic(op, x, y, places));
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

int jbc_callj(const char *class_name, const char *method, const char *argument,
              jbc_variable *result, const char *file, int line, int column)
{
    (void)class_name;
    (void)method;
    (void)argument;
    (void)result;
    numeric_error(file, line, column, "CALLJ requires a JVM backend");
    return 0;
}

static jbc_variable select_lists[12];
static jbc_variable jbc_record_id = {"", 0, 0};
static jbc_variable jbc_record = {"", 0, 0};
static jbc_variable jbc_filename = {"", 0, 0};
static jbc_variable jbc_company_no = {"", 0, 0};

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

#ifdef JBC_CHDIR
#include <unistd.h>

const char *jbc_chdir(const char *path)
{
    return *path && chdir(path) == 0 ? "1" : "0";
}

const char *jbc_getcwd(jbc_variable *target)
{
    size_t size = 256;
    for (;;) {
        char *buffer = allocate(size);
        if (getcwd(buffer, size)) {
            assign_value(target, buffer);
            return "1";
        }
        if (errno != ERANGE || size > SIZE_MAX / 2) return "0";
        size *= 2;
    }
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
    /* Named storage is COMMON. Prime starts COMMON scalars and matrix
       elements at 0 (named_common and unnamed_common = zero in TAFC's
       Config_EMULATE; tests/tafc/common-*.b); jbase leaves them unassigned. */
    if (name && jbc_emulation_prime)
        for (size_t i = 0; i < count; ++i) s->values[i].value = "0";
    return s;
}

jbc_variable *jbc_storage(size_t count, const char *name)
{
    return storage(count, name)->values;
}

/* Unnamed COMMON is the block named "" and its matrices are keyed ":<member>". */
void jbc_clearcommon(void)
{
    for (struct jbc_slots *s = storages; s; s = s->next)
        if (s->name && (!*s->name || *s->name == ':'))
            for (size_t i = 0; i < s->count; ++i) assign_value(&s->values[i], "0");
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
                                     int rank, const int *bounds, const char *mismatch,
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
        if (!mismatch) mismatch = key ? "incompatible COMMON matrix dimensions"
                                      : "incompatible local matrix dimensions";
        numeric_error(file, line, column, mismatch);
    }
    return s;
}

void jbc_dimension_mat_parameter(jbc_matrix *matrix, struct jbc_slots **owned,
                                 int rank, const int *bounds, const char *file, int line, int column)
{
    if (!matrix->rank) {
        struct jbc_slots *s = jbc_matrix_storage(NULL, NULL, rank, bounds, NULL, file, line, column);
        *owned = s;
        *matrix = (jbc_matrix){s->values, s->bounds, s->rank, s->count};
    } else if (matrix->rank != rank || memcmp(matrix->bounds, bounds, (size_t)rank * sizeof *bounds)) {
        numeric_error(file, line, column, "incompatible MAT parameter dimensions");
    }
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
    if (jbc_record_id.value == value || jbc_record.value == value || jbc_filename.value == value
        || jbc_company_no.value == value) return 1;
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

size_t jbc_matrix_index(int rank, const int *bounds, int count, const char **indices,
                 const char *file, int line, int column)
{
    if (rank != count)
        numeric_error(file, line, column, "COMMON matrix subscript count is unsupported");
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

const char *jbc_read(jbc_variable *slot, const char *name, const char *file, int line, int column)
{
    /* An unassigned read warns, assigns '' and continues, as in TAFC
       PB201214, where ASSIGNED is then 1 (tests/tafc/unassigned-continues.b). */
    if (!slot->value) {
        fprintf(stderr, "%s:%d:%d: warning: unassigned variable '%s' -- NULL USED\n", file,
                line, column, name);
        assign_value(slot, "");
    }
    return slot->value;
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
    const char *text = jbc_read(slot, name, file, line, column);
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

#if (defined(JBC_SESSION) && !defined(__wasi__)) || defined(JBC_SEQUENTIAL)
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
#ifndef __wasi__
#include <pwd.h>
#endif

static uintmax_t port_number;
static int invalid_port_number;
static const char *login_override;
static const char *account_override;
static const char *paragraph_sentence;
static char user_root[64];

#ifdef JBC_USERSTATS
static time_t session_started;
static size_t record_open_count, record_read_count, record_write_count;
static size_t record_delete_count, record_clear_count;
static size_t command_count, input_count;
#endif

static const char *session_environment(const char *name)
{
    const char *value = getenv(name);
    return value && *value ? strcpy(allocate(strlen(value)), value) : NULL;
}

static uintmax_t session_process_id(void)
{
#ifdef __wasi__
    return 0;
#else
    return (uintmax_t)getpid();
#endif
}

void jbc_init_session(void)
{
#ifdef JBC_USERSTATS
    session_started = time(NULL);
#endif
    login_override = session_environment("JBCLOGNAME");
    account_override = login_override;
    if (!login_override) login_override = session_environment("JBASICLOGNAME");
    if (!account_override) account_override = session_environment("LOGNAME");
    paragraph_sentence = session_environment("JBCC_PARASENTENCE");

    const char *value = getenv("JBCPORTNO");
    if (!value || !*value) {
        port_number = session_process_id();
        return;
    }
    char *end;
    errno = 0;
    port_number = strtoumax(value, &end, 10);
    invalid_port_number = errno || *end || *value < '0' || *value > '9';
}

const char *jbc_para_sentence(void)
{
    return paragraph_sentence ? paragraph_sentence : jbc_command_line;
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
#ifdef __wasi__
    return "";
#else
    const struct passwd *user = getpwuid(getuid());
    if (!user || !user->pw_name) return "";
    return strcpy(allocate(strlen(user->pw_name)), user->pw_name);
#endif
}

const char *jbc_account_name(void)
{
    return account_override ? account_override : jbc_login_name();
}

const char *jbc_account_path(const char *file, int line, int column)
{
#ifdef __wasi__
    (void)file;
    (void)line;
    (void)column;
    return "/";
#else
    const char *path = working_directory();
    if (!path) numeric_error(file, line, column, "cannot resolve @PATH");
    return path;
#endif
}

/* @UID: the user id of the process; 0 where the host has none. */
const char *jbc_uid(void)
{
#if defined(__wasi__) || defined(_WIN32)
    return "0";
#else
    return size_value((uintmax_t)getuid());
#endif
}

const char *jbc_process_id(void)
{
    return size_value(session_process_id());
}

const char *jbc_terminal_type(void)
{
    const char *type = session_environment("TERM");
    return type ? type : "";
}

const char *jbc_terminal_name(void)
{
#ifdef __wasi__
    return "phantom";
#else
    /* A plain TAFC PB201214 run without a terminal gives '' (tests/tafc/
       at-tty.b), but T24 tests @TTY = 'phantom' for a background job, which
       is what a jbcc run without a terminal usually is. */
    const char *terminal = ttyname(STDIN_FILENO);
    return terminal ? strcpy(allocate(strlen(terminal)), terminal) : "phantom";
#endif
}

const char *jbc_user_root(void)
{
    return strcpy(allocate(strlen(user_root)), user_root);
}

void jbc_set_user_root(const char *value, const char *file, int line, int column)
{
    size_t length = strlen(value);
    if (length >= sizeof user_root)
        numeric_error(file, line, column, "@USER.ROOT accepts at most 63 bytes");
    memcpy(user_root, value, length + 1);
}

#ifdef JBC_USERSTATS
const char *jbc_userstats(const char *file, int line, int column)
{
    enum { USERSTATS_ATTRIBUTES = 52 };
    jbc_variable attrs[USERSTATS_ATTRIBUTES + 1] = {{0}};
    for (int i = 1; i <= USERSTATS_ATTRIBUTES; ++i) attrs[i].value = "";
    attrs[1].value = jbc_port_number(file, line, column);
    attrs[2].value = "1";
    if (session_started != (time_t)-1)
        attrs[3].value = size_value((uintmax_t)session_started);
    attrs[4].value = jbc_process_id();
    attrs[5].value = jbc_account_name();
    attrs[6].value = jbc_login_name();
    attrs[8].value = jbc_terminal_type();
    attrs[10].value = jbc_terminal_name();
    attrs[18].value = size_value(record_open_count);
    attrs[19].value = size_value(record_read_count);
    attrs[20].value = size_value(record_write_count);
    attrs[21].value = size_value(record_delete_count);
    attrs[22].value = size_value(record_clear_count);
    attrs[23].value = size_value(command_count);
    attrs[24].value = size_value(input_count);
    attrs[28].value = user_root;
    attrs[41].value = jbc_command_line;
    attrs[42].value = size_value((size_t)line);
    attrs[43].value = file;
    const int bounds[] = {USERSTATS_ATTRIBUTES};
    return jbc_matbuild(attrs, 1, bounds, NULL, NULL, "\376", "@USERSTATS", file, line, column);
}
#endif
#endif

#ifdef JBC_USERSTATS
static void count_userstat(size_t *counter)
{
    if (*counter < SIZE_MAX) ++*counter;
}
#else
#define count_userstat(counter) ((void)0)
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

struct assigned_key {
    struct assigned_key *next;
    const char *key, *value;
};
static struct assigned_key *assigned_keys;

void jbc_assign_system(const char *value, const char *key, const char *file, int line, int column)
{
    if (!jbc_compare(key, "1036", -1)) {
        if (jbc_compare(value, "0", -1))
            numeric_error(file, line, column, "SYSTEM(1036) can only be reset to zero");
        blocked_record_locks = 0;
        return;
    }
    /* Other keys keep the value, which SYSTEM() then returns, as TAFC
       PB201214 does for SYSTEM(2021); T24 assigns 1039 and 2021. */
    for (struct assigned_key *a = assigned_keys; a; a = a->next)
        if (!jbc_compare(a->key, key, -1)) {
            a->value = value;
            return;
        }
    struct assigned_key *a = malloc(sizeof *a);
    if (!a) fail("out of memory");
    *a = (struct assigned_key){assigned_keys, key, value};
    assigned_keys = a;
    (void)file, (void)line, (void)column;
}

#if defined(JBC_SESSION) && defined(JBC_TERMINAL) && !defined(__wasi__)
static const char *assigned_system_key(const char *key)
{
    for (struct assigned_key *a = assigned_keys; a; a = a->next)
        if (!jbc_compare(a->key, key, -1)) return a->value;
    return NULL;
}
#endif

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
    /* TAFC PB201214 (tests/tafc/emulation-rules-*.b): one trailing delimiter
       ends the record without an empty field after it, an empty delimiter
       splits the record into bytes, and SETTING is 0 when fields are left
       over. The rest goes into element 0 under prime and is joined to the
       last element under jbase. */
    size_t length = strlen(source);
    if (length && *delimiter && source[length - 1] == *delimiter) {
        char *copy = allocate(length - 1);
        memcpy(copy, source, length - 1);
        copy[length - 1] = '\0';
        source = copy;
    }
    const char *field = length ? source : NULL;
    for (size_t i = first; i <= last; ++i) {
        if (field) ++assigned;
        const char *value;
        if (*delimiter || !field) value = take_field(&field, (unsigned char)*delimiter);
        else {
            char *byte = allocate(1);
            byte[0] = *field;
            byte[1] = '\0';
            value = byte;
            field = field[1] ? field + 1 : NULL;
        }
        assign_value(&dest[matrix_element_offset(i - 1, rank, bounds)], value);
    }
    if (first <= last) {
        /* The unparsed suffix can point inside a temporary collected after this statement. */
        const char *rest = field && *field ? strcpy(allocate(strlen(field)), field) : "";
        if (field && !jbc_emulation_prime) {
            jbc_variable *target = &dest[matrix_element_offset(last - 1, rank, bounds)];
            char mark[2] = {*delimiter ? *delimiter : '\0', '\0'};
            assign_value(target, jbc_concat(jbc_concat(target->value, mark), rest));
            rest = "";
        }
        assign_value(&dest[0], rest);
    }
    if (field) assigned = 0;
    last_matrix_load = assigned;
    if (setting) assign_value(setting, size_value(assigned));
}

const char *jbc_remove(jbc_variable *out, jbc_variable *source, jbc_variable *setting,
                const char *name, const char *file, int line, int column)
{
    const char *text = jbc_read(source, name, file, line, column);
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

/* LOCATE BY AR/DR. jbase right-justifies every pair. Prime compares two
   numbers numerically, two non-numbers right-justified, and a number with a
   non-number byte by byte, so 100 sorts before B and b2 before b10. */
static int locate_compare_right(const char *item, const char *needle)
{
    if (!jbc_emulation_prime) return compare_right(item, needle);
    struct decimal a, b;
    int item_number = parse_decimal(item, &a), needle_number = parse_decimal(needle, &b);
    if (item_number && needle_number) return compare_decimals(a, b, -1);
    if (!item_number && !needle_number) return compare_right(item, needle);
    return strcmp(item, needle);
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
                else if (*order && order[1] == 'R') cmp = locate_compare_right(item, needle);
                else cmp = strcmp(item, needle);
                found = cmp == 0;
                if (found || (*order == 'A' && cmp > 0) || (*order == 'D' && cmp < 0)) break;
            }
            ++index;
            if (!next) break;
            item = next;
        }
    }
    /* A start past the end is the position, as TAFC returns it. */
    if (!found && index < (uint64_t)first) index = (size_t)first;
    assign_value(position, size_value(index));
    return found;
}

/* LOCATE needle IN source<coordinates>, at run time as TAFC decides it
   (TAFC-CROSSCHECK.md section 1). Both emulations drop trailing zero
   coordinates, so <0> is no coordinate and <2,0> is <2>.
   prime: no coordinate searches fields from start; the last coordinate is
   the start at the level below the ones before it: <f> searches fields from
   field f, <f,v> the values of field f from v, <f,v,s> the subvalues of
   value v from s. A separate start applies only without coordinates.
   jbase: every coordinate selects: <f> searches the values of field f,
   <f,v> the subvalues of value v, and a third coordinate is the start. */
int jbc_locate_at(const char *needle, const char *source, const char **coordinates,
                  int count, const char *start, const char *order,
                  jbc_variable *position, const char *file, int line, int column)
{
    while (count > 0 && integer(coordinates[count - 1], file, line, column) == 0) --count;
    if (jbc_emulation_prime && count > 0) {
        int64_t first = integer(coordinates[count - 1], file, line, column);
        if (first < 1) numeric_error(file, line, column, "LOCATE positions start at one");
        start = size_value((uintmax_t)first);
        --count;
    } else if (count == 3) {
        start = coordinates[2];
        count = 2;
    }
    const char *container = count ? jbc_array(source, coordinates, count, NULL) : source;
    return jbc_locate(needle, container, 254 - count, start, order, position, file, line,
                      column);
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

    /* Four places without an argument, whatever the PRECISION (TAFC
       PB201214, tests/snippets/dround.b). */
    int64_t digits = 4;
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
    parse_decimal(numeric_operand(left, file, line, column), &a);
    parse_decimal(numeric_operand(right, file, line, column), &b);

    /* TAFC PB201214 truncates to 14 places (tests/tafc/string-math.b). */
    uintmax_t places = string_math_places(precision, 14,
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
    if (!result.digits && !result.places) return "0";
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
    parse_decimal(numeric_operand(left, file, line, column), &a);
    parse_decimal(numeric_operand(right, file, line, column), &b);
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

    /* Discard the incomplete interval so each remainder is equally likely. */
    uint32_t threshold = (UINT64_C(1) << 32) % bound;
    uint32_t sample;
#ifdef __wasi__
    do {
        if (__wasi_random_get((unsigned char *)&sample, sizeof sample))
            numeric_error(file, line, column, "RND cannot get random bytes");
    } while (sample < threshold);
#else
    FILE *random = fopen("/dev/urandom", "rb");
    if (!random) numeric_error(file, line, column, "RND cannot open /dev/urandom");
    do {
        if (fread(&sample, sizeof sample, 1, random) != 1) {
            fclose(random);
            numeric_error(file, line, column, "RND cannot read /dev/urandom");
        }
    } while (sample < threshold);
    fclose(random);
#endif
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

static int ascii_alpha(unsigned char c);

/* The MX mask: each byte as two upper-case hex digits, as in
   FMT('ABCDEF', 'MX') = 414243444546 and FMT(@FM, 'MX') = FE. */
static const char *hex_bytes(const char *text)
{
    static const char digits[] = "0123456789ABCDEF";
    size_t n = strlen(text);
    if (n > (SIZE_MAX - 1) / 2) fail("value is too large");
    char *out = allocate(2 * n);
    for (size_t i = 0; i < n; ++i) {
        unsigned char c = (unsigned char)text[i];
        out[2 * i] = digits[c >> 4];
        out[2 * i + 1] = digits[c & 15];
    }
    out[2 * n] = '\0';
    return out;
}

static int byte_class(unsigned char c, char kind);
static const char *change_substrings(const char *text, const char *search, const char *replacement,
                                     int64_t limit, int64_t first);

/* MCP{c}: the guide's table says MCP turns every non-printable byte into
   "." (or c), and its note on printing arrays shows field, value and
   subvalue marks as ^, ] and \. Printable is ISPRINT's ASCII 32 to 126. */
static const char *printable_marks(const char *text, char replacement)
{
    size_t n = strlen(text);
    char *out = allocate(n);
    for (size_t i = 0; i < n; ++i) {
        unsigned char c = (unsigned char)text[i];
        /* TAFC shows byte 255 as _ (tests/tafc/mcp-bytes.b). */
        out[i] = c == 254 ? '^' : c == 253 ? ']' : c == 252 ? '\\' : c == 255 ? '_'
               : byte_class(c, 'P') ? (char)c : replacement;
    }
    out[n] = '\0';
    return out;
}

/* MCPN{x}: each byte outside ASCII 32 to 126, marks included, becomes x
   (default ".") and two upper-case hex digits; x itself is not escaped.
   MCNP{x} turns x and one or two hex digits back into the byte. As in TAFC
   PB201214 (tests/tafc/mcpn-mcnp.b). */
static const char *escape_unprintable(const char *text, char escape)
{
    size_t n = strlen(text), size = 0;
    for (size_t i = 0; i < n; ++i) size += byte_class((unsigned char)text[i], 'P') ? 1 : 3;
    char *out = allocate(size), *w = out;
    for (size_t i = 0; i < n; ++i) {
        unsigned char c = (unsigned char)text[i];
        if (byte_class(c, 'P')) *w++ = (char)c;
        else w += sprintf(w, "%c%02X", escape, c);
    }
    *w = '\0';
    return out;
}

static int hex_value(char c)
{
    return c >= '0' && c <= '9' ? c - '0' : c >= 'A' && c <= 'F' ? c - 'A' + 10
         : c >= 'a' && c <= 'f' ? c - 'a' + 10 : -1;
}

static const char *unescape_unprintable(const char *text, char escape)
{
    char *out = allocate(strlen(text)), *w = out;
    for (const char *p = text; *p; ++p) {
        int high = *p == escape ? hex_value(p[1]) : -1;
        if (high < 0) { *w++ = *p; continue; }
        int low = hex_value(p[2]);
        int byte = low < 0 ? high : high * 16 + low;
        if (!byte) { *w++ = *p; continue; } /* strings cannot hold NUL yet */
        *w++ = (char)byte;
        p += low < 0 ? 1 : 2;
    }
    *w = '\0';
    return out;
}

/* MCA, MCN, MCB and their /-forms keep or remove ASCII letters, digits, or
   both, as ISALPHA and ISDIGIT classify them. */
static const char *keep_class(const char *text, char kind, int remove)
{
    size_t n = strlen(text), used = 0;
    char *out = allocate(n);
    for (size_t i = 0; i < n; ++i) {
        unsigned char c = (unsigned char)text[i];
        int in = kind == 'A' ? ascii_alpha(c) : kind == 'N' ? ascii_digit(c)
               : ascii_alpha(c) || ascii_digit(c);
        if (in != remove) out[used++] = (char)c;
    }
    out[used] = '\0';
    return out;
}

/* MCL, MCU and MCT: lower case, upper case, and each word capitalised with
   the rest of it lower case ("LONG STRING" becomes "Long String"). */
static const char *convert_case(const char *text, char kind)
{
    size_t n = strlen(text);
    char *out = allocate(n);
    int in_word = 0;
    for (size_t i = 0; i < n; ++i) {
        unsigned char c = (unsigned char)text[i];
        int upper = kind == 'U' || (kind == 'T' && !in_word);
        if (upper && c >= 'a' && c <= 'z') c = (unsigned char)(c - 32);
        else if (!upper && c >= 'A' && c <= 'Z') c = (unsigned char)(c + 32);
        in_word = ascii_alpha(c);
        out[i] = (char)c;
    }
    out[n] = '\0';
    return out;
}

/* The MC conversions of the guide's OCONV table, shared by FMT and OCONV.
   Returns NULL for a mask that is not one of them. */
static const char *mc_conversion(const char *text, const char *mask, const char *file,
                                 int line, int column)
{
    if (strncmp(mask, "MC", 2) != 0) return NULL;
    const char *code = mask + 2;
    if (code[0] == 'P' && code[1] == 'N' && (!code[2] || !code[3]))
        return escape_unprintable(text, code[2] ? code[2] : '.');
    if (code[0] == 'N' && code[1] == 'P' && (!code[2] || !code[3]))
        return unescape_unprintable(text, code[2] ? code[2] : '.');
    if (*code == 'P' && (!code[1] || (!code[2] && code[1] != 'N')))
        return printable_marks(text, code[1] ? code[1] : '.');
    if (!strcmp(code, "A") || !strcmp(code, "N") || !strcmp(code, "B")) return keep_class(text, *code, 0);
    if (!strcmp(code, "/A") || !strcmp(code, "/N") || !strcmp(code, "/B")) return keep_class(text, code[1], 1);
    if (!strcmp(code, "L") || !strcmp(code, "U") || !strcmp(code, "T")) return convert_case(text, *code);
    if (*code == 'C' && code[1]) {
        /* MCC;s1;s2, with the character after MCC as the separator. */
        char separator[2] = {code[1], '\0'};
        const char *from = code + 2, *middle = strstr(from, separator);
        if (!middle || middle == from) return NULL;
        size_t length = (size_t)(middle - from);
        char *search = allocate(length);
        memcpy(search, from, length);
        search[length] = '\0';
        const char *with = middle + 1;
        if (strchr(with, code[1])) return NULL;
        return change_substrings(text, search, with, -1, 1);
    }
    if (!strcmp(code, "DX") || !strcmp(code, "XD")) {
        int from_hex = code[0] == 'X';
        if (!*text || strspn(text, from_hex ? "0123456789ABCDEFabcdef" : "0123456789") != strlen(text)
            || strlen(text) > 15)
            numeric_error(file, line, column, from_hex ? "MCXD requires hexadecimal digits"
                                                       : "MCDX requires a nonnegative integer");
        unsigned long long value = strtoull(text, NULL, from_hex ? 16 : 10);
        char *out = allocate(24);
        snprintf(out, 25, from_hex ? "%llu" : "%llX", value);
        return out;
    }
    return NULL;
}

/* FMT pattern masks: L(...) or R(...), or a bare pattern that starts
   with #. A precision digit before the pattern, as in R2(##.##), first
   formats a number to that many places (rounding half away from zero), so
   12.345 becomes 12.35 and fills the slots as 2..35, as TAFC PB201214 does
   (tests/tafc/pattern-mask-decimals.b). In the
   pattern, # takes one character of the value and #n takes n; anything
   else is literal. R fills the slots from the value's rightmost characters
   and L from its leftmost, as in the guide's FMT(1234567890,
   'R((###) ###-###)') = (234) 567-890 and its UNIQUEKEY example; missing
   characters become spaces. Returns NULL when the mask is not a pattern. */
static const char *pattern_format(const char *text, const char *mask)
{
    char align = 'L';
    const char *pattern, *end;
    if (*mask == '#') {
        pattern = mask;
        end = mask + strlen(mask);
    } else {
        const char *p = mask;
        if (*p != 'L' && *p != 'R') return NULL;
        align = *p++;
        if (ascii_digit((unsigned char)*p) && p[1] == '(') {
            size_t places = (size_t)(*p++ - '0');
            struct decimal check;
            struct exact n;
            if (parse_decimal(text, &check) && exact_parse(text, places, &n)) {
                const char *digits = fixed_digits(n, places, 0);
                text = n.negative ? jbc_concat("-", digits) : digits;
            }
        }
        size_t length = strlen(p);
        if (*p != '(' || length < 2 || p[length - 1] != ')') return NULL;
        pattern = p + 1;
        end = p + length - 1;
    }
    size_t slots = 0, literals = 0;
    for (const char *q = pattern; q < end;) {
        if (*q++ != '#') { ++literals; continue; }
        size_t count = 1;
        if (q < end && ascii_digit((unsigned char)*q)) {
            count = 0;
            while (q < end && ascii_digit((unsigned char)*q)) {
                if (count > (SIZE_MAX - 9) / 10) fail("FMT pattern too large");
                count = count * 10 + (size_t)(*q++ - '0');
            }
        }
        if (count > SIZE_MAX - slots - literals - 1) fail("FMT pattern too large");
        slots += count;
    }
    size_t length = strlen(text);
    size_t pad = length < slots ? slots - length : 0;
    const char *source = text + (align == 'R' && length > slots ? length - slots : 0);
    char *out = allocate(slots + literals), *write = out;
    size_t taken = 0;
    for (const char *q = pattern; q < end;) {
        if (*q != '#') { *write++ = *q++; continue; }
        ++q;
        size_t count = 1;
        if (q < end && ascii_digit((unsigned char)*q)) {
            count = 0;
            while (q < end && ascii_digit((unsigned char)*q)) count = count * 10 + (size_t)(*q++ - '0');
        }
        for (size_t i = 0; i < count; ++i, ++taken) {
            int blank = align == 'R' ? taken < pad : taken >= slots - pad;
            *write++ = blank ? ' ' : *source++;
        }
    }
    *write = '\0';
    return out;
}

/* Numeric FMT masks with the parts the guide's table lists after the
   justification and precision: a scaling digit m, Z, the thousands
   separator ",", a credit indicator (C, D, E, M or N), "$", "&x" and a
   fill (#n spaces, %n zeros, *n asterisks). The guide's examples:
   FMT(123456.78, 'R2,$#15') = "    $123,456.78" and
   FMT(-123456.78, 'R2,C&*$#15') = "  $123,456.78CR". "&x" makes x the
   fill character, whatever the #, % or * fill says, and x itself is not
   shown: TAFC PB201214 gives "**$123,456.78CR" for that example and
   "$$$$$123,456.78" for 'R2,&$#15' (tests/tafc/fmt-fill-character.b).
   Returns NULL for masks the plain FMT code handles. */
static const char *numeric_format(const char *text, const char *mask)
{
    const char *p = mask;
    if (*p != 'L' && *p != 'R') return NULL;
    char align = *p++;
    int precision = -1, scale = -1, zero = 0, thousands = 0, dollar = 0, extended = 0;
    char credit = 0, fill = ' ', ampersand_fill = 0;
    size_t width = 0;
    if (ascii_digit((unsigned char)*p)) precision = *p++ - '0';
    if (precision >= 0 && ascii_digit((unsigned char)*p)) { scale = *p++ - '0'; extended = 1; }
    for (; *p && !strchr("#%*", *p); ++p) {
        extended = 1;
        if (*p == 'Z') zero = 1;
        else if (*p == ',') thousands = 1;
        else if (*p == '$') dollar = 1;
        else if (strchr("CDEMN", *p)) { if (credit) return NULL; credit = *p; }
        else if (*p == '&' && p[1]) ampersand_fill = *++p;
        else return NULL;
    }
    if (*p) {
        fill = *p == '%' ? '0' : *p == '*' ? '*' : ' ';
        ++p;
        if (!ascii_digit((unsigned char)*p)) return NULL;
        while (ascii_digit((unsigned char)*p)) {
            if (width > (SIZE_MAX - 9) / 10) fail("FMT width too large");
            width = width * 10 + (size_t)(*p++ - '0');
        }
        if (*p || !width) return NULL;
    }
    if (ampersand_fill) fill = ampersand_fill;
    if (!extended) return NULL;
    struct decimal n;
    if (!parse_decimal(text, &n)) return NULL;
    if (scale > 0) {
        /* Descale: move the decimal point m places to the left. */
        size_t digits = n.digits + n.places, total = digits > (size_t)scale ? digits : (size_t)scale;
        char *shifted = allocate(total + 3), *w = shifted;
        if (n.sign < 0) *w++ = '-';
        size_t pad = total - digits;
        size_t whole = total - (size_t)scale;
        for (size_t i = 0; i < total; ++i) {
            if (i == whole) { if (!whole) *w++ = '0'; *w++ = '.'; }
            size_t k = i - pad;
            *w++ = i < pad ? '0' : k < n.digits ? n.whole[k] : n.fraction[k - n.digits];
        }
        *w = '\0';
        text = shifted;
        parse_decimal(text, &n);
    }
    int negative = n.sign < 0;
    n.sign = 1;
    const char *number = fmt_decimal(n, precision < 0 ? 0 : (size_t)precision);
    if (precision < 0 && n.places) number = fmt_decimal(n, n.places);
    int is_zero = number[strspn(number, "0.")] == '\0';
    if (is_zero) negative = 0;
    if (zero && is_zero) number = "";
    /* Group the whole digits in threes. */
    size_t len = strlen(number), whole = strcspn(number, ".");
    size_t commas = thousands && whole > 3 ? (whole - 1) / 3 : 0;
    char *body = allocate(len + commas + 1), *b = body;
    for (size_t i = 0; i < len; ++i) {
        if (i && i < whole && commas && (whole - i) % 3 == 0) *b++ = ',';
        *b++ = number[i];
    }
    *b = '\0';
    const char *before = negative && !credit ? "-" : "";
    const char *after = "";
    switch (credit) {
    case 'C': after = negative ? "CR" : "  "; break;
    case 'D': after = negative ? "  " : "DB"; break;
    case 'M': after = negative ? "-" : " "; break;
    case 'E': before = negative ? "<" : " "; after = negative ? ">" : " "; break;
    default: break; /* N: no minus sign at all */
    }
    size_t used = strlen(before) + (dollar ? 1 : 0) + strlen(body) + strlen(after);
    size_t total = used > width ? used : width;
    char *out = allocate(total), *o = out;
    size_t padding = total - used;
    if (align == 'R') { memset(o, fill, padding); o += padding; }
    o += sprintf(o, "%s%s%s%s", before, dollar ? "$" : "", body, after);
    if (align == 'L') { memset(o, fill, padding); o += padding; }
    *o = '\0';
    return out;
}

/* G{n}cx: x groups delimited by c after skipping n, as in the guide's
   OCONV('LONG STRING TO BE SPLIT', 'G1 3') = STRING TO BE. */
static const char *group_extract(const char *text, const char *mask)
{
    const char *p = mask + 1;
    size_t skip = 0, take = 0;
    while (ascii_digit((unsigned char)*p)) skip = skip * 10 + (size_t)(*p++ - '0');
    char delimiter = *p;
    if (!delimiter || ascii_digit((unsigned char)delimiter)) return NULL;
    ++p;
    if (!ascii_digit((unsigned char)*p)) return NULL;
    while (ascii_digit((unsigned char)*p)) take = take * 10 + (size_t)(*p++ - '0');
    if (*p || !take) return NULL;
    const char *start = text;
    for (size_t i = 0; i < skip; ++i) {
        start = strchr(start, delimiter);
        if (!start) return "";
        ++start;
    }
    const char *end = start;
    for (size_t i = 0; i < take; ++i) {
        const char *next = strchr(end, delimiter);
        if (!next) { end += strlen(end); break; }
        end = i + 1 < take ? next + 1 : next;
    }
    size_t length = (size_t)(end - start);
    char *out = allocate(length);
    memcpy(out, start, length);
    out[length] = '\0';
    return out;
}

const char *jbc_oconv(const char *value, const char *mask, const char *file, int line, int column);

const char *jbc_fmt(const char *text, const char *mask, const char *file, int line, int column)
{
    /* An empty mask returns the value unchanged (TAFC PB201214). */
    if (!*mask) return text;
    struct md_mask md;
    if (md_parse(mask, &md)) return md_output(text, &md);
    const char *converted = mc_conversion(text, mask, file, line, column);
    if (converted) return converted;
    if (strcmp(mask, "MX") == 0) return hex_bytes(text);
    if ((converted = pattern_format(text, mask))) return converted;
    if ((converted = numeric_format(text, mask))) return converted;
    if (*mask == 'G' && (converted = group_extract(text, mask))) return converted;
    /* The guide's FMT table: D and M masks are dates and times, as OCONV
       formats them, as in FMT(16376, 'D4/') = 10/31/2012. */
    if (*mask == 'D' || strncmp(mask, "MT", 2) == 0) return jbc_oconv(text, mask, file, line, column);
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

const char *jbc_isdigit(const char *text)
{
    if (!*text) return "0";
    for (; *text; ++text)
        if (!ascii_digit((unsigned char)*text)) return "0";
    return "1";
}

const char *jbc_isalnum(const char *text)
{
    if (!*text) return "0";
    for (; *text; ++text)
        if (!ascii_alpha((unsigned char)*text) && !ascii_digit((unsigned char)*text)) return "0";
    return "1";
}

static int ascii_space(unsigned char c)
{
    return c == ' ' || (c >= '\t' && c <= '\r');
}

const char *jbc_isupper(const char *text)
{
    if (!*text) return "0";
    for (; *text; ++text)
        if (*text < 'A' || *text > 'Z') return "0";
    return "1";
}

const char *jbc_islower(const char *text)
{
    if (!*text) return "0";
    for (; *text; ++text)
        if (*text < 'a' || *text > 'z') return "0";
    return "1";
}

const char *jbc_isspace(const char *text)
{
    if (!*text) return "0";
    for (; *text; ++text)
        if (!ascii_space((unsigned char)*text)) return "0";
    return "1";
}

/* Extended patterns are prime's: codes A, N and X in either case, n-mX
   ranges and "..." for any run of bytes. jbase MATCHES has the codes A, N,
   C and X in upper case only. MATCHFIELD uses extended patterns in both
   emulations, as TAFC PB201214 does. */
static int pattern_extended = 1;

static char pattern_code(char c)
{
    if (pattern_extended) {
        char upper = (char)(c >= 'a' && c <= 'z' ? c - 'a' + 'A' : c);
        return upper && strchr("ANX", upper) ? upper : 0;
    }
    return c && strchr("ANCX", c) ? c : 0;
}

static int pattern_ellipsis(const char *p, const char *end)
{
    return pattern_extended && end - p >= 3 && memcmp(p, "...", 3) == 0;
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
        if (pattern_ellipsis(p, end)) {
            p += 3;
            kind = 'X';
            high = SIZE_MAX;
        } else if (*p == '\'' || *p == '"') {
            char quote = *p++;
            literal = p;
            const char *close = memchr(p, quote, (size_t)(end - p));
            if (!close) return 0;
            p = close + 1;
            literal_length = (size_t)(close - literal);
        } else if (ascii_digit(*p)) {
            low = read_decimal_count(&p, end);
            high = low ? low : SIZE_MAX;
            /* n-mX ranges are prime pattern syntax; jbase reads them as
               text, so "2-4N" does not match "2022". */
            if (pattern_extended && end - p >= 2 && *p == '-' && ascii_digit(p[1])) {
                const char *after = p + 1;
                size_t upper = read_decimal_count(&after, end);
                if (after < end && pattern_code(*after)) {
                    p = after;
                    high = upper;
                }
            }
            if (p < end && pattern_code(*p)) kind = pattern_code(*p++);
            else literal_length = (size_t)(p - literal);
        } else {
            do { ++p; } while (p < end && !ascii_digit(*p) && *p != '\'' && *p != '"' &&
                               !pattern_ellipsis(p, end));
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
    pattern_extended = jbc_emulation_prime || field;
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

#ifdef JBC_TIMESTAMP
const char *jbc_timestamp(const char *file, int line, int column)
{
    struct timespec now;
    if (clock_gettime(CLOCK_REALTIME, &now) != 0)
        numeric_error(file, line, column, "TIMESTAMP cannot read the UTC clock");
    intmax_t seconds = now.tv_sec;
    long fraction = now.tv_nsec;
    int negative = seconds < 0;
    if (negative && fraction) {
        /* POSIX normalizes the fractional part to a positive value. */
        ++seconds;
        fraction = 1000000000L - fraction;
    }
    uintmax_t magnitude = seconds < 0 ? (uintmax_t)(-(seconds + 1)) + 1 : (uintmax_t)seconds;
    char text[sizeof(intmax_t) * CHAR_BIT + 12];
    snprintf(text, sizeof text, "%s%" PRIuMAX ".%09ld", negative ? "-" : "", magnitude, fraction);
    struct decimal value;
    if (!parse_decimal(text, &value))
        numeric_error(file, line, column, "invalid UTC clock value");
    limit_places(&value, jbc_precision < 0 ? 4 : jbc_precision);
    return fmt_decimal(value, value.places);
}
#endif

#ifdef JBC_TIMESTAMP
/* MAKETIMESTAMP, LOCALDATE, LOCALTIME and TIMEDIFF work in whole
   milliseconds of UTC time since 1970-01-01, internal date 732. */
enum { UNIX_EPOCH_ORDINAL = JBC_DATE_EPOCH + 732, UNIX_EPOCH_DATE = 732 };

static int64_t floor_div(int64_t a, int64_t b)
{
    int64_t q = a / b;
    return (a % b && (a < 0) != (b < 0)) ? q - 1 : q;
}

static int64_t milliseconds(const char *text, const char *what, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(text, &n)) numeric_error(file, line, column, what);
    if (n.digits > 15) numeric_error(file, line, column, "time value out of range");
    int64_t value = 0;
    for (size_t i = 0; i < n.digits; ++i) value = value * 10 + (n.whole[i] - '0');
    value *= 1000;
    for (size_t i = 0, place = 100; i < n.places && place; ++i, place /= 10)
        value += (int64_t)(n.fraction[i] - '0') * (int64_t)place;
    return n.sign < 0 ? -value : value;
}

static const char *milliseconds_value(int64_t ms)
{
    int64_t whole = ms / 1000, part = ms % 1000;
    if (part < 0) part = -part;
    char *out = allocate(32);
    int n = snprintf(out, 32, "%s%" PRId64, ms < 0 && whole == 0 ? "-" : "", whole);
    if (part) {
        n += snprintf(out + n, (size_t)(32 - n), ".%03d", (int)part);
        while (out[n - 1] == '0') out[--n] = '\0';
    }
    return out;
}

struct zone_scope {
    int active;
    char *saved;
};

/* An empty zone is the process's own; another name is set as TZ for the
   conversion. WASI has no zone database, so its clock is UTC. */
static void enter_zone(const char *zone, struct zone_scope *scope, const char *file, int line, int column)
{
    scope->active = 0;
    scope->saved = NULL;
    if (!*zone) return;
#ifdef __wasi__
    if (strcmp(zone, "UTC") && strcmp(zone, "GMT"))
        numeric_error(file, line, column, "named time zones require a zone database");
#else
    const char *old = getenv("TZ");
    if (old) {
        scope->saved = malloc(strlen(old) + 1);
        if (!scope->saved) fail("out of memory");
        strcpy(scope->saved, old);
    }
    if (setenv("TZ", zone, 1) != 0) numeric_error(file, line, column, "cannot set the time zone");
    scope->active = 1;
    tzset();
#endif
}

static void leave_zone(struct zone_scope *scope)
{
#ifndef __wasi__
    if (!scope->active) return;
    if (scope->saved) setenv("TZ", scope->saved, 1);
    else unsetenv("TZ");
    free(scope->saved);
    tzset();
#else
    (void)scope;
#endif
}

/* Seconds that the current zone adds to UTC second t. */
static int64_t zone_offset(int64_t t, const char *file, int line, int column)
{
    time_t stamp = (time_t)t;
    struct tm local;
    if ((int64_t)stamp != t || !localtime_r(&stamp, &local))
        numeric_error(file, line, column, "time value out of range");
    int64_t years = local.tm_year + 1900 - 1;
    int64_t days = years * 365 + years / 4 - years / 100 + years / 400 + local.tm_yday - UNIX_EPOCH_ORDINAL;
    return days * 86400 + local.tm_hour * 3600 + local.tm_min * 60 + local.tm_sec - t;
}

const char *jbc_maketimestamp(const char *date, const char *time, const char *zone,
                              const char *file, int line, int column)
{
    int64_t day = milliseconds(date, "MAKETIMESTAMP requires a numeric internal date", file, line, column);
    int64_t clock = milliseconds(time, "MAKETIMESTAMP requires a numeric internal time", file, line, column);
    if (day % 1000) numeric_error(file, line, column, "MAKETIMESTAMP requires a whole internal date");
    int64_t local = (day / 1000 - UNIX_EPOCH_DATE) * 86400000 + clock;
    int64_t seconds = floor_div(local, 1000);
    struct zone_scope scope;
    enter_zone(zone, &scope, file, line, column);
    /* Find the UTC second whose local reading is this one; the second pass
       settles a guess that crossed a daylight saving change. */
    int64_t utc = seconds - zone_offset(seconds, file, line, column);
    utc = seconds - zone_offset(utc, file, line, column);
    leave_zone(&scope);
    return milliseconds_value(local + (utc - seconds) * 1000);
}

static int64_t local_seconds(const char *stamp, const char *zone, const char *what,
                             const char *file, int line, int column)
{
    int64_t seconds = floor_div(milliseconds(stamp, what, file, line, column), 1000);
    struct zone_scope scope;
    enter_zone(zone, &scope, file, line, column);
    int64_t local = seconds + zone_offset(seconds, file, line, column);
    leave_zone(&scope);
    return local;
}

const char *jbc_localdate(const char *stamp, const char *zone, const char *file, int line, int column)
{
    int64_t local = local_seconds(stamp, zone, "LOCALDATE requires a numeric timestamp", file, line, column);
    char *out = allocate(24);
    snprintf(out, 24, "%" PRId64, floor_div(local, 86400) + UNIX_EPOCH_DATE);
    return out;
}

const char *jbc_localtime(const char *stamp, const char *zone, const char *file, int line, int column)
{
    int64_t local = local_seconds(stamp, zone, "LOCALTIME requires a numeric timestamp", file, line, column);
    return size_value((uintmax_t)(local - floor_div(local, 86400) * 86400));
}

/* Days from 1970-01-01 to a proleptic Gregorian date, and back. */
static int64_t timediff_days(int64_t year, int month, int day)
{
    year -= month <= 2;
    int64_t era = (year >= 0 ? year : year - 399) / 400;
    int64_t yoe = year - era * 400;
    int64_t doy = (153 * (month + (month > 2 ? -3 : 9)) + 2) / 5 + day - 1;
    return era * 146097 + yoe * 365 + yoe / 4 - yoe / 100 + doy - 719468;
}

static void timediff_civil(int64_t days, int64_t *year, int *month, int *day)
{
    days += 719468;
    int64_t era = (days >= 0 ? days : days - 146096) / 146097;
    int64_t doe = days - era * 146097;
    int64_t yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    int64_t doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    int64_t mp = (5 * doy + 2) / 153;
    *day = (int)(doy - (153 * mp + 2) / 5 + 1);
    *month = (int)(mp < 10 ? mp + 3 : mp - 9);
    *year = yoe + era * 400 + (*month <= 2);
}

/* The UTC instant `months` calendar months after `start`, keeping its time
   of day and clamping the day to the end of the month: 31 January plus one
   month is the last day of February. */
static int64_t add_calendar_months(int64_t start, int64_t months)
{
    int64_t day_ms = 86400000, days = start / day_ms - (start % day_ms < 0);
    int64_t time = start - days * day_ms, year;
    int month, day;
    timediff_civil(days, &year, &month, &day);
    int64_t index = year * 12 + (month - 1) + months;
    year = index / 12 - (index % 12 < 0);
    month = (int)(index - year * 12) + 1;
    int64_t next = month == 12 ? timediff_days(year + 1, 1, 1) : timediff_days(year, month + 1, 1);
    int last = (int)(next - timediff_days(year, month, 1));
    return timediff_days(year, month, day < last ? day : last) * day_ms + time;
}

/* TIMEDIFF(first, second, mask) is second - first, as TAFC PB201214
   computes it; every field carries that sign. Masks 2 to 7 count calendar
   months or years forward from the earlier timestamp (UTC), clamping to the
   end of a shorter month, and split the rest into weeks, days, hours,
   minutes, seconds and milliseconds (tests/tafc/timediff.b). */
const char *jbc_timediff(const char *first, const char *second, const char *mask,
                         const char *file, int line, int column)
{
    int64_t a = milliseconds(first, "TIMEDIFF requires numeric timestamps", file, line, column);
    int64_t b = milliseconds(second, "TIMEDIFF requires numeric timestamps", file, line, column);
    int64_t m = milliseconds(*mask ? mask : "0", "TIMEDIFF requires a mask from 0 to 7", file, line, column);
    if (m % 1000 || m < 0 || m > 7000) numeric_error(file, line, column, "TIMEDIFF requires a mask from 0 to 7");
    int code = (int)(m / 1000);
    int64_t sign = b < a ? -1 : 1, low = b < a ? b : a, high = b < a ? a : b;
    int64_t fields[8], *f = fields;
    int years = code >= 4, months = code == 2 || code == 3 || code >= 6;
    int weeks = code == 1 || code == 3 || code == 5 || code == 7;
    if (years || months) {
        /* Count from the first timestamp towards the second, forwards or
           backwards: TAFC gives -1^-30 for one order of 2020-01-31 and
           2021-03-01 and 1^29 for the other. */
        int64_t from_days = a / 86400000 - (a % 86400000 < 0);
        int64_t to_days = b / 86400000 - (b % 86400000 < 0), fy, ty;
        int fm, fd, tm, td;
        timediff_civil(from_days, &fy, &fm, &fd);
        timediff_civil(to_days, &ty, &tm, &td);
        int64_t count = months ? (ty - fy) * 12 + (tm - fm) : ty - fy;
        count *= sign;
        int64_t step = months ? 1 : 12;
        for (; count > 0; --count) {
            int64_t moved = add_calendar_months(a, sign * count * step);
            if (sign > 0 ? moved <= b : moved >= b) break;
        }
        if (count < 0) count = 0;
        int64_t total = count * step, moved = add_calendar_months(a, sign * total);
        low = sign > 0 ? moved : b;
        high = sign > 0 ? b : moved;
        if (years) *f++ = total / 12;
        if (months) *f++ = years ? total % 12 : total;
    }
    int64_t rest = high - low, days = rest / 86400000;
    if (weeks) { *f++ = days / 7; days %= 7; }
    *f++ = days;
    *f++ = rest / 3600000 % 24;
    *f++ = rest / 60000 % 60;
    *f++ = rest / 1000 % 60;
    *f++ = rest % 1000;
    char *out = allocate(8 * 22);
    size_t n = 0;
    for (int64_t *p = fields; p < f; ++p)
        n += (size_t)snprintf(out + n, 8 * 22 - n, "%s%" PRId64, p == fields ? "" : "\376", *p * sign);
    return out;
}
#endif

/* @TIMEZONE: jBASE reads the zone from its environment. jbcc uses
   JBASE_TIMEZONE, then TZ, else an empty string (provisional). */
const char *jbc_timezone(void)
{
    const char *zone = getenv("JBASE_TIMEZONE");
    if (!zone || !*zone) zone = getenv("TZ");
    return zone ? zone : "";
}

const char *jbc_uniquekey(const char *file, int line, int column)
{
    unsigned char bytes[16];
#ifdef __wasi__
    if (__wasi_random_get(bytes, sizeof bytes))
        numeric_error(file, line, column, "UNIQUEKEY cannot get random bytes");
#else
    FILE *random = fopen("/dev/urandom", "rb");
    if (!random) numeric_error(file, line, column, "UNIQUEKEY cannot open /dev/urandom");
    size_t count = fread(bytes, 1, sizeof bytes, random);
    fclose(random);
    if (count != sizeof bytes)
        numeric_error(file, line, column, "UNIQUEKEY cannot read /dev/urandom");
#endif

    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    static const char hex[] = "0123456789abcdef";
    char *value = allocate(37);
    char *out = value;
    for (size_t i = 0; i < sizeof bytes; ++i) {
        if (i == 4 || i == 6 || i == 8 || i == 10) *out++ = '-';
        *out++ = hex[bytes[i] >> 4];
        *out++ = hex[bytes[i] & 0x0f];
    }
    *out = '\0';
    return value;
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

/* @DAY, @MONTH and @YEAR: the day of the month, the month and the
   two-digit year of @DATE (TAFC PB201214 prints 27, 11 and 26 on
   27 November 2026). */
const char *jbc_startup_date_part(char part, const char *file, int line, int column)
{
    if (!have_startup_clock) numeric_error(file, line, column, "@DATE cannot read startup clock");
    int value = part == 'D' ? startup_clock.tm_mday : part == 'M' ? startup_clock.tm_mon + 1
              : (startup_clock.tm_year + 1900) % 100;
    char *out = allocate(3);
    snprintf(out, 4, part == 'Y' ? "%02d" : "%d", value);
    return out;
}

enum input_conversion { ICONV_UNSUPPORTED, ICONV_DATE, ICONV_DATE_EUROPEAN, ICONV_TIME, ICONV_HEX };

/* D masks for ICONV: D, an optional year width, an optional separator and
   an optional E for day before month, as in D4/E; DG reads YYYYMMDD too. */
static enum input_conversion input_mask(const char *mask)
{
    if (!strcmp(mask, "MX")) return ICONV_HEX;
    if (!strcmp(mask, "MT") || !strcmp(mask, "MTS")) return ICONV_TIME;
    if (*mask++ != 'D') return ICONV_UNSUPPORTED;
    if (!strcmp(mask, "G")) return ICONV_DATE;
    if (ascii_digit((unsigned char)*mask)) ++mask;
    if (*mask && *mask != 'E' && !ascii_digit((unsigned char)*mask) && !ascii_alpha((unsigned char)*mask))
        ++mask;
    /* TAFC PB201214 reads any code that starts with D as a date and
       ignores options it does not know (tests/tafc/conversion-chains.b). */
    return *mask == 'E' && (!mask[1] || (unsigned char)mask[1] == 253) ? ICONV_DATE_EUROPEAN
                                                                     : ICONV_DATE;
}

static int month_of_name(const char *word, size_t length)
{
    static const char *const names[] = {"JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
        "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"};
    if (length < 3) return 0;
    for (int m = 0; m < 12; ++m) {
        size_t full = strlen(names[m]);
        if (length > full) continue;
        size_t i = 0;
        while (i < length && (word[i] & ~0x20) == names[m][i]) ++i;
        if (i == length) return m + 1;
    }
    return 0;
}

/* ICONV date as TAFC PB201214 reads it (tests/tafc/iconv-dates.b):
   YYYYMMDD; a day, a month name or abbreviation and a year in either order,
   as in 31 JAN 2020, JAN 31 2020 or 31JAN20; or numbers, month first (day
   first with an E mask), the year defaulting to the current one. A day past
   the end of its month rolls forward and sets STATUS 3; anything else that
   is not a date gives '' and STATUS 1. Two-digit years from 30 are 19xx and
   below 30 are 20xx (provisional). */
static const char *input_date(const char *value, int european, int *status)
{
    long numbers[3];
    size_t widths[3], count = 0;
    int month = 0;
    const char *p = value;
    while (*p) {
        if (ascii_digit((unsigned char)*p)) {
            size_t width = strspn(p, "0123456789");
            if (count == 3 || width > 8) goto invalid;
            numbers[count] = 0;
            for (size_t i = 0; i < width; ++i) numbers[count] = numbers[count] * 10 + (p[i] - '0');
            widths[count++] = width;
            p += width;
        } else if (ascii_alpha((unsigned char)*p)) {
            size_t width = 0;
            while (ascii_alpha((unsigned char)p[width])) ++width;
            if (month || !(month = month_of_name(p, width))) goto invalid;
            p += width;
        } else if (strchr(" /-.,", *p)) {
            ++p;
        } else {
            goto invalid;
        }
    }
    long year, day;
    int year_width = 4;
    if (!month && count == 1 && widths[0] == 8) {
        year = numbers[0] / 10000;
        month = (int)(numbers[0] / 100 % 100);
        day = numbers[0] % 100;
    } else if (!month && count == 1 && widths[0] == 7) {
        /* YYYYDDD, a year and a day of the year: 2012123 is 2 May 2012. */
        year = numbers[0] / 1000;
        long day_of_year = numbers[0] % 1000;
        if (year < 1 || day_of_year < 1) goto invalid;
        *status = 0;
        return internal_date((int)year, (int)day_of_year);
    } else if (month && (count == 1 || count == 2)) {
        day = numbers[0];
        year = count == 2 ? numbers[1] : -1;
        if (count == 2) year_width = (int)widths[1];
    } else if (!month && (count == 2 || count == 3)) {
        long first = numbers[0], second = numbers[1];
        month = (int)(european ? second : first);
        day = european ? first : second;
        year = count == 3 ? numbers[2] : -1;
        if (count == 3) year_width = (int)widths[2];
    } else {
        goto invalid;
    }
    if (year < 0) {
        time_t now = time(NULL);
        const struct tm *today = now == (time_t)-1 ? NULL : localtime(&now);
        if (!today) goto invalid;
        year = today->tm_year + 1900;
    } else if (year_width <= 2) {
        year += year < 30 ? 2000 : 1900;
    }
    if (year < 1 || year > 9999 || month < 1 || month > 12 || day < 1 || day > 99) goto invalid;
    *status = day > month_length((int)year, month) ? 3 : 0;
    int day_of_year = (int)day;
    for (int m = 1; m < month; ++m) day_of_year += month_length((int)year, m);
    return internal_date((int)year, day_of_year);

invalid:
    *status = 1;
    return "";
}

/* ICONV time: H:MM or H:MM:SS with an optional AM or PM. As in TAFC
   PB201214, hours, minutes and seconds may overflow (25:00 is 90000 and
   12:99 is 49140); the MT mask then sets STATUS 3, MTS does not. */
static const char *input_time(const char *value, int seconds_mask, int *status)
{
    const char *p = value;
    size_t width = strspn(p, "0123456789");
    if (!width || width > 4 || p[width] != ':') goto invalid;
    size_t hour = read_decimal_count(&p, p + width);
    size_t minute, second = 0;
    ++p;
    width = strspn(p, "0123456789");
    if (!width || width > 4) goto invalid;
    minute = read_decimal_count(&p, p + width);
    if (*p == ':') {
        ++p;
        width = strspn(p, "0123456789");
        if (!width || width > 4) goto invalid;
        second = read_decimal_count(&p, p + width);
    }
    while (*p == ' ') ++p;
    /* PM adds 12 to an hour below 12; AM changes nothing, so 12:34 AM is
       45240 as in TAFC. */
    if (!strcmp(p, "AM") || !strcmp(p, "PM")) {
        if (hour > 12) goto invalid;
        if (*p == 'P' && hour < 12) hour += 12;
    } else if (*p) goto invalid;
    *status = !seconds_mask && (minute >= 60 || second >= 60) ? 3 : 0;
    return size_value(hour * 3600 + minute * 60 + second);

invalid:
    *status = 1;
    return "";
}

/* MX: pairs of hex digits to bytes, as in ICONV('4020412042', 'MX'). */
/* MX: hex digit pairs to bytes, up to the first pair that is not hex; an
   odd last digit is ignored, as TAFC PB201214 reads ICONV('414', 'MX') as
   "A". A 00 pair ends the result too, since strings cannot hold NUL yet. */
static const char *input_hex(const char *value, const char **error)
{
    size_t n = strlen(value), used = 0;
    char *out = allocate(n / 2);
    for (size_t i = 0; i + 1 < n; i += 2) {
        int high = hex_value(value[i]), low = hex_value(value[i + 1]);
        if (high < 0 || low < 0 || !(high | low)) break;
        out[used++] = (char)(high * 16 + low);
    }
    out[used] = '\0';
    if (!used && n) *error = "ICONV MX found no hexadecimal pair";
    return used || !n ? out : NULL;
}

static const char *convert_input(const char *value, enum input_conversion conversion,
                                 const char *mask, int *status)
{
    *status = 0;
    if (conversion == ICONV_HEX) {
        const char *error = NULL;
        const char *result = input_hex(value, &error);
        if (result) return result;
        *status = 1;
        return "";
    }
    if (conversion == ICONV_TIME) return input_time(value, !strcmp(mask, "MTS"), status);
    return input_date(value, conversion == ICONV_DATE_EUROPEAN, status);
}

/* ICONV sets STATUS(): 0 when the conversion succeeds, 1 when the value or
   the mask is not valid (the result is then ''), 3 when a date or time
   rolled over. An unknown mask warns, as TAFC prints "Unknown conversion
   code.", and execution continues. */
static const char *iconv_code(const char *value, const char *mask, const char *file, int line,
                              int column)
{
    /* An empty mask returns the value unchanged (TAFC PB201214). */
    if (!*mask) return value;
    /* MC codes convert as in OCONV and leave STATUS() alone (TAFC). */
    const char *converted = mc_conversion(value, mask, file, line, column);
    if (converted) return converted;
    struct md_mask md;
    if (md_parse(mask, &md)) {
        int status;
        const char *result = md_input(value, &md, &status);
        last_file_status = status;
        return result;
    }
    enum input_conversion conversion = input_mask(mask);
    if (conversion == ICONV_UNSUPPORTED) {
        fprintf(stderr, "%s:%d:%d: warning: unsupported ICONV mask '%s' -- Unknown conversion code.\n",
                file, line, column, mask);
        last_file_status = 1;
        return "";
    }
    int status;
    const char *result = convert_input(value, conversion, mask, &status);
    /* A time that converts cleanly leaves STATUS() as it was (TAFC). */
    if (status || conversion != ICONV_TIME) last_file_status = status;
    return result;
}

/* A date code with no part letter (D, D4, D/, but not DD or DM) takes the
   value mark after it and the rest of the mask as its own options, as in
   TAFC PB201214: ICONV(X, 'D':@VM:'D4') is ICONV(X, 'D'). */
static int whole_date_code(const char *code)
{
    return *code == 'D' && !(code[1] && strchr("DMJQWYG", code[1]));
}

/* Codes separated by value marks apply in turn, left to right, as in TAFC
   PB201214 (tests/tafc/conversion-chains.b): OCONV(X, 'MCU':@VM:'MCT')
   is OCONV(OCONV(X, 'MCU'), 'MCT'). */
static const char *convert_chain(const char *value, const char *mask,
                                 const char *(*code)(const char *, const char *, const char *,
                                                     int, int),
                                 const char *file, int line, int column)
{
    if (!strchr(mask, 253)) return code(value, mask, file, line, column);
    const char *codes = mask;
    while (codes) {
        if (whole_date_code(codes)) return code(value, codes, file, line, column);
        value = code(value, take_field(&codes, 253), file, line, column);
    }
    return value;
}

const char *jbc_iconv(const char *value, const char *mask, const char *file, int line, int column)
{
    return convert_chain(value, mask, iconv_code, file, line, column);
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
    int width, european, name, seconds, twelve;
};

static int output_mask(const char *mask, struct output_conversion *conversion)
{
    *conversion = (struct output_conversion){.width = 4};
    if (strncmp(mask, "MT", 2) == 0) {
        const char *suffix = mask + 2;
        conversion->part = 'T';
        /* MTH: a 12-hour clock with AM or PM, 12:00AM for 0 (TAFC). */
        conversion->twelve = *suffix == 'H';
        if (conversion->twelve) ++suffix;
        conversion->seconds = *suffix == 'S';
        if (conversion->seconds) ++suffix;
        return !*suffix || !strcmp(suffix, ":");
    }

    if (*mask != 'D') return 0;
    /* DG writes YYYYMMDD, which T24 R19 slices as [1,4], [5,2] and [7,2]. */
    if (!strcmp(mask, "DG")) {
        conversion->part = 'G';
        return 1;
    }
    const char *p = mask + 1;
    if (*p && strchr("DMJQWY", *p)) conversion->part = *p++;
    /* A width above 4 shows four digits, as TAFC prints OCONV(0, 'D5/'). */
    if ((!conversion->part || conversion->part == 'Y') && *p >= '0' && *p <= '9') {
        conversion->width = *p++ - '0';
        if (conversion->width > 4) conversion->width = 4;
    }
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
        /* A value mark ends the code; TAFC ignores what follows. */
        if ((unsigned char)*p == 253) return 1;
    } else if (!conversion->part && (unsigned char)*p == 253 && !p[1]) {
        /* D followed by a value mark and nothing else: the mark is the
           separator, as TAFC writes OCONV(0, 'D':@VM:'') as 12]31]1967. */
        conversion->separator = *p;
        return 1;
    }
    return !*p;
}

static const char *convert_output(const char *value, const struct output_conversion *conversion,
                                  const char **error)
{
    static const char *const weekdays[] = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY",
        "FRIDAY", "SATURDAY", "SUNDAY"};

    struct decimal n;
    /* As in TAFC PB201214 (tests/tafc/iconv-dates.b): hours go past 23
       (99999 is 27:46:39), nonnumeric text is 00:00:00 with STATUS 1, a
       fraction is dropped and a negative count gives its magnitude
       (-1 is 00:00:01). */
    if (conversion->part == 'T') {
        long seconds = 0;
        if (parse_decimal(value, &n) && n.sign >= 0 && n.digits <= 9)
            for (size_t i = 0; i < n.digits; ++i) seconds = seconds * 10 + (n.whole[i] - '0');
        else if (parse_decimal(value, &n))
            for (size_t i = 0; i < n.digits && n.digits <= 9; ++i) seconds = seconds * 10 + (n.whole[i] - '0');
        else {
            /* '' gives '' and text 00:00:00, both with STATUS() 1. */
            last_file_status = 1;
            if (!*value) return "";
        }
        long hours = seconds / 3600;
        const char *suffix = "";
        if (conversion->twelve) {
            suffix = hours % 24 < 12 ? "AM" : "PM";
            hours = hours % 12 ? hours % 12 : 12;
        }
        char *out = allocate(28);
        if (conversion->seconds)
            snprintf(out, 29, "%02ld:%02ld:%02ld%s", hours, seconds / 60 % 60, seconds % 60, suffix);
        else
            snprintf(out, 29, "%02ld:%02ld%s", hours, seconds / 60 % 60, suffix);
        return out;
    }

    /* A date that is not a number comes back as it is, with STATUS 1, and
       a fractional day count is truncated toward zero, as in TAFC. */
    if (!parse_decimal(value, &n)) {
        last_file_status = 1;
        return value;
    }
    char whole[32];
    if (n.digits > 18) {
        *error = "integer operand out of range";
        return NULL;
    }
    snprintf(whole, sizeof whole, "%s%.*s", n.sign < 0 ? "-" : "", (int)n.digits, n.whole);
    if (!n.digits) strcpy(whole, "0");
    errno = 0;
    intmax_t days = strtoimax(whole, NULL, 10);
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
    if (part == 'G') {
        char *out = allocate(8);
        snprintf(out, 9, "%04d%02d%02d", year, month + 1, day);
        return out;
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

/* OCONV L codes as TAFC PB201214 applies them (tests/tafc/
   conversion-tests.b): L followed by no digit gives the length; Ln gives
   the value when it has at most n bytes, else ''; Ln,m gives it when it has
   n to m bytes, else '' with STATUS() 1. */
static const char *length_test(const char *value, const char *mask, const char *file, int line,
                               int column)
{
    const char *p = mask + 1;
    size_t length = strlen(value);
    if (!ascii_digit((unsigned char)*p)) return size_value(length);
    uintmax_t low = 0, high;
    while (ascii_digit((unsigned char)*p)) low = low * 10 + (uintmax_t)(*p++ - '0');
    if (*p != ',') return length <= low ? value : "";
    ++p;
    if (!ascii_digit((unsigned char)*p)) {
        fprintf(stderr, "%s:%d:%d: warning: OCONV mask '%s' -- Missing Parameter 2.\n",
                file, line, column, mask);
        last_file_status = 1;
        return "";
    }
    high = 0;
    while (ascii_digit((unsigned char)*p)) high = high * 10 + (uintmax_t)(*p++ - '0');
    if (length >= low && length <= high) return value;
    last_file_status = 1;
    return "";
}

/* OCONV R codes are range tests in TAFC PB201214, not FMT masks:
   Rn,m{;n,m}... with integer bounds gives a number inside any range and
   otherwise '' with STATUS() 1. Any other R mask prints "Error in Range
   Test." and gives ''. */
static const char *range_test(const char *value, const char *mask, const char *file, int line,
                              int column)
{
    struct decimal n;
    int numeric = *value && parse_decimal(value, &n), inside = 0;
    const char *p = mask + 1;
    for (;;) {
        char *end;
        long long low, high;
        if (!(ascii_digit((unsigned char)*p) || (*p == '-' && ascii_digit((unsigned char)p[1]))))
            goto invalid;
        low = strtoll(p, &end, 10);
        if (*end != ',') goto invalid;
        p = end + 1;
        if (!(ascii_digit((unsigned char)*p) || (*p == '-' && ascii_digit((unsigned char)p[1]))))
            goto invalid;
        high = strtoll(p, &end, 10);
        if (low > high) goto invalid;
        if (numeric) {
            char bound[24];
            snprintf(bound, sizeof bound, "%lld", low);
            int above = jbc_compare(value, bound, -1) >= 0;
            snprintf(bound, sizeof bound, "%lld", high);
            if (above && jbc_compare(value, bound, -1) <= 0) inside = 1;
        }
        p = end;
        if (!*p) break;
        if (*p++ != ';') goto invalid;
    }
    if (inside) return value;
    last_file_status = 1;
    return "";

invalid:
    fprintf(stderr, "%s:%d:%d: warning: OCONV mask '%s' -- Error in Range Test.\n",
            file, line, column, mask);
    last_file_status = 1;
    return "";
}

static const char *oconv_code(const char *value, const char *mask, const char *file, int line,
                              int column)
{
    /* An empty mask returns the value unchanged (TAFC PB201214). */
    if (!*mask) return value;
    struct md_mask md;
    if (md_parse(mask, &md)) {
        last_file_status = 0;
        return md_output(value, &md);
    }
    const char *converted = mc_conversion(value, mask, file, line, column);
    if (converted) return converted;
    if (strcmp(mask, "MX") == 0) return hex_bytes(value);
    if (*mask == 'G' && (converted = group_extract(value, mask))) return converted;
    if (*mask == 'L') return length_test(value, mask, file, line, column);
    if (*mask == 'R') return range_test(value, mask, file, line, column);
    struct output_conversion conversion;
    /* A mask that starts with a digit is an FMT mask, as in OCONV(X, '6R');
       it sets STATUS() 0. */
    if (!output_mask(mask, &conversion) && ascii_digit((unsigned char)*mask)) {
        last_file_status = 0;
        return jbc_fmt(value, mask, file, line, column);
    }
    if (*mask == 'D' && !output_mask(mask, &conversion)) {
        /* A D code with options TAFC cannot read gives the value back,
           with STATUS() 1 for text, as in OCONV(X, 'DUMMY'). */
        struct decimal n;
        if (!*value || !parse_decimal(value, &n)) last_file_status = 1;
        return value;
    }
    if (!output_mask(mask, &conversion)) {
        /* TAFC prints "Unknown conversion code.", returns '' and sets
           STATUS 1; execution continues. */
        fprintf(stderr, "%s:%d:%d: warning: unsupported OCONV mask '%s' -- Unknown conversion code.\n",
                file, line, column, mask);
        last_file_status = 1;
        return "";
    }
    const char *error = NULL;
    const char *result = convert_output(value, &conversion, &error);
    if (!result) numeric_error(file, line, column, error);
    return result;
}

const char *jbc_oconv(const char *value, const char *mask, const char *file, int line, int column)
{
    return convert_chain(value, mask, oconv_code, file, line, column);
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

const char *jbc_trim_array(const char *source, char mode)
{
    char *out = strcpy(allocate(strlen(source)), source);
    const char *set = mode == 'R' ? " " : " \t";
    char *write = out, *item = out;
    for (;;) {
        char *end = item + strcspn(item, "\376\375\374");
        char mark = *end;
        *end = '\0';
        write = trim_element(write, item, set, mode);
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

const char *jbc_utf8(const char *value)
{
    const unsigned char *bytes = (const unsigned char *)value;
    size_t length = strlen(value), extra = 0;
    for (size_t i = 0; i < length; ++i)
        if (bytes[i] >= 0x80) ++extra;
    if (extra > SIZE_MAX - length) fail("UTF8 result is too large");
    char *out = allocate(length + extra);
    unsigned char *write = (unsigned char *)out;
    for (size_t i = 0; i < length; ++i) {
        unsigned char c = bytes[i];
        if (c < 0x80) {
            *write++ = c;
        } else {
            *write++ = 0xc0 | (c >> 6);
            *write++ = 0x80 | (c & 0x3f);
        }
    }
    *write = 0;
    return out;
}

const char *jbc_latin1(const char *value, const char *file, int line, int column)
{
    char *out = allocate(strlen(value));
    unsigned char *write = (unsigned char *)out;
    const unsigned char *read = (const unsigned char *)value;
    while (*read) {
        if (*read < 0x80) {
            *write++ = *read++;
        } else if ((*read == 0xc2 || *read == 0xc3) && read[1] >= 0x80 && read[1] <= 0xbf) {
            *write++ = (unsigned char)(((*read & 0x03) << 6) | (read[1] & 0x3f));
            read += 2;
        } else {
            numeric_error(file, line, column, "LATIN1 requires UTF-8 representable in ISO-8859-1");
        }
    }
    *write = 0;
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

const char *jbc_checksum(const char *text, const char *file, int line, int column)
{
    const unsigned char *byte = (const unsigned char *)text;
    uintmax_t sum = 0;
    for (uintmax_t position = 1; *byte; ++position, ++byte) {
        if (position > (UINTMAX_MAX - sum) / *byte)
            numeric_error(file, line, column, "CHECKSUM result out of range");
        sum += position * *byte;
    }
    return size_value(sum);
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
                       const char *limit, const char *first,
                       const char *message, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(limit, &n) || n.places || !parse_decimal(first, &n) || n.places)
        numeric_error(file, line, column, message);
    int64_t count = integer(limit, file, line, column);
    int64_t start = integer(first, file, line, column);
    /* An empty search string changes nothing (TAFC, tests/tafc/search-edges.b). */
    if (!*search) return text;
    return change_substrings(text, search, replacement, count, start);
}

/* COUNT, COUNTS and DCOUNT: TAFC PB201214 counts nonoverlapping matches
   under prime and overlapping ones under jbase (tests/tafc/
   emulation-rules-*.b). */
static size_t count_matches(const char *s, const char *needle)
{
    if (jbc_emulation_prime || !*needle) return occurrences(s, needle);
    size_t count = 0;
    while ((s = strstr(s, needle)) != NULL) {
        ++count;
        ++s;
    }
    return count;
}

const char *jbc_count(const char *s, const char *separator)
{
    return size_value(count_matches(s, separator));
}

const char *jbc_dcount(const char *s, const char *separator)
{
    if (!*s) return "0";
    if (!*separator) return jbc_len(s);
    return size_value(1 + count_matches(s, separator));
}

/* A FIELD position or count below 1 means 1 (TAFC, tests/tafc/field-edges.b). */
static int64_t field_index(const char *s, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(s, &n) || n.places)
        numeric_error(file, line, column, "FIELD requires integer positions and counts");
    int64_t value = n.sign <= 0 ? 1 : integer(s, file, line, column);
    return value < 1 ? 1 : value;
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

/* GROUPSTORE value IN target USING start, replace, delimiter: with replace
   0, value goes in before group start; otherwise it replaces group start.
   Missing groups are added empty, and a start below 1 means 1. The guide's
   example and TAFC PB201214 (tests/tafc/groupstore.b) agree. */
const char *jbc_groupstore(const char *target, const char *value, const char *start,
                           const char *replace, const char *delimiter,
                           const char *file, int line, int column)
{
    int64_t first = field_index(start, file, line, column);
    struct decimal n;
    int replacing = parse_decimal(replace, &n) && n.sign != 0;
    size_t width = strlen(delimiter);
    if (!width) return replacing ? value : jbc_concat(value, target);
    /* Find the start of group first, padding with delimiters if needed. */
    const char *p = target;
    int64_t group = 1;
    while (group < first) {
        const char *next = strstr(p, delimiter);
        if (!next) break;
        p = next + width;
        ++group;
    }
    const char *prefix_end = p, *suffix = p;
    size_t padding = (size_t)(first - group);
    if (padding) {
        prefix_end = target + strlen(target);
        suffix = prefix_end;
    } else if (replacing) {
        const char *next = strstr(p, delimiter);
        suffix = next ? next : p + strlen(p);
    }
    size_t prefix = (size_t)(prefix_end - target), added = strlen(value), rest = strlen(suffix);
    size_t size = prefix + padding * width + added + (replacing || padding ? 0 : width) + rest;
    char *out = allocate(size), *w = out;
    memcpy(w, target, prefix);
    w += prefix;
    for (size_t i = 0; i < padding; ++i) { memcpy(w, delimiter, width); w += width; }
    memcpy(w, value, added);
    w += added;
    if (!replacing && !padding) { memcpy(w, delimiter, width); w += width; }
    memcpy(w, suffix, rest);
    w[rest] = '\0';
    return out;
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

const char *jbc_field_replace(const char *s, const char *separator, const char *start,
                              const char *count, const char *file, int line, int column,
                              const char *replacement, int append)
{
    int64_t first = field_index(start, file, line, column);
    int64_t length = field_index(count, file, line, column);
    size_t width = strlen(separator), size = strlen(s), take;
    const char *selected = field_range(s, separator, width, first, length, &take);
    size_t prefix = selected ? (size_t)(selected - s) : size;
    size_t padding = 0;
    if (!selected) {
        if (!width)
            numeric_error(file, line, column, "cannot extend fields with an empty delimiter");
        uintmax_t missing = (uintmax_t)(first - 1) - occurrences(s, separator);
        if (missing > SIZE_MAX / width)
            numeric_error(file, line, column, "field replacement is too large");
        padding = (size_t)missing * width;
    }
    if (append) {
        prefix += take;
        take = 0;
    }
    size_t kept = size - take, added = strlen(replacement);
    if (padding > SIZE_MAX - kept || added > SIZE_MAX - kept - padding)
        numeric_error(file, line, column, "field replacement is too large");
    char *out = allocate(kept + padding + added);
    memcpy(out, s, prefix);
    for (size_t offset = 0; offset < padding; offset += width)
        memcpy(out + prefix + offset, separator, width);
    memcpy(out + prefix + padding, replacement, added);
    memcpy(out + prefix + padding + added, s + prefix + take, size - prefix - take + 1);
    return out;
}

/* REUSE of a dynamic array has no effect: its elements pair as usual
   (TAFC PB201214: ADDS(REUSE(1:@VM:2), 3) is 4]2). */
const char *jbc_reuse_scalar(const char *value, const char *message, const char *file, int line, int column)
{
    (void)message, (void)file, (void)line, (void)column;
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
    cursor.reuse = reuse && !strpbrk(text, "\376\375\374");
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

const char *jbc_nums(const char *source)
{
    size_t marks = 0;
    char *items = split_array_items(source, &marks);
    if (marks > (SIZE_MAX - 1) / 2) fail("NUMS result too large");
    char *out = allocate(2 * marks + 1), *write = out;
    for (const char *item = items;;) {
        const char *end = item + strlen(item);
        char mark = source[end - items];
        *write++ = *jbc_num(item);
        *write++ = mark;
        if (!mark) break;
        item = end + 1;
    }
    free(items);
    return out;
}

/* Apply a scalar function to each element, keeping the original marks. */
static const char *map_elements(const char *source, const char *(*each)(const char *))
{
    char *items = split_array_items(source, NULL);
    const char *out = "";
    for (const char *item = items;;) {
        const char *end = item + strlen(item);
        char mark[2] = {source[end - items], '\0'};
        out = jbc_concat(out, jbc_concat(each(item), mark));
        if (!*mark) break;
        item = end + 1;
    }
    free(items);
    return out;
}

const char *jbc_nots(const char *source)
{
    return map_elements(source, jbc_not);
}

const char *jbc_lens(const char *source)
{
    return map_elements(source, jbc_len);
}

const char *jbc_counts(const char *source, const char *needle)
{
    size_t length = strlen(source), marks = 0;
    char *items = split_array_items(source, &marks);
    /* A count fits within each nonempty item. Empty items grow by one byte. */
    if (marks >= SIZE_MAX - length) fail("COUNTS result too large");
    size_t capacity = length + marks + 1;
    char *out = allocate(capacity), *write = out;
    for (const char *item = items;;) {
        const char *end = item + strlen(item);
        char mark = source[end - items];
        size_t available = capacity - (size_t)(write - out) + 1;
        write += snprintf(write, available, "%zu", count_matches(item, needle));
        *write++ = mark;
        if (!mark) break;
        item = end + 1;
    }
    free(items);
    return out;
}

/* ICONVS and OCONVS apply the whole chain of codes to each element, as
   TAFC PB201214 does (tests/tafc/conversion-chains.b), and keep every
   element: one that does not convert becomes what ICONV or OCONV gives it.
   Each element sets STATUS() as ICONV or OCONV would, so the last one
   decides what is left. */
static const char *convert_array(const char *source, const char *mask, int input,
                                 const char *file, int line, int column)
{
    char *items = split_array_items(source, NULL);
    const size_t limit = SIZE_MAX - sizeof(struct jbc_buffer) - 1;
    size_t capacity = strlen(source), used = 0;
    char *out = allocate(capacity);
    for (const char *item = items;;) {
        const char *value = convert_chain(item, mask, input ? iconv_code : oconv_code,
                                          file, line, column);
        const char *end = item + strlen(item);
        char mark = source[end - items];
        size_t bytes = strlen(value), separator = mark != '\0';
        if (bytes > limit - used || separator > limit - used - bytes)
            numeric_error(file, line, column, input ? "ICONVS result too large"
                                                    : "OCONVS result too large");
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
    return out;
}

const char *jbc_iconvs(const char *source, const char *mask, const char *file, int line, int column)
{
    if (!*mask) numeric_error(file, line, column, "ICONVS requires a conversion mask");
    return convert_array(source, mask, 1, file, line, column);
}

const char *jbc_oconvs(const char *source, const char *mask, const char *file, int line, int column)
{
    if (!*mask) numeric_error(file, line, column, "OCONVS requires a conversion mask");
    return convert_array(source, mask, 0, file, line, column);
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

static const char *prime_element(const char *item, const char *file, int line, int column)
{
    struct decimal n;
    const char *value = trim_blanks(item);
    if (!*value) return "0";
    if (parse_decimal(value, &n)) return value;
    fprintf(stderr, "%s:%d:%d: warning: Non-numeric value -- ZERO USED\n", file, line, column);
    return "0";
}

static const char *array_arithmetic(char op, int warn_on_zero_divisor, const char *left, const char *right,
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
        if (jbc_emulation_prime) {
            /* Prime: a missing or empty element is 0, and a nonnumeric one
               warns and is 0 (TAFC PB201214, tests/snippets/adds.b). */
            const char *x = prime_element(lhs.present ? a : "", file, line, column);
            const char *y = prime_element(rhs.present ? b : "", file, line, column);
            item = arithmetic(op, x, y, 1, file, line, column);
        } else if (op == '-') {
            const char *minuend = lhs.present && *a ? a : "0";
            const char *subtrahend = rhs.present && *b ? b : "0";
            item = jbc_arithmetic('-', minuend, subtrahend, file, line, column);
        } else if (!lhs.present || !rhs.present) {
            item = "0";
            if (op == '+') item = lhs.present ? a : b;
            else if (op == '/' && lhs.present) item = a;
        } else if (*a && *b) {
            item = arithmetic(op, a, b, warn_on_zero_divisor, file, line, column);
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
    return array_arithmetic('+', 0, left, right, reuse_left, reuse_right, file, line, column);
}

const char *jbc_subs(const char *left, const char *right, int reuse_left, int reuse_right,
                     const char *file, int line, int column)
{
    return array_arithmetic('-', 0, left, right, reuse_left, reuse_right, file, line, column);
}

const char *jbc_muls(const char *left, const char *right, int reuse_left, int reuse_right,
                     const char *file, int line, int column)
{
    return array_arithmetic('*', 0, left, right, reuse_left, reuse_right, file, line, column);
}

const char *jbc_divs(const char *left, const char *right, int reuse_left, int reuse_right,
                     const char *file, int line, int column)
{
    return array_arithmetic('/', 1, left, right, reuse_left, reuse_right, file, line, column);
}

const char *jbc_divide_reuse(const char *left, const char *right, int reuse_left, int reuse_right,
                             const char *file, int line, int column)
{
    return array_arithmetic('/', 0, left, right, reuse_left, reuse_right, file, line, column);
}

static const char *array_sign(const char *source, int absolute, const char *file, int line, int column)
{
    if (!*source) return "0";
    size_t marks = 0, length = strlen(source);
    char *items = split_array_items(source, &marks);
    /* A decimal can gain a minus sign and a leading zero. */
    const size_t limit = SIZE_MAX - sizeof(struct jbc_buffer) - 1;
    if (length > limit || marks + 1 > (limit - length) / 2)
        numeric_error(file, line, column, absolute ? "ABSS result too large" : "NEGS result too large");
    char *out = allocate(length + 2 * (marks + 1)), *write = out;
    for (const char *item = items;;) {
        const char *value = "";
        if (!*item) value = "0"; /* TAFC PB201214 under both emulations */
        else if (*item && absolute)
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

enum array_order { ARRAY_LESS = 1, ARRAY_EQUAL = 2, ARRAY_GREATER = 4 };

static int array_pair_matches(const char *left, const char *right, unsigned orders)
{
    int compare = jbc_compare(left, right, jbc_precision);
    unsigned order = compare < 0 ? ARRAY_LESS : compare > 0 ? ARRAY_GREATER : ARRAY_EQUAL;
    return (orders & order) != 0;
}

static const char *compare_array_items(const char *left, const char *right, int reuse_left,
                                       int reuse_right, unsigned orders, char unmatched)
{
    struct array_cursor lhs = array_cursor(left, reuse_left, 1);
    struct array_cursor rhs = array_cursor(right, reuse_right, 1);
    if (lhs.mark == 256 && rhs.mark == 256)
        return !*left || !*right ? "" : (array_pair_matches(left, right, orders) ? "1" : "0");

    size_t marks = 0;
    char *a = split_array_items(left, &marks);
    char *b = split_array_items(right, &marks);
    if (marks > (SIZE_MAX - 1) / 2) fail("array comparison result too large");
    char *out = allocate(2 * marks + 1), *write = out;
    for (;;) {
        if (unmatched && (!lhs.present || !rhs.present)) {
            *write++ = unmatched;
        } else if ((!lhs.present || lhs.length) && (!rhs.present || rhs.length)) {
            const char *value_left = lhs.present ? a + (lhs.item - left) : "";
            const char *value_right = rhs.present ? b + (rhs.item - right) : "";
            *write++ = array_pair_matches(value_left, value_right, orders) ? '1' : '0';
        }
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
    return compare_array_items(left, right, reuse_left, reuse_right, ARRAY_EQUAL, '0');
}

const char *jbc_nes(const char *left, const char *right, int reuse_left, int reuse_right)
{
    return compare_array_items(left, right, reuse_left, reuse_right, ARRAY_LESS | ARRAY_GREATER, '1');
}

const char *jbc_les(const char *left, const char *right, int reuse_left, int reuse_right)
{
    return compare_array_items(left, right, reuse_left, reuse_right, ARRAY_LESS | ARRAY_EQUAL, 0);
}

const char *jbc_lts(const char *left, const char *right, int reuse_left, int reuse_right)
{
    return compare_array_items(left, right, reuse_left, reuse_right, ARRAY_LESS, 0);
}

const char *jbc_ges(const char *left, const char *right, int reuse_left, int reuse_right)
{
    return compare_array_items(left, right, reuse_left, reuse_right, ARRAY_GREATER | ARRAY_EQUAL, 0);
}

const char *jbc_gts(const char *left, const char *right, int reuse_left, int reuse_right)
{
    return compare_array_items(left, right, reuse_left, reuse_right, ARRAY_GREATER, 0);
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
    int foreign, shared; /* shared: taken by READL or READVL */
    char key[];
};

struct memory_file {
    struct memory_file *next;
    struct memory_record *records, *last_read;
    struct record_lock *locks;
    size_t serial;
    int file_locked;
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

static int has_foreign_record_lock(const struct memory_file *file)
{
    for (const struct record_lock *lock = file->locks; lock; lock = lock->next)
        if (lock->foreign) return 1;
    return 0;
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
    lock->shared = 0;
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
            p->file->file_locked = 0;
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
    if (f) count_userstat(&record_open_count);
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
    f->file_locked = 0;
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

void jbc_selecte(jbc_variable *list, jbc_variable *setting)
{
    jbc_variable *dest = list_slot(list);
    if (setting) assign_value(setting, "0");
    if (select_lists[0].value) *dest = select_lists[0];
    else assign_value(dest, "");
    file_result(0);
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
    if (has_foreign_record_lock(file)) {
        /* Keep the original error status unless a LOCKED arm handles it. */
        if (setting) assign_value(setting, "32768");
        file_result(32768);
        return JBC_LOCKED;
    }
    clear_records(file);
    release_locks(file, NULL, 0);
    count_userstat(&record_clear_count);
    return file_result(0);
}

int jbc_filelock(const char *handle, jbc_variable *setting)
{
    struct memory_file *file = file_for(handle);
    if (setting) assign_value(setting, file ? "0" : "128");
    if (!file) return file_result(128);
    if (has_foreign_record_lock(file)) {
        if (setting) assign_value(setting, "32768");
        file_result(32768);
        return JBC_LOCKED;
    }
    file->file_locked = 1;
    return file_result(0);
}

int jbc_fileunlock(const char *handle)
{
    struct memory_file *file = file_for(handle);
    if (!file) return file_succeeded(128);
    file->file_locked = 0;
    return file_succeeded(0);
}

int jbc_delete_record(const char *handle, const char *key, jbc_variable *setting)
{
    struct memory_file *f = file_for(handle);
    if (setting) assign_value(setting, f ? "0" : "128");
    if (!f) return file_result(128);
    struct record_lock *lock = find_lock(f, key);
    if (lock && lock->foreign) {
        if (setting) assign_value(setting, "32768");
        file_result(32768);
        return JBC_LOCKED;
    }
    release_locks(f, key, 0);
    struct memory_record **link = record_link(f, key);
    if (*link) {
        struct memory_record *record = *link;
        *link = record->next;
        if (f->last_read == record) f->last_read = NULL;
        free_record(record);
    }
    count_userstat(&record_delete_count);
    return file_result(0);
}

/* TRANS and XLATE (file, key, field, code), as TAFC PB201214 runs them
   (tests/tafc/trans-xlate.b): field -1 is the whole record and field 0 the
   key; the result has its marks lowered one level (field marks to value
   marks, value marks to subvalue marks, subvalue marks to text marks). For a missing record, or an empty field with C,
   the code decides: X gives '', C the key, V warns and gives ''. A key with
   value marks gives one result per key. "DICT name" reads the dictionary. */
const char *jbc_trans(const char *filename, const char *keys, const char *field,
                      const char *code, const char *file, int line, int column)
{
    const char *section = "", *name = filename;
    if (!strncmp(filename, "DICT ", 5)) {
        section = "DICT";
        name = filename + 5;
    }
    struct memory_file *f = find_memory_file(section, name);
    if (!f) numeric_error(file, line, column, jbc_concat("TRANS cannot open file ", filename));
    struct decimal n;
    if (!parse_decimal(field, &n) || n.places)
        numeric_error(file, line, column, "TRANS requires an integer field number");
    int64_t position = integer(field, file, line, column);
    char action = *code ? *code : 'X';
    const char *out = "";
    char *items = split_array_items(keys, NULL);
    for (const char *key = items;;) {
        const char *end = key + strlen(key);
        struct memory_record *r = *record_link(f, key);
        const char *value = "";
        if (r && position == 0) {
            value = key;
        } else if (r) {
            char index[24];
            snprintf(index, sizeof index, "%" PRId64, position);
            value = position < 0 ? r->value : jbc_array(r->value, (const char *[]){index}, 1, NULL);
            char *lowered = strcpy(allocate(strlen(value)), value);
            for (char *c = lowered; *c; ++c)
                if ((unsigned char)*c >= 252 && (unsigned char)*c <= 254) --*c;
            value = lowered;
        }
        if ((!r || !*value) && action == 'C') {
            value = key;
        } else if (!r && action == 'V') {
            fprintf(stderr, "%s:%d:%d: warning: record %s is not on file %s\n", file, line, column,
                    key, filename);
        }
        out = jbc_concat(out, value);
        if (!keys[end - items]) break;
        out = jbc_concat(out, "\375");
        key = end + 1;
    }
    free(items);
    return out;
}

int jbc_read_record(const char *handle, const char *key, jbc_variable *out, jbc_variable *setting)
{
    struct memory_file *f = file_for(handle);
    struct memory_record *r = f ? *record_link(f, key) : NULL;
    assign_value(out, r ? strcpy(allocate(strlen(r->value)), r->value) : "");
    if (setting) assign_value(setting, r ? "" : "128");
    if (r) count_userstat(&record_read_count);
    return file_result(r ? 0 : 128);
}

const char *jbc_recordlocked(const char *handle, const char *key)
{
    struct memory_file *f = file_for(handle);
    if (f && f->file_locked) return "2";
    struct record_lock *lock = f ? find_lock(f, key) : NULL;
    /* 1 for this process's READL lock and 2 for its READU lock, as the
       guide's table and TAFC PB201214 give them (tests/tafc/shared-locks.b). */
    return !lock ? "0" : lock->foreign ? "-2" : lock->shared ? "1" : "2";
}

int jbc_release_lock(const char *handle, const char *key)
{
    if (key) {
        struct memory_file *f = file_for(handle);
        if (!f) return 128;
        release_locks(f, key, 0);
    } else {
        for (struct memory_file *f = files; f; f = f->next)
            release_locks(f, NULL, 0);
    }
    return 0;
}

static int lock_for_update(struct memory_file *f, const char *key, jbc_variable *setting,
                           int shared)
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
    if (!lock) {
        add_lock(f, key, 0);
        f->locks->shared = shared;
    } else if (!shared) {
        lock->shared = 0;
    }
    return 0;
}

static int read_locked(const char *handle, const char *key, jbc_variable *out, jbc_variable *setting,
                       int shared)
{
    struct memory_file *f = file_for(handle);
    if (!f) assign_value(out, "");
    int status = lock_for_update(f, key, setting, shared);
    if (status) return file_result(status);
    return jbc_read_record(handle, key, out, setting);
}

int jbc_readu(const char *handle, const char *key, jbc_variable *out, jbc_variable *setting)
{
    return read_locked(handle, key, out, setting, 0);
}

/* READL takes a shared lock, which only another process's READU blocks. */
int jbc_readl(const char *handle, const char *key, jbc_variable *out, jbc_variable *setting)
{
    return read_locked(handle, key, out, setting, 1);
}

int jbc_recordlocku(const char *handle, const char *key, jbc_variable *setting)
{
    int status = lock_for_update(file_for(handle), key, setting, 0);
    if (!status && setting) assign_value(setting, "");
    return file_result(status);
}

int jbc_matread(const char *handle, const char *key, jbc_variable *dest, int rank,
                const int *bounds, size_t storage_count, jbc_variable *setting, int update)
{
    last_matrix_load = 0;
    struct memory_file *f = file_for(handle);
    if (update) {
        int status = lock_for_update(f, key, setting, 0);
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
    count_userstat(&record_read_count);
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
        int status = lock_for_update(f, key, setting, update == 2); /* 2: READVL */
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
    if (record) count_userstat(&record_read_count);
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
    count_userstat(&record_write_count);
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
                 const int *bounds, jbc_variable *setting, int keep_lock, const char *name,
                 const char *file, int line, int column)
{
    const char *record = jbc_matbuild(src, rank, bounds, NULL, NULL, "\376", name, file, line, column);
    int status = write_record_status(handle, key, record, 0, keep_lock);
    if (setting) {
        const char *result = status == 128 ? "128" : "32768";
        assign_value(setting, status ? result : jbc_dcount(record, "\376"));
    }
    return file_result(status);
}

const char *jbc_char(const char *value, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n))
        numeric_error(file, line, column, "CHAR requires a number");
    /* The integer part modulo 256, as TAFC PB201214 gives it: CHAR(300) is
       ',' and CHAR(-1) is byte 255 (tests/tafc/char-bytes.b). */
    unsigned int code = 0;
    for (size_t i = 0; i < n.digits; ++i)
        code = (code * 10 + (unsigned int)(n.whole[i] - '0')) % 256;
    if (n.sign < 0) code = (256 - code) % 256;
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
    if (remaining < 1) return "0";
    /* An empty needle is found at position 1 (TAFC, tests/tafc/search-edges.b). */
    if (!width) return "1";
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

static uint32_t decimal_word(const char *value, const char *message,
                             const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(value, &n))
        numeric_error(file, line, column, message);
    uint32_t bits = 0;
    for (size_t i = 0; i < n.digits; ++i)
        bits = (uint32_t)(UINT64_C(10) * bits + (unsigned)(n.whole[i] - '0'));
    return n.sign < 0 ? (uint32_t)(0u - bits) : bits;
}

/* The bit functions' operand as TAFC PB201214 takes it (tests/tafc/
   bit-unsigned.b): the integer part's low 32 bits; an empty or nonnumeric
   operand is 0, as is a value outside the signed 64-bit range. */
static uint32_t bit_operand(const char *value)
{
    struct decimal n;
    if (!parse_decimal(value, &n) || n.digits > 19) return 0;
    uint64_t magnitude = 0;
    for (size_t i = 0; i < n.digits; ++i)
        magnitude = UINT64_C(10) * magnitude + (unsigned)(n.whole[i] - '0');
    if (magnitude > (uint64_t)INT64_MAX + (n.sign < 0)) return 0;
    return (uint32_t)(n.sign < 0 ? 0u - magnitude : magnitude);
}

static const char *signed_word_value(uint32_t bits)
{
    int64_t result = bits <= INT32_MAX ? (int64_t)bits : (int64_t)bits - (INT64_C(1) << 32);
    char *out = allocate(11);
    snprintf(out, 12, "%" PRId64, result);
    return out;
}

static const char *unsigned_word_value(uint32_t bits)
{
    char *out = allocate(10);
    snprintf(out, 11, "%" PRIu32, bits);
    return out;
}

/* BITAND, BITOR, BITXOR and BITNOT return unsigned 32-bit values. */
const char *jbc_bitxor(const char *left, const char *right, const char *file, int line, int column)
{
    (void)file, (void)line, (void)column;
    return unsigned_word_value(bit_operand(left) ^ bit_operand(right));
}

const char *jbc_bitand(const char *left, const char *right, const char *file, int line, int column)
{
    (void)file, (void)line, (void)column;
    return unsigned_word_value(bit_operand(left) & bit_operand(right));
}

const char *jbc_bitnot(const char *value, const char *file, int line, int column)
{
    (void)file, (void)line, (void)column;
    return unsigned_word_value(~bit_operand(value));
}

const char *jbc_bitor(const char *left, const char *right, const char *file, int line, int column)
{
    (void)file, (void)line, (void)column;
    return unsigned_word_value(bit_operand(left) | bit_operand(right));
}

const char *jbc_dtx(const char *value, const char *file, int line, int column)
{
    uint32_t bits = decimal_word(value, "DTX requires a numeric operand", file, line, column);
    char *out = allocate(8);
    snprintf(out, 9, "%" PRIX32, bits);
    return out;
}

const char *jbc_xtd(const char *value)
{
    uint32_t bits = 0;
    for (; *value; ++value) {
        unsigned digit;
        if (*value >= '0' && *value <= '9') digit = *value - '0';
        else if (*value >= 'A' && *value <= 'F') digit = *value - 'A' + 10;
        else if (*value >= 'a' && *value <= 'f') digit = *value - 'a' + 10;
        else break;
        bits = (uint32_t)(UINT64_C(16) * bits + digit);
    }
    return signed_word_value(bits);
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
/* The reference compiles FSUB to its floating-point routine, unlike "-".
   The guide's example, 2.54 - 5.703358 at PRECISION 7, prints -3.163358,
   so the double result is rounded to the precision. */
static const char *significant_value(long double value, const char *name, const char *file,
                                     int line, int column);

const char *jbc_fsub(const char *left, const char *right, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(left, &n) || !parse_decimal(right, &n) || !*left || !*right)
        numeric_error(file, line, column, "FSUB requires numeric operands");
    long double value = (long double)strtod(left, NULL) - (long double)strtod(right, NULL);
    return significant_value(value, "FSUB", file, line, column);
}

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
    return format_decimal(logl(value));
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
    return format_decimal(result);
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
    return format_decimal(sqrtl(value));
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
    return format_decimal(result);
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
    return format_decimal(sinl(radians(s, file, line, column)));
}

const char *jbc_cos(const char *s, const char *file, int line, int column)
{
    return format_decimal(cosl(radians(s, file, line, column)));
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
                 jbc_variable *return_list, const char *file, int line, int column)
{
    if (return_list)
        numeric_error(file, line, column, "RTNLIST requires a jBC command backend");
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
        count_userstat(&command_count);
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
    count_userstat(&command_count);
}

/* CHAIN and ENTER run a command and do not return: the program ends with
   the command's exit status (guide, CHAIN and ENTER). The (I option, which
   passes COMMON to a jBC program, is dropped; separately built jbcc
   programs share no COMMON. */
void jbc_chain(const char *command, const char *file, int line, int column)
{
    size_t length = strlen(command);
    char *text = strcpy(allocate(length), command);
    char *option = strrchr(text, '(');
    if (option && (option[1] == 'I' || option[1] == 'i') && !option[2]) {
        while (option > text && option[-1] == ' ') --option;
        *option = '\0';
    }
    jbc_execute(text, NULL, NULL, NULL, file, line, column);
    fflush(stdout);
    jbc_terminate(last_command_code > 255 ? 255 : (int)last_command_code);
}
#endif

#ifdef JBC_SLEEP
static void pause_for(struct timespec delay, const char *failure, const char *file, int line, int column)
{
    while (delay.tv_sec || delay.tv_nsec) {
        struct timespec remaining;
        if (nanosleep(&delay, &remaining) == 0) break;
        if (errno != EINTR) numeric_error(file, line, column, failure);
        delay = remaining;
    }
}

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
    pause_for(delay, "SLEEP failed", file, line, column);
}

void jbc_msleep(const char *duration, const char *file, int line, int column)
{
    struct decimal n;
    if (!parse_decimal(duration, &n) || n.sign < 0)
        numeric_error(file, line, column, "MSLEEP requires a nonnegative duration in milliseconds");
    int64_t milliseconds = n.digits ? integer(duration, file, line, column) : 0;
    struct timespec delay = {(time_t)(milliseconds / 1000), (long)(milliseconds % 1000) * 1000000L};
    if (delay.tv_sec != milliseconds / 1000)
        numeric_error(file, line, column, "MSLEEP duration out of range");
    pause_for(delay, "MSLEEP failed", file, line, column);
}

/* PAUSE and WAKE within one process: a WAKE for this process cancels the
   next PAUSE, as the guide describes; otherwise PAUSE waits for its
   timeout, or forever without one, since no other process can wake it. */
static int wake_pending;

void jbc_pause(const char *timeout, const char *file, int line, int column)
{
    if (wake_pending) {
        wake_pending = 0;
        return;
    }
    if (timeout) {
        jbc_sleep(timeout, file, line, column);
        return;
    }
    for (;;) pause_for((struct timespec){3600, 0}, "PAUSE failed", file, line, column);
}
#endif

void jbc_wake(const char *port)
{
    (void)port;
#ifdef JBC_SLEEP
    wake_pending = 1;
#endif
}

#ifdef JBC_TERMINAL
#ifdef __wasi__
/* The playground provides a finite byte stream in place of a terminal. */
static int stream_input_byte(void)
{
    if (!input_data) return fgetc(stdin);
    int c = input_data->bytes[input_data->offset++];
    if (input_data->offset == input_data->length) drop_input_chunk();
    return c;
}

int jbc_input(jbc_variable *out, const char *cursor, const char *limit_text, int suppress_newline, int discard_excess,
              const char *timeout_text, const char *file, int line, int column)
{
    (void)suppress_newline;
    int64_t limit = limit_text ? truncated(limit_text, file, line, column) : 0;
    if (limit < -1) numeric_error(file, line, column, "negative INPUT length");
    if (timeout_text) numeric_error(file, line, column, "timed INPUT is unavailable in the browser");
    if (limit == -1) {
        int ready = input_data != NULL;
        if (!ready) {
            int c = fgetc(stdin);
            ready = c != EOF && ungetc(c, stdin) != EOF;
            if (ferror(stdin)) numeric_error(file, line, column, "cannot read input");
        }
        assign_value(out, ready ? "1" : "0");
        return ready;
    }
    if ((cursor && fputs(cursor, stdout) == EOF) ||
        fputs(jbc_input_prompt, stdout) == EOF || fflush(stdout))
        numeric_error(file, line, column, "cannot write input prompt");
    char *text = NULL;
    size_t length = 0, capacity = 0;
    while (discard_excess || !limit_text || length < (uint64_t)limit) {
        int c = stream_input_byte();
        if (c == EOF || c == '\n') break;
        if (discard_excess && length == (uint64_t)limit) continue;
        if (c == 0) { free(text); numeric_error(file, line, column, "INPUT cannot store a NUL byte"); }
        if (length == capacity) {
            if (capacity > SIZE_MAX / 2) { free(text); numeric_error(file, line, column, "input line too long"); }
            capacity = capacity ? 2 * capacity : 128;
            char *grown = realloc(text, capacity);
            if (!grown) { free(text); numeric_error(file, line, column, "out of memory"); }
            text = grown;
        }
        text[length++] = (char)c;
    }
    if (ferror(stdin)) { free(text); numeric_error(file, line, column, "cannot read input"); }
    char *value = allocate(length);
    if (length) memcpy(value, text, length);
    value[length] = '\0';
    free(text);
    assign_value(out, input_null_value(value, cursor));
    count_userstat(&input_count);
    return 1;
}
#else
#include <fcntl.h>
#include <signal.h>
#include <termios.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <unistd.h>

/* Some input operations need each keystroke before the line is submitted. */
static struct termios input_saved;
static volatile sig_atomic_t input_modified;
static int input_echo = -1;
static const int input_signals[] = {SIGINT, SIGTERM, SIGHUP, SIGQUIT, SIGPIPE};

struct input_mode {
    struct sigaction saved[sizeof input_signals / sizeof *input_signals];
    size_t handlers;
};

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

static const char *set_input_mode(struct input_mode *state, struct termios *mode)
{
    struct sigaction action = {0};
    action.sa_handler = input_signal;
    sigemptyset(&action.sa_mask);
    for (; state->handlers < sizeof input_signals / sizeof *input_signals; ++state->handlers) {
        size_t i = state->handlers;
        int sig = input_signals[i];
        if (sigaction(sig, NULL, &state->saved[i]) ||
            (state->saved[i].sa_handler == SIG_DFL && sigaction(sig, &action, NULL)))
            return "cannot protect input terminal settings";
    }
    mode->c_lflag &= ~(ICANON | ECHO | ECHONL);
    mode->c_cc[VMIN] = 1;
    mode->c_cc[VTIME] = 0;
    input_modified = 1;
    return tcsetattr(STDIN_FILENO, TCSANOW, mode) ? "cannot set input terminal mode" : NULL;
}

static const char *restore_input_mode(struct input_mode *state, const char *error)
{
    if (input_modified && tcsetattr(STDIN_FILENO, TCSANOW, &input_saved))
        error = "cannot restore input terminal mode";
    input_modified = 0;
    while (state->handlers) {
        --state->handlers;
        sigaction(input_signals[state->handlers], &state->saved[state->handlers], NULL);
    }
    return error;
}

static ssize_t read_input_byte(unsigned char *c)
{
    if (!input_data) return read(STDIN_FILENO, c, 1);
    *c = input_data->bytes[input_data->offset++];
    if (input_data->offset == input_data->length) drop_input_chunk();
    return 1;
}

static const char *pending_stdin_bytes(int *bytes)
{
    *bytes = 0;
    struct input_mode state = {0};
    const char *error = NULL;
    if (isatty(STDIN_FILENO)) {
        if (tcgetattr(STDIN_FILENO, &input_saved))
            return "cannot read input terminal settings";
        if (input_saved.c_lflag & ICANON) {
            /* A canonical terminal can hide pending bytes until Enter. */
            struct termios mode = input_saved;
            error = set_input_mode(&state, &mode);
        }
    }
    if (!error) {
        int result;
        do {
            result = ioctl(STDIN_FILENO, FIONREAD, bytes);
        } while (result < 0 && errno == EINTR);
        if (result < 0) {
            /* Devices such as /dev/null have no input queue to inspect. */
            if (errno != ENODEV && errno != ENOTTY && errno != EOPNOTSUPP)
                error = "cannot query pending input bytes";
            *bytes = 0;
        }
    }
    return restore_input_mode(&state, error);
}

static int input_available(const char *file, int line, int column)
{
    if (fflush(stdout)) numeric_error(file, line, column, "cannot flush output before input poll");
    if (input_data) return 1;

    int bytes;
    const char *error = pending_stdin_bytes(&bytes);
    if (error) numeric_error(file, line, column, error);
    return bytes > 0;
}

/* IN var {FOR tenths}: the code of the next byte read from standard input,
   not from the DATA queue, as TAFC PB201214 reads it (x is 120). With FOR,
   it waits that many tenths of a second and returns 0, leaving var as it
   was, when nothing arrives. Without FOR, end of input is an error. */
int jbc_in(jbc_variable *out, const char *timeout, const char *file, int line, int column)
{
    if (fflush(stdout)) numeric_error(file, line, column, "cannot flush output before IN");
    struct input_mode state = {0};
    const char *error = NULL;
    if (isatty(STDIN_FILENO)) {
        if (tcgetattr(STDIN_FILENO, &input_saved))
            numeric_error(file, line, column, "cannot read input terminal settings");
        struct termios mode = input_saved;
        mode.c_lflag &= ~(ICANON | ECHO | IEXTEN);
        mode.c_iflag &= ~(ICRNL | INLCR | IGNCR | ISTRIP);
        mode.c_cc[VMIN] = 1;
        mode.c_cc[VTIME] = 0;
        error = set_input_mode(&state, &mode);
    }
    int ready = 1;
    if (!error && timeout) {
        struct decimal n;
        if (!parse_decimal(timeout, &n) || n.sign < 0)
            error = "IN FOR requires a nonnegative number of tenths of a second";
        else {
            int64_t tenths = n.digits ? integer(timeout, file, line, column) : 0;
            struct timespec interval = {(time_t)(tenths / 10), (long)(tenths % 10) * 100000000L};
            fd_set readable;
            do {
                FD_ZERO(&readable);
                FD_SET(STDIN_FILENO, &readable);
                ready = pselect(STDIN_FILENO + 1, &readable, NULL, NULL, &interval, NULL);
            } while (ready < 0 && errno == EINTR);
            if (ready < 0) error = "cannot wait for input";
        }
    }
    unsigned char c = 0;
    ssize_t count = 0;
    if (!error && ready > 0) {
        do {
            count = read(STDIN_FILENO, &c, 1);
        } while (count < 0 && errno == EINTR);
        if (count < 0) error = "cannot read IN input";
        else if (!count && !timeout) error = "IN reached the end of input";
    }
    error = restore_input_mode(&state, error);
    if (error) numeric_error(file, line, column, error);
    if (count <= 0) return 0;
    assign_value(out, size_value(c));
    return 1;
}

const char *jbc_keyin(const char *file, int line, int column)
{
    if (fflush(stdout)) numeric_error(file, line, column, "cannot flush output before KEYIN");
    struct input_mode state = {0};
    const char *error = NULL;
    if (!input_data && isatty(STDIN_FILENO)) {
        if (tcgetattr(STDIN_FILENO, &input_saved))
            numeric_error(file, line, column, "cannot read input terminal settings");
        struct termios mode = input_saved;
        mode.c_lflag &= ~IEXTEN;
        mode.c_iflag &= ~(ICRNL | INLCR | IGNCR | ISTRIP);
        error = set_input_mode(&state, &mode);
    }

    unsigned char c;
    ssize_t count = 0;
    if (!error) {
        do {
            count = read_input_byte(&c);
        } while (count < 0 && errno == EINTR);
        if (count < 0) error = "cannot read KEYIN input";
    }
    error = restore_input_mode(&state, error);
    if (error) numeric_error(file, line, column, error);
    if (!count) return "";
    if (!c) numeric_error(file, line, column, "KEYIN cannot store a NUL byte");
    char *value = allocate(1);
    value[0] = (char)c;
    value[1] = '\0';
    return value;
}

int jbc_input(jbc_variable *out, const char *cursor, const char *limit_text, int suppress_newline, int discard_excess,
              const char *timeout_text, const char *file, int line, int column)
{
    struct input_mode state = {0};
    int echo_fd = -1, edit = 0;
    const char *error = NULL;
    char *text = NULL;
    size_t length = 0, capacity = 0;

    int64_t limit = limit_text ? truncated(limit_text, file, line, column) : 0;
    if (limit < -1) numeric_error(file, line, column, "negative INPUT length");
    int64_t ticks = timeout_text ? truncated(timeout_text, file, line, column) : 0;
    if (ticks < 0) numeric_error(file, line, column, "negative INPUT timeout");
    if (limit == -1) {
        int ready = input_available(file, line, column);
        assign_value(out, ready ? "1" : "0");
        return ready;
    }
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
            struct termios mode = input_saved;
            edit = (mode.c_lflag & ICANON) != 0;
            error = set_input_mode(&state, &mode);
        }
    }
    if (!error && ((cursor && fputs(cursor, stdout) == EOF) ||
                   fputs(jbc_input_prompt, stdout) == EOF || fflush(stdout)))
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
        ssize_t count = read_input_byte(&c);
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
    error = restore_input_mode(&state, error);
    if (echo_fd >= 0) close(echo_fd);
    if (error) {
        free(text);
        numeric_error(file, line, column, error);
    }
    char *value = allocate(length);
    if (length) memcpy(value, text, length);
    value[length] = '\0';
    free(text);
    assign_value(out, input_null_value(value, cursor));
    if (!timed_out) count_userstat(&input_count);
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
    /* Keys whose TAFC PB201214 values are fixed or come from the process
       (tests/tafc/system-keys.b): no printer (1), the terminal's width and
       depth (2, 3: COLUMNS and LINES, else 80 and 24), its type (7),
       milliseconds since midnight (12), the C locale's language, decimal
       places, thousands and decimal separators and currency (35 to 39), the
       program name (40) and the platform (1017). */
    if (!jbc_compare(code, "1", -1)) return "0";
    if (!jbc_compare(code, "2", -1) || !jbc_compare(code, "3", -1)) {
        const char *size = getenv(!jbc_compare(code, "2", -1) ? "COLUMNS" : "LINES");
        struct decimal n;
        if (size && parse_decimal(size, &n) && n.sign > 0 && !n.places) return size;
        return !jbc_compare(code, "2", -1) ? "80" : "24";
    }
    if (!jbc_compare(code, "7", -1)) {
        const char *term = getenv("TERM");
        return term ? term : "";
    }
    if (!jbc_compare(code, "12", -1)) {
        struct timespec now;
        if (clock_gettime(CLOCK_REALTIME, &now)) numeric_error(file, line, column, "SYSTEM(12) cannot read the clock");
        time_t seconds = now.tv_sec;
        struct tm local;
        if (!localtime_r(&seconds, &local)) numeric_error(file, line, column, "SYSTEM(12) cannot read the clock");
        uintmax_t ms = ((uintmax_t)local.tm_hour * 3600 + (uintmax_t)local.tm_min * 60 + (uintmax_t)local.tm_sec) * 1000
                     + (uintmax_t)(now.tv_nsec / 1000000);
        return size_value(ms);
    }
    if (!jbc_compare(code, "35", -1)) return "C";
    if (!jbc_compare(code, "36", -1)) return "0";
    if (!jbc_compare(code, "37", -1)) return ",";
    if (!jbc_compare(code, "38", -1)) return ".";
    if (!jbc_compare(code, "39", -1)) return "$";
    if (!jbc_compare(code, "40", -1)) {
        const char *name = command_argc ? command_argv[0] : "";
        const char *slash = strrchr(name, '/');
        return slash ? slash + 1 : name;
    }
    if (!jbc_compare(code, "1017", -1)) return "UNIX";
    const char *assigned = assigned_system_key(code);
    if (assigned) return assigned;
    /* Keys T24 reads, with TAFC PB201214's values where jbcc has no
       counterpart (tests/tafc/system-keys.b): 11 the default select list's
       count, 1021 the release (T24 tests [1,4] for TAFJ and looks for
       TEMENOS), 1019 the host, and zeros or empty strings for the
       transaction (47), port (43), phantom (25), UTF-8 (1025), call stack
       (1029), after-image (1039) and platform (91 is 0 for UNIX) keys. */
    if (!jbc_compare(code, "11", -1)) return jbc_selected();
    if (!jbc_compare(code, "1021", -1))
        return "201214.0\3760.0\376\376jbcc, compatible with TEMENOS TAFC PB201214";
    if (!jbc_compare(code, "1019", -1)) {
#ifdef __wasi__
        return "";
#else
        struct utsname host;
        if (uname(&host)) return "";
        return jbc_concat(jbc_concat(host.sysname, " "), jbc_concat(jbc_concat(host.nodename, " "), host.release));
#endif
    }
    static const char *const zeros[] = {"25", "32", "43", "47", "91", "600", "1025", "2003", "2021"};
    for (size_t i = 0; i < sizeof zeros / sizeof *zeros; ++i)
        if (!jbc_compare(code, zeros[i], -1)) return "0";
    if (!jbc_compare(code, "1027", -1) || !jbc_compare(code, "1029", -1) ||
        !jbc_compare(code, "1039", -1) || !jbc_compare(code, "2090", -1))
        return "";
    if (jbc_compare(code, "14", -1))
        numeric_error(file, line, column, jbc_concat("unsupported SYSTEM key ", code));
    fflush(stdout);
    int bytes;
    const char *error = pending_stdin_bytes(&bytes);
    if (error) numeric_error(file, line, column, error);

    uintmax_t pending = bytes > 0 ? (unsigned)bytes : 0;
    for (const struct input_chunk *chunk = input_data; chunk; chunk = chunk->next)
        pending += chunk->length - chunk->offset;
    return pending ? size_value(pending) : "0";
}
#endif

const char *jbc_cursor(const char *col, const char *row, const char *file, int line, int column)
{
    /* One-argument codes as TAFC PB201214 writes them for TERM=vt100
       (tests/tafc/at-minus-codes.b). A code the terminal does not define
       is an empty string; @(n) moves to column n of the current line. */
    if (!row) {
        static const char *const codes[] = {
            "", "\033[H\033[J", "\033[H", "\033[J", "\033[K", "\033[5m", "\033[m\017",
            "", "\033[m\017", "\b", "\033[A", "", "", "\033[7m", "\033[m\017", "\033[4m",
            "\033[m\017", "\033[5i", "\033[4i", "\033[C", "\n",
        };
        int64_t code = truncated(col, file, line, column);
        if (code < 0) return -code < (int64_t)(sizeof codes / sizeof *codes) ? codes[-code] : "";
        if (!code) return "\r";
        char *out = allocate(24);
        snprintf(out, 25, "\r\033[%" PRId64 "C", code);
        return out;
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

/* OUT writes one byte, the integer part of its argument modulo 256, with
   no newline; a nonnumeric argument warns and writes byte 0, as in TAFC
   PB201214 (tests/tafc/out-statement.b). */
/* PRINTERR id:@FM:arguments prints a jBASE error message as TAFC PB201214
   does: " ** Error [ id ] ** " and the message text with the arguments.
   jbcc knows the messages its own runtime raises; for others it prints
   TAFC's "Error message ... not found" line. */
void jbc_printerr(const char *value, const char *file, int line, int column)
{
    (void)file, (void)line, (void)column;
    const char *fields = value, *id = take_field(&fields, 254);
    const char *argument = fields ? take_field(&fields, 254) : "";
    const char *text = NULL;
    if (!strcmp(id, "201")) text = jbc_concat("Unable to open file ", argument);
    else if (!strcmp(id, "202")) text = jbc_concat(jbc_concat("Record ", argument), " is not on file");
    const char *out = text
        ? jbc_concat(jbc_concat(jbc_concat(" ** Error [ ", id), " ] ** \n"), jbc_concat(text, "\n"))
        : jbc_concat(jbc_concat("!!! Error message ", id), " not found !!!\n");
    jbc_output(JBC_SCREEN, out, file, line, column);
}

void jbc_out(const char *value, const char *file, int line, int column)
{
    struct decimal n;
    unsigned code = 0;
    if (!parse_decimal(value, &n))
        fprintf(stderr, "%s:%d:%d: warning: Non-numeric value -- ZERO USED\n", file, line, column);
    else {
        for (size_t i = 0; i < n.digits; ++i) code = (code * 10 + (unsigned)(n.whole[i] - '0')) % 256;
        if (n.sign < 0) code = (256 - code) % 256;
    }
    if (code) {
        char text[2] = {(char)code, '\0'};
        jbc_output(JBC_SCREEN, text, file, line, column);
    } else {
        fputc(0, stdout);
    }
}

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

/* Whether this process already has the file behind fd open as a sequential
   file. Its own lock then does not block it: TAFC PB201214 lets a program
   OSOPEN or OPENSEQ a file it already has open (tests/tafc/
   osread-line-feeds.b). Another process's lock still does. */
static int open_in_this_process(int fd)
{
    struct stat target, other;
    if (fstat(fd, &target) < 0) return 0;
    for (struct sequential_file *s = sequential_files; s; s = s->next)
        if (s->stream && fstat(fileno(s->stream), &other) == 0 &&
            other.st_dev == target.st_dev && other.st_ino == target.st_ino)
            return 1;
    return 0;
}

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
            status = errno != EWOULDBLOCK ? file_error(errno)
                   : open_in_this_process(fd) ? 0 : JBC_LOCKED;
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
        /* Line feeds become field marks, as TAFC PB201214 reads a file
           (tests/tafc/osread-line-feeds.b); carriage returns stay. */
        for (size_t i = 0; i < length; ++i)
            value[i] = contents[i] == '\n' ? (char)254 : contents[i] ? contents[i] : (char)128;
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
    else if (flock(fd, LOCK_EX | LOCK_NB) < 0 && (errno != EWOULDBLOCK || !open_in_this_process(fd)))
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

/* DELETESEQ removes the file named by a directory and an item, or by a path. */
int jbc_deleteseq(const char *path, const char *name)
{
    if (name) path = jbc_concat(jbc_concat(path, "/"), name);
    if (unlink(path) == 0) return file_result(0);
    return file_result(file_error(errno));
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

const char *jbc_jbasecoredump(const char *suffix, const char *mode, const char *file, int line, int column)
{
    (void)suffix;
    (void)mode;
    numeric_error(file, line, column, "JBASECOREDUMP requires an application snapshot backend");
    return "";
}

const char *jbc_validate_product_license(const char *product, const char *file, int line,
                                         int column)
{
    (void)product;
    numeric_error(file, line, column, "VALIDATE_PRODUCT_LICENSE requires a licensing backend");
    return "";
}

/* DATELOCALETOGREGORIAN and DATEGREGORIANTOLOCALE(date, format, calendar,
   format, locale) convert between calendars in R19. Neither the guide nor
   the PB201214 headers define them; they parse and report when reached. */
const char *jbc_datelocaletogregorian(const char *date, const char *from, const char *calendar,
                                      const char *to, const char *locale,
                                      const char *file, int line, int column)
{
    (void)date; (void)from; (void)calendar; (void)to; (void)locale;
    numeric_error(file, line, column, "DATELOCALETOGREGORIAN requires a calendar backend");
    return "";
}

const char *jbc_dategregoriantolocale(const char *date, const char *from, const char *calendar,
                                      const char *to, const char *locale,
                                      const char *file, int line, int column)
{
    (void)date; (void)from; (void)calendar; (void)to; (void)locale;
    numeric_error(file, line, column, "DATEGREGORIANTOLOCALE requires a calendar backend");
    return "";
}

const char *jbc_crypt(const char *value, const char *key, const char *method, int decrypt,
                      const char *file, int line, int column)
{
    enum { JBASE_CRYPT_ROT13 = 1 };
    (void)key;
    if (truncated(method, file, line, column) != JBASE_CRYPT_ROT13)
        numeric_error(file, line, column, decrypt ? "DECRYPT requires a backend for this method"
                                                  : "ENCRYPT requires a backend for this method");
    size_t length = strlen(value);
    char *out = allocate(length);
    for (size_t i = 0; i < length; ++i) {
        unsigned char byte = (unsigned char)value[i];
        if (byte >= 'A' && byte <= 'Z') byte = 'A' + (byte - 'A' + 13) % 26;
        else if (byte >= 'a' && byte <= 'z') byte = 'a' + (byte - 'a' + 13) % 26;
        out[i] = (char)byte;
    }
    out[length] = '\0';
    return out;
}

const char *jbc_itype(const char *descriptor, const char *file, int line, int column)
{
    (void)descriptor;
    numeric_error(file, line, column, "ITYPE requires a compiled dictionary backend");
    return "";
}

const char *jbc_xml_transform(const char *input, const char *stylesheet, jbc_variable *status,
                              const char *reason, const char *file, int line, int column)
{
    (void)input;
    (void)stylesheet;
    (void)status;
    numeric_error(file, line, column, reason);
    return "";
}

int jbc_readxml(const char *handle, const char *key, jbc_variable *out, jbc_variable *setting,
                const char *reason, const char *file, int line, int column)
{
    (void)handle;
    (void)key;
    (void)out;
    (void)setting;
    numeric_error(file, line, column, reason);
    return 0;
}

const char *jbc_indices(const char *handle, const char *index, const char *file, int line, int column)
{
    (void)handle;
    (void)index;
    numeric_error(file, line, column, "INDICES requires a secondary-index backend");
    return "";
}

static int open_file_info(const char *handle, const char **path)
{
    struct memory_file *memory = file_for(handle);
    const char *name;
    if (memory) {
        name = memory->name;
    } else {
#ifdef JBC_SEQUENTIAL
        struct sequential_file *sequential = *sequential_slot(handle);
        if (!sequential || !sequential->stream) return 128;
        name = path ? sequential_path(sequential->token) : NULL;
#else
        return 128;
#endif
    }
    if (!path) return 0;
    if (!name) return 32768;
    /* An exposed path is text and must have a different identity from the handle. */
    *path = strcpy(allocate(strlen(name)), name);
    return 0;
}

const char *jbc_fileinfo(const char *handle, const char *key, const char *source, int line, int column)
{
    if (!jbc_compare(key, "0", -1)) return open_file_info(handle, NULL) ? "0" : "1";
    if (jbc_compare(key, "2", -1))
        numeric_error(source, line, column, "FILEINFO supports keys 0 and 2");
    const char *path = "";
    if (open_file_info(handle, &path) == 32768)
        numeric_error(source, line, column, "cannot resolve FILEINFO path");
    return path;
}

const char *jbc_ioctl(const char *handle, const char *command, jbc_variable *output,
                      const char *source, int line, int column)
{
    if (jbc_compare(command, "100", -1))
        numeric_error(source, line, column, "IOCTL supports only command 100");
    const char *path;
    int status = open_file_info(handle, &path);
    if (status == 128 && handle && !jbc_compare(handle, "-1", -1))
        status = open_file_info(jbc_default_file.value, &path);
    if (status) return "0";
    assign_value(output, path);
    return "1";
}

/* Catalogue functions that the T24 corpora never call. Their behaviour
   follows the guide's descriptions and examples; README.md lists the
   choices that remain provisional. */

#ifdef JBC_MATH
static long double angle_operand(const char *s, const char *name, const char *file, int line, int column)
{
    struct decimal n;
    long double value = strtold(s, NULL);
    if (!parse_decimal(s, &n) || !isfinite(value)) {
        char message[64];
        snprintf(message, sizeof message, "%s requires a numeric operand", name);
        numeric_error(file, line, column, message);
    }
    return value;
}

/* Round away the conversion's binary noise so that ASIN(-0.5) is -30. */
static const char *degrees_value(long double radians)
{
    long double degrees = roundl(radians * (180.0L / 3.14159265358979323846L) * 1e12L) / 1e12L;
    return format_decimal(degrees);
}

/* TAN takes degrees like SIN and COS; the inverse functions return them. */
const char *jbc_tan(const char *s, const char *file, int line, int column)
{
    long double value = tanl(radians(s, file, line, column));
    if (!isfinite(value)) numeric_error(file, line, column, "TAN result out of range");
    return format_decimal(value);
}

const char *jbc_asin(const char *s, const char *file, int line, int column)
{
    long double value = angle_operand(s, "ASIN", file, line, column);
    if (value < -1 || value > 1) numeric_error(file, line, column, "ASIN requires an operand from -1 to 1");
    return degrees_value(asinl(value));
}

const char *jbc_acos(const char *s, const char *file, int line, int column)
{
    long double value = angle_operand(s, "ACOS", file, line, column);
    if (value < -1 || value > 1) numeric_error(file, line, column, "ACOS requires an operand from -1 to 1");
    return degrees_value(acosl(value));
}

const char *jbc_atan(const char *s, const char *file, int line, int column)
{
    return degrees_value(atanl(angle_operand(s, "ATAN", file, line, column)));
}

static long double float_operand(const char *s, const char *name, const char *file, int line, int column)
{
    struct decimal n;
    long double value = strtold(s, NULL);
    if (!*s || !parse_decimal(s, &n) || !isfinite(value)) {
        char message[64];
        snprintf(message, sizeof message, "%s requires numeric operands", name);
        numeric_error(file, line, column, message);
    }
    return value;
}

/* The guide's FDIV and FMUL examples, 0.1428571429 and 14.48652932, both
   show ten significant digits and ignore PRECISION. */
static const char *significant_value(long double value, const char *name, const char *file, int line, int column)
{
    if (!isfinite(value)) {
        char message[64];
        snprintf(message, sizeof message, "%s result out of range", name);
        numeric_error(file, line, column, message);
    }
    char scientific[64];
    snprintf(scientific, sizeof scientific, "%.9Le", value);
    int places = 9 - atoi(strchr(scientific, 'e') + 1);
    if (places < 0) places = 0;
    int length = snprintf(NULL, 0, "%.*Lf", places, value);
    char *out = allocate((size_t)length);
    snprintf(out, (size_t)length + 1, "%.*Lf", places, value);
    if (places) {
        while (out[length - 1] == '0') out[--length] = '\0';
        if (out[length - 1] == '.') out[--length] = '\0';
    }
    return strcmp(out, "-0") == 0 ? "0" : out;
}

/* FADD, FSUB, FMUL and FDIV return a raw double, which TAFC prints with
   ten significant digits, not at PRECISION: FSUB(10, 0.00004) is 9.99996
   at PRECISION 4 (TAFC PB201214, tests/snippets/element-functions.b). */
const char *jbc_fadd(const char *left, const char *right, const char *file, int line, int column)
{
    long double value = float_operand(left, "FADD", file, line, column)
                      + float_operand(right, "FADD", file, line, column);
    return significant_value(value, "FADD", file, line, column);
}

const char *jbc_fmul(const char *left, const char *right, const char *file, int line, int column)
{
    long double value = float_operand(left, "FMUL", file, line, column)
                      * float_operand(right, "FMUL", file, line, column);
    return significant_value(value, "FMUL", file, line, column);
}

const char *jbc_fdiv(const char *left, const char *right, const char *file, int line, int column)
{
    long double dividend = float_operand(left, "FDIV", file, line, column);
    long double divisor = float_operand(right, "FDIV", file, line, column);
    if (divisor == 0) numeric_error(file, line, column, "FDIV division by zero");
    return significant_value(dividend / divisor, "FDIV", file, line, column);
}

const char *jbc_fcmp(const char *left, const char *right, const char *file, int line, int column)
{
    long double a = float_operand(left, "FCMP", file, line, column);
    long double b = float_operand(right, "FCMP", file, line, column);
    return a < b ? "-1" : a > b ? "1" : "0";
}
#endif

/* Exact decimal addition of magnitudes or signed values. */
static const char *decimal_sum(struct decimal a, struct decimal b, const char *precision,
                               const char *name, const char *file, int line, int column)
{
    char diagnostic[64];
    snprintf(diagnostic, sizeof diagnostic, "%s precision requires -1 or a nonnegative integer", name);
    /* TAFC PB201214 keeps 14 places (tests/tafc/string-math.b): a sum of
       operands with the same sign rounds half away from zero, and one with
       opposite signs truncates toward zero. */
    uintmax_t places = string_math_places(precision, 14, diagnostic, file, line, column);
    if (!a.sign || !b.sign) {
        struct decimal n = a.sign ? a : b;
        limit_places(&n, places > INT_MAX ? -1 : (int)places);
        while (n.places && n.fraction[n.places - 1] == '0') --n.places;
        if (!n.digits && !n.places) return "0";
        return fmt_decimal(n, n.places);
    }
    int subtract = a.sign != b.sign;
    int sign = a.sign;
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
    if (scale >= SIZE_MAX - whole - 2) numeric_error(file, line, column, "decimal result is too large");
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
    while (result.digits && *result.whole == '0') { ++result.whole; --result.digits; }
    if (subtract && places < result.places) result.places = (size_t)places;
    else limit_places(&result, places > INT_MAX ? -1 : (int)places);
    while (result.places && result.fraction[result.places - 1] == '0') --result.places;
    while (result.digits && *result.whole == '0') { ++result.whole; --result.digits; }
    if (!result.digits && !result.places) return "0";
    return fmt_decimal(result, result.places);
}

const char *jbc_sadd(const char *left, const char *right, const char *precision,
                     const char *file, int line, int column)
{
    struct decimal a, b;
    parse_decimal(numeric_operand(left, file, line, column), &a);
    parse_decimal(numeric_operand(right, file, line, column), &b);
    return decimal_sum(a, b, precision, "SADD", file, line, column);
}

const char *jbc_ssub(const char *left, const char *right, const char *precision,
                     const char *file, int line, int column)
{
    struct decimal a, b;
    parse_decimal(numeric_operand(left, file, line, column), &a);
    parse_decimal(numeric_operand(right, file, line, column), &b);
    b.sign = -b.sign;
    return decimal_sum(a, b, precision, "SSUB", file, line, column);
}

const char *jbc_scmp(const char *left, const char *right, const char *file, int line, int column)
{
    struct decimal a, b;
    int numeric = parse_decimal(left, &a);
    if (!parse_decimal(right, &b) || !numeric)
        numeric_error(file, line, column, "SCMP requires numeric operands");
    int order = compare_decimals(a, b, -1);
    return order < 0 ? "-1" : order > 0 ? "1" : "0";
}

static char ascii_upper(unsigned char c)
{
    return (char)(c >= 'a' && c <= 'z' ? c - 'a' + 'A' : c);
}

/* Each process has a table of 128 flags, numbered from 1. Codes -1 to -3
   name the break-key and restart switches; jbcc keeps them as flags
   without a terminal effect. */
static unsigned char bit_table[128], bit_switches[3];

static unsigned char *bit_flag(const char *number, const char *name, int *all,
                               const char *file, int line, int column)
{
    struct decimal n;
    char message[80];
    snprintf(message, sizeof message, "%s requires a bit number from -3 to 128", name);
    if (!parse_decimal(number, &n)) numeric_error(file, line, column, message);
    int64_t bit = n.digits > 4 ? 1000 : truncated(number, file, line, column);
    *all = bit == 0;
    if (bit == 0) return NULL;
    if (bit < -3 || bit > 128) numeric_error(file, line, column, message);
    return bit > 0 ? &bit_table[bit - 1] : &bit_switches[-bit - 1];
}

static const char *update_bit(const char *number, const char *name, int mode,
                              const char *file, int line, int column)
{
    int all;
    unsigned char *flag = bit_flag(number, name, &all, file, line, column);
    if (all) {
        if (mode == 0 || mode == 1) {
            memset(bit_table, mode, sizeof bit_table);
            return mode ? "1" : "0";
        }
        numeric_error(file, line, column, "bit number 0 applies only to BITSET and BITRESET");
    }
    const char *previous = *flag ? "1" : "0";
    if (mode == 0 || mode == 1) *flag = (unsigned char)mode;
    else if (mode == 2) *flag = !*flag;
    return previous;
}

const char *jbc_bitset(const char *bit, const char *file, int line, int column)
{
    return update_bit(bit, "BITSET", 1, file, line, column);
}

const char *jbc_bitreset(const char *bit, const char *file, int line, int column)
{
    return update_bit(bit, "BITRESET", 0, file, line, column);
}

const char *jbc_bitchange(const char *bit, const char *file, int line, int column)
{
    return update_bit(bit, "BITCHANGE", 2, file, line, column);
}

const char *jbc_bitcheck(const char *bit, const char *file, int line, int column)
{
    return update_bit(bit, "BITCHECK", 3, file, line, column);
}

/* BITLOAD returns the table as hexadecimal with trailing zero digits
   removed. Given a nonempty string, it loads the table and returns the
   previous contents (provisional: the guide names the result VALUE.OLD). */
const char *jbc_bitload(const char *source)
{
    static const char hex[] = "0123456789ABCDEF";
    char *out = allocate(32);
    int length = 0;
    for (int i = 0; i < 32; ++i) {
        unsigned char *b = bit_table + 4 * i;
        out[i] = hex[b[0] << 3 | b[1] << 2 | b[2] << 1 | b[3]];
        if (out[i] != '0') length = i + 1;
    }
    out[length] = '\0';
    if (!source || !*source) return out;
    memset(bit_table, 0, sizeof bit_table);
    for (int i = 0; i < 32 && source[i]; ++i) {
        const char *digit = strchr(hex, ascii_upper((unsigned char)source[i]));
        if (!digit || !*digit) break;
        int value = (int)(digit - hex);
        for (int j = 0; j < 4; ++j) bit_table[4 * i + j] = (unsigned char)(value >> (3 - j) & 1);
    }
    return out;
}

/* Character classes use the C locale's ASCII rules. The guide's ISCNTRL
   example counts @FM as a control character, so the system delimiters
   248 to 255 are control characters; other high bytes are in no class. */
static int byte_class(unsigned char c, char kind)
{
    switch (kind) {
    /* System marks and other bytes above 127 are not control characters
       (TAFC PB201214, tests/tafc/char-class-marks.b). */
    case 'C': return c < 32 || c == 127;
    case 'G': return c > 32 && c < 127;
    case 'P': return c >= 32 && c < 127;
    case 'U': return c > 32 && c < 127 && !ascii_alpha(c) && !ascii_digit(c);
    default: return ascii_digit(c) || (c >= 'A' && c <= 'F') || (c >= 'a' && c <= 'f');
    }
}

static const char *all_in_class(const char *text, char kind)
{
    if (!*text) return "0";
    for (; *text; ++text)
        if (!byte_class((unsigned char)*text, kind)) return "0";
    return "1";
}

const char *jbc_iscntrl(const char *text) { return all_in_class(text, 'C'); }
const char *jbc_isgraph(const char *text) { return all_in_class(text, 'G'); }
const char *jbc_isprint(const char *text) { return all_in_class(text, 'P'); }
const char *jbc_ispunct(const char *text) { return all_in_class(text, 'U'); }
const char *jbc_isxdigit(const char *text) { return all_in_class(text, 'X'); }

/* Pair the elements of two dynamic arrays as ADDS does. The callback sees
   NULL for an element that has no counterpart. */
static const char *pair_elements(const char *left, const char *right,
                                 const char *(*each)(const char *, const char *, const void *),
                                 const void *context)
{
    struct array_cursor lhs = array_cursor(left, 0, 1);
    struct array_cursor rhs = array_cursor(right, 0, 1);
    char *left_items = split_array_items(left, NULL);
    char *right_items = split_array_items(right, NULL);
    const char *out = "";
    for (;;) {
        const char *a = lhs.present ? left_items + (lhs.item - left) : NULL;
        const char *b = rhs.present ? right_items + (rhs.item - right) : NULL;
        out = jbc_concat(out, each(a, b, context));
        unsigned mark = lhs.mark < rhs.mark ? lhs.mark : rhs.mark;
        if (mark == 256) break;
        out = jbc_concat(out, (const char[]){(char)mark, '\0'});
        advance_array_item(&lhs, mark);
        advance_array_item(&rhs, mark);
    }
    free(left_items);
    free(right_items);
    return out;
}

/* ANDS: a missing element is false; two nulls give null; a null beside a
   false value is false. A null beside a true value gives null, as in
   UniVerse (provisional). */
static const char *and_pair(const char *a, const char *b, const void *context)
{
    (void)context;
    if (!a || !b) return "0";
    if (!*a && !*b) return "";
    if ((*a && !jbc_truth(a)) || (*b && !jbc_truth(b))) return "0";
    if (!*a || !*b) return "";
    return "1";
}

/* ORS: a missing element is false; a null beside a false value or another
   null gives null, and a null beside a true value gives true. */
static const char *or_pair(const char *a, const char *b, const void *context)
{
    (void)context;
    if (!a) a = "0";
    if (!b) b = "0";
    if ((*a && jbc_truth(a)) || (*b && jbc_truth(b))) return "1";
    if (!*a || !*b) return "";
    return "0";
}

struct source_location {
    const char *file;
    int line, column;
};

/* MODS: X - INT(X / Y) * Y, with 0 for a missing element or a zero
   divisor and null when either element is null. */
static const char *mod_pair(const char *a, const char *b, const void *context)
{
    const struct source_location *at = context;
    if (!a || !b) return "0";
    if (!*a || !*b) return "";
    struct decimal divisor;
    if (parse_decimal(b, &divisor) && !divisor.sign) return "0";
    return jbc_mod(a, b, "MODS requires numeric elements", at->file, at->line, at->column);
}

const char *jbc_ands(const char *left, const char *right)
{
    return pair_elements(left, right, and_pair, NULL);
}

const char *jbc_ors(const char *left, const char *right)
{
    return pair_elements(left, right, or_pair, NULL);
}

const char *jbc_mods(const char *left, const char *right, const char *file, int line, int column)
{
    struct source_location at = {file, line, column};
    return pair_elements(left, right, mod_pair, &at);
}

/* IFS selects, for each element of the condition, the element at the same
   field, value and subvalue position of the true or false array. A null
   condition is false and a missing element is empty. */
const char *jbc_ifs(const char *condition, const char *when_true, const char *when_false)
{
    char *items = split_array_items(condition, NULL);
    const char *out = "";
    int64_t position[3] = {1, 1, 1};
    const char *field = condition;
    for (const char *item = items;;) {
        const char *end = item + strlen(item);
        unsigned char mark = (unsigned char)condition[end - items];
        /* Address the value or subvalue only when the condition has one. */
        size_t field_length = strcspn(field, "\376");
        int depth = memchr(field, 253, field_length) || memchr(field, 252, field_length) ? 2 : 1;
        const char *value = condition + (item - items);
        while (value > field && (unsigned char)value[-1] != 253) --value;
        size_t value_length = strcspn(value, "\376\375");
        if (memchr(value, 252, value_length)) depth = 3;
        const char *source = *item && jbc_truth(item) ? when_true : when_false;
        out = jbc_concat(out, array_part(source, strlen(source), position, depth, 0, NULL, 0));
        if (!mark) break;
        out = jbc_concat(out, (const char[]){(char)mark, '\0'});
        if (mark == 254) {
            ++position[0]; position[1] = position[2] = 1;
            field = condition + (end - items) + 1;
        } else if (mark == 253) {
            ++position[1]; position[2] = 1;
        } else {
            ++position[2];
        }
        item = end + 1;
    }
    free(items);
    return out;
}

static const char *seq_element(const char *item)
{
    return *item ? jbc_seq(item) : "";
}

const char *jbc_seqs(const char *source)
{
    return map_elements(source, seq_element);
}

/* CHARS and STRS keep null elements null. */
const char *jbc_chars(const char *source, const char *file, int line, int column)
{
    char *items = split_array_items(source, NULL);
    const char *out = "";
    for (const char *item = items;;) {
        const char *end = item + strlen(item);
        char mark[2] = {source[end - items], '\0'};
        if (*item) out = jbc_concat(out, jbc_char(item, file, line, column));
        out = jbc_concat(out, mark);
        if (!*mark) break;
        item = end + 1;
    }
    free(items);
    return out;
}

const char *jbc_strs(const char *source, const char *count, const char *file, int line, int column)
{
    if (!*count) numeric_error(file, line, column, "STRS requires a numeric repeat count");
    if (truncated(count, file, line, column) <= 0) return "";
    char *items = split_array_items(source, NULL);
    const char *out = "";
    for (const char *item = items;;) {
        const char *end = item + strlen(item);
        char mark[2] = {source[end - items], '\0'};
        out = jbc_concat(out, jbc_str(item, count, file, line, column));
        out = jbc_concat(out, mark);
        if (!*mark) break;
        item = end + 1;
    }
    free(items);
    return out;
}

/* SOUNDEX keeps the first letter and codes later consonants, skipping
   repeats of the same letter. The guide gives one to three digits. */
const char *jbc_soundex(const char *text)
{
    static const char codes[] = "01230120022455012623010202";
    while (*text && !ascii_alpha((unsigned char)*text)) ++text;
    if (!*text) return "";
    char *out = allocate(4);
    int length = 0;
    out[length++] = ascii_upper((unsigned char)*text);
    char previous = ascii_upper((unsigned char)*text);
    for (++text; *text && length < 4; ++text) {
        if (!ascii_alpha((unsigned char)*text)) continue;
        char letter = ascii_upper((unsigned char)*text);
        if (letter == previous) continue;
        previous = letter;
        char code = codes[letter - 'A'];
        if (code != '0') out[length++] = code;
    }
    out[length] = '\0';
    return out;
}

#ifdef JBC_REGEXP
#include <regex.h>

/* REGEXP returns the one-based position of the first match, 0 when there
   is none and -1 for an invalid POSIX extended expression. */
const char *jbc_regexp(const char *text, const char *expression)
{
    regex_t pattern;
    if (regcomp(&pattern, expression, REG_EXTENDED)) return "-1";
    regmatch_t match;
    int status = regexec(&pattern, text, 1, &match, 0);
    regfree(&pattern);
    if (status) return "0";
    return size_value((uintmax_t)match.rm_so + 1);
}
#endif

#ifdef JBC_TIMESTAMP
static int64_t adjustment_field(const char *changes, int index, const char *file, int line, int column)
{
    int64_t position[1] = {index};
    const char *field = array_part(changes, strlen(changes), position, 1, 0, NULL, 0);
    if (!*field) return 0;
    struct decimal n;
    if (!parse_decimal(field, &n) || n.places)
        numeric_error(file, line, column, "CHANGETIMESTAMP requires whole adjustments");
    if (n.digits > 12) numeric_error(file, line, column, "CHANGETIMESTAMP adjustment out of range");
    return integer(field, file, line, column);
}

/* Years^Months^Weeks^Days^Hours^Minutes^Seconds^Milliseconds. Years and
   months move along the UTC calendar, keeping the day of the month where
   it exists and otherwise using the month's last day (provisional). */
const char *jbc_changetimestamp(const char *stamp, const char *changes,
                                const char *file, int line, int column)
{
    int64_t ms = milliseconds(stamp, "CHANGETIMESTAMP requires a numeric timestamp", file, line, column);
    int64_t field[8];
    for (int i = 0; i < 8; ++i) field[i] = adjustment_field(changes, i + 1, file, line, column);
    if (field[0] || field[1]) {
        int64_t day = floor_div(ms, 86400000), clock = ms - day * 86400000;
        int64_t ordinal = day + UNIX_EPOCH_ORDINAL;
        int64_t year = 1 + 400 * floor_div(ordinal, 146097);
        int64_t remaining = ordinal - floor_div(ordinal, 146097) * 146097;
        while (remaining >= 365 + leap_year((int)year)) remaining -= 365 + leap_year((int)year++);
        int month = 1;
        while (remaining >= month_length((int)year, month)) remaining -= month_length((int)year, month++);
        int64_t months = (year * 12 + month - 1) + field[0] * 12 + field[1];
        year = floor_div(months, 12);
        month = (int)(months - year * 12) + 1;
        if (year < 1 || year > 9999) numeric_error(file, line, column, "CHANGETIMESTAMP result out of range");
        int64_t date = remaining + 1;
        if (date > month_length((int)year, month)) date = month_length((int)year, month);
        int64_t years = year - 1;
        ordinal = years * 365 + years / 4 - years / 100 + years / 400 + date - 1;
        for (int m = 1; m < month; ++m) ordinal += month_length((int)year, m);
        ms = (ordinal - UNIX_EPOCH_ORDINAL) * 86400000 + clock;
    }
    static const int64_t unit[] = {0, 0, 604800000, 86400000, 3600000, 60000, 1000, 1};
    for (int i = 2; i < 8; ++i) ms += field[i] * unit[i];
    return milliseconds_value(ms);
}
#endif

#ifdef JBC_PUTENV
const char *jbc_delenv(const char *name)
{
    if (!*name || strchr(name, '=') || !getenv(name)) return "0";
    return unsetenv(name) == 0 ? "1" : "0";
}
#endif

#ifdef JBC_HOST_INFO
#include <grp.h>
#include <pwd.h>
#include <sys/stat.h>

/* DIR returns size^date^time^D, with the date and time in internal format
   for the local zone. jbcc returns an empty string for a missing path. */
const char *jbc_dir(const char *path)
{
    struct stat info;
    if (!*path || stat(path, &info) != 0) return "";
    time_t stamp = info.st_mtime;
    struct tm local;
    if (!localtime_r(&stamp, &local)) return "";
    int directory = S_ISDIR(info.st_mode);
    char *out = allocate(64);
    snprintf(out, 65, "%jd\376%s\376%d\376%s", directory ? (intmax_t)0 : (intmax_t)info.st_size,
             internal_date(local.tm_year + 1900, local.tm_yday + 1),
             local.tm_hour * 3600 + local.tm_min * 60 + local.tm_sec, directory ? "D" : "");
    return out;
}

static int user_id(const char *uid, uid_t *out)
{
    struct decimal n;
    if (!parse_decimal(uid, &n) || n.sign < 0 || n.places || n.digits > 9) return 0;
    *out = (uid_t)strtoul(uid, NULL, 10);
    return 1;
}

const char *jbc_getusername(const char *uid)
{
    uid_t id;
    struct passwd *entry = user_id(uid, &id) ? getpwuid(id) : NULL;
    return entry ? strcpy(allocate(strlen(entry->pw_name)), entry->pw_name) : "";
}

/* The guide says Windows returns zero, so the result is the user's
   primary group number rather than its name. */
const char *jbc_getusergroup(const char *uid)
{
    uid_t id;
    struct passwd *entry = user_id(uid, &id) ? getpwuid(id) : NULL;
    return entry ? size_value((uintmax_t)entry->pw_gid) : "";
}
#endif

#ifdef JBC_CACHE
/* The JBC.h in-memory cache: named buckets of items with hit, get and put
   counters and a size limit. Values outlive the runtime's string
   collector, so the cache keeps its own copies. */
struct cache_item {
    struct cache_item *next;
    char *key, *value;
    uint64_t used;
};

struct cache_bucket {
    struct cache_bucket *next;
    char *name;
    struct cache_item *items;
    uint64_t count, hits, gets, puts, max_size, threshold;
};

enum { CACHE_DEFAULT_SIZE = 1048576, CACHE_DEFAULT_THRESHOLD = 90 };
static struct cache_bucket *cache_buckets;
static uint64_t cache_clock;

static char *cache_copy(const char *text)
{
    char *copy = malloc(strlen(text) + 1);
    if (!copy) fail("out of memory");
    return strcpy(copy, text);
}

static struct cache_bucket *cache_bucket(const char *name, int create)
{
    struct cache_bucket **link = &cache_buckets;
    for (; *link; link = &(*link)->next)
        if (!strcmp((*link)->name, name)) return *link;
    if (!create) return NULL;
    struct cache_bucket *bucket = calloc(1, sizeof *bucket);
    if (!bucket) fail("out of memory");
    bucket->name = cache_copy(name);
    bucket->max_size = CACHE_DEFAULT_SIZE;
    bucket->threshold = CACHE_DEFAULT_THRESHOLD;
    *link = bucket;
    return bucket;
}

static struct cache_item **cache_item(struct cache_bucket *bucket, const char *key)
{
    struct cache_item **link = &bucket->items;
    while (*link && strcmp((*link)->key, key)) link = &(*link)->next;
    return link;
}

static void cache_remove(struct cache_bucket *bucket, struct cache_item **link)
{
    struct cache_item *item = *link;
    *link = item->next;
    --bucket->count;
    free(item->key);
    free(item->value);
    free(item);
}

static void cache_empty(struct cache_bucket *bucket)
{
    while (bucket->items) cache_remove(bucket, &bucket->items);
    bucket->hits = bucket->gets = bucket->puts = 0;
}

/* The guide purges "the most outdated data" once the size exceeds
   CACHE_MAX_SIZE * CACHE_PURGE_THRESHOLD / 100. TAFC PB201214 counts the
   size in items (CACHE_SIZE reports the item count, and three items stay
   under a maximum of 10 at 60%: tests/snippets/cache.b). jbcc removes the
   least recently written or read items until the bucket is back under that
   limit (provisional). */
static void cache_purge(struct cache_bucket *bucket)
{
    uint64_t limit = bucket->max_size / 100 * bucket->threshold
                   + bucket->max_size % 100 * bucket->threshold / 100;
    while (bucket->items && bucket->count > limit) {
        struct cache_item **oldest = &bucket->items;
        for (struct cache_item **link = &bucket->items; *link; link = &(*link)->next)
            if ((*link)->used < (*oldest)->used) oldest = link;
        cache_remove(bucket, oldest);
    }
}

static int cache_number(const char *text, uint64_t *out)
{
    struct decimal n;
    if (!parse_decimal(text, &n) || n.sign < 0 || n.digits > 18) return 0;
    *out = 0;
    for (size_t i = 0; i < n.digits; ++i) *out = *out * 10 + (uint64_t)(n.whole[i] - '0');
    return 1;
}

const char *jbc_cache_put(const char *name, const char *key, const char *value)
{
    struct cache_bucket *bucket = cache_bucket(name, 1);
    struct cache_item **link = cache_item(bucket, key);
    if (*link) {
        free((*link)->value);
    } else {
        *link = calloc(1, sizeof **link);
        if (!*link) fail("out of memory");
        (*link)->key = cache_copy(key);
        ++bucket->count;
    }
    (*link)->value = cache_copy(value);
    (*link)->used = ++cache_clock;
    ++bucket->puts;
    cache_purge(bucket);
    return "";
}

const char *jbc_cache_get(const char *name, const char *key)
{
    struct cache_bucket *bucket = cache_bucket(name, 0);
    if (!bucket) return "";
    ++bucket->gets;
    struct cache_item *item = *cache_item(bucket, key);
    if (!item) return "";
    ++bucket->hits;
    item->used = ++cache_clock;
    return strcpy(allocate(strlen(item->value)), item->value);
}

const char *jbc_cache_exists(const char *name, const char *key)
{
    struct cache_bucket *bucket = cache_bucket(name, 0);
    return bucket && *cache_item(bucket, key) ? "1" : "0";
}

const char *jbc_cache_delete(const char *name, const char *key)
{
    struct cache_bucket *bucket = cache_bucket(name, 0);
    struct cache_item **link = bucket ? cache_item(bucket, key) : NULL;
    if (link && *link) cache_remove(bucket, link);
    return "";
}

/* CacheClear drops the bucket, so its statistics and options start again:
   a CacheGet afterwards counts nothing in TAFC PB201214. */
const char *jbc_cache_clear(const char *name)
{
    for (struct cache_bucket **link = &cache_buckets; *link; link = &(*link)->next) {
        struct cache_bucket *bucket = *link;
        if (strcmp(bucket->name, name)) continue;
        *link = bucket->next;
        cache_empty(bucket);
        free(bucket->name);
        free(bucket);
        break;
    }
    return "";
}

const char *jbc_cache_clear_all(void)
{
    while (cache_buckets) {
        struct cache_bucket *bucket = cache_buckets;
        cache_buckets = bucket->next;
        cache_empty(bucket);
        free(bucket->name);
        free(bucket);
    }
    return "";
}

const char *jbc_cache_clear_stats(const char *name)
{
    struct cache_bucket *bucket = cache_bucket(name, 0);
    if (bucket) bucket->hits = bucket->gets = bucket->puts = 0;
    return "";
}

static int compare_names(const void *left, const void *right)
{
    return strcmp(*(const char *const *)left, *(const char *const *)right);
}

/* TAFC sorts both lists by name, as the guide notes for TAFJ. */
static const char *joined_names(const char **names, size_t count, const char *delimiter)
{
    qsort(names, count, sizeof *names, compare_names);
    const char *out = "";
    for (size_t i = 0; i < count; ++i)
        out = jbc_concat(i ? jbc_concat(out, delimiter) : out, names[i]);
    free(names);
    return out;
}

const char *jbc_cache_key_list(const char *name, const char *delimiter)
{
    struct cache_bucket *bucket = cache_bucket(name, 0);
    if (!bucket || !bucket->count) return "";
    const char **names = malloc(bucket->count * sizeof *names);
    if (!names) fail("out of memory");
    size_t count = 0;
    for (struct cache_item *item = bucket->items; item; item = item->next) names[count++] = item->key;
    return joined_names(names, count, delimiter);
}

const char *jbc_cache_bucket_list(const char *delimiter)
{
    size_t count = 0;
    for (struct cache_bucket *bucket = cache_buckets; bucket; bucket = bucket->next) ++count;
    if (!count) return "";
    const char **names = malloc(count * sizeof *names);
    if (!names) fail("out of memory");
    count = 0;
    for (struct cache_bucket *bucket = cache_buckets; bucket; bucket = bucket->next) names[count++] = bucket->name;
    return joined_names(names, count, delimiter);
}

/* Unknown counters and options read as zero (provisional). */
const char *jbc_cache_stats(const char *name, const char *counter)
{
    struct cache_bucket *bucket = cache_bucket(name, 0);
    uint64_t id;
    if (!bucket || !cache_number(counter, &id)) return "0";
    switch (id) {
    case 1: return size_value(bucket->hits);
    case 2: return size_value(bucket->gets);
    case 3: return size_value(bucket->puts);
    /* TAFC PB201214 reports the number of items as CACHE_SIZE, not bytes
       (tests/tafc/misc-section-4.b). */
    case 4:
    case 5: return size_value(bucket->count);
    default: return "0";
    }
}

const char *jbc_cache_get_option(const char *name, const char *option)
{
    struct cache_bucket *bucket = cache_bucket(name, 0);
    uint64_t id;
    if (!bucket || !cache_number(option, &id)) return "0";
    if (id == 1) return size_value(bucket->max_size);
    if (id == 2) return size_value(bucket->threshold);
    return "0";
}

/* The guide gives the threshold as a percentage from 1 to 100; jbcc
   ignores other values and nonnumeric sizes (provisional). */
const char *jbc_cache_set_option(const char *name, const char *option, const char *value)
{
    struct cache_bucket *bucket = cache_bucket(name, 1);
    uint64_t id, number;
    if (!cache_number(option, &id) || !cache_number(value, &number)) return "";
    if (id == 1) bucket->max_size = number;
    else if (id == 2 && number >= 1 && number <= 100) bucket->threshold = number;
    cache_purge(bucket);
    return "";
}
#endif
