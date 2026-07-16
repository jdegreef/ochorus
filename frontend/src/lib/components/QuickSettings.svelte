<script lang="ts">
	import { onMount } from 'svelte';
	import { theme } from '$lib/theme.svelte';
	import { readerPrefs, type Measure } from '$lib/readerPrefs.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import Icon from '$lib/components/Icon.svelte';

	// Take Root's quick-settings popover: the gear opens a small menu with a
	// theme toggle and a reading-width stepper — no navigation to the Settings
	// page. Both controls write the same device-local prefs the Settings page and
	// reader use (readerPrefs.measure drives --reading-measure everywhere), so a
	// width change resizes the reading column live.
	const t = i18n.t;
	let open = $state(false);
	let root = $state<HTMLDivElement>();

	onMount(() => readerPrefs.init());

	const ORDER: Measure[] = ['narrow', 'normal', 'wide'];
	const idx = $derived(ORDER.indexOf(readerPrefs.measure));
	const step = (d: number) => {
		const next = ORDER[idx + d];
		if (next) readerPrefs.setMeasure(next);
	};

	function onWindowClick(e: MouseEvent) {
		if (open && root && !root.contains(e.target as Node)) open = false;
	}
</script>

<svelte:window
	onclick={onWindowClick}
	onkeydown={(e) => {
		if (e.key === 'Escape') open = false;
	}}
/>

<div class="prefs" bind:this={root}>
	<button
		class="prefs-btn"
		aria-haspopup="menu"
		aria-expanded={open}
		aria-label={t('settings.title')}
		title={t('settings.title')}
		onclick={(e) => {
			e.stopPropagation();
			open = !open;
		}}
	>
		<Icon name="gear" size={19} />
	</button>
	{#if open}
		<div class="account-menu prefs-menu" role="menu">
			<div class="prefs-row">
				<span class="prefs-label">{t('nav.theme')}</span>
				<button
					class="prefs-toggle"
					onclick={() => theme.toggle()}
					aria-label={theme.current === 'dark' ? t('settings.themeLight') : t('settings.themeDark')}
					title={theme.current === 'dark' ? t('settings.themeLight') : t('settings.themeDark')}
				>
					<Icon name={theme.current === 'dark' ? 'moon' : 'sun'} size={17} />
				</button>
			</div>
			<div class="prefs-row">
				<span class="prefs-label">{t('nav.readingWidth')}</span>
				<div class="widthctl">
					<button
						onclick={() => step(-1)}
						disabled={idx <= 0}
						aria-label={t('a11y.narrower')}
						title={t('a11y.narrower')}
					>
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
							<path d="M3 12h6" /><path d="M6 9l3 3-3 3" />
							<path d="M21 12h-6" /><path d="M18 9l-3 3 3 3" />
						</svg>
					</button>
					<button
						onclick={() => step(1)}
						disabled={idx >= ORDER.length - 1}
						aria-label={t('a11y.wider')}
						title={t('a11y.wider')}
					>
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
							<path d="M9 12H3" /><path d="M6 9l-3 3 3 3" />
							<path d="M15 12h6" /><path d="M18 9l3 3-3 3" />
						</svg>
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
