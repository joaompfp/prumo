/* Prumo Admin progressive enhancement.
   Every feature here is optional: the server-rendered forms work with this file blocked. */
(function () {
  "use strict";

  // Block-type disclosure. Server validation remains the authority; irrelevant fields are
  // only hidden, never disabled, so a submit without JavaScript still carries every value.
  var blocks = document.querySelectorAll("[data-block]");
  for (var i = 0; i < blocks.length; i += 1) {
    (function (block) {
      var select = block.querySelector("[data-block-type-select]");
      if (!select) return;
      function sync() {
        block.setAttribute("data-block-type", select.value);
        var groups = block.querySelectorAll("[data-show-for]");
        for (var j = 0; j < groups.length; j += 1) {
          var kinds = (groups[j].getAttribute("data-show-for") || "").split(/\s+/);
          groups[j].hidden = kinds.indexOf(select.value) === -1;
        }
      }
      select.addEventListener("change", sync);
      sync();
    }(blocks[i]));
  }

  // A plain filter over the existing <select>. The select keeps its name, value and every
  // option; non-matching options are only hidden. A short list is left alone.
  var selects = document.querySelectorAll("select[data-filterable]");
  for (var s = 0; s < selects.length; s += 1) {
    (function (select) {
      var options = Array.prototype.slice.call(select.options);
      if (options.length < 12) return;
      var field = select.parentNode;
      var input = document.createElement("input");
      input.type = "search";
      input.className = "select-filter form-control form-control-sm";
      input.autocomplete = "off";
      input.placeholder = select.getAttribute("data-filter-placeholder") || "Filtrar opções";
      input.setAttribute("aria-label", select.getAttribute("data-filter-label") || "Filtrar opções");
      field.insertBefore(input, select);

      function filter() {
        var query = input.value.trim().toLocaleLowerCase();
        var visible = 0;
        for (var o = 0; o < options.length; o += 1) {
          var option = options[o];
          var keep = !query || option.text.toLocaleLowerCase().indexOf(query) !== -1 ||
                     option.value === select.value || option.value === "";
          option.hidden = !keep;
          if (keep && option.value !== "") visible += 1;
        }
        var groups = select.querySelectorAll("optgroup");
        for (var g = 0; g < groups.length; g += 1) {
          var children = groups[g].querySelectorAll("option");
          var any = false;
          for (var c = 0; c < children.length; c += 1) {
            if (!children[c].hidden) { any = true; break; }
          }
          groups[g].hidden = !any;
        }
        input.setAttribute("data-results", visible ? "" : "none");
      }
      input.addEventListener("input", filter);
    }(selects[s]));
  }

  // One quiet dirty-state notice and the browser's own leave confirmation. Forms still work
  // when this is absent; a normal submit clears the flag before the page unloads.
  var watched = document.querySelectorAll("form[data-dirty-watch]");
  if (watched.length) {
    var dirty = false;
    var submitting = false;
    var note = document.createElement("p");
    note.className = "dirty-note";
    note.setAttribute("role", "status");
    note.textContent = "Alterações por guardar.";
    document.body.appendChild(note);

    function mark(event) {
      // The option filter is a search helper: it changes visibility, never a submitted value.
      if (event && event.target && event.target.classList &&
          event.target.classList.contains("select-filter")) return;
      if (dirty) return;
      dirty = true;
      note.classList.add("is-visible");
    }
    function clear() {
      dirty = false;
      submitting = true;
      note.classList.remove("is-visible");
    }
    for (var w = 0; w < watched.length; w += 1) {
      watched[w].addEventListener("input", mark);
      watched[w].addEventListener("change", mark);
      watched[w].addEventListener("submit", clear);
    }

    // Publishing, unpublishing, restoring or duplicating acts on the STORED draft. Block it
    // while the visible form has unsaved edits, before any confirmation dialog can appear,
    // and send the operator to the save control instead of discarding the edits silently.
    function blockStoredAction(event) {
      if (!dirty) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      note.textContent = "Alterações por guardar: guarde o rascunho antes de publicar, " +
        "despublicar, restaurar ou duplicar.";
      note.classList.add("is-visible");
      var save = document.querySelector(".draft-save");
      if (save) {
        if (save.scrollIntoView) save.scrollIntoView({ block: "center" });
        save.focus();
      }
    }
    var guarded = document.querySelectorAll("form[data-requires-clean]");
    for (var g = 0; g < guarded.length; g += 1) {
      // A click is caught first so browser validation of the reason field cannot hide the
      // dirty warning; Enter still reaches the submit listener below.
      guarded[g].addEventListener("click", function (event) {
        var target = event.target;
        var button = target && target.closest
          ? target.closest('button[type="submit"]') : null;
        if (button) blockStoredAction(event);
      });
      guarded[g].addEventListener("submit", blockStoredAction);
    }

    window.addEventListener("beforeunload", function (event) {
      if (!dirty || submitting) return;
      event.preventDefault();
      event.returnValue = "";
      return "";
    });
  }

  // Deliberate actions keep their label; the confirmation is only an extra browser guard.
  var forms = document.querySelectorAll("form[data-confirm]");
  for (var f = 0; f < forms.length; f += 1) {
    forms[f].addEventListener("submit", function (event) {
      var message = event.currentTarget.getAttribute("data-confirm");
      if (message && !window.confirm(message)) event.preventDefault();
    });
  }
}());
