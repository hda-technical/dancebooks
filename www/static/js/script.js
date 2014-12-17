var bib = {
	VERSION: "{{ config.version }}",
	BASKET_EXPIRE: 7 * 24, /* 7 days */

	SearchType: {
		Undefined: -1,
		Basic: 0,
		Advanced: 1,
		AllFields: 2
	},

	SEARCH_PATHS: [
		'/bib/basic-search',
		'/bib/advanced-search',
		'/bib/all-fields-search'
	],
};

bib.utils = function() {
	//privates
	//publics
	return {
		init: function() {
		},

		hide: function(item) {
			item.addClass('hidden');
		},

		show: function(item) {
			item.removeClass('hidden')
		},

		activateAction: function(item) {
			item.addClass('action');
		},

		deactivateAction: function(item) {
			item.removeClass('action');
		},

		/*
		 * Extracts key from location
		 * @param key: key to extract
		 */
		extractFromLocation: function(key) {
			var regexp = new RegExp('[&\\?]' + key + '=([^&]*)');
			var match = regexp.exec(window.location.search);
			if ((match != null) && (match[1] != null)) {
				return decodeURIComponent(match[1].replace("+", " "));
			} else {
				return '';
			}
		},

		/*
		 * Creates text element of type elem,
		 *   adds specified text content,
		 *   and sets given attrs (of text->text mapping type)
		 */
		makeTextElement: function(elem, content, attrs) {
			var element = document.createElement(elem);
			$(element).html(content);
			for (attr in attrs) {
				value = attrs[attr];
				$(element).attr(attr, value);
			}
			return element;
		},

		trim: function(str) {
			return str.trim();
		},

		/*
		 * Expects 'this' as the current DOM element
		 */
		isValid: function() {
			//javascript guaranties valid element value to be non-empty
			return (this.value.length > 0);
		},

		/*
		 * Expecteds 'this' as the current DOM element
		 */
		isInvalid: function() {
			//javascript guaranties invalid element value to be empty
			//$(this).is(':invalid');
			return false;
		},

		isEmptyOrInvalid: function() {
			return (this.value.length == 0) || bib.utils.isInvalid();
		},

		/*
		 * Makes search string (form post data)
		 */
		makeSearchString: function(attrs) {
			var result = []
			for (key in attrs) {
				result.push(key + "=" + encodeURIComponent(attrs[key]));
			}
			return result.join("&");
		},

		/*
		 * Dumps object to console
		 */
		dumpObject: function(obj) {
			for (key in obj) {
				console.log(key + ': ' + obj[key]);
			};
		},
	};
}();

