import { config as dotenvConfig } from "dotenv";
import { resolve } from "path";

// Load .env from parent catfun directory
dotenvConfig({ path: resolve(__dirname, "../../.env") });

export const CONFIG = {
  // Discord
  DISCORD_BOT_TOKEN: process.env.DISCORD_BOT_TOKEN || "",
  DISCORD_APP_ID: process.env.DISCORD_APP_ID || "",
  DISCORD_GUILD_ID: process.env.DISCORD_GUILD_ID || "",
  DISCORD_PUBLIC_KEY: process.env.DISCORD_PUBLIC_KEY || "",

  // Python API (local for now)
  PYTHON_API_URL: process.env.PYTHON_API_URL || "http://localhost:8900",

  // Pipeline defaults
  DEFAULT_PAGES: 4,
  MAX_PAGES: 6,
  MIN_PAGES: 2,
} as const;
