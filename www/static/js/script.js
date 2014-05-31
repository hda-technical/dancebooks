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
		document.location = '/bib/search?' + search;
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

function clearSearchForm() {
	$('#search input').val('');
	$('#search select').val('');
	$('#search input[type="checkbox"]').prop("checked", false);
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
		return decodeURIComponent(match[1] || "").replace("+", " ");
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

function loadSearchParams() {
	$.get('/bib/languages',
		function(data, textStatus, jqXHR) {
			selected = extractFromLocation("langid");
			html = '';
			for (lang in data) {
				if (lang == selected) {
					html += '<option value="' + lang + '" selected="selected">' + data[lang] + '</option>';
				} else {
					html += '<option value="' + lang + '">' + data[lang] + '</option>';
				}
			}
			$('#langid option[value=""]').after(html);
			$('#langid option[value="empty"]').remove();
		}
	)

	$.get('/bib/keywords',
		function(data, textStatus, jXHR) {
			keywords = extractFromLocation("keywords")
			$('input[name="keywords"]').val(keywords);

			keywords = keywords.split(",");
			selected = new Array();

			for (index in keywords) {
				selected.push(keywords[index].trim());
			}
			html = '';
			for (index in data) {
				id = 'keyword' + index;

				html += '<input id="' + id + '" type="checkbox" onchange="updateKeywords()"';

				keyword = data[index];
				//goddamn javascript doesn't have sets
				if (selected.indexOf(keyword) != -1) {
					html += ' checked="checked"';
				}
				html += '/>';
				html += '<label for="' + id + '">' + keyword + '</label>';
			}
			$('#keywordsChooser #keywordsHider').after(html);
		}
	)

	$('#search input[name!="keywords"]').map(setInputFromLocation);
}

$(document).ready(function() {
	loadSearchParams();
	$('#search input, #search select').on("keyup", function(event) {
		if (event.keyCode == 0x0D) {
			submitSearchForm();
		}
	});

	$('#reportForm input').on("keyup", function(event) {
		if (event.keyCode == 0x0D) {
			sendReportForm();
		}
	});
})
