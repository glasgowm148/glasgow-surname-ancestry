(() => {
  const button = document.getElementById("copy-profile-update");
  const draft = document.getElementById("profile-update-draft");
  const status = document.getElementById("profile-update-status");
  if (!button || !draft) return;

  button.addEventListener("click", async () => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(draft.value);
      } else {
        draft.select();
        document.execCommand("copy");
      }
      if (status) {
        status.textContent = "Full revised WikiTree biography copied.";
        status.dataset.state = "success";
      }
    } catch (error) {
      if (status) {
        status.textContent = `Copy failed: ${error.message}`;
        status.dataset.state = "error";
      }
    }
  });
})();
