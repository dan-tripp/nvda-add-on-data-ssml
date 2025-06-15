(function () {

window.NvdaAddOnDataSsml = window.NvdaAddOnDataSsml || {};

window.NvdaAddOnDataSsml.init = function(technique_) {
	encodeAllDataSsmlAttribs(technique_);
}

const HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES = '4b9b696c-8fc8-49ca-9bb9-73afc9bd95f7';
const HIDING_PLACE_GUID_FOR_INDEX_TECHNIQUE = 'b4f55cd4-8d9e-40e1-b344-353fe387120f';
const HIDING_PLACE_GUID_FOR_PAGE_WIDE_OVERRIDE_TECHNIQUE = 'c7a998a5-4b7e-4683-8659-f2da4aa96eee';

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

function encodeAllDataSsmlAttribs_inlineTechnique() {
	let elements = [...document.querySelectorAll('[data-ssml]')]
		.filter(el => el.getAttribute('data-ssml')?.trim() !== '');
	for(let elem of elements) {
		let dataSsmlValue = elem.getAttribute('data-ssml');
		if(!dataSsmlValue) continue;
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
	let elements = [...document.querySelectorAll('[data-ssml]')]
		.filter(el => el.getAttribute('data-ssml')?.trim() !== '');
	for(let elem of elements) {
		let curSsmlStr = elem.getAttribute('data-ssml');
		if(!curSsmlStr) continue;
		let indexOfCurSsmlStrInGlobalList = globalListOfSsmlStrs.indexOf(curSsmlStr);
		if(indexOfCurSsmlStrInGlobalList == -1) {
			globalListOfSsmlStrs.push(curSsmlStr);
			indexOfCurSsmlStrInGlobalList = globalListOfSsmlStrs.length-1;
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
