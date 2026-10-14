# Original algorithmic helper

The admission Dockerfile copies the checked-in, checksum-verified Bookworm binary.
It needs only the official Python parent and vendored Python wheels; it does not
require a compiler image or network access. Source, the attributed MIT rules
header/license, and all SHA-256 values are included for review.

To reproduce the binary during development, preload the pinned compiler image
listed in Dockerfile.build, then run from this directory:

```sh
docker build --pull=false --network=none -f Dockerfile.build --target compiler -t triad-chess-native-build .
docker create --name triad-chess-native-export triad-chess-native-build
docker cp triad-chess-native-export:/build/analysis-bookworm ./analysis
docker rm triad-chess-native-export
```

Verify the result against SHA256SUMS.json. GCC 13 targets ordinary x86-64 with
static libstdc++/libgcc and Bookworm system glibc, without host-specific ISA flags.
PROVENANCE.txt records the original algorithm, permitted rules dependency and
compiler/runtime attribution. The model still makes the final move selection.
