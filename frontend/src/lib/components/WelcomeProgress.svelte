<script lang="ts">
	import { onMount } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { auth } from '$lib/auth.svelte';
	import { track } from '$lib/analytics';
	import { welcome } from '$lib/welcome.svelte';
	import { hasStarted, readerActivity } from '$lib/readerActivity';
	import {
		STEP_COPY,
		WELCOME_EVENT,
		welcomeEventProps,
		welcomeSteps,
		type WelcomeAction
	} from '$lib/welcomeSteps';
	import Icon from '$lib/components/Icon.svelte';

	/**
	 * "Finish getting started": the /welcome checklist carried onto the home
	 * dashboard after the reader has seen the page, so the four first steps stay
	 * one tap away until they're done. Only for an account that came through the
	 * welcome on this device (`welcome.inProgress`, never an existing reader),
	 * and not while OnboardingCard is up — a reader with no activity at all is
	 * already being pointed at /welcome by that card. It puts itself away for
	 * good when the checklist is complete or the reader hides it.
	 *
	 * Client-only, like OnboardingCard: the stores are localStorage, re-read on
	 * mount and on the `ochorus:sync` a sign-in merge fires.
	 */
	const t = i18n.t;

	let ticks = $state(0);
	onMount(() => {
		const bump = () => ticks++;
		bump();
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	const view = $derived.by(() => {
		if (!ticks) return null;
		const activity = readerActivity(getLang());
		const checklist = welcomeSteps({ signedIn: !!auth.user, ...activity });
		return { started: hasStarted(activity), ...checklist };
	});
	const complete = $derived(!!view && view.done === view.steps.length);
	const next = $derived(view?.steps.find((s) => !s.done) ?? null);

	// Everything done: the card has nothing left to offer, ever.
	$effect(() => {
		if (welcome.inProgress && complete) welcome.finishProgress();
	});

	const report = (action: WelcomeAction) => track(WELCOME_EVENT, welcomeEventProps(action, getLang()));

	function hide() {
		report('hide progress');
		welcome.finishProgress();
	}
</script>

{#if welcome.inProgress && view?.started && !complete && next}
	<section class="page-col px-5 pt-8" aria-labelledby="welcome-progress-heading">
		<div class="progress rounded-card border border-border bg-surface">
			<div class="min-w-0 grow">
				<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
					<h2 id="welcome-progress-heading" class="font-display text-h3">
						{t('welcomePage.progressTitle')}
					</h2>
					<span class="count text-small">
						{t('welcomePage.stepsCount')
							.replace('%n%', String(view.done))
							.replace('%m%', String(view.steps.length))}
					</span>
				</div>
				<div class="bar mt-2" aria-hidden="true">
					<i style="width: {(view.done / view.steps.length) * 100}%"></i>
				</div>
				<p class="mt-2 text-small text-muted">
					{t('welcomePage.progressNext').replace('%step%', t(STEP_COPY[next.key].title))}
				</p>
			</div>
			<div class="flex shrink-0 items-center gap-2">
				<a
					class="btn btn-primary btn-sm hover:no-underline"
					href={localizeHref('/welcome')}
					onclick={() => report('resume from home')}>{t('welcomePage.progressContinue')}</a
				>
				<button class="btn btn-ghost btn-icon" onclick={hide} aria-label={t('welcomePage.progressHide')}>
					<Icon name="close" size={16} />
				</button>
			</div>
		</div>
	</section>
{/if}

<style>
	.progress {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 1rem 1.5rem;
		padding: 1rem 1.25rem;
	}
	.bar {
		height: 4px;
		max-width: 20rem;
		border-radius: var(--radius-sm);
		background: var(--surface-2);
		overflow: hidden;
	}
	.bar i {
		display: block;
		height: 100%;
		background: var(--accent);
	}
</style>
