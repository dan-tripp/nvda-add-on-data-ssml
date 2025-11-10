#!/usr/bin/env bash

set -uo pipefail
function err_trap_func () {
	exit_status="$?"
  echo "Exiting with status \"$exit_status\" due to command \"$BASH_COMMAND\" (call stack: line(s) $LINENO ${BASH_LINENO[*]} in $0)" >&2
	exit "$exit_status"
}
trap err_trap_func ERR

function exit_trap_func () {
	true
}
trap exit_trap_func EXIT

set -o errtrace
shopt -s expand_aliases
cd "$(dirname "$0")"
#set -o xtrace

nameOfThisProgram="$(basename "$0")"
dirOfThisProgram="$(realpath "$(dirname "$0")")"

numArgsMin=0
numArgsMax=0
if [[ ( "$#" -le "$numArgsMin"-1 ) || ( "$#" -ge "$numArgsMax"+1 ) || ( "$#" == 1 && "$1" == "--help" ) ]] ; then
	cat >&2 << EOF
Usage example(s): 
$nameOfThisProgram # no args 
EOF
	exit 1
fi

scons
mv *.nvda-addon releases

