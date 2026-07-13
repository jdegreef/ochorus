<script lang="ts">
	import { readerPrefs, type Leading, type Measure, type ReaderFont } from '$lib/readerPrefs.svelte';
	import { listen, RATES } from '$lib/listen.svelte';
	import { i18n } from '$lib/i18n.svelte';

	let open = $state(false);
	let wrap = $state<HTMLDivElement>();
	const t = i18n.t;

	// Load the device voice list when the panel opens (async on some browsers).
	$effect(() => {
		if (open) listen.init();
	});

	const LEADINGS: { v: Leading; k: string }[] = [
		{ v: 'compact', k: 'spacing.compact' },
		{ v: 'normal', k: 'spacing.normal' },
		{ v: 'relaxed', k: 'spacing.relaxed' }
	];
	const MEASURES: { v: Measure; k: string }[] = [
		{ v: 'narrow', k: 'width.narrow' },
		{ v: 'normal', k: 'width.normal' },
		{ v: 'wide', k: 'width.wide' }
	];
	const FONTS: { v: ReaderFont; k: string }[] = [
		{ v: 'serif', k: 'font.serif' },
		{ v: 'sans', k: 'font.sans' },
		{ v: 'dyslexic', k: 'font.dyslexic' }
	];

	function onWindowClick(e: MouseEvent) {
		if (open && wrap && !wrap.contains(e.target as Node)) open = false;
	}
	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') open = false;
	}
</script>

<svelte:window onclick={onWindowClick} onkeydown={onKey} />

<div class="relative" bind:this={wrap}>
	<button
		class="btn btn-ghost !px-3 !py-1"
		onclick={() => (open = !open)}
		aria-haspopup="dialog"
		aria-expanded={open}
		aria-label={t('reader.textSettings')}
	>
		<span style="font-family: var(--font-display)">A</span><span class="text-small">a</span>
	</button>

	{#if open}
		<div
			class="absolute right-0 z-30 mt-2 w-64 rounded-card border border-border bg-surface p-4 shadow-lg"
			role="dialog"
			aria-label={t('reader.textSettings')}
		>
			<!-- Font size -->
			<div class="mb-3 flex items-center justify-between">
				<span class="text-small font-semibold text-text">{t('reader.size')}</span>
				<div class="flex items-center gap-1">
					<button
						class="btn btn-ghost !px-2.5 !py-1"
						onclick={() => readerPrefs.bumpScale(-0.1)}
						aria-label="Smaller text">A−</button
					>
					<span class="w-10 text-center text-small text-muted"
						>{Math.round(readerPrefs.scale * 100)}%</span
					>
					<button
						class="btn btn-ghost !px-2.5 !py-1 !text-base"
						onclick={() => readerPrefs.bumpScale(0.1)}
						aria-label="Larger text">A+</button
					>
				</div>
			</div>

			<!-- Leading -->
			<div class="mb-3">
				<span class="mb-1.5 block text-small font-semibold text-text">{t('reader.spacing')}</span>
				<div class="grid grid-cols-3 gap-1">
					{#each LEADINGS as o (o.v)}
						<button
							class="rounded-sm border px-2 py-1.5 text-[0.8rem]"
							class:border-accent={readerPrefs.leading === o.v}
							class:text-accent={readerPrefs.leading === o.v}
							class:border-border={readerPrefs.leading !== o.v}
							class:text-muted={readerPrefs.leading !== o.v}
							onclick={() => readerPrefs.setLeading(o.v)}
							aria-pressed={readerPrefs.leading === o.v}>{t(o.k)}</button
						>
					{/each}
				</div>
			</div>

			<!-- Measure / width -->
			<div class="mb-3">
				<span class="mb-1.5 block text-small font-semibold text-text">{t('reader.width')}</span>
				<div class="grid grid-cols-3 gap-1">
					{#each MEASURES as o (o.v)}
						<button
							class="rounded-sm border px-2 py-1.5 text-[0.8rem]"
							class:border-accent={readerPrefs.measure === o.v}
							class:text-accent={readerPrefs.measure === o.v}
							class:border-border={readerPrefs.measure !== o.v}
							class:text-muted={readerPrefs.measure !== o.v}
							onclick={() => readerPrefs.setMeasure(o.v)}
							aria-pressed={readerPrefs.measure === o.v}>{t(o.k)}</button
						>
					{/each}
				</div>
			</div>

			<!-- Typeface -->
			<div>
				<span class="mb-1.5 block text-small font-semibold text-text">{t('reader.typeface')}</span>
				<div class="grid grid-cols-3 gap-1">
					{#each FONTS as o (o.v)}
						<button
							class="rounded-sm border px-2 py-1.5 text-[0.8rem]"
							class:border-accent={readerPrefs.font === o.v}
							class:text-accent={readerPrefs.font === o.v}
							class:border-border={readerPrefs.font !== o.v}
							class:text-muted={readerPrefs.font !== o.v}
							onclick={() => readerPrefs.setFont(o.v)}
							aria-pressed={readerPrefs.font === o.v}>{t(o.k)}</button
						>
					{/each}
				</div>
			</div>

			<!-- Listening (voice + speed): device Text-to-Speech settings, applied to
			     chapters, sermons and biographies alike. -->
			{#if listen.supported}
				<div class="mt-3 border-t border-border pt-3">
					<span class="mb-1.5 block text-small font-semibold text-text">{t('reader.listen')}</span>

					{#if listen.voices.length}
						<select
							class="mb-2 w-full rounded-sm border border-border bg-surface px-2 py-1.5 text-small text-text"
							value={listen.voiceURI}
							onchange={(e) => listen.setVoice(e.currentTarget.value)}
							aria-label={t('reader.voice')}
						>
							<option value="">{t('reader.voice')}</option>
							{#each listen.voicesByLang as group (group.lang)}
								<optgroup label={group.lang}>
									{#each group.voices as voice (voice.voiceURI)}
										<option value={voice.voiceURI}>{voice.name}</option>
									{/each}
								</optgroup>
							{/each}
						</select>
					{/if}

					<div class="flex items-center gap-2">
						<div class="grid flex-1 grid-cols-5 gap-1">
							{#each RATES as r (r)}
								<button
									class="rounded-sm border px-1 py-1.5 text-[0.8rem] tabular-nums"
									class:border-accent={listen.rate === r}
									class:text-accent={listen.rate === r}
									class:border-border={listen.rate !== r}
									class:text-muted={listen.rate !== r}
									onclick={() => listen.setRate(r)}
									aria-label={t('reader.speed')}
									aria-pressed={listen.rate === r}>{r}×</button
								>
							{/each}
						</div>
						<button
							class="btn btn-ghost !px-2.5 !py-1.5"
							onclick={() => listen.preview(t('bios.tagline'))}
							aria-label={t('reader.listen')}
							title={t('reader.listen')}>▶</button
						>
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>
