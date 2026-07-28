/**
 * AI Brief Discord Bot — Entry Point
 *
 * Connects to Discord, registers slash commands, and handles interactions.
 *
 * PROCESS SAFETY:
 *   - Writes a PID file on startup → kills any old instance first
 *   - Locks a TCP port (8901) as a single-instance guard
 *   - Cleans up on SIGINT / SIGTERM / uncaught exceptions
 *   - Prevents competing bot instances from eating interaction tokens
 *
 * STARTUP ORDER:
 *   Connect to Discord before loading heavy OneDrive-backed modules
 *   (googleapis etc.) so /ping works even when Drive deps are slow.
 */

import {
  Client,
  GatewayIntentBits,
  Partials,
  REST,
  Routes,
  MessageFlags,
  SlashCommandBuilder,
} from "discord.js";
import { CONFIG } from "./config";
import { setClient } from "./utils/bot-client";
import * as fs from "fs";
import * as path from "path";
import * as net from "net";

// Lightweight command schemas only — heavy handlers load after defer
import * as pingCommand from "./commands/ping";

const aibriefCommandData = new SlashCommandBuilder()
  .setName("aibrief")
  .setDescription("Start a new AI Brief — multi-agent content pipeline");

// ═══════════════════════════════════════════════════════════════
//  SINGLE-INSTANCE GUARD
// ═══════════════════════════════════════════════════════════════

const DATA_DIR = path.join(__dirname, "..", "data");
const PID_FILE = path.join(DATA_DIR, "bot.pid");
const LOCK_PORT = 8901; // TCP port used as a process lock

/** Ensure data directory exists */
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

/**
 * Kill any previous bot instance using the PID file.
 */
function killOldInstance(): void {
  try {
    if (fs.existsSync(PID_FILE)) {
      const oldPid = parseInt(fs.readFileSync(PID_FILE, "utf-8").trim(), 10);
      if (oldPid && oldPid !== process.pid) {
        console.log(`🔒 Found old PID ${oldPid} — sending kill signal...`);
        try {
          process.kill(oldPid, "SIGTERM");
          // Give it a moment to shut down
          console.log(`   Old process ${oldPid} terminated.`);
        } catch (err: any) {
          if (err.code === "ESRCH") {
            console.log(`   Old process ${oldPid} already dead.`);
          } else {
            console.warn(`   Could not kill ${oldPid}: ${err.message}`);
          }
        }
      }
    }
  } catch {
    // PID file doesn't exist or can't be read — that's fine
  }
}

/**
 * Write current PID to the PID file.
 */
function writePidFile(): void {
  fs.writeFileSync(PID_FILE, String(process.pid), "utf-8");
  console.log(`🔒 PID file written: ${process.pid}`);
}

/**
 * Clean up PID file on exit.
 */
function removePidFile(): void {
  try {
    if (fs.existsSync(PID_FILE)) {
      const storedPid = parseInt(fs.readFileSync(PID_FILE, "utf-8").trim(), 10);
      // Only remove if it's OUR pid (another instance might have overwritten it)
      if (storedPid === process.pid) {
        fs.unlinkSync(PID_FILE);
      }
    }
  } catch {
    // Best effort
  }
}

/**
 * Start a TCP server on a fixed port as a single-instance lock.
 * If the port is already taken, another instance is running → kill it.
 */
function acquireProcessLock(): Promise<net.Server> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();

    server.on("error", (err: NodeJS.ErrnoException) => {
      if (err.code === "EADDRINUSE") {
        console.log(`⚠️  Lock port ${LOCK_PORT} in use — another instance may be running.`);
        console.log("   The PID-based kill should have handled it. Retrying in 2s...");
        // Try to kill via PID file, then retry
        killOldInstance();
        setTimeout(() => {
          server.close();
          const retry = net.createServer();
          retry.on("error", () => {
            console.error(`❌ Could not acquire lock port ${LOCK_PORT}. Is another bot running?`);
            reject(new Error("Could not acquire process lock"));
          });
          retry.listen(LOCK_PORT, "127.0.0.1", () => {
            console.log(`🔒 Lock acquired on retry (port ${LOCK_PORT})`);
            resolve(retry);
          });
        }, 2000);
      } else {
        reject(err);
      }
    });

    server.listen(LOCK_PORT, "127.0.0.1", () => {
      console.log(`🔒 Process lock acquired (port ${LOCK_PORT})`);
      resolve(server);
    });
  });
}

