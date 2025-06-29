(function () {

window.NvdaAddOnDataSsml = window.NvdaAddOnDataSsml || {};

window.NvdaAddOnDataSsml.init = function(technique_) {
	encodeAllDataSsmlAttribs(technique_);
}

const HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES = '4b9b696c-8fc8-49ca-9bb9-73afc9bd95f7';
const HIDING_PLACE_GUID_FOR_INDEX_TECHNIQUE = 'b4f55cd4-8d9e-40e1-b344-353fe387120f';
const HIDING_PLACE_GUID_FOR_PAGE_WIDE_OVERRIDE_TECHNIQUE = 'c7a998a5-4b7e-4683-8659-f2da4aa96eee';
const INPUT_TYPES_SUPPORTED = new Set(['checkbox', 'radio', 'button', 'reset', 'submit', ]);

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
		console.log(`encoded string: ${JSON.stringify({'orig str': str_, 'orig str len': str_.length, 'baseNDigits.length': baseNDigits.length, baseNDigits})}`);
		console.log(`resultReadable: "${resultReadable}"`);
	}

    return result;
}

function* getAllElemsWithDataSsml(technique_) {
	
	for(let element of document.querySelectorAll('[data-ssml]')) {
		let dataSsmlVal = element.getAttribute('data-ssml')?.trim();
		if(!dataSsmlVal) continue;
		if(element.children.length > 0) {
			console.error("This element which has a data-ssml attribute has child elements.  This plugin doesn't support that.  So we will ignore the data-ssml attribute on this element.  To fix this, you need to rearrange your HTML along these lines: put a <span> around the text that you want to override the spoken presentation of, and make it the tightest span possible (i.e. make it cover the text that you want to cover and nothing else), then put the data-ssml attribute on that <span>.  And maybe put that <span> in an aria-labelledby target.  The failing element was: ", element);
			/* we don't support it b/c it's difficult-to-impossible to deal with on the python end.  (assuming technique=index|inline.)  our macro_start / macro_end markers can end up appearing in the speech filter's input sequence in different (string) elements of the speech command list that is passed to our speech filter.  and there might be eg. a LangChangeCommand or any number of non-strings between the two.  I've seen it.  I don't know how to deal with that.  it's reproduced by eg. this: <label data-ssml='...>yes<textarea></textarea></label>.  so instead do this: <label><span data-ssml='...>yes</span><textarea></textarea></label>*/
			continue;
		} else if(element.tagName === 'TEXTAREA') {
			console.error(`Found data-ssml on a <textarea> element. This plugin doesn't support that.   So we will ignore the data-ssml attribute on this element.  If you want to use SSML on the /label/ of this <textarea>, then put data-ssml on the label element instead (or - if your label wraps another element - put data-ssml on a text-only child element of the label).  If you want to use SSML on the /contents/ of this <textarea>, then your only option is to use technique=page-wide-override.  Currently using technique=${technique_}.  The failing element was: `, element);
			continue;
		} else if(element.tagName === 'INPUT') {
			let type = element.getAttribute('type');
			if(!INPUT_TYPES_SUPPORTED.has(type)) {
				console.error(`Found data-ssml on an <input type="${type}">.  This plugin doesn't support that.   So we will ignore the data-ssml attribute on this element.  Our list of supported types is: ${[...INPUT_TYPES_SUPPORTED]}.  If you want to use SSML on the /label/ of this <input>, then put data-ssml on the label element instead (or - if your label wraps another element - put data-ssml on a text-only child element of the label).  If you want to use SSML on the /contents/ of this <input>: we don't support that, because it's unclear what it would mean.  data-ssml makes the most sense if you imagine it being put on a DOM text node that never changes.  Equivalently: on a DOM element which contains nothing but text that never changes.  And that DOM element can be a widget, or inside of a widget, or not.  But the following ideas don't make sense: 1) data-ssml on a value that can be edited by the user, and 2) data-ssml on an element that has content which is more complicated than just text.  The input types that we don't support fall into those categories.  (To elaborate on #1: we mean a /value/ of a widget, not a widget.  And a value that is /edited/ - not selected - by the user.)  The failing element was: `, element);
				continue;
			}
		}
		yield [element, dataSsmlVal];
	}
}

function encodeAllDataSsmlAttribs_inlineTechnique() {
	for(let [elem, dataSsmlValue] of getAllElemsWithDataSsml('inline')) {
		let encodedSsml = encodeStrAsZeroWidthChars(dataSsmlValue);
		const START_END_MARKER = '\u2062';
		elem.insertBefore(document.createTextNode(START_END_MARKER+encodedSsml+START_END_MARKER), elem.firstChild);
		const MACRO_END_MARKER = START_END_MARKER+START_END_MARKER;
		elem.appendChild(document.createTextNode(MACRO_END_MARKER));
		for(let descendentElem of [...elem.querySelectorAll('[data-ssml]')]) {
			console.warn(`Found data-ssml in a descendent of an element that has a data-ssml attribute.  We will ignore this one (the descendent.)`, descendentElem);
		}
	}
}

