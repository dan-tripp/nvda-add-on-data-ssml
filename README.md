# nvda-add-on-data-ssml: An NVDA add-on which implements data-ssml

## General Info

- Inspired by https://www.w3.org/TR/spoken-html/#data-ssml-attribute-properties-and-values , roughly. 
- Demo video here: https://www.youtube.com/watch?v=wfTMUn4ttYI 

## Developing 

- To keep NVDA's copy of this plugin (AKA add-on) in sync with this repo, I use NVDA's "scratchPad" directory.  Here are some ways to make that work:
	- symlink 
		- i.e. in Windows, run a command prompt as administrator, then run something like this: mklink /D "C:\Users\dt\AppData\Roaming\nvda\scratchpad\globalPlugins\nvda-add-on-data-ssml" "\\wsl.localhost\Ubuntu\root\nvda-add-on-data-ssml" 
		- This might rely on WSL running.  It's unclear what "WSL running" means.  It seems not to mean "there are one or more interactive WSL shells running", because I shut down all my shells, and the symlink still worked.
	- Copy files 
		- I do all my edits to the code on NVDA's copy, then when it's time to commit I copy NVDA's copy to this repo.
		- These files are meant to help with that: copy-scratchpad-files-to-here.bash , copy-here-files-to-scratchpad.bash , cd-scratchpad.bash , git-add-commit-etc.bash . 

