# Scanner / Save Favourites connection recovery

The screenshot supplied during Sprint 35.1 showed Streamlit's frontend `DownloadButton`
throwing `Error: not connected to a server!`. That exception is generated in the browser
when the Streamlit websocket/server connection is already unavailable; Python cannot catch
that browser-side exception after disconnect.

## Atlas handling rule
- Do not interpret this as scanner-data or SQLite corruption.
- Preserve cached scan and paper-trading data.
- On reconnect, show concise recovery guidance rather than treating the event as a trading failure.
- Avoid destructive recovery actions.

## Integration note for the full scanner app
Where the scanner app owns `Save Favourites`, keep generation of the downloadable payload
separate from the button rendering and do not clear selection/cache on a failed rerun.
Use `paper_trading.resilience.safe_call` for server-side save/export preparation.
The browser itself must be reconnected by refreshing/restarting Streamlit if its websocket is gone.
