CRT 'before'
EXECUTE = 'child'
EXECUTE "printf '%s\n' " : EXECUTE : "; printf 'stderr\n' >&2; exit 7"
PERFORM CHAR(255) : 's' : "printf 'second\n'"
CRT 'after'
