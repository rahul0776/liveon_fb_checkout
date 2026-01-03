import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getStatus } from "@/lib/backup";
import axios from "axios";

export async function GET() {
    const cookieStore = await cookies();
    const token = cookieStore.get("fb_token")?.value;

    if (!token) {
        return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    try {
        // Get User ID
        const meRes = await axios.get(`https://graph.facebook.com/me?access_token=${token}`);
        const userId = meRes.data.id;

        const status = await getStatus(userId);
        return NextResponse.json(status || { running: false, progress: 0 });

    } catch (e) {
        return NextResponse.json({ error: "Failed to check status" }, { status: 500 });
    }
}
