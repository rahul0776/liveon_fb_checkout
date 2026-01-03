import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { v4 as uuidv4 } from "uuid";
import crypto from "crypto";

const FB_CLIENT_ID = process.env.FB_CLIENT_ID;
const FB_REDIRECT_URI = process.env.FB_REDIRECT_URI;
// State secret for signing (should be in env, but fallback for demo)
const STATE_SECRET = process.env.SESSION_SECRET || "default_secret_change_me";

function makeState() {
  const nonce = uuidv4();
  const ts = Math.floor(Date.now() / 1000);
  const payload = JSON.stringify({ ts, nonce });

  const hmac = crypto.createHmac("sha256", STATE_SECRET);
  hmac.update(payload);
  const sig = hmac.digest("base64url");

  return Buffer.from(payload).toString("base64url") + "." + sig;
}

export const dynamic = 'force-dynamic';

export async function GET() {
  // Hardcoded for debugging to rule out Env Var issues
  const REDIRECT_URI = "http://localhost:3000/api/auth/callback";

  if (!FB_CLIENT_ID) {
    return NextResponse.json({ error: "Missing FB Configuration" }, { status: 500 });
  }

  const state = makeState();
  const scope = "public_profile,user_photos";

  const params = new URLSearchParams({
    client_id: FB_CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    scope: scope,
    state: state,
    response_type: "code",
  });

  console.log("DEBUG: Generated Auth URL with URI:", REDIRECT_URI);

  const url = `https://www.facebook.com/v18.0/dialog/oauth?${params.toString()}`;

  return NextResponse.redirect(url);
}
