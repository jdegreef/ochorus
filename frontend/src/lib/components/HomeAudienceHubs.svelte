<script lang="ts">
	import type { HubAudience } from '$lib/library-public';
	import { AUDIENCE_HUBS } from '$lib/audienceHub';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	/**
	 * The home page's way in to the young-reader hubs — one row card each,
	 * shown only for the hubs this language has something in (the snapshot's
	 * `audiences`, so a locale never links to an empty hub). Renders nothing
	 * when neither has.
	 */
	let { audiences }: { audiences: HubAudience[] } = $props();
	const t = i18n.t;

	const hubs = $derived(AUDIENCE_HUBS.filter((h) => audiences.includes(h.audience)));
	const TAGLINE: Record<HubAudience, string> = {
		young_readers: 'audience.youngTagline',
		teens: 'audience.teensTagline'
	};
</script>

{#if hubs.length}
	<section class="page-col px-5 pt-14">
		<h2 class="text-h2 mb-6">{t('audience.homeHeading')}</h2>
		<div class="grid gap-4 sm:grid-cols-2">
			{#each hubs as h (h.path)}
				<a
					href={localizeHref(h.path)}
					class="card-tint flex gap-4 rounded-card border border-border bg-surface p-5"
				>
					<span
						class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent"
						aria-hidden="true"
					>
						<Icon name={h.icon} size={20} />
					</span>
					<span class="min-w-0">
						<h3 class="text-h3 mb-1 text-text">{t(h.labelKey)} <Arrow /></h3>
						<span class="block text-small text-muted">{t(TAGLINE[h.audience])}</span>
					</span>
				</a>
			{/each}
		</div>
	</section>
{/if}
