"""Fixed in-memory verification fixtures, not customer pages or catalog scenarios."""
from adaptive_qa.interactive_contracts import FormOperation

FIXTURES = {'login-transition':FormOperation.LOGIN,'login-rejected':FormOperation.LOGIN,
    'search-transition':FormOperation.SEARCH,'search-empty':FormOperation.SEARCH,
    'no-transition':FormOperation.LOGIN,'canary':FormOperation.LOGIN,'busy':FormOperation.LOGIN}


def fixture_document(fixture_id,url):
    operation=FIXTURES[fixture_id]
    controls = ('<label>Username<input name="user"></label><label>Password<input type="password" name="password"></label><button>Sign in</button>'
        if operation==FormOperation.LOGIN else '<label>Search products<input type="search" name="query"></label><button>Search</button>')
    marker = 'negative' if fixture_id in ('login-rejected','search-empty') else 'result'
    script = "document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();document.querySelector('[data-testid="+marker+"]').hidden=false;});"
    if fixture_id=='no-transition':script="document.querySelector('form').addEventListener('submit',e=>e.preventDefault());"
    if fixture_id=='canary':script+="document.querySelector('input').addEventListener('input',()=>fetch('https://example.invalid/denied'));"
    if fixture_id=='busy':script='while(true){}'
    return '<meta charset="utf-8"><form method="get" action="'+url+'">'+controls+'</form><div data-testid="result" hidden>Complete</div><div data-testid="negative" hidden>Rejected</div><script>'+script+'</script>'
