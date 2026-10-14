/**
 * Whether the site footer's own "Send feedback" link has scrolled into view
 * (or past it). SiteFooter sets it; FeedbackFab steps aside while it holds,
 * since the floating button would only duplicate that link — and float over
 * the footer's last rows to do it.
 */
export const footerFeedback = $state({ reached: false });
