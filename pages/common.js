
function addTestCasesToTable(testCases_, table_, tableHasWithoutSsmlColumn_) {
	let tbody = table_.querySelector('tbody');
	for(let testCase of testCases_) {
		let tr = document.createElement('tr');
		tr.innerHTML = `
			<td>${testCase.html}</td>
			<td>${testCase.expected}</td>
		`;
		let tdHtmlWithSsml = tr.querySelector('td');
		if(tableHasWithoutSsmlColumn_) {
			let tdHtmlWithoutSsml = tdHtmlWithSsml.cloneNode(true);
			if(tdHtmlWithoutSsml.querySelector('[id]')) {
				tdHtmlWithoutSsml.innerHTML = `<strong>ERROR: test case html has an id attribute, so we can't clone it.  If you need to use an id attribute, put it in the "expected" column.</strong>`;
			} else {
				for(let e of tdHtmlWithoutSsml.querySelectorAll('[data-ssml]')) {
					e.removeAttribute('data-ssml');
				}
			}
			tdHtmlWithSsml.insertAdjacentElement('beforebegin', tdHtmlWithoutSsml);
		}
		tbody.appendChild(tr);
	}
}

