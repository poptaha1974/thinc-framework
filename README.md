# thinc-framework
THINC Framework v2.1 - Reality Validation Marketing Intelligence System

## Notion daily worklog writer

Use `/home/runner/work/thinc-framework/thinc-framework/scripts/notion_worklog_writer.py` to add a daily log entry to Notion.

### Safe run

1. Export credentials in your shell (never hardcode or echo tokens):
   - `NOTION_TOKEN`
   - one target id: `NOTION_PAGE_ID` or `NOTION_DATABASE_ID`
2. Run:
   - `python /home/runner/work/thinc-framework/thinc-framework/scripts/notion_worklog_writer.py`
3. Optional structured items (repeat `--item`):
   - `python /home/runner/work/thinc-framework/thinc-framework/scripts/notion_worklog_writer.py --item "Finished task A" --item "Reviewed PR B"`

The script writes only to the Notion API and prints a minimal JSON success/error result without exposing secret values.
