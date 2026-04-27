import re
import json
import httpx
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.calculator import CalculatorTools
from agno.tools.wikipedia import WikipediaTools

BUILTIN_TOOLS = {
    'duckduckgo': DuckDuckGoTools,
    'calculator': CalculatorTools,
    'wikipedia': WikipediaTools
}

def extract_template_params(url: str, body: str) -> list[str]:
    pattern = r'\{(\w+)\}'
    params = set(re.findall(pattern, url))
    params.update(re.findall(pattern, body or ''))
    return sorted(params)


def _fill_template(template: str, kwargs: dict) -> str:
    """Substitui {variavel} no template usando regex, sem usar str.format().
    Evita KeyError quando o template contém JSON com chaves como {"chave": ...}.
    """
    return re.sub(r'\{(\w+)\}', lambda m: str(kwargs.get(m.group(1), m.group(0))), template)


def build_http_function(tool):
    '''
    Cria uma função Python com assinatura dinâmica baseada nos placeholders
    {variavel} da URL e do body_template. O Agno inspeciona a assinatura para
    montar o JSON Schema que a IA usa ao chamar a tool
    '''

    params = extract_template_params(tool.url, tool.body_template)

    _url = tool.url
    _headers = json.loads(tool.headers or '{}')
    _body = tool.body_template
    _method = tool.method

    param_str = ', '.join(params)
    sig_args = ', '.join(f'"{p}": {p}' for p in params)

    fn_src = f'''
def {tool.name}({param_str}):
    kwargs = {{{sig_args}}}
    url = _fill_template(_url, kwargs)
    body = json.loads(_fill_template(_body, kwargs)) if _body else None
    try:
        resp = httpx.request(_method, url, json=body, headers=_headers, timeout=15)
        return resp.text
    except Exception as exc:
        return f"Erro ao chamar a tool: {{exc}}"
    '''

    ns = {
        '_url': _url,
        '_headers': _headers,
        '_body': _body,
        '_method': _method,
        '_fill_template': _fill_template,
        'json': json,
        'httpx': httpx,
    }
    exec(fn_src, ns)  # noqa: S102
    fn = ns[tool.name]
    fn.__doc__ = tool.description
    return fn


def get_tools_for_agent(agent) -> list:
    tools = []

    for name in agent.enabled_tools:
        cls = BUILTIN_TOOLS.get(name)
        if cls:
            tools.append(cls())

    for custom_tool in agent.custom_tools.filter(is_active=True):
        tools.append(build_http_function(custom_tool))

    return tools

