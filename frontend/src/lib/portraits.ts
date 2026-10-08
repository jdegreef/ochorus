/**
 * Where the face sits in each author portrait, as a CSS `object-position`.
 *
 * Portraits are always rendered into a circle with `object-cover`, and almost
 * every source we hold is *tall* — 3:5 photographic plates, standing paintings,
 * engraved half-lengths — with the head near the top. `object-cover` defaults
 * to `50% 50%`, so the square crop keeps the vertical **middle** of the plate:
 * a torso, a pair of folded hands, the arm of a chair. The face is either cut
 * off at the chin or missing from the circle altogether.
 *
 * Each value below is derived from where the face actually is in that file.
 * For a source of aspect `a` (width ÷ height) with the face centred at `fy`
 * (a fraction of the image height), the position that lands the face 45% of
 * the way down the circle is
 *
 *     y = (fy − 0.45·a) ÷ (1 − a)
 *
 * clamped to 0–100%. Many clamp to `0%`: the head sits so high in the plate
 * that the top edge is as close as a cover-crop can get. Square sources crop
 * nothing at all, so their value is inert — they are listed only so the table
 * stays a complete inventory of what is in `static/portraits/`
 * (`portraits.test.ts` fails if the two drift apart).
 *
 * Horizontal is always 50%: no source here is wider than it is tall, so the
 * crop never trims the sides and an x other than 50% would do nothing.
 */
