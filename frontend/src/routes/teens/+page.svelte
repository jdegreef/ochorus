<script lang="ts">
	import AudienceHub from '$lib/components/AudienceHub.svelte';

	let { data } = $props();
</script>

<AudienceHub hub={data.hub} shelf={data.shelf} loadError={data.loadError} />
