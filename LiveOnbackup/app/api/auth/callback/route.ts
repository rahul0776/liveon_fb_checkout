import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import crypto from "crypto";
import axios from "axios";

const FB_CLIENT_ID = process.env.FB_CLIENT_ID;
const FB_CLIENT_SECRET = process.env.FB_CLIENT_SECRET;
const FB_REDIRECT_URI = process.env.FB_REDIRECT_URI;
const STATE_SECRET = process.env.SESSION_SECRET || "default_secret_change_me";

function verifyState(s: string, maxAge = 600) {
    try {
        const [rawB64, sigB64] = s.split(".");
        if (!rawB64 || !sigB64) return null;

        const raw = Buffer.from(rawB64, "base64url");
        const hmac = crypto.createHmac("sha256", STATE_SECRET);
        hmac.update(raw);
        const expectedSig = hmac.digest("base64url");

        if (expectedSig !== sigB64) return null;

        const data = JSON.parse(raw.toString());
        const now = Math.floor(Date.now() / 1000);

        if (now - data.ts > maxAge) return null;

        return data;
    } catch (e) {
        return null;
    }
}

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const error = searchParams.get("error");

    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000";

    if (error) {
        return NextResponse.redirect(`${baseUrl}?error=${error}`);
    }

    if (!code || !state) {
        return NextResponse.redirect(`${baseUrl}?error=missing_params`);
    }

    const stateData = verifyState(state);
    if (!stateData) {
        return NextResponse.redirect(`${baseUrl}?error=invalid_state`);
    }

    try {
        // Exchange code for token
        // Hardcoded to match login route debug
        const REDIRECT_URI = "http://localhost:3000/api/auth/callback";

        const tokenRes = await axios.get("https://graph.facebook.com/v18.0/oauth/access_token", {
            params: {
                client_id: FB_CLIENT_ID,
                redirect_uri: REDIRECT_URI,
                client_secret: FB_CLIENT_SECRET,
                code: code,
            },
        });

        const accessToken = tokenRes.data.access_token;

        // Fetch user profile immediately to cache it
        const userRes = await axios.get("https://graph.facebook.com/v18.0/me", {
            params: {
                access_token: accessToken,
                fields: "id,name"
            }
        });
        const userData = userRes.data;

        // Set cookies
        const cookieStore = await cookies();

        // Store token
        cookieStore.set("fb_token", accessToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === "production",
            maxAge: 60 * 60 * 24 * 7,
            path: "/",
            sameSite: "lax",
        });

        // Store profile (non-httpOnly so client could potentially use it, but server definitely can)
        cookieStore.set("fb_user", JSON.stringify(userData), {
            httpOnly: true, // Keep it secure for now
            secure: process.env.NODE_ENV === "production",
            maxAge: 60 * 60 * 24 * 7,
            path: "/",
            sameSite: "lax",
        });

        console.log("DEBUG: Token and Profile cached, redirecting to home");

        // Redirect to main page.
        return NextResponse.redirect(`${baseUrl}/`);

    } catch (e) {
        console.error("Token exchange error:", e);
        return NextResponse.redirect(`${baseUrl}?error=token_exchange_failed`);
    }
}
