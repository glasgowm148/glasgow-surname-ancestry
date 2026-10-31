"""Public family pages reuse sourced conclusions without another research store."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import repair_site_experience as subject


class FamilyResearchContextTests(unittest.TestCase):
    def test_public_conclusion_keeps_citation_and_identity_limits(self):
        with tempfile.TemporaryDirectory() as temporary:
            web = Path(temporary)
            (web / 'people').mkdir()
            dossier = {'research_findings': [{'sections': [
                {'category': 'conclusion', 'markdown': '**Charles** is named in the [original register](https://example.org/register). Later identity remains uncertain.'},
                {'category': 'notes', 'markdown': 'Separate notes must remain on the person account.'},
            ]}]}
            (web / 'people/person.json').write_text(json.dumps(dossier))
            people = {'person': {'slug': 'person', 'name': 'Daniel & family', 'url': '/people/person.html'}}
            branch = {'kind': 'family', 'root': 'person'}
            with patch.object(subject, 'WEB', web):
                context = subject.family_research_context(branch, people)
                self.assertIn('<strong>Charles</strong>', context)
                self.assertIn('https://example.org/register', context)
                self.assertIn('Later identity remains uncertain.', context)
                self.assertIn('Daniel &amp; family', context)
                self.assertNotIn('Separate notes', context)
                self.assertEqual('', subject.family_research_context({'kind': 'region'}, people))
                self.assertEqual('', subject.family_research_context({'kind': 'family', 'root': 'missing'}, people))
                (web / 'people/person.json').write_text(json.dumps({'research_findings': []}))
                self.assertEqual('', subject.family_research_context(branch, people))

    def test_reprojection_is_idempotent_and_stale_context_is_removed(self):
        page = '<header>Site</header><main><header class="r-page-head"><h1>Family</h1></header><section>People</section></main>'
        context = '<section id="family-research-context"><h2>Current family research</h2><p>Qualified account.</p></section>'
        result = subject.insert_family_research_context(page, context)
        self.assertLess(result.index('<main>'), result.index(context))
        self.assertLess(result.index(context), result.index('<section>People'))
        self.assertEqual(result, subject.insert_family_research_context(result, context))
        self.assertEqual(page, subject.insert_family_research_context(result, ''))
        with self.assertRaisesRegex(ValueError, 'insertion point missing'):
            subject.insert_family_research_context('<main><h1>No page header</h1></main>', context)


if __name__ == '__main__':
    unittest.main()
