<!--
	"Start here": a new admin's first steps, one per area their grants open,
	each ticked from the admin log once they've done it (/api/admin/onboarding/).
	Shown on the dashboard until every step is done or they hide it. A super
	admin gets no steps, so sees nothing.
-->
<script lang="ts">
	import { getOnboarding, type OnboardingStep } from '$lib/library-admin';
	import { onMount } from 'svelte';

	const HIDE_KEY = 'ochorus:admin:start-here-hidden';

	let steps = $state<OnboardingStep[]>([]);
	let hidden = $state(false);

	onMount(async () => {
		try {
			hidden = localStorage.getItem(HIDE_KEY) === '1';
		} catch {
			/* storage blocked: show the card */
		}
		if (hidden) return;
		try {
			steps = (await getOnboarding()).steps;
		} catch {
			steps = []; // an extra, never a reason for the dashboard to fail
		}
	});

	const done = $derived(steps.filter((s) => s.done).length);
	const show = $derived(!hidden && steps.length > 0 && done < steps.length);

	function hide() {
		hidden = true;
		try {
			localStorage.setItem(HIDE_KEY, '1');
		} catch {
			/* fine: hidden for this visit */
		}
	}
</script>

{#if show}
	<section
		class="mb-8 rounded-card border border-accent-soft-border bg-accent-soft p-5"
		aria-labelledby="start-here"
	>
		<div class="mb-1 flex flex-wrap items-baseline justify-between gap-3">
			<h2 id="start-here" class="text-h3">Start here</h2>
			<span class="text-small text-muted">{done} of {steps.length} done</span>
		</div>
		<p class="mb-4 text-small text-muted">
			A few first steps for your role. Each one ticks itself once you've done it.
			<a href="/admin/help" class="text-accent hover:underline">Help &amp; roles</a> explains what your
			access covers and has the Admin Manual.
		</p>
		<ol class="space-y-3">
			{#each steps as s (s.key)}
				<li class="flex items-start gap-3">
					<span
						class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-micro font-semibold {s.done
							? 'border-accent bg-accent text-white'
							: 'border-border-strong bg-surface text-muted'}"
						aria-hidden="true"
					>
						{s.done ? '✓' : ''}
					</span>
					<span class="min-w-0">
						<a
							href={s.href}
							class="font-semibold hover:underline {s.done
								? 'text-muted line-through'
								: 'text-text'}"
						>
							{s.title}
						</a>
						<span class="sr-only">{s.done ? '(done)' : '(not done yet)'}</span>
						<span class="block text-small text-muted">{s.why}</span>
					</span>
				</li>
			{/each}
		</ol>
		<button type="button" onclick={hide} class="mt-4 text-small text-muted hover:text-text">
			Hide this
		</button>
	</section>
{/if}
