/* Progressive selection feedback for the catalogue and the notebook quick search.
   The native GET forms remain the source of truth: this only keeps the visible count and the
   checked row styling in step while the reader is choosing. No network, storage or inline code. */
(function () {
  "use strict";

  function selectedCount(form) {
    var values = new Set();
    var fields = form.elements;
    for (var index = 0; index < fields.length; index += 1) {
      var field = fields[index];
      if (field.name !== "s") {
        continue;
      }
      if (field.type === "checkbox" && !field.checked) {
        continue;
      }
      values.add(field.value);
    }
    return values.size;
  }

  function countText(count) {
    return count === 1 ? "1 selecionada" : count + " selecionadas";
  }

  function sync(form) {
    var count = selectedCount(form);
    var targets = form.querySelectorAll("[data-selection-count-text]");
    for (var index = 0; index < targets.length; index += 1) {
      targets[index].textContent = countText(count);
    }
    var boxes = form.querySelectorAll('input[type="checkbox"][name="s"]');
    for (var boxIndex = 0; boxIndex < boxes.length; boxIndex += 1) {
      var row = boxes[boxIndex].closest("[data-selection-row]");
      if (row) {
        row.classList.toggle("is-selected", boxes[boxIndex].checked);
      }
    }
  }

  function init(form) {
    sync(form);
    form.addEventListener("change", function (event) {
      if (event.target && event.target.name === "s") {
        sync(form);
      }
    });
  }

  var forms = document.querySelectorAll("form");
  for (var index = 0; index < forms.length; index += 1) {
    var form = forms[index];
    if (form.querySelector("[data-selection-count-text]")) {
      init(form);
    }
  }
})();
