/**
 * Shared client reference — avoids circular dependency between
 * index.ts and command files.
 */

import { Client } from "discord.js";

let _client: Client | null = null;

export function setClient(client: Client) {
  _client = client;
}

export function getClient(): Client {
  if (!_client) throw new Error("Bot client not initialized");
  return _client;
}
