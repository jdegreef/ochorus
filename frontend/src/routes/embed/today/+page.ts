// Client-only, like /today: "today" is the reader's local date (see
// $lib/dailyDate), so a prerendered page would freeze on the day the site last
// deployed. The church widget's page ($lib/embed).
export const prerender = false;
export const ssr = false;
