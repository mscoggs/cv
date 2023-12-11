import os
import re
import sys

if len(sys.argv) == 3:
    res = re.findall(
        "{}=([-+]?[0-9]*\.?[0-9]+)".format(sys.argv[1]),
        os.getenv("COMMIT_MESSAGE", ""),
    )
    if len(res):
        print(res[0])
    else:
        print(sys.argv[2])
