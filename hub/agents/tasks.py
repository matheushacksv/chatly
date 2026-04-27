from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_agent_document(doc_id: int):
    from agents.models import AgentDocument

    try:
        doc = AgentDocument.objects.get(id=doc_id)
        doc.status = 'processing'
        doc.save(update_fields=['status'])

        url = doc.file_url
        ext = url.rsplit('.', 1)[-1].lower()

        if ext == 'pdf':
            import httpx
            from pypdf import PdfReader
            from io import BytesIO

            resp = httpx.get(url)
            reader = PdfReader(BytesIO(resp.content))
            content = '\n'.join(page.extract_text() or '' for page in reader.pages)
        else:
            import httpx
            content = httpx.get(url).text
        
        doc.content = content[:50000]
        doc.status = 'ready'
        doc.save(update_fields=['content', 'status'])
    except Exception as e:
        logger.error(f'process_agent_document {doc_id}: {e}')
        AgentDocument.objects.filter(id=doc_id).update(status='failed')