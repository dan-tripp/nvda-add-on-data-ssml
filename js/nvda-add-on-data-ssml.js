(function () {

window.NvdaAddOnDataSsml = window.NvdaAddOnDataSsml || {};

/* these variables are only used if technique == index.  not page-wide, b/c page-wide doesn't support watchForDomChanges. */
window.NvdaAddOnDataSsml.g_hidingPlaceElement = null;
window.NvdaAddOnDataSsml.g_hidingPlaceList = [];

window.NvdaAddOnDataSsml.initByUrlParams = function(urlParams_, defaultTechnique_, defaultWatchForDomChanges_) {
	let urlParams = new URLSearchParams(urlParams_);
	let technique = urlParams.has('technique') ? urlParams.get('technique') : defaultTechnique_;	
	let watchForDomChanges = urlParams.has('watchForDomChanges') ? (urlParams.get('watchForDomChanges') === 'true') : defaultWatchForDomChanges_;	
	NvdaAddOnDataSsml.initByTechnique(technique, watchForDomChanges);
}

/* if you call this multiple times: that is probably harmless.  
	- more commentary, probably not interesting: this function could be seen as idempotent if you just look at its effect on the DOM.  but it's not idempotent if you look at what's happening in the JS, because if watchForDomChanges_ is true, then on every call to this function, we'll add a new mutation observer, so when a mutation happens, multiple instances of our mutation observer will get called.  this won't matter much because the second and subsequent calls won't change the DOM, because of data-ssml-processed. */
window.NvdaAddOnDataSsml.initByTechnique = function(technique_, watchForDomChanges_) {
	if(technique_ === 'page-wide' && watchForDomChanges_) throw new Error("page-wide && watch: not supported yet");
	encodeAllDataSsmlAttribs(technique_);
	if(watchForDomChanges_) {
		startObserver(technique_);
	}
}

function isMutationInteresting(m_) {
    if (m_.type === 'attributes') {
        let el = m_.target;
        let prevValue = m_.oldValue;
        let newValue = el.getAttribute('data-ssml');
        return prevValue === null && newValue !== null; // i.e. we don't act support a data-ssml value changing (after it has initially appeared).  once we see it, it's spoken presentation is carved in stone until page reload.  we do support a data-ssml attribute /appearing/ (on an element where there was none before), even long after page load.  
    } else if (m_.type === 'childList') {
    	for (let node of m_.addedNodes) {
            if (node.nodeType === Node.ELEMENT_NODE && node.hasAttribute('data-ssml')) {
                return true;
            }
        }
    }
    return false;
}

function startObserver(technique_) {
	let observer = new MutationObserver((mutations__) => {
		if(!mutations__.some(isMutationInteresting)) return;
		console.debug(`data-ssml: in mutation observer: proceeding.`);
		encodeAllDataSsmlAttribs(technique_);
	});
	observer.observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['data-ssml'], attributeOldValue: true});
}

const HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES = '4b9b696c-8fc8-49ca-9bb9-73afc9bd95f7';
const HIDING_PLACE_GUID_FOR_INDEX_TECHNIQUE = 'b4f55cd4-8d9e-40e1-b344-353fe387120f';
const HIDING_PLACE_GUID_FOR_PAGE_WIDE_TECHNIQUE = 'c7a998a5-4b7e-4683-8659-f2da4aa96eee';
const INPUT_TYPES_SUPPORTED = new Set(['checkbox', 'radio', 'button', 'reset', 'submit', ]);
const SUPPORTED_SSML_INSTRUCTIONS = new Set(["say-as", "phoneme", "sub", "break"]);

function isPowerOfTwo(n_) {
	return (n_ & (n_ - 1)) !== 0;
}

function encodeStrAsZeroWidthChars(str_) {
    let encoder = new TextEncoder();
    let utf8Bytes = encoder.encode(str_);
    let bigInt = BigInt(0);

    for (let byte of utf8Bytes) {
        bigInt = (bigInt << BigInt(8)) + BigInt(byte);
    }

    const ENCODING_CHARS = [
		'\uFFF9', 
		'\u200C', 
		'\u200D',
		'\u2060',
		'\u2061',
		'\uFEFF',
		'\u2063',
		'\u2064',
		'\uFFFB',
		'\uFFFA',
		'\u206A',
		'\u206B',
		'\u206C',
		'\u206D',
		'\u206E',
		'\u206F', 
	];

    let n = ENCODING_CHARS.length;

    if(isPowerOfTwo(n)) {
    	throw new Error("Encoding character count must be a power of 2");
    }

    let baseNDigits = [];
    if (bigInt === BigInt(0)) {
        baseNDigits.push(0);
    } else {
        while (bigInt > 0) {
            baseNDigits.push(Number(bigInt % BigInt(n)));
            bigInt = bigInt / BigInt(n);
        }
    }
    baseNDigits.reverse();

    let result = '';
    for (let digit of baseNDigits) {
        result += ENCODING_CHARS[digit];
    }

	if(true) {
		let resultReadable = [...result].map(c => `\\u${c.codePointAt(0).toString(16).padStart(4, '0')}`).join('');
		console.debug(`data-ssml: encoded string: ${JSON.stringify({'orig str': str_, 'orig str len': str_.length, 'baseNDigits.length': baseNDigits.length, baseNDigits})}`);
		console.debug(`data-ssml: resultReadable: "${resultReadable}"`);
	}

    return result;
}

