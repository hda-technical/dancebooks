var SearchType = {
	Basic: 0,
	Advanced: 1,
	Fulltext: 2
};

var env = {
	searchToggleBasic: null,
	searchToggleAdvanced: null,
	serachToggleFulltext: null,

	searchFormBasic: null,
	searchFormAdvanced: null,
	searchFormFulltext: null,

	searchType: SearchType.Basic,

	searchTypeToPath: [
		'/bib/basic-search',
		'/bib/advanced-search',
		'/bib/fulltext-search'
	]
};

function submitSearchForm() {
	this.disabled = 'disabled'
	search = $('#search input[type!="checkbox"], #search select').filter(function(index) {
		return (
			(this.value.length != 0) ||
			($(this).is(':invalid'))
		);
	}).map(function(index) {
		return (this.name + '=' + encodeURIComponent(this.value));
	}).get().join("&");

	if (search.length != 0) {
		searchPath = env.searchTypeToPath[env.searchType];
		document.location = searchPath + '?' + search;
	}
}

function sendReportForm() {
	this.disabled = 'disabled'
	data = $('#reportForm textarea, #reportForm input').filter(function(index) {
		return (
			(this.value.length != 0) ||
			($(this).is(':invalid'))
		);
	}).map(function(index) {
		return (this.name + '=' + this.value);
	}).get().join("&");

	$.post(
		window.location,
		data,
		function(data, textStatus, jqXHR) {
			$('#submitMessage').remove()
			html = '<h2 id="submitMessage">' + data['message'] + '</h2>';
			$('#reportForm').fadeToggle();
			$('#bugReport').fadeToggle();
			$('#reportForm').after(html);
		}
	).fail(function(jqXHR) {
		$('#submitMessage').remove()
		html = '<h2 id="submitMessage" style="color: #ff0000;">' + jqXHR.responseJSON['message'] + '</h2>';
		$('#reportForm').after(html);
	})
}

function toggleReportForm() {
	$('#reportForm').slideToggle();
}

function showKeywordsChooser() {
	$('#keywordsChooser').slideDown();
}

function hideKeywordsChooser() {
	$('#keywordsChooser').slideUp();
	return false;
}

function extractFromLocation(key) {
	var regexp = new RegExp('[&\\?]' + key + '=([\^&]*)');
	match = regexp.exec(window.location.search);
	if (match != null) {
		return decodeURIComponent(match[1] || "");
	} else {
		return '';
	}
}

function setInputFromLocation() {
	value = extractFromLocation(this.name);
		this.value = value;
}

function updateKeywords() {
	keywords = $('#keywordsChooser input[type="checkbox"]:checked + label').map(function(index) {
		return $(this).html();
	}).get().join(", ");
	$('input[name="keywords"]').val(keywords);
}

function trim(str) {
	return str.trim();
}

function loadSearchParams() {
	$.get('/bib/options',
		function(data, textStatus, jqXHR) {
			languages = data['languages']
			keywords = data['keywords']
			source_files = data['source_files']

			//setting languages select options
			selectedLanguage = extractFromLocation("langid");
			html = '';
			for (index in languages) {
				languageKey = languages[index][0]
				languageValue = languages[index][1]

				if (languageKey == selectedLanguage) {
					html += '<option value="' + languageKey + '" selected="selected">' + languageValue + '</option>';
				} else {
					html += '<option value="' + languageKey + '">' + languageValue + '</option>';
				}
			}
			$('#langid option[value=""]').after(html);
			$('#langid option[value="empty"]').remove();

			//setting source file select options
			selectedFile = extractFromLocation("source_file");
			html = '';
			for (index in source_files) {
				sourceFile = source_files[index];
				if (sourceFile == selectedFile) {
					html += '<option value="' + sourceFile + '" selected="selected">' + sourceFile + '</option>';
				} else {
					html += '<option value="' + sourceFile + '">' + sourceFile + '</option>';
				}
			}
			$('#source_file option[value=""]').after(html);
			$('#source_file option[value="empty"]').remove();

			//setting keywords select options
			selectedKeywords = extractFromLocation("keywords").split(",").map(trim)
			html = '';
			for (index in keywords) {
				id = 'keyword' + index;
				keyword = keywords[index];
				//goddamn javascript doesn't have sets
				if (selectedKeywords.indexOf(keyword) != -1) {
					html += '<input id="' + id + '" type="checkbox" checked="checked" onchange="updateKeywords()"/>';
				} else {
					html += '<input id="' + id + '" type="checkbox" onchange="updateKeywords()"/>';
				}
				html += '<label for="' + id + '">' + keyword + '</label>';
			}
			$('#keywordsChooser #keywordsHider').after(html);

			updateKeywords();
		}
	)

	$(
		'#search input[name!="keywords"], ' +
		'#url, ' +
		'#origlanguage'
	).map(setInputFromLocation);
}

