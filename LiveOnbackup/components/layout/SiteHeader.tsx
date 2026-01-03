"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import clsx from "clsx";

const links = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#help", label: "Help" },
  { href: "#faq", label: "FAQ" },
  { href: "#contact", label: "Contact" },
  { href: "#testimonials", label: "Testimonials" },
];

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  const toggle = () => setOpen((prev) => !prev);
  const close = () => setOpen(false);

  return (
    <header className="sticky top-0 z-40 border-b border-white/8 backdrop-blur-md bg-[#0f253dcc]/85">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-0">
        <Link
          href="/"
          className="flex items-center gap-3 text-lg font-semibold tracking-wide"
          onClick={close}
        >
          <div className="relative h-10 w-10 overflow-hidden rounded-lg shadow-ring bg-white flex items-center justify-center">
            <Image
              src="/media/logo.png"
              alt="LiveOn Logo"
              width={40}
              height={40}
              className="object-contain p-1"
            />
          </div>
          <span className="flex flex-col leading-none text-sm uppercase text-white/80">
            <span className="text-base font-black tracking-[0.25em] text-white">
              LiveOn
            </span>
            <span className="text-[0.7rem] tracking-[0.32em] text-gold-300/90">
              Facebook Backups
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-8 text-sm font-medium text-white/80 md:flex">
          {links.map((link) => (
            <a key={link.href} href={link.href} className="transition hover:text-white">
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-4 md:flex">
          <a
            href="#login"
            className="rounded-lg bg-[#f6c35d] px-5 py-2 text-sm font-semibold text-[#0f253d] shadow-ring transition hover:shadow-lg hover:brightness-105"
          >
            Start Backup
          </a>
        </div>

        <button
          onClick={toggle}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 text-white/80 transition hover:text-white md:hidden"
          aria-label="Toggle navigation"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      <div
        className={clsx(
          "md:hidden",
          open ? "max-h-[360px] border-t border-white/10" : "max-h-0 overflow-hidden"
        )}
      >
        <div className="space-y-2 px-4 pb-5 pt-3 text-sm font-medium text-white/80">
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={close}
              className="block rounded-lg border border-transparent px-3 py-2 transition hover:border-white/10 hover:bg-white/[0.04] hover:text-white"
            >
              {link.label}
            </a>
          ))}

          <a
            href="#login"
            onClick={close}
            className="block rounded-lg bg-[#f6c35d] px-3 py-2 text-center font-semibold text-[#0f253d] shadow-sm transition hover:brightness-110"
          >
            Start Backup
          </a>
        </div>
      </div>
    </header>
  );
}
