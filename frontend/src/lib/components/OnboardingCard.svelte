<script lang="ts">
	import { onMount } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { hasStarted, readerActivity } from '$lib/readerActivity';

	/**
	 * The signed-in dashboard's welcome for a reader with nothing yet — no reading,
	 * no saved works, no started plan. Rather than a page of empty self-hiding
	 * blocks, it gives them one clear next step. It self-hides the instant there's
	 * any activity, so it only ever shows once.
	 *
	 * Client-only (prerendered page): read localStorage on mount and re-read on
	 * the ochorus:sync a sign-in merge fires — a returning reader signing in on a
	 * new device shouldn't flash the onboarding before their data arrives.
	 */
	const t = i18n.t;

	let ticks = $state(0);
	onMount(() => {
		const bump = () => ticks++;
		bump();
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	const isNew = $derived.by(() => {
		void ticks;
		return !hasStarted(readerActivity(getLang()));
	});
</script>

{#if isNew}
	<section class="page-col px-5 pt-8">
		<EmptyState message={t('settings.activityEmpty')}>
			{#snippet action()}
				<div class="flex flex-wrap justify-center gap-3">
					<a href={localizeHref('/welcome')} class="btn btn-primary hover:no-underline">
						{t('welcomePage.getStarted')}
					</a>
					<a href={localizeHref('/books')} class="btn btn-ghost hover:no-underline">
						{t('home.browseLibrary')}
					</a>
				</div>
			{/snippet}
		</EmptyState>
	</section>
{/if}
