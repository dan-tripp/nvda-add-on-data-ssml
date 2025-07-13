#!/usr/bin/env bash

set -euo pipefail

PATH="$PATH":/mnt/c/cygwin64/home/dt/apps

pict_model_file_path="$(mktemp --tmpdir pict-model-XXXXXXXX)"

cat << EOF > "$pict_model_file_path"

TECHNIQUE: inline, index, page-wide
BROWSER: chrome, firefox, edge
ARROW_NAV: regular, table
SYNTH: eSpeak, sapi5, OneCore

#IF [OS] = "Ubuntu" THEN [DotNetVersion] =  "NA" ELSE [DotNetVersion] <> "NA";

EOF

order=2

# Test run, checking for errors: 
pict.exe "$pict_model_file_path" "$@" 2>&1 >/dev/null 

# Prints generated tests: 
pict_output_file_path="$(mktemp --tmpdir pict-output-XXXXXXXX)"
pict.exe "$pict_model_file_path" /o:"$order" "$@" > "$pict_output_file_path"
(head -1 "$pict_output_file_path" ; tail +2 "$pict_output_file_path" | sort -V ) | dos2unix | column -t

# Prints stats: 
pict.exe "$pict_model_file_path" /o:"$order" /s "$@" | dos2unix

echo Raw PICT output is at "$pict_output_file_path"


