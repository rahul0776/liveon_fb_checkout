import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { fetchAllData, uploadJson, updateStatus, getStatus } from "@/lib/backup";
import { v4 as uuidv4 } from "uuid";

export async function POST() {
    const cookieStore = await cookies();
    const token = cookieStore.get("fb_token")?.value;

    if (!token) {
        return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    // Get User ID first
    let userId = "";
    try {
        const meRes = await fetch("https://graph.facebook.com/me?access_token=" + token).then(r => r.json());
        if (!meRes.id) throw new Error("Failed to get User ID");
        userId = meRes.id;
    } catch (e) {
        return NextResponse.json({ error: "Failed to fetch user profile" }, { status: 500 });
    }

    const existingStatus = await getStatus(userId);
    if (existingStatus && existingStatus.running && (Date.now() - existingStatus.last_updated < 60000)) {
        return NextResponse.json({ message: "Backup already running" });
    }

    // Start backup process (Note: In Vercel serverless, this must complete within timeout)
    // We will try to do as much as possible, or use Edge Runtime if needed, but for now standard Node.

    const runId = uuidv4();
    const startTime = Date.now();

    // Fire and forget promise (Node.js runtime might kill this when response returns, but 
    // allows some execution after response in some envs. Safer to await for demo.)

    // We will await it to ensure it runs, client needs to handle long loading or polling
    await (async () => {
        try {
            await updateStatus(userId, { running: true, progress: 0, step: "Initializing", last_updated: Date.now() });

            // 1. Fetch Photos (Prefer uploaded photos)
            await updateStatus(userId, { running: true, progress: 10, step: "Fetching photos...", last_updated: Date.now() });

            // Try photos/uploaded first (like Streamlit app)
            let photos = await fetchAllData("photos/uploaded?fields=images,created_time,name,place,id", token);
            if (photos.length === 0) {
                console.log("DEBUG: No uploaded photos, trying all photos");
                photos = await fetchAllData("photos?fields=images,created_time,name,place,id", token);
            }
            await uploadJson(userId, `backup_${runId}`, "photos.json", photos);

            // 2. Process Photos into "Posts" (Streamlit logic compatibility)
            // The original app treats photos as posts. We map them here.
            await updateStatus(userId, { running: true, progress: 40, step: "Processing photos as posts...", last_updated: Date.now() });

            const posts = photos.map(photo => {
                // Find largest image source
                let full_picture = null;
                if (Array.isArray(photo.images) && photo.images.length > 0) {
                    // Start with first, typically largest/newest
                    full_picture = photo.images[0].source;
                    // Or precise sort (optional, usually Facebook sends largest first)
                }

                return {
                    id: photo.id,
                    created_time: photo.created_time,
                    message: photo.name || "", // Caption often in 'name'
                    full_picture: full_picture,
                    images: full_picture ? [full_picture] : [],
                    is_photo: true
                };
            });

            await uploadJson(userId, `backup_${runId}`, "posts.json", posts);

            // 3. Summary
            await updateStatus(userId, { running: true, progress: 80, step: "Finalizing...", last_updated: Date.now() });
            const summary = {
                timestamp: new Date().toISOString(),
                total_photos: photos.length,
                total_posts: posts.length, // Matched count
                run_id: runId
            };
            await uploadJson(userId, `backup_${runId}`, "summary.json", summary);

            // Done
            await updateStatus(userId, {
                running: false,
                progress: 100,
                step: "Complete",
                last_updated: Date.now(),
                result: summary
            });

        } catch (e) {
            console.error("Backup failed", e);
            await updateStatus(userId, { running: false, error: String(e), last_updated: Date.now() });
        }
    })();

    return NextResponse.json({ message: "Backup started", runId });
}
