#!/bin/bash
# Runs inside the jbc-internals TAFC image (see ../jbc-internals/docker).
# Compiles and runs every /probes/*.b with TAFC and writes, for each NAME:
#   NAME.clog (jcompile output), NAME.crc (jcompile status),
#   NAME.out, NAME.err and NAME.rc (program stdout, stderr and status,
#   present only when jcompile produced an executable)
# into /output. Environment: JOBS (parallel programs, default 2),
# EMU (JBCEMULATE, default prime), RUN_SECONDS (default 10).
set -eu
unset JBCNOLICENSE LD_PRELOAD

unpacked=/tmp/tafc
mkdir -p "$unpacked"
tar -xzf /input/tafc.tar.gz -C "$unpacked"
release=
for candidate in "$unpacked" "$unpacked"/*/; do
    if [ -x "$candidate/bin/jbccom" ] && [ -x "$candidate/bin/jcompile" ]; then
        release=${candidate%/}
    fi
done
if [ -z "$release" ]; then
    echo 'No TAFC installation with bin/jbccom and bin/jcompile in the archive' >&2
    exit 1
fi

# Generated C refers to /opt/TAFC.
ln -sfn "$release" /opt/TAFC
export JBCRELEASEDIR=$release
export JBCGLOBALDIR=$release
export JBCOBJECTLIST=$release/lib
export JBCEMULATE=${EMU:-prime}
export TERM=vt100
export HOME=/tmp/home
mkdir -p "$HOME"

compat=/tmp/compat
mkdir -p "$compat"
# libTAFCjcf.so (CREATE-FILE, COUNT, LIST and other jBASE commands) links
# libssl.so.10 only for remote sockets; a stub library lets it load.
printf '%s\n' 'void abort(void);' \
    'int SSL_get_error(void) { abort(); return 0; }' \
    'int SSL_clear(void) { abort(); return 0; }' \
    'int SSL_shutdown(void) { abort(); return 0; }' > "$compat/ssl.c"
cc -shared -fPIC -Wl,-soname,libssl.so.10 -o "$compat/libssl.so.10" "$compat/ssl.c"
# jcompile links with plain cc; generated C needs sys/types.h first.
printf '%s\n' '#!/bin/sh' 'exec /usr/bin/cc -include sys/types.h -no-pie "$@"' > "$compat/cc"
chmod +x "$compat/cc"
# EXECUTE runs shell commands through /bin/ksh.
[ -e /bin/ksh ] || ln -s /bin/bash /bin/ksh

export PATH="$compat:$release/bin:$PATH"
export LD_LIBRARY_PATH="$release/lib:/usr/local/lib:$compat"
export LIBRARY_PATH=/usr/local/lib/tafc-build

run_one() {
    source=$1
    name=$(basename "$source" .b)
    work=/tmp/work/$name
    mkdir -p "$work"
    cd "$work"
    # Lines "* tafc-program: NAME" start other programs the probe EXECUTEs;
    # each is written to NAME.b and compiled before the main program.
    awk -v main="$name.b" '
        /^\*[ \t]*tafc-program:[ \t]*[A-Za-z0-9_]+[ \t]*$/ {
            out = $NF ".b"; print out > "companions"; next
        }
        { print > (out ? out : main) }
    ' "$source"
    # Each program gets its own directory for jBASE files and OS files.
    export JEDIFILEPATH=$work
    set +e
    : >"/output/$name.clog"
    status=0
    if [ -f companions ]; then
        while read -r companion; do
            timeout 120 jcompile -I"$JBCRELEASEDIR/include" "$companion" </dev/null >>"/output/$name.clog" 2>&1 || status=$?
        done <companions
    fi
    if [ "$status" = 0 ]; then
        timeout 120 jcompile -I"$JBCRELEASEDIR/include" "$name.b" </dev/null >>"/output/$name.clog" 2>&1
        status=$?
    fi
    echo $status >"/output/$name.crc"
    if [ -x "./$name" ]; then
        # Concurrent jBASE start-ups sometimes fail to create the licensing
        # semaphore or attach shared memory; run such a program again.
        for attempt in 1 2 3 4 5; do
            timeout "${RUN_SECONDS:-10}" "./$name" </dev/null >"/output/$name.out" 2>"/output/$name.err"
            status=$?
            grep -q 'while initiating jBASE' "/output/$name.err" || break
            sleep "$attempt"
        done
        echo "$status" >"/output/$name.rc"
    fi
}
export -f run_one

find /probes -maxdepth 1 -name '*.b' -print0 | xargs -0 -r -P "${JOBS:-2}" -I{} bash -c 'run_one "$1"' _ {}
