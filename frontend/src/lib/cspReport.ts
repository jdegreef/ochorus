/**
 * Report Content-Security-Policy violations to Sentry.
 *
 * The CSP ships as a <meta> (csp.config.js, `kit.csp` hash mode), and a <meta>
 * policy cannot carry `report-uri` / `report-to`. So until this, a violation was
 * silent: a new third-party host, a hash that drifted, or a Supabase ref that
 * changed would simply be refused in the reader's browser — and the first sign
 * would be "sign-in is broken". The browser still fires a
 * `securitypolicyviolation` event on the document for every refusal, which is
 * all this listens to.
 *
 * Kept cheap: browser extensions cause most violations on any site, and each
 * report here loads the Sentry SDK (~145 KB gzipped). So only violations that
 * look like OURS are sent — a blocked http(s) host, or inline/eval code whose
 * source is this origin — each distinct (directive, blocked host) once per page,
 * and at most MAX_REPORTS per page. The blocked URL is reduced to its origin:
 * a path or query could carry a reader's search text or a token.
 */

/** The SDK surface this needs. */
export interface MessageSdk {
	captureMessage(
		message: string,
		context?: { level?: 'warning'; tags?: Record<string, string> }
	): unknown;
}

export interface CspReportOptions {
	/** Loads (and initialises) the SDK. Called only when there is something to send. */
	load: () => Promise<MessageSdk>;
	/** This page's origin; inline violations from elsewhere are not ours. */
	origin: string;
	/** Where the event fires (a test passes its own). */
	target?: Pick<Document, 'addEventListener' | 'removeEventListener'>;
}

/** One page that violates in a loop must not send without bound. */
export const MAX_REPORTS = 5;

type Violation = Pick<
	SecurityPolicyViolationEvent,
	'effectiveDirective' | 'blockedURI' | 'sourceFile' | 'disposition'
>;

const EXTENSION = /^(chrome|moz|safari(-web)?|ms-browser)-extension:/;

/**
 * What to report for a violation, or null to ignore it: the directive and the
 * blocked origin (`inline` / `eval` for code with no URL).
 */
export function describeViolation(
	v: Violation,
	origin: string
): { directive: string; blocked: string } | null {
	if (v.disposition && v.disposition !== 'enforce') return null;
	const directive = v.effectiveDirective || 'unknown';
	const blocked = v.blockedURI || '';
	if (EXTENSION.test(blocked) || EXTENSION.test(v.sourceFile || '')) return null;
	if (blocked === 'inline' || blocked === 'eval') {
		// No URL to judge by, so judge by where the code ran from: an extension's
		// content script reports its own file or none at all.
		if (!v.sourceFile || !v.sourceFile.startsWith(origin)) return null;
		return { directive, blocked };
	}
	let url: URL;
	try {
		url = new URL(blocked);
	} catch {
		return null; // data:, blob:, about: and other schemes with nothing to fix
	}
	if (url.protocol !== 'https:' && url.protocol !== 'http:') return null;
	return { directive, blocked: url.origin };
}

/** Start listening. Returns a function that stops (tests; the app never does). */
export function armCspReports({ load, origin, target = document }: CspReportOptions): () => void {
	const seen = new Set<string>();

	const onViolation = (event: Event) => {
		if (seen.size >= MAX_REPORTS) return;
		const found = describeViolation(event as SecurityPolicyViolationEvent, origin);
		if (!found) return;
		const key = `${found.directive} ${found.blocked}`;
		if (seen.has(key)) return;
		seen.add(key);
		load()
			.then((sdk) =>
				sdk.captureMessage(`CSP blocked ${found.directive}: ${found.blocked}`, {
					level: 'warning',
					tags: { csp_directive: found.directive, csp_blocked: found.blocked }
				})
			)
			// Offline or blocked: nothing to report to, and a reporter must never throw.
			.catch(() => {});
	};

	target.addEventListener('securitypolicyviolation', onViolation);
	return () => target.removeEventListener('securitypolicyviolation', onViolation);
}
