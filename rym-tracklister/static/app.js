const defaultSettings = {
  lang: 'e',
  va: 'n',
  merge: 'n',
  isClass: false,
  toClear: '',
  mvlang: 'e',
  source: 'o'
};

const api = {
  baseUrl: '/api/',
  post: function(endpoint, data, callback) {
    $.post(this.baseUrl + endpoint, data, callback);
  }
};

const am = {
  map: function(arr, callback) {
    let mappedArr = [];
    for (let i = 0; i < arr.length; i++) {
      mappedArr.push(callback(arr[i]));
    }
    return mappedArr;
  },
  reduce: function(arr, callback, initAcc) {
    let acc = initAcc;
    for (let i = 0; i < arr.length; i++) {
      acc = callback(acc, arr[i]);
    }
    return acc;
  },
  forEach(arr, callback) {
    for (let i = 0; i < arr.length; i++) {
      if (callback(arr[i]) === false) break;
    }
  }
};

function getInputSelector(parentSelector) {
  const inputSelectors = [
    'input',
    'select',
    'textarea'
  ];
  return am.map(inputSelectors, function(inputSelector) {
    return parentSelector + ' ' + inputSelector;
  }).join(', ');
}

function setValue(element, value) {
  if ($(element).attr('type') === 'checkbox') {
    $(element).prop('checked', value);
  } else if ($(element).hasClass('split-by-newline')) {
    if ($(element).val() !== '') $(element).val(value.join('/n'));
    else $(element).val('');
  } else {
    $(element).val(value);
  }
}

function setFormData(elements, data) {
  am.forEach(elements, function(element) {
    const name = $(element).attr('name');
    if (name in data) setValue(element, data[name]);
  })
}

function getValue(element) {
  if ($(element).attr('type') === 'checkbox') {
    return $(element).prop('checked');
  } else if ($(element).hasClass('split-by-newline')) {
    return $(element).val() !== '' ? $(element).val().split('\n') : []
  } else {
    return $(element).val();
  }
}

function getFormData(elements) {
  return am.reduce(elements, function(acc, element) {
    const key = $(element).attr('name');

    const value = getValue(element)

    acc[key] = value;

    return acc;
  }, {});
}

$(document).ready(function () {
  const $inputForm = $('#inputForm');
  const inputElements = $(this).find(getInputSelector('.root-section'));
  const optInputElements = $(this).find(getInputSelector('.options-section'));

  setFormData(optInputElements, defaultSettings);

  $inputForm.on('submit', function(e) {
    e.preventDefault();
    let data = getFormData(inputElements);

    data.options = getFormData(optInputElements);

    api.post('write-tracks', data, console.log);
  });
});
