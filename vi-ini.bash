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

numArgsMin=0
numArgsMax=0
if [[ ( "$#" -le "$numArgsMin"-1 ) || ( "$#" -ge "$numArgsMax"+1 ) || ( "$#" == 1 && "$1" == "--help" ) ]] ; then
	cat >&2 << EOF
Usage example(s): 
$nameOfThisProgram # no args 
EOF
	exit 1
fi

windowsLocalAppDataDirWindows="$(cmd.exe /c echo %APPDATA% 2>/dev/null | tr -d '\r')"  # I'm assuming that we're running inside WSL, not cygwin.  LOCALAPPDATA (and all it's windows env var friends eg. USERPROFILE) isn't defined inside WSL.  it is defined inside cmd.exe. 
windowsLocalAppDataDirUnix="$(wslpath -ua "$windowsLocalAppDataDirWindows")"
nvdaIniFilePath="$windowsLocalAppDataDirUnix"/nvda/nvda.ini
vi + "$nvdaIniFilePath"
