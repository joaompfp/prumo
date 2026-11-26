/* Native GET forms own the selection. This local enhancement adds feedback only.
   No network, cookies or second selection store; submitted values are validated by the server. */
(function () {
  "use strict";

  function selectedValues(form) {
    return Array.from(new Set(Array.from(form.elements).filter(function (field) {
      return field.name === "s" && !field.disabled &&
        (field.type !== "checkbox" || field.checked);
    }).map(function (field) { return field.value; })));
  }

  function countText(count) {
    return count === 1 ? "1 selecionada" : count + " selecionadas";
  }

  function init(form) {
    var original = selectedValues(form).sort().join("\n");
    var pending = false;
    function sync() {
      var values = selectedValues(form);
      var count = values.length;
      pending = values.sort().join("\n") !== original;
      form.querySelectorAll("[data-selection-count-text]").forEach(function (target) {
        target.textContent = countText(count);
      });
      form.querySelectorAll("[data-selection-count-number]").forEach(function (target) {
        target.textContent = count;
      });
      form.querySelectorAll('[type="checkbox"][name="s"]').forEach(function (box) {
        var row = box.closest("[data-selection-row]");
        if (row) row.classList.toggle("is-selected", box.checked);
        box.disabled = count >= 12 && !box.checked;
      });
      form.querySelectorAll("[data-selection-pending]").forEach(function (target) {
        target.hidden = !pending;
      });
    }
    form.addEventListener("change", function (event) {
      if (event.target && event.target.name === "s") sync();
    });
    window.addEventListener("pageshow", sync);
    sync();

    // Chart settings operate on the applied notebook, not an unsubmitted selection.
    // Refuse that unrelated submit rather than discarding pending checked/unchecked rows.
    var chartForm = document.getElementById("notebook-chart-form");
    if (chartForm && form.id === "notebook-search-form") {
      chartForm.addEventListener("submit", function (event) {
        if (!pending) return;
        event.preventDefault();
        var apply = form.querySelector('button[name="acao"][value="abrir"]');
        if (apply) apply.focus();
      });
    }
  }

  document.querySelectorAll("form").forEach(function (form) {
    if (form.querySelector("[data-selection-count-text]")) init(form);
  });
})();
