<script setup lang="ts">
import { Icon } from '@iconify/vue'

definePageMeta({ layout: 'landing' })

// Login/registro vivem no domínio da aplicação (app.*).
const appUrl = useRuntimeConfig().public.appUrl
const appLink = (path: string) => `${appUrl}${path}`

useSeoMeta({
  title: 'Atendimento WhatsApp com agentes de IA',
  description:
    'ChatlyAi — plataforma multi-tenant para atender no WhatsApp com agentes de IA, mensagens em tempo real e CRM integrado.',
})

const features = [
  {
    icon: 'solar:chat-round-dots-bold-duotone',
    title: 'Atendimento WhatsApp',
    desc: 'Conecte suas instâncias e centralize todas as conversas em uma inbox em tempo real.',
  },
  {
    icon: 'solar:cpu-bolt-bold-duotone',
    title: 'Agentes de IA',
    desc: 'Crie agentes com OpenAI, Anthropic ou Groq. Troque de provedor sem refazer nada.',
  },
  {
    icon: 'solar:document-text-bold-duotone',
    title: 'RAG com documentos',
    desc: 'Envie PDFs e documentos — o agente responde com base no seu conhecimento.',
  },
  {
    icon: 'solar:bolt-bold-duotone',
    title: 'Tempo real',
    desc: 'Mensagens, status e novas conversas chegam na hora via WebSocket.',
  },
  {
    icon: 'solar:users-group-rounded-bold-duotone',
    title: 'Multi-tenant e CRM',
    desc: 'Organizações isoladas, contatos, anotações e etiquetas para gerir cada cliente.',
  },
  {
    icon: 'solar:settings-bold-duotone',
    title: 'Automações',
    desc: 'Dispare mensagens, mude etiquetas e integre fluxos sem escrever código.',
  },
]

const steps = [
  {
    n: '01',
    title: 'Conecte o WhatsApp',
    desc: 'Crie uma instância e leia o QR Code. Em segundos seu número está na plataforma.',
  },
  {
    n: '02',
    title: 'Crie seu agente de IA',
    desc: 'Defina o comportamento, escolha o provedor e anexe documentos para o RAG.',
  },
  {
    n: '03',
    title: 'Atenda e acompanhe',
    desc: 'A IA responde sozinha; sua equipe assume quando quiser, tudo numa inbox só.',
  },
]
</script>

<template>
  <div>
    <!-- Hero -->
    <section class="relative overflow-hidden">
      <div class="beam-border-v absolute left-[20%]"></div>
      <div class="beam-border-v absolute left-auto right-[20%]" style="animation-delay: 2.5s"></div>

      <div class="max-w-4xl mx-auto px-6 pt-24 pb-20 text-center relative z-10">
        <p class="field-label text-center !mb-6">Plataforma de atendimento com IA</p>
        <h1 class="text-4xl md:text-6xl font-medium text-white tracking-tight leading-[1.1]">
          Atenda no WhatsApp com
          <span class="text-accent">agentes de IA</span>
        </h1>
        <p class="mt-6 text-base md:text-lg text-neutral-400 max-w-2xl mx-auto">
          Centralize conversas, automatize respostas e gerencie seus contatos — tudo numa
          plataforma multi-tenant em tempo real.
        </p>

        <div class="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <a
            :href="appLink('/register')"
            class="relative inline-flex items-center justify-center px-8 py-4 border border-white/10 hover:border-accent transition-colors group w-full sm:w-auto"
          >
            <div class="corner-tl"></div>
            <div class="corner-br"></div>
            <span class="text-white text-sm font-medium uppercase tracking-wider">Começar agora</span>
          </a>
          <a
            :href="appLink('/login')"
            class="inline-flex items-center justify-center px-8 py-4 text-sm font-mono uppercase tracking-wider text-neutral-400 hover:text-white transition-colors w-full sm:w-auto"
          >
            Já tenho conta →
          </a>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section id="recursos" class="max-w-6xl mx-auto px-6 pt-12 scroll-mt-20">
      <div class="mb-10">
        <p class="field-label">Recursos</p>
        <h2 class="text-2xl md:text-3xl font-medium text-white tracking-tight">
          Tudo para atender melhor
        </h2>
      </div>

      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="f in features"
          :key="f.title"
          class="bg-surface border border-white/5 p-6 relative overflow-hidden hover:border-white/10 transition-colors"
        >
          <Icon :icon="f.icon" class="text-3xl text-accent mb-4" />
          <h3 class="text-white text-sm font-medium mb-2">{{ f.title }}</h3>
          <p class="text-sm text-neutral-500 leading-relaxed">{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <!-- Como funciona -->
    <section id="como-funciona" class="max-w-6xl mx-auto px-6 pt-24 scroll-mt-20">
      <div class="mb-10">
        <p class="field-label">Como funciona</p>
        <h2 class="text-2xl md:text-3xl font-medium text-white tracking-tight">
          No ar em três passos
        </h2>
      </div>

      <div class="grid md:grid-cols-3 gap-4">
        <div
          v-for="s in steps"
          :key="s.n"
          class="bg-surface border border-white/5 p-6 relative overflow-hidden hover:border-white/10 transition-colors"
        >
          <div class="beam-border-h"></div>
          <p class="text-4xl font-mono text-white/10 mb-4">{{ s.n }}</p>
          <h3 class="text-white text-sm font-medium mb-2">{{ s.title }}</h3>
          <p class="text-sm text-neutral-500 leading-relaxed">{{ s.desc }}</p>
        </div>
      </div>
    </section>

    <!-- CTA final -->
    <section class="max-w-6xl mx-auto px-6 pt-24">
      <div class="bg-surface border border-white/5 p-12 text-center relative overflow-hidden">
        <div class="beam-border-h"></div>
        <h2 class="text-2xl md:text-3xl font-medium text-white tracking-tight">
          Pronto para começar?
        </h2>
        <p class="mt-3 text-neutral-400 max-w-md mx-auto">
          Crie sua organização e conecte o primeiro número em minutos.
        </p>
        <a
          :href="appLink('/register')"
          class="mt-8 relative inline-flex items-center justify-center px-8 py-4 border border-white/10 hover:border-accent transition-colors"
        >
          <div class="corner-tl"></div>
          <div class="corner-br"></div>
          <span class="text-white text-sm font-medium uppercase tracking-wider">Criar organização</span>
        </a>
      </div>
    </section>
  </div>
</template>
