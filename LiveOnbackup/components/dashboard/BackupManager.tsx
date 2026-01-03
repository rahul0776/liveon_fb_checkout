"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import axios from "axios";

export function BackupManager({ user }: { user: any }) {
    const [status, setStatus] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [runId, setRunId] = useState<string | null>(null);

    const fetchStatus = async () => {
        try {
            const res = await axios.get("/api/backup/status");
            setStatus(res.data);
            if (res.data.result && res.data.result.run_id) {
                setRunId(res.data.result.run_id);
            }
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 3000);
        return () => clearInterval(interval);
    }, []);

    const startBackup = async () => {
        setLoading(true);
        try {
            const res = await axios.post("/api/backup/start");
            setRunId(res.data.runId);
            // Status poller will pick it up
        } catch (e) {
            alert("Failed to start backup");
        } finally {
            setLoading(false);
        }
    };

    const handleCheckout = async () => {
        if (!runId && !status?.result?.run_id) return;
        try {
            const res = await axios.post("/api/checkout/create-session", {
                runId: runId || status?.result?.run_id
            });
            if (res.data.url) {
                window.location.href = res.data.url;
            }
        } catch (e) {
            alert("Checkout failed");
        }
    };

    if (!status) return <div className="text-white">Loading status...</div>;

    return (
        <div className="glass-panel navy-fade-border p-8 rounded-2xl max-w-2xl mx-auto text-center">
            <h2 className="text-2xl font-bold text-white mb-4">Welcome, {user.name}</h2>

            {status.running ? (
                <div className="space-y-4">
                    <div className="text-gold text-lg animate-pulse">Running Backup: {status.step}</div>
                    <div className="w-full bg-white/10 rounded-full h-4">
                        <div
                            className="bg-[#f6c35d] h-4 rounded-full transition-all duration-500"
                            style={{ width: `${status.progress}%` }}
                        />
                    </div>
                </div>
            ) : status.result ? (
                <div className="space-y-6">
                    <div className="text-green-400 font-bold text-xl">Backup Complete!</div>
                    <div className="grid grid-cols-2 gap-4 text-white/70">
                        <div className="bg-white/5 p-4 rounded-lg">
                            <div className="text-2xl text-white">{status.result.total_photos}</div>
                            <div>Photos</div>
                        </div>
                        <div className="bg-white/5 p-4 rounded-lg">
                            <div className="text-2xl text-white">{status.result.total_posts}</div>
                            <div>Posts</div>
                        </div>
                    </div>
                    <div className="flex justify-center gap-4">
                        <Button onClick={handleCheckout}>Unlock & Download ($9.99)</Button>
                    </div>
                </div>
            ) : (
                <div className="space-y-6">
                    <p className="text-white/70">
                        Ready to backup your profile? This will fetch your photos and posts and save them securely.
                    </p>
                    <Button onClick={startBackup} disabled={loading}>
                        {loading ? "Starting..." : "Start New Backup"}
                    </Button>
                </div>
            )}
        </div>
    );
}
