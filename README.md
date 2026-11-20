# db_project
# Car Tracking — Phase III GitHub Issues

Due: **December 3, 2026**. Course: CIIC 4060 / ICOM 5016, UPR Mayagüez, Fall 2026.

These issues extend the existing Phase II project to implement **Phase III — Web Interface**, which is the specification supplied in the request. They are prepared issue drafts, not published GitHub issues. No repository or implementation was inspected; confirm existing work before assigning tasks. IDs CT3-01 through CT3-17 are planning identifiers, not GitHub issue numbers.

## Source references and grading

**S1:** Department of Electrical and Computer Engineering, UPR Mayagüez, *Term Project – Car Tracking, Phase III – Web Interface*, due December 3, 2026; text supplied by the user. References below use its section names and numbered requirements because no document URL or page numbers were supplied.

**S2:** Phase II API specification, referenced by S1 but not supplied here. Retrieve its actual endpoint definitions before changing API behavior. No route names, response schemas, bbox boundary semantics, or pagination contracts in S2 are assumed in these issues.

**S3:** Phase I dataset/schema and project requirements, referenced by S1 but not supplied here. Use them to verify production data provenance, schema, and consistency.

The rubric starts at **100 points** and applies cumulative deductions. It does **not** allocate points to individual features. Repeated references to a category below refer to the same category cap; they must not be added together as separate issue values.

| Rubric category | Stated grading exposure |
|---|---|
| A — Functional Requirements | Up to 50 points deducted across functionality |
| B — Graphical User Interface Quality | Up to 20 points deducted across UI quality |
| C — Code Organization, Architecture, and Data Consistency | Up to 25 points deducted across architecture and data consistency |
| E — Individual Oral Code-Understanding Questions | Up to 5 points deducted per student |
| D — Major penalties | Additional and cumulative: −100 for any required component missing cloud deployment; −100 for frontend database bypass; −100 for ORM use; −100 for failure of the live cloud redeployment challenge; −90 for matplotlib; −50 for missing Handler/DAO organization |

S1 also states individual zero/failure consequences for absence and zero recorded contribution, an invalid evaluation if screen sharing is missing, one oral attempt, and no AI coding agents during the oral exam. These are mandatory conditions, not invented point allocations.

Priority meanings: **P0** = major-penalty or evaluation blocker; **P1** = required functionality, consistency, or delivery; **P2** = dedicated UI refinement. Every issue remains required. Estimates are rough engineering effort assuming the Phase II API and Phase I database already exist; they are not grade weights or promised completion times.

## Issue index

| ID | Priority | Issue title | Main grading exposure |
|---|---|---|---|
| CT3-01 | P0 | Enforce API-only Streamlit architecture and Handler/DAO boundaries | D: −100 bypass/ORM; −50 Handler/DAO; C |
| CT3-02 | P0 | Verify cloud PostgreSQL 17/PostGIS and valid Phase I production data | D: −100 missing cloud component; C |
| CT3-03 | P0 | Deploy the FastAPI service against the cloud database | D: −100 missing cloud component |
| CT3-04 | P0 | Create and deploy the separate Streamlit web_application project | D: −100 missing cloud component; C |
| CT3-05 | P1 | Implement cloud user registration through the REST API | A, B, C |
| CT3-06 | P1 | Implement login and protect all application views | A, B, C |
| CT3-07 | P1 | Display parking areas with selection, bbox filtering, and a matching table | A, B, C |
| CT3-08 | P1 | Display road segments with selection, bbox filtering, and a matching table | A, B, C |
| CT3-09 | P1 | Display each vehicle's latest ping with correct bbox semantics | A, B, C |
| CT3-10 | P1 | Display vehicle breadcrumb trails and associated trip IDs | A, B, C |
| CT3-11 | P0 | Display daily ping counts without matplotlib | D: −90 matplotlib; A, C |
| CT3-12 | P1 | Preserve Phase II endpoint contracts and document API additions | A, C |
| CT3-13 | P2 | Polish navigation, map usability, validation, and feedback | B: up to 20 total |
| CT3-14 | P1 | Verify all acceptance criteria against the live cloud application | A, C; verification of D blockers |
| CT3-15 | P1 | Complete README, database changelog, and repository deliverables | C; mandatory deliverables |
| CT3-16 | P0 | Rehearse live changes and cloud redeployment without AI assistance | D: −100 failed challenge |
| CT3-17 | P0 | Prepare every member for the single oral exam and verify contributions | E; individual zero/failure conditions |



database course
