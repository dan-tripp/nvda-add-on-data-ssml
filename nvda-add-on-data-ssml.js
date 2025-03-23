
function go() {
	turnDataSsmlIntoZeroWidthChars();
}

function encodeDataSsmlAsZeroWidthCharsStr(str_) {
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

function turnDataSsmlIntoZeroWidthChars() {
	for(let elem of document.querySelectorAll('[data-ssml]')) {
		let dataSsmlValue = elem.getAttribute('data-ssml');
		if(!dataSsmlValue) continue;
		let dataSsmlValueEncoded = encodeDataSsmlAsBase64(dataSsmlValue);
		const START_MARKER = '[ssml-start]', END_MARKER = '[ssml-end]';
		elem.insertBefore(document.createTextNode(START_MARKER+dataSsmlValueEncoded.repeat(100)+END_MARKER), elem.firstChild);
		// 												^^ tdr 
		elem.appendChild(document.createTextNode(START_MARKER+END_MARKER));
	}
}

window.addEventListener("load", function(event) {
	go();
});
