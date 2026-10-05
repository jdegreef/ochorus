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
 * The band's button carries the arm it shows as its sign-up source
 * (`$lib/signupSource`), so the arm the reader clicked is the one Django
 * records create-only against the new account.
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

function isArm(value: string | null): value is FirstVisitArm {
	return value !== null && (FIRST_VISIT_ARMS as readonly string[]).includes(value);
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
 * The band to show now: `progress` targeting wins whenever there is local
 * reading; otherwise the sticky random arm.
 */
export function chooseVariant(hasProgress: boolean, pick: () => number = Math.random): SignupVariant {
	return hasProgress ? 'progress' : firstVisitArm(pick);
}
