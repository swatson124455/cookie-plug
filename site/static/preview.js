/* One-file preview: hash routing between pages, and a form that never leaves the page. */
(function () {
  "use strict";
  var routes = Array.prototype.slice.call(document.querySelectorAll("[data-route]"));
  var navLinks = Array.prototype.slice.call(document.querySelectorAll("[data-nav]"));
  var LABELS = { product: "Product", volume: "Monthly volume", timing: "Timing", current_setup: "Made today",
                 name: "Name", company: "Brand and website", email: "Email", phone: "Phone", notes: "Notes" };

  function show() {
    var token = decodeURIComponent(window.location.hash.replace(/^#/, "")) || "home";
    var target = document.getElementById(token);
    var route = target && target.closest ? target.closest("[data-route]") : null;
    if (!route) { route = document.getElementById("home"); target = null; }
    routes.forEach(function (item) { item.hidden = item !== route; });
    var section = route.getAttribute("data-nav-key");
    navLinks.forEach(function (link) {
      if (link.getAttribute("data-nav") === section) { link.setAttribute("aria-current", "page"); }
      else { link.removeAttribute("aria-current"); }
    });
    document.title = route.getAttribute("data-title") || document.title;
    scrollTo(target, route);
  }

  function scrollTo(target, route) {
    if (target && target !== route) { target.scrollIntoView(); } else { window.scrollTo(0, 0); }
  }

  function row(list, label, value) {
    var term = document.createElement("dt");
    var detail = document.createElement("dd");
    term.textContent = label;
    detail.textContent = value;
    list.appendChild(term);
    list.appendChild(detail);
  }

  function confirmSubmission(form) {
    var box = document.createElement("div");
    var heading = document.createElement("h3");
    var note = document.createElement("p");
    var list = document.createElement("dl");
    box.className = "form-done";
    box.setAttribute("role", "status");
    heading.textContent = "Preview: nothing was sent";
    note.textContent = "On the live site this goes to the form inbox, then into the lead pipeline with leadgen import-form. These are the fields it would carry:";
    new FormData(form).forEach(function (value, key) {
      if (LABELS[key] && String(value).trim()) { row(list, LABELS[key], String(value)); }
    });
    box.appendChild(heading);
    box.appendChild(note);
    box.appendChild(list);
    form.replaceWith(box);
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form.matches || !form.matches("form[data-preview]")) { return; }
    event.preventDefault();
    if (form.reportValidity()) { confirmSubmission(form); }
  });
  if ("scrollRestoration" in history) { history.scrollRestoration = "manual"; }
  window.addEventListener("hashchange", show);
  // A page opened with a hash gets the browser's own jump-to-anchor after load; route again after it.
  window.addEventListener("load", function () { window.setTimeout(show, 0); });
  show();
}());
