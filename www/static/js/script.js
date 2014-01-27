function submitSearchForm() {
	$('#search').submit();
}

function clearSearchForm() {
	$('#search input').val('');
	$('#search select').val('');
}

function extractFromLocation(key) {
	var regexp = new RegExp('[&\\?]' + key + '=([\^&]*)');
	match = regexp.exec(window.location.search);
	if (match != null) {
		return decodeURIComponent(match[1] || "").replace("+", " ");
	} else {
		return null
	}
}

function setInputFromLocation() {
	value = extractFromLocation(this.name);
	if (value != null) {
		this.value = value;
	}
}

function loadSearchParams() {
	$('#search input').map(setInputFromLocation);

	$.get('/bib/langid', 
		function(data, textStatus, jqXHR) {
			selected = extractFromLocation("langid")
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
}

$(document).ready(loadSearchParams)
