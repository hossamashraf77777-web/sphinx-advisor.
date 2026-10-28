# Official data goes here

This folder is intentionally empty. It is **git-ignored** (except this file), so real student
records never reach a public repository.

To switch the app to official data:

1. Put these three files in this folder (the exact names matter):
   - `courses.csv`
   - `student.json`
   - `regulations.json`
2. Start the app with the environment variable `SPHINX_DATA_MODE=official`.

If any file is missing, the app shows an error. It will **not** fall back to demo data.

## courses.csv

Columns (header row required): `code,title,credits,category,level,prerequisites,description`

- `prerequisites`: course codes separated by `;`. Leave empty for "no prerequisites".
  Write `UNKNOWN` if the official source does not say - the agent will then answer "needs verification".
- `credits` and `level` must be numbers. `description` is optional.

## student.json

```json
{"students": [{
  "student_id": "...", "name": "...", "program": "...", "admission_term": "...",
  "records": [{"course_code": "...", "grade": "...", "term": "...", "term_order": 1}]
}]}
```

`term_order` is a number that sorts terms chronologically (1 = first term).

## regulations.json

Use the same keys as `data/demo/regulations.json`. Set a key to `null` when the regulation
has not been provided; never fill in a guess. Set `"is_demo": false` in `meta` and replace
`label` with the source document (for example its title and date).

- `grade_scale`: grade -> grade points.
- `min_passing_points`: lowest grade points that count as a pass.
- `retake_policy`: `"all"`, `"latest"` or `"best"` (how repeated attempts count in the GPA), or `null`.
- `max_credits_per_semester`: number or `null`.
- `min_cgpa_good_standing`: number or `null`.
- `graduation.total_credits`, `graduation.required_categories` (every course in these
  categories is mandatory), `graduation.category_credits` (credits needed from a category,
  for example electives).