bib.report = function() {
	//privates
	var reportForm = null;
	var reportFormToggle = null;
	var reportFormSubmitter = null;
	var reportInputs = null;

	var keywordForm = null;
	var keywordFormToggle = null;
	var keywordFormSubmitter = null;
	var keywordInputs = null;

	var sendReportForm = function() {
		var invalids = reportInputs.filter(bib.utils.isEmptyOrInvalid);
		if (invalids.length > 0) {
			return;
		}
		reportFormSubmitter.attr("disabled", "disabled");
		var data = {};
		reportInputs.filter(bib.utils.isValid)
			.map(function(index) {
				data[this.name] = this.value;
			});

		bib.server.postBugReport(
			data,
			//to be called on success
			function(data) {
				$('#submitMessage').remove();
				var message = bib.utils.makeTextElement(
					"h2",
					data['message'],
					{
						id: "submitMessage"
					}
				);
				reportFormToggle.fadeToggle();
				keywordFormToggle.fadeToggle();
				reportForm.fadeToggle();
				reportForm.after(message);
			},
			//to be called in case of fail
			function(data) {
				reportFormSubmitter.removeAttr("disabled");
				$('#submitMessage').remove();
				var message = bib.utils.makeTextElement(
					"h2",
					data["message"],
					{
						id: "submitMessage",
						style: "color: #ff0000;"
					}
				);
				reportForm.after(message);
			}
		)
	}

	var sendKeywordForm = function() {
		var invalids = keywordInputs.filter(bib.utils.isEmptyOrInvalid);
		if (invalids.length > 0) {
			return;
		}
		keywordFormSubmitter.attr("disabled", "disabled");
		var data = {};
		keywordInputs.filter(bib.utils.isValid)
			.map(function(index) {
				data[this.name] = this.value;
			});
		bib.utils.dumpObject(data);
		bib.server.postKeywordReport(
			data,
			//to be called on success
			function(data) {
				$('#submitMessage').remove();
				var message = bib.utils.makeTextElement(
					"h2",
					data['message'],
					{
						id: "submitMessage"
					}
				);
				reportFormToggle.fadeToggle();
				keywordFormToggle.fadeToggle();
				keywordForm.fadeToggle();
				keywordForm.after(message);
			},
			//to be called in case of fail
			function(data) {
				keywordFormSubmitter.removeAttr("disabled");
				$('#submitMessage').remove();
				var message = bib.utils.makeTextElement(
					"h2",
					data["message"],
					{
						id: "submitMessage",
						style: "color: #ff0000;"
					}
				);
				keywordForm.after(message);
			}
		)
	}

	//publics
	return {
		init: function() {
			reportForm = $('#reportForm');
			reportFormToggle = $('#reportFormToggle');
			reportInputs = reportForm.find("textarea, input");

			keywordForm = $('#keywordForm');
			keywordFormToggle = $('#keywordFormToggle');
			keywordInputs = keywordForm.find("textarea, input");

			reportFormToggle.click(function() {
				keywordForm.hide();
				reportForm.slideToggle();
			});

			keywordFormToggle.click(function() {
				reportForm.hide();
				keywordForm.slideToggle();
			});

			reportFormSubmitter = $("#reportFormSubmitter");
			reportFormSubmitter.click(sendReportForm);

			keywordFormSubmitter = $('#keywordFormSubmitter');
			keywordFormSubmitter.click(sendKeywordForm);

			var reportInput = $('#reportForm input');
			reportInput.keyup(function(event) {
				if (event.keyCode == 0x0D) {
					sendReportForm();
				}
			});
		},
	};
}();

