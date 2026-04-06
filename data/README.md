# Data — Provenance and Structure

## Source

**Recfluence** by Mark Ledwich & Anna Zaitsev
- Repository: https://github.com/markledwich2/Recfluence
- License: MIT
- Data generated: 2023-02-18
- Download link: https://ytapp.blob.core.windows.net/public/results/recfluence_shared_data.zip
- Date accessed: 2026-03-29

## How to obtain the data

1. Download `recfluence_shared_data.zip` from the link above.
2. Unzip and copy the following CSV files into this `data/` directory:
   - `vis_channel_stats.csv`
   - `vis_channel_recs2.csv`
3. The CSV files are excluded from Git via `.gitignore`. This README is the only
   tracked file in `data/`.

## Files

### vis_channel_stats.csv — Node data (7,079 rows)
Each row is one YouTube channel. This is the **node table** for graph construction.

| Column | Type | Description |
|--------|------|-------------|
| `CHANNEL_ID` | string | Unique YouTube channel identifier |
| `CHANNEL_TITLE` | string | Human-readable channel name |
| `LR` | string (L/C/R) | Left, Center, or Right classification (majority of 3+ reviewers) |
| `RELEVANCE` | float 0–1 | Proportion of content relevant to US politics |
| `SUBS` | integer | Subscriber count |
| `CHANNEL_VIEWS` | integer | Total lifetime views |
| `CHANNEL_VIDEO_VIEWS` | integer | Total video views |
| `RELEVANT_IMPRESSIONS_DAILY` | float | Estimated daily outgoing recommendation impressions |
| `RELEVANT_IMPRESSIONS_IN_DAILY` | float | Estimated daily incoming recommendation impressions |
| `MEDIA` | string | Media type (YouTube, Mainstream Media) |
| `COUNTRY` | string | Channel country |
| `FROM_DATE` / `TO_DATE` | datetime | Data collection period for the channel |

### vis_channel_recs2.csv — Edge data (401,384 rows)
Each row is a directed recommendation from one channel to another. This is the **edge table**.

| Column | Type | Description |
|--------|------|-------------|
| `FROM_CHANNEL_ID` | string | Source channel (YouTube recommended from here...) |
| `TO_CHANNEL_ID` | string | Target channel (...to here) |
| `RELEVANT_IMPRESSIONS_DAILY` | float | Estimated daily impressions for this recommendation |
| `PERCENT_OF_CHANNEL_RECS` | float | What fraction of the source channel's total recommendations this edge represents |

## Data quality notes

- **100% coverage:** Every channel in the edge table has a matching entry in the node table.
- **Self-loops:** 6,942 edges where a channel recommends itself. These should be filtered during graph construction.
- **LR distribution:** R=4,034, C=2,120, L=925. The rightward skew may reflect the YouTube political landscape or collection methodology.
- **Logged-off data:** Recommendations were scraped without user login, reflecting YouTube's default algorithm rather than personalized results.
