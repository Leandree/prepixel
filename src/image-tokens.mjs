// Image token cost, AFTER the API's automatic downscale.
//
// Naive `w*h/750` overstates the pixel side for any screenshot bigger than the
// model's cap: the API resizes the image down before charging for it. Two tiers:
//
//   high-res (Opus 4.7+, Opus 4.8, Opus 5, Sonnet 5, Fable 5)
//        long edge <= 2576 px, total <= 3.588 MP  ->  cap ~4784 tokens
//   legacy   (Opus 4.6, Sonnet 4.6 and earlier)
//        long edge <= 1568 px, total <= 1.15  MP  ->  cap ~1533 tokens
//
// Consequence worth knowing before quoting any ratio: a 2x Retina screenshot of a
// 1280x800 viewport costs 4784 tokens on a high-res model but only 1534 on a legacy
// one — the API scales it back down to roughly what the CSS-resolution shot (1366)
// would have cost. Sending Retina pixels to a legacy model buys nothing.
export function imageTokens(w, h, tier = 'highres') {
  const [maxEdge, maxPx] = tier === 'highres' ? [2576, 3_588_000] : [1568, 1_150_000];
  const s = Math.min(1, maxEdge / Math.max(w, h));
  let [W, H] = [w * s, h * s];
  if (W * H > maxPx) { const s2 = Math.sqrt(maxPx / (W * H)); W *= s2; H *= s2; }
  return Math.ceil((W * H) / 750);
}
