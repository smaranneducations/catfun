/**
 * Standalone script to register slash commands.
 * Run with: npx ts-node src/deploy-commands.ts
 */

import { REST, Routes } from "discord.js";
import { CONFIG } from "./config";

import * as pingCommand from "./commands/ping";
import * as aibriefCommand from "./commands/aibrief";

async function deploy() {
  const rest = new REST({ version: "10" }).setToken(CONFIG.DISCORD_BOT_TOKEN);
  const commands = [pingCommand.data.toJSON(), aibriefCommand.data.toJSON()];

  console.log("📝 Deploying slash commands...");
  console.log(`   App ID: ${CONFIG.DISCORD_APP_ID}`);
  console.log(`   Guild ID: ${CONFIG.DISCORD_GUILD_ID}`);

  try {
    await rest.put(
      Routes.applicationGuildCommands(
        CONFIG.DISCORD_APP_ID,
        CONFIG.DISCORD_GUILD_ID
      ),
      { body: commands }
    );
    console.log("✅ Commands deployed successfully!");
  } catch (err) {
    console.error("❌ Deploy failed:", err);
  }
}

deploy();
