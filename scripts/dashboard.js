(function () {
  const search = document.getElementById("note-search");
  const list = document.getElementById("note-list");
  const status = document.getElementById("search-status");
  if (!search || !list) return;

  const items = Array.from(list.querySelectorAll(".dashboard-note"));
  const itemByUrl = new Map(items.map((item) => [item.getAttribute("data-note-url"), item]));
  const searchIndexUrl = search.getAttribute("data-search-index") || list.getAttribute("data-search-index") || "/search-index.json";
  let searchEntries = null;

  const escapeHtml = (value) =>
    value.replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[char]);

  const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const normalize = (value) => value.toLocaleLowerCase();
  const queryTerms = (value) => Array.from(new Set(normalize(value).split(/\s+/).filter(Boolean)));

  const pathText = (entry) => (entry.paths || []).map((path) => path.join(" \u00b7 ")).join(" ");

  const searchText = (entry) => {
    if (!entry.searchText) {
      entry.searchText = normalize([entry.title, entry.summary, entry.date, pathText(entry), entry.body].filter(Boolean).join(" "));
    }
    return entry.searchText;
  };

  const renderHighlighted = (text, terms) => {
    const pattern = new RegExp(terms.map(escapeRegExp).join("|"), "gi");
    let output = "";
    let cursor = 0;
    for (const match of text.matchAll(pattern)) {
      output += escapeHtml(text.slice(cursor, match.index));
      output += `<mark>${escapeHtml(match[0])}</mark>`;
      cursor = match.index + match[0].length;
    }
    output += escapeHtml(text.slice(cursor));
    return output;
  };

  const excerpt = (text, terms) => {
    const lower = normalize(text);
    const found = terms
      .map((term) => ({ term, index: lower.indexOf(term) }))
      .filter((match) => match.index >= 0)
      .sort((left, right) => left.index - right.index)[0];
    if (!found) return "";

    const radius = 96;
    let start = Math.max(0, found.index - radius);
    let end = Math.min(text.length, found.index + found.term.length + radius);
    while (start > 0 && /\S/.test(text[start - 1])) start -= 1;
    while (end < text.length && /\S/.test(text[end])) end += 1;
    return `${start > 0 ? "..." : ""}${text.slice(start, end).trim()}${end < text.length ? "..." : ""}`;
  };

  const snippetsFor = (entry, terms) => {
    const fields = [
      [entry.title || "", false],
      [entry.date || "", false],
      [pathText(entry), false],
      [entry.summary || "", false],
      [entry.body || "", true],
    ];
    return fields
      .map(([text, useExcerpt]) => {
        if (!text || !terms.some((term) => normalize(text).includes(term))) return "";
        const snippet = useExcerpt ? excerpt(text, terms) : text;
        if (!snippet) return "";
        return `<div class="dashboard-match">${renderHighlighted(snippet, terms)}</div>`;
      })
      .filter(Boolean)
      .slice(0, 4);
  };

  const setStatus = (message) => {
    if (status) status.textContent = message;
  };

  const clearMatches = (item) => {
    const matches = item.querySelector(".dashboard-matches");
    if (!matches) return;
    matches.hidden = true;
    matches.innerHTML = "";
  };

  const renderMatches = (item, snippets) => {
    const matches = item.querySelector(".dashboard-matches");
    if (!matches) return;
    matches.innerHTML = snippets.join("");
    matches.hidden = snippets.length === 0;
  };

  const filterFromCards = (terms) => {
    let count = 0;
    for (const item of items) {
      clearMatches(item);
      const haystack = item.getAttribute("data-search") || "";
      const matched = terms.every((term) => haystack.includes(term));
      item.classList.toggle("is-hidden", !matched);
      if (matched) count += 1;
    }
    return count;
  };

  const filterFromIndex = (terms) => {
    let count = 0;
    for (const entry of searchEntries) {
      const item = itemByUrl.get(entry.url);
      if (!item) continue;
      const matched = terms.every((term) => searchText(entry).includes(term));
      item.classList.toggle("is-hidden", !matched);
      if (!matched) {
        clearMatches(item);
        continue;
      }
      count += 1;
      renderMatches(item, snippetsFor(entry, terms));
    }
    return count;
  };

  const resetSearch = () => {
    for (const item of items) {
      item.classList.remove("is-hidden");
      clearMatches(item);
    }
    setStatus("");
  };

  const filter = () => {
    const terms = queryTerms(search.value);
    if (terms.length === 0) {
      resetSearch();
      return;
    }

    const count = searchEntries ? filterFromIndex(terms) : filterFromCards(terms);
    const suffix = count === 1 ? "match" : "matches";
    setStatus(searchEntries ? `${count} ${suffix}` : `${count} ${suffix} while the full index loads`);
  };

  search.addEventListener("input", filter);

  fetch(searchIndexUrl, { cache: "no-store" })
    .then((response) => (response.ok ? response.json() : Promise.reject(new Error("missing search index"))))
    .then((data) => {
      searchEntries = Array.isArray(data.notes) ? data.notes : [];
      filter();
    })
    .catch(() => {
      searchEntries = null;
      if (search.value.trim()) setStatus("Full-content search index unavailable");
    });
})();
