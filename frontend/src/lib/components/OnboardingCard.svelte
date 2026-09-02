<script lang="ts">
	import { onMount } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { allProgress } from '$lib/progress';
	import { favorites } from '$lib/favorites.svelte';
	import { planProgress } from '$lib/planProgress.svelte';

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
		return (
			allProgress().length === 0 &&
			favorites.count() === 0 &&
			planProgress.started().length === 0
		);
	});
</script>

{#if isNew}
	<section class="page-col px-5 pt-8">
		<EmptyState message={t('settings.activityEmpty')}>
			{#snippet action()}
				<a href={localizeHref('/books')} class="btn btn-primary hover:no-underline">
					{t('home.browseLibrary')}
				</a>
			{/snippet}
		</EmptyState>
	</section>
{/if}
