import { config as dotenvConfig } from "dotenv";
import { resolve } from "path";
import { createServer } from "http";
import { mkdirSync, writeFileSync } from "fs";
import { google } from "googleapis";
import { exec } from "child_process";

dotenvConfig({ path: resolve(__dirname, "../../.env") });

const CLIENT_ID = process.env.GDRIVE_OAUTH_CLIENT_ID || process.env.GOOGLE_CLIENT_ID || "";
const CLIENT_SECRET =
  process.env.GDRIVE_OAUTH_CLIENT_SECRET || process.env.GOOGLE_CLIENT_SECRET || "";

const REDIRECT_URI = process.env.GDRIVE_OAUTH_REDIRECT_URI || "http://127.0.0.1:53682/oauth2callback";
const TOKEN_FILE = process.env.GDRIVE_OAUTH_TOKEN_FILE || resolve(__dirname, "../../temp/gdrive-oauth-token.json");
const SCOPES = ["https://www.googleapis.com/auth/drive"];

function openBrowser(url: string) {
  const safe = url.replace(/"/g, '\\"');
  if (process.platform === "win32") {
    exec(`start "" "${safe}"`);
    return;
  }
  if (process.platform === "darwin") {
    exec(`open "${safe}"`);
    return;
  }
  exec(`xdg-open "${safe}"`);
}

async function main() {
  if (!CLIENT_ID || !CLIENT_SECRET) {
    console.error(
      "Missing OAuth client credentials. Set GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET in .env (or GDRIVE_OAUTH_* overrides)."
    );
    process.exit(1);
  }

  const oauth2Client = new google.auth.OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);

  const authUrl = oauth2Client.generateAuthUrl({
    access_type: "offline",
    prompt: "consent",
    scope: SCOPES,
  });

  console.log("Opening browser for Google Drive OAuth consent...");
  console.log(authUrl);

  const url = new URL(REDIRECT_URI);
  const host = url.hostname;
  const port = Number(url.port || 53682);
  const path = url.pathname || "/oauth2callback";

  const server = createServer(async (req, res) => {
    try {
      if (!req.url) return;
      const incoming = new URL(req.url, `${url.protocol}//${host}:${port}`);
      if (incoming.pathname !== path) {
        res.statusCode = 404;
        res.end("Not found");
        return;
      }

      const code = incoming.searchParams.get("code");
      const err = incoming.searchParams.get("error");
      if (err) {
        res.statusCode = 400;
        res.end(`OAuth failed: ${err}`);
        throw new Error(`OAuth failed: ${err}`);
      }
      if (!code) {
        res.statusCode = 400;
        res.end("Missing auth code");
        throw new Error("Missing auth code");
      }

      const { tokens } = await oauth2Client.getToken(code);
      oauth2Client.setCredentials(tokens);

      mkdirSync(resolve(TOKEN_FILE, ".."), { recursive: true });
      writeFileSync(TOKEN_FILE, JSON.stringify(tokens, null, 2), "utf-8");

      res.statusCode = 200;
      res.setHeader("Content-Type", "text/html; charset=utf-8");
      res.end(
        "<h2>Google Drive OAuth complete.</h2><p>You can close this tab and return to Discord.</p>"
      );

      console.log(`Saved token file: ${TOKEN_FILE}`);
      if (tokens.refresh_token) {
        console.log("Refresh token acquired successfully.");
      } else {
        console.log(
          "No refresh token returned. Re-run and ensure you approve with prompt=consent."
        );
      }

      server.close(() => process.exit(0));
    } catch (e: any) {
      console.error("OAuth setup failed:", e.message || e);
      server.close(() => process.exit(1));
    }
  });

  server.listen(port, host, () => {
    openBrowser(authUrl);
  });
}

main().catch((e) => {
  console.error("Setup failed:", e);
  process.exit(1);
});

