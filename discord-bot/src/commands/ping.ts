import { ChatInputCommandInteraction, MessageFlags, SlashCommandBuilder } from "discord.js";
import { healthCheck } from "../services/pipeline-client";

export const data = new SlashCommandBuilder()
  .setName("ping")
  .setDescription("Check if the bot and pipeline API are alive");

export async function execute(interaction: ChatInputCommandInteraction) {
  if (!interaction.deferred && !interaction.replied) {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
  }

  const start = Date.now();
  const apiUp = await healthCheck();
  const latency = Date.now() - start;

  const botPing = interaction.client.ws.ping;

  await interaction.editReply({
    content: [
      "**🏓 Pong!**",
      `Bot latency: **${botPing}ms**`,
      `API check: **${latency}ms** ${apiUp ? "✅ Online" : "❌ Offline"}`,
    ].join("\n"),
  });
}
