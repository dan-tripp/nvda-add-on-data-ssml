
function init() {
	turnDataSsmlIntoAriaDescriptions();
}

function turnDataSsmlIntoAriaDescriptions() {
	for(let elem of document.querySelectorAll('[data-ssml]')) {
		let dataSsmlValue = elem.getAttribute('data-ssml');
		if(!dataSsmlValue) continue;
		
	}
}

init();
