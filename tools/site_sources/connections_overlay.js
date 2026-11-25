/* Point readers to the least-supported step in the displayed relationship route. */
(() => {
  const results = document.querySelector('#v3-connection-results');
  if (!results) return;

  const grades = ['unknown', 'uncertain', 'possible', 'probable', 'strongly_supported', 'proved', 'direct'];
  function rank(step) {
    return grades.indexOf(step.querySelector('[data-status]')?.dataset.status);
  }

  function showReviewLink() {
    const heading = results.querySelector('.v3-route-heading > div');
    if (!heading || heading.querySelector('.glasgow-weakest-step')) return;
    const steps = [...results.querySelectorAll('.v3-route-link')];
    const weakest = steps.reduce((first, step) => !first || rank(step) < rank(first) ? step : first, null);
    if (!weakest || ['proved', 'direct'].includes(weakest.querySelector('[data-status]')?.dataset.status)) return;
    const before = weakest.previousElementSibling?.querySelector('h3')?.textContent;
    const after = weakest.nextElementSibling?.querySelector('h3')?.textContent;
    const badge = weakest.querySelector('[data-status]');
    const control = weakest.querySelector('button[data-edge]');
    if (!before || !after || !badge || !control) return;

    const note = document.createElement('p');
    note.className = 'glasgow-weakest-step';
    const title = document.createElement('strong');
    title.textContent = 'First link to check: ';
    const link = document.createElement('button');
    link.type = 'button';
    link.className = 'r-button quiet';
    link.textContent = 'Read the evidence for this step';
    link.addEventListener('click', () => {
      if (control.getAttribute('aria-expanded') !== 'true') control.click();
      control.focus();
    });
    const label = badge.textContent.replace(/^[✓?×·]\s*/, '').trim();
    note.append(title, before + ' ↔ ' + after + ' (' + label + '). ', link);
    const modelNote = document.createElement('p');
    modelNote.textContent = 'This route follows the relationship snapshot. For later assessments, open the linked catalogue pages for ';
    for (const [index, node] of [weakest.previousElementSibling, weakest.nextElementSibling].entries()) {
      if (index) modelNote.append(' and ');
      modelNote.append(node.querySelector('h3 a').cloneNode(true));
    }
    modelNote.append('.');
    heading.append(note, modelNote);
  }

  new MutationObserver(showReviewLink).observe(results, {childList: true, subtree: true});
  showReviewLink();
})();