bib.search = function() {
	//privates
	var searchType = bib.SearchType.Basic;

	var searchButton = null;

	var searchFormBasic = null;
	var searchFormAdvanced = null;
	var searchFormAllFields = null;

	var searchToggeBasic = null;
	var searchToggleAdvanced = null;
	var searchToggleAllFields = null;
	var searchToggles = null;

	var inputs = null;
	var keywordsChooser = null;
	var keywordsButtons = null;
	var keywordsInput = null;

	/*
	 * Clears searchForm by
	 *   setting input and select values to empty string,
	 *   unchecking all checkboxes
	 * @param form: jQuery collection of forms to be cleared
	 */
	var clearForm = function(form) {
		form.find('input').val('');
		form.find('select').val('');
		form.find('input[type="checkbox"]').prop('checked', false);
	};

	/*
	 * Fills input (passed as this) from window.location
	 * Intended to be passed to jQuery.map
	 */
	var fillFromLocation = function() {
		this.value = bib.utils.extractFromLocation(this.name);
	};

	var switchToBasicSearch = function() {
		searchType = bib.SearchType.Basic;
		switchSearchForms();
	};

	var switchToAdvancedSearch = function() {
		searchType = bib.SearchType.Advanced;
		switchSearchForms();
	};

	var switchToAllFieldsSearch = function() {
		searchType = bib.SearchType.AllFields;
		switchSearchForms();
	};

	/*
	 * Switches between search forms, clears unused data
	 */
	var switchSearchForms = function() {
		var toClear = null;
		var toHide = null;
		var toShow = null;
		var toActivate = null;
		var toDeactivate = null;

		if (searchType == bib.SearchType.Undefined) {
			return;
		} else if (searchType == bib.SearchType.Basic) {
			toShow = [searchFormBasic]
			toHide = [searchFormAdvanced, searchFormAllFields];
			toActivate = [searchToggleAdvanced, searchToggleAllFields];
			toDeactivate = [searchToggleBasic];

			searchToggleBasic.off('click');
			searchToggleAdvanced.click(switchToAdvancedSearch);
			searchToggleAllFields.click(switchToAllFieldsSearch);
		} else if (searchType == bib.SearchType.Advanced) {
			//don't clear basic search form
			toShow = [searchFormBasic, searchFormAdvanced];
			toHide = [searchFormAllFields];
			toActivate = [searchToggleBasic, searchToggleAllFields];
			toDeactivate = [searchToggleAdvanced];

			searchToggleAdvanced.off('click');
			searchToggleBasic.click(switchToBasicSearch);
			searchToggleAllFields.click(switchToAllFieldsSearch);
		} else if (searchType == bib.SearchType.AllFields) {
			toShow = [searchFormAllFields];
			toHide = [searchFormBasic, searchFormAdvanced];
			toActivate = [searchToggleBasic, searchToggleAdvanced];
			toDeactivate = [searchToggleAllFields];

			searchToggleAllFields.off('click');
			searchToggleBasic.click(switchToBasicSearch);
			searchToggleAdvanced.click(switchToAdvancedSearch);
		}

		toHide.forEach(clearForm);
		toHide.forEach(bib.utils.hide);
		toShow.forEach(bib.utils.show);
		toActivate.forEach(bib.utils.activateAction);
		toDeactivate.forEach(bib.utils.deactivateAction);
	};

	var fillLanguages = function(languages) {
		//setting languages select options
		var selectedLanguage = bib.utils.extractFromLocation("langid");
		var options = []
		for (index in languages) {
			var languageKey = languages[index][0];
			var languageValue = languages[index][1];
			var attrs = {
				"value": languageKey
			}
			if (languageKey == selectedLanguage) {
				attrs["selected"] = "selected";
			}
			var option = bib.utils.makeTextElement(
				"option",
				languageValue,
				attrs
			)
			options.push(option);
		}
		$('#langid option[value=""]').after(options);
		$('#langid option[value="empty"]').remove();
	};

	var fillSourceFiles = function(sourceFiles) {
			var selectedFile = bib.utils.extractFromLocation("source_file");
			var options = [];
			for (index in sourceFiles) {
				var sourceFile = sourceFiles[index];
				var attrs = {
					"value": sourceFile
				};
				if (sourceFile == selectedFile) {
					attrs["selected"] = "selected";
				}
				var option = bib.utils.makeTextElement(
					"option",
					sourceFile,
					attrs
				)
				options.push(option);
			}
			$('#source_file option[value=""]').after(options);
			$('#source_file option[value="empty"]').remove();

	};

	var updateKeywords = function() {
		var foundKeywords = keywordsButtons.find('input[type="checkbox"]:checked')
			.map(function() {
				return this.value
			}).get();
		var uniqueKeywords = new Set(foundKeywords);
		keywordsInput.val([...uniqueKeywords].join(', '));
	};

	var fillKeywords = function(keywords) {
		//setting keywords select options
		var selectedKeywords = bib.utils.extractFromLocation("keywords").split(",").map(bib.utils.trim)
		//server will respond with the following data:
		/*
		[
			category : {
				"translation": header,
				"keywords": [keywords]
			}
		]
		*/
		var elems = [];
		for (catIndex in keywords) {
			var catTranslation = keywords[catIndex]["translation"]
			var catKeywords = keywords[catIndex]["keywords"]

			var headerAttrs = {
				"class": "bold center"
			};
			var header = bib.utils.makeTextElement(
				"div",
				catTranslation,
				headerAttrs
			);
			elems.push(header);

			for (index in catKeywords) {
				var keyword = catKeywords[index]
				var id = 'keyword-' + catIndex + '-' + index;

				var inputAttrs = {
					"id": id,
					"value": keyword,
					"type": "checkbox",
				};
				if (selectedKeywords.indexOf(keyword) != -1) {
					inputAttrs["checked"] = "checked";
				}

				var input = bib.utils.makeTextElement(
					"input",
					"",
					inputAttrs
				);
				$(input).change(updateKeywords);
				elems.push(input);

				var labelAttrs = {
					"for": id
				};
				var label = bib.utils.makeTextElement(
					"label",
					keyword,
					labelAttrs
				);
				elems.push(label);
			}
		}

		$('#keywordsButtons').html(elems);
		updateKeywords();
	};

	var fillSearchForm = function(data) {
		fillLanguages(data["languages"]);
		fillSourceFiles(data["source_files"]);
		fillKeywords(data['keywords']);
	};

	var submitSearch = function() {
		var invalids = inputs.filter(bib.utils.isInvalid);
		if (invalids.length > 0) {
			return;
		}

		searchButton.attr("disabled", "disabled");
		var data = {};
		search = inputs.filter(bib.utils.isValid)
			.map(function() {
				data[this.name] = this.value;
			});
		if (Object.keys(data).length > 0) {
			bib.server.submitSearch(searchType, data);
		}
		searchButton.removeAttr("disabled");
	};

	//publics
	return {
		init: function() {
			searchFormBasic = $('#searchFormBasic');
			searchFormAdvanced = $('#searchFormAdvanced');
			searchFormAllFields = $('#searchFormAllFields');

			searchToggleBasic = $('#searchToggleBasic');
			searchToggleAdvanced = $('#searchToggleAdvanced');
			searchToggleAllFields = $('#searchToggleAllFields');

			keywordsInput = $('#keywords');
			keywordsChooser = $('#keywordsChooser');
			keywordsButtons = $('#keywordsButtons');

			//setting event handlers
			$('#clearSearch').click(function() {
				clearForm(searchFormBasic);
				clearForm(searchFormAdvanced);
				clearForm(searchFormAllFields);
			});

			searchButton = $('#submitSearch');
			searchButton.click(submitSearch);

			keywordsInput.focus(function() {
				keywordsChooser.slideDown();
			});

			$('#keywordsHider').click(function() {
				keywordsChooser.slideUp();
			});

			searchToggleAdvanced.click(switchToAdvancedSearch);
			searchToggleAllFields.click(switchToAllFieldsSearch);

			inputs = $(
				'#search input[type!="checkbox"], ' +
				'#search select, ' +
				'#url, ' +
				'#origlanguage'
			);
			inputs.keyup(function(event) {
				if (event.keyCode == 0x0D) {
					submitSearch();
				}
			});

			bib.server.getOptions(fillSearchForm);

			$(
				'#search input[name!="keywords"], ' +
				'#url, ' +
				'#origlanguage'
			).map(fillFromLocation);

			searchType = bib.SEARCH_PATHS.indexOf(window.location.pathname);
			if (searchType == -1) {
				searchType = bib.SearchType.Basic;
			}
			switchSearchForms()
		},

	};
}();

bib.server = function() {
	//privates

	//publics
	return {
		init: function() {
		},

		getOptions: function(callback) {
			$.get('/bib/options', function(data, textStatus, jqXHR) {
				callback(data);
			});
		},

		/*
		 * Expects data as a mapping object
		 */
		postBugReport: function(data, successCallback, failCallback) {
			$.post(
				window.location,
				bib.utils.makeSearchString(data),
				function(data, textStatus, jqXHR) {
					successCallback(data)
				}
			).fail(
				function(jqXHR) {
					failCallback(jqXHR.responseJSON)
				}
			)
		},

		postKeywordReport: function(data, successCallback, failCallback) {
			$.post(
				window.location + '/keywords',
				bib.utils.makeSearchString(data),
				function(data, textStatus, jqXHR) {
					successCallback(data)
				}
			).fail(
				function(jqXHR) {
					failCallback(jqXHR.responseJSON)
				}
			)
		},

		/*
		 * Expects data as a mapping object
		 */
		submitSearch: function(searchType, data) {
			var newLocation =
				bib.SEARCH_PATHS[searchType] +
				"?" +
				bib.utils.makeSearchString(data);
			document.location = newLocation;



		}
	};
}();

