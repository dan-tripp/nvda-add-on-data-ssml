# nvda-add-on-data-ssml: An NVDA add-on which implements data-ssml

## Intro 

- The goal of this add-on is accurate "spoken presentation" (sometimes called just "pronunciation").  Specifically on web pages. 
- This add-on accomplishes that goal by implementing support for the "data-ssml" attribute on web pages, as per the spec at https://www.w3.org/TR/spoken-html/.
- A demo video of this add-on is here: https://www.youtube.com/watch?v=wfTMUn4ttYI .  

## Support of the spec 

- This add-on implements parts of the spec at https://www.w3.org/TR/spoken-html/.  Not all of it.  The "Single-attribute Approach", not the "Multi-attribute Approach".
- The SSML instructions that this add-on supports are: "say-as", "phoneme", "sub", "break".  There are caveats to most of those.
- For "say-as": this add-on supports only the "interpret-as" sub-instruction, and of it: only "characters" and "spell" (as a synonym for "characters").
- For "phoneme": this add-on supports only the alphabet "ipa".  Not "x-sampa".
- This add-on does not support: "voice", "emphasis", "prosody", "audio".
- The spec seems ambiguous to me as to whether it's valid to have multiple SSML instructions in one data-ssml attribute eg. &lt;span data-ssml='{"sub": {"alias": "3 prime"}, "break": {"time": "500ms"}}'&gt;3'&lt;/span&gt; .  Regardless, this add-on doesn't support that.

## How this add-on works 

This add-on can be configured to use one of several "techniques", but regardless of technique, this is roughly how it works: 
- The add-on has two parts: 1) some Javascript (JS) that runs on the page, and 2) the NVDA add-on python code.
- The JS runs on page load.  It looks at each element that has a data-ssml attribute, encodes that attribute's value (details later), and adds that encoded value to the text content of the element.
	- This is necessary because I don't know of any way for this NVDA add-on to get the data-ssml attribute values.  NVDA add-ons don't have access to the DOM.  They have access to an accessibility tree, roughly.  The data-ssml, as well as most of the DOM's info and attributes, doesn't make it into this accessibility tree.  But all text content does.  That's why we put the (encoded) data-ssml values in the text content. 
- The characters we use for encoding are obscure zero-width unicode characters.  So they don't show up visually, and they aren't spoken (in the audio output) by either NVDA or any other screen reader I tested with.  Unfortunately they probably show up in braille output.  More on that later.  
- The python code intercepts the text content before it reaches the speech synth.  It looks for our encoding characters, and if it sees any, it replaces them with appropriate NVDA speech commands which will implement the wishes of the data-ssml.
- Our encoding characters were chosen for their obscurity.  If the page uses any of them already, some part of our process might break.
- This add-on doesn't support whitespace.  That is: this add-on doesn't support multiple words which are separated by whitespace or a &lt;br&gt; (line break) element.  Of course it's fine to have whitespace and line breaks on your web page.  But it's not supported to have whitespace or line breaks inside of an element which has data-ssml on it.  This means that you can't override the spoken presentation of "St. Paul, Minn" in one shot - instead, you will need to override "St." and "Minn" separately.  This is because NVDA, when the user is navigating with the up/down arrow keys, will obviously break up sentences into "chunks" or "lines".  (This kind of "line" usually doesn't correspond with a visual line.  "Line" here means whatever NVDA's up/down arrow keys move across.)  NVDA will often, more-or-less at random, consider the second word in any pair of words to be part of the next "line".  In order for this add-on to work, each unit of "plain text" (i.e. the text that this add-on will override the spoken presentation of) needs to be sent to our speech filter function in one function call.  That means that the entire plain text needs to be contained in one "line".  If the plain text has multiple words, then there is no guarantee of this.  So this add-on refuses to try to handle it.
	- For the same reason, this add-on doesn't support overriding the spoken presentation of very long words.  Approx. 100 characters seems to be the limit.
