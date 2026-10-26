#!/usr/bin/env python3
"""Refresh research-access interfaces after targeted or full site generation."""
from pathlib import Path
import runpy
try:
    from catalogue_theme import repair_clean_catalogue_stylesheet
except ModuleNotFoundError:
    from tools.catalogue_theme import repair_clean_catalogue_stylesheet

ROOT = Path(__file__).resolve().parents[1]


def research_publication_gate():
    """Refuse the release when research would not reach a reader.

    Runs tools/check_research_publication.py against its baseline: problems
    already listed there are tolerated, any new one stops the release.
    """
    try:
        from tools import check_research_publication as research_check
    except ModuleNotFoundError:
        import check_research_publication as research_check
    baseline = ROOT / research_check.DEFAULT_BASELINE
    if research_check.main(['--baseline', str(baseline), '--examples', '5']):
        raise RuntimeError(
            'Release stopped: the research publication check found new problems (listed above). Fix them, '
            'or record them on purpose with tools/check_research_publication.py --baseline '
            f'{research_check.DEFAULT_BASELINE} --update-baseline --accept-new and say why in the commit.')


def publish(*, render_people=True, gate=True, refresh_index=True):
    """The release repairs. The full rebuild runs them with ``gate`` and
    ``refresh_index`` off: it reports the research check itself and does not
    refresh the local search index."""
    try:
        from tools.public_privacy import repair as repair_privacy
    except ModuleNotFoundError:
        from public_privacy import repair as repair_privacy
    # Source library documents follow the dossiers' current evidence; the repairs
    # below (dates, privacy, static sections) then apply on top.
    runpy.run_path(str(ROOT / 'tools/build_source_documents.py'))['main']([])
    runpy.run_path(str(ROOT / 'tools/build_record_details.py'))['main']([])   # uses the documents' record lists
    runpy.run_path(str(ROOT / 'tools/build_person_models.py'))['main']([])    # uses both, plus the dossiers
    runpy.run_path(str(ROOT / 'tools/repair_public_dna.py'))['repair']()
    runpy.run_path(str(ROOT / 'tools/withhold_licensed_assets.py'))['withhold']()
    repair_privacy(ROOT / 'www')
    runpy.run_path(str(ROOT / 'tools/repair_assessment_dates.py'))['repair'](ROOT / 'www')
    runpy.run_path(str(ROOT / 'tools/repair_claim_status.py'))['repair'](ROOT / 'www')
    runpy.run_path(str(ROOT / 'tools/publish_resolved_dossiers.py'))['publish']()
    # Reapply approved map corrections after imports; raw map inputs are private.
    runpy.run_path(str(ROOT / 'tools/project_record_locations.py'))['project'](ROOT / 'www', write=True)
    runpy.run_path(str(ROOT / 'tools/repair_evidence_source_links.py'))['repair']()
    runpy.run_path(str(ROOT / 'tools/build_research_catalog.py'))['sync_generated_profile_work_status']()
    # Source pages made from the canonical-record block alone lacked the standard
    # reader container that the static-source sections anchor on.
    runpy.run_path(str(ROOT / 'tools/ingest_canonical_records.py'))['repair_layout'](ROOT)
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
    runpy.run_path(str(ROOT / 'tools/publish_newspaper_review.py'))['repair']()
    # Rendering old imported dossiers must not overwrite merge redirects.
    runpy.run_path(str(ROOT / 'tools/publish_wikitree_redirect_aliases.py'))['publish']()
    # Retired record subjects (record-…) redirect to the person they became.
    runpy.run_path(str(ROOT / 'tools/publish_retired_record_redirects.py'))['publish']()
    repair_privacy(ROOT / 'www')
    runpy.run_path(str(ROOT / 'tools/site_analytics.py'))['repair']()
    if gate:
        research_publication_gate()
    try:
        from tools.finalize_site import finalize
    except ModuleNotFoundError:
        from finalize_site import finalize
    finalize(ROOT / 'www')
    if not refresh_index:
        return
    refresh_result = runpy.run_path(str(ROOT / 'tools/genealogy/batch_complete.py'))['refresh_after_batch']()
    if refresh_result:
        raise RuntimeError('Website synchronized; local genealogy index refresh failed (see refresh state/logs).')


if __name__ == '__main__':
    publish()
