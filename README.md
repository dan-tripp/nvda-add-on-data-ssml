# nvda-add-on-data-ssml: An NVDA add-on which implements data-ssml

## General Info

- Inspired by https://www.w3.org/TR/spoken-html/#data-ssml-attribute-properties-and-values , roughly. 
- Demo video here: https://www.youtube.com/watch?v=wfTMUn4ttYI 

## The techniques and their problems 

All techniques have these things in common:
- They have two parts: 1) some Javascript (JS) that runs on the page, and 2) the NVDA plugin python code.
- The JS runs on page load.  It looks at each element that has a data-ssml attribute, encodes that attribute's value (details later), and adds that encoded value to the text content of the element.
	- This is necessary because I don't know of any way for an NVDA plugin to get the data-ssml attribute values, or even know that they're there.  In general, an NVDA plugin doesn't have access to the DOM.  It has access to an accessibility tree, roughly.  The data-ssml - and most DOM info and attributes - don't make it into this accessibility tree.  But all text content does.  So that's why we put the (encoded) data-ssml values in the text content. 
- The characters we use for encoding are obscure zero-width unicode characters.  So they don't show up visually, and they aren't announced by either NVDA or any other screen reader I tested with.  Unfortunately they do probably show up in braille output.  More on that later.  
- The python code intercepts the text content before it reaches the speech synth.  It looks for our encoding characters, and if it sees any, it replaces them with appropriate NVDA speech commands which will implement the wishes of the data-ssml.
- Our encoding characters were chosen for their obscurity.  If the page uses any of them already, some part of our process might break.
- This plugin implements my own loose dialect of data-ssml.  Not the full version at https://www.w3.org/TR/spoken-html/.

<table>
	<caption>Technique problem comparison</caption>
	<tbody>
		<tr>
			<td>
			<th>technique=inline
			<th>technique=dom-root
		</tr>
		<tr>
			<th scope="row">Left/right arrow nav sees junk characters
			<td>The worse technique.  The JS adds many silent junk characters.  Number of junk characters is approximately equal to the length of the data-ssml attribute value x 2.  That's at the start of the element that has the data-ssml attribute.  And at the end of the element: the JS adds 2 more. 
			<td>The better technique.  The JS adds approx. 2 junk characters at the start of the element.  And again 2 at the end.  At the start: those 2 characters take 4 right-arrow-key-presses to get through.  I don't know why.  TO DO: figure that out. 
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
			<td>The better technique.  Braille viewer sees much fewer characters.  Still: the negative user impact of this is still significant, I expect.
		</tr>
		<tr>
			<th scope="row">Bug: stale DOM root reference
			<td>The better technique.  Bug does not exist.
			<td>The worse technique.  Bug exists.  This means that sometimes, if the user hasn't yet arrowed or tabbed on the current page (eg. just loaded that page and NVDA is reading the whole page) this plugin's DOM root reference will be stale, which will result in either: 1) this plugin not working, or 2: this plugin using SSML from another web page i.e. whichever data-ssml-enabled web page it saw last.
		</tr>
		<tr>
			<th scope="row">Clipboard junk.  i.e. our encoding characters, even though they're invisible to the eye and the screen-reader-audio, show up if in the clipboard if you select and copy that part of the page.
			<td>The worse technique.  The JS adds approx 2 characters of clipboard junk per data-ssml character.
			<td>The better technique.  The JS adds a roughly-constant 6 characters of clipboard junk, regardless of the length of data-ssml.  4 characters at the start of the element + 2 characters at the end.
		</tr>
		<tr>
			<th scope="row">The JS adds somewhat-human-readable junk in DOM root, near the footer of the page
			<td>The better technique.  No junk here.
			<td>The worse technique.  Substantial junk here.
		</tr>
	</tbody>
</table>

## Developing 

- To keep NVDA's copy of this plugin (AKA add-on) in sync with this repo, I use NVDA's "scratchPad" directory.  Here are some ways to make that work:
	- symlink 
		- i.e. in Windows, run a command prompt as administrator, then run something like this: mklink /D "C:\Users\dt\AppData\Roaming\nvda\scratchpad\globalPlugins\nvda-add-on-data-ssml" "\\wsl.localhost\Ubuntu\root\nvda-add-on-data-ssml" 
		- This might rely on WSL running.  It's unclear what "WSL running" means.  It seems not to mean "there are one or more interactive WSL shells running", because I shut down all my shells, and the symlink still worked.
	- Copy files 
		- I do all my edits to the code on NVDA's copy, then when it's time to commit I copy NVDA's copy to this repo.
		- These files are meant to help with that: copy-scratchpad-files-to-here.bash , copy-here-files-to-scratchpad.bash , cd-scratchpad.bash , git-add-commit-etc.bash . 


