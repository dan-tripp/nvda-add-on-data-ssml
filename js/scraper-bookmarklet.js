
/* 
- This code is largely untested.  specifically the iframe parts.  
- As for dynamic DOM updates: this code doesn't catch a data-ssml attribute appearing on an existing element.  Only catches a new element appearing which has data-ssml. 
*/

(() => {

let g_ssmlStrs = new Set();

function handleDocument(doc_) {

	function gatherDataSsmlFromDescendents(root) {
		let elements = root.querySelectorAll('[data-ssml]');
		for (let el of elements) {
			addDataSsmlElementToOurCollection(el);
		}
	}

	function addDataSsmlElementToOurCollection(element_) {
		let ssmlStr = element_.getAttribute('data-ssml');
		g_ssmlStrs.add(ssmlStr);
		//if(ssmlStr.includes('break')) {
			console.error(ssmlStr, element_);
		//}
	}

	function logOurDataSsmlCollection() {
		let date = new Date();
		let str = `${date} start\n`;
		for(let ssmlStr of [...g_ssmlStrs].sort()) {
			str += ssmlStr + '\n';
		}
		str += `${date} end\n`;
		console.warn(str);
	}

	gatherDataSsmlFromDescendents(doc_);
	logOurDataSsmlCollection();

	let observer = new doc_.defaultView.MutationObserver(mutations => {
		for (let mutation of mutations) {
			for (let node of mutation.addedNodes) {
				if (node.nodeType === 1) {
					if (node.hasAttribute('data-ssml')) {
						addDataSsmlElementToOurCollection(el);
					}
					gatherDataSsmlFromDescendents(node);
				}
			}
		}
		logOurDataSsmlCollection();
	});

	observer.observe(doc_, { childList: true, subtree: true });
}

function tryHandleFrame(frame) {
	try {
		if (frame.contentDocument) {
			handleDocument(frame.contentDocument);
		}
	} catch (e) {
		console.warn('Cannot access iframe due to cross-origin restrictions:', frame);
	}
}

handleDocument(document);

let iframes = document.querySelectorAll('iframe');
for (let iframe of iframes) {
	tryHandleFrame(iframe);
}

let frameObserver = new MutationObserver(mutations => {
	for (let mutation of mutations) {
		for (let node of mutation.addedNodes) {
			if (node.nodeName === 'IFRAME') {
				tryHandleFrame(node);
			}
		}
	}
});

frameObserver.observe(document, { childList: true, subtree: true });

})();
