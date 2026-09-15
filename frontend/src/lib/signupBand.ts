import { readJSON, writeJSON } from './persisted';

/**
 * Which logged-out sign-up band to show, and the attribution key that lets the
 * backend tell later which one earned an account.
 *
 * Two strategies run together, on purpose (see the design note in the PR):
 *
 *  - TARGETING. A reader who already has local reading is shown the
 *    progress-aware band (`progress`) — a different, warmer audience with the
 *    obvious reason to sign up (don't lose what you've read). It is not an A/B
 *    arm and is never compared head-to-head with the random ones.
 *  - A/B. Everyone else (a first-time visitor, no local progress) is assigned
 *    ONE of the three random arms, uniformly and STICKILY — the same visitor
 *    keeps their arm across visits, so returning doesn't reshuffle the band or
 *    pollute the counts. The even split is what makes raw signup counts fair to
 *    compare without an exposure denominator.
 *
 * The arm that is actually shown is stored as the attribution key; `auth`
 * attaches it to the Supabase sign-up metadata, and Django records it
 * create-only against the new account (accounts.authentication). So the value
 * the reader saw when they clicked "Create an account" is the value counted.
 *
 * Storage goes through `persisted` (browser-guarded, and it flags
 * `storageHealth` on write failure) — private mode / SSR / blocked storage all
 * degrade to a safe default, so attribution is best-effort by design.
 */

/** The four bands, and the single source of the variant type. Kept in step with
 *  backend `accounts.models.SIGNUP_VARIANTS`. */
export const SIGNUP_VARIANTS = ['keep', 'habit', 'library', 'progress'] as const satisfies string[];
export type SignupVariant = (typeof SIGNUP_VARIANTS)[number];

/** The random A/B arms shown to a first-time visitor (no local progress) — a
 *  subset of {@link SIGNUP_VARIANTS}, so dropping a variant there fails to
 *  compile here rather than drifting. */
export const FIRST_VISIT_ARMS = ['keep', 'habit', 'library'] as const satisfies readonly SignupVariant[];
type FirstVisitArm = (typeof FIRST_VISIT_ARMS)[number];

/** Sticky first-visit assignment: the same visitor keeps their arm across visits. */
const ARM_KEY = 'ochorus:signup_arm';
/** The arm actually shown last — what a sign-up is attributed to. */
const SHOWN_KEY = 'ochorus:signup_variant';

function isArm(value: string | null): value is FirstVisitArm {
	return value !== null && (FIRST_VISIT_ARMS as readonly string[]).includes(value);
}

function isVariant(value: string | null): value is SignupVariant {
	return value !== null && (SIGNUP_VARIANTS as readonly string[]).includes(value);
}

/**
 * The visitor's sticky random arm, assigning (and persisting) one on first call.
 * `pick` is injectable so tests are deterministic; it defaults to a uniform
 * 1-in-N draw. A stored value that is no longer a valid arm is re-drawn.
 */
export function firstVisitArm(pick: () => number = Math.random): FirstVisitArm {
	const stored = readJSON<string | null>(ARM_KEY, null);
	if (isArm(stored)) return stored;
	const arm = FIRST_VISIT_ARMS[Math.floor(pick() * FIRST_VISIT_ARMS.length)] ?? FIRST_VISIT_ARMS[0];
	writeJSON(ARM_KEY, arm);
	return arm;
}

/**
 * The band to show now, and — as a side effect — the attribution key for a
 * sign-up that follows. `progress` targeting wins whenever there is local
 * reading; otherwise the sticky random arm. Call this once where the band
 * renders; `auth` reads {@link shownVariant} at sign-up time.
 */
export function chooseVariant(hasProgress: boolean, pick: () => number = Math.random): SignupVariant {
	const variant: SignupVariant = hasProgress ? 'progress' : firstVisitArm(pick);
	writeJSON(SHOWN_KEY, variant);
	return variant;
}

/**
 * The band the visitor last saw, for attributing a sign-up — or `null` if they
 * never saw one (e.g. reached /login straight from the nav). `auth` forwards a
 * non-null value into the sign-up metadata; the backend drops anything that
 * isn't a known arm, so a stale/hand-edited value can't corrupt the analytics.
 */
export function shownVariant(): SignupVariant | null {
	const value = readJSON<string | null>(SHOWN_KEY, null);
	return isVariant(value) ? value : null;
}
