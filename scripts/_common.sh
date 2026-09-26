# Shared helpers for the scripts in this folder. Do not run this file directly.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export TOKENIZERS_PARALLELISM=false

# Print the lesson folders to use: the ones given as arguments, or all of them.
lessons() {
  if [ "$#" -gt 0 ]; then
    for l in "$@"; do echo "${l%/}"; done
  else
    (cd "$ROOT" && ls -d lesson*/ | sed 's#/##' | sort -V)
  fi
}
