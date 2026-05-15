<script setup lang="ts">
definePageMeta({ layout: 'landing' })

useSeoMeta({
  title: 'Política de Cookies',
  description: 'O que são cookies, como a ChatlyAi os utiliza e como gerenciar seu consentimento.',
})

const { consent, accept, reject } = useCookieConsent()
</script>

<template>
  <article class="max-w-3xl mx-auto px-6 pt-20">
    <p class="field-label">Legal</p>
    <h1 class="text-3xl md:text-4xl font-medium text-white tracking-tight">Política de Cookies</h1>
    <p class="mt-3 text-sm font-mono text-neutral-600">Vigência: 15 de maio de 2026</p>

    <div class="mt-8 bg-surface border border-white/10 p-4">
      <p class="text-xs font-mono text-neutral-500 leading-relaxed">
        ⚠ Rascunho. Modelo genérico baseado na LGPD — revisar com assessoria jurídica antes da publicação.
      </p>
    </div>

    <div class="mt-10 space-y-10 text-sm text-neutral-400 leading-relaxed">
      <section>
        <h2 class="text-white text-base font-medium mb-3">1. O que são cookies</h2>
        <p>
          Cookies são pequenos arquivos armazenados no seu navegador. Também usamos tecnologias
          equivalentes, como o <code class="text-neutral-200">localStorage</code>, para guardar
          preferências e manter sua sessão ativa.
        </p>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">2. Categorias que usamos</h2>
        <ul class="list-disc pl-5 space-y-1.5">
          <li><strong class="text-neutral-200">Essenciais:</strong> autenticação e manutenção da sessão (tokens JWT). Sem eles a plataforma não funciona.</li>
          <li><strong class="text-neutral-200">Preferências:</strong> tema e ajustes de interface.</li>
          <li><strong class="text-neutral-200">Analytics:</strong> monitoramento de erros e desempenho (Sentry), para melhorar o serviço.</li>
        </ul>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">3. Gestão do consentimento</h2>
        <p>
          Na primeira visita exibimos um banner para você aceitar ou recusar cookies não essenciais.
          A escolha é gravada no <code class="text-neutral-200">localStorage</code> e respeitada nas
          próximas visitas. Cookies essenciais são sempre necessários.
        </p>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">4. Revogar ou alterar a escolha</h2>
        <p class="mb-4">
          Você pode alterar sua decisão a qualquer momento abaixo, ou limpando os dados do site no
          seu navegador.
        </p>
        <div class="bg-surface border border-white/10 p-5 flex flex-col sm:flex-row sm:items-center gap-4">
          <p class="text-sm flex-1">
            Status atual:
            <strong class="text-neutral-200">
              {{ consent === 'accepted' ? 'Aceito' : consent === 'rejected' ? 'Recusado' : 'Sem decisão' }}
            </strong>
          </p>
          <div class="flex items-center gap-3 shrink-0">
            <button
              class="px-4 py-2 text-xs font-mono uppercase tracking-wider text-neutral-400 hover:text-white transition-colors"
              @click="reject"
            >
              Recusar
            </button>
            <button
              class="px-5 py-2.5 border border-white/10 hover:border-accent transition-colors text-xs font-medium uppercase tracking-wider text-white"
              @click="accept"
            >
              Aceitar
            </button>
          </div>
        </div>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">5. Mais informações</h2>
        <p>
          O tratamento de dados pessoais está descrito na
          <NuxtLink to="/privacidade" class="text-accent hover:text-white transition-colors">Política de Privacidade</NuxtLink>.
          Dúvidas:
          <a href="mailto:privacidade@chatly.ia.br" class="text-accent hover:text-white transition-colors">privacidade@chatly.ia.br</a>.
        </p>
      </section>
    </div>
  </article>
</template>
