/**
 * The /welcome page's first-steps checklist. Each step is ticked from what the
 * reader has actually done on this device (their reading data merges into the
 * account on sign-in), never from a box they clicked — so the list answers
 * "have I tried this yet?" truthfully and finishes itself as they read.
 */
import type { ReaderActivity } from './readerActivity';

export type WelcomeStepKey = 'account' | 'read' | 'save' | 'mark';

export interface WelcomeStep {
	key: WelcomeStepKey;
	done: boolean;
}

export interface WelcomeActivity extends ReaderActivity {
	signedIn: boolean;
}

export function welcomeSteps(a: WelcomeActivity): { steps: WelcomeStep[]; done: number } {
	const steps: WelcomeStep[] = [
		{ key: 'account', done: a.signedIn },
		{ key: 'read', done: a.read },
		{ key: 'save', done: a.saved },
		{ key: 'mark', done: a.marked }
	];
	return { steps, done: steps.filter((s) => s.done).length };
}

/**
 * What the /welcome page reports to analytics: one Plausible event, "Welcome
 * page", whose `action` says what the new reader did there — so the shape of a
 * first visit (did they read? start the plan? leave?) can be read off one
 * breakdown. Short labels only, plus the UI language; never an id or a URL.
 */
export type WelcomeAction =
	| 'viewed'
	| 'read first chapter'
	| 'follow plan'
	| 'browse library'
	| `step: ${WelcomeStepKey}`
	| `goal: ${number}`
	| 'go home';

export const WELCOME_EVENT = 'Welcome page';

export function welcomeEventProps(action: WelcomeAction, lang: string): Record<string, string> {
	return { action, lang };
}
