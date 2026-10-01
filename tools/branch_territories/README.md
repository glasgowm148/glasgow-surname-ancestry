# Study map boundaries

The main Families & places map retains the parish territories in
`territories.geojson` and its clipped county context in `counties.geojson`.
`tools/build_branches_directory.py` renders that map and the homepage copy.

Each of the six regional guides also receives a map from
`tools/build_regional_study_maps.py`, called by the directory builder.
Scotland and Ireland retain their maintained parish studies and research
ranking. Other guides show the ten leading administrative areas represented
in the public record CSV, with documentary coverage ranked before unreviewed
profile leads. Areas and links are rebuilt from current public inputs.

An explicitly named state, province or county can be assigned even when its
record's pin uses a country-centre fallback. That fallback coordinate is
never used to identify an area. Country-only entries, inferred locations and
holding points cannot create a local concentration. Geocoded localities can
be assigned by containment; where several administrative names occur, the
last mention wins, with longer names breaking ties. These outlines describe
representative study areas, rather than family lands or precise residences.
The Other guide omits countries represented by the five named regional guides.

`regional-boundaries.geojson` contains simplified regional context and
administrative outlines. Its source URLs, licences, archive hashes and
simplification settings are in `regional-boundaries-sources.json`.
Regenerate it with `.venv/bin/python tools/prepare_regional_boundaries.py`;
`--download` fetches missing Natural Earth archives. Existing Irish and UK
raw inputs are shared with `tools/prepare_branch_territories.py`.
Normal website builds use the prepared geometry and require no downloads.

Shared map assets are maintained in `tools/branches_directory.css` and
`tools/branches_directory.js`; the directory builder publishes both.
Regional ranking and provenance are exported in
`www/assets/research/regional-study-maps.json`. Refresh just the regional
pages with `.venv/bin/python tools/build_regional_study_maps.py`.
