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
cd "$(dirname "$0")"
#set -o xtrace

nameOfThisProgram="$(basename "$0")"

numArgsMin=0
numArgsMax=1
if [[ ( "$#" -le "$numArgsMin"-1 ) || ( "$#" -ge "$numArgsMax"+1 ) || ( "$#" == 1 && "$1" == "--help" ) ]] ; then
	cat >&2 << EOF
Usage example(s): 
$nameOfThisProgram [-m]
EOF
	exit 1
fi

if [ $# -eq 0 ]; then
	writeCommitMessage=0
elif [ "$1" = "-m" ]; then
	writeCommitMessage=1
else
	echo "Error: unknown argument '$1'"
	exit 1
fi

alias git-windows='/mnt/c/Program\ Files/Git/bin/git.exe'

cd ../nvda-add-on-data-ssml-private
((git add --all && if git diff-index --quiet HEAD --; then echo "No changes to commit." ; else echo "changed files:"; git diff --name-only --cached  && git commit -m . ; fi ) && git-windows push;) 
cd ~-

cp -r /mnt/c/Users/dt/AppData/Roaming/nvda/scratchpad/globalPlugins/* ./from-scratchpad
git add --all
if git diff-index --quiet HEAD --; then 
	echo "No changes to commit." ; 
else 
	echo "changed files:"; 
	git diff --name-only --cached
	if [ "$writeCommitMessage" -eq 1 ]; then
		git commit 
	else
		git commit -m . 
	fi
fi
git-windows push