export const PORTRAIT_POSITION: Record<string, string> = {
	'a-b-simpson': '50% 50%', // square source — the crop takes the whole plate
	'a-w-tozer': '50% 65%', // 1950s bust; face centred at ~55% of a 0.75 plate — 2% left the eyes below centre and cut the chin
	'absalom-jones': '50% 29%', // Raphaelle Peale 1810 oil, cropped to a bust; face at ~41% of a 0.75 plate
	'alexander-maclaren': '50% 0%', // 1889 bust photo; face high at ~22% of a 0.75 plate
	'amanda-berry-smith': '50% 0%',
	'amy-carmichael': '50% 0%',
	'andrew-murray': '50% 2%',
	'anselm-of-canterbury': '50% 0%', // engraved profile, face at ~28% of a near-square plate
	'arthur-t-pierson': '50% 10%', // 1886 engraving (Many Infallible Proofs); face at ~25% of a 0.77 plate
	'athanasius-of-alexandria': '50% 0%', // icon: head at ~20% of a 0.69 plate
	'augustine-of-hippo': '50% 0%',
	'bernard-of-clairvaux': '50% 0%', // painting cropped to a bust; face at ~42%, near-square so nearly inert
	'bill-bright': '50% 5%', // 1980 bust photo; face at ~34% of a 0.75 plate
	'billy-graham': '50% 0%', // 1966 press photo; face high at ~23% of a 0.80 plate
	'billy-sunday': '50% 0%', // 1921 LoC studio bust; face at ~33% of a 0.70 plate — 0% is the highest the crop goes
	'blaise-pascal': '50% 10%', // c. 1690 Versailles oil, cropped to a bust; face at ~35% of a 0.84 plate
	'brother-lawrence': '50% 8%', // Ochorus firelight illustration (imagined likeness); face at ~35% of a 0.75 plate
	'c-s-lewis': '50% 0%', // 1957 dust-jacket photo (John S. Murray); head high — anything lower clips the crown
	'c-t-studd': '50% 0%', // full-length cricket photo; head high at ~10% of a 0.54 plate
	'catherine-booth': '50% 0%',
	'charles-finney': '50% 0%',
	'charles-h-spurgeon': '50% 0%',
	'charles-s-price': '50% 30%', // 1920s–30s studio portrait; near-square, so nearly inert
	'christmas-evans': '50% 25%', // 1859 engraved frontispiece; face at ~40% of a 0.75 plate
	'clement-of-rome': '50% 0%', // mosaic bust; face at ~28% of a 0.80 plate
	'corrie-ten-boom': '50% 0%', // 1921 photo, hat; face at ~27% of a 0.63 plate
	'cyprian-of-carthage': '50% 0%', // icon: bust, face at ~22%
	'david-brainerd': '50% 0%',
	'david-livingstone': '50% 3%', // seated Annan photo; face high at ~25% of a 0.82 plate
	'derek-prince': '50% 5%', // studio bust; face at ~29% of a 0.71 plate
	'dietrich-bonhoeffer': '50% 0%', // 1939 standing figure; head high at ~15% of a 0.63 plate
	'dwight-l-moody': '50% 5%',
	'e-m-bounds': '50% 2%', // 1864 photograph; face at ~32% of a 0.72 plate
	'erica-sabiti': '50% 20%', // bust in clerical cap; near-square
	'evelyn-christenson': '50% 50%', // square source — the crop takes the whole photo
	'f-f-bosworth': '50% 0%', // small studio bust; face at ~30% of a 0.85 plate
	'fanny-jackson-coppin': '50% 9%', // 1913 frontispiece (Reminiscences); face at ~36% of a 0.75 plate
	'festo-kivengere': '50% 10%', // bishop photo; face at ~37% of a 0.70 plate
	'frederick-brotherton-meyer': '50% 0%',
	'g-k-chesterton': '50% 10%', // E. H. Mills photo; face at ~28% of a 0.78 plate
	'gareth-evans': '50% 45%', // square source
	'george-herbert': '50% 8%', // engraving; face at ~35% of a 0.80 plate
	'george-macdonald': '50% 10%', // 1860s William Jeffrey photo, signature cropped off
	'george-muller': '50% 37%',
	'george-whitefield': '50% 0%',
	'gladys-aylward': '50% 8%', // bust-cropped from a full-length photo; face at ~28% of a 0.74 plate
	'gregory-the-great': '50% 0%', // Goya painting, seated; face high at ~13% of a 0.57 plate
	'hannah-whitall-smith': '50% 0%',
	'helen-roseveare': '50% 8%', // 2003 bust photo; face at ~36% of a 0.82 plate
	'hudson-taylor': '50% 20%',
	'ignatius-of-antioch': '50% 0%', // fresco: head at ~17% of a 0.72 plate
	'isaac-watts': '50% 20%', // NPG portrait cropped to a bust; near-square, so nearly inert
	'j-c-ryle': '50% 0%', // 1888 photograph: bust, face high at ~30% of a 0.70 plate
	'janani-luwum': '50% 50%', // square close-up — the crop takes the whole photo
	'jarena-lee': '50% 0%', // 1849 lithograph: seated figure, face at ~18% of a 0.73 plate
	'jeanne-guyon': '50% 58%',
	'jesse-lyman-hurlbut': '50% 30%', // c. 1895 bust photo; near-square, so nearly inert
	'joe-church': '50% 30%', // cropped from a photo with his wife Decie; near-square
	'john-bunyan': '50% 0%',
	'john-calvin': '50% 0%', // c.1550 capped portrait; face at ~29% of a 0.72 plate
	'john-cassian': '50% 0%', // icon: standing figure, head at ~20% of a 0.70 plate
	'john-chrysostom': '50% 0%', // mosaic: standing figure, head at ~11%
	'john-foxe': '50% 20%', // 1587 portrait cropped to a bust; near-square
	'john-g-lake': '50% 0%', // c.1900–05 profile bust; face at ~25% of a 0.62 plate
	'john-hyde': '50% 20%', // studio bust; face at ~40% of a 0.86 plate
	'john-milton': '50% 30%', // c. 1629 portrait; face at ~40% of a 0.80 plate
	'john-newton': '50% 27%', // portrait; face at ~40% of a 0.72 plate
	'john-owen': '50% 0%', // Greenhill portrait; face at ~31% of a 0.81 plate
	'john-r-mott': '50% 0%', // 1910 Review of Reviews bust; face at ~28% of a 0.81 plate
	'john-stott': '50% 0%', // photograph, bust; face at ~25% of a 0.73 plate
	'john-wesley': '50% 0%',
	'jonathan-edwards': '50% 0%',
	'josephine-bakhita': '50% 21%', // studio photo cropped to a bust; face at ~39% of a 0.75 plate
	'julia-foote': '50% 0%', // studio photo: standing figure, face at ~22% of a 0.62 plate
	'kanzo-uchimura': '50% 15%', // c.1912 photo; face at ~37% of a 0.75 plate
	'kateri-tekakwitha': '50% 0%', // Chauchetière's c.1690s painting cropped to the upper figure; face high at ~28%
	'lawrence-barham': '50% 0%', // cropped from a photo with his wife Julia; head at the top edge
	'lemuel-haynes': '50% 0%',
	'loren-cunningham': '50% 0%', // cropped from a group photo; face at ~22% of a 0.61 plate
	'lottie-moon': '50% 30%', // oval studio photo; face at ~40% of a 0.66 plate
	'martin-luther': '50% 0%', // Cranach 1517 half-length; face at ~23% of a 0.64 plate
	'martyn-lloyd-jones': '50% 50%', // square source — the crop takes the whole photo
	'mary-slessor': '50% 3%', // seated photo; head high at ~22% of a 0.67 plate
	'monica-of-hippo': '50% 0%', // Gozzoli fresco, tall niche; head high at ~18% of a 0.42 plate
	'pandita-ramabai': '50% 20%', // bust photo; face at ~30% of a 0.73 plate
	'r-a-torrey': '50% 10%',
	'rees-howells': '50% 10%', // bust photo; face at ~32% of a 0.84 plate
	'richard-allen': '50% 37%',
	'richard-baxter': '50% 18%',
	'richard-sibbes': '50% 0%', // labelled portrait; face at ~28% of a 0.72 plate
	'robert-murray-mcheyne': '50% 2%', // engraving; side profile, head high at ~32% of a 0.78 plate
	'sadhu-sundar-singh': '50% 2%', // 1922 Uppsala photo cropped to a bust; face at ~34% of a 0.75 plate
	'samson-occom': '50% 0%', // 18th-c. portrait engraving (repr. 1899); face at ~34% of a 0.75 plate
	'samuel-ajayi-crowther': '50% 45%',
	'simeon-nsibambi': '50% 30%', // cropped from a photo with his wife Eva; near-square
	'smith-wigglesworth': '50% 0%', // 1920 preaching photo cropped to a bust; face at ~25% of a 0.77 plate
	'soonderbai-powar': '50% 0%', // 1900 plate (Dyer, Pandita Ramabai); oval vignette, face at ~33% of a 0.76 plate
	'susanna-wesley': '50% 21%',
	'teresa-of-avila': '50% 0%', // cropped to the bust; face at ~25% of a 0.58 plate
	'thomas-a-kempis': '50% 0%',
	'thomas-watson': '50% 0%',
	'timothy-keller': '50% 0%', // speaking pose; face high at ~19% of a 0.73 plate
	'watchman-nee': '50% 32%',
	'william-booth': '50% 25%',
	'william-carey': '50% 18%', // engraved bust; face at ~30% of a 0.67 plate
	'william-j-seymour': '50% 0%', // 1910s photo cropped to a bust; face high at ~25% of a 0.75 plate
	'william-law': '50% 16%', // cropped oval engraving; face at ~33% of a 0.58 plate
	'william-nagenda': '50% 20%', // cropped from a photo with his wife Sala; near-square
	'yosiya-kinuka': '50% 30%', // cropped from a photo of him riding a motorcycle; near-square
};

