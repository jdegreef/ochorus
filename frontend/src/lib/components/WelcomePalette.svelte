<script lang="ts">
	import { onMount } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { theme } from '$lib/theme.svelte';
	import { welcome } from '$lib/welcome.svelte';
	import PalettePicker from '$lib/components/PalettePicker.svelte';

	/**
	 * A new reader's first choice: the colours of their library. Shown at the
	 * top of the home dashboard after sign-up (welcome.svelte.ts says when),
	 * once. Picking applies at once to the whole page around the card — the
	 * preview is the app itself — and both buttons put it away for good; the
	 * same choice lives on in Settings → Appearance.
	 */
	const t = i18n.t;
	const BRIGHTNESS = [
		{ v: 'light', k: 'settings.themeLight' },
		{ v: 'sepia', k: 'settings.themeSepia' },
		{ v: 'dark', k: 'settings.themeDark' }
	] as const;

	onMount(() => welcome.init());
</script>

{#if welcome.pending}
	<section class="page-col px-5 pt-8" aria-labelledby="welcome-palette-heading">
		<div class="rounded-card border border-border bg-surface p-6 sm:p-8">
			<p class="eyebrow text-gold">{t('welcome.eyebrow')}</p>
			<h2 id="welcome-palette-heading" class="font-display mt-2 text-h2">{t('welcome.paletteTitle')}</h2>
			<p class="mt-1 mb-5 text-small text-muted">{t('welcome.paletteSub')}</p>

			<PalettePicker label={t('welcome.paletteTitle')} />

			<div class="mt-5 flex flex-wrap items-center gap-3">
				<span class="text-small font-semibold">{t('welcome.brightness')}</span>
				<div class="seg">
					{#each BRIGHTNESS as o (o.v)}
						<button class:active={theme.current === o.v} onclick={() => theme.set(o.v)}>{t(o.k)}</button>
					{/each}
				</div>
			</div>

			<div class="mt-6 flex flex-wrap gap-3">
				<button class="btn btn-primary" onclick={() => welcome.done()}>{t('welcome.done')}</button>
				<button class="btn btn-ghost" onclick={() => welcome.done()}>{t('welcome.skip')}</button>
			</div>
		</div>
	</section>
{/if}
