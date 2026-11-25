(() => {
  const params = new URLSearchParams(location.search);
  const person = params.get('person') || '';
  const study = params.get('study');
  const question = params.get('question');
  const profile = params.get('profile');
  const path = params.get('page') || '';
  const origin = /^\/branches\/[a-z0-9-]+\/#(?:research-gap-\d+|study-question)$/.test(path)
    ? location.origin + path : '';
  const outline = document.querySelector('#feedback-template');
  const context = [
    study && 'Study: ' + study,
    question && 'Research question: ' + question,
    profile && 'Linked catalogue profile: ' + profile,
    person && 'Person: ' + person,
    'Page: ' + (origin || (person ? location.origin + '/people/' + encodeURIComponent(person.toLowerCase()) + '.html' : '[name or page link]')),
  ].filter(Boolean);
  outline.value = context.join('\n') + '\n\nWhat I can add or correct:\n\nSource, reference and date (or how I know):\n';
  const label = document.querySelector('#feedback-person');
  if (study || person) {
    label.textContent = [study, person, question].filter(Boolean).join(' · ');
    document.querySelector('#feedback-person-line').hidden = false;
  }
  if (/^[A-Za-z][A-Za-z_'’-]*-\d+$/.test(person)) {
    const wiki = document.querySelector('#feedback-wikitree');
    wiki.href = 'https://www.wikitree.com/wiki/' + encodeURIComponent(person);
    wiki.hidden = false;
  }
  const send = document.querySelector('#how-to-send .actions a[href^="mailto:"]');
  if (send) {
    const address = send.href.split('?')[0];
    const updateMail = () => {
      send.href = address + '?subject=' + encodeURIComponent(study || person || 'Glasgow surname research')
        + '&body=' + encodeURIComponent(outline.value);
    };
    updateMail();
    outline.addEventListener('input', updateMail);
  }
  const copy = document.querySelector('#feedback-copy');
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(outline.value);
      copy.textContent = 'Copied';
    } catch {
      outline.select();
      copy.textContent = 'Selected: press Ctrl+C or ⌘C to copy';
    }
  });
})();
