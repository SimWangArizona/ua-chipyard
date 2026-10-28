#!/usr/bin/env python3
"""Build/test dot-only S5 and rebuild/retest S4 with bounded JVM resources."""
from build_s4 import main

if __name__=='__main__':
    raise SystemExit(main('s5'))
