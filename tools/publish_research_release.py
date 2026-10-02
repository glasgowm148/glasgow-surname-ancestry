#!/usr/bin/env python3
"""Refresh research-access interfaces after targeted or full site generation."""
from pathlib import Path
import runpy
try:
    from catalogue_theme import repair_clean_catalogue_stylesheet
except ModuleNotFoundError:
    from tools.catalogue_theme import repair_clean_catalogue_stylesheet

ROOT = Path(__file__).resolve().parents[1]


def publish(*, render_people=True):
    try:
        from tools.public_privacy import repair as repair_privacy
    except ModuleNotFoundError:
        from public_privacy import repair as repair_privacy
    runpy.run_path(str(ROOT / 'tools/repair_public_dna.py'))['repair']()
    runpy.run_path(str(ROOT / 'tools/withhold_licensed_assets.py'))['withhold']()
    repair_privacy(ROOT / 'www')
    runpy.run_path(str(ROOT / 'tools/repair_assessment_dates.py'))['repair'](ROOT / 'www')
    runpy.run_path(str(ROOT / 'tools/repair_claim_status.py'))['repair'](ROOT / 'www')
    runpy.run_path(str(ROOT / 'tools/publish_resolved_dossiers.py'))['publish']()
    runpy.run_path(str(ROOT / 'tools/repair_evidence_source_links.py'))['repair']()
    runpy.run_path(str(ROOT / 'tools/build_research_catalog.py'))['sync_generated_profile_work_status']()
    runpy.run_path(str(ROOT / 'tools/publish_static_sources.py'))['main']()
    repair_clean_catalogue_stylesheet(ROOT / 'www')
    runpy.run_path(str(ROOT / 'tools/repair_sources_page.py'))['repair']()
    if render_people:
        runpy.run_path(str(ROOT / 'tools/repair_person_hierarchy.py'))['repair']()
    runpy.run_path(str(ROOT / 'tools/repair_profile_update_controls.py'))['repair']()
    repair_privacy(ROOT / 'www')
    runpy.run_path(str(ROOT / 'tools/repair_release_readiness.py'))['repair']()
    runpy.run_path(str(ROOT / 'tools/repair_publication_policy.py'))['repair']()
    runpy.run_path(str(ROOT / 'tools/site_analytics.py'))['repair']()
    runpy.run_path(str(ROOT / 'tools/publish_research_access.py'))['repair']()
    runpy.run_path(str(ROOT / 'tools/repair_reader_guidance.py'))['repair']()
    runpy.run_path(str(ROOT / 'tools/refresh_comparison_index.py'))['refresh'](ROOT)
    runpy.run_path(str(ROOT / 'tools/build_latest_findings.py'))['repair']()
    runpy.run_path(str(ROOT / 'tools/build_relationship_audit.py'))['build']()
    runpy.run_path(str(ROOT / 'tools/build_research_queue.py'))['build']()
    # Rendering old imported dossiers must not overwrite merge redirects.
    runpy.run_path(str(ROOT / 'tools/publish_wikitree_redirect_aliases.py'))['publish']()
    repair_privacy(ROOT / 'www')
    runpy.run_path(str(ROOT / 'tools/site_analytics.py'))['repair']()
    try:
        from tools.finalize_site import finalize
    except ModuleNotFoundError:
        from finalize_site import finalize
    finalize(ROOT / 'www')
    refresh_result = runpy.run_path(str(ROOT / 'tools/genealogy/batch_complete.py'))['refresh_after_batch']()
    if refresh_result:
        raise RuntimeError('Website synchronized; local genealogy index refresh failed (see refresh state/logs).')


if __name__ == '__main__':
    publish()
