
function go() {
	encodeAllDataSsmlAttribs();
}

function encodeSsmlAsZeroWidthCharsBinary(str_) {
    let encoder = new TextEncoder();
    let utf8Bytes = encoder.encode(str_);
    let result = '';

    for (let byte of utf8Bytes) {
        for (let i = 7; i >= 0; i--) {
            let bit = (byte >> i) & 1;
            result += bit === 0 ? '\u200C' : '\u200D';
        }
    }

    return result;
}

function isPowerOfTwo(n_) {
	return (n_ & (n_ - 1)) !== 0;
}

function encodeSsmlAsZeroWidthChars(str_) {
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
		console.log(`data-ssml encoding: ${JSON.stringify({str_, 'baseNDigits.length': baseNDigits.length, baseNDigits})}`);
		console.log(`resultReadable: "${resultReadable}"`);
	}

    return result;
}


function encodeDataSsmlAsBase64(str_) {
    let encoder = new TextEncoder();
    let utf8Bytes = encoder.encode(str_);
    let binaryString = '';
    for (let byte of utf8Bytes) {
        binaryString += String.fromCharCode(byte);
    }
    let base64String = btoa(binaryString);
    return base64String;
}

function encodeAllDataSsmlAttribs() {
	let elements = [...document.querySelectorAll('[data-ssml]')]
		.filter(el => el.getAttribute('data-ssml')?.trim() !== '');
	for(let elem of elements) {
		let dataSsmlValue = elem.getAttribute('data-ssml');
		if(!dataSsmlValue) continue;
		let encodedSsml = encodeSsmlAsZeroWidthChars(dataSsmlValue);
		const START_END_MARKER = '\u2062';
		elem.insertBefore(document.createTextNode(START_END_MARKER+encodedSsml+START_END_MARKER), elem.firstChild);
		const MACRO_END_MARKER = START_END_MARKER+START_END_MARKER;
		elem.appendChild(document.createTextNode(MACRO_END_MARKER));
		for(let descendentElem of [...elem.querySelectorAll('[data-ssml]')]) {
			console.warn(`Found data-ssml in a descendent of an element that has a data-ssml attribute.  We will ignore this one (the descendent.)`, descendentElem);
		}
	}
}

window.addEventListener("load", function(event) {
	go();
});
