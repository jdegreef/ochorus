<script lang="ts">
	import { listen, RATES } from '$lib/listen.svelte';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	// Cycle through the preset speeds on tap — quicker than a dropdown mid-listen.
	function cycleRate() {
		const i = RATES.indexOf(listen.rate as (typeof RATES)[number]);
		listen.setRate(RATES[(i + 1) % RATES.length]);
	}
</script>

{#if listen.status !== 'idle'}
	<div class="listen-bar" role="region" aria-label={t('reader.listen')}>
		<div class="mx-auto flex max-w-3xl items-center gap-2 px-4 py-2.5">
			<button
				class="btn btn-primary !rounded-full !px-3.5 !py-1.5"
				onclick={() => listen.toggle()}
				aria-label={listen.status === 'playing' ? t('reader.pause') : t('reader.resume')}
			>
				{listen.status === 'playing' ? '❚❚' : '▶'}
			</button>

			<button class="btn btn-ghost !px-2 !py-1" onclick={() => listen.skip(-1)} aria-label={t('reader.previous')}>
				⏮
			</button>
			<button class="btn btn-ghost !px-2 !py-1" onclick={() => listen.skip(1)} aria-label={t('reader.next')}>
				⏭
			</button>

			<span class="min-w-0 flex-1 truncate text-small text-muted">
				{listen.current + 1} / {listen.total}
			</span>

			<button
				class="btn btn-ghost !px-2.5 !py-1 text-small tabular-nums"
				onclick={cycleRate}
				aria-label={t('reader.speed')}
				title={t('reader.speed')}
			>
				{listen.rate}×
			</button>

			<!-- Voice is chosen in Settings → Reading → Listen. -->

			<select
				class="rounded-sm border bg-surface px-1 py-1 text-small tabular-nums"
				class:border-accent={listen.sleepMinutes > 0}
				class:text-accent={listen.sleepMinutes > 0}
				class:border-border={listen.sleepMinutes === 0}
				class:text-muted={listen.sleepMinutes === 0}
				value={listen.sleepMinutes}
				onchange={(e) => listen.setSleep(Number(e.currentTarget.value))}
				aria-label={t('reader.sleepTimer')}
				title={t('reader.sleepTimer')}
			>
				<option value={0}>🌙</option>
				<option value={5}>5m</option>
				<option value={15}>15m</option>
				<option value={30}>30m</option>
				<option value={60}>60m</option>
			</select>

			<button class="btn btn-ghost !px-2.5 !py-1" onclick={() => listen.stop()} aria-label={t('reader.stopListening')}>
				✕
			</button>
		</div>
	</div>
{/if}

<style>
	.listen-bar {
		position: fixed;
		inset-inline: 0;
		bottom: 0;
		z-index: 40;
		border-top: 1px solid var(--border);
		background: color-mix(in srgb, var(--surface) 92%, transparent);
		backdrop-filter: blur(8px);
	}
</style>
