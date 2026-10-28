#!/bin/zsh
# Rebuild the local site in place after a change to the builders or to many
# research files. Local only: it never deploys, pushes or edits WikiTree.
#
# This is the order that was run and checked on 7 October 2026. It is not the
# full catalogue build (see docs/build-reproducibility.md): the records index
# is left as it is, so a corrected record's person, date or place does not
# change in record lists here.
#
# Order matters:
#   1. section pages first, because the link index (built at the start of the
#      person-page pass) reads them;
#   2. then the research sync and every person page;
#   3. then the pages and passes that touch the shared shell;
#   4. finalize last, then the checks.
#
# usage: tools/rebuild_local_site.sh [first-step] [last-step]
#        (steps are numbered in the progress log; rerun from a failed step)
# Takes about an hour: 4,800 person pages render in about 25 minutes and
# finalize re-stamps all 24,000 pages in about 13.

cd "$(dirname "$0")/.." || exit 2
export PYTHONPATH=$PWD:$PWD/tools
PY=.venv/bin/python
LOG=tmp/rebuild-logs
mkdir -p $LOG
FIRST=${1:-1}; LAST=${2:-99}
N=0
step() {  # step <tolerate-failure 0|1> <name> <command...>
  N=$((N+1)); local tolerate=$1 name=$2; shift 2
  if (( N < FIRST || N > LAST )); then return 0; fi
  echo "[$(date +%H:%M:%S)] step $N $name: start" | tee -a $LOG/progress.log
  "$@" > $LOG/$(printf %02d $N)-$name.log 2>&1
  local rc=$?
  echo "[$(date +%H:%M:%S)] step $N $name: exit $rc" | tee -a $LOG/progress.log
  if (( rc != 0 && tolerate == 0 )); then echo "STOPPED at step $N $name (see $LOG)" | tee -a $LOG/progress.log; exit 1; fi
}

# 0. Declared inputs: the research registries are generated from the research
#    database, and site inputs no builder writes are installed from their homes.
step 0 research-views      $PY tools/workbench_legacy_views.py --write
step 0 site-inputs         $PY tools/site_declared_inputs.py --install
# 1. Sections the link index reads.
step 0 latest-findings     $PY tools/build_latest_findings.py
step 0 place-pages         $PY tools/refresh_place_pages.py
step 0 research-groups     $PY tools/repair_research_groups.py
step 0 branches-directory  $PY tools/build_branches_directory.py
step 0 study-pages         $PY tools/build_study_pages.py
step 0 research-questions  $PY tools/repair_research_questions.py
step 0 subject-drafts      $PY tools/build_research_subject_drafts.py
step 0 research-queue      $PY tools/build_research_queue.py
# 2. People. The sync exits 1 when findings exist for people with no page yet
#    (it lists them); that is reported, not a reason to stop.
step 1 sync-research       $PY tools/sync_catalogue_research.py --write
step 0 person-pages        $PY tools/repair_person_hierarchy.py
step 0 comparison-index    $PY tools/refresh_comparison_index.py
# 3. Section pages and the shared shell.
step 0 evidence-page       $PY tools/build_evidence_page.py
step 0 relabel-badges      $PY tools/relabel_evidence_badges.py
step 0 about-pages         $PY -m tools.about_pages
step 0 dna-navigation      $PY tools/repair_dna_navigation.py
step 0 statistics          $PY tools/build_statistics_page.py
step 0 resources           $PY tools/build_resources_page.py
step 0 research-access     $PY tools/publish_research_access.py
step 0 reader-guidance     $PY tools/repair_reader_guidance.py
step 0 clean-urls          $PY tools/publish_clean_urls.py
step 0 work-status         $PY -c "import runpy; print(runpy.run_path('tools/build_research_catalog.py')['sync_generated_profile_work_status']())"
step 0 ancestry-progress   $PY tools/build_ancestry_progress.py
# 4. Finalize, then the checks. A check that fails is reported and the rest still run.
# The release repairs (privacy and DNA withholding, licensed assets, merge
# redirects, the newspaper review and others) and the publishers whose files the
# catalogue's directory reset removes. The live site has always had these.
step 0 release-repairs     $PY -c "import runpy; runpy.run_path('tools/publish_research_release.py')['publish'](gate=False, refresh_index=False)"
step 0 irish-death-index   $PY tools/publish_irish_death_index.py
step 0 opr-marriages       $PY tools/publish_opr_marriage_review.py
step 0 tree-links          $PY tools/profile_tree_links.py   # the check below expects every page's tree row
step 0 group-places        $PY tools/study_place_links.py   # tree-group place lists link only existing place pages
# Later steps rewrite the atlas models after the release's DNA repair; restore the
# approved versions last, or the privacy check finds individual DNA annotations.
step 0 dna-withhold        $PY -c "import runpy; print(runpy.run_path('tools/repair_public_dna.py')['repair']())"
step 0 finalize            $PY -c "from tools.finalize_site import finalize; print(finalize())"
step 0 release-totals      $PY tools/check_release_consistency.py --fix --no-research   # totals after finalize's record ingest
step 1 check-research      $PY tools/check_research_publication.py --baseline data/site/research-publication-baseline.json
step 1 check-release       $PY tools/check_release_consistency.py
step 1 check-links         $PY tools/check_internal_links.py --site www --baseline data/site/internal-link-baseline.json
step 1 check-finding-links $PY tools/relink_finding_anchors.py --check
step 1 check-tree-links    $PY tools/profile_tree_links.py --check
step 1 check-experience    $PY tools/audit_site_experience.py
step 1 check-asset-stamps  $PY tools/stamp_asset_versions.py --check
step 1 check-privacy       $PY tools/check_publication_boundary.py
echo "[$(date +%H:%M:%S)] DONE: read $LOG/progress.log; every check step should say exit 0" | tee -a $LOG/progress.log
# Build state (files the build reads from www/ before writing them) is carried
# forward only on purpose, after the checks above have been reviewed: a rebuild
# that failed the privacy check must not become the next build's input.
echo "Once the checks are reviewed: $PY tools/site_declared_inputs.py --save-state" | tee -a $LOG/progress.log
