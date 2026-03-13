## Metro CODB — Known Validation Gaps (as of Session E-Fix)

### Manufacturing: −0.74 pp gap (benchmark 20.9%, model 20.2%)
Likely causes: partial state-level OEWS wage fallbacks for 58 metros,
minor industrial rent gaps. Root cause analysis in metro_codb_validation_report.md.
Recommended fix: improve OEWS MSA coverage. Deferred post-launch.

### Distribution: −3.80 pp gap (benchmark 37.4%, model 33.6%)
Likely causes: CommercialEdge industrial rent over-estimation vs whitepaper
rates (est. 1.5–2 pp), electricity parameter possibly high at 200K kWh/month
(est. 0.7–1.0 pp). Root cause analysis in metro_codb_validation_report.md.
Recommended fix: verify rent and electricity parameters against source Excel.
Deferred post-launch.

## Repo Location
Current build is in `edai_accounting_modules/`.
Target location is the EDai 3.0 app folder per OneDrive structure.
Reorganize at Session I or Session K — do not move files mid-build
as it will break all existing path references.
