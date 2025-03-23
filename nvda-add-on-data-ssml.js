
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

function encodeSsmlAsZeroWidthCharsOctal(str_) {
    let encoder = new TextEncoder();
    let utf8Bytes = encoder.encode(str_);
    let bigInt = BigInt(0);

    // Convert all bytes into one big integer
    for (let byte of utf8Bytes) {
        bigInt = (bigInt << BigInt(8)) + BigInt(byte);
    }

    // Convert bigInt to base-8 (octal)
    let base8Digits = [];
    if (bigInt === BigInt(0)) {
        base8Digits.push(0);
    } else {
        while (bigInt > 0) {
            base8Digits.push(Number(bigInt % BigInt(8)));
            bigInt = bigInt / BigInt(8);
        }
    }
    base8Digits.reverse();

    let dict = [
        '\u180E', // 0
        '\u200C', // 1
        '\u200D', // 2
        '\u2060', // 3
        '\u2061', // 4
        '\uFEFF', // 5
        '\u202C', // 6
        '\u202D'  // 7
    ];

	dict = Array(8).fill('\u200D'); // tdr 
	/* 
	u180E bad
	u200C good 
	u200D good
	*/

    let result = '';
    for (let digit of base8Digits) {
        result += dict[digit];
    }

	if(true) { // tdr 
		result = '\u200C\u200D\u2060\u2061\uFEFF\u202C\u202D'.repeat(9999);
		result = result.substring(0, 90);
		/*
		all at len 70: bad 
		all but first at len 70: good 
		all but first at len 90: good
		all but first at len 110: bad 
		all but first at len 100: bad
		 */
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
	for(let elem of document.querySelectorAll('[data-ssml]')) {
		let dataSsmlValue = elem.getAttribute('data-ssml');
		if(!dataSsmlValue) continue;
		const USE_BASE64 = false;
		if(USE_BASE64) {
			let dataSsmlValueEncoded = encodeDataSsmlAsBase64(dataSsmlValue);
			const START_MARKER = '[ssml-start]', END_MARKER = '[ssml-end]';
			elem.insertBefore(document.createTextNode(START_MARKER+dataSsmlValueEncoded+END_MARKER), elem.firstChild);
			elem.appendChild(document.createTextNode(START_MARKER+END_MARKER))
		} else {
			let zeroWidthCharsStr = encodeSsmlAsZeroWidthCharsOctal(dataSsmlValue);
			const START_MARKER = '\u2062\u2063', END_MARKER = '\u2063\u2062';
			elem.insertBefore(document.createTextNode(START_MARKER+zeroWidthCharsStr+END_MARKER), elem.firstChild);
			elem.appendChild(document.createTextNode(START_MARKER+END_MARKER));
		}
	}
}

window.addEventListener("load", function(event) {
	go();
});