- For most cases, the choice of technique will not affect the spoken presentation (i.e. audio output by NVDA).  But there are some exceptions to this rule i.e. cases where one technique supports a certain thing, and another technique doesn't.
- The negative side effects, if the JS part of this add-on is run on a page and the user is not running (the python part of) this add-on, and who is...
	- ... a user of NVDA: are the same as for a user of NVDA who _is_ running this add-on.
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
			<th>technique=page-wide
		</tr>
		<tr>
			<th scope="row">Description of technique
			<td>The JS adds an encoded version of the entire data-ssml attribute value into the text content of the element that has the data-ssml attribute.  So this technique adds a lot of our encoding characters all over the page.
			<td>The JS adds a list of all of the data-ssml attribute values on the page into a central "hiding place" in the DOM root, near the footer.  To the text content of each element that has the data-ssml attribute, the JS only adds an encoded integer index, which represents an array index in the central "hiding place".  So this adds a lot less of our encoding characters all over the page than the "inline" technique does.
			<td>Lets you do a "page-wide override" of how a certain string is spoken.  Doesn't let you do any kind of spoken presentation control beyond this.  So you can have "3'" spoken as "3 prime" or "3 feet", but not both - not on the same web page.  Like technique=index, the JS adds one "hiding place" to the web page.  Unlike the other two techniques, in this technique the JS doesn't add any encoded characters to the text content.  The string lookup uses a case-insensitive whole-word regex, roughly.
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
			<th scope="row">Max length of SSML i.e. max length of the string $SSML in &lt;span data-ssml="$SSML"&gt;$PLAIN_TEXT&lt;/span&gt;
			<td>The worst technique.  Add-on will only work if len($PLAIN_TEXT) 2*len($SSML) + 2 <= 100 , roughly.  That's for arrow nav and tab, I think.  Table nav (ctrl+alt+arrow_key) gets away with more, for some reason.  At any rate: this max length is easy to exceed with this technique.  e.g SSML = "'{"say-as": {"interpret-as": "characters"}}'" is close to it. 
			<td>Tied for the best technique.  No max length.
			<td>Tied for the best technique.  No max length.
		</tr>
		<tr>
			<th scope="row">Max length of plain text i.e. max length of the string $PLAIN_TEXT in &lt;span data-ssml="$SSML"&gt;$PLAIN_TEXT&lt;/span&gt;
			<td>The worst technique.  For reasons: see the comment for the row "Max length of SSML".
			<td>The middle technique.  The max length is approx. 96 characters, which is probably high enough that you won't exceed it in the real world.  It's the same limit that's shown in the formula in the row "Max length of SSML", but with this techique $SSML is an index (i.e. an integer) so len($SSML) = 1 (roughly), so the formula collapses like this: <br>
			len($PLAIN_TEXT) 2*len($SSML) + 2 <= 100<br>
			len($PLAIN_TEXT) 2*1 + 2 <= 100<br>
			len($PLAIN_TEXT) <= 96<br>
			<td>The best technique.  Max length is approx. 100. 
		</tr>
		<tr>
			<th scope="row">Max number of overrides on a page for a given plain text string
			<td>Tied for the best technique.  No max.
			<td>Tied for the best technique.  No max.
			<td>The worst technique.  Max=1.  This is a serious limitation.
		</tr>
		<tr>
			<th scope="row">NVDA braille viewer sees junk characters 
			<td>The worse technique.  Braille viewer sees a lot of junk characters.
			<td>The middle technique.  Braille viewer sees much fewer characters.  Still: the negative user impact of this is still significant, I expect.
			<td>The best technique.  Braille viewer sees no junk characters, because the JS didn't add any. 
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
		<tr>
			<th scope="row">Supports SSML on the <i>contents</i> (not label) of a &lt;textarea&gt;
			<td>Not supported.
			<td>Not supported.
			<td>Supported.  Whether supporting this is a good thing or not is another question.
		</tr>
		<tr>
			<th scope="row">SSML "break" instruction
			<td>"time" attribute: supported.  eg. data-ssml='{"break":{"time":"500ms"}'  Other spuported "time" values include "500ms", "1s", "0.5s".<br>"strength" attribute (weak, strong, etc.): not supported.  
			<td>Same as technique=inline (the table cell to the left of this one.)
			<td>Not supported.  Reason: "break" is typically used on an element which has no text content, and page-wide relies on that text content: it effectively searches the rest of the page for matching text content.
		</tr>
	</tbody>
</table>



## Installing 

If you have an .nvda-addon file for this project:
- This file will be called something like data_ssml-0.1.nvda-addon. 
- Option 1: "Double-click" on that .nvda-addon file, to install it.  Or, with the keyboard: in Windows Explorer, move your focus to the .nvda-addon file, the press ENTER.
	- This installation method (via mouse or keyboard) will only work if NVDA is running.  So if it isn't: run it.
- Option 2: With NVDA running, go to NVDA in the task bar > Tools > Add-on store > Install from external source, and select the .nvda-addon file.
- Regardless of option: you will need to restart NVDA for the add-on to take effect.  NVDA will probably prompt you to do this.


## Developing 

- To build, for distribution: "Open a command line, change to the folder that has the sconstruct file (usually the root of your add-on development folder) and run the scons command. The created add-on, if there were no errors, is placed in the current directory." (copied from https://github.com/nvdaaddons/AddonTemplate/blob/master/readme.md)

- For convenience while developing: I use NVDA's "scratchPad" directory, and I keep this repo in sync with the scratchPad directory.  Here are two options for how to do that: 
	- (A prerequisite is to enable the scratchpad directory.  nvda > preferences > settings > advanced > ... )
	- option 1: symlink 
		- i.e. in Windows, run a command prompt as administrator, then run something like this: mklink /D "C:\Users\dt\AppData\Roaming\nvda\scratchpad\globalPlugins\data_ssml" "\\wsl.localhost\Ubuntu\root\nvda-add-on-data-ssml\addon\globalPlugins\data_ssml"  
			- this will create a link from nvda's scratchPad directory to the git repo, not the other way around.  so nvda - via it's scratchPad directory - will find your repo this way.  the git repo in no way finds the nvda scratchPad directory.
		- This might rely on WSL running.  It's unclear what "WSL running" means.  It seems not to mean "there are one or more interactive WSL shells running", because I shut down all my shells, and the symlink still worked.
	- option 2: copy files 
		- do all your edits to the code on NVDA's copy, then when it's time to commit I copy NVDA's copy to this repo.