function encodeAllDataSsmlAttribs_pageWideOverrideTechnique() {
	let mapOfPlainTextStrToSsmlStr = getMapOfPlainTextStrToSsmlStr_pageWideOverrideTechnique();
	encodeAllDataSsmlAttribs_pageWideOverrideTechnique_addCentralHidingPlaceElement(mapOfPlainTextStrToSsmlStr);
}

function encodeAllDataSsmlAttribs_pageWideOverrideTechnique_addCentralHidingPlaceElement(mapOfPlainTextStrToSsmlStr_) {
	let div = document.createElement("div");
	let mapAsJson = jsonStringifyJsMap(mapOfPlainTextStrToSsmlStr_);
	div.textContent = `Please ignore. ${HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES} ${HIDING_PLACE_GUID_FOR_PAGE_WIDE_OVERRIDE_TECHNIQUE} ${mapAsJson}`;
	document.body.appendChild(div);
}

function jsonStringifyJsMap(map_) {
	let r = JSON.stringify(Object.fromEntries(map_));
	return r;
}

function getMapOfPlainTextStrToSsmlStr_pageWideOverrideTechnique() {
	let mapOfPlainTextStrToSsmlStr = new Map();
	for(let elem of [...document.querySelectorAll('[data-ssml]')]) {
		let elemSsmlStr = elem.getAttribute('data-ssml');
		if(!elemSsmlStr) continue;
		let elemPlainText = elem.textContent;
		if(!mapOfPlainTextStrToSsmlStr.has(elemPlainText)) {
			console.log(new Date(), "map set:", JSON.stringify({elemPlainText, elemSsmlStr}, null, 0), 'from element:', elem);
			mapOfPlainTextStrToSsmlStr.set(elemPlainText, elemSsmlStr);
		} else {
			let firstSsmlStr = mapOfPlainTextStrToSsmlStr.get(elemPlainText);
			if(firstSsmlStr !== elemSsmlStr) {
				console.log(`Warning: found mismatching data-ssml values for plain text "${elemPlainText}".  The first data-ssml was "${firstSsmlStr}".  The current data-ssml is "${elemSsmlStr}".  This program will use the first one and ignore the current one.`);
			}
		}
	}
	return mapOfPlainTextStrToSsmlStr;
}

function encodeAllDataSsmlAttribs_indexTechnique() {
	let globalListOfSsmlStrs = encodeAllDataSsmlAttribs_indexTechnique_encodeEachOccurrenceAsAnIndex();
	encodeAllDataSsmlAttribs_indexTechnique_addCentralHidingPlaceElement(globalListOfSsmlStrs);
}

function encodeAllDataSsmlAttribs_indexTechnique_addCentralHidingPlaceElement(globalListOfSsmlStrs_) {
	let div = document.createElement("div");
	let globaListAsJson = JSON.stringify(globalListOfSsmlStrs_);
	div.textContent = `Please ignore. ${HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES} ${HIDING_PLACE_GUID_FOR_INDEX_TECHNIQUE} ${globaListAsJson}`;
	document.body.appendChild(div);
}

function encodeAllDataSsmlAttribs_indexTechnique_encodeEachOccurrenceAsAnIndex() {
	let globalListOfSsmlStrs = [];
	for(let [elem, curSsmlStr] of getAllElemsWithDataSsml('index')) {
		let indexOfCurSsmlStrInGlobalList = globalListOfSsmlStrs.indexOf(curSsmlStr);
		if(indexOfCurSsmlStrInGlobalList == -1) {
			globalListOfSsmlStrs.push(curSsmlStr);
			indexOfCurSsmlStrInGlobalList = globalListOfSsmlStrs.length-1;
			console.info(`New index: ${indexOfCurSsmlStrInGlobalList}.  SSML: "${curSsmlStr}".  For element: `, elem);
		} else {
			console.info(`Reusing index ${indexOfCurSsmlStrInGlobalList}.  SSML: "${curSsmlStr}".  For element: `, elem);
		}
		let indexOfCurSsmlStrInGlobalListEncoded = encodeStrAsZeroWidthChars(indexOfCurSsmlStrInGlobalList.toString());
		const MARKER = '\u2062';
		elem.insertBefore(document.createTextNode(MARKER+indexOfCurSsmlStrInGlobalListEncoded+MARKER), elem.firstChild);
		const MACRO_END_MARKER = MARKER+MARKER;
		elem.appendChild(document.createTextNode(MACRO_END_MARKER));
		for(let descendentElem of [...elem.querySelectorAll('[data-ssml]')]) {
			console.warn(`Found data-ssml in a descendent of an element that has a data-ssml attribute.  We will ignore this one (the descendent.)`, descendentElem);
		}
	}
	return globalListOfSsmlStrs;
}

function encodeAllDataSsmlAttribs(technique_) {
	if(technique_ === 'index') {
		encodeAllDataSsmlAttribs_indexTechnique();
	} else if(technique_ === 'inline') {
		encodeAllDataSsmlAttribs_inlineTechnique();
	} else if(technique_ === 'page-wide-override') {
		encodeAllDataSsmlAttribs_pageWideOverrideTechnique();
	} else {
		throw new Error();
	}
}

})();
