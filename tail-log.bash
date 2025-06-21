#!/usr/bin/env bash

set -uo pipefail
IFS=$'\n\t'  # Inspired by http://redsymbol.net/articles/unofficial-bash-strict-mode/.  Meant as a safety net.  You should still quote variable expansions.
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
#cd "$(dirname "$0")"
#set -o xtrace

nameOfThisProgram="$(basename "$0")"
dirOfThisProgram="$(realpath "$(dirname "$0")")"

numArgsMin=0
numArgsMax=1
if [[ ( "$#" -le "$numArgsMin"-1 ) || ( "$#" -ge "$numArgsMax"+1 ) || ( "$#" == 1 && "$1" == "--help" ) ]] ; then
	cat >&2 << EOF
Usage example(s): 
$nameOfThisProgram [GREP_REGEX]
EOF
	exit 1
fi

logFilePathUnix="$("$dirOfThisProgram"/get-log-file-path.bash)"
logFilePathWindows="$(wslpath -wa "$logFilePathUnix")"
powershellCmd="Get-Content '$logFilePathWindows' -Wait"
if (( $# > 0 )); then
	grepRegex="$1"
	powershell.exe -Command "$powershellCmd" | grep --ignore-case --line-buffered "$grepRegex" | stdin-squeeze-into-column.py 50 
else
	powershell.exe -Command "$powershellCmd" | stdin-squeeze-into-column.py 50 
fi