$(document).ready(function() {
	env.searchToggleBasic = $('#searchToggleBasic');
	env.searchToggleAdvanced = $('#searchToggleAdvanced');
	env.searchToggleFulltext = $('#searchToggleFulltext');

	env.searchFormBasic = $('#searchFormBasic');
	env.searchFormAdvanced = $('#searchFormAdvanced');
	env.searchFormFulltext = $('#searchFormFulltext');

	loadSearchParams();
	$('#search input, #search select').on('keyup', function(event) {
		if (event.keyCode == 0x0D) {
			submitSearchForm();
		}
	});

	$('#reportForm input').on('keyup', function(event) {
		if (event.keyCode == 0x0D) {
			sendReportForm();
		}
	});

	if (window.location.pathname == '/bib/advanced-search') {
		env.searchType = SearchType.Advanced;
	} else if (window.location.pathname == '/bib/fulltext-search') {
		env.searchType = SearchType.Fulltext;
	}
	switchSearchForms(true)

})

function clearSearchForm(form) {
	form.children('input').val('');
	form.children('select').val('');
	form.children('input[type="checkbox"]').prop('checked', false);
}

function clearSearchForms() {
	clearSearchForm(env.searchFormBasic);
	clearSearchForm(env.searchFormAdvanced);
	clearSearchForm(env.searchFormFulltext);
}

function switchToBasicSearch() {
	env.searchType = SearchType.Basic;
	switchSearchForms(false);
}

function switchToAdvancedSearch() {
	env.searchType = SearchType.Advanced;
	switchSearchForms(false);
}

function switchToFulltextSearch() {
	env.searchType = SearchType.Fulltext;
	switchSearchForms(false);
}

function switchSearchForms(initial) {

	if (env.searchType == SearchType.Basic) {
		clearSearchForm(env.searchFormAdvanced);
		clearSearchForm(env.searchFormFulltext);

		env.searchFormBasic.removeClass('hidden');
		env.searchFormAdvanced.addClass('hidden');
		env.searchFormFulltext.addClass('hidden');

		env.searchToggleBasic.removeClass("action");
		env.searchToggleAdvanced.addClass("action");
		env.searchToggleFulltext.addClass("action");

		env.searchToggleBasic.off('click');
		env.searchToggleAdvanced.on('click', switchToAdvancedSearch);
		env.searchToggleFulltext.on('click', switchToFulltextSearch);
	} else if (env.searchType == SearchType.Advanced) {
		//don't clear basic search form
		clearSearchForm(env.searchFormFulltext);

		env.searchFormBasic.removeClass('hidden');
		env.searchFormAdvanced.removeClass('hidden');
		env.searchFormFulltext.addClass('hidden');

		env.searchToggleBasic.addClass("action");
		env.searchToggleAdvanced.removeClass("action");
		env.searchToggleFulltext.addClass("action");

		env.searchToggleBasic.on('click', switchToBasicSearch);
		env.searchToggleAdvanced.off('click');
		env.searchToggleFulltext.on('click', switchToFulltextSearch);
	} else if (env.searchType == SearchType.Fulltext) {
		clearSearchForm(env.searchFormBasic);
		clearSearchForm(env.searchFormAdvanced);

		env.searchFormBasic.addClass('hidden');
		env.searchFormAdvanced.addClass('hidden');
		env.searchFormFulltext.removeClass('hidden');

		env.searchToggleBasic.addClass("action");
		env.searchToggleAdvanced.addClass("action");
		env.searchToggleFulltext.removeClass("action");

		env.searchToggleBasic.on('click', switchToBasicSearch);
		env.searchToggleAdvanced.on('click', switchToAdvancedSearch);
		env.searchToggleFulltext.off('click');
	}
}
