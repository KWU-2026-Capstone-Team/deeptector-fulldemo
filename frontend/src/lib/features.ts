// Build-time switches. Public deployments build with NEXT_PUBLIC_ENABLE_GAMES=0
// because the game media's redistribution rights are unverified.
export const GAMES_ENABLED = process.env.NEXT_PUBLIC_ENABLE_GAMES !== "0";
export const PUBLIC_DEPLOYMENT = process.env.NEXT_PUBLIC_DEPLOYMENT === "public";
