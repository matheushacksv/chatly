<script setup lang="ts">
import { Icon } from '@iconify/vue'

interface Rule { field: string; op: string; value: string }
interface Logic { combinator: string; rules: Rule[] }

const props = defineProps<{
  logic: Logic
  instances?: any[]
  members?: any[]
}>()

// vtype define como o campo "valor" é editado
const SYSTEM_FIELDS = [
  { value: 'contact.name', label: 'Contato · nome', vtype: 'text' },
  { value: 'contact.email', label: 'Contato · email', vtype: 'text' },
  { value: 'contact.phone', label: 'Contato · telefone', vtype: 'text' },
  { value: 'conversation.status', label: 'Conversa · status', vtype: 'select',
    options: [{ value: 'open', label: 'Aberta' }, { value: 'closed', label: 'Fechada' }] },
  { value: 'conversation.assigned_to', label: 'Conversa · responsável', vtype: 'member' },
  { value: 'conversation.instance', label: 'Conversa · instância', vtype: 'instance' },
  { value: 'conversation.ai_active', label: 'Conversa · IA ativa', vtype: 'boolean' },
  { value: 'message.content', label: 'Mensagem · conteúdo', vtype: 'text' },
]

const OPERATORS = [
  { value: 'equals', label: 'igual a' },
  { value: 'not_equals', label: 'diferente de' },
  { value: 'contains', label: 'contém' },
  { value: 'not_contains', label: 'não contém' },
  { value: 'is_empty', label: 'está vazio' },
  { value: 'is_not_empty', label: 'não está vazio' },
]

const CUSTOM_PREFIX = 'contact.custom_fields.'

// garante estrutura mínima
if (!props.logic.combinator) props.logic.combinator = 'AND'
if (!props.logic.rules) props.logic.rules = []

const isCustom = (r: Rule) => (r.field || '').startsWith(CUSTOM_PREFIX)
const customKey = (r: Rule) => isCustom(r) ? r.field.slice(CUSTOM_PREFIX.length) : ''
const fieldSelectValue = (r: Rule) => isCustom(r) ? '__custom__' : r.field

const fieldMeta = (r: Rule) => SYSTEM_FIELDS.find(f => f.value === r.field)
// campo personalizado = texto livre; campo de sistema = vtype declarado
const valueType = (r: Rule) => isCustom(r) ? 'text' : (fieldMeta(r)?.vtype ?? 'text')

const onFieldSelect = (r: Rule, val: string) => {
  r.field = val === '__custom__' ? CUSTOM_PREFIX : val
  r.value = ''  // reseta valor ao trocar de campo
}
const onCustomKey = (r: Rule, key: string) => {
  r.field = CUSTOM_PREFIX + key.trim()
}

const noValue = (op: string) => op === 'is_empty' || op === 'is_not_empty'

const addRule = () => props.logic.rules.push({ field: 'contact.name', op: 'equals', value: '' })
const removeRule = (i: number) => props.logic.rules.splice(i, 1)
</script>

<template>
  <div class="space-y-2">
    <div class="flex items-center gap-2">
      <span class="text-[10px] font-mono text-neutral-600 uppercase tracking-widest">Combinar regras com</span>
      <div class="flex border border-white/10">
        <button
          type="button"
          @click="props.logic.combinator = 'AND'"
          class="px-2.5 py-1 text-[10px] font-mono uppercase tracking-widest transition-colors"
          :class="props.logic.combinator === 'AND' ? 'bg-accent text-white' : 'text-neutral-500 hover:text-neutral-300'"
        >E</button>
        <button
          type="button"
          @click="props.logic.combinator = 'OR'"
          class="px-2.5 py-1 text-[10px] font-mono uppercase tracking-widest transition-colors"
          :class="props.logic.combinator === 'OR' ? 'bg-accent text-white' : 'text-neutral-500 hover:text-neutral-300'"
        >OU</button>
      </div>
    </div>

    <div v-if="props.logic.rules.length === 0" class="text-[10px] font-mono text-neutral-700 uppercase tracking-widest">
      Sem regras — condição sempre verdadeira
    </div>

    <div
      v-for="(rule, i) in props.logic.rules"
      :key="i"
      class="bg-canvas border border-white/10 p-2 space-y-2"
    >
      <div class="flex items-start gap-2">
        <div class="flex-1 min-w-0 space-y-2">
          <!-- campo -->
          <select
            :value="fieldSelectValue(rule)"
            @change="(e: any) => onFieldSelect(rule, e.target.value)"
            class="w-full bg-surface border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20"
          >
            <option v-for="f in SYSTEM_FIELDS" :key="f.value" :value="f.value">{{ f.label }}</option>
            <option value="__custom__">Campo personalizado…</option>
          </select>

          <input
            v-if="isCustom(rule)"
            :value="customKey(rule)"
            @input="(e: any) => onCustomKey(rule, e.target.value)"
            type="text"
            placeholder="chave do campo personalizado"
            class="w-full bg-surface border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20"
          />

          <div class="flex flex-wrap gap-2">
            <!-- operador -->
            <select
              v-model="rule.op"
              class="shrink-0 bg-surface border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20"
            >
              <option v-for="o in OPERATORS" :key="o.value" :value="o.value">{{ o.label }}</option>
            </select>

            <!-- valor: editor varia por tipo de campo -->
            <template v-if="!noValue(rule.op)">
              <!-- status / opções fixas -->
              <select
                v-if="valueType(rule) === 'select'"
                v-model="rule.value"
                class="grow basis-28 min-w-0 bg-surface border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20"
              >
                <option value="">—</option>
                <option v-for="o in fieldMeta(rule)?.options" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>

              <!-- IA ativa / booleano -->
              <select
                v-else-if="valueType(rule) === 'boolean'"
                v-model="rule.value"
                class="grow basis-28 min-w-0 bg-surface border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20"
              >
                <option value="">—</option>
                <option value="true">Sim (ativa)</option>
                <option value="false">Não (inativa)</option>
              </select>

              <!-- instância da conta -->
              <select
                v-else-if="valueType(rule) === 'instance'"
                v-model="rule.value"
                class="grow basis-28 min-w-0 bg-surface border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20"
              >
                <option value="">—</option>
                <option
                  v-for="inst in props.instances"
                  :key="inst.id"
                  :value="inst.instance_name || inst.name"
                >{{ inst.instance_name || inst.name }}</option>
              </select>

              <!-- responsável / membro da org -->
              <select
                v-else-if="valueType(rule) === 'member'"
                v-model="rule.value"
                class="grow basis-28 min-w-0 bg-surface border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20"
              >
                <option value="">—</option>
                <option
                  v-for="m in props.members"
                  :key="m.id || m.user_id"
                  :value="m.email || m.user_email"
                >{{ m.name || m.email || m.user_email }}</option>
              </select>

              <!-- texto livre -->
              <input
                v-else
                v-model="rule.value"
                type="text"
                placeholder="valor"
                class="grow basis-28 min-w-0 bg-surface border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20"
              />
            </template>
          </div>
        </div>

        <button
          type="button"
          @click="removeRule(i)"
          class="p-1 text-neutral-600 hover:text-red-400 transition-colors shrink-0"
          title="Remover regra"
        >
          <Icon icon="solar:close-circle-bold-duotone" class="text-sm" />
        </button>
      </div>
    </div>

    <button
      type="button"
      @click="addRule"
      class="text-[10px] font-mono uppercase tracking-widest text-accent hover:text-accent/80 px-2.5 py-1 border border-accent/30"
    >
      + Regra
    </button>
  </div>
</template>
