"use client";

import { Marquee } from "@/components/animations/Marquee";
import { mockLogos } from "@/lib/mockData";

export function LogoMarquee() {
    return (
        <section className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-0">
            <div className="space-y-6 text-center">
                <p className="section-heading">Trusted by families and businesses</p>
                <h2 className="text-2xl font-semibold text-white sm:text-3xl">
                    Join thousands preserving their digital legacy
                </h2>
            </div>

            <Marquee speed={30} className="mt-10">
                {mockLogos.map((logo) => (
                    <div
                        key={logo.name}
                        className="flex h-20 w-40 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] px-6 backdrop-blur-sm"
                    >
                        <span className="text-lg font-semibold text-white/70">{logo.name}</span>
                    </div>
                ))}
            </Marquee>
        </section>
    );
}
