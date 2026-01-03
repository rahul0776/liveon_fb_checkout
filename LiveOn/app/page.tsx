import Image from "next/image";
import { ArrowRight, HelpCircle, LifeBuoy, MessageCircle, ShieldCheck, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { TestimonialShowcase } from "@/components/sections/TestimonialShowcase";
import { LogoMarquee } from "@/components/sections/LogoMarquee";
import { mockTestimonials, mockFeatureCards } from "@/lib/mockData";
import { ScrollReveal } from "@/components/animations/ScrollReveal";
import { TextReveal } from "@/components/animations/TextReveal";
import { CardCarousel } from "@/components/animations/CardCarousel";
import { FlashlightCard } from "@/components/animations/FlashlightCard";

export default function Home() {
  return (
    <div className="space-y-24 overflow-x-hidden">
      <section className="relative mx-auto max-w-6xl px-4 pt-6 sm:px-6 lg:px-0">
        <ScrollReveal animation="fade" duration={0.8}>
          <div className="glass-panel navy-fade-border relative overflow-hidden px-6 py-12 sm:px-10 sm:py-16 lg:px-16 lg:py-18">
            <div className="grid-glow" />

            {/* Background clip animation */}
            <div className="absolute inset-0 z-0 bg-clip-columns bg-gradient-to-r from-transparent via-white/[0.03] to-transparent" />

            <div className="relative z-10 max-w-3xl">
              <div className="space-y-8">
                <ScrollReveal animation="slide-down" delay={200}>
                  <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-1 text-xs uppercase tracking-[0.32em] text-white/70">
                    <Sparkles className="h-3.5 w-3.5" />
                    Facebook backups reimagined
                  </div>
                </ScrollReveal>

                <div className="space-y-6">
                  <h1 className="text-4xl font-semibold leading-tight text-white sm:text-5xl lg:text-6xl">
                    <TextReveal text="Back up your Facebook." className="block" delay={400} />
                    <span className="block mt-2">
                      Bring it to life with <span className="gold-gradient-text">LiveOn</span>
                    </span>
                  </h1>
                  <ScrollReveal animation="fade" delay={800}>
                    <p className="max-w-xl text-base text-white/70 sm:text-lg">
                      LiveOn turns years of posts, photos, and reactions into a secure, story-driven archive you can revisit any time. No contracts. No hassle. Just memories preserved.
                    </p>
                  </ScrollReveal>
                </div>

                <ScrollReveal animation="slide-up" delay={1000}>
                  <div className="flex flex-wrap items-center gap-4">
                    <Button href="#login" rightIcon={<ArrowRight className="h-4 w-4" />}>
                      Start backing up
                    </Button>
                    <div className="flex items-center gap-3 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs uppercase tracking-[0.32em] text-white/55">
                      <ShieldCheck className="h-4 w-4 text-[#f6c35d]" />
                      OAuth + encrypted storage
                    </div>
                  </div>
                </ScrollReveal>

                <ScrollReveal animation="fade" delay={1200}>
                  <dl className="grid gap-6 sm:grid-cols-3">
                    {["10k+ posts", "6.4k photos", "97% 5-star reviews"].map((stat) => (
                      <div key={stat} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4 text-sm text-white/70">
                        <p className="text-xl font-semibold text-white">{stat}</p>
                        <p className="text-xs uppercase tracking-[0.28em] text-white/45">
                          from early LiveOn families
                        </p>
                      </div>
                    ))}
                  </dl>
                </ScrollReveal>
              </div>
            </div>
          </div>
        </ScrollReveal>
      </section>

      <LogoMarquee />

      <section id="how-it-works" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-0">
        <ScrollReveal animation="slide-up">
          <div className="space-y-6 text-center">
            <p className="section-heading">How it works</p>
            <h2 className="text-3xl font-semibold text-white sm:text-4xl">
              Three simple steps to safeguard your timeline
            </h2>
            <p className="mx-auto max-w-2xl text-sm text-white/65 sm:text-base">
              When you’re ready to wire up the backend, these steps will connect directly to your existing Azure Functions + Stripe flow.
            </p>
          </div>
        </ScrollReveal>

        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {[{
            step: "01",
            title: "Link with Facebook",
            copy:
              "We authenticate via Facebook OAuth, using state tokens to keep every session secure and traceable.",
          },
          {
            step: "02",
            title: "Collect & curate",
            copy:
              "Posts, photos, and reactions are sorted into chapters that you can explore with filters and timelines.",
          },
          {
            step: "03",
            title: "Download in minutes",
            copy:
              "Stripe checkout unlocks polished ZIP archives from Azure Blob Storage with expiring SAS links.",
          }].map((item, index) => (
            <ScrollReveal key={item.step} animation="slide-up" delay={index * 200}>
              <FlashlightCard className="glass-panel navy-fade-border relative overflow-hidden px-6 py-6 text-left h-full">
                <div className="grid-glow" />
                <div className="relative z-10 space-y-4">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/20 bg-white/[0.08] text-sm font-semibold text-[#f6c35d]">
                    {item.step}
                  </span>
                  <h3 className="text-lg font-semibold text-white">{item.title}</h3>
                  <p className="text-sm text-white/65">{item.copy}</p>
                </div>
              </FlashlightCard>
            </ScrollReveal>
          ))}
        </div>
      </section>

      <section id="features" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-0">
        <ScrollReveal animation="fade">
          <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
            <div className="space-y-6">
              <p className="section-heading">Features</p>
              <h2 className="text-3xl font-semibold text-white sm:text-4xl">
                More than just a backup
              </h2>
              <p className="text-sm text-white/65 sm:text-base">
                Explore your digital history in ways Facebook never allowed. Our interactive tools bring your past to life.
              </p>

              <div className="w-full max-w-md">
                <CardCarousel
                  cards={mockFeatureCards.map(card => (
                    <div key={card.id} className="glass-panel navy-fade-border p-6 mx-2">
                      <div className="text-4xl mb-4">{card.icon}</div>
                      <h3 className="text-xl font-semibold text-white mb-2">{card.title}</h3>
                      <p className="text-white/70 mb-4">{card.description}</p>
                      <div className="text-xs uppercase tracking-widest text-[#f6c35d]">{card.stats}</div>
                    </div>
                  ))}
                />
              </div>
            </div>

            <div className="relative hidden lg:block h-[500px] w-full">
              <div className="absolute inset-0 bg-gradient-to-tr from-[#f6c35d]/20 to-transparent rounded-full blur-[100px]" />
              <div className="relative h-full w-full overflow-hidden rounded-3xl border border-white/10 bg-white/5">
                <Image
                  src="/media/sample-memory-4.jpg"
                  alt="Feature preview"
                  fill
                  className="object-cover opacity-80"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#0f253d] via-transparent to-transparent" />
              </div>
            </div>
          </div>
        </ScrollReveal>
      </section>

      <section id="help" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-0">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-6">
            <ScrollReveal animation="slide-right">
              <p className="section-heading">Help center</p>
              <h2 className="text-3xl font-semibold text-white sm:text-4xl">
                Everything you need to get started
              </h2>
            </ScrollReveal>

            <div className="grid gap-4 sm:grid-cols-2">
              {[{
                title: "Guided onboarding",
                icon: <LifeBuoy className="h-5 w-5" />,
                copy: "Step-by-step walkthrough covering authentication, project creation, and downloads.",
                href: "#faq",
                label: "Read FAQ",
              },
              {
                title: "Talk to our team",
                icon: <MessageCircle className="h-5 w-5" />,
                copy: "Need help wiring in Azure Functions or Stripe webhooks? We’re happy to help.",
                href: "mailto:hello@liveon.app",
                label: "Email support",
              }].map((card, index) => (
                <ScrollReveal key={card.title} animation="slide-up" delay={index * 150}>
                  <FlashlightCard className="glass-panel navy-fade-border relative overflow-hidden px-5 py-6 text-left h-full">
                    <div className="grid-glow" />
                    <div className="relative z-10 space-y-3">
                      <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/[0.06] text-[#f6c35d]">
                        {card.icon}
                      </span>
                      <h3 className="text-lg font-semibold text-white">{card.title}</h3>
                      <p className="text-sm text-white/65">{card.copy}</p>
                      <a href={card.href} className="text-sm font-semibold text-[#f6c35d] transition hover:text-[#fbe199]">
                        {card.label} →
                      </a>
                    </div>
                  </FlashlightCard>
                </ScrollReveal>
              ))}
            </div>
          </div>

          <ScrollReveal animation="slide-left" delay={300}>
            <FlashlightCard className="glass-panel navy-fade-border relative overflow-hidden px-5 py-6 text-left h-full">
              <div className="grid-glow" />
              <div className="relative z-10 space-y-4">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/[0.06] text-[#f6c35d]">
                  <HelpCircle className="h-5 w-5" />
                </span>
                <h3 className="text-lg font-semibold text-white">Need something specific?</h3>
                <p className="text-sm text-white/65">
                  We can tailor onboarding decks and documentation for stakeholders. Share your use case and we’ll prepare a walkthrough.
                </p>
                <Button variant="outline" href="mailto:hello@liveon.app" className="border-white/20 bg-white/[0.05]">
                  Get in touch
                </Button>
              </div>
            </FlashlightCard>
          </ScrollReveal>
        </div>
      </section>

      <section id="faq" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-0">
        <ScrollReveal animation="fade">
          <div className="space-y-6 text-center">
            <p className="section-heading">FAQ</p>
            <h2 className="text-3xl font-semibold text-white sm:text-4xl">
              Answers before you even log in
            </h2>
          </div>
        </ScrollReveal>

        <div className="mt-8 space-y-4 text-left">
          {[{
            question: "Is this connected to my real Facebook account yet?",
            answer:
              "This preview uses mock data only. When you’re ready, swap the providers in `lib/mockData.ts` for your Azure Functions endpoints and Facebook OAuth flow.",
          },
          {
            question: "Where do my files live?",
            answer:
              "In production they’ll be stored in your Azure Blob Storage container with expiring SAS links generated per download.",
          },
          {
            question: "Can I change pricing or messaging later?",
            answer:
              "Absolutely. All copy and components are modular so you can update CTAs, pricing plans, or testimonials without touching business logic.",
          }].map((faq, index) => (
            <ScrollReveal key={faq.question} animation="slide-up" delay={index * 100}>
              <details className="group rounded-2xl border border-white/12 bg-white/[0.04] px-5 py-4 text-white/80">
                <summary className="cursor-pointer text-base font-semibold text-white">
                  {faq.question}
                </summary>
                <p className="mt-3 text-sm text-white/70">{faq.answer}</p>
              </details>
            </ScrollReveal>
          ))}
        </div>
      </section>

      <section id="contact" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-0">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
          <div className="space-y-4">
            <ScrollReveal animation="slide-right">
              <p className="section-heading">Contact</p>
              <h2 className="text-3xl font-semibold text-white sm:text-4xl">
                We’d love to hear from you
              </h2>
              <p className="text-sm text-white/65 sm:text-base">
                Whether you’re planning a private beta or prepping investor demos, we can provide tailored scripts, analytics, and design assets.
              </p>
            </ScrollReveal>

            <div className="grid gap-3 sm:grid-cols-2">
              {[{
                label: "Email",
                value: "hello@liveon.app",
                href: "mailto:hello@liveon.app",
              },
              {
                label: "Support hours",
                value: "Mon–Fri · 9am–6pm PST",
              },
              {
                label: "Media kit",
                value: "Request assets",
                href: "mailto:press@liveon.app",
              },
              {
                label: "Press",
                value: "press@liveon.app",
                href: "mailto:press@liveon.app",
              }].map((item, index) => (
                <ScrollReveal key={`${item.label}-${item.value}`} animation="fade" delay={index * 100}>
                  <a
                    href={item.href ?? "#"}
                    className="block h-full glass-panel navy-fade-border relative overflow-hidden px-4 py-4 text-sm text-white/70 transition hover:text-white"
                  >
                    <div className="grid-glow" />
                    <div className="relative z-10 space-y-1">
                      <p className="text-xs uppercase tracking-[0.28em] text-white/45">{item.label}</p>
                      <p className="text-base font-semibold text-white">{item.value}</p>
                    </div>
                  </a>
                </ScrollReveal>
              ))}
            </div>
          </div>

          <ScrollReveal animation="slide-left" delay={200} className="hidden lg:block">
            <div className="relative h-full overflow-hidden rounded-3xl border border-white/12 bg-white/[0.08]">
              <Image
                src="/media/sample-memory-4.jpg"
                alt="LiveOn scrapbook preview"
                fill
                sizes="320px"
                className="object-cover"
              />
            </div>
          </ScrollReveal>
        </div>
      </section>

      <ScrollReveal animation="fade">
        <TestimonialShowcase testimonials={mockTestimonials} />
      </ScrollReveal>

      <section className="mx-auto max-w-6xl px-4 pb-24 text-center sm:px-6 lg:px-0">
        <ScrollReveal animation="slide-up">
          <div className="glass-panel navy-fade-border relative overflow-hidden px-6 py-12 sm:px-10">
            <div className="grid-glow" />
            <div className="relative z-10 space-y-6">
              <h2 className="text-3xl font-semibold text-white sm:text-4xl">
                Ready to give stakeholders a tour?
              </h2>
              <p className="mx-auto max-w-2xl text-sm text-white/65 sm:text-base">
                Deploy this frontend to Vercel, connect your Azure Functions and Stripe credentials, and invite early adopters to secure their Facebook history today.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-4">
                <Button href="#login">Start backup</Button>
                <Button variant="outline" href="mailto:hello@liveon.app" className="border-white/20 bg-white/[0.05]">
                  Talk to our team
                </Button>
              </div>
            </div>
          </div>
        </ScrollReveal>
      </section>
    </div>
  );
}
