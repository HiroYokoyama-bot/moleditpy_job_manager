# Where your data lives

Persistent state is stored in `~/.moleditpy/job_manager/`, outside the plugin
folder so updates preserve it.

| File or folder | Purpose |
|---|---|
| `settings.json` | Hosts, presets, command templates and preferences; SSH passwords are not stored |
| `jobs.pmejdb` | Tracked jobs, retained across application restarts |
| `archived/jobs_<date>.pmejdb` | Job lists preserved by **Clear List** |
| `downloads/` | Fetched results |
| `api_token` / `api.json` | Local API secret and active endpoint |
| `web_monitor_token` | Persistent web-monitor access token, separate from the API secret |

New lists use SQLite for both internal storage and portable saved files.
**File → Save As...** offers `.pmejdb` and legacy JSON `.pmejbs`. Both extensions
are registered for File Import and drag-and-drop. Existing `jobs.pmejbs` or
`jobs.json` stays in its original format until **File → Convert to Job Database...**
is chosen. Conversion verifies the DB, archives the original bytes, then switches
tracking to the DB. Close other windows using the legacy list before converting.
Reading a file never converts or saves it.

Use Save As to share a consistent snapshot; no result files or host credentials
are embedded. SQLite uses rollback journaling, so a completed export is one file.
Concurrent editing is intended for local processes with working filesystem locks,
not a database opened from several computers through a sync folder.

Job lists can also be exported to CSV. Archived lists open read-only.
Result-folder imports also produce read-only lists. See
[job-list management](WORKFLOW.md#7-keeping-exporting-and-clearing-the-list)
and the [security model](SECURITY_MODEL.md) for storage and trust boundaries.
