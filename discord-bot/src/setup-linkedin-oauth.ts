/**
 * LinkedIn OAuth — opens the browser for manual consent, receives the redirect,
 * exchanges the code for tokens, and saves them for the Python API + refresh flow.
 *
 * Prereqs in catfun/.env:
 *   LINKEDIN_CLIENT_ID
 *   LINKEDIN_CLIENT_SECRET
 *
 * In LinkedIn Developer Portal → your app → Auth → Authorized redirect URLs, add e.g.:
 *   - http://localhost:3000/auth/linkedin/callback (this script listens here; override via LINKEDIN_OAUTH_REDIRECT_URI)
 *   - https://www.linkedin.com/developers/tools/oauth/redirect (LinkedIn’s OAuth tool only — not used by this script)
 */
import { config as dotenvConfig } from "dotenv";
import { resolve } from "path";
import { createServer } from "http";
import { mkdirSync, writeFileSync } from "fs";
import { randomBytes } from "crypto";
import { exec } from "child_process";

dotenvConfig({ path: resolve(__dirname, "../../.env") });

const CLIENT_ID = (process.env.LINKEDIN_CLIENT_ID || "").trim();
const CLIENT_SECRET = (process.env.LINKEDIN_CLIENT_SECRET || "").trim();
const REDIRECT_URI = (
  process.env.LINKEDIN_OAUTH_REDIRECT_URI || "http://localhost:3000/auth/linkedin/callback"
).trim();
const TOKEN_FILE =
  process.env.LINKEDIN_OAUTH_TOKEN_FILE || resolve(__dirname, "../../temp/linkedin-oauth-token.json");
const SCOPES = (process.env.LINKEDIN_OAUTH_SCOPES || "openid profile w_member_social").trim();

const AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization";
const TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken";

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

async function exchangeCode(code: string): Promise<Record<string, unknown>> {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: REDIRECT_URI,
    client_id: CLIENT_ID,
    client_secret: CLIENT_SECRET,
  });

  const resp = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  const text = await resp.text();
  if (!resp.ok) {
    throw new Error(`Token exchange failed (${resp.status}): ${text.slice(0, 800)}`);
  }
  try {
    return JSON.parse(text) as Record<string, unknown>;
  } catch {
    throw new Error(`Token response was not JSON: ${text.slice(0, 200)}`);
  }
}

async function main() {
  if (!CLIENT_ID || !CLIENT_SECRET) {
    console.error(
      "Missing LINKEDIN_CLIENT_ID or LINKEDIN_CLIENT_SECRET in .env (repo root catfun/.env)."
    );
    process.exit(1);
  }

  const state = randomBytes(16).toString("hex");
  const params = new URLSearchParams({
    response_type: "code",
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    state,
    scope: SCOPES,
  });
  const authorizeUrl = `${AUTH_URL}?${params.toString()}`;

  const url = new URL(REDIRECT_URI);
  const host = url.hostname;
  const port = Number(url.port || (url.protocol === "https:" ? 443 : 80));
  const callbackPath = url.pathname || "/oauth/callback";

  console.log("");
  console.log("Authorized redirect URLs (LinkedIn app → Auth) should include at least:");
  console.log(`  ${REDIRECT_URI}`);
  console.log("  (optional, for LinkedIn’s OAuth playground) https://www.linkedin.com/developers/tools/oauth/redirect");
  console.log("");
  console.log("Opening browser for LinkedIn OAuth consent...");
  console.log("(If nothing opens, paste this URL into your browser:)");
  console.log(authorizeUrl);
  console.log("");

  const server = createServer(async (req, res) => {
    try {
      if (!req.url) return;
      const incoming = new URL(req.url, `${url.protocol}//${host}:${port}`);
      if (incoming.pathname !== callbackPath) {
        res.statusCode = 404;
        res.end("Not found");
        return;
      }

      const err = incoming.searchParams.get("error");
      const errDesc = incoming.searchParams.get("error_description");
      if (err) {
        res.statusCode = 400;
        res.setHeader("Content-Type", "text/html; charset=utf-8");
        res.end(
          `<h2>LinkedIn OAuth error</h2><p>${err}</p><p>${errDesc || ""}</p>`
        );
        throw new Error(`OAuth failed: ${err} ${errDesc || ""}`);
      }

      const code = incoming.searchParams.get("code");
      const returnedState = incoming.searchParams.get("state");
      if (returnedState !== state) {
        res.statusCode = 400;
        res.end("Invalid state");
        throw new Error("OAuth state mismatch — try again.");
      }
      if (!code) {
        res.statusCode = 400;
        res.end("Missing auth code");
        throw new Error("Missing auth code");
      }

      const tokens = await exchangeCode(code);

      mkdirSync(resolve(TOKEN_FILE, ".."), { recursive: true });
      writeFileSync(TOKEN_FILE, JSON.stringify(tokens, null, 2), "utf-8");

      res.statusCode = 200;
      res.setHeader("Content-Type", "text/html; charset=utf-8");
      res.end(
        "<h2>LinkedIn OAuth complete.</h2><p>You can close this tab. Tokens were saved for the AI Brief API.</p>"
      );

      console.log(`Saved token file: ${TOKEN_FILE}`);
      const at = tokens.access_token ? "present" : "missing";
      const rt = tokens.refresh_token ? "present" : "missing";
      console.log(`  access_token: ${at}  |  refresh_token: ${rt}`);
      if (!tokens.refresh_token) {
        console.log(
          "  Note: No refresh_token in response. LinkedIn may only send it once — try revoking app access in LinkedIn settings and run this script again, or check your app's OAuth products/scopes."
        );
      }
      console.log("");
      console.log("Restart the Python API (and bot) so config reloads. Client ID/secret stay in .env; tokens are in the file above.");

      server.close(() => process.exit(0));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.error("LinkedIn OAuth setup failed:", msg);
      server.close(() => process.exit(1));
    }
  });

  server.listen(port, host, () => {
    openBrowser(authorizeUrl);
  });
}

main().catch((e) => {
  console.error("Setup failed:", e);
  process.exit(1);
});
