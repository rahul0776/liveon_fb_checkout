"use client";

import { Button } from "@/components/ui/Button";
import { ArrowRight } from "lucide-react";

export function LoginButton() {
    const handleLogin = () => {
        window.location.href = "/api/auth/login";
    };

    return (
        <Button onClick={handleLogin} rightIcon={<ArrowRight className="h-4 w-4" />}>
            Log in with Facebook
        </Button>
    );
}
