#!/usr/bin/env bash
# Double-clickable macOS launcher. Finder runs .command files in Terminal
# (unlike .sh, which just opens in an editor). Delegates to run.sh.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$DIR/run.sh" || {
  echo
  echo "Mapr3D exited with an error. Press any key to close this window."
  read -n 1 -s
}
