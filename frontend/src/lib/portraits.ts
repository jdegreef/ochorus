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
	'amanda-berry-smith': '50% 0%',
	'amy-carmichael': '50% 0%',
	'andrew-murray': '50% 2%',
	'anselm-of-canterbury': '50% 0%', // engraved profile, face at ~28% of a near-square plate
	'athanasius-of-alexandria': '50% 0%', // icon: head at ~20% of a 0.69 plate
	'augustine-of-hippo': '50% 0%',
	'bernard-of-clairvaux': '50% 0%', // painting cropped to a bust; face at ~42%, near-square so nearly inert
	'catherine-booth': '50% 0%',
	'charles-finney': '50% 0%',
	'charles-h-spurgeon': '50% 0%',
	'cyprian-of-carthage': '50% 0%', // icon: bust, face at ~22%
	'david-brainerd': '50% 0%',
	'dwight-l-moody': '50% 5%',
	'frederick-brotherton-meyer': '50% 0%',
	'gareth-evans': '50% 45%', // square source
	'george-muller': '50% 37%',
	'george-whitefield': '50% 0%',
	'hannah-whitall-smith': '50% 0%',
	'hudson-taylor': '50% 20%',
	'ignatius-of-antioch': '50% 0%', // fresco: head at ~17% of a 0.72 plate
	'jeanne-guyon': '50% 58%',
	'john-bunyan': '50% 0%',
	'john-chrysostom': '50% 0%', // mosaic: standing figure, head at ~11%
	'john-wesley': '50% 0%',
	'jonathan-edwards': '50% 0%',
	'lemuel-haynes': '50% 0%',
	'r-a-torrey': '50% 10%',
	'richard-allen': '50% 37%',
	'richard-baxter': '50% 18%',
	'samuel-ajayi-crowther': '50% 45%',
	'susanna-wesley': '50% 21%',
	'thomas-a-kempis': '50% 0%',
	'thomas-watson': '50% 0%',
	'watchman-nee': '50% 32%',
	'william-booth': '50% 25%'
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
