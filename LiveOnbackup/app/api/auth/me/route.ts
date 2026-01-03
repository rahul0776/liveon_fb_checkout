import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import axios from "axios";

export async function GET() {
    const cookieStore = await cookies();
    const token = cookieStore.get("fb_token")?.value;

    if (!token) {
        return NextResponse.json({ authenticated: false }, { status: 401 });
    }

    try {
        const res = await axios.get("https://graph.facebook.com/me", {
            params: {
                access_token: token,
                fields: "id,name,picture",
            },
            timeout: 5000,
        });

        return NextResponse.json({
            authenticated: true,
            user: res.data,
        });
    } catch (e) {
        // Token might be invalid/expired
        return NextResponse.json({ authenticated: false, error: "Invalid token" }, { status: 401 });
    }
}
