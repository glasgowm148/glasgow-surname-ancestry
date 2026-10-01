(() => {
 function bind(root=document){
  const button = root.querySelector("#copy-profile-update");
  const draft = root.querySelector("#profile-update-draft");
  const status = root.querySelector("#profile-update-status");
  if (!button || !draft || button.dataset.copyBound) return;
  button.dataset.copyBound="yes";

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
}
 bind();document.addEventListener("glasgow:fragment-loaded",event=>bind(event.detail.root));
})();
