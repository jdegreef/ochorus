// Prerenders to rss/index.html, which the static host serves natively for
// /rss/ — no Render rewrite needed ($lib/canonicalRedirect isSlashedPath).
// Shipped first as a no-slash route (#5080): /rss.html was built, but /rss
// matched no rewrite and served the empty app shell.
export const trailingSlash = 'always';
