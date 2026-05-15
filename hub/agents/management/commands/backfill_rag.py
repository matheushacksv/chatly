from django.core.management.base import BaseCommand

from agents.models import AgentDocument
from agents.tasks import index_document


class Command(BaseCommand):
    help = 'Re-chunka e gera embeddings dos documentos ready (RAG). Idempotente.'

    def add_arguments(self, parser):
        parser.add_argument('--agent', type=int, help='Limita a um agent_id específico.')

    def handle(self, *args, **options):
        qs = AgentDocument.objects.filter(status='ready')
        agent_id = options.get('agent')
        if agent_id:
            qs = qs.filter(agent_id=agent_id)

        total = qs.count()
        self.stdout.write(f'{total} documento(s) ready para indexar')

        ok = fail = 0
        for doc in qs.iterator():
            try:
                n = index_document(doc)
                ok += 1
                self.stdout.write(self.style.SUCCESS(f'  [{doc.id}] {doc.name}: {n} chunks'))
            except Exception as e:
                fail += 1
                self.stderr.write(self.style.ERROR(f'  [{doc.id}] {doc.name}: FALHOU — {e}'))

        self.stdout.write(self.style.SUCCESS(f'Concluído: {ok} ok, {fail} falha(s)'))
