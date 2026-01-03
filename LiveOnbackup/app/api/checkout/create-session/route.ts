import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import Stripe from "stripe";
import axios from "axios";

const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY;
const stripe = STRIPE_SECRET_KEY ? new Stripe(STRIPE_SECRET_KEY, { apiVersion: "2024-12-18.acacia" as any }) : null;

export async function POST(request: Request) {
    if (!stripe) {
        return NextResponse.json({ error: "Stripe not configured" }, { status: 500 });
    }

    const cookieStore = await cookies();
    const token = cookieStore.get("fb_token")?.value;

    if (!token) {
        return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    try {
        // Get User ID
        const meRes = await axios.get(`https://graph.facebook.com/me?access_token=${token}`);
        const userId = meRes.data.id;
        const { runId } = await request.json(); // Pass the backup run ID

        const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000";

        const session = await stripe.checkout.sessions.create({
            payment_method_types: ["card"],
            line_items: [
                {
                    price_data: {
                        currency: "usd",
                        product_data: {
                            name: "LiveOn Facebook Backup Premium",
                            description: `Backup ID: ${runId}`,
                        },
                        unit_amount: 999, // $9.99
                    },
                    quantity: 1,
                },
            ],
            mode: "payment",
            success_url: `${baseUrl}?payment_success=true&session_id={CHECKOUT_SESSION_ID}`,
            cancel_url: `${baseUrl}?payment_canceled=true`,
            metadata: {
                userId: userId,
                runId: runId
            },
        });

        return NextResponse.json({ url: session.url });

    } catch (e) {
        console.error("Stripe error", e);
        return NextResponse.json({ error: "Checkout failed" }, { status: 500 });
    }
}