function assert(bool_) {
	if(!bool_) throw new Error();
}

class SsmlError extends Error {
	constructor(message_) {
		super(message_)
		this.name = 'SsmlError'
	}
}

/* note 1: you might be thinking "it's not really processed yet, so why are we adding the 'processed' attribute now?"  answer: b/c by adding this attribute now, we get the benefit that we won't re-process elements w/ data-ssml="" or SSML errors.  the only reason we wouldn't want to add this attribute now would be in case of an error during "processing" (i.e. adding encoding characters).  we don't currently care about that. */
function* getAllElemsWithDataSsmlNotProcessed(technique_) {
	let isTechniquePageWide = technique_ === 'page-wide';
	for(let element of document.querySelectorAll('[data-ssml]:not([data-ssml-processed]')) {
		element.setAttribute('data-ssml-processed', ''); /* see note 1 */ 
		let dataSsmlVal = element.getAttribute('data-ssml')?.trim();
		if(!dataSsmlVal) continue;
		try {
			doElementLevelChecks(element, isTechniquePageWide);
			doSsmlAttribChecks(dataSsmlVal, element.textContent, isTechniquePageWide);
			yield [element, dataSsmlVal];
		} catch(err) {
			if(err instanceof SsmlError) {
				console.warn(`data-ssml: Found some invalid or unsupported data-ssml.  So we will ignore the data-ssml attribute on this element.  ${err.message}  The failing element was: `, element);
			} else {
				throw err;
			}
		}
	}
}

