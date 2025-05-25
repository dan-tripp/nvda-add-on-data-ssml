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

## Techniques: Pros and Cons 


<table>
	<tbody>
		<tr>
			<td>
			<th>technique=inline
			<th>technique=dom-root
		</tr>
		<tr>
			<th scope="row">Left/right arrow nav sees junk characters
			<td>The worse technique.  The JS adds many silent junk characters.  Number of junk characters is approximately equal to the length of the data-ssml attribute value x 2.  That's at the start of the element that has the data-ssml attribute.  And at the end of the element: the JS adds 2 more. 
			<td>The better technique.  The JS adds approx. 2 junk characters at the start of the element.  And again 2 at the end.  At the start: those 2 characters take 4 right-arrow pressed to get through.  I don't know why.  TO DO: figure that out. 
		</tr>
		<tr>
			<th scope="row">Up/down arrow is different due to junk characters 
			<td>The worse technique.  Noticeable.
			<td>The better technique.  Not noticeable.
		</tr>
		<tr>
			<th scope="row">Max length of SSML
			<td>The worse technique.  Plugin will only work if len(textContent) 2*len(ssmlJsonString) + 2 <= 100 , roughly.  
			<td>The better technique.  No length limit. 
		</tr>
		<tr>
			<th scope="row">NVDA braille viewer sees junk characters 
			<td>The worse technique.  Braille viewer sees a lot of junk characters.
			<td>The better technique.  Braille viewer sees much fewer characters.
		</tr>
		<tr>
			<th scope="row">Bug: stale DOM root reference
			<td>The better technique.  Bug does not exist.
			<td>The worse technique.  Bug exists.  This means that sometimes, if the user hasn't arrowed or tabbed yet (eg. is reading the whole document) this plugin's DOM root reference will be stale, which will result in either: 1) this plugin not working, or 2: this plugin using SSML from another web page i.e. whichever data-ssml-enabled web page it saw last.
		</tr>
		<tr>
			<th scope="row">Adds somewhat-human-readable junk in the footer
			<td>The better technique.  No junk here.
			<td>The worse technique.  Substantial junk here.
		</tr>
	</tbody>
</table>


