(() => {
  const workbench = document.getElementById("profile-workbench");
  if (!workbench) return;

  const status = document.getElementById("profile-link-status");

  const showStatus = (message, state = "success") => {
    if (!status) return;
    status.textContent = message;
    status.dataset.state = state;
  };

  const copyText = async (value) => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(value);
      return;
    }
    const area = document.createElement("textarea");
    area.value = value;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    try {
      area.select();
      if (!document.execCommand("copy")) throw new Error("The browser could not copy the draft.");
    } finally {
      area.remove();
    }
  };

  document.getElementById("copy-profile-draft")?.addEventListener("click", async () => {
    try {
      await copyText(document.getElementById("profile-draft")?.value || "");
      showStatus("WikiTree biography copied.");
    } catch (error) {
      showStatus(`Copy failed: ${error.message}`, "error");
    }
  });
})();
