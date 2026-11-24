import os
import sys

assert "-lm" in sys.argv[1:], sys.argv[1:]
os.execvp("cc", ["cc", *sys.argv[1:]])