function doElementLevelChecks(element_, isTechniquePageWide_) {
	let doesAncestorHaveDataSsml = element_.parentElement.closest('[data-ssml]');
	if(doesAncestorHaveDataSsml) {
		throw new SsmlError("This element which has data-ssml has an ancestor which also has data-ssml.  We will ignore the data-ssml on this element, and probably the data-ssml on those ancestor element(s) too - there might be other warnings logged about them.");
	}
	if(element_.children.length > 0) {
		throw new SsmlError("This element which has a data-ssml attribute has child elements.  So we will ignore the data-ssml attribute on this element.  To fix this, you need to rearrange your HTML along these lines: put a <span> around the text that you want to override the spoken presentation of, and make it the tightest span possible (i.e. make it cover the text that you want to cover and nothing else), then put the data-ssml attribute on that <span>.  And maybe put that <span> in an aria-labelledby target.");
		/* we don't support it b/c it's difficult-to-impossible to deal with on the python end.  (assuming technique=index|inline.)  our macro_start / macro_end markers can end up appearing in the speech filter's input sequence in different (string) elements of the speech command list that is passed to our speech filter.  and there might be eg. a LangChangeCommand or any number of non-strings between the two.  I've seen it.  I don't know how to deal with that.  it's reproduced by eg. this: <label data-ssml='...>yes<textarea></textarea></label>.  so instead do this: <label><span data-ssml='...>yes</span><textarea></textarea></label>*/
	}
	if(isTechniquePageWide_ && element_.tagName !== 'SPAN') {
		throw new SsmlError(`Found data-ssml on an element that is not a <span>, and technique=page-wide.  This plugin doesn't support this, because it's a sign of author confusion.  With this technique, the tagName of the element doesn't matter: only its textContent and the data-ssml value matter.  Technically we could easily support data-ssml on a non-<span>, but this might mislead the author into thinking that their data-ssml will take effect only on that element, or only on elements with the same tag name.  With this technique, neither of those things are true, or likely to ever be true.  Instead, with this technique, the author should add a separate section to their page - which should probably be unperceivable to the user, so should probably with CSS "display: none" on it - where they put all of their data-ssml.  Since this section should be unperceivable, it should have no semantics or operability, so it might as well be all <span>s.  If, on the other hand, they put data-ssml throughout the parts of the page that will be percieved by the end user, then under technique=page-wide, that is a sign of author confusion.  Under the other techniques, it is normal and desirable.`);
	}
	if(element_.tagName === 'TEXTAREA') {
		assert(!isTechniquePageWide_);
		throw new SsmlError(`Found data-ssml on a <textarea> element.  If you want to use SSML on the /label/ of this <textarea>, then put data-ssml on the label element instead (or - if your label wraps another element - put data-ssml on a text-only child element of the label).  If you want to use SSML on the /contents/ of this <textarea>, then your only option is to use technique=page-wide.`);
	}
	if(element_.tagName === 'INPUT') {
		assert(!isTechniquePageWide_);
		let type = element_.getAttribute('type');
		if(!INPUT_TYPES_SUPPORTED.has(type)) {
			throw new SsmlError(`Found data-ssml on an <input type="${type}">.  Our list of supported types is: ${[...INPUT_TYPES_SUPPORTED]}.  If you want to use SSML on the /label/ of this <input>, then put data-ssml on the label element instead (or - if your label wraps another element - put data-ssml on a text-only child element of the label).  If you want to use SSML on the /contents/ of this <input>: we don't support that, because it's unclear what it would mean.  data-ssml makes the most sense if you imagine it being put on a DOM text node that never changes.  Equivalently: on a DOM element which contains nothing but text that never changes.  And that DOM element can be a widget, or inside of a widget, or not.  But the following ideas don't make sense: 1) data-ssml on a value that can be edited by the user, and 2) data-ssml on an element that has content which is more complicated than just text.  The input types that we don't support fall into those categories.  (To elaborate on #1: this means the /value/ of a widget, not the name of it.  And a value that is /edited/ - not selected - by the user.)`);
		}
	}
	let isTextContentWhitespaceOnlyOrEmpty = /^\s*$/.test(element_.textContent);
	if(isTechniquePageWide_ && isTextContentWhitespaceOnlyOrEmpty) {
		throw new SsmlError(`Found data-ssml on an element that either has no text content or has whitespace-only text content.  This plugin doesn't support that - under technique=page-wide, which this page is - because this plugin relies on some meaningful text content - the longer the better.  This plugin effectively searches the rest of the page for matching text content, so if it searched for whitespace, it would override the spoken presentation of all of that whitespace.  Suggestion: use technique=index.`);
	}
}

function insistOnDictLikeObjWithOneVal(x_, key_ = undefined) {
	let hurdle1 = (x_ !== undefined && x_ !== null && typeof x_ === 'object' && !Array.isArray(x_));
	if(!hurdle1) {
		throw new SsmlError(`In parsed post-JSON object, we expected a dictionary-like object with exactly one key/value pair.  Instead we got this: ${JSON.stringify(x_)} .`);
	}
	let numKeys = Object.keys(x_).length;
	let hurdle2 = (numKeys === 1);
	if(!hurdle2) {
		throw new SsmlError(`In parsed post-JSON object, we expected a dictionary-like object with exactly one key/value pair.  Instead we got ${numKeys} pairs.  Object is: ${JSON.stringify(x_)} .`);
	}
	if(key_ !== undefined) {
		let actualKey = Object.keys(x_)[0];
		if(actualKey !== key_) {
			throw new SsmlError(`In parsed post-JSON object, we expected a key named "${key_}".  Instead we see a key named "${actualKey}".  Object in question: ${JSON.stringify(x_)}.`);
		}
	}
}

function doSsmlAttribChecks(ssmlStr_, textContent_, isTechniquePageWide_) {
	try {
		let ssmlObj = JSON.parse(ssmlStr_);
		insistOnDictLikeObjWithOneVal(ssmlObj);
		let instruction = Object.keys(ssmlObj)[0], instructionVal = ssmlObj[instruction];
		if(!SUPPORTED_SSML_INSTRUCTIONS.has(instruction)) {
			throw new SsmlError(`Found an unsupported SSML instruction: "${instruction}".`);
		}
		if(instruction === 'phoneme') {
			let alphabet = instructionVal['alphabet'];
			if(alphabet !== 'ipa') throw new SsmlError(`This plugin supports alphabet=ipa and nothing else.  Found alphabet=${alphabet}.`);
			let ph = instructionVal['ph'];
			if(!ph) throw new SsmlError(`Expected to see a non-empty value for "ph".`);
		} else if(instruction === 'break') {
			if(isTechniquePageWide_) {
				throw new SsmlError(`Found a data-ssml "break" command, and technique=page-wide.  This plugin doesn't support that, because "break" is typically used on an element which has no text content, and page-wide relies on that text content: it effectively searches the rest of the page for matching text content.`);
			} else {
				let isTextContentWhitespaceOnlyOrEmpty = /^\s*$/.test(textContent_);
				if(!isTextContentWhitespaceOnlyOrEmpty) {
					throw new SsmlError(`Found a data-ssml "break" command on text content that includes non-whitespace.  This plugin doesn't support that.  It only supports the "break" command on an element which has text content that is either empty or is all whitespace.`);
				}
			}
			insistOnDictLikeObjWithOneVal(instructionVal, 'time');
			let timeStr = instructionVal['time'];
			getBreakTimeMillisFromStr(timeStr);
		}
	} catch(err) {
		if(err instanceof SyntaxError) {
			throw new SsmlError(`Failed to parse the data-ssml value as JSON.  ${err}`);
		} else {
			throw err;
		}
	}
}

