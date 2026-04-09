(function () {
  const bar = document.createElement("div");
  bar.className = "page-progress";
  document.documentElement.appendChild(bar);

  let active = false;
  let settleTimer = 0;
  let resetTimer = 0;

  const stop = () => {
    active = false;
    window.clearTimeout(settleTimer);
    window.clearTimeout(resetTimer);
    bar.classList.add("is-active", "is-complete");
    settleTimer = window.setTimeout(() => {
      bar.classList.remove("is-active");
      bar.classList.add("is-running", "is-complete");
      resetTimer = window.setTimeout(() => {
        bar.classList.remove("is-running", "is-complete");
        bar.style.removeProperty("transform");
      }, 220);
    }, 140);
  };

  const start = () => {
    if (active) return;
    active = true;
    window.clearTimeout(settleTimer);
    window.clearTimeout(resetTimer);
    bar.classList.remove("is-complete");
    bar.style.transform = "scaleX(0.06)";
    bar.classList.add("is-active");
    window.requestAnimationFrame(() => {
      bar.classList.add("is-running");
    });
  };

  const shouldTrack = (link) => {
    if (!link || link.target === "_blank" || link.hasAttribute("download")) return false;
    const href = link.getAttribute("href") || "";
    if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("javascript:")) return false;
    const url = new URL(link.href, window.location.href);
    return url.origin === window.location.origin;
  };

  document.addEventListener("click", (event) => {
    const link = event.target.closest("a");
    if (!shouldTrack(link)) return;
    start();
  });

  window.addEventListener("pageshow", stop);
  window.addEventListener("load", stop);
})();