// ═══════════════════════════════════════════════════════════════
//  GRACEFUL SHUTDOWN
// ═══════════════════════════════════════════════════════════════

let lockServer: net.Server | null = null;

function gracefulShutdown(signal: string) {
  console.log(`\n🛑 Received ${signal} — shutting down gracefully...`);
  removePidFile();
  lockServer?.close();
  client.destroy();
  console.log("   Bot disconnected. Goodbye.");
  process.exit(0);
}

process.on("SIGINT", () => gracefulShutdown("SIGINT"));
process.on("SIGTERM", () => gracefulShutdown("SIGTERM"));
process.on("uncaughtException", (err) => {
  console.error("💥 Uncaught exception:", err);
  removePidFile();
  lockServer?.close();
  process.exit(1);
});
process.on("unhandledRejection", (reason) => {
  console.error("💥 Unhandled rejection:", reason);
  // Don't exit on unhandled rejections — log and continue
});

// ═══════════════════════════════════════════════════════════════
//  DISCORD CLIENT
// ═══════════════════════════════════════════════════════════════

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers,
  ],
  partials: [Partials.Channel, Partials.Message],
});

// ---- Event: Ready ----
client.once("ready" as any, async () => {
  setClient(client);
  console.log(`✅ Bot online as ${client.user?.tag}`);
  console.log(`   Guilds: ${client.guilds.cache.size}`);
  console.log(`   API URL: ${CONFIG.PYTHON_API_URL}`);
  console.log(`   PID: ${process.pid}`);

  // Register slash commands on the guild (instant, no 1-hour cache)
  await registerCommands();
});

// ---- Event: Interactions ----
client.on("interactionCreate", async (interaction) => {
  const type = interaction.isChatInputCommand() ? "CMD"
    : interaction.isButton() ? "BTN"
    : interaction.isStringSelectMenu() ? "SEL"
    : interaction.isModalSubmit() ? "MOD"
    : "OTHER";
  const id = (interaction as any).customId || (interaction as any).commandName || "?";
  console.log(`[INTERACTION] ${type}: ${id} | channel: ${interaction.channelId} | user: ${interaction.user.tag}`);

  try {
    // Acknowledge slash commands within Discord's 3s window BEFORE loading heavy modules
    if (interaction.isChatInputCommand() && !interaction.deferred && !interaction.replied) {
      if (interaction.commandName === "ping") {
        await interaction.deferReply({ flags: MessageFlags.Ephemeral });
      } else {
        await interaction.deferReply();
      }
    }

    const { handleInteraction } = await import("./handlers/interactions");
    await handleInteraction(interaction);
  } catch (err) {
    console.error("[INTERACTION ERROR]", err);
    if (interaction.isRepliable() && (interaction.deferred || interaction.replied)) {
      await interaction.editReply({ content: "Something went wrong handling that command." }).catch(() => {});
    }
  }
});

// ---- Register slash commands ----
async function registerCommands() {
  const rest = new REST({ version: "10" }).setToken(CONFIG.DISCORD_BOT_TOKEN);
  const commands = [pingCommand.data.toJSON(), aibriefCommandData.toJSON()];

  try {
    console.log("📝 Registering slash commands...");
    await rest.put(
      Routes.applicationGuildCommands(
        CONFIG.DISCORD_APP_ID,
        CONFIG.DISCORD_GUILD_ID
      ),
      { body: commands }
    );
    console.log("✅ Slash commands registered: /ping, /aibrief");
  } catch (err) {
    console.error("❌ Failed to register commands:", err);
  }
}

// ═══════════════════════════════════════════════════════════════
//  STARTUP
// ═══════════════════════════════════════════════════════════════

async function start() {
  console.log("🤖 Starting AI Brief bot...");
  console.log(`   PID: ${process.pid}`);

  // Step 1: Kill any old instance
  killOldInstance();

  // Step 2: Acquire single-instance lock
  try {
    lockServer = await acquireProcessLock();
  } catch (err: any) {
    console.error("❌ Failed to acquire process lock:", err.message);
    process.exit(1);
  }

  // Step 3: Write our PID
  writePidFile();

  // Step 4: Connect to Discord
  try {
    await client.login(CONFIG.DISCORD_BOT_TOKEN);
  } catch (err: any) {
    console.error("❌ Failed to login:", err.message);
    removePidFile();
    lockServer?.close();
    process.exit(1);
  }
}

start();