/* This parses a CSS time value, probably.  This function supports all of the examples on https://wpt.fyi/results/css/css-transitions/transition-duration-001.html?label=experimental&label=master&aligned except "foobar" I think.  I got to that page starting from https://www.w3.org/TR/spoken-html/#break which links to https://www.w3.org/TR/speech-synthesis11/#S3.2.3 which mentions "the time value format from the Cascading Style Sheets Level 2 Recommendation [CSS2]" and the link there to CSS2 is deprecated.  So I dug up https://drafts.csswg.org/css-values-3/#time on my own, and it links to that transition-duration-001.html page. */
function getBreakTimeMillisFromStr(str_) {
	let numberStr;
	if(str_.endsWith('ms')) {
		numberStr = str_.slice(0, -2);
	} else if(str_.endsWith('s')) {
		numberStr = str_.slice(0, -1);
	} else {
		throw new SsmlError(`While parsing time string: We expected this time string to end with "s" or "ms".  It doesn't.  String: "${str_}".`);
	}
	if (!/^-?(?:\d+|\.\d+|\d+\.\d+)$/.test(numberStr)) {
		throw new SsmlError(`While parsing time string: Failed to parse this string as a number: "${numberStr}".`);
	}
	let number = parseFloat(numberStr);
	if(number < 0) {
		throw new SsmlError(`While parsing time string: We expected a number >= 0.  Got ${number}.`);
	}
	return number;
}

function encodeAllDataSsmlAttribs_inlineTechnique() {
	for(let [elem, dataSsmlValue] of getAllElemsWithDataSsmlNotProcessed('inline')) {
		let encodedSsml = encodeStrAsZeroWidthChars(dataSsmlValue);
		const START_END_MARKER = '\u2062';
		elem.insertBefore(document.createTextNode(START_END_MARKER+encodedSsml+START_END_MARKER), elem.firstChild);
		const MACRO_END_MARKER = START_END_MARKER+START_END_MARKER;
		elem.appendChild(document.createTextNode(MACRO_END_MARKER));
	}
}

function encodeAllDataSsmlAttribs_pageWideTechnique() {
	let mapOfPlainTextStrToSsmlStr = getMapOfPlainTextStrToSsmlStr_pageWideTechnique();
	encodeAllDataSsmlAttribs_pageWide_addHidingPlaceElement(mapOfPlainTextStrToSsmlStr);
}

function encodeAllDataSsmlAttribs_pageWide_addHidingPlaceElement(mapOfPlainTextStrToSsmlStr_) {
	/* we don't bother to update our hiding place (in-memory) variables here, b/c we only read those if watchForDomChanges, and we haven't implemented watchForDomChanges && page-wide. */
	let div = document.createElement("div");
	let mapAsJson = jsonStringifyJsMap(mapOfPlainTextStrToSsmlStr_);
	div.textContent = `Please ignore. ${HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES} ${HIDING_PLACE_GUID_FOR_PAGE_WIDE_TECHNIQUE} ${mapAsJson}`;
	document.body.appendChild(div);
	window.NvdaAddOnDataSsml.g_hidingPlaceElement = null;
}

function jsonStringifyJsMap(map_) {
	let r = JSON.stringify(Object.fromEntries(map_));
	return r;
}

