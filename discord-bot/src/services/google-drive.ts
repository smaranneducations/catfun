import { existsSync, readFileSync, statSync } from "fs";
import { basename } from "path";
import { google } from "googleapis";
import { resolve } from "path";
import { request } from "gaxios";

const GDRIVE_FOLDER_ID = process.env.GDRIVE_FOLDER_ID || "";
const GDRIVE_KEY_FILE = process.env.GDRIVE_SERVICE_ACCOUNT_KEY_FILE || "";
const GDRIVE_CREDENTIALS_JSON = process.env.GDRIVE_SERVICE_ACCOUNT_JSON || "";
const GDRIVE_CREDENTIALS_B64 = process.env.GDRIVE_SERVICE_ACCOUNT_JSON_B64 || "";
const GDRIVE_OAUTH_CLIENT_ID = process.env.GDRIVE_OAUTH_CLIENT_ID || process.env.GOOGLE_CLIENT_ID || "";
const GDRIVE_OAUTH_CLIENT_SECRET =
  process.env.GDRIVE_OAUTH_CLIENT_SECRET || process.env.GOOGLE_CLIENT_SECRET || "";
const GDRIVE_OAUTH_REFRESH_TOKEN = process.env.GDRIVE_OAUTH_REFRESH_TOKEN || "";
const GDRIVE_OAUTH_TOKEN_FILE =
  process.env.GDRIVE_OAUTH_TOKEN_FILE || resolve(__dirname, "../../../temp/gdrive-oauth-token.json");

type ServiceAccountCredentials = {
  client_email: string;
  private_key: string;
};

function parseInlineCredentials(): ServiceAccountCredentials | null {
  try {
    if (GDRIVE_CREDENTIALS_JSON.trim()) {
      const parsed = JSON.parse(GDRIVE_CREDENTIALS_JSON);
      if (parsed.client_email && parsed.private_key) {
        return {
          client_email: String(parsed.client_email),
          private_key: String(parsed.private_key),
        };
      }
    }
  } catch {
    // Try base64 variant below.
  }

  try {
    if (GDRIVE_CREDENTIALS_B64.trim()) {
      const raw = Buffer.from(GDRIVE_CREDENTIALS_B64, "base64").toString("utf-8");
      const parsed = JSON.parse(raw);
      if (parsed.client_email && parsed.private_key) {
        return {
          client_email: String(parsed.client_email),
          private_key: String(parsed.private_key),
        };
      }
    }
  } catch {
    // Ignore invalid credentials payload.
  }

  return null;
}

export function isGoogleDriveConfigured(): boolean {
  if (GDRIVE_KEY_FILE.trim() || !!parseInlineCredentials()) return true;

  const hasOAuthClient = !!(GDRIVE_OAUTH_CLIENT_ID.trim() && GDRIVE_OAUTH_CLIENT_SECRET.trim());
  if (!hasOAuthClient) return false;
  if (GDRIVE_OAUTH_REFRESH_TOKEN.trim()) return true;
  return existsSync(GDRIVE_OAUTH_TOKEN_FILE);
}

function buildDriveClient() {
  const inlineCreds = parseInlineCredentials();
  if (inlineCreds || GDRIVE_KEY_FILE.trim()) {
    const auth = inlineCreds
      ? new google.auth.GoogleAuth({
          credentials: inlineCreds,
          scopes: ["https://www.googleapis.com/auth/drive"],
        })
      : new google.auth.GoogleAuth({
          keyFile: GDRIVE_KEY_FILE,
          scopes: ["https://www.googleapis.com/auth/drive"],
        });
    return google.drive({ version: "v3", auth });
  }

  if (!GDRIVE_OAUTH_CLIENT_ID.trim() || !GDRIVE_OAUTH_CLIENT_SECRET.trim()) {
    throw new Error(
      "Google Drive not configured. Set service account env vars or OAuth credentials."
    );
  }

  const oauth2Client = new google.auth.OAuth2(
    GDRIVE_OAUTH_CLIENT_ID,
    GDRIVE_OAUTH_CLIENT_SECRET
  );

  if (GDRIVE_OAUTH_REFRESH_TOKEN.trim()) {
    oauth2Client.setCredentials({ refresh_token: GDRIVE_OAUTH_REFRESH_TOKEN });
    return google.drive({ version: "v3", auth: oauth2Client });
  }

  if (existsSync(GDRIVE_OAUTH_TOKEN_FILE)) {
    const raw = readFileSync(GDRIVE_OAUTH_TOKEN_FILE, "utf-8");
    const token = JSON.parse(raw);
    oauth2Client.setCredentials(token);
    return google.drive({ version: "v3", auth: oauth2Client });
  }

  throw new Error(
    "OAuth token not found. Run: npm run setup-gdrive-oauth (inside discord-bot)."
  );
}

