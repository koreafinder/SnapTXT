import sys
for idx, entry in enumerate(sys.path):
    print(idx, repr(entry))
