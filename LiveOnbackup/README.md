# LiveOn Frontend Preview

This folder now contains a single-page, frontend-only preview of the LiveOn marketing + login experience. It’s built with **Next.js 14**, **TypeScript**, and **Tailwind CSS** so you can host a polished landing page while keeping all backend wiring (Azure Functions, Stripe, Facebook OAuth) separate.

## ✨ Highlights

- Navy & gold visual identity carried over from the existing Streamlit app
- Mock data that represents real projects, memories, timeline events, and downloads
- Responsive layouts for desktop and mobile (hero marketing page + projects + memories + success flow)
- Modular React components (cards, timeline, headers, buttons) ready for real data

## 📁 Structure

```
LiveOn/
├── app/
│   └── page.tsx           # Single-page marketing + login flow
├── components/            # Layout + sections used on the homepage
├── lib/mockData.ts        # Placeholder testimonials used by the UI
├── public/media/          # Shared imagery & logos
├── package.json
└── README.md (this file)
```

## 🚀 Run locally

```bash
cd LiveOn
npm install
npm run dev
# open http://localhost:3000
```

## 🔌 Wire it up later

Integration notes:

- Replace testimonials in `lib/mockData.ts` with real stories from your customers.
- Wire the login form (`HeroLoginCard`) to your production Facebook OAuth + Azure onboarding flow.
- Update CTA copy, anchors, and contact information as your messaging evolves.

## 📦 Ready for Vercel

- Deploy the `LiveOn/` folder as a standalone Next.js project
- Configure environment variables in Vercel when you connect real integrations (`NEXT_PUBLIC_*`, Stripe keys, Azure endpoints)

## 🧭 Next steps

1. Align the mock copy with marketing tone or product messaging
2. Connect the existing backend endpoints once they’re available
3. Add analytics (Vercel Analytics or Umami) and contact forms as needed
4. Remove or adjust sections that aren’t relevant to the production launch

Enjoy showcasing LiveOn with a professional, production-ready frontend shell! 🎉
