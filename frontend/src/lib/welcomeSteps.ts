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
