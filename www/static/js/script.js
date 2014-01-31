function submitSearchForm() {
	//validating number fields
	var valid = true;
	numbers = $('input[type="number"]').get();
	for (index in numbers) {
		number = numbers[index]
		if (number.value.length == 0) {
			continue;
		}

		var regexp = new RegExp(email.pattern)
		parsed = parseInt(number.value)
		if (isNaN(parsed) || (parsed < number.min) || (parsed > number.max)) {
			return;
		}
	}

	search = $('#search input, #search select').filter(function(index) {
		return (this.value.length != 0);
	}).map(function(index) {
		return (this.name + '=' + this.value);
	}).get().join("&");

	if (search.length != 0) {
		document.location = '/bib/index.html?' + search;
	}
}

function sendReportForm() {
	//validating message field
	textareas = $('#reportForm textarea, #reportForm input[type="text"]').get();
	for (index in textareas) {
		textarea = textareas[index];
		if (textarea.value.length == 0) {
			return;
		}
	}

	emails = $('#reportForm input[type="email"]').get();
	for (index in emails) {
		email = emails[index];
		var regexp = new RegExp(email.pattern)
		if ((email.value.length == 0) || (regexp.exec(email.value) == null)) {
			return;
		}
	}

	this.disabled = 'disabled'
	data = $('#reportForm textarea, #reportForm input').filter(function(index) {
		return (this.value.length != 0);
	}).map(function(index) {
		return (this.name + '=' + this.value);
	}).get().join("&");

	$.post(
		window.location,
		data,
		function(data, textStatus, jqXHR) {
			if (data['result'] != 'OK') {
				alert(data['message']);
			} else {
				html = '<h2>' + data['message'] + '</h2>';
				$('#reportForm').fadeToggle();
				$('#bugReport').fadeToggle();
				$('#reportForm').after(html);
			}
		}
	)
}

function clearSearchForm() {
	$('#search input').val('');
	$('#search select').val('');
}
	
function toggleReportForm() {
	$('#reportForm').slideToggle();
}

function extractFromLocation(key) {
	var regexp = new RegExp('[&\\?]' + key + '=([\^&]*)');
	match = regexp.exec(window.location.search);
	if (match != null) {
		return decodeURIComponent(match[1] || "").replace("+", " ");
	} else {
		return null;
	}
}

function setInputFromLocation() {
	value = extractFromLocation(this.name);
	if (value != null) {
		this.value = value;
	}
}

function loadSearchParams() {
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

	$.get('/bib/keywords',
		function(data, textStatus, jXHR) {
		}
	)
	
	$('#search input').map(setInputFromLocation);
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