/**
 * The fallback for a portrait nobody has looked at yet — an author added from
 * the admin, or a photo hosted elsewhere. Biased upwards rather than centred,
 * because the failure mode we keep meeting is a tall plate with a high head:
 * a third of the way down beats the middle far more often than not.
 */
export const PORTRAIT_POSITION_DEFAULT = '50% 30%';

/** The `object-position` to render `slug`'s portrait with. */
export function portraitPosition(slug: string | null | undefined): string {
	return (slug && PORTRAIT_POSITION[slug]) || PORTRAIT_POSITION_DEFAULT;
}

/**
 * Widths (px) of the responsive portrait WebP variants that
 * `backend/scripts/build_portrait_assets.py` commits beside each source. 96
 * covers every avatar (32–44px) at 2× DPR; 224 covers the largest painted size
 * (the 112px biography card) at 2×. Mirrored there; `portraits.test.ts` fails if
 * a source is missing a variant.
 */
export const PORTRAIT_WIDTHS = [96, 224] as const;

/**
 * A `srcset` of the small WebP variants for a `/portraits/<slug>.jpg` URL, so a
 * 44px avatar fetches ~2 KB instead of the ~50 KB full plate. Pair it with a
 * `sizes` matching the CSS box. Returns `undefined` for anything that is not a
 * self-hosted portrait JPEG — an off-site photo has no committed variants, so
 * the `<img>` falls back to its `src`.
 */
export function portraitSrcset(url: string | null | undefined): string | undefined {
	if (!url) return undefined;
	const m = /^(\/portraits\/[^?#]+)\.jpe?g$/i.exec(url);
	if (!m) return undefined;
	return PORTRAIT_WIDTHS.map((w) => `${m[1]}-${w}.webp ${w}w`).join(', ');
}

/** Initials for the placeholder avatar shown when a person has no portrait —
 * first letter of the first two words, uppercased. One home so the author
 * header, the bio card and the person card can't drift apart. */
export const initials = (name: string): string =>
	name.split(' ').filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();
