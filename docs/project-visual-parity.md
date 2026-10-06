# Project editing and Pulse visual dogfood

## Baseline

Persistent headed browser at 1264×1258: t1 authenticated local Hoja Test Workspace project `/workspace/project/bb8dab20-52fb-4dcd-a14b-86db7238a3be`, with two ongoing project issues; t2 authenticated external Linear reference project overview, read-only; t4 isolated populated Pulse fixture. Dirty frontend/backend files and `docs/dogfood-pulse.md` predate this visual pass and must remain intact. At 390×844 the local project editor still consumes the upper viewport; no document horizontal overflow was observed. The local project is `started` in persisted data, though a recently mounted form showed `backlog` while loading, so draft state must follow fresh project data before edits.

## Comparison

Local `ProjectDetails` renders `<form className="modal">` inline, but shared `.modal` CSS has `position:absolute;left:50%;top:12%` (`frontend/src/styles.css` line 1). At 1264px the form occupies x347–917,y151–529, directly overlapping the project heading (x295–1213,y130–243), metrics and issues. Its description textarea is only ~54px tall and the Save and Archive buttons touch. At 390px the 358px-wide form still overlays content and exposes destructive Archive next to Save. In Linear the project name/summary are inline editable with Properties in a separate panel, rather than a floating modal on top of overview. Do not copy unknown controls or mutate the external account. The local project title, description and state are draft fields; save uses `projectUpdate`, while archive is a separate destructive mutation. A non-destructive edit area should sit in document flow, have readable field spacing/textarea height and a deliberate Archive separation; opening/closing edit must not discard persisted values or silently save. 

## Source map

`frontend/src/main.tsx` line 159 owns ProjectDetails draft fields, projectUpdate save, archive confirmation and issue list. `frontend/src/styles.css` lines 1,6,33 and 209+ own global modal/project/Pulse layout. Pulse currently renders a real read-only feed (`main.tsx` lines 71–94); isolated t4 showed 24 posts grouped Recent/Older and its existing layout had no document horizontal overflow. No independent Pulse visual defect has been established yet beyond the unavailable publishing composer (a separate ongoing dogfood task). Do not alter that publication path, post ordering or authenticated scope as a cosmetic fix. The two sidebar Views entries were re-observed but are outside the user's cramped project editing concern.

## Editing

`ProjectDetails` (`frontend/src/main.tsx` line 159) keeps name/description/state drafts, saves only through `projectUpdate`, updates parent project on success, and archives only behind its existing confirm dialog. The fix replaces the accidental shared absolute `.modal` class with in-flow `.project-editor ui-card`; draft fields sync when fresh project data arrives, Save changes is disabled when unchanged/blank/busy, Discard changes restores last persisted values, and save errors remain visible without discarding drafts. `frontend/src/styles.css` after the Pulse rules defines a full-width flow card, 130px description area, field/action spacing, a separate archive region and narrow one-column layout. A second correction moves State and Save/Discard into full-width grid rows so controls cannot squeeze into a side column. No new backend contract or external Linear mutation. Missing project description remains an empty editable textarea; long content wraps and can be resized. Archive remains confirm-only, never grouped with Save.


## Pulse

No independent cosmetic Pulse defect was proven. Existing `frontend/src/main.tsx` lines 71–94 and `styles.css` lines 209 onward still render project-update cards; isolated fixture t4 showed Recent/Older grouping and no horizontal overflow. The publication composer is separately tracked under the ongoing dogfood task. Rather than edit feed data or styling speculatively, this visual pass leaves Pulse implementation unchanged. Loading/empty/error and long body wrapping remain as described in `docs/pulse-parity.md`; actual composition and Linear dark-mode parity remain unverified.


## Verification

At authenticated t1 `/workspace/project/bb8dab20-52fb-4dcd-a14b-86db7238a3be`, 1264×1258, the form now starts below the project heading (x≈295, y≈269, width≈919) instead of overlapping it (previously x≈347,y≈151,width570). Description textarea grew from ≈54px to 130px; State and action row no longer share a narrow grid column, and Archive is separately framed. Changing Name to a draft enabled Save/Discard without changing heading; Discard restored the persisted name and disabled Save. An authorized local description change was saved once; status read “Project saved.” and both header/textarea retained the suffix after reload. At 390×844 the form was ≈351px wide, textarea 130px, both actions visible and no horizontal overflow. Focusing Name exposed a 2px visible outline. Two previously created project issues remained visible. Compared with read-only Linear project overview, Hoja is now in-flow but still has a conventional form rather than Linear's direct field editing/properties sidebar. External Linear t2 was not mutated.

Pulse fixture t4 at `/workspace/pulse/all` still rendered 24 posts, Recent/Older sections and no horizontal overflow at 1264px or 390px; no Pulse visual code changed. Original local Pulse remains an honest empty state pending dogfood publication. Browser error/console captures on t1 were empty; sampled GraphQL requests returned 200, the project route served HTML 200, and `/ready` returned ready. Forced failed save and visual keyboard traversal across every control were not exercised. No unit tests were added or run.


## Result

Fixed the observed cramped, overlapping project editor with an in-flow responsive card, readable textarea, explicit Save/Discard draft behavior, and separated Archive confirmation. This change is `frontend/src/main.tsx` line 159 plus `frontend/src/styles.css` lines 254–279, while the ongoing dogfood backend and issue changes remain untouched. No independent Pulse visual defect was observed; the publishing composer remains separate ongoing work. Frontend build, `git diff --check`, headed-browser edit/discard/save/reload/mobile checks and route readiness passed. The project editor is usable, not 1:1 with Linear's inline editing. No commit/tag/release was made; version was reconciled at 0.15.0 with the ongoing dogfood publication work.