/**
 * Bearer token for manual Drive upload requests (resumable session).
 */
async function getDriveAccessToken(): Promise<string> {
  const inlineCreds = parseInlineCredentials();
  if (inlineCreds) {
    const auth = new google.auth.GoogleAuth({
      credentials: inlineCreds,
      scopes: ["https://www.googleapis.com/auth/drive"],
    });
    const client = await auth.getClient();
    const tr = await client.getAccessToken();
    if (!tr.token) throw new Error("Could not obtain Google access token (service account).");
    return tr.token;
  }
  if (GDRIVE_KEY_FILE.trim()) {
    const auth = new google.auth.GoogleAuth({
      keyFile: GDRIVE_KEY_FILE,
      scopes: ["https://www.googleapis.com/auth/drive"],
    });
    const client = await auth.getClient();
    const tr = await client.getAccessToken();
    if (!tr.token) throw new Error("Could not obtain Google access token (key file).");
    return tr.token;
  }

  if (!GDRIVE_OAUTH_CLIENT_ID.trim() || !GDRIVE_OAUTH_CLIENT_SECRET.trim()) {
    throw new Error("Google Drive OAuth client is not configured.");
  }

  const oauth2Client = new google.auth.OAuth2(
    GDRIVE_OAUTH_CLIENT_ID,
    GDRIVE_OAUTH_CLIENT_SECRET
  );

  if (GDRIVE_OAUTH_REFRESH_TOKEN.trim()) {
    oauth2Client.setCredentials({ refresh_token: GDRIVE_OAUTH_REFRESH_TOKEN });
  } else if (existsSync(GDRIVE_OAUTH_TOKEN_FILE)) {
    const raw = readFileSync(GDRIVE_OAUTH_TOKEN_FILE, "utf-8");
    oauth2Client.setCredentials(JSON.parse(raw));
  } else {
    throw new Error("OAuth token not found. Run: npm run setup-gdrive-oauth (inside discord-bot).");
  }

  const tr = await oauth2Client.getAccessToken();
  if (!tr.token) throw new Error("OAuth access token unavailable (refresh or re-authorize).");
  return tr.token;
}

/**
 * Resumable upload — avoids multipart timeouts and size issues on large PDFs.
 * @see https://developers.google.com/drive/api/guides/manage-uploads#resumable
 */
async function uploadPdfResumable(pdfPath: string, finalName: string, size: number): Promise<string> {
  const token = await getDriveAccessToken();
  const metadata = {
    name: finalName,
    mimeType: "application/pdf",
    parents: GDRIVE_FOLDER_ID ? [GDRIVE_FOLDER_ID] : undefined,
  };

  const init = await request<unknown>({
    method: "POST",
    url: "https://www.googleapis.com/upload/drive/v3/files",
    params: {
      uploadType: "resumable",
      fields: "id",
      supportsAllDrives: true,
    },
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json; charset=UTF-8",
      "X-Upload-Content-Type": "application/pdf",
      "X-Upload-Content-Length": String(size),
    },
    data: metadata,
    timeout: 120_000,
    validateStatus: (status: number) => status === 200,
  });

  const rawHeaders = init.headers as unknown as { location?: string; get?: (n: string) => string | null };
  const sessionUrl =
    typeof rawHeaders.get === "function"
      ? rawHeaders.get("location") || rawHeaders.get("Location")
      : rawHeaders.location;
  if (!sessionUrl || typeof sessionUrl !== "string") {
    throw new Error("Drive resumable upload did not return a session URL.");
  }

  const buf = readFileSync(pdfPath);
  const put = await request<{ id?: string }>({
    method: "PUT",
    url: sessionUrl,
    headers: {
      "Content-Length": String(size),
      "Content-Range": `bytes 0-${size - 1}/${size}`,
    },
    data: buf,
    timeout: 900_000,
    validateStatus: (status: number) => status >= 200 && status < 300,
  });

  const id = put.data?.id;
  if (!id) {
    throw new Error("Drive resumable upload completed but response had no file id.");
  }
  return id;
}

export async function uploadPdfToGoogleDrive(pdfPath: string, fileName?: string): Promise<string> {
  const drive = buildDriveClient();
  const finalName = fileName || basename(pdfPath);
  const size = statSync(pdfPath).size;
  if (size === 0) {
    throw new Error("PDF file is empty.");
  }

  const fileId = await uploadPdfResumable(pdfPath, finalName, size);

  await drive.permissions.create(
    {
      fileId,
      requestBody: {
        role: "reader",
        type: "anyone",
      },
      supportsAllDrives: true,
      sendNotificationEmail: false,
    },
    { timeout: 60_000 }
  );

  return `https://drive.google.com/file/d/${fileId}/view?usp=sharing`;
}
