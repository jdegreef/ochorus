/**
 * Accept a `?redirect=` value only when it is a same-origin path.
 *
 * The login page sends the reader wherever this points once a session exists, so
 * the value is fully attacker-controlled on the one page where a phishing
 * landing is worth the most. `goto` currently rejects cross-origin URLs, which
 * makes an off-site value a *broken sign-in* rather than an open redirect — but
 * that is a property of SvelteKit's navigation, not a decision this app made,
 * and it stops holding the moment anyone swaps in `location.assign`.
 *
 * Returns the path to navigate to, or `null` to fall back to home.
 */
export function safeRedirect(raw: string | null | undefined): string | null {
	if (!raw) return null;

	// Must be rooted. This alone rejects "https://evil.test", "evil.test" and
	// "javascript:alert(1)".
	if (!raw.startsWith('/')) return null;

	// "//evil.test" is protocol-relative: it inherits the page's scheme and goes
	// off-site. "/\evil.test" is treated the same way by several URL parsers
	// (browsers normalise the backslash to a slash), so exclude both forms.
	if (raw.startsWith('//') || raw.startsWith('/\\')) return null;

	// Browsers strip tab, newline and CR out of a URL before parsing it, so
	// "/\t/evil.test" reaches the parser as "//evil.test" and would slip past the
	// prefix checks above. Reject any C0 control or DEL outright.
	// eslint-disable-next-line no-control-regex
	if (/[\u0000-\u001f\u007f]/.test(raw)) return null;

	return raw;
}
