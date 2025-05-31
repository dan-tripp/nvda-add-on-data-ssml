# nvda-add-on-data-ssml: An NVDA add-on which implements data-ssml

## Intro 

- Inspired by https://www.w3.org/TR/spoken-html/#data-ssml-attribute-properties-and-values , roughly. 
- Demo video here: https://www.youtube.com/watch?v=wfTMUn4ttYI 

## How this plugin works 

This plugin can be configured to use one of several "techniques", but regardless of technique, this is roughly how it works: 
- The plugin has two parts: 1) some Javascript (JS) that runs on the page, and 2) the NVDA plugin python code.
	- I use the words "plugin" and "add-on" interchangeably.
- The JS runs on page load.  It looks at each element that has a data-ssml attribute, encodes that attribute's value (details later), and adds that encoded value to the text content of the element.
	- This is necessary because I don't know of any way for this NVDA plugin to get the data-ssml attribute values.  NVDA plugins don't have access to the DOM.  They have access to an accessibility tree, roughly.  The data-ssml, as well as most of the DOM's info and attributes, doesn't make it into this accessibility tree.  But all text content does.  That's why we put the (encoded) data-ssml values in the text content. 
- The characters we use for encoding are obscure zero-width unicode characters.  So they don't show up visually, and they aren't announced (in the audio output) by either NVDA or any other screen reader I tested with.  Unfortunately they probably show up in braille output.  More on that later.  
- The python code intercepts the text content before it reaches the speech synth.  It looks for our encoding characters, and if it sees any, it replaces them with appropriate NVDA speech commands which will implement the wishes of the data-ssml.
- Our encoding characters were chosen for their obscurity.  If the page uses any of them already, some part of our process might break.
- This plugin implements my own loose dialect of the data-ssml JSON format.  Not the full version at https://www.w3.org/TR/spoken-html/. 
- Regardless of technique, the audio output by NVDA will be the same.
- The negative side effects if the JS part of this plugin is run on a page and the user is not running (the python part of) this plugin, and who is...
	- ... a user of NVDA: are the same as for a user of NVDA who _is_ running this plugin.
	- ... a user of JAWS: I don't know, because I haven't tested on JAWS. 
	- ... a user of VoiceOver / TalkBack: none in the audio.  Some regarding the delimiting of words/sentences.  TO DO: elaborate.  
	- ... all users, including non-screen-reader users: "clipboard junk".  See table below. 

<table>
	<caption>Technique comparison</caption>
	<tbody>
		<tr>
			<td>
			<th>technique=inline
			<th>technique=index
			<th>technique=page-wide-override
		</tr>
		<tr>
			<th scope="row">Description of technique
			<td>The JS adds an encoded version of the entire data-ssml attribute value into the text content of the element that has the data-ssml attribute.  So this technique adds a lot of our encoding characters all over the page.
			<td>The JS adds a list of all of the data-ssml attribute values on the page into a central "hiding place" in the DOM root, near the footer.  To the text content of each element that has the data-ssml attribute, the JS only adds an encoded integer index, which represents an array index in the central "hiding place".  So this adds a lot less of our encoding characters all over the page than the "inline" technique does.
			<td>Like technique=index, the JS uses a central "hiding place".  Unlike the other two techniques, in this technique the JS adds nothing to the text content.  Instead, the plugin does a string lookup to do a central lookup of plainText -> SSML.  This technique assumes that you only want to override plainText XYZ one way on a page.  So you can have "3'" announced as "3 prime" or "3 feet", but not both.  The string lookup uses a case-insensitive whole-word regex, roughly.
		</tr>
		<tr>
			<th scope="row">Left/right arrow nav sees junk characters
			<td>The worst technique.  The JS adds many silent junk characters.  Number of junk characters is approximately equal to the length of the data-ssml attribute value x 2.  That's at the start of the element that has the data-ssml attribute.  And at the end of the element: the JS adds 2 more. 
			<td>The middle technique.  The JS adds approx. 2 junk characters at the start of the element.  And again 2 at the end.  At the start: those 2 characters take 4 right-arrow-key-presses to get through.  I don't know why.  TO DO: figure that out. 
			<td>The best technique.  The JS adds no junk characters here.
		</tr>
		<tr>
			<th scope="row">Up/down arrow is different due to junk characters 
			<td>The worst technique.  Noticeable.
			<td>The almost-best technique.  I didn't notice it, but there might be cases that I'm missing.
			<td>The best technique.  The JS adds no junk characters here.
		</tr>
		<tr>
			<th scope="row">Max length of SSML
			<td>The worst technique.  Plugin will only work if len(textContent) 2*len(ssmlJsonString) + 2 <= 100 , roughly.  
			<td>Tied for the best technique.  No length limit. 
			<td>Tied for the best technique.  No length limit. 
		</tr>
		<tr>
			<th scope="row">NVDA braille viewer sees junk characters 
			<td>The worse technique.  Braille viewer sees a lot of junk characters.
			<td>The middle technique.  Braille viewer sees much fewer characters.  Still: the negative user impact of this is still significant, I expect.
			<td>The best technique.  Braille viewer sees no junk characters, because the JS didn't add any. 
		</tr>
		<tr>
			<th scope="row">Bug: stale DOM root reference
			<td>The best technique.  Bug does not exist.
			<td>Tied for the worst technique.  Bug exists.  This bug means that sometimes, if the user hasn't yet arrowed or tabbed on the current page (eg. just loaded that page and NVDA is reading the whole page - I think - details unclear) then this plugin's DOM root reference will be stale, which will result in either: 1) this plugin not working, or 2: this plugin using SSML from another web page i.e. whichever data-ssml-enabled web page it saw last.
			<td>Tied for the worst technique.  Same bug. 
		</tr>
		<tr>
			<th scope="row">Clipboard junk.  i.e. our encoding characters, even though they're invisible to the eye and silent in the screen reader audio, show up in the clipboard if you select and copy that part of the page.
			<td>The worse technique.  The JS adds approx 2 characters of clipboard junk per data-ssml character.
			<td>The middle technique.  The JS adds a roughly-constant 6 characters of clipboard junk, regardless of the length of data-ssml.  4 characters at the start of the element + 2 characters at the end.
			<td>The best technique.  The JS adds no clipboard junk.
		</tr>
		<tr>
			<th scope="row">The JS adds somewhat-human-readable junk in DOM root, near the footer of the page
			<td>The best technique.  No junk here.
			<td>Tied for the worst technique.  Substantial junk here.
			<td>Tied for the worst technique.  Same amount of junk, roughly. 
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


