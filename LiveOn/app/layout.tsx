import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { SiteFooter } from "@/components/layout/SiteFooter";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LiveOn · Facebook Backup Experience",
  description:
    "Preview the LiveOn Facebook backup journey: professional dashboards, curated memories, and premium download flows.",
  metadataBase: new URL("https://liveon-preview.local"),
  openGraph: {
    title: "LiveOn · Preserve every memory",
    description:
      "See the polished LiveOn frontend that will host secure Facebook backups with Azure and Stripe integrations.",
    images: [
      {
        url: "/media/banner.png",
        width: 1600,
        height: 900,
        alt: "LiveOn Facebook backup preview",
      },
    ],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <div className="relative min-h-screen overflow-hidden">
          <div className="pointer-events-none absolute inset-0 opacity-80">
            <div className="grid-glow" />
          </div>
          <div className="relative z-10 flex min-h-screen flex-col">
            <SiteHeader />
            <main className="flex-1 pt-12 pb-16">
              {children}
            </main>
            <SiteFooter />
          </div>
        </div>
      </body>
    </html>
  );
}
