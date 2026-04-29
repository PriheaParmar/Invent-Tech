document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("sbToggle");
  if (!btn) return;

  const saved = localStorage.getItem("inventtech_sidebar") || "open";
  if (saved === "collapsed") document.body.classList.add("sb-collapsed");

  btn.addEventListener("click", () => {
    document.body.classList.toggle("sb-collapsed");
    const collapsed = document.body.classList.contains("sb-collapsed");
    localStorage.setItem("inventtech_sidebar", collapsed ? "collapsed" : "open");
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const SEARCH_INPUT_SELECTOR = [
    'input[type="search"]',
    'input[type="text"][placeholder*="Search" i]',
    'input:not([type])[placeholder*="Search" i]'
  ].join(',');

  const CLEAR_ICON = `
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M18 6 6 18"></path>
      <path d="M6 6l12 12"></path>
    </svg>
  `;

  function dispatchInputEvents(input) {
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function shouldAutoSubmit(input) {
    const form = input.form;
    if (!form) return false;
    if ((input.dataset.clearSubmit || "") === "0") return false;
    if ((form.dataset.clearSubmit || "") === "0") return false;
    return (form.method || "get").toLowerCase() === "get";
  }

  function clearInput(input) {
    if (!input.value) return;

    input.value = "";
    dispatchInputEvents(input);
    input.focus();

    if (shouldAutoSubmit(input)) {
      if (typeof input.form.requestSubmit === "function") {
        input.form.requestSubmit();
      } else {
        input.form.submit();
      }
    }
  }

  function syncState(input, wrapper) {
    wrapper.classList.toggle("has-value", Boolean((input.value || "").trim()));
  }

  function enhanceSearchInput(input) {
    if (!input || input.dataset.clearEnhanced === "1" || input.disabled || input.readOnly) {
      return;
    }

    let wrapper = input.parentElement;
    if (!wrapper || !wrapper.classList.contains("it-search-control")) {
      wrapper = document.createElement("span");
      wrapper.className = "it-search-control";
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);
    }

    let clearBtn = wrapper.querySelector(".it-search-clear");
    if (!clearBtn) {
      clearBtn = document.createElement("button");
      clearBtn.type = "button";
      clearBtn.className = "it-search-clear";
      clearBtn.setAttribute("aria-label", "Clear search");
      clearBtn.innerHTML = CLEAR_ICON;
      wrapper.appendChild(clearBtn);
    }

    const sync = () => syncState(input, wrapper);

    clearBtn.addEventListener("click", () => clearInput(input));
    input.addEventListener("input", sync);
    input.addEventListener("change", sync);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && input.value) {
        event.preventDefault();
        clearInput(input);
      }
    });

    input.dataset.clearEnhanced = "1";
    sync();
  }

  function enhanceSearchInputs(root = document) {
    if (!root) return;

    if (root.matches && root.matches(SEARCH_INPUT_SELECTOR)) {
      enhanceSearchInput(root);
    }

    root.querySelectorAll?.(SEARCH_INPUT_SELECTOR).forEach(enhanceSearchInput);
  }

  enhanceSearchInputs(document);

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === 1) {
          enhanceSearchInputs(node);
        }
      });
    });
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
});