function getMapOfPlainTextStrToSsmlStr_pageWideTechnique() {
	let mapOfPlainTextStrToSsmlStr = new Map();
	for(let [elem, elemSsmlStr] of getAllElemsWithDataSsmlNotProcessed('page-wide')) {
		let elemPlainText = elem.textContent;
		if(!mapOfPlainTextStrToSsmlStr.has(elemPlainText)) {
			console.debug("data-ssml: map set:", JSON.stringify({elemPlainText, elemSsmlStr}, null, 0), 'from element:', elem);
			mapOfPlainTextStrToSsmlStr.set(elemPlainText, elemSsmlStr);
		} else {
			let firstSsmlStr = mapOfPlainTextStrToSsmlStr.get(elemPlainText);
			if(firstSsmlStr !== elemSsmlStr) {
				console.warn(`data-ssml: found mismatching data-ssml values for plain text "${elemPlainText}".  The first data-ssml was "${firstSsmlStr}".  The current data-ssml is "${elemSsmlStr}".  This program will use the first one and ignore the current one.`);
			}
		}
	}
	return mapOfPlainTextStrToSsmlStr;
}

function encodeAllDataSsmlAttribs_indexTechnique() {
	encodeAllDataSsmlAttribs_indexTechnique_encodeEachOccurrenceAsAnIndex();
	encodeAllDataSsmlAttribs_indexTechnique_createOrUpdateHidingPlaceElement();
}

function encodeAllDataSsmlAttribs_indexTechnique_createOrUpdateHidingPlaceElement() {
	if(haveWeCreatedTheHidingPlaceDomElementYet()) {
		encodeAllDataSsmlAttribs_indexTechnique_updateHidingPlaceElement();
	} else {
		encodeAllDataSsmlAttribs_indexTechnique_createHidingPlaceElement();
	}
}

function haveWeCreatedTheHidingPlaceDomElementYet() {
	let r = !!NvdaAddOnDataSsml.g_hidingPlaceElement;
	return r;
}

function encodeAllDataSsmlAttribs_indexTechnique_updateHidingPlaceElement() {
	let hidingPlaceListAsJson = JSON.stringify(NvdaAddOnDataSsml.g_hidingPlaceList);
	NvdaAddOnDataSsml.g_hidingPlaceElement.textContent = `Please ignore. ${HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES} ${HIDING_PLACE_GUID_FOR_INDEX_TECHNIQUE} ${hidingPlaceListAsJson}`;
}

function encodeAllDataSsmlAttribs_indexTechnique_createHidingPlaceElement() {
	let div = document.createElement("div");
	let hidingPlaceListAsJson = JSON.stringify(NvdaAddOnDataSsml.g_hidingPlaceList);
	div.textContent = `Please ignore. ${HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES} ${HIDING_PLACE_GUID_FOR_INDEX_TECHNIQUE} ${hidingPlaceListAsJson}`;
	document.body.appendChild(div);
	NvdaAddOnDataSsml.g_hidingPlaceElement = div;
}

/* in this function we will add to the in-memory hiding place list.  so the in-memory list will out of sync (and newer) than the in-DOM list.  shortly after this function, we will write the in-memory list to the DOM. */
function encodeAllDataSsmlAttribs_indexTechnique_encodeEachOccurrenceAsAnIndex() {
	let hidingPlaceList = NvdaAddOnDataSsml.g_hidingPlaceList;
	for(let [elem, curSsmlStr] of getAllElemsWithDataSsmlNotProcessed('index')) {
		let idxInHidingPlaceListOfCurSsmlStr = hidingPlaceList.indexOf(curSsmlStr);
		if(idxInHidingPlaceListOfCurSsmlStr == -1) {
			hidingPlaceList.push(curSsmlStr);
			idxInHidingPlaceListOfCurSsmlStr = hidingPlaceList.length-1;
			console.debug(`data-ssml: New index: ${idxInHidingPlaceListOfCurSsmlStr}.  SSML: "${curSsmlStr}".  For element: `, elem);
		} else {
			console.debug(`data-ssml: Reusing index ${idxInHidingPlaceListOfCurSsmlStr}.  SSML: "${curSsmlStr}".  For element: `, elem);
		}
		let encodedIdxInHidingPlaceListOfCurSsmlStr = encodeStrAsZeroWidthChars(idxInHidingPlaceListOfCurSsmlStr.toString());
		const MARKER = '\u2062';
		elem.insertBefore(document.createTextNode(MARKER+encodedIdxInHidingPlaceListOfCurSsmlStr+MARKER), elem.firstChild);
		const MACRO_END_MARKER = MARKER+MARKER;
		elem.appendChild(document.createTextNode(MACRO_END_MARKER));
	}
}

function encodeAllDataSsmlAttribs(technique_) {
	if(technique_ === 'index') {
		encodeAllDataSsmlAttribs_indexTechnique();
	} else if(technique_ === 'inline') {
		encodeAllDataSsmlAttribs_inlineTechnique();
	} else if(technique_ === 'page-wide') {
		encodeAllDataSsmlAttribs_pageWideTechnique();
	} else {
		throw new Error();
	}
}

})();
