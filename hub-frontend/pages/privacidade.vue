<script setup lang="ts">
definePageMeta({ layout: 'landing' })

useSeoMeta({
  title: 'Política de Privacidade',
  description: 'Como a ChatlyAi coleta, usa e protege seus dados pessoais — conforme a LGPD.',
})
</script>

<template>
  <article class="max-w-3xl mx-auto px-6 pt-20">
    <p class="field-label">Legal</p>
    <h1 class="text-3xl md:text-4xl font-medium text-white tracking-tight">Política de Privacidade</h1>
    <p class="mt-3 text-sm font-mono text-neutral-600">Vigência: 15 de maio de 2026</p>

    <!-- Aviso de rascunho -->
    <div class="mt-8 bg-surface border border-white/10 p-4">
      <p class="text-xs font-mono text-neutral-500 leading-relaxed">
        ⚠ Rascunho. Este texto é um modelo genérico baseado na LGPD (Lei nº 13.709/2018)
        e deve ser revisado por assessoria jurídica antes da publicação definitiva.
      </p>
    </div>

    <div class="mt-10 space-y-10 text-sm text-neutral-400 leading-relaxed">
      <section>
        <h2 class="text-white text-base font-medium mb-3">1. Controlador dos dados</h2>
        <p>
          O controlador dos dados pessoais tratados nesta plataforma é a <strong class="text-neutral-200">Hack
          Softwares</strong>, responsável pelo produto ChatlyAi. Contato do encarregado (DPO):
          <a href="mailto:privacidade@chatly.ia.br" class="text-accent hover:text-white transition-colors">privacidade@chatly.ia.br</a>.
        </p>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">2. Dados que coletamos</h2>
        <ul class="list-disc pl-5 space-y-1.5">
          <li><strong class="text-neutral-200">Cadastro:</strong> nome, e-mail, senha e dados da organização.</li>
          <li><strong class="text-neutral-200">Contatos e conversas:</strong> números de telefone, mensagens, anexos e mídia trocados via WhatsApp.</li>
          <li><strong class="text-neutral-200">Uso:</strong> registros de acesso, endereço IP e dados técnicos do dispositivo.</li>
          <li><strong class="text-neutral-200">Cookies:</strong> conforme a <NuxtLink to="/cookies" class="text-accent hover:text-white transition-colors">Política de Cookies</NuxtLink>.</li>
        </ul>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">3. Finalidade do tratamento</h2>
        <p>
          Usamos os dados para operar a plataforma de atendimento, autenticar usuários, processar
          mensagens com agentes de IA, prestar suporte, cumprir obrigações legais e melhorar o serviço.
        </p>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">4. Base legal</h2>
        <p>
          O tratamento se fundamenta na execução de contrato, no cumprimento de obrigação legal, no
          legítimo interesse e, quando aplicável, no consentimento do titular (art. 7º da LGPD).
        </p>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">5. Compartilhamento com terceiros</h2>
        <p class="mb-2">Compartilhamos dados apenas com operadores necessários ao funcionamento do serviço:</p>
        <ul class="list-disc pl-5 space-y-1.5">
          <li><strong class="text-neutral-200">WhatsApp / EvoGO:</strong> envio e recebimento de mensagens.</li>
          <li><strong class="text-neutral-200">Provedores de IA</strong> (OpenAI, Anthropic, Groq): processamento das respostas dos agentes.</li>
          <li><strong class="text-neutral-200">Infraestrutura e monitoramento:</strong> hospedagem e detecção de erros.</li>
        </ul>
        <p class="mt-2">Não vendemos dados pessoais a terceiros.</p>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">6. Retenção</h2>
        <p>
          Os dados são mantidos enquanto a conta estiver ativa e pelo prazo necessário ao cumprimento
          de obrigações legais. Após esse período, são eliminados ou anonimizados.
        </p>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">7. Direitos do titular</h2>
        <p class="mb-2">Nos termos do art. 18 da LGPD, você pode solicitar:</p>
        <ul class="list-disc pl-5 space-y-1.5">
          <li>confirmação da existência de tratamento e acesso aos dados;</li>
          <li>correção de dados incompletos, inexatos ou desatualizados;</li>
          <li>anonimização, bloqueio ou eliminação de dados desnecessários;</li>
          <li>portabilidade e informação sobre o compartilhamento;</li>
          <li>revogação do consentimento.</li>
        </ul>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">8. Segurança</h2>
        <p>
          Adotamos medidas técnicas e organizacionais para proteger os dados, incluindo criptografia
          de credenciais sensíveis e controle de acesso por organização.
        </p>
      </section>

      <section>
        <h2 class="text-white text-base font-medium mb-3">9. Contato</h2>
        <p>
          Dúvidas ou solicitações sobre privacidade:
          <a href="mailto:privacidade@chatly.ia.br" class="text-accent hover:text-white transition-colors">privacidade@chatly.ia.br</a>.
        </p>
      </section>
    </div>
  </article>
</template>
