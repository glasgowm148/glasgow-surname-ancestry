(() => {
  const roots = document.querySelectorAll("[data-candidate-tabs]");

  roots.forEach((root) => {
    const tabs = [...root.querySelectorAll('[role="tab"]')];
    const panels = tabs.map((tab) => document.getElementById(tab.getAttribute("aria-controls")));
    if (!tabs.length || panels.some((panel) => !panel)) return;

    const activate = (tab, updateHash = true) => {
      tabs.forEach((item, index) => {
        const selected = item === tab;
        item.setAttribute("aria-selected", String(selected));
        item.tabIndex = selected ? 0 : -1;
        panels[index].hidden = !selected;
      });
      if (updateHash) history.replaceState(null, "", `#${tab.getAttribute("aria-controls")}`);
    };

    root.classList.add("is-enhanced");
    const hashTab = tabs.find((tab) => `#${tab.getAttribute("aria-controls")}` === location.hash);
    activate(hashTab || tabs[0], false);

    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => activate(tab));
      tab.addEventListener("keydown", (event) => {
        let target = null;
        if (event.key === "ArrowRight") target = tabs[(index + 1) % tabs.length];
        if (event.key === "ArrowLeft") target = tabs[(index - 1 + tabs.length) % tabs.length];
        if (event.key === "Home") target = tabs[0];
        if (event.key === "End") target = tabs[tabs.length - 1];
        if (!target) return;
        event.preventDefault();
        activate(target);
        target.focus();
      });
    });

    window.addEventListener("hashchange", () => {
      const target = tabs.find((tab) => `#${tab.getAttribute("aria-controls")}` === location.hash);
      if (target) activate(target, false);
    });
  });
})();